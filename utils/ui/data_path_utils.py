"""
データパスに関する関数を提供するモジュール
"""
from pathlib import Path
from typing import Dict, Any, List

def get_required_data_roots(app_info: Dict[str, Any], docker_compose_dir: str) -> List[str]:
    """アプリケーションに必要なデータルートのリストを取得する
    
    Args:
        app_info (Dict[str, Any]): アプリケーション情報
        docker_compose_dir (str): docker-compose.ymlが存在するディレクトリのパス
        
    Returns:
        List[str]: データルートのリスト
    """
    data_roots = []
    for data_root in app_info.get('data_roots', []):
        if isinstance(data_root, str):
            data_roots.append(Path(data_root).name)
    return data_roots 