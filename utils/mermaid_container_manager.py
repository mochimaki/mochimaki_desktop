"""
Mermaidコンテナの管理機能を提供するモジュール
"""
import subprocess
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import flet as ft
from .dialogs import show_error_dialog, show_status

class MermaidContainerManager:
    """Mermaidコンテナの管理を行うクラス"""
    
    def __init__(self):
        self.container_name = "mochimaki-mermaid-system-graph-viewer"
        self.image_name = "mochimaki-mermaid-system-graph-viewer"
        self.repo_url = "https://github.com/mochimaki/mermaid_viewer.git"
        self.repo_dir = Path.home() / "mermaid_viewer"
        self.api_base_url = "http://localhost"
        
    def ensure_container_running(self, page: ft.Page) -> bool:
        """Mermaidコンテナが起動していることを確認し、必要に応じて起動する"""
        try:
            # コンテナが存在するかチェック
            if not self._container_exists():
                show_status(page, "Mermaidコンテナが存在しません。ビルドを開始します...")
                if not self._build_container(page):
                    return False
            
            # コンテナが起動しているかチェック
            if not self._container_is_running():
                show_status(page, "Mermaidコンテナを起動中...")
                if not self._start_container(page):
                    return False
            
            # コンテナのヘルスチェック
            if not self._wait_for_container_ready(page):
                return False
                
            show_status(page, "Mermaidコンテナが正常に起動しました")
            return True
            
        except Exception as e:
            show_error_dialog(page, "エラー", f"Mermaidコンテナの起動に失敗しました: {e}")
            return False
    
    def _container_exists(self) -> bool:
        """コンテナが存在するかチェック"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                capture_output=True, text=True, check=True
            )
            return self.container_name in result.stdout.strip()
        except subprocess.CalledProcessError:
            return False
    
    def _container_is_running(self) -> bool:
        """コンテナが起動しているかチェック"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                capture_output=True, text=True, check=True
            )
            return self.container_name in result.stdout.strip()
        except subprocess.CalledProcessError:
            return False
    
    def _build_container(self, page: ft.Page) -> bool:
        """コンテナをビルドする"""
        try:
            # リポジトリをクローン
            if not self.repo_dir.exists():
                show_status(page, "Mermaidリポジトリをクローン中...")
                subprocess.run(['git', 'clone', self.repo_url, str(self.repo_dir)], check=True)
            
            # イメージが存在するかチェック
            result = subprocess.run(
                ['docker', 'images', '--format', '{{.Repository}}', self.image_name],
                capture_output=True, text=True
            )
            
            if self.image_name not in result.stdout:
                show_status(page, "Mermaidイメージをビルド中...")
                subprocess.run(
                    ['docker', 'build', '-t', self.image_name, 'mermaid-container/'],
                    cwd=self.repo_dir, check=True
                )
            
            # コンテナを作成（dynamic port assignment）
            show_status(page, "Mermaidコンテナを作成中...")
            subprocess.run([
                'docker', 'run', '-d',
                '--name', self.container_name,
                '-p', '8080',  # dynamic port assignment
                self.image_name
            ], check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            show_error_dialog(page, "ビルドエラー", f"Mermaidコンテナのビルドに失敗しました: {e}")
            return False
    
    def _start_container(self, page: ft.Page) -> bool:
        """コンテナを起動する"""
        try:
            subprocess.run(['docker', 'start', self.container_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            show_error_dialog(page, "起動エラー", f"Mermaidコンテナの起動に失敗しました: {e}")
            return False
    
    def _wait_for_container_ready(self, page: ft.Page, timeout: int = 30) -> bool:
        """コンテナが準備完了するまで待機"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # ヘルスチェックAPIを呼び出し
                response = requests.get(f"{self.api_base_url}:{self._get_container_port()}/api/health", timeout=5)
                if response.status_code == 200 and response.json().get('status') == 'healthy':
                    return True
            except (requests.RequestException, json.JSONDecodeError):
                pass
            time.sleep(2)
        
        show_error_dialog(page, "タイムアウト", "Mermaidコンテナの準備がタイムアウトしました")
        return False
    
    def _get_container_port(self) -> int:
        """コンテナのホストポートを取得"""
        try:
            result = subprocess.run([
                'docker', 'port', self.container_name, '8080/tcp'
            ], capture_output=True, text=True, check=True)
            
            # 出力例: "0.0.0.0:32768"
            port_str = result.stdout.strip().split(':')[-1]
            return int(port_str)
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return 8080  # デフォルトポート
    
    def update_graph(self, mermaid_content: str, file_path: str, page: ft.Page) -> bool:
        """システムグラフを更新する"""
        try:
            port = self._get_container_port()
            url = f"{self.api_base_url}:{port}/api/update"
            
            payload = {
                "mermaid_content": mermaid_content,
                "file_path": file_path,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    if page:
                        show_status(page, "システムグラフを更新しました")
                    else:
                        print("システムグラフを更新しました")
                    return True
                else:
                    error_msg = f"グラフの更新に失敗しました: {result.get('message', '不明なエラー')}"
                    if page:
                        show_error_dialog(page, "更新エラー", error_msg)
                    else:
                        print(f"更新エラー: {error_msg}")
                    return False
            else:
                error_msg = f"APIリクエストに失敗しました: {response.status_code}"
                if page:
                    show_error_dialog(page, "APIエラー", error_msg)
                else:
                    print(f"APIエラー: {error_msg}")
                return False
                
        except requests.RequestException as e:
            error_msg = f"Mermaidコンテナとの通信に失敗しました: {e}"
            if page:
                show_error_dialog(page, "通信エラー", error_msg)
            else:
                print(f"通信エラー: {error_msg}")
            return False
    
    def open_graph_viewer(self, page: ft.Page) -> bool:
        """システムグラフビューアーをブラウザで開く"""
        try:
            import webbrowser
            port = self._get_container_port()
            url = f"{self.api_base_url}:{port}"
            webbrowser.open(url)
            show_status(page, "システムグラフビューアーを開きました")
            return True
        except Exception as e:
            show_error_dialog(page, "ブラウザエラー", f"ブラウザの起動に失敗しました: {e}")
            return False

# シングルトンインスタンス
mermaid_container_manager = MermaidContainerManager() 