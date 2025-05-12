import flet as ft

# グローバル変数の宣言
snack_bar = None

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

def show_status(page: ft.Page, message: str):
    """ステータスメッセージをSnackBarで表示する"""
    global snack_bar
    if snack_bar is None:
        # 初回呼び出し時にSnackBarを作成
        snack_bar = ft.SnackBar(
            content=ft.Text(""),
            action="閉じる"
        )
        page.overlay.append(snack_bar)
    
    snack_bar.content.value = message
    snack_bar.open = True
    page.update()
