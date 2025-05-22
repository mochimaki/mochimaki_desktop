"""
コンテナ操作に関する関数を提供するモジュール
"""
from typing import Dict, Any
import subprocess
import time

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

def wait_for_container(container_name, docker_compose_dir, timeout=60):
    """コンテナの起動を待機する
    
    Args:
        container_name (str): コンテナ名
        docker_compose_dir (str): docker-compose.ymlが存在するディレクトリのパス
        timeout (int): タイムアウト時間（秒）
        
    Returns:
        bool: コンテナが起動した場合はTrue、タイムアウトした場合はFalse
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
                capture_output=True,
                text=True,
                check=True,
                cwd=docker_compose_dir
            )
            if result.stdout.strip() == 'true':
                return True
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    return False 