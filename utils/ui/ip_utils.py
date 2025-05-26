"""
IP設定に関する関数を提供するモジュール
"""
import flet as ft

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