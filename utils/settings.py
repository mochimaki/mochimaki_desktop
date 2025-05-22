import json
import subprocess
from .dialogs import show_error_dialog, show_status
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

def clone_repositories(project_info: dict, docker_compose_dir: str, page) -> bool:
    """リポジトリをクローンする"""
    if 'repositories' not in project_info:
        return True

    programs_dir = Path(docker_compose_dir) / 'programs'
    programs_dir.mkdir(exist_ok=True)
    
    for repo_name, repo_info in project_info['repositories'].items():
        repo_dir = programs_dir / repo_name
        if not repo_dir.exists():
            try:
                show_status(page, f"{repo_name}をクローン中...")
                subprocess.run(
                    ['git', 'clone', '-b', repo_info['branch'], repo_info['url'], str(repo_dir)],
                    check=True
                )
                show_status(page, f"{repo_name}をクローンしました")
            except subprocess.CalledProcessError as e:
                show_error_dialog(page, "エラー", f"{repo_name}のクローンに失敗しました: {str(e)}")
                return False
    return True

def clone_dockerfiles(project_info: dict, docker_compose_dir: str, page) -> bool:
    """Dockerfileをクローンする"""
    if 'dockerfiles' not in project_info:
        return True

    dockerfiles_dir = Path(docker_compose_dir) / 'dockerfiles'
    dockerfiles_dir.mkdir(exist_ok=True)
    
    for dockerfile_name, dockerfile_info in project_info['dockerfiles'].items():
        dockerfile_dir = dockerfiles_dir / dockerfile_name
        dockerfile_dir.mkdir(exist_ok=True)
        dockerfile_path = dockerfile_dir / 'Dockerfile'
        if not dockerfile_path.exists():
            try:
                show_status(page, f"{dockerfile_name}のDockerfileをクローン中...")
                subprocess.run(
                    ['git', 'clone', '-b', dockerfile_info['branch'], dockerfile_info['url'], str(dockerfile_dir)],
                    check=True
                )
                show_status(page, f"{dockerfile_name}のDockerfileをクローンしました")
            except subprocess.CalledProcessError as e:
                show_error_dialog(page, "エラー", f"{dockerfile_name}のDockerfileのクローンに失敗しました: {str(e)}")
                return False
    return True
