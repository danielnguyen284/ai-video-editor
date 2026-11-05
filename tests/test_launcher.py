import json
from pathlib import Path
import socket
import subprocess
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from core.common import ROOT, EditorError
from core.editor_server import make_server
from core.launcher import launch, server_status
from core.editor_media import receive_upload
import io
import tempfile


class LauncherTests(unittest.TestCase):
    def test_existing_server_is_reused_and_wrong_workspace_is_rejected(self):
        server = make_server(0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertEqual(json.load(urlopen(url+'/api/health'))['app'], 'ai-editor-studio')
            with patch('core.launcher.subprocess.Popen') as spawn, patch('core.launcher.webbrowser.open', return_value=True) as browser:
                self.assertEqual(launch(port=server.server_port), url)
                self.assertEqual(launch(port=server.server_port), url)
                spawn.assert_not_called()
                self.assertEqual(browser.call_count, 2)
            with self.assertRaisesRegex(EditorError, 'khác'):
                server_status(url, ROOT/'.test-output')
        finally:
            server.shutdown(); server.server_close()

    def test_shortcut_launch_starts_real_hidden_server_once(self):
        if not (ROOT/'.venv/Scripts/pythonw.exe').is_file() or not (ROOT/'editor/build/index.html').is_file():
            self.skipTest('Windows editor setup required for launcher integration')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        spawned = []
        real_popen = subprocess.Popen
        def start(*args, **kwargs):
            process = real_popen(*args, **kwargs); spawned.append(process); return process
        try:
            with patch('core.launcher.subprocess.Popen', side_effect=start):
                url = launch(port=port, open_browser=False)
                self.assertTrue(server_status(url))
                self.assertEqual(launch(port=port, open_browser=False), url)
            self.assertEqual(len(spawned), 1)
            self.assertIsNone(spawned[0].poll())
        finally:
            for process in spawned:
                process.terminate(); process.wait(timeout=10)

    def test_upload_streams_unicode_files_rejects_paths_and_cleans_interrupted_data(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-output') as directory:
            folder=Path(directory)
            data=b'fixture'*400000
            source=io.BytesIO(data)
            target=receive_upload(source,len(data),folder,'ảnh mẫu.png')
            self.assertEqual(target.read_bytes(),data)
            for name in ('../outside.mp4', 'folder\\outside.mp4', 'unknown.exe', ''):
                with self.assertRaises(EditorError): receive_upload(io.BytesIO(b'x'),1,folder,name)
            with self.assertRaisesRegex(EditorError,'video'):
                receive_upload(io.BytesIO(b'x'),1,folder,'photo.png',video_only=True)
            with self.assertRaisesRegex(EditorError,'ngắt'):
                receive_upload(io.BytesIO(b'x'),100,folder,'truncated.mp4')
            with self.assertRaises(EditorError): receive_upload(io.BytesIO(),0,folder,'empty.mp4')
            self.assertEqual(list(folder.iterdir()),[target])


if __name__ == '__main__':
    unittest.main()
