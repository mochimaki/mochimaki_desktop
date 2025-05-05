import os
import json
from .dialogs import show_error_dialog

def get_container_settings(docker_compose_dir, page):
    """project_info.jsonから設定を読み込む"""
    project_info_path = os.path.join(docker_compose_dir, 'project_info.json')
    try:
        if not os.path.exists(project_info_path):
            raise FileNotFoundError(f"project_info.jsonが見つかりません: {project_info_path}")
            
        if os.path.getsize(project_info_path) == 0:
            raise ValueError(f"project_info.jsonが空です: {project_info_path}")

        with open(project_info_path, 'r') as f:
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
