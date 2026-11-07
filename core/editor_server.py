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
import uuid
from urllib.parse import parse_qs, quote, unquote, urlparse
import webbrowser

from core.common import EditorError, ROOT, executable, identifier, read_json, within
from core.editor_service import EditorStore, fingerprint
from core.editor_media import MEDIA_EXTENSIONS, media_type, receive_upload, MAX_UPLOAD_BYTES


def make_server(port=8765, root=ROOT):
    store = EditorStore(root)
    proxy_mutex = threading.Lock()
    thumbnail_mutex = threading.Lock()
    duration_cache = {}

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
                if path == '/api/health':
                    return self.send_json({'app': 'ai-editor-studio', 'workspace': fingerprint(str(store.root.resolve())), 'version': 1})
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
                    state['profile'] = read_json(folder/'revisions'/state['base_revision']/'resolved-config.json')['profile']
                    state['setup'] = read_json(folder/'editor/setup.json') if (folder/'editor/setup.json').is_file() else read_json(folder/'revisions'/state['base_revision']/'decisions.json')['setup']
                    state['library'] = self.library(folder)
                    from core.adapters.ffmpeg import probe
                    state['durations'] = {layer['path']: probe(within(folder, layer['path']))['duration_seconds'] for layer in state['plan']['overlays'] if layer['type'] == 'video' and layer['id'] not in state['motions']}
                    return self.send_json(state)
                if path == '/api/library':
                    return self.send_json(self.library(store.folder(query['job'])))
                if path == '/thumbnail':
                    folder = store.folder(query['job'])
                    source = within(folder, query['path'])
                    kind = media_type(source)
                    if not source.is_file():
                        raise EditorError('Không tìm thấy media để tạo thumbnail.')
                    if kind == 'image':
                        return self.send_file(source)
                    key = fingerprint([str(source), source.stat().st_mtime_ns, source.stat().st_size])
                    target = folder/'editor/thumbnails'/f'{key}.jpg'
                    with thumbnail_mutex:
                        if not target.is_file():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            temporary = target.with_name(uuid.uuid4().hex+'.jpg')
                            command = [executable('ffmpeg'), '-v', 'error', '-nostdin']
                            if kind == 'audio': command += ['-t', '20']
                            command += ['-i', str(source)]
                            command += ['-filter_complex', 'aformat=channel_layouts=mono,showwavespic=s=240x100:colors=0xc1e875', '-frames:v', '1'] if kind == 'audio' else ['-vf', 'thumbnail=30,scale=240:160:force_original_aspect_ratio=decrease', '-frames:v', '1']
                            try:
                                result = subprocess.run(command+['-update', '1', str(temporary)], capture_output=True, timeout=30)
                                if result.returncode or not temporary.is_file():
                                    raise EditorError('Không tạo được thumbnail cho file này.')
                                temporary.replace(target)
                            finally:
                                temporary.unlink(missing_ok=True)
                    return self.send_file(target)
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
            except (EditorError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
                self.send_json({'error': str(error)}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def library(self, folder):
            allowed = MEDIA_EXTENSIONS
            paths = [p for base in ('input', 'assets') for p in (folder/base).rglob('*') if p.is_file() and p.suffix.lower() in allowed]
            result = []
            for p in paths:
                item = {'path': p.relative_to(folder).as_posix(), 'name': re.sub(r'^[a-f0-9]{12}-', '', p.name) if p.parent == folder/'assets/imported' else p.name, 'type': media_type(p)}
                if item['type'] == 'video':
                    key = (str(p), p.stat().st_mtime_ns, p.stat().st_size)
                    if key not in duration_cache:
                        from core.adapters.ffmpeg import probe
                        try:
                            info = probe(p)
                            duration_cache[key] = info['duration_seconds'] if info['has_video'] else 0
                        except (EditorError, ValueError):
                            duration_cache[key] = 0
                    item['duration_seconds'] = duration_cache[key]
                result.append(item)
            return result

        def do_POST(self):
            try:
                url = urlparse(self.path)
                if url.path == '/api/upload':
                    if self.headers.get('Origin') not in (None, f'http://{self.headers.get("Host")}') or self.headers.get('X-AI-Editor') != 'studio':
                        self.close_connection = True
                        size = int(self.headers.get('Content-Length', 0))
                        if 0 < size <= 20 * 1024**2:
                            self.rfile.read(size)
                        return self.send_json({'error': 'Yêu cầu phải đến từ editor local.'}, 403)
                    query = {k: v[0] for k, v in parse_qs(url.query).items()}
                    size = int(self.headers.get('Content-Length', 0))
                    if not 0 < size <= MAX_UPLOAD_BYTES:
                        self.close_connection = True
                        raise EditorError('File cần có dữ liệu và không vượt quá 10 GB.')
                    source = query.get('kind') == 'source'
                    folder = None if source else store.folder(query['job'])
                    directory = store.root/'.studio/imports' if source else folder/'assets/imported'
                    # Invalid names/types are rejected before opening a destination file.
                    self.close_connection = True
                    target = receive_upload(self.rfile, size, directory, query['name'], video_only=source)
                    if source:
                        return self.send_json({'path': str(target)})
                    return self.send_json({'path': target.relative_to(folder).as_posix(), 'library': self.library(folder)})
                # Consume bounded request bytes before replying, including rejected requests.
                # Closing a socket with an unread request body can reset the response on Windows.
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 20 * 1024 * 1024:
                    self.close_connection = True
                    raise EditorError('Request cần nhỏ hơn 20MB.')
                payload = self.rfile.read(size)
                # No CORS. Same-origin mutation guard blocks web pages from writing local projects.
                origin = self.headers.get('Origin')
                expected = f'http://{self.headers.get("Host")}'
                if origin and origin != expected:
                    return self.send_json({'error': 'Yêu cầu phải đến từ editor local.'}, 403)
                if self.headers.get('X-AI-Editor') != 'studio':
                    return self.send_json({'error': 'Thiếu header editor.'}, 403)
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    return self.send_json({'error': 'Chỉ nhận JSON.'}, 415)
                body = json.loads(payload)
                if not isinstance(body, dict):
                    raise EditorError('Request cần là JSON object.')
                path = urlparse(self.path).path
                if path == '/api/discard-upload':
                    target = Path(body['path']).resolve()
                    if target.parent == (store.root/'.studio/imports').resolve():
                        target.unlink(missing_ok=True)
                    return self.send_json({'ok': True})
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
                    staged = Path(body['video']).resolve()
                    if staged.parent == (store.root/'.studio/imports').resolve():
                        staged.unlink(missing_ok=True)
                    return self.send_json({'job': folder.name})
                if path == '/api/asset':
                    folder = store.folder(body['job'])
                    paths = body.get('paths', [body.get('path')])
                    if not isinstance(paths, list) or not 1 <= len(paths) <= 100 or not all(isinstance(p, str) for p in paths):
                        raise EditorError('Chọn từ 1 đến 100 file media.')
                    sources = [Path(p).resolve() for p in paths]
                    for source in sources:
                        if not source.is_file():
                            raise EditorError('Không tìm thấy file: '+source.name)
                        media_type(source)
                    targets = []
                    try:
                        for source in sources:
                            target = folder/'assets/imported'/(uuid.uuid4().hex[:12]+'-'+source.name)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            targets.append(target)
                            shutil.copy2(source, target)
                    except OSError:
                        for target in targets:
                            target.unlink(missing_ok=True)
                        raise
                    return self.send_json({'path': targets[0].relative_to(folder).as_posix(), 'paths': [p.relative_to(folder).as_posix() for p in targets], 'library': self.library(folder)})
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
