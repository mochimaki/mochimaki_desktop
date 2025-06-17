"""
UIコンポーネントに関する関数を提供するモジュール
"""
import flet as ft
from pathlib import Path
from ..container_utils import extract_service_name

def get_container_control_icon(state, container_data=None):
    """コンテナの状態に応じたコントロールアイコンを取得する
    
    Args:
        state (str): コンテナの状態
        container_data: コンテナ情報の辞書（オプション）
        
    Returns:
        str: アイコン名
    """
    if state.lower() in ["starting", "起動処理中"]:
        return ft.Icons.HOURGLASS_EMPTY
    if state.lower() == "running":
        if container_data and 'docker_compose_dir' in container_data:
            service_name = extract_service_name(container_data['name'], container_data['docker_compose_dir'])
            if service_name:
                signal_dir = Path(container_data['docker_compose_dir']) / 'signal' / service_name
                if signal_dir.exists():
                    for signal_file in signal_dir.glob('*_startup_signal.txt'):
                        if signal_file.exists():
                            return ft.Icons.STOP_CIRCLE
                return ft.Icons.HOURGLASS_EMPTY  # 起動処理中
        return ft.Icons.HOURGLASS_EMPTY  # 起動処理中
    elif state.lower() in ["exited", "not created", ""]:  # 停止中や未生成の状態を追加
        return ft.Icons.PLAY_CIRCLE
    else:
        return ft.Icons.PLAY_CIRCLE  # デフォルトは起動アイコン

def set_card_color(card, state):
    """カードの色を設定する
    
    Args:
        card: カードオブジェクト
        state (str): コンテナの状態
    """
    if state == "desktop":
        color = ft.Colors.BLUE_400  # 青色（デスクトップ）
    elif state.lower() == "running":
        color = ft.Colors.GREEN_400  # 明るい緑（起動中）
    elif state.lower() in ["exited", "starting"]:  # starting状態を追加
        color = ft.Colors.GREEN_900  # 暗い緑（停止または起動中）
    else:
        color = ft.Colors.GREY_700  # 灰色（存在しないまたはその他の状態）
    
    # Containerの背景色を設定する代わりに、borderを設定
    card.content.bgcolor = ft.Colors.TRANSPARENT  # 背景を透明に
    card.content.border = ft.border.all(2, color)  # 輪郭線を設定
    card.content.border_radius = ft.border_radius.all(10)  # 角の丸みを追加 