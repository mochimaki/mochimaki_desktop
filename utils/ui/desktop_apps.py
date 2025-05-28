"""
デスクトップアプリケーションの設定に関する関数を提供するモジュール
"""
from pathlib import Path
from typing import Dict, Any
import flet as ft
import json
import subprocess
import os
import signal
from ..file_utils import create_symlink
from ..dialogs import show_status, show_error_dialog

def get_app_status(app_name: str, desktop_processes: Dict[str, Any]) -> str:
    """アプリケーションの状態を確認"""
    if app_name in desktop_processes:
        process = desktop_processes[app_name]
        return_code = process.poll()
        if return_code is None:
            return "running"
    return "stopped"

def create_start_command(app_info):
    """アプリケーションの起動コマンドを生成する"""
    args = []
    for arg_name, arg_value in app_info.get('args', {}).items():
        args.append(f"{arg_name} {arg_value}")
    args_str = " ".join(args)
    command = f"{app_info['interpreter']} {app_info['main']} {args_str}"
    print(f"実行コマンド: {command}")
    return command

def setup_desktop_apps_directory(project_root: str, desktop_apps: Dict[str, Any], page: ft.Page = None):
    try:
        desktop_apps_dir = Path(project_root) / 'desktop_apps'
        desktop_apps_dir.mkdir(exist_ok=True)

        # host_machineのappsを取得
        if 'host_machine' in desktop_apps and 'apps' in desktop_apps['host_machine']:
            apps = desktop_apps['host_machine']['apps']
        else:
            apps = {}

        for app_name, app_info in apps.items():
            # アプリケーションディレクトリの作成
            app_dir = desktop_apps_dir / app_name
            app_dir.mkdir(exist_ok=True)

            # メインプログラムのディレクトリ名を取得
            main_program_path = Path(app_info['main'])
            program_dir_name = main_program_path.parent.name

            # プログラムディレクトリのシンボリックリンクを作成
            src_program_dir = Path(project_root) / 'programs' / program_dir_name
            dst_program_dir = app_dir / program_dir_name
            create_symlink(str(src_program_dir), str(dst_program_dir), page)

            # データルートのシンボリックリンクを作成
            for host_path in app_info.get('data_roots', []):
                src_data_dir = Path(host_path)
                dst_data_dir = app_dir / src_data_dir.name
                create_symlink(str(src_data_dir), str(dst_data_dir), page)

            # app_info.jsonの生成
            app_info_data = {
                "interpreter": app_info['interpreter'],
                "main": str(Path(program_dir_name) / main_program_path.name),
                "args": app_info.get('args', {}),
                "devices": app_info.get('devices', {}),
                "data_roots": {
                    Path(host_path).name: str(app_dir / Path(host_path).name)
                    for host_path in app_info.get('data_roots', [])
                }
            }
            
            app_info_path = app_dir / 'app_info.json'
            with app_info_path.open('w', encoding='utf-8') as f:
                json.dump(app_info_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        raise Exception(f"デスクトップアプリディレクトリの設定に失敗しました: {e}") 

def on_app_control(e, app_name, app_info, button, page, desktop_processes, docker_compose_dir):
    """アプリケーションの起動/停止制御
    
    Args:
        e: イベントオブジェクト
        app_name (str): アプリケーション名
        app_info (Dict[str, Any]): アプリケーション情報
        button (ft.IconButton): 制御ボタン
        page (ft.Page): ページオブジェクト
        desktop_processes (Dict[str, subprocess.Popen]): 実行中のプロセス情報
        docker_compose_dir (str): Docker Composeディレクトリのパス
    """
    current_state = get_app_status(app_name, desktop_processes)
    
    if current_state == "running":
        try:
            # プロセスグループ全体を終了させる
            process = desktop_processes[app_name]
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:  # Unix系
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
            # プロセスの終了を確認
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            
            del desktop_processes[app_name]
            button.icon = ft.Icons.PLAY_ARROW
            show_status(page, f"アプリケーション {app_name} を停止しました")
        except Exception as e:
            show_error_dialog(page, "エラー", f"アプリケーションの停止に失敗しました: {e}")
    else:
        # 起動処理
        try:
            # プログラムのディレクトリを取得
            app_dir = Path(docker_compose_dir) / 'desktop_apps' / app_name
            program_dir = app_dir / Path(app_info['main']).parent.name
            
            cmd = create_start_command(app_info)
            if os.name == 'nt':  # Windows
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(program_dir)  # Popenはstr型のパスを期待するため変換
                )
            else:  # Unix系
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    preexec_fn=os.setsid,
                    cwd=str(program_dir)  # Popenはstr型のパスを期待するため変換
                )
            desktop_processes[app_name] = process
            button.icon = ft.Icons.STOP
            show_status(page, f"アプリケーション {app_name} を起動しました")
        except Exception as e:
            show_error_dialog(page, "エラー", f"アプリケーションの起動に失敗しました: {e}")
    
    page.update() 