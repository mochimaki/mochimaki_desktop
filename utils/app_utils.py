import json
from pathlib import Path

def get_required_data_roots(app_info: dict, docker_compose_dir: str) -> list:
    """必要なデータルートを取得する
    
    Args:
        app_info (dict): アプリケーション情報
        docker_compose_dir (str): docker-compose.ymlが存在するディレクトリのパス
        
    Returns:
        list: 必要なデータルートのリスト
    """
    print("get_required_data_roots called with:", app_info)  # デバッグ出力
    main_path = Path(app_info['main'])
    if not main_path.is_absolute():
        main_path = Path(docker_compose_dir) / main_path
    print("main_path:", main_path)  # デバッグ出力

    program_name = main_path.stem
    print("program_name:", program_name)  # デバッグ出力
    
    if 'desktop_apps' in str(main_path):
        original_dir = main_path.parent
        if original_dir.is_symlink():
            original_dir = original_dir.resolve()
    else:
        original_dir = Path(docker_compose_dir) / 'programs' / program_name
    print("original_dir:", original_dir)  # デバッグ出力
    
    config_path = original_dir / 'app_config.json'
    print("config_path:", config_path)  # デバッグ出力
    
    try:
        with config_path.open('r', encoding='utf-8') as f:
            app_config = json.load(f)
            data_roots = app_config.get('data_roots', [])
            print("data_roots:", data_roots)  # デバッグ出力
            return data_roots
    except Exception as e:
        print(f"app_config.jsonの読み込みに失敗: {e}")
        print(f"探索したパス: {config_path}")
        return [] 