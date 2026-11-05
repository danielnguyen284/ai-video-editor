"""Media types and streamed browser-to-loopback uploads; never buffer videos in RAM."""
from pathlib import Path
import uuid

from core.common import EditorError

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS
MAX_UPLOAD_BYTES = 10 * 1024**3


def media_type(path):
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS: return 'image'
    if suffix in AUDIO_EXTENSIONS: return 'audio'
    if suffix in VIDEO_EXTENSIONS: return 'video'
    raise EditorError('Định dạng không hỗ trợ. Chọn video, ảnh hoặc nhạc.')


def receive_upload(stream, size, directory, name, *, video_only=False):
    if not isinstance(name, str) or not name or any(char in name for char in '/\\\x00') or len(name) > 180:
        raise EditorError('Tên file không hợp lệ hoặc dài hơn 180 ký tự.')
    kind = media_type(name)
    if video_only and kind != 'video':
        raise EditorError('Chọn một video nguồn.')
    if not 0 < size <= MAX_UPLOAD_BYTES:
        raise EditorError('File cần có dữ liệu và không vượt quá 10 GB.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory/(uuid.uuid4().hex[:12]+'-'+name)
    partial = target.with_name(target.name+'.part')
    try:
        with partial.open('xb') as output:
            remaining = size
            while remaining:
                chunk = stream.read(min(1024**2, remaining))
                if not chunk:
                    raise EditorError('Truyền file bị ngắt. Chọn lại file để thử lại.')
                output.write(chunk)
                remaining -= len(chunk)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target
