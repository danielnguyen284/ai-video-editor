"""Loopback-only HTTP API and ranged local media streaming for AI Editor Studio."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import threading
from urllib.parse import parse_qs, quote, unquote, urlparse
import webbrowser

from core.common import EditorError, ROOT, executable, identifier, read_json, within
from core.editor_service import EditorStore, fingerprint


def make_server(port=8765, root=ROOT):
    store = EditorStore(root)
    proxy_mutex = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_):
            pass

        def send_json(self, value, status=200):
            data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                url = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                path = unquote(url.path)
                if path == '/api/jobs':
                    return self.send_json(store.jobs())
                if path == '/api/profiles':
                    return self.send_json([read_json(p) for p in sorted((ROOT/'profiles').glob('*.json'))])
                if path == '/api/task':
                    return self.send_json(store.tasks.get(query['id'], {'status': 'error', 'message': 'Tác vụ không tồn tại; kiểm tra revision trong job nếu server đã khởi động lại.'}))
                if path == '/api/project':
                    state = store.load(query['job'], query.get('revision'))
                    folder = store.folder(query['job'])
                    state['media'] = read_json(folder/'job.json')['input']['media']
                    state['source'] = read_json(folder/'job.json')['assets'][0]['path']
                    state['setup'] = read_json(folder/'editor/setup.json') if (folder/'editor/setup.json').is_file() else read_json(folder/'revisions'/state['base_revision']/'decisions.json')['setup']
                    state['library'] = self.library(folder)
                    from core.adapters.ffmpeg import probe
                    state['durations'] = {layer['path']: probe(within(folder, layer['path']))['duration_seconds'] for layer in state['plan']['overlays'] if layer['type'] == 'video' and layer['id'] not in state['motions']}
                    return self.send_json(state)
                if path == '/api/library':
                    return self.send_json(self.library(store.folder(query['job'])))
                if path == '/media':
                    folder = store.folder(query['job'])
                    target = within(folder, query['path'])
                    # ProRes/MOV is not browser-compatible. Built-in motion uses React preview;
                    # unknown MOVs get a silent, cached browser proxy only on demand.
                    if query.get('proxy') == '1' and target.suffix.lower() in ('.mov', '.mkv', '.avi'):
                        key = fingerprint([str(target), target.stat().st_mtime_ns, target.stat().st_size])
                        proxy = folder/'editor/proxies'/f'{key}.mp4'
                        with proxy_mutex:
                            if not proxy.is_file():
                                proxy.parent.mkdir(parents=True, exist_ok=True)
                                result = subprocess.run([executable('ffmpeg'), '-v', 'error', '-nostdin', '-i', str(target), '-an', '-vf', 'scale=960:960:force_original_aspect_ratio=decrease:force_divisible_by=2', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(proxy)], capture_output=True)
                                if result.returncode:
                                    proxy.unlink(missing_ok=True)
                                    raise EditorError('Lỗi tạo preview proxy: '+result.stderr.decode(errors='replace')[-800:])
                        target = proxy
                    return self.send_file(target)
                if path.startswith('/api/'):
                    return self.send_json({'error': 'API không tồn tại.'}, 404)
                build = ROOT/'editor/build'
                target = within(build, path.lstrip('/') or 'index.html')
                if not target.is_file():
                    target = build/'index.html'
                return self.send_file(target)
            except (EditorError, OSError, ValueError, KeyError, TypeError) as error:
                self.send_json({'error': str(error)}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def library(self, folder):
            allowed = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.webm', '.mp3', '.wav', '.m4a'}
            paths = [p for base in ('input', 'assets') for p in (folder/base).rglob('*') if p.is_file() and p.suffix.lower() in allowed]
            return [{'path': p.relative_to(folder).as_posix(), 'name': p.name, 'type': 'image' if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'} else 'audio' if p.suffix.lower() in {'.mp3', '.wav', '.m4a'} else 'video'} for p in paths]

        def do_POST(self):
            try:
                # No CORS. Same-origin mutation guard blocks web pages from writing local projects.
                origin = self.headers.get('Origin')
                expected = f'http://{self.headers.get("Host")}'
                if origin and origin != expected:
                    return self.send_json({'error': 'Yêu cầu phải đến từ editor local.'}, 403)
                if self.headers.get('X-AI-Editor') != 'studio':
                    return self.send_json({'error': 'Thiếu header editor.'}, 403)
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    return self.send_json({'error': 'Chỉ nhận JSON.'}, 415)
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 20 * 1024 * 1024:
                    raise EditorError('Request cần nhỏ hơn 20MB.')
                body = json.loads(self.rfile.read(size))
                path = urlparse(self.path).path
                if path == '/api/project':
                    state = store.save(body['job'], body['state'], body['expected_version'])
                    return self.send_json(state)
                if path == '/api/lock':
                    return self.send_json(store.lock(body['job'], body['start'], body['end'], body['label'], body['expected_version']))
                if path == '/api/checkout':
                    return self.send_json(store.checkout(body['job'], body['revision'], body['expected_version']))
                if path == '/api/unlock':
                    return self.send_json(store.unlock(body['job'], body['id']))
                if path == '/api/export':
                    return self.send_json(store.export(body['job'], body['expected_version'], body.get('setup')))
                if path == '/api/import':
                    from core.jobs import create_job
                    if store.root.resolve() != ROOT.resolve():
                        raise EditorError('Import bị tắt trong workspace test.')
                    folder = create_job(body['job'], body['video'], body['profile'], body.get('brief', 'Tạo từ editor local'))
                    return self.send_json({'job': folder.name})
                if path == '/api/asset':
                    folder = store.folder(body['job'])
                    source = Path(body['path']).resolve()
                    if not source.is_file() or source.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.webm', '.mp3', '.wav', '.m4a'}:
                        raise EditorError('Chọn file ảnh/video/nhạc có thật trên máy.')
                    import uuid
                    target = folder/'assets/imported'/(uuid.uuid4().hex[:12]+source.suffix.lower())
                    target.parent.mkdir(exist_ok=True)
                    shutil.copy2(source, target)
                    return self.send_json({'path': target.relative_to(folder).as_posix(), 'library': self.library(folder)})
                return self.send_json({'error': 'API không tồn tại.'}, 404)
            except (EditorError, OSError, ValueError, KeyError, TypeError) as error:
                self.send_json({'error': str(error)}, 409)

        def send_file(self, target):
            if not target.is_file():
                return self.send_json({'error': 'Không tìm thấy file. Chạy npm run build trong editor/ trước.'}, 404)
            total = target.stat().st_size
            start, end, status = 0, total-1, 200
            request = self.headers.get('Range')
            if request:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', request)
                if not match or (not match[1] and not match[2]):
                    return self.send_json({'error': 'Range không hợp lệ.'}, 416)
                if match[1]:
                    start = int(match[1]); end = min(total-1, int(match[2])) if match[2] else total-1
                else:
                    start = max(0, total-int(match[2]))
                if start >= total or end < start:
                    return self.send_json({'error': 'Range ngoài file.'}, 416)
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(end-start+1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-cache')
            if status == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{total}')
            self.end_headers()
            try:
                with target.open('rb') as stream:
                    stream.seek(start)
                    remaining = end-start+1
                    while remaining:
                        chunk = stream.read(min(1024*1024, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.store = store
    return server


def serve(port=8765, open_browser=True):
    if not (ROOT/'editor/build/index.html').is_file():
        raise EditorError('Cài editor: scripts/setup.ps1 -WithEditor (hoặc npm ci và npm run build trong editor/).')
    server = make_server(port)
    url = f'http://127.0.0.1:{server.server_port}'
    print('AI Editor Studio: ' + url, flush=True)
    print('Chạy local, Ctrl+C để dừng. Không upload media lên mạng.', flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
