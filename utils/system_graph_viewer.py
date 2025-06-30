import flet as ft
import json
import os
import traceback
import asyncio
from pathlib import Path

class SystemGraphViewer:
    def __init__(self):
        self.project_info = None

    def load_project_info(self, docker_compose_dir: Path):
        """docker_compose_dirからproject_info.jsonを読み込む"""
        try:
            project_info_path = docker_compose_dir / "project_info.json"
            with open(project_info_path, 'r', encoding='utf-8') as f:
                self.project_info = json.load(f)
            return True
        except Exception as e:
            print(f"プロジェクト情報の読み込みエラー: {e}")
            return False

    def _generate_mermaid_string(self, title: str, graph_type: str):
        node_list = []
        edge_list = []
        node_id_map = {}
        node_counter = 0

        def add_node(label, ntype):
            nonlocal node_counter
            key = (label, ntype)
            if key not in node_id_map:
                node_id = f"N{node_counter}"
                node_id_map[key] = node_id
                node_list.append((node_id, label, ntype))
                node_counter += 1
            return node_id_map[key]

        if graph_type == "unified":
            # 統合されたシステム構成図
            # Host Machine Apps
            host_apps = self.project_info.get("desktop_apps", {}).get("host_machine", {}).get("apps", {})
            if host_apps:
                host_section_id = add_node("Host Machine", "section")
                
                for app_name, app_info in host_apps.items():
                    app_id = add_node(f"App: {app_name}", "host_app")
                    edge_list.append((host_section_id, app_id))
                    if "data_roots" in app_info:
                        for data_root in app_info["data_roots"]:
                            data_id = add_node(f"Data: {data_root}", "data")
                            edge_list.append((app_id, data_id))
                    if "devices" in app_info:
                        for device_name, device_info in app_info["devices"].items():
                            if "target" in device_info:
                                for target in device_info["target"]:
                                    device_label = f"Device: {device_name} (Target: {target})"
                                    dev_id = add_node(device_label, "device")
                                    edge_list.append((app_id, dev_id))
                            else:
                                dev_id = add_node(f"Device: {device_name}", "device")
                                edge_list.append((app_id, dev_id))
            
            # Services
            services = self.project_info.get("services", {})
            if services:
                services_section_id = add_node("Docker", "docker_section")
                
                for service_name, service_info in services.items():
                    container_label = f"Container: {service_name}"
                    if "image" in service_info:
                        container_label += f" (Image: {service_info['image']})"
                    cont_id = add_node(container_label, "container")
                    edge_list.append((services_section_id, cont_id))
                    
                    if "apps" in service_info:
                        for app_name, app_info in service_info["apps"].items():
                            app_label = f"App: {app_name}"
                            if "container_port" in app_info:
                                app_label += f" (Port: {app_info['container_port']})"
                            app_id = add_node(app_label, "app")
                            edge_list.append((cont_id, app_id))
                            
                            if "data_roots" in app_info:
                                for data_root in app_info["data_roots"]:
                                    data_id = add_node(f"Data: {data_root}", "data")
                                    edge_list.append((app_id, data_id))
                            if "devices" in app_info:
                                for device_name, device_info in app_info["devices"].items():
                                    if "target" in device_info:
                                        for target in device_info["target"]:
                                            device_label = f"Device: {device_name} (Target: {target})"
                                            dev_id = add_node(device_label, "device")
                                            edge_list.append((app_id, dev_id))
                                    else:
                                        dev_id = add_node(f"Device: {device_name}", "device")
                                        edge_list.append((app_id, dev_id))
        
        # Mermaid定義生成
        lines = ["%%{init: {'theme': 'dark'}}%%"]
        lines.append("graph TD")
        for node_id, label, ntype in node_list:
            lines.append(f'    {node_id}["{label}"]')
            lines.append(f'    class {node_id} {ntype};')
        for src, dst in edge_list:
            lines.append(f'    {src} --> {dst}')
        # classDefでスタイル共通化
        lines.append('    classDef host fill:#2d3748,stroke:#e2e8f0,stroke-width:2px,color:#ffffff;')
        lines.append('    classDef section fill:#38a169,stroke:#e2e8f0,stroke-width:3px,color:#ffffff;')
        lines.append('    classDef docker_section fill:#3182ce,stroke:#e2e8f0,stroke-width:1px,color:#ffffff;')
        lines.append('    classDef app fill:#805ad5,stroke:#e2e8f0,stroke-width:1px,color:#ffffff;')
        lines.append('    classDef host_app fill:#805ad5,stroke:#e2e8f0,stroke-width:3px,color:#ffffff;')
        lines.append('    classDef device fill:#d69e2e,stroke:#e2e8f0,stroke-width:1px,color:#ffffff;')
        lines.append('    classDef container fill:#38a169,stroke:#e2e8f0,stroke-width:1px,color:#ffffff;')
        lines.append('    classDef data fill:#2f855a,stroke:#e2e8f0,stroke-width:1px,color:#ffffff;')
        mermaid_body = "\n".join(lines)
        return mermaid_body, len(node_list), len(edge_list)

    def generate_system_graph(self, docker_compose_dir: Path, output_path: str = "output_mermaid.txt"):
        """システム構成グラフを生成してファイルに出力する"""
        try:
            if not self.load_project_info(docker_compose_dir):
                return False, "プロジェクト情報の読み込みに失敗しました"

            unified_md, unified_nodes, unified_edges = self._generate_mermaid_string("System Configuration", "unified")

            # ファイル出力（docker_compose_dirと同じ場所に出力）
            output_file_path = docker_compose_dir / output_path
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(unified_md)

            return True, f"システム構成グラフを {output_file_path} に出力しました。ノード: {unified_nodes}, エッジ: {unified_edges}"
        except Exception as e:
            tb = traceback.format_exc()
            return False, f"システム構成グラフの生成に失敗しました: {e}\n{tb}"

async def main(page: ft.Page):
    page.title = "システム構成グラフビューアー"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1000
    page.window_height = 600
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#F5F5F5"
    page.scroll = ft.ScrollMode.ADAPTIVE

    stats_text = ft.Text("統計情報: 計算中...", size=12, color="gray", italic=True)
    info_text = ft.Text("統合システム構成図を output_mermaid.txt に出力しました。ファイルを開いて https://mermaid.live/ などのWebエディタに貼り付けて可視化してください。", color="blue")

    page.add(
        ft.Column(
            controls=[
                ft.Text("システム構成グラフビューアー", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),
                info_text,
                ft.Row([stats_text]),
                ft.Divider(height=10),
                ft.Row(
                    controls=[
                        ft.Column([ft.Text("統合システム構成図", size=16), ft.Text("output_mermaid.txt に出力済み", color="blue")], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START
                ),
            ],
            expand=True
        )
    )

    try:
        viewer = SystemGraphViewer()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_info_path = os.path.join(script_dir, "..", "project_info.json")

        if not viewer.load_project_info(project_info_path):
            raise FileNotFoundError(f"project_info.jsonの読み込みに失敗しました: {project_info_path}")

        loop = asyncio.get_running_loop()
        
        unified_md, unified_nodes, unified_edges = await loop.run_in_executor(None, viewer._generate_mermaid_string, "System Configuration", "unified")

        # ファイル出力
        with open("output_mermaid.txt", "w", encoding="utf-8") as f:
            f.write(unified_md)

        stats_text.value = f"ノード: {unified_nodes}  |  エッジ: {unified_edges}"
        stats_text.italic = False
        # 正常時はawait page.update_async()を呼ばない
        return
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        page.controls.clear()
        page.add(ft.Text(f"致命的なエラーが発生しました:\n{tb}", font_family="monospace"))
        await page.update_async()

def auto_generate_mermaid_file():
    """システム構成のMermaidファイルを自動生成する"""
    # docker_compose_dirはui_utils.pyで定義されているグローバル変数
    # この関数はui_utils.pyから呼び出されることを想定
    try:
        # ui_utils.pyのdocker_compose_dirを参照
        from .ui_utils import docker_compose_dir
        
        # docker_compose_dirをPathオブジェクトに変換
        docker_compose_path = Path(docker_compose_dir) if docker_compose_dir else None
        
        if docker_compose_path and docker_compose_path.exists():
            viewer = SystemGraphViewer()
            success, message = viewer.generate_system_graph(docker_compose_path)
            if success:
                print(f"Mermaidファイル自動生成: {message}")
                
                # Mermaidコンテナに通知を送信
                notify_mermaid_container(docker_compose_path)
            else:
                print(f"Mermaidファイル自動生成エラー: {message}")
    except Exception as e:
        print(f"Mermaidファイル自動生成でエラーが発生: {e}")

def notify_mermaid_container(docker_compose_path: Path):
    """Mermaidコンテナにシステムグラフの更新を通知する"""
    try:
        from .mermaid_container_manager import mermaid_container_manager
        
        # output_mermaid.txtの内容を読み込み
        mermaid_file_path = docker_compose_path / "output_mermaid.txt"
        if mermaid_file_path.exists():
            with open(mermaid_file_path, 'r', encoding='utf-8') as f:
                mermaid_content = f.read()
            
            # Mermaidコンテナに更新を送信
            # ページオブジェクトがないため、エラーハンドリングは最小限に
            try:
                mermaid_container_manager.update_graph(
                    mermaid_content, 
                    str(mermaid_file_path), 
                    None  # ページオブジェクトなし
                )
                print("Mermaidコンテナにシステムグラフの更新を通知しました")
            except Exception as e:
                print(f"Mermaidコンテナへの通知に失敗: {e}")
        else:
            print("output_mermaid.txtが見つかりません")
            
    except Exception as e:
        print(f"Mermaidコンテナ通知でエラーが発生: {e}")

if __name__ == "__main__":
    ft.app(target=main) 