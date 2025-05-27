"""
アプリケーション関連のユーティリティ関数を提供するモジュール
"""
from pathlib import Path
import json

def update_container_info_in_project_info(docker_compose_dir, container_info):
    """project_info.jsonにコンテナIDとイメージ情報を反映する"""
    project_info_path = Path(docker_compose_dir) / 'project_info.json'
    try:
        with project_info_path.open('r') as f:
            settings = json.load(f)
        
        # servicesの各サービスに対してコンテナIDとイメージを更新
        if 'services' in settings:
            for service_name, service_info in settings['services'].items():
                # コンテナ名を構築（例：m2k-app03-fg_pg-1）
                project_name = Path(docker_compose_dir).name
                container_name = f"{project_name}-{service_name}-1"
                
                # 対応するコンテナ情報を探す
                for container in container_info:
                    if container['name'] == container_name:
                        # コンテナIDを更新
                        service_info['id'] = container['id']
                        # イメージを更新（存在する場合のみ）
                        if container.get('image'):
                            service_info['image'] = container['image']
                        break
        
        # 更新した設定を保存
        with project_info_path.open('w') as f:
            json.dump(settings, f, indent=2)
            
        print("コンテナIDとイメージ情報をproject_info.jsonに反映しました")
        
    except Exception as e:
        print(f"project_info.json更新エラー: {e}")
