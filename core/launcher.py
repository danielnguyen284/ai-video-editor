"""Open the local Studio once, reusing its server across repeated shortcut clicks."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser

from core.common import EditorError, ROOT
from core.editor_service import fingerprint


def server_status(url, root=ROOT):
    try:
        # Ignore system HTTP proxies for the loopback health check.
        with build_opener(ProxyHandler({})).open(url+'/api/health', timeout=1) as response:
            value = json.load(response)
    except HTTPError:
        raise EditorError('Cổng Studio đang được ứng dụng khác sử dụng.')
    except (URLError, OSError):
        return False
    except (ValueError, UnicodeError):
        raise EditorError('Cổng Studio đang được ứng dụng khác sử dụng.')
    if not isinstance(value, dict) or value.get('app') != 'ai-editor-studio' or value.get('workspace') != fingerprint(str(Path(root).resolve())):
        raise EditorError('Cổng Studio đang mở một ứng dụng hoặc thư mục dự án khác. Đóng server đó trước.')
    return True


@contextmanager
def launch_lock(root):
    directory = Path(root)/'.studio'
    directory.mkdir(exist_ok=True)
    with (directory/'launcher.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            for _ in range(120):
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(.25)
            else:
                raise EditorError('Studio đang khởi động ở lần mở trước. Thử lại sau một lát.')
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def launch(root=ROOT, port=8765, open_browser=True):
    root = Path(root).resolve()
    url = f'http://127.0.0.1:{port}'
    with launch_lock(root):
        if not server_status(url, root):
            if not (root/'editor/build/index.html').is_file():
                raise EditorError('Chưa build Studio. Chạy scripts/setup.ps1 -WithEditor trước.')
            python = root/'.venv/Scripts/pythonw.exe'
            if not python.is_file():
                raise EditorError('Chưa có môi trường Python. Chạy scripts/setup.ps1 -WithEditor trước.')
            log_path = root/'.studio/server.log'
            with log_path.open('a', encoding='utf-8') as log:
                process = subprocess.Popen(
                    [str(python), '-u', str(root/'ai_editor.py'), 'editor', '--no-open', '--port', str(port)],
                    cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
            for _ in range(120):
                if server_status(url, root):
                    break
                if process.poll() is not None:
                    raise EditorError(f'Studio không khởi động được. Xem {log_path}')
                time.sleep(.25)
            else:
                raise EditorError(f'Studio khởi động lâu hơn dự kiến. Xem {log_path} rồi thử mở lại.')
    if open_browser and not webbrowser.open(url):
        raise EditorError('Studio đã chạy. Mở trình duyệt tại '+url)
    return url


def main():
    try:
        launch()
    except Exception as error:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        try:
            messagebox.showerror('AI Editor Studio', str(error), parent=root)
        finally:
            root.destroy()
        return 1
    return 0
