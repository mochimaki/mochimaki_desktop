"""
コンテナ操作に関する関数を提供するモジュール
"""
from typing import Dict, Any

def get_container_status(container: Dict[str, Any]) -> str:
    """コンテナの状態を取得する
    
    Args:
        container (Dict[str, Any]): コンテナ情報
        
    Returns:
        str: コンテナの状態
    """
    state = container.get('state', '').lower()
    if state == "running":
        return "起動中"
    elif state == "exited":
        return "停止中"
    elif state == "not created":
        return "未生成"
    else:
        return state 