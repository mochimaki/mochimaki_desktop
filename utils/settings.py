import os
import json
from .dialogs import show_error_dialog
from pathlib import Path

def get_container_settings(docker_compose_dir, page):
    """project_info.jsonから設定を読み込む"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        if not project_info_path.exists():
            raise FileNotFoundError(f"project_info.jsonが見つかりません: {project_info_path}")
            
        if project_info_path.stat().st_size == 0:
            raise ValueError(f"project_info.jsonが空です: {project_info_path}")

        with project_info_path.open('r') as f:
            return json.load(f)
            
    except FileNotFoundError as e:
        show_error_dialog(page, "ファイルが見つかりません", str(e))
        return None
    except ValueError as e:
        show_error_dialog(page, "ファイルエラー", str(e))
        return None
    except json.JSONDecodeError as e:
        show_error_dialog(page, "JSONエラー", f"project_info.jsonの解析エラー: {str(e)}")
        return None
    except Exception as e:
        show_error_dialog(page, "エラー", f"予期せぬエラーが発生しました: {str(e)}")
        return None
