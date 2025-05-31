"""
IP設定に関する関数を提供するモジュール
"""
import flet as ft
from ..ip_settings import validate_ip_selections
from ..container_utils import extract_service_name
from ..dialogs import show_status, show_error_dialog
from ..ip_settings import update_settings_json
from pathlib import Path
import re

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

def show_ip_setting_dialog(container, page, container_list, get_settings_func):
    """IP設定ダイアログを表示する
    
    Args:
        container (Dict[str, Any]): コンテナ情報
        page (ft.Page): ページオブジェクト
        container_list (ft.Column): コンテナリスト
        get_settings_func (function): 設定取得関数
    """
    try:
        # サービス名を抽出
        service_name = extract_service_name(container['name'], Path(__file__).parent.parent.parent / "docker-compose")
        if not service_name:
            raise ValueError("サービス名の抽出に失敗しました")

        # 設定を取得
        settings = get_settings_func(Path(__file__).parent.parent.parent / "docker-compose", page)
        if not settings:
            return

        # コンテナの設定を取得
        container_settings = next((s for s in settings['services'] if s['name'] == service_name), None)
        if not container_settings:
            raise ValueError(f"コンテナ {service_name} の設定が見つかりません")

        # 現在のIP設定を取得
        current_ip = container_settings.get('ip', '')
        current_netmask = container_settings.get('netmask', '')
        current_gateway = container_settings.get('gateway', '')

        # 入力フィールド
        ip_field = ft.TextField(
            label="IPアドレス",
            value=current_ip,
            width=300
        )
        netmask_field = ft.TextField(
            label="サブネットマスク",
            value=current_netmask,
            width=300
        )
        gateway_field = ft.TextField(
            label="デフォルトゲートウェイ",
            value=current_gateway,
            width=300
        )

        def validate_ip(ip: str) -> bool:
            """IPアドレスの形式を検証する"""
            pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(pattern, ip):
                return False
            return all(0 <= int(x) <= 255 for x in ip.split('.'))

        def on_save(e):
            """保存ボタンのクリックハンドラ"""
            try:
                # 入力値の検証
                if not validate_ip(ip_field.value):
                    raise ValueError("IPアドレスの形式が正しくありません")
                if not validate_ip(netmask_field.value):
                    raise ValueError("サブネットマスクの形式が正しくありません")
                if gateway_field.value and not validate_ip(gateway_field.value):
                    raise ValueError("デフォルトゲートウェイの形式が正しくありません")

                # 設定を更新
                container_settings['ip'] = ip_field.value
                container_settings['netmask'] = netmask_field.value
                container_settings['gateway'] = gateway_field.value

                # 設定ファイルを更新
                update_settings_json(settings, Path(__file__).parent.parent.parent / "docker-compose", page)

                # カードを更新
                from ..ui_utils import update_apps_card
                update_apps_card(container['name'], container_list, page, get_settings_func)

                # ダイアログを閉じる
                page.dialog.open = False
                page.update()

                show_status(page, "IP設定を更新しました。")
            except Exception as e:
                show_error_dialog(page, "エラー", str(e))

        # ダイアログの作成
        dialog = ft.AlertDialog(
            title=ft.Text(f"IP設定 - {container['name']}"),
            content=ft.Column([
                ip_field,
                netmask_field,
                gateway_field
            ], spacing=10),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: setattr(page.dialog, 'open', False)),
                ft.TextButton("保存", on_click=on_save)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        # ダイアログを表示
        page.dialog = dialog
        dialog.open = True
        page.update()

    except Exception as e:
        show_error_dialog(page, "エラー", str(e)) 