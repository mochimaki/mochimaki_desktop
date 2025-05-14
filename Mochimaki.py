import os
import subprocess
import json
import flet as ft
import webbrowser
import time
import re
import signal
from utils import (
    show_error_dialog,
    show_status,
    on_edit_ip_options,
    get_container_settings,
    update_settings_json,
    parse_project_info,
    DockerComposeGenerator,
    clone_repositories,
    clone_dockerfiles
)
from utils.container_utils import extract_service_name
from typing import Dict, Any
from pathlib import Path

# グローバル変数の宣言
global docker_compose_dir
docker_compose_dir = None
global containers_info
containers_info = {}
global snack_bar
global desktop_processes
desktop_processes = {}

def get_container_status(container):
    if container['id'] and container['state'].lower() == "running":
        return "実行中"
    elif container['id']:
        return "停止中"
    elif not container['id'] and container['state'] == "not created":
        return "未生成"
    else:
        return "不明"

def set_card_color(card, state):
    if state == "desktop":
        color = ft.Colors.BLUE_400  # 青色（デスクトップ）
    elif state.lower() == "running":
        color = ft.Colors.GREEN_400  # 明るい緑（起動中）
    elif state.lower() == "exited":
        color = ft.Colors.GREEN_900  # 暗い緑（停止）
    else:
        color = ft.Colors.GREY_700  # 灰色（存在しないまたはその他の状態）
    
    # Containerの背景色を設定する代わりに、borderを設定
    card.content.bgcolor = ft.Colors.TRANSPARENT  # 背景を透明に
    card.content.border = ft.border.all(2, color)  # 輪郭線を設定
    card.content.border_radius = ft.border_radius.all(10)  # 角の丸みを追加

def on_open_browser_click(e, container_name, port):
    """ブラウザを開くボタンがクリックされたときの処理"""
    if container_name in containers_info and containers_info[container_name]['ports']:
        ports = containers_info[container_name]['ports']
        if int(port) in ports:
            host_port = ports[int(port)]
            url = f"http://localhost:{host_port}"
            webbrowser.open(url)

def get_container_info(docker_compose_dir, page: ft.Page):
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

        # グローバル変数 containers_info を更新
        global containers_info
        containers_info = {container['name']: container for container in container_info}

        return container_info
    except subprocess.CalledProcessError as e:
        show_error_dialog(page, "Docker Composeエラー", f"Docker Composeコマンドの実行中にエラーが発生しました: {e}\n\n標準エラー出力: {e.stderr}")
        return []
    except Exception as e:
        show_error_dialog(page, "エラー", f"予期せぬエラーが発生しました: {e}")
        return []
    
def update_container_info_in_project_info(docker_compose_dir, container_info):
    """project_info.jsonにコンテナIDとイメージ情報を反映する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        # servicesの各サービスに対してコンテナIDとイメージを更新
        if 'services' in settings:
            for service_name, service_info in settings['services'].items():
                # コンテナ名を構築（例：m2k-app03-fg_pg-1）
                project_name = Path(docker_compose_dir).name
                container_name = f"{project_name}-{service_name}-1"
                
                # 対応するコンテナ情報を探す
                for container in container_info:
                    if container['name'] == container_name:
                        # コンテナIDを更新
                        service_info['id'] = container['id']
                        # イメージを更新（存在する場合のみ）
                        if container.get('image'):
                            service_info['image'] = container['image']
                        break
        
        # 更新した設定を保存
        with project_info_path.open('w') as f:
            json.dump(settings, f, indent=2)
            
        print("コンテナIDとイメージ情報をproject_info.jsonに反映しました")
        
    except Exception as e:
        print(f"project_info.json更新エラー: {e}")

def update_apps_card(container_name, container_list, page, get_settings_func):
    """アプリケーションカードを更新する"""
    try:
        # 設定情報を取得
        settings = get_settings_func(docker_compose_dir, page)
        if not settings:
            return

        is_desktop = container_name == "host_machine"

        # カードを探す
        target_card = None
        if is_desktop:
            if container_list.controls:
                target_card = container_list.controls[0]
        else:
            if container_name not in containers_info:
                return
            container = containers_info[container_name]
            for control in container_list.controls:
                if isinstance(control, ft.Card) and control.data and control.data.get('name') == container_name:
                    target_card = control
                    break

        if not target_card:
            return

        # アプリケーション情報の取得
        if is_desktop:
            if 'desktop_apps' not in settings:
                return
            apps_dict = settings['desktop_apps'].get('host_machine', {}).get('apps', {})
        else:
            service_name = extract_service_name(container['name'], docker_compose_dir)
            if not service_name:
                raise ValueError("サービス名の抽出に失敗しました")
            apps_dict = settings['services'][service_name]['apps']

        # アプリケーションパネルのリストを作成
        app_panels = []
        for app_name, app_info in apps_dict.items():
            # アプリケーション名のテキスト
            app_name_text = ft.Text(
                f"アプリケーション: {app_name}",
                size=14,
                weight=ft.FontWeight.BOLD,
                tooltip=f"プログラム: {Path(app_info['main']).name if is_desktop else app_info.get('app', '不明')}"
            )

            # コントロールボタンまたはブラウザボタンの作成
            control_elements = []
            if is_desktop:
                current_state = get_app_status(app_name)
                control_elements.append(
                    ft.IconButton(
                        icon=ft.Icons.STOP if current_state == "running" else ft.Icons.PLAY_ARROW,
                        tooltip="起動/停止",
                        on_click=lambda e, name=app_name, info=app_info, btn=None: 
                            on_app_control(e, name, info, e.control, page)
                    )
                )
            else:
                container_port = app_info.get('container_port', '')
                host_port = ''
                if container_port and int(container_port) in container['ports']:
                    host_port = container['ports'][int(container_port)]
                control_elements.extend([
                    ft.Text(f"ポート: {container_port}->{host_port}" if host_port else "ポート: 未割当"),
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_BROWSER,
                        tooltip="ブラウザで開く",
                        on_click=lambda e, name=container['name'], port=container_port: 
                            on_open_browser_click(e, name, port),
                        disabled=container['state'].lower() != "running" or not host_port
                    )
                ])

            # データルートを取得
            data_roots = get_required_data_roots(app_info)

            # アプリケーションカード
            app_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Column([app_name_text] + 
                                    ([control_elements[0]] if is_desktop else [control_elements[0]]), 
                                    expand=True),
                            control_elements[-1] if not is_desktop else ft.Container()
                        ]),
                        # デバイスパネル
                        ft.ExpansionPanelList(
                            controls=[
                                ft.ExpansionPanel(
                                    header=ft.ListTile(
                                        title=ft.Text("デバイス設定", size=12, weight=ft.FontWeight.BOLD),
                                    ),
                                    content=ft.Column([
                                        ft.Container(
                                            content=ft.Row([
                                                ft.Column([
                                                    ft.Text(f"デバイス: {device_type}", size=12, weight=ft.FontWeight.BOLD),
                                                    ft.Text(f"IPアドレス: {', '.join(device_info.get('target', []) or ['未設定'])}", size=12)
                                                ], expand=True),
                                                ft.IconButton(
                                                    icon=ft.Icons.SETTINGS,
                                                    tooltip="IPアドレス設定",
                                                    on_click=lambda e, a=app_name, d=device_type: 
                                                        show_ip_setting_dialog(page, 
                                                                            "host_machine" if is_desktop else container, 
                                                                            a, d, container_list)
                                                )
                                            ]),
                                            padding=5,
                                            bgcolor=ft.Colors.GREY_700,
                                            border_radius=ft.border_radius.all(5)
                                        )
                                        for device_type, device_info in app_info.get('devices', {}).items()
                                    ], spacing=5),
                                    bgcolor=ft.Colors.TRANSPARENT,
                                    expanded=False
                                )
                            ] if app_info.get('devices') else [],
                            elevation=0,
                            spacing=0
                        ),
                        # データ設定パネル
                        ft.ExpansionPanelList(
                            controls=[
                                ft.ExpansionPanel(
                                    header=ft.ListTile(
                                        title=ft.Text("データ設定", size=12, weight=ft.FontWeight.BOLD),
                                    ),
                                    content=ft.Column([
                                        ft.Container(
                                            content=ft.Row([
                                                ft.Column([
                                                    ft.Text(f"データ: {data_root}", size=12, weight=ft.FontWeight.BOLD),
                                                    ft.Text(
                                                        f"パス: {next((path for path in app_info.get('data_roots', []) if data_root in path), '未設定')}", 
                                                        size=12
                                                    )
                                                ], expand=True),
                                                ft.IconButton(
                                                    icon=ft.icons.FOLDER_OPEN,
                                                    tooltip="パスを設定",
                                                    on_click=lambda e, container_name=container_name, a=app_name, d=data_root: 
                                                        show_data_path_dialog(page, container_name, a, d, container_list)
                                                )
                                            ]),
                                            padding=5,
                                            bgcolor=ft.Colors.GREY_700,
                                            border_radius=ft.border_radius.all(5)
                                        )
                                        for data_root in data_roots
                                    ], spacing=5),
                                    bgcolor=ft.Colors.TRANSPARENT,
                                    expanded=False
                                )
                            ] if data_roots else [],
                            elevation=0,
                            spacing=0
                        )
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=ft.border_radius.all(5)
                ),
                margin=ft.margin.only(left=10, right=10, top=5, bottom=5)
            )
            app_panels.append(app_card)

        # メインカードの内容を作成
        header_row = ft.Row([])
        if is_desktop:
            header_row.controls.append(
                ft.Column([
                    ft.Text("Desktop Apps", size=16, weight=ft.FontWeight.BOLD),
                ], expand=True)
            )
        else:
            header_row.controls.extend([
                ft.IconButton(
                    icon=get_container_control_icon(container['state']),
                    tooltip="起動/停止",
                    on_click=lambda e, c=container: on_control_button_click(e, c, page, container_list, get_container_settings)
                ),
                ft.VerticalDivider(width=1),
                ft.Column([
                    ft.Text(
                        f"コンテナ名: {container['name']}", 
                        size=16, 
                        weight=ft.FontWeight.BOLD,
                        tooltip=f"イメージ: {container.get('image', '未設定')}"
                    ),
                    ft.Text(f"コンテナID: {container['id'] or '未生成'}"),
                    ft.Text(f"状態: {get_container_status(container)}"),
                ], expand=True)
            ])

        # カード内容の更新
        target_card.content = ft.Container(
            content=ft.Column([
                header_row,
                ft.ExpansionPanelList(
                    controls=[
                        ft.ExpansionPanel(
                            header=ft.ListTile(
                                title=ft.Text("アプリケーション", size=14, weight=ft.FontWeight.BOLD),
                            ),
                            content=ft.Column(
                                controls=app_panels,
                                spacing=5
                            ),
                            bgcolor=ft.Colors.TRANSPARENT,
                            expanded=True
                        )
                    ],
                    elevation=0,
                    spacing=0
                )
            ]),
            padding=10
        )

        # カードの色を設定
        if is_desktop:
            set_card_color(target_card, "desktop")
        else:
            target_card.data = container
            set_card_color(target_card, container['state'])

        page.update()

    except Exception as e:
        print(f"カードの更新でエラーが発生: {e}")
        
def get_required_data_roots(app_info: dict) -> list:
    """必要なデータルートを取得する"""
    print("get_required_data_roots called with:", app_info)  # デバッグ出力
    main_path = Path(app_info['main'])
    if not main_path.is_absolute():
        main_path = Path(docker_compose_dir) / main_path
    print("main_path:", main_path)  # デバッグ出力

    program_name = main_path.stem
    print("program_name:", program_name)  # デバッグ出力
    
    if 'desktop_apps' in str(main_path):
        original_dir = main_path.parent
        if original_dir.is_symlink():
            original_dir = original_dir.resolve()
    else:
        original_dir = Path(docker_compose_dir) / 'programs' / program_name
    print("original_dir:", original_dir)  # デバッグ出力
    
    config_path = original_dir / 'app_config.json'
    print("config_path:", config_path)  # デバッグ出力
    
    try:
        with config_path.open('r', encoding='utf-8') as f:
            app_config = json.load(f)
            data_roots = app_config.get('data_roots', [])
            print("data_roots:", data_roots)  # デバッグ出力
            return data_roots
    except Exception as e:
        print(f"app_config.jsonの読み込みに失敗: {e}")
        print(f"探索したパス: {config_path}")
        return []

def get_app_status(app_name):
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

def on_app_control(e, app_name, app_info, button, page):
    """アプリケーションの起動/停止制御"""
    current_state = get_app_status(app_name)
    
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

def wait_for_container(container_name, docker_compose_dir, timeout=60):
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

def create_error_text():
    """エラーメッセージ用のテキストコントロールを作成"""
    return ft.Text(
        value="",
        color=ft.Colors.RED_400,
        size=12,
        visible=False
    )

def show_error_message(error_text, scrollable_container, message, page):
    """エラーメッセージを表示"""
    error_text.value = message
    error_text.visible = True
    scrollable_container.border = ft.border.all(1, ft.Colors.RED_400)
    page.update()

def clear_error_message(error_text, scrollable_container, page):
    """エラーメッセージをクリア"""
    error_text.value = ""
    error_text.visible = False
    scrollable_container.border = ft.border.all(1, ft.Colors.GREY_400)
    page.update()

def validate_ip_selections(selected_ips, min_connections, max_connections):
    """選択されたIPアドレスの検証を行う"""
    error_messages = []
    
    # 接続数の検証
    current_count = len(selected_ips)
    if current_count < min_connections:
        error_msg = f"最低{min_connections}個のIPアドレスを設定してください。（現在：{current_count}個）"
        error_messages.append(error_msg)
    if max_connections is not None and current_count > max_connections:
        error_msg = f"IPアドレスは最大{max_connections}個まで設定できます。（現在：{current_count}個）"
        error_messages.append(error_msg)
    
    # 重複チェック
    value_counts = {}
    for ip in selected_ips:
        value_counts[ip] = value_counts.get(ip, 0) + 1
    
    duplicates = {ip for ip, count in value_counts.items() if count > 1}
    
    return error_messages, duplicates, value_counts

def update_all_dropdowns(ip_dropdowns_column, error_text, scrollable_container, apply_button, min_connections, max_connections, allow_duplicate, page):
    """全てのドロップダウンの選択肢と色を更新"""
    try:
        # 選択されているIPアドレスとその出現回数を収集
        value_counts = {}
        selected_ips = []
        
        # すべてのドロップダウンから値を収集
        for control in ip_dropdowns_column.controls:
            if isinstance(control, ft.Container):
                row = control.content  # Row
                dropdown_container = row.controls[0]  # Container
                dropdown = dropdown_container.content  # Dropdown
                if isinstance(dropdown, ft.Dropdown) and dropdown.value:
                    ip = dropdown.value
                    selected_ips.append(ip)
                    value_counts[ip] = value_counts.get(ip, 0) + 1

        # 検証を実行
        error_messages, duplicates, value_counts = validate_ip_selections(
            selected_ips, min_connections, max_connections
        )
        
        # エラーメッセージの表示と適用ボタンの制御
        messages = []
        if duplicates:
            messages.append("IPアドレスが重複しています")
            if not allow_duplicate:
                apply_button.disabled = True
        if error_messages:
            messages.extend(error_messages)
            apply_button.disabled = True
        
        if messages:
            show_error_message(error_text, scrollable_container, "\n".join(messages), page)
        else:
            clear_error_message(error_text, scrollable_container, page)
            apply_button.disabled = False
        
        # 各ドロップダウンの色を更新
        color_index = 0
        used_colors = {}
        duplicate_colors = [
            ft.Colors.RED_400,
            ft.Colors.GREEN_400,
            ft.Colors.BLUE_400,
            ft.Colors.ORANGE_400,
            ft.Colors.PURPLE_400,
            ft.Colors.CYAN_400,
        ]

        for control in ip_dropdowns_column.controls:
            if isinstance(control, ft.Container):
                row = control.content  # Row
                dropdown_container = row.controls[0]  # Container
                dropdown = dropdown_container.content  # Dropdown
                if isinstance(dropdown, ft.Dropdown) and dropdown.value:
                    if dropdown.value in duplicates:
                        if dropdown.value not in used_colors:
                            used_colors[dropdown.value] = duplicate_colors[color_index % len(duplicate_colors)]
                            color_index += 1
                        dropdown_container.bgcolor = ft.Colors.with_opacity(0.1, used_colors[dropdown.value])
                        dropdown_container.border = ft.border.all(2, used_colors[dropdown.value])
                        dropdown.color = used_colors[dropdown.value]
                        dropdown.text_style = ft.TextStyle(
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=used_colors[dropdown.value]
                        )
                    else:
                        dropdown_container.bgcolor = None
                        dropdown_container.border = ft.border.all(1, ft.Colors.GREY_400)
                        dropdown.color = None
                        dropdown.text_style = ft.TextStyle(
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        )

        # 接続数制限違反時の枠線色変更
        current_count = len(selected_ips)
        if current_count < min_connections or (max_connections is not None and current_count > max_connections):
            scrollable_container.border = ft.border.all(1, ft.Colors.RED_400)
        else:
            scrollable_container.border = ft.border.all(1, ft.Colors.GREY_400)

        page.update()

    except Exception as e:
        print(f"update_all_dropdowns でエラーが発生: {e}")
        import traceback
        print(traceback.format_exc())

def show_ip_setting_dialog(page: ft.Page, container, app_name, device_type, container_list):
    """IPアドレス設定ダイアログを表示する"""
    print(f"""show_ip_setting_dialog が呼び出されました:
page: {page}
container: {container}
app_name: {app_name}
device_type: {device_type}
container_list: {container_list}
""")
    try:
        settings = get_container_settings(docker_compose_dir, page)

        # コンテナ名が"host_machine"の場合はデスクトップアプリとして処理
        if container == "host_machine":
            if ('desktop_apps' not in settings or 
                'host_machine' not in settings['desktop_apps'] or
                app_name not in settings['desktop_apps']['host_machine']['apps']):
                show_error_dialog(page, "設定エラー", "アプリケーション設定が見つかりません。")
                return
            app_info = settings['desktop_apps']['host_machine']['apps'][app_name]
        else:
            # 通常のコンテナアプリの場合
            service_name = extract_service_name(container['name'], docker_compose_dir)

            if not service_name:
                show_error_dialog(page, "設定エラー", "サービス名の抽出に失敗しました")
                return
            
            if (service_name not in settings['services'] or 
                app_name not in settings['services'][service_name]['apps']):
                show_error_dialog(page, "設定エラー", "アプリケーション設定が見つかりません。")
                return

            app_info = settings['services'][service_name]['apps'][app_name]
        
        # デバイス設定の取得と接続数制限の解析
        if ('devices' not in app_info or 
            device_type not in app_info['devices'] or 
            'num' not in app_info['devices'][device_type]):
            show_error_dialog(page, "設定エラー", "デバイス接続数の設定が見つかりません。")
            return

        # 接続数制限とフラグを解析
        num_constraint = app_info['devices'][device_type]['num']
        try:
            min_conn, max_conn_str, allow_duplicate_str = num_constraint.split(':')
            min_connections = int(min_conn)
            max_connections = int(max_conn_str) if max_conn_str else None
            allow_duplicate = bool(int(allow_duplicate_str))  # 0/1 を False/True に変換
        except ValueError:
            show_error_dialog(page, "設定エラー", f"デバイス接続数の形式が不正です: {num_constraint}")
            return

        # 利用可能なIPアドレスの取得
        if ('devices' not in app_info or 
            device_type not in app_info['devices'] or 
            'ip_addr' not in app_info['devices'][device_type]):
            show_error_dialog(page, "設定エラー", "利用可能なIPアドレスが設定されていません。")
            return

        ip_addresses = app_info['devices'][device_type]['ip_addr']
        if not ip_addresses:
            show_error_dialog(page, "設定エラー", "IPアドレスのリストが空です。")
            return

        # 現在のtargetを取得
        current_targets = []
        if ('devices' in app_info and 
            device_type in app_info['devices'] and 
            'target' in app_info['devices'][device_type]):
            current_targets = app_info['devices'][device_type]['target']

        # エラーメッセージ用のテキスト
        error_text = create_error_text()

        # IPアドレス選択用のカラム
        ip_dropdowns_column = ft.Column(spacing=10)

        def create_ip_dropdown_row(page: ft.Page, ip_dropdowns_column: ft.Column, available_ips: list, initial_value=None):
            def on_delete_click(e):
                ip_dropdowns_column.controls.remove(row_container)
                update_all_dropdowns(ip_dropdowns_column, error_text, scrollable_container, apply_button, 
                                   min_connections, max_connections, allow_duplicate, page)
                page.update()

            def on_change(e):
                update_all_dropdowns(ip_dropdowns_column, error_text, scrollable_container, apply_button, 
                                   min_connections, max_connections, allow_duplicate, page)

            dropdown = ft.Dropdown(
                options=[ft.dropdown.Option(ip) for ip in available_ips],
                value=initial_value,
                width=200,
                on_change=on_change,
                text_style=ft.TextStyle(
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                color=None
            )

            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="削除",
                on_click=on_delete_click
            )

            row_container = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=dropdown,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=ft.border_radius.all(4),
                            padding=ft.padding.all(1),
                        ),
                        delete_button
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                margin=ft.margin.only(left=10, right=10)
            )

            return row_container

        def on_add_click(e):
            """新しいドロップダウンを追加"""
            new_row = create_ip_dropdown_row(page, ip_dropdowns_column, ip_addresses)
            ip_dropdowns_column.controls.append(new_row)
            scrollable_container.content.scroll_to(offset=-1)
            update_all_dropdowns(ip_dropdowns_column, error_text, scrollable_container, apply_button, 
                               min_connections, max_connections, allow_duplicate, page)
            page.update()

        def on_apply(e):
            """変更を適用してダイアログを閉じる"""
            try:
                # 選択されたIPアドレスを収集
                new_targets = []
                for control in ip_dropdowns_column.controls:
                    if isinstance(control, ft.Container):
                        dropdown = control.content.controls[0].content
                        if dropdown.value:
                            new_targets.append(dropdown.value)

                # 最小接続数のチェック
                if len(new_targets) < min_connections:
                    show_error_message(error_text, scrollable_container, 
                                     f"最低{min_connections}個のIPアドレスを設定してください。", page)
                    return

                # 設定を更新
                service_or_host = "host_machine" if container == "host_machine" else service_name
                if update_settings_json(docker_compose_dir, new_targets, service_or_host, app_name, device_type, page):
                    # デスクトップアプリの場合はapp_info.jsonを再生成
                    if container == "host_machine":
                        settings = get_container_settings(docker_compose_dir, page)
                        if 'desktop_apps' in settings:
                            setup_desktop_apps_directory(docker_compose_dir, settings['desktop_apps'], page)
                        update_apps_card("host_machine", container_list, page, get_container_settings)
                    else:
                        update_apps_card(container['name'], container_list, page, get_container_settings)
                    close_dialog(e)
                else:
                    show_error_message(error_text, scrollable_container, "設定の更新に失敗しました。", page)

            except Exception as e:
                show_error_message(error_text, scrollable_container, f"エラーが発生しました: {e}", page)

        def close_dialog(e):
            """ダイアログを閉じる"""
            dialog.open = False
            page.update()
            page.overlay.remove(dialog)

        # 既存のターゲットIPアドレスの行を作成
        for target in current_targets:
            row = create_ip_dropdown_row(page, ip_dropdowns_column, ip_addresses, target)
            ip_dropdowns_column.controls.append(row)

        # スクロール可能なコンテナを作成
        scrollable_container = ft.Container(
            content=ft.Column(
                controls=[ip_dropdowns_column],
                scroll=ft.ScrollMode.AUTO  # スクロールはここに設定
            ),
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=10,
            padding=10,
            height=300
        )

        # 適用ボタン
        apply_button = ft.ElevatedButton(
            text="適用",
            on_click=on_apply
        )

        # ダイアログを作成
        dialog = ft.AlertDialog(
            title=ft.Text(f"{device_type}のIPアドレス設定"),
            content=ft.Container(
                content=ft.Column([
                    error_text,
                    scrollable_container,
                    ft.Row([
                        ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.ADD,
                                tooltip="IPアドレスを追加",
                                on_click=on_add_click
                            ),
                            alignment=ft.alignment.center
                        ),
                        ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.EDIT_NOTE,
                                tooltip="IPアドレスの選択肢を編集",
                                on_click=lambda e: on_edit_ip_options(e, page, ip_addresses, docker_compose_dir, device_type)
                            ),
                            alignment=ft.alignment.center
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ], 
                spacing=10
                ),
                width=400
            ),
            actions=[
                apply_button,
                ft.TextButton("キャンセル", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # 初期状態の検証を実行
        update_all_dropdowns(ip_dropdowns_column, error_text, scrollable_container, apply_button, 
                           min_connections, max_connections, allow_duplicate, page)

        # ダイアログを表示
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    except Exception as e:
        show_error_dialog(page, "エラー", f"IPアドレス設定ダイアログの表示に失敗しました: {e}")

def start_container(container, page, container_list, get_settings_func):
    global docker_compose_dir, containers_info
    try:
        show_status(page, f"コンテナ {container['name']} を起動中...")

        # サービス名を抽出
        service_name = extract_service_name(container['name'], docker_compose_dir)
        if not service_name:
            raise ValueError("サービス名の抽出に失敗しました")

        subprocess.check_call(['docker-compose', 'up', '-d', service_name], cwd=docker_compose_dir)
        
        if wait_for_container(container['name'], docker_compose_dir):
            show_status(page, f"コンテナ {container['name']} が正常に起動しました。")
        else:
            show_status(page, f"コンテナ {container['name']} の起動がタイムアウトしました。")
            return

        # コンテナ情報を再取得
        get_container_info(docker_compose_dir, page)
        
        # 更新されたコンテナ情報を使用してカードを更新
        if container['name'] in containers_info:
            update_apps_card(container['name'], container_list, page, get_settings_func)
        

        page.update()
    except Exception as e:
        show_status(page, f"起動エラー: {e}")
        page.update()

def stop_container(container, page, container_list, get_settings_func):
    global docker_compose_dir, containers_info
    try:
        show_status(page, f"コンテナ {container['name']} を停止中...")

        # サービス名を抽出
        service_name = extract_service_name(container['name'], docker_compose_dir)
        if not service_name:
            raise ValueError("サービス名の抽出に失敗しました")

        subprocess.check_call(['docker-compose', 'stop', service_name], cwd=docker_compose_dir)
        
        # コンテナ情報を再取得
        get_container_info(docker_compose_dir, page)
        
        # 更新されたコンテナ情報を使用してカードを更新
        if container['name'] in containers_info:
            update_apps_card(container['name'], container_list, page, get_settings_func)
        

        show_status(page, f"コンテナ {container['name']} を停止しました。")
        page.update()
    except Exception as e:
        show_status(page, f"停止エラー: {e}")
        page.update()

def on_control_button_click(e, container, page, container_list, get_settings_func):
    button = e.control
    current_icon = button.icon
    
    print(f"現在のアイコン: {current_icon}")
    print(f"コンテナの状態: {container['state']}")
    print(f"コンテナの情報: {container}")
    
    if current_icon == ft.Icons.PLAY_CIRCLE:
        start_container(container, page, container_list, get_settings_func)
    else:
        stop_container(container, page, container_list, get_settings_func)

def create_apps_card(app_type, data, page, container_list, get_settings_func):
    """アプリケーションカードを生成する
    
    Args:
        app_type (str): "desktop" または "container"
        data (dict): アプリケーションのデータ
        page (ft.Page): ページオブジェクト
        container_list (ft.Column): コンテナリスト
        get_settings_func (function): 設定取得関数
    """
    # 起動・停止ボタン（コンテナアプリの場合のみ表示）
    control_button = (
        ft.IconButton(
            icon=get_container_control_icon(data.get('state', '')),
            tooltip="起動/停止",
            on_click=lambda e, c=data: on_control_button_click(e, c, page, container_list, get_settings_func)
        ) if app_type == "container" else ft.Container(width=0)
    )

    # アプリケーション情報
    info_column = ft.Column([
        ft.Text(
            "ホストマシン" if app_type == "desktop" else f"コンテナ名: {data.get('name', '')}",
            size=16,
            weight=ft.FontWeight.BOLD
        ),
    ], expand=True)

    # コンテナアプリの場合のみ追加情報を表示
    if app_type == "container":
        info_column.controls.extend([
            ft.Text(f"コンテナID: {data.get('id', '') or '未生成'}"),
            ft.Text(f"状態: {get_container_status(data)}"),
        ])

    # カードの作成
    app_card = ft.Card(
        content=ft.Container(
            content=ft.Row([
                control_button,
                ft.VerticalDivider(width=1),
                info_column,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10
        ),
        margin=10,
        data=data
    )

    # カードの色を設定
    set_card_color(app_card, "desktop" if app_type == "desktop" else data.get('state', ''))

    return app_card

def show_data_path_dialog(page: ft.Page, container_name: str, app_name: str, data_root: str, container_list: ft.Column):
    """データパス設定ダイアログを表示する"""
    try:
        def on_dialog_result(e: ft.FilePickerResultEvent):
            if e.path:
                # 選択されたディレクトリ名を取得
                selected_dir_name = Path(e.path).name
                
                # 選択されたディレクトリ名が対象と異なる場合は警告
                if selected_dir_name != data_root:
                    def close_dialog(e):
                        page.dialog.open = False
                        page.dialog = None
                        page.update()

                    page.dialog = ft.AlertDialog(
                        title=ft.Text("警告"),
                        content=ft.Text(f"選択されたディレクトリ名 '{selected_dir_name}' が\n"
                                      f"対象のディレクトリ名 '{data_root}' と異なります。"),
                        actions=[
                            ft.TextButton("OK", on_click=close_dialog)
                        ]
                    )
                    page.dialog.open = True
                    page.update()
                    return

                # project_info.jsonを読み込む
                project_info_path = Path(docker_compose_dir) / 'project_info.json'
                with project_info_path.open('r', encoding='utf-8') as f:
                    project_info = json.load(f)

                # コンテナ名からアプリケーションの種類を判断
                is_desktop = container_name == "host_machine"

                # data_rootsを更新
                if is_desktop:
                    # デスクトップアプリの場合
                    if 'desktop_apps' in project_info and 'host_machine' in project_info['desktop_apps']:
                        if app_name in project_info['desktop_apps']['host_machine']['apps']:
                            app_info = project_info['desktop_apps']['host_machine']['apps'][app_name]
                            if 'data_roots' not in app_info:
                                app_info['data_roots'] = []
                            
                            # 既存のパスを新しいパスで置き換え
                            data_roots = app_info['data_roots']
                            for i, path in enumerate(data_roots):
                                if data_root in str(Path(path)):  # 対象のデータルートを含むパスを見つけたら
                                    data_roots[i] = e.path  # 新しいパスで置き換え
                                    break
                            else:  # 既存のパスが見つからない場合は追加
                                data_roots.append(e.path)
                else:
                    # コンテナアプリの場合
                    service_name = extract_service_name(container_name, docker_compose_dir)
                    if service_name in project_info.get('services', {}):
                        service = project_info['services'][service_name]
                        if app_name in service.get('apps', {}):
                            app_info = service['apps'][app_name]
                            if 'data_roots' not in app_info:
                                app_info['data_roots'] = []
                            
                            # 既存のパスを新しいパスで置き換え
                            data_roots = app_info['data_roots']
                            for i, path in enumerate(data_roots):
                                if data_root in str(Path(path)):  # 対象のデータルートを含むパスを見つけたら
                                    data_roots[i] = e.path  # 新しいパスで置き換え
                                    break
                            else:  # 既存のパスが見つからない場合は追加
                                data_roots.append(e.path)

                # project_info.jsonを保存
                with project_info_path.open('w', encoding='utf-8') as f:
                    json.dump(project_info, f, indent=2, ensure_ascii=False)

                # コンテナアプリの場合のみparse_project_infoを実行
                if not is_desktop:
                    parse_project_info(docker_compose_dir)

                # on_container_dialog_resultを直接呼び出し
                class MockEvent:
                    def __init__(self, path):
                        self.path = path

                mock_event = MockEvent(docker_compose_dir)
                on_container_dialog_result(mock_event, page, container_list)

        # ディレクトリ選択ダイアログを表示
        file_picker = ft.FilePicker(
            on_result=on_dialog_result
        )
        page.overlay.append(file_picker)
        page.update()
        file_picker.get_directory_path()

    except Exception as e:
        print(f"データパス設定ダイアログでエラーが発生: {e}")
        def close_error_dialog(e):
            page.dialog.open = False
            page.dialog = None
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("エラー"),
            content=ft.Text(f"データパス設定中にエラーが発生しました:\n{str(e)}"),
            actions=[
                ft.TextButton("OK", on_click=close_error_dialog)
            ]
        )
        page.dialog.open = True
        page.update()

def refresh_container_status(page, container_list):
    global docker_compose_dir, containers_info
    if not docker_compose_dir:
        show_status(page, "ビルドコンテキストが選択されていません。")
        page.update()
        return

    try:
        show_status(page, "情報を更新中...")

        settings = get_container_settings(docker_compose_dir, page)
        if not settings:
            return

        container_list.controls.clear()

        # デスクトップカードを先頭に追加
        if 'desktop_apps' in settings:
            desktop_card = create_apps_card("desktop", settings['desktop_apps'], page, container_list, get_container_settings)
            container_list.controls.append(desktop_card)
            update_apps_card("host_machine", container_list, page, get_container_settings)

        # コンテナサービスが存在する場合のみコンテナ関連の処理を実行
        if 'services' in settings and settings['services']:
            parse_project_info(docker_compose_dir)
            containers = get_container_info(docker_compose_dir, page)

            if containers:
                for container in containers:
                    container_card = create_apps_card("container", container, page, container_list, get_container_settings)
                    container_list.controls.append(container_card)
                    update_apps_card(container['name'], container_list, page, get_container_settings)

        show_status(page, "情報を更新しました。")
        page.update()

    except Exception as e:
        show_error_dialog(page, "エラー", f"情報の更新中にエラーが発生しました: {e}")

def get_container_control_icon(state):
    if state.lower() == "running":
        return ft.Icons.STOP_CIRCLE
    elif state.lower() in ["exited", "not created", ""]:  # 停止中や未生成の状態を追加
        return ft.Icons.PLAY_CIRCLE
    else:
        return ft.Icons.PLAY_CIRCLE  # デフォルトは起動アイコン
    
def create_symlink(src: str, dst: str, page: ft.Page = None):
    """プラットフォームに応じてシンボリックリンクを作成する"""
    try:
        import shutil
        src_path = Path(src)
        dst_path = Path(dst)
        
        # 既存のディレクトリやファイルを削除
        if dst_path.exists():
            if dst_path.is_symlink():  # シンボリックリンクの場合
                dst_path.unlink()  # リンク自体のみを削除
            elif dst_path.is_dir():
                shutil.rmtree(dst_path)
            else:
                dst_path.unlink()

        # Windows環境の場合
        if os.name == 'nt':
            # パスを正規化
            src = str(src_path.resolve())
            dst = str(dst_path)
            
            if src_path.is_dir():
                cmd = f'cmd.exe /c mklink /D "{dst}" "{src}"'
            else:
                cmd = f'cmd.exe /c mklink "{dst}" "{src}"'
            
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                if page:
                    error_message = (
                        "シンボリックリンクの作成に失敗しました。\n\n"
                        "以下の手順で開発者モードを有効にしてください：\n"
                        "1. Windowsの設定を開く（Windowsキー + I）\n"
                        "2. 「システム」を選択\n"
                        "3. 右側のメニューを下にスクロールし、「開発者向け」を選択\n"
                        "4. 「開発者モード」をオンにする\n"
                        "5. アプリケーションを再起動する"
                    )
                    show_error_dialog(page, "開発者モードが必要です", error_message)
                raise Exception("シンボリックリンクの作成に失敗しました。開発者モードを有効にしてください。")
        # Unix系環境の場合
        else:
            dst_path.symlink_to(src_path)

    except Exception as e:
        raise Exception(f"ファイルのリンクの作成に失敗しました: {e}")
        raise Exception(f"ファイルのリンクの作成に失敗しました: {e}")

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

def on_container_dialog_result(e: ft.FilePickerResultEvent, page: ft.Page, container_list: ft.Column):
    """ビルドコンテキストが選択されたときの処理"""
    global docker_compose_dir, containers_info
    if e.path:
        docker_compose_dir = e.path
        page.title = Path(e.path).name
        
        try:
            # project_info.jsonの読み込みと検証
            project_info_path = Path(docker_compose_dir) / 'project_info.json'
            if not project_info_path.exists():
                show_error_dialog(page, "エラー", "project_info.jsonが見つかりません")
                return

            with project_info_path.open('r', encoding='utf-8') as f:
                project_info = json.load(f)

            # リポジトリのクローン処理
            if not clone_repositories(project_info, docker_compose_dir, page):
                return

            # Dockerfileのクローン処理
            if not clone_dockerfiles(project_info, docker_compose_dir, page):
                return

            # デスクトップアプリのディレクトリ構成を設定
            if 'desktop_apps' in project_info:
                setup_desktop_apps_directory(docker_compose_dir, project_info['desktop_apps'], page)
                show_status(page, "デスクトップアプリのディレクトリ構成を設定しました")

            # コンテナサービスがある場合のみdocker-compose.ymlを生成
            if 'services' in project_info and project_info['services']:
                generator = DockerComposeGenerator(str(project_info_path))
                docker_compose_path = Path(docker_compose_dir) / 'docker-compose.yml'
                generator.save(str(docker_compose_path))
                show_status(page, "docker-compose.ymlを生成しました")
            
            refresh_container_status(page, container_list)

        except Exception as e:
            show_error_dialog(page, "エラー", f"セットアップに失敗しました: {str(e)}")
            return

def main(page: ft.Page):
    global containers_info  # snack_barを削除
    containers_info = {}
    page.title = "Mochimaki"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 20

    # スクロール可能なコンテナリストを作成
    container_list = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=10,
    )

    def get_container_height():
        # window_heightの代わりにwindow.heightを使用
        return page.window.height - 150

    # コンテナリストをスクロール可能なコンテナでラップ
    scrollable_container = ft.Container(
        content=container_list,
        height=get_container_height(),  # 動的な高さを設定
        border=ft.border.all(1, ft.Colors.GREY_800),
        border_radius=10,
        padding=10,
    )

    def on_resized(e):  # on_resizeの代わりにon_resizedを使用
        # ウィンドウサイズが変更されたときにコンテナの高さを更新
        scrollable_container.height = get_container_height()
        page.update()

    # ウィンドウサイズ変更イベントのハンドラを設定
    page.on_resized = on_resized  # on_resizeの代わりにon_resizedを使用

    def pick_files_result(e: ft.FilePickerResultEvent):
        """ファイル選択ダイアログの結果を処理"""
        if e.path:  # ディレクトリが選択された場合
            on_container_dialog_result(e, page, container_list)

    # FilePickerを作成
    container_file_picker = ft.FilePicker(
        on_result=pick_files_result
    )
    page.overlay.extend([container_file_picker])

    select_container_button = ft.ElevatedButton(
        "ビルドコンテキストを選択",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _: container_file_picker.get_directory_path()  # ディレクトリ選択モードを使用
    )

    refresh_button = ft.ElevatedButton(
        "状態を更新",
        icon=ft.Icons.REFRESH,
        on_click=lambda _: refresh_container_status(page, container_list)
    )

    # ボタンを横に並べるためのRowを作成
    buttons_row = ft.Row(
        [select_container_button, refresh_button],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,  # ボタン間の間隔を追加
    )

    page.add(
        ft.Column([
            buttons_row,
            scrollable_container  # スクロール可能なコンテナを追加
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,  # 要素間の間隔を追加
        )
    )

ft.app(target=main)