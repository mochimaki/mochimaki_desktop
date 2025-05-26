import json
import flet as ft
from .dialogs import show_error_dialog
from pathlib import Path

def is_valid_ipv4(ip: str) -> bool:
    """IPv4アドレスの形式が正しいかチェックする"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        return all(0 <= int(part) <= 255 for part in parts)
    except (AttributeError, TypeError, ValueError):
        return False

def ip_to_int(ip: str) -> int:
    """IPアドレスを整数値に変換する"""
    try:
        parts = ip.split('.')
        return sum(int(part) << (24 - 8 * i) for i, part in enumerate(parts))
    except:
        return 0

def update_settings_json(docker_compose_dir, new_targets, service_name, app_name, device_type, page: ft.Page):
    """特定のアプリケーションのtargetを更新する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        if service_name == "host_machine":
            service = settings['desktop_apps']['host_machine']          
        elif service_name in settings['services']:
            service = settings['services'][service_name]

        if 'apps' in service and app_name in service['apps']:
            app = service['apps'][app_name]
            if 'devices' in app and device_type in app['devices']:
                # targetを新しいIPアドレスのリストで更新
                app['devices'][device_type]['target'] = new_targets
                
                # 更新した設定を保存
                with project_info_path.open('w') as f:
                    json.dump(settings, f, indent=2)
                
                # container_infoディレクトリの更新
                from .container_utils import parse_project_info
                parse_project_info(docker_compose_dir)
                
                print(f"{app_name}の{device_type}のtargetを更新しました: {new_targets}")
                return True
    except Exception as e:
        show_error_dialog(page, "設定更新エラー", f"project_info.json更新エラー: {e}")
    return False

def get_ip_addresses(docker_compose_dir, service_name, app_name, device_type, page: ft.Page):
    """指定されたデバイスで利用可能なIPアドレスのリストを取得する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        if (service_name in settings['services'] and 
            app_name in settings['services'][service_name]['apps']):
            app_info = settings['services'][service_name]['apps'][app_name]
            if ('devices' in app_info and 
                device_type in app_info['devices'] and 
                'ip_addr' in app_info['devices'][device_type]):
                return app_info['devices'][device_type]['ip_addr']
    except Exception as e:
        show_error_dialog(page, "設定読み込みエラー", f"IPアドレスリストの取得に失敗しました: {e}")
    return []

def get_current_targets(docker_compose_dir, service_name, app_name, device_type, page: ft.Page):
    """指定されたデバイスの現在のターゲットIPアドレスのリストを取得する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        if (service_name in settings['services'] and 
            app_name in settings['services'][service_name]['apps']):
            app_info = settings['services'][service_name]['apps'][app_name]
            if ('devices' in app_info and 
                device_type in app_info['devices'] and 
                'target' in app_info['devices'][device_type]):
                return app_info['devices'][device_type]['target']
    except Exception as e:
        show_error_dialog(page, "設定読み込みエラー", f"現在のターゲットの取得に失敗しました: {e}")
    return []

def get_device_constraints(docker_compose_dir, service_name, app_name, device_type, page: ft.Page):
    """デバイスの接続数制限を取得する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        if (service_name in settings['services'] and 
            app_name in settings['services'][service_name]['apps']):
            app_info = settings['services'][service_name]['apps'][app_name]
            if ('devices' in app_info and 
                device_type in app_info['devices'] and 
                'num' in app_info['devices'][device_type]):
                num_constraint = app_info['devices'][device_type]['num']
                min_conn, max_conn_str, allow_duplicate_str = num_constraint.split(':')
                return {
                    'min_connections': int(min_conn),
                    'max_connections': int(max_conn_str) if max_conn_str else None,
                    'allow_duplicate': bool(int(allow_duplicate_str))
                }
    except Exception as e:
        show_error_dialog(page, "設定読み込みエラー", f"デバイス制約の取得に失敗しました: {e}")
    return None

def validate_ip_selections(selected_ips: list, min_connections: int, max_connections: int | None) -> tuple[list[str], set[str], dict[str, int]]:
    """選択されたIPアドレスの検証を行う
    
    Args:
        selected_ips (list): 選択されたIPアドレスのリスト
        min_connections (int): 最小接続数
        max_connections (int | None): 最大接続数（Noneの場合は制限なし）
    
    Returns:
        tuple[list[str], set[str], dict[str, int]]: 
            - エラーメッセージのリスト
            - 重複しているIPアドレスのセット
            - IPアドレスごとの出現回数の辞書
    """
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

def on_edit_ip_options(e, page: ft.Page, current_ip_addresses: list, build_context_path: str, device_type: str):
    """IPアドレスの選択肢を編集するダイアログを表示する"""
    # IPアドレスリストを管理するための状態変数
    ip_list = sorted(current_ip_addresses.copy(), key=ip_to_int)

    # エラーメッセージ用のテキスト
    error_text = ft.Text(
        value="",
        color=ft.Colors.RED_400,
        size=12,
        visible=False
    )

    # IPアドレスのリストを表示するColumn
    ip_list_column = ft.Column(spacing=10)

    def show_ip_validation_error(message):
        """エラーメッセージを表示し、適用ボタンを無効化"""
        error_text.value = message
        error_text.visible = True
        apply_button.disabled = True
        page.update()

    def clear_ip_validation_error():
        """エラーメッセージをクリアし、適用ボタンを有効化"""
        error_text.value = ""
        error_text.visible = False
        apply_button.disabled = False
        page.update()

    def validate_input(new_ip: str) -> tuple[bool, str]:
        """入力値を検証し、結果とエラーメッセージを返す"""
        if not new_ip:
            return False, "IPアドレスを入力してください。"
        
        if not is_valid_ipv4(new_ip):
            return False, "有効なIPv4アドレスを入力してください。"
        
        if new_ip in ip_list:
            return False, "このIPアドレスは既にリストに存在します。"
        
        return True, ""

    def update_ip_list():
        """IPアドレスリストの表示を更新する"""
        nonlocal ip_list, ip_list_column
        ip_list_column.controls.clear()
        # IPアドレスを数値に変換してソート
        sorted_ips = sorted(ip_list, key=ip_to_int)
        for ip in sorted_ips:
            ip_list_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(ip, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="削除",
                            on_click=lambda e, addr=ip: remove_ip_address(addr)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
        page.update()

    def toggle_input_visibility(show: bool):
        """入力フィールドとプラスボタンを切り替える"""
        if show:
            # テキストフィールドと追加・キャンセルボタンを表示
            input_container.content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.TextField(
                            hint_text="例: 192.168.1.100",
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CHECK,
                            tooltip="追加",
                            on_click=lambda e: add_ip_address(e)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip="キャンセル",
                            on_click=lambda e: toggle_input_visibility(False)
                        )
                    ],
                    spacing=10
                ),
                width=400,  # スクロール可能なリスト領域と同じ幅
                padding=10,
            )
        else:
            # プラスボタンを表示
            input_container.content = ft.IconButton(
                icon=ft.Icons.ADD,
                tooltip="新しいIPアドレスを追加",
                on_click=lambda e: toggle_input_visibility(True)
            )
            clear_ip_validation_error()  # 入力フィールドを閉じるときにエラー状態をクリア
        page.update()

    def remove_ip_address(ip: str):
        """IPアドレスをリストから削除する"""
        nonlocal ip_list
        if ip in ip_list:
            ip_list.remove(ip)
            update_ip_list()  # リストを更新

    def add_ip_address(e):
        """新しいIPアドレスをリストに追加する"""
        new_ip = input_container.content.content.controls[0].value.strip()
        
        is_valid, error_message = validate_input(new_ip)
        if not is_valid:
            show_ip_validation_error(error_message)  # エラー表示と適用ボタンの無効化
            return

        ip_list.append(new_ip)
        toggle_input_visibility(False)
        update_ip_list()
        clear_ip_validation_error()  # エラー状態をクリアし、適用ボタンを有効化

    def save_changes(device_type):
        """変更をproject_info.jsonに保存する"""
        nonlocal ip_list
        try:
            project_info_path = Path(build_context_path) / 'project_info.json'
            with project_info_path.open('r') as f:
                settings = json.load(f)

            # 指定されたデバイスのip_addrを更新（ソートして保存）
            sorted_ip_list = sorted(ip_list, key=ip_to_int)

            # デスクトップアプリの設定を更新
            if 'desktop_apps' in settings and 'host_machine' in settings['desktop_apps']:
                for app in settings['desktop_apps']['host_machine'].get('apps', {}).values():
                    if 'devices' in app and device_type in app['devices']:
                        app['devices'][device_type]['ip_addr'] = sorted_ip_list

            # コンテナアプリの設定を更新
            if 'services' in settings:
                for service in settings['services'].values():
                    for app in service.get('apps', {}).values():
                        if 'devices' in app and device_type in app['devices']:
                            app['devices'][device_type]['ip_addr'] = sorted_ip_list

            with project_info_path.open('w') as f:
                json.dump(settings, f, indent=2)

            # 設定を再パース
            from .container_utils import parse_project_info
            parse_project_info(build_context_path)
            return True
        except Exception as e:
            show_error_dialog(page, "保存エラー", f"設定の保存中にエラーが発生しました: {e}")
            return False

    def close_dialog(e):
        """ダイアログを閉じる"""
        dialog.open = False
        page.update()
        page.overlay.remove(dialog)

    def on_apply(e, device_type):
        """変更を適用してダイアログを閉じる"""
        if save_changes(device_type):  # 変更を保存
            close_dialog(e)

    # 入力用のコンテナを作成
    input_container = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="新しいIPアドレスを追加",
            on_click=lambda e: toggle_input_visibility(True)
        ),
        alignment=ft.alignment.center,
        padding=10,
    )

    # 適用ボタンを作成（初期状態は有効）
    apply_button = ft.TextButton("適用", on_click=lambda e: on_apply(e, device_type))

    # ダイアログを作成
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("IPアドレスの選択肢を編集"),
        content=ft.Column([
            error_text,  # エラーメッセージ用のテキスト
            # スクロール可能なリスト領域
            ft.Container(
                content=ft.Column([
                    ip_list_column,
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO
                ),
                width=400,
                height=300,
                border=ft.border.all(1, ft.Colors.GREY_400),
                border_radius=ft.border_radius.all(4),
            ),
            # 入力用のコンテナを追加
            input_container,
        ]),
        actions=[
            apply_button,
            ft.TextButton("キャンセル", on_click=close_dialog),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # 初期リストを表示
    update_ip_list()

    # ダイアログを表示
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
