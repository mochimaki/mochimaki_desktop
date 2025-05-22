import flet as ft
from utils import (
    on_container_dialog_result,
    refresh_container_status
)

# グローバル変数の宣言
global docker_compose_dir
docker_compose_dir = None
global containers_info
containers_info = {}
global snack_bar

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