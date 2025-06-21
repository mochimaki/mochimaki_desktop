"""
IP設定に関する関数を提供するモジュール
"""
import flet as ft
from ..ip_settings import validate_ip_selections

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