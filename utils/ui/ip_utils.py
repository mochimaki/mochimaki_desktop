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