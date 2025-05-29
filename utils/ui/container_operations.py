"""
コンテナ操作に関する関数を提供するモジュール
"""
from typing import Dict, Any
import subprocess
import time
import flet as ft
from pathlib import Path
import json
import os
import re
from ..container_utils import extract_service_name, parse_project_info
from ..dialogs import show_error_dialog
from .app_utils import update_container_info_in_project_info

class ContainerInfoManager:
    """コンテナ情報を管理するクラス"""
    def __init__(self):
        self._containers_info: Dict[str, Dict[str, Any]] = {}
    
    def get_container_info(self, docker_compose_dir: str, page: ft.Page) -> list:
        """
        コンテナ情報を取得する
        
        Args:
            docker_compose_dir: docker-compose.ymlが存在するディレクトリのパス
            page: ページオブジェクト
            
        Returns:
            list: コンテナ情報のリスト
        """
        try:
            os.chdir(docker_compose_dir)
            
            # プロジェクト名を取得（ディレクトリ名）
            project_name = Path(docker_compose_dir).name
            
            # docker-compose.ymlで定義されているサービスを取得
            result = subprocess.run(['docker-compose', 'config', '--services'], 
                                    capture_output=True, text=True, check=True)
            services = result.stdout.strip().split('\n')
            services = [s for s in services if s]

            # 実際のコンテナ情報を取得（イメージ情報を含める）
            result = subprocess.run([
                'docker-compose',
                'ps',
                '-a',
                '--format', 
                '{"Name":"{{ .Name }}","ID":"{{ .ID }}","State":"{{ .State }}","Ports":"{{ .Ports }}","Image":"{{ .Image }}"}'
            ], capture_output=True, text=True, check=True)
            
            compose_output = result.stdout
            
            container_info = []
            json_data = '[' + ','.join(line for line in compose_output.strip().split('\n') if line.strip()) + ']'

            if json_data:
                try:
                    containers = json.loads(json_data)
                    for container in containers:
                        name = container.get('Name', '')
                        short_id = container.get('ID', '')
                        state = container.get('State', '')
                        ports_str = container.get('Ports', '')
                        image = container.get('Image', '')  # イメージ情報を取得
                        
                        # ポート情報をパース
                        ports = {}
                        if ports_str:
                            port_matches = re.findall(r'(\d+)->(\d+)/tcp', ports_str)
                            for host_port, container_port in port_matches:
                                ports[int(container_port)] = int(host_port)
                        
                        container_info.append({
                            'name': name,
                            'id': short_id,
                            'ports': ports,
                            'state': state,
                            'image': image,  # イメージ情報を追加
                            'docker_compose_dir': docker_compose_dir
                        })
                except json.JSONDecodeError as e:
                    print(f"JSONデコードエラー。データ: {json_data}. エラー: {e}")
                except Exception as e:
                    print(f"コンテナ情報のパースエラー。データ: {json_data}. エラー: {e}")

            # サービスリストにないコンテナを追加
            for service in services:
                if not any(c['name'] == f"{project_name}-{service}-1" for c in container_info):
                    # project_info.jsonから既存のimage情報を取得
                    image = ''
                    try:
                        project_info_path = Path(docker_compose_dir) / 'project_info.json'
                        with project_info_path.open('r') as f:
                            project_info = json.load(f)
                            if service in project_info.get('services', {}):
                                image = project_info['services'][service].get('image', '')
                    except Exception as e:
                        print(f"project_info.jsonからimage情報の取得に失敗: {e}")

                    container_info.append({
                        'name': f"{project_name}-{service}-1",
                        'id': '',
                        'ports': {},
                        'state': 'not created',
                        'image': image,  # 既存のimage情報を使用
                        'docker_compose_dir': docker_compose_dir
                    })

            # コンテナIDとイメージをproject_info.jsonに反映
            update_container_info_in_project_info(docker_compose_dir, container_info)
            
            # project_info.jsonを再パース
            parse_project_info(docker_compose_dir)

            # コンテナ情報を更新
            self._containers_info = {container['name']: container for container in container_info}

            return container_info
        except subprocess.CalledProcessError as e:
            show_error_dialog(page, "Docker Composeエラー", f"Docker Composeコマンドの実行中にエラーが発生しました: {e}\n\n標準エラー出力: {e.stderr}")
            return []
        except Exception as e:
            show_error_dialog(page, "エラー", f"予期せぬエラーが発生しました: {e}")
            return []

# シングルトンインスタンス
container_info_manager = ContainerInfoManager()

def get_container_status(container: Dict[str, Any]) -> str:
    """コンテナの状態を取得する
    
    Args:
        container (Dict[str, Any]): コンテナ情報
        
    Returns:
        str: コンテナの状態
    """
    state = container.get('state', '').lower()
    if state == "running":
        return "起動中"
    elif state == "exited":
        return "停止中"
    elif state == "not created":
        return "未生成"
    else:
        return state 

def wait_for_container(container_name, docker_compose_dir, timeout=60):
    """コンテナの起動を待機する
    
    Args:
        container_name (str): コンテナ名
        docker_compose_dir (str): docker-compose.ymlが存在するディレクトリのパス
        timeout (int): タイムアウト時間（秒）
        
    Returns:
        bool: コンテナが起動した場合はTrue、タイムアウトした場合はFalse
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
                capture_output=True,
                text=True,
                check=True,
                cwd=docker_compose_dir
            )
            if result.stdout.strip() == 'true':
                return True
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    return False 