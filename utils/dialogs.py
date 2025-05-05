import flet as ft

def show_error_dialog(page: ft.Page, title: str, message: str):
    """エラーダイアログを表示する"""
    def close_dialog(e):
        dialog.open = False
        page.update()
        page.overlay.remove(dialog)  # overlayからダイアログを削除

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.TextButton("OK", on_click=close_dialog),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
