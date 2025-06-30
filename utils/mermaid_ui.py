"""
Mermaid関連のUI機能を提供するモジュール
"""
import flet as ft
import threading
from .mermaid_container_manager import mermaid_container_manager
from .dialogs import show_error_dialog, show_status

def initialize_mermaid_container(page: ft.Page):
    """Mochimaki起動時にmermaidコンテナを初期化する"""
    try:
        # バックグラウンドでmermaidコンテナを起動
        def start_mermaid_container():
            mermaid_container_manager.ensure_container_running(page)
        
        # 非同期でコンテナ起動を開始
        thread = threading.Thread(target=start_mermaid_container, daemon=True)
        thread.start()
        
    except Exception as e:
        print(f"Mermaidコンテナの初期化でエラーが発生: {e}")

def on_system_graph_button_click(page: ft.Page):
    """システムグラフボタンがクリックされたときの処理"""
    try:
        # mermaidコンテナが起動していることを確認
        if mermaid_container_manager.ensure_container_running(page):
            # システムグラフビューアーをブラウザで開く
            mermaid_container_manager.open_graph_viewer(page)
        else:
            show_error_dialog(page, "エラー", "Mermaidコンテナの起動に失敗しました")
    except Exception as e:
        show_error_dialog(page, "エラー", f"システムグラフの表示に失敗しました: {e}") 