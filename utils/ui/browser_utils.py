"""
ブラウザ関連のユーティリティ関数を提供するモジュール
"""
import webbrowser

def on_open_browser_click(e, container_name, port, containers_info):
    """ブラウザを開くボタンがクリックされたときの処理"""
    if container_name in containers_info and containers_info[container_name]['ports']:
        ports = containers_info[container_name]['ports']
        if int(port) in ports:
            host_port = ports[int(port)]
            url = f"http://localhost:{host_port}"
            webbrowser.open(url) 