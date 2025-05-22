import json
from pathlib import Path
import re

def parse_project_info(build_context_path: str) -> None:
    """
    project_info.jsonをパースしてcontainer_infoディレクトリに階層構造で保存する
    
    Args:
        build_context_path: ビルドコンテキストのパス
    """
    try:
        # project_info.jsonを読み込む
        project_info_path = Path(build_context_path) / 'project_info.json'
        with project_info_path.open('r') as f:
            project_info = json.load(f)

        # container_infoディレクトリを作成
        container_info_dir = Path(build_context_path) / 'container_info'
        container_info_dir.mkdir(exist_ok=True)

        # サービスごとにcontainer_info.jsonとapp_info.jsonを作成
        for service_name, service_info in project_info['services'].items():
            # サービスディレクトリを作成
            service_dir = container_info_dir / service_name
            service_dir.mkdir(exist_ok=True)

            # container_info.jsonを作成
            container_info_path = service_dir / 'container_info.json'
            with container_info_path.open('w') as f:
                container_info = {
                    'name': service_name,
                    'image': service_info.get('image', ''),
                    'id': service_info.get('id', ''),
                    'Dockerfile': service_info.get('Dockerfile', ''),
                    'apps': service_info.get('apps', {})
                }
                json.dump(container_info, f, indent=2)

            # アプリケーションごとにapp_info.jsonを作成
            for app_name, app_info in service_info.get('apps', {}).items():
                # アプリケーションディレクトリを作成
                app_dir = service_dir / app_name
                app_dir.mkdir(exist_ok=True)

                # app_info.jsonを作成
                app_info_path = app_dir / 'app_info.json'
                with app_info_path.open('w') as f:
                    json.dump(app_info, f, indent=2)
    
    except FileNotFoundError:
        print(f"エラー: project_info.jsonが見つかりません: {project_info_path}")
    except json.JSONDecodeError:
        print(f"エラー: project_info.jsonの解析に失敗しました")
    except Exception as e:
        print(f"エラー: container_info生成中に予期せぬエラーが発生しました: {e}")

def extract_service_name(container_name: str, docker_compose_dir: str) -> str:
    """コンテナ名からサービス名を抽出する
    
    Args:
        container_name (str): コンテナ名（例：project-name-service-1）
        docker_compose_dir (str): docker-compose.ymlが存在するディレクトリのパス
        
    Returns:
        str: 抽出されたサービス名。失敗した場合はNone
        
    Example:
        >>> extract_service_name("my-project-web-1", "/path/to/project")
        'web'
    """
    try:
        # プロジェクト名を取得（ディレクトリ名）
        project_name = Path(docker_compose_dir).name
        
        # プロジェクト名のプレフィックスを確認
        if not container_name.startswith(f"{project_name}-"):
            raise ValueError(f"Invalid container name format: {container_name}")
            
        # プロジェクト名の部分を除去
        name_without_prefix = container_name[len(project_name)+1:]
        
        # 末尾の"-数字"を除去
        service_name = re.sub(r'-\d+$', '', name_without_prefix)
        
        return service_name
            
    except Exception as e:
        print(f"サービス名の抽出に失敗: {e}")
        return None