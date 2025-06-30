import flet as ft
from utils import (
    on_container_dialog_result,
    refresh_container_status,
    initialize_mermaid_container,
    on_system_graph_button_click
)

# グローバル変数の宣言
global docker_compose_dir
docker_compose_dir = None
global snack_bar

def main(page: ft.Page):
    page.title = "Mochimaki"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 20

    # Mochimaki起動時にmermaidコンテナを初期化
    initialize_mermaid_container(page)

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

    system_graph_button = ft.ElevatedButton(
        "システムグラフを表示",
        icon=ft.Icons.ACCOUNT_TREE,
        on_click=lambda _: on_system_graph_button_click(page)
    )

    # ボタンを横に並べるためのRowを作成
    buttons_row = ft.Row(
        [select_container_button, refresh_button, system_graph_button],
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