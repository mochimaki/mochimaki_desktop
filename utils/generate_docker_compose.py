import json
import yaml
import re
from typing import Dict, Any
from pathlib import Path
from yaml.dumper import SafeDumper

class DockerComposeGenerator:
    def __init__(self, project_info_path: str):
        self.project_info_path = project_info_path
        self.project_info = self._load_project_info(project_info_path)
        
    def _load_project_info(self, path: str) -> Dict[str, Any]:
        try:
            project_info_path = Path(path)
            with project_info_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"project_info.jsonが見つかりません: {path}")
        except json.JSONDecodeError:
            raise ValueError(f"project_info.jsonの形式が不正です: {path}")
        except Exception as e:
            raise Exception(f"project_info.jsonの読み込み中にエラーが発生しました: {str(e)}")
    
    def _generate_permission_commands(self, user: str, apps: Dict[str, Any]) -> str:
        # Windowsのパスを変換する関数
        def normalize_path(path):
            # バックスラッシュをフォワードスラッシュに変換
            return str(Path(path)).replace('\\', '/')

        commands = []
        for app_name, app_info in apps.items():
            app_path = normalize_path(f"/home/{user}/apps/{app_name}")
            # app_info.jsonとcontainer_info.jsonを除外してパーミッションを設定
            commands.append(f"find {app_path} -type f ! -name 'app_info.json' ! -name 'container_info.json' -exec chmod 755 {{}} \\;")
            commands.append(f"find {app_path} -type d -exec chmod 755 {{}} \\;")
            
            if "data_roots" in app_info:
                for host_path in app_info["data_roots"]:
                    container_path = normalize_path(Path("/home") / user / "apps" / app_name / Path(host_path).name)
                    commands.extend([
                        f"chmod 777 {container_path} # データディレクトリのルートにパーミッションを設定",
                        f"find {container_path} -type d -exec chmod 777 {{}} \\; # サブディレクトリのパーミッションを設定",
                        f"find {container_path} -type f -exec chmod 666 {{}} \\; # ファイルのパーミッションを設定"
                    ])
        return "\n".join(commands)

    def _generate_venv_setup_commands(self, user: str, apps: Dict[str, Any]) -> str:
        def normalize_path(path):
            return str(Path(path)).replace('\\', '/')

        commands = []
        for app_name, app_info in apps.items():
            venv_name = app_info['venv']
            venv_path = normalize_path(Path("/home") / user / "venv" / venv_name)
            app_path = normalize_path(Path("/home") / user / "apps" / app_name / Path(app_info['main']).stem)
            
            commands.extend([
                f'echo "Setting up virtual environment for {app_name}..."',
                f'python3 -m venv {venv_path} --clear --system-site-packages',
                f'echo "Installing requirements for {app_name}..."',
                f'{venv_path}/bin/pip install --no-cache-dir -r {app_path}/requirements.txt',
                f'# {app_name}のパッケージリストを保存',
                f'{venv_path}/bin/pip freeze > /opt/version_info/{app_name}_requirements.txt'
            ])
        return "\n".join(commands)

    def _generate_pythonpath_commands(self, user: str, apps: Dict[str, Any]) -> str:
        commands = []
        # 仮想環境名でグループ化してPYTHONPATHを設定
        used_venvs = set()
        for app_name, app_info in apps.items():
            venv_name = app_info['venv']
            if venv_name in used_venvs:
                continue
            
            used_venvs.add(venv_name)
            venv_path = f"/home/{user}/venv/{venv_name}"
            commands.extend([
                f'# {venv_name}環境のPYTHONPATH設定',
                # システムのPythonパスを先頭に追加
                f'export PYTHONPATH_{venv_name}="/usr/local/lib/python${{PY_VER}}/dist-packages:/usr/local/lib/python${{PY_VER}}/site-packages:/usr/lib/python${{PY_VER}}/dist-packages:/usr/lib/python${{PY_VER}}/site-packages:{venv_path}/lib/python${{PY_VER}}/site-packages"',
                f'echo "PYTHONPATH for {venv_name} set to: ${{PYTHONPATH_{venv_name}}}"'
            ])
        return "\n".join(commands)

    def _generate_start_commands(self, user: str, apps: Dict[str, Any]) -> str:
        commands = []
        for app_name, app_info in apps.items():
            app_dir = f"/home/{user}/apps/{app_name}/{Path(app_info['main']).stem}"
            venv_name = app_info['venv']
            venv_path = f"/home/{user}/venv/{venv_name}"
            is_last = list(apps.keys())[-1] == app_name
            background = "&" if not is_last else ""

            args = []
            for arg_name, arg_value in app_info.get('args', {}).items():
                args.append(f"{arg_name} {arg_value}")
            args_str = " ".join(args)

            commands.append(
                f"cd {app_dir}/ &&\n"
                f"PYTHONPATH=${{PYTHONPATH_{venv_name}}} {venv_path}/bin/python3 ./{app_info['main']} {args_str} {background}"
            )
        return "\n".join(commands)

    def _generate_service_command(self, user: str, apps: Dict[str, Any]) -> str:
        # 最初の仮想環境名を取得（テスト用）
        first_venv = next(iter(apps.values()))['venv']
        first_venv_path = f"/home/{user}/venv/{first_venv}"

        # Windowsのパスを変換する関数
        def normalize_path(path):
            return path.replace('\\', '/')

        commands = [
            'set -e',
            '# rootとして所有権を変更（sudoを使用）',
            f'sudo -n chown -R {user}:{user} /home/{user}',
            '# パーミッション変更（一般ユーザーで実行）',
            self._generate_permission_commands(user, apps),
            '# 以降は一般ユーザーとして実行',
            'echo "Current working directory: $${pwd}"',
            'ls -la',
            'echo "Detecting Python version..."',
            'RAW_VERSION="$$(python3 --version)"',
            'FULL_VERSION="$${RAW_VERSION#Python }"',
            'PY_VER="$$(echo $${FULL_VERSION} | cut -d. -f1,2)"',
            '# 仮想環境のセットアップ',
            self._generate_venv_setup_commands(user, apps),
            '# バージョン情報をコピー',
            f'cp -r /opt/version_info/* /home/{user}/version_info/',
            'rm -rf /opt/version_info/*',
            '# PYTHONPATHの設定',
            self._generate_pythonpath_commands(user, apps),
            'echo "Testing libm2k..."',
            f'PYTHONPATH=${{PYTHONPATH_{first_venv}}} {normalize_path(first_venv_path)}/bin/python3 -c "import libm2k; print(f\\"libm2k path: {{libm2k.__file__}}\\")"',
            'echo "Starting applications..."',
            f'mkdir -p /home/{user}/version_info',
            self._generate_start_commands(user, apps)
        ]
        
        command_str = '\n'.join(filter(None, commands))
        return f'/bin/bash -c \'{command_str}\''

    def _generate_volumes(self, user: str, apps: Dict[str, Any], service_name: str) -> list:
        volumes = [
            f"./version_info/{service_name}:/home/{user}/version_info",
            f"./container_info/{service_name}/container_info.json:/home/{user}/container_info.json"
        ]
        
        for app_name, app_info in apps.items():
            main_file = Path(app_info['main']).stem
            volumes.append(
                f"./programs/{main_file}:/home/{user}/apps/{app_name}/{main_file}"
            )
            volumes.append(
                f"./container_info/{service_name}/{app_name}/app_info.json:/home/{user}/apps/{app_name}/app_info.json"
            )
            
            if "data_roots" in app_info:
                for host_path in app_info["data_roots"]:  # リストとして処理
                    container_path = f"/home/{user}/apps/{app_name}/{Path(host_path).name}"
                    volumes.append(f"{host_path}:{container_path}")  # フルパスをそのまま使用
        
        return volumes
    
    def generate(self) -> Dict[str, Any]:
        compose = {
            "services": {},
            "networks": {
                "default": {
                    "driver": "bridge"
                }
            }
        }
        
        for service_name, service_info in self.project_info["services"].items():
            user = service_info["user"]
            service_config = {
                "build": {
                    "context": ".",
                    "dockerfile": f"./dockerfiles/{service_info['Dockerfile']}/Dockerfile"
                },
                "image": service_info["image"],
                "user": user,
                "working_dir": service_info["working_dir"],
                "networks": ["default"],
                "volumes": self._generate_volumes(user, service_info["apps"], service_name),
                "command": self._generate_service_command(user, service_info["apps"]),
                "ports": [],
                "environment": ["PYTHONPATH"]
            }
            
            # ポートの設定
            for app_info in service_info["apps"].values():
                service_config["ports"].append(f"{app_info['container_port']}")
            
            compose["services"][service_name] = service_config
        
        return compose
    
    def save(self, output_path: str = None):
        """
        docker-compose.ymlを生成して保存します。
        output_pathが指定されていない場合は、project_info.jsonと同じディレクトリに保存します。
        """
        if output_path is None:
            # project_info.jsonと同じディレクトリにdocker-compose.ymlを生成
            output_path = Path(self.project_info_path).parent / 'docker-compose.yml'
            
        compose_data = self.generate()
        
        yaml_str = yaml.dump(
            compose_data, 
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False, 
            indent=2,
            default_flow_style=False,
            default_style='',
            width=float("inf")
        )
        
        pattern = r"command: '(/bin/bash -c) ''(.+?)'''$"
        
        def replace_command(match):
            bash_cmd = match.group(1)
            command = match.group(2)
            lines = command.split('\n')
            processed_lines = []
            processed_lines.append(f"      {bash_cmd} '")
            for line in lines:
                line = line.strip()
                if line:
                    processed_lines.append(f"      {line}")
            processed_lines.append("      '")
            return f"command: |\n{chr(10).join(processed_lines)}"
        
        fixed_yaml = re.sub(pattern, replace_command, yaml_str, flags=re.MULTILINE | re.DOTALL)
        
        try:
            output_path = Path(output_path)
            with output_path.open('w', encoding='utf-8', newline='\n') as f:
                f.write(fixed_yaml)
        except Exception as e:
            raise Exception(f"docker-compose.ymlの保存中にエラーが発生しました: {str(e)}")

class CustomDumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)
    
    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()

if __name__ == "__main__":
    generator = DockerComposeGenerator("project_info.json")
    generator.save()