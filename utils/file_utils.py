import os
import subprocess
import shutil
from pathlib import Path
from .dialogs import show_error_dialog

def create_symlink(src: str, dst: str, page = None):
    """プラットフォームに応じてシンボリックリンクを作成する
    
    Args:
        src (str): ソースパス
        dst (str): デスティネーションパス
        page (ft.Page, optional): Fletのページオブジェクト。エラーダイアログ表示に使用。
    
    Raises:
        Exception: シンボリックリンクの作成に失敗した場合
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        # 既存のディレクトリやファイルを削除
        if dst_path.exists():
            if dst_path.is_symlink():  # シンボリックリンクの場合
                dst_path.unlink()  # リンク自体のみを削除
            elif dst_path.is_dir():
                shutil.rmtree(dst_path)
            else:
                dst_path.unlink()

        # Windows環境の場合
        if os.name == 'nt':
            # パスを正規化
            src = str(src_path.resolve())
            dst = str(dst_path)
            
            if src_path.is_dir():
                cmd = f'cmd.exe /c mklink /D "{dst}" "{src}"'
            else:
                cmd = f'cmd.exe /c mklink "{dst}" "{src}"'
            
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                if page:
                    error_message = (
                        "シンボリックリンクの作成に失敗しました。\n\n"
                        "以下の手順で開発者モードを有効にしてください：\n"
                        "1. Windowsの設定を開く（Windowsキー + I）\n"
                        "2. 「システム」を選択\n"
                        "3. 右側のメニューを下にスクロールし、「開発者向け」を選択\n"
                        "4. 「開発者モード」をオンにする\n"
                        "5. アプリケーションを再起動する"
                    )
                    show_error_dialog(page, "開発者モードが必要です", error_message)
                raise Exception("シンボリックリンクの作成に失敗しました。開発者モードを有効にしてください。")
        # Unix系環境の場合
        else:
            dst_path.symlink_to(src_path)

    except Exception as e:
        raise Exception(f"ファイルのリンクの作成に失敗しました: {e}") 