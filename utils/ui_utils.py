import flet as ft
from typing import Dict, Any
from .container_utils import extract_service_name, parse_project_info
from .settings import get_container_settings, clone_repositories, clone_dockerfiles
from .dialogs import show_status, show_error_dialog
from .ip_settings import update_settings_json, on_edit_ip_options
from .generate_docker_compose import DockerComposeGenerator
from .ui import (
    get_container_status,
    get_container_control_icon,
    set_card_color,
    get_required_data_roots,
    on_open_browser_click,
    wait_for_container,
    create_error_text,
    show_error_message,
    update_all_dropdowns,
    setup_desktop_apps_directory,
    get_app_status,
    on_app_control,
    container_info_manager
)
from pathlib import Path
import subprocess
import json

# グローバル変数の定義
docker_compose_dir = Path(__file__).parent.parent.parent / "docker-compose"
desktop_processes = {}

def start_container(container, page, container_list, get_settings_func):
    """コンテナを起動する
    
    Args:
        container (Dict[str, Any]): コンテナ情報
        page (ft.Page): ページオブジェクト
        container_list (ft.Column): コンテナリスト
        get_settings_func (function): 設定取得関数
    """
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
        container_info_manager.get_container_info(docker_compose_dir, page)
        
        # 更新されたコンテナ情報を使用してカードを更新
        if container['name'] in container_info_manager._containers_info:
            update_apps_card(container['name'], container_list, page, get_settings_func)
        
        page.update()
    except Exception as e:
        show_status(page, f"起動エラー: {e}")
        page.update()

def stop_container(container, page, container_list, get_settings_func):
    """コンテナを停止する
    
    Args:
        container (Dict[str, Any]): コンテナ情報
        page (ft.Page): ページオブジェクト
        container_list (ft.Column): コンテナリスト
        get_settings_func (function): 設定取得関数
    """
    try:
        show_status(page, f"コンテナ {container['name']} を停止中...")

        # サービス名を抽出
        service_name = extract_service_name(container['name'], docker_compose_dir)
        if not service_name:
            raise ValueError("サービス名の抽出に失敗しました")

        subprocess.check_call(['docker-compose', 'stop', service_name], cwd=docker_compose_dir)
        
        # コンテナ情報を再取得
        container_info_manager.get_container_info(docker_compose_dir, page)
        
        # 更新されたコンテナ情報を使用してカードを更新
        if container['name'] in container_info_manager._containers_info:
            update_apps_card(container['name'], container_list, page, get_settings_func)
        
        show_status(page, f"コンテナ {container['name']} を停止しました。")
        page.update()
    except Exception as e:
        show_status(page, f"停止エラー: {e}")
        page.update()

def on_control_button_click(e, container, page, container_list, get_settings_func):
    """コンテナの起動/停止ボタンがクリックされたときの処理
    
    Args:
        e: イベントオブジェクト
        container (Dict[str, Any]): コンテナ情報
        page (ft.Page): ページオブジェクト
        container_list (ft.Column): コンテナリスト
        get_settings_func (function): 設定取得関数
    """
    button = e.control
    current_icon = button.icon
    
    print(f"現在のアイコン: {current_icon}")
    print(f"コンテナの状態: {container['state']}")
    print(f"コンテナの情報: {container}")
    
    if current_icon == ft.Icons.PLAY_CIRCLE:
        start_container(container, page, container_list, get_settings_func)
    else:
        stop_container(container, page, container_list, get_settings_func)

def create_apps_card(app_type: str, data: Dict[str, Any], page: ft.Page, container_list: ft.Column, get_settings_func):
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

def update_apps_card(container_name: str, container_list: ft.Column, page: ft.Page, get_settings_func):
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
            if container_name not in container_info_manager._containers_info:
                return
            container = container_info_manager._containers_info[container_name]
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
                current_state = get_app_status(app_name, desktop_processes)
                control_elements.append(
                    ft.IconButton(
                        icon=ft.Icons.STOP if current_state == "running" else ft.Icons.PLAY_ARROW,
                        tooltip="起動/停止",
                        on_click=lambda e, name=app_name, info=app_info, btn=None: 
                            on_app_control(e, name, info, e.control, page, desktop_processes, docker_compose_dir)
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
                            on_open_browser_click(e, name, port, container_info_manager._containers_info),
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
                                                        show_data_path_dialog(e, page, container_name, a, d, container_list)
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
            page.overlay.remove(dialog)
            page.update()

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

def show_data_path_dialog(e, page, container_name: str, app_name: str, data_root: str, container_list: ft.Column):
    """データパス設定ダイアログを表示する"""
    try:
        def on_dialog_result(e: ft.FilePickerResultEvent):
            if e.path:
                # 選択されたディレクトリ名を取得
                selected_dir_name = Path(e.path).name
                # 選択されたディレクトリ名が対象と異なる場合は警告
                if selected_dir_name != data_root:
                    show_error_dialog(
                        page,
                        "警告",
                        f"選択されたディレクトリ名 '{selected_dir_name}' が\n"
                        f"対象のディレクトリ名 '{data_root}' と異なります。"
                    )
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
        show_error_dialog(
            page,
            "エラー",
            f"データパス設定中にエラーが発生しました:\n{str(e)}"
        )

def on_container_dialog_result(e: ft.FilePickerResultEvent, page: ft.Page, container_list: ft.Column):
    """ビルドコンテキストが選択されたときの処理"""
    global docker_compose_dir
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

def refresh_container_status(page, container_list):
    global docker_compose_dir
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
            containers = container_info_manager.get_container_info(docker_compose_dir, page)

            if containers:
                for container in containers:
                    container_card = create_apps_card("container", container, page, container_list, get_container_settings)
                    container_list.controls.append(container_card)
                    update_apps_card(container['name'], container_list, page, get_container_settings)

        show_status(page, "情報を更新しました。")
        page.update()

    except Exception as e:
        show_error_dialog(page, "エラー", f"情報の更新中にエラーが発生しました: {e}")