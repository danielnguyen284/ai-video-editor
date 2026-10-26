"""Persistent, non-destructive visual drafts and enforceable approval locks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import uuid

from core.common import EditorError, ROOT, digest, identifier, read_json, timestamp, within, write_json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        write_json(temporary, value)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def cues_for(folder, plan):
    from core.adapters.ffmpeg import mapped_captions
    caps = plan['captions']
    transcript = {}
    if 'items' not in caps:
        path = within(folder, caps['transcript_ref'])
        if path.is_file():
            transcript = read_json(path)
    return [{'id': f'cue-{index:04d}', 'timeline_in_frame': round(a * plan['fps']),
             'timeline_out_frame': round(b * plan['fps']), 'text': text}
            for index, (a, b, text) in enumerate(mapped_captions(plan, transcript))]


def motion_for(folder, plan):
    result = {}
    for layer in plan['overlays']:
        request = within(folder, layer['path']).parent / 'request.json'
        manifest = request.parent / 'manifest.json'
        if layer['type'] == 'video' and request.is_file() and manifest.is_file() and read_json(manifest).get('renderer') == 'remotion':
            result[layer['id']] = read_json(request)
    return result


def compile_plan(state):
    plan = deepcopy(state['plan'])
    plan['captions']['items'] = [{key: cue[key] for key in ('timeline_in_frame', 'timeline_out_frame', 'text')} for cue in state['cues']]
    return plan


def content_signature(folder, plan, cues, motions, start, end):
    """Fingerprint exactly what can affect this fixed output interval, on every track."""
    def asset(path):
        resolved = within(folder, path)
        return digest(resolved) if resolved.is_file() else 'missing:' + path

    def intersect(item):
        return max(start, item['timeline_in_frame']), min(end, item['timeline_out_frame'])

    clips, overlays, captions = [], [], []
    for clip in plan['clips']:
        a, b = intersect(clip)
        if a < b:
            offset = clip['source_in_seconds'] + (a - clip['timeline_in_frame']) / plan['fps']
            clips.append({'in': a, 'out': b, 'source': round(offset, 8), 'asset': clip['asset_id'], 'crop': clip.get('crop')})
    for layer in plan['overlays']:
        a, b = intersect(layer)
        if a < b:
            value = {key: value for key, value in layer.items() if key not in ('timeline_in_frame', 'timeline_out_frame', 'source_in_seconds')}
            value.update(start=a, end=b, asset_sha256=asset(layer['path']))
            if layer['type'] == 'video':
                value['source'] = round(layer.get('source_in_seconds', 0) + (a-layer['timeline_in_frame'])/plan['fps'], 8)
            if layer['id'] in motions:
                # Logical motion is editable before its first encoding. Its rendered
                # cache path changes on export without changing the approved scene.
                value.pop('path', None)
                value.pop('asset_sha256', None)
                value['motion'] = motions[layer['id']]
            overlays.append(value)
    if plan['captions']['enabled']:
        for cue in cues:
            a, b = intersect(cue)
            if a < b:
                captions.append({'start': a, 'end': b, 'text': cue['text']})
    job = read_json(folder / 'job.json')
    return fingerprint({'interval': [start, end], 'available': plan['duration_frames'] >= end,
                        'source': asset(job['assets'][0]['path']), 'clips': clips, 'overlays': overlays, 'captions': captions,
                        'export': plan['export'], 'audio': plan['audio'],
                        'music_sha256': asset(plan['audio']['music']['path']) if plan['audio'].get('music') else None,
                        'caption_style': {k: v for k, v in plan['captions'].items() if k not in ('items', 'transcript_ref')}})


def check_locks(folder, state):
    path = folder / 'editor/locks.json'
    locks = read_json(path) if path.is_file() else []
    for lock in locks:
        actual = content_signature(folder, state['plan'], state['cues'], state['motions'], lock['start'], lock['end'])
        if actual != lock['signature']:
            raise EditorError(f"Vùng đã khóa ‘{lock['label']}’ sẽ thay đổi. Mở khóa vùng này trước khi sửa.")


def check_render_locks(folder, plan):
    if (folder / 'editor/locks.json').is_file():
        check_locks(folder, {'plan': plan, 'cues': cues_for(folder, plan), 'motions': motion_for(folder, plan)})


class EditorStore:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.mutex = threading.RLock()
        self.tasks = {}

    def folder(self, job):
        folder = self.root / 'jobs' / identifier(job)
        if not (folder / 'job.json').is_file():
            raise EditorError('Không tìm thấy job.')
        return folder

    def jobs(self):
        result = []
        for path in sorted((self.root / 'jobs').glob('*/job.json')):
            job = read_json(path)
            revisions = [p.name for p in sorted((path.parent / 'revisions').glob('r[0-9]*')) if (p/'edit-plan.json').is_file()]
            result.append({'id': job['job_id'], 'brief': job.get('brief', ''), 'profile': job['profile_id'], 'revisions': revisions})
        return result

    def load(self, job, revision=None):
        folder = self.folder(job)
        project = folder / 'editor/project.json'
        if project.is_file():
            state = read_json(project)
        else:
            from core.jobs import revision_folder
            source = revision_folder(folder, revision)
            plan = read_json(source/'edit-plan.json')
            state = {'schema_version': '1.0', 'version': 0, 'job_id': job, 'base_revision': source.name,
                     'base_plan_sha256': digest(source/'edit-plan.json'), 'plan': plan,
                     'cues': cues_for(folder, plan), 'motions': motion_for(folder, plan), 'updated_at': timestamp()}
        locks = folder/'editor/locks.json'
        return {**state, 'locks': read_json(locks) if locks.is_file() else []}

    def _validate(self, folder, state):
        from core.adapters.ffmpeg import mapped_captions, probe, validate_plan
        from core.adapters.motion import validate_spec
        from core.validation import supported_keys
        supported_keys(state, 'schema_version version job_id base_revision base_plan_sha256 plan cues motions updated_at locks', 'editor project')
        plan = compile_plan(state)
        if plan.get('config_ref') != 'resolved-config.json' or plan['revision'] != int(state['base_revision'][1:]):
            raise EditorError('Plan phải giữ revision/config nguồn của draft.')
        job = read_json(folder/'job.json')
        validate_plan(plan, job, job['input']['media'])
        ids = set()
        for cue in state['cues']:
            supported_keys(cue, 'id timeline_in_frame timeline_out_frame text', 'editor cue')
            identifier(cue['id'])
            if cue['id'] in ids:
                raise EditorError('Caption ID bị trùng.')
            ids.add(cue['id'])
            if not isinstance(cue['text'], str) or not cue['text'].strip():
                raise EditorError('Caption cần nội dung.')
        # Validate cue ranges even when captions are disabled; retain them for later use.
        mapped_captions(plan, {})
        import textwrap
        for cue in state['cues']:
            wrapped = textwrap.wrap(' '.join(cue['text'].split()), width=plan['captions']['max_chars'], break_long_words=False, break_on_hyphens=False)
            if len(wrapped) > plan['captions']['max_lines']:
                raise EditorError('Caption quá dài. Tách cue hoặc tăng giới hạn dòng trước khi lưu.')
        layers = {layer['id']: layer for layer in plan['overlays']}
        for key, spec in state['motions'].items():
            if key not in layers or layers[key]['type'] != 'video':
                raise EditorError('Motion cần tham chiếu đúng layer video.')
            validate_spec(spec)
            if spec['duration_frames'] / spec['fps'] + .001 < (layers[key]['timeline_out_frame'] - layers[key]['timeline_in_frame']) / plan['fps'] + layers[key].get('source_in_seconds', 0):
                raise EditorError('Motion ngắn hơn khoảng layer. Tăng duration của motion trước.')
        for layer in plan['overlays']:
            if not within(folder, layer['path']).is_file():
                raise EditorError('Asset không tồn tại: ' + layer['path'])
            if layer['type'] == 'video' and layer['id'] not in state['motions'] and not layer.get('loop', False):
                from core.adapters.visuals import visual_info
                duration = visual_info(within(folder, layer['path']))['duration']
                needed = layer.get('source_in_seconds', 0) + (layer['timeline_out_frame']-layer['timeline_in_frame'])/plan['fps']
                if duration is None or duration + .001 < needed:
                    raise EditorError('Video layer ngắn hơn khoảng đã chọn: ' + layer['id'])
        if plan['audio'].get('music') and not within(folder, plan['audio']['music']['path']).is_file():
            raise EditorError('File nhạc không tồn tại.')

    def save(self, job, candidate, expected_version):
        with self.mutex:
            folder = self.folder(job)
            before = self.load(job)
            if before['version'] != expected_version:
                raise EditorError('Project đã được thay đổi ở nơi khác. Tải lại trước khi lưu để tránh ghi đè.')
            for key in ('job_id', 'schema_version', 'base_revision', 'base_plan_sha256'):
                if candidate.get(key) != before[key]:
                    raise EditorError('Không được thay metadata nguồn của draft.')
            if digest(folder/'revisions'/before['base_revision']/'edit-plan.json') != before['base_plan_sha256']:
                raise EditorError('Plan nguồn đã thay đổi ngoài editor. Dùng revision khác trước khi tiếp tục.')
            self._validate(folder, candidate)
            check_locks(folder, candidate)
            value = deepcopy(candidate)
            value.pop('locks', None)
            value.update(version=before['version']+1, updated_at=timestamp())
            history = folder/'editor/history'/f"{value['version']:06d}.json"
            write_json(history, value)
            atomic_json(folder/'editor/project.json', value)
            return self.load(job)

    def lock(self, job, start, end, label, expected_version):
        with self.mutex:
            state = self.load(job)
            if state['version'] != expected_version:
                raise EditorError('Lưu/tải lại draft trước khi khóa.')
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= state['plan']['duration_frames']:
                raise EditorError('Vùng khóa phải nằm trong timeline.')
            folder = self.folder(job)
            lock = {'id': uuid.uuid4().hex, 'start': start, 'end': end, 'label': str(label)[:120] or 'Vùng đã duyệt',
                    'signature': content_signature(folder, state['plan'], state['cues'], state['motions'], start, end), 'created_at': timestamp()}
            atomic_json(folder/'editor/locks.json', [*state['locks'], lock])
            return self.load(job)

    def unlock(self, job, lock_id):
        with self.mutex:
            folder = self.folder(job)
            state = self.load(job)
            atomic_json(folder/'editor/locks.json', [x for x in state['locks'] if x['id'] != lock_id])
            return self.load(job)

    def checkout(self, job, revision, expected_version):
        """Explicitly adopt an AI-created revision without bypassing approved regions."""
        with self.mutex:
            from core.jobs import revision_folder
            before = self.load(job)
            if before['version'] != expected_version:
                raise EditorError('Draft đã thay đổi. Tải lại trước khi mở revision khác.')
            folder = self.folder(job)
            source = revision_folder(folder, revision)
            plan = read_json(source/'edit-plan.json')
            state = {'schema_version': '1.0', 'version': before['version']+1, 'job_id': job,
                     'base_revision': source.name, 'base_plan_sha256': digest(source/'edit-plan.json'),
                     'plan': plan, 'cues': cues_for(folder, plan), 'motions': motion_for(folder, plan), 'updated_at': timestamp()}
            self._validate(folder, state)
            check_locks(folder, state)
            # Keep a working snapshot even when this was the first adoption.
            archive = folder/'editor/checkpoints'/f"before-checkout-{before['version']}-{uuid.uuid4().hex[:8]}.json"
            write_json(archive, before)
            write_json(folder/'editor/history'/f"{state['version']:06d}.json", state)
            atomic_json(folder/'editor/project.json', state)
            (folder/'editor/setup.json').unlink(missing_ok=True)
            return self.load(job)

    def export(self, job, expected_version, setup=None):
        with self.mutex:
            state = self.load(job)
            if expected_version != state['version']:
                raise EditorError('Lưu draft mới nhất trước khi xuất.')
            if any(x.get('job') == job and x['status'] == 'running' for x in self.tasks.values()):
                raise EditorError('Job này đang xuất. Chờ bản xuất hiện tại hoàn tất.')
            folder = self.folder(job)
            self._validate(folder, state)
            check_locks(folder, state)
            decisions = read_json(folder/'revisions'/state['base_revision']/'decisions.json')
            saved_setup = folder/'editor/setup.json'
            answers = setup or (read_json(saved_setup)['answers'] if saved_setup.is_file() else decisions['setup'].get('answers'))
            if not answers:
                raise EditorError('Cần chọn đầy đủ thiết lập trước khi xuất (nút Thiết lập).')
            from core.decisions import validate_answers
            answers = deepcopy(answers)
            answers['output'] = {k: state['plan']['export'][k] for k in ('width', 'height', 'fps', 'fit')}
            answers['captions'] = state['plan']['captions']['enabled']
            validate_answers(answers)
            config = read_json(folder/'revisions'/state['base_revision']/'resolved-config.json')
            if any(answers[kind] != config['profile']['skills'][kind]['id'] for kind in ('style', 'domain')):
                raise EditorError('Thiết lập style/domain không khớp profile của draft.')
            atomic_json(saved_setup, {'status': 'selected', 'answers': answers, 'user_message': 'UI: Nhấn Xác nhận bản dựng & xuất MP4 với thiết lập hiển thị.', 'selected_at': timestamp()})
            task = uuid.uuid4().hex
            self.tasks[task] = {'status': 'running', 'job': job, 'message': 'Chuẩn bị revision và tái sử dụng motion không đổi…'}
            threading.Thread(target=self._export_worker, args=(task, folder, deepcopy(state), answers), daemon=True).start()
            return {'task': task}

    def _export_worker(self, task, folder, state, answers):
        try:
            from core.jobs import clone_revision
            from core.adapters.motion import render_motion
            from core.adapters.ffmpeg import render
            from core.decisions import record_choice
            with self.mutex:
                revision = clone_revision(folder, folder/'revisions'/state['base_revision'], 'UI: Xuất bản dựng đang hiển thị trong editor; giữ các vùng đã khóa.')
            plan = compile_plan(state)
            plan['revision'] = int(revision.name[1:])
            write_json(revision/'edit-plan.json', plan, replace=True)
            record_choice(revision, 'setup', 'UI: Người dùng nhấn Xuất MP4, xác nhận thiết lập hiển thị và kế thừa các lựa chọn setup đã ghi.', answers=answers)
            for layer in plan['overlays']:
                spec = state['motions'].get(layer['id'])
                if not spec:
                    continue
                original = within(folder, layer['path']).parent/'request.json'
                if original.is_file() and read_json(original) == spec:
                    existing_manifest = read_json(original.parent/'manifest.json')
                    if existing_manifest.get('output_sha256') != digest(within(folder, layer['path'])):
                        raise EditorError('Motion asset đã bị thay đổi ngoài editor: ' + layer['id'])
                    continue
                key = fingerprint(spec)
                name = 'editor-' + key[:24]
                target = folder/'assets/visuals'/name/'motion.mov'
                manifest = target.parent/'manifest.json'
                if not target.is_file() or not manifest.is_file() or read_json(manifest).get('spec') != spec or read_json(manifest).get('output_sha256') != digest(target):
                    request = folder/'assets'/f'{name}.json'
                    atomic_json(request, spec)
                    self.tasks[task]['message'] = 'Render riêng motion đã thay đổi…'
                    target = render_motion(folder, revision, name, request.relative_to(folder).as_posix())
                layer['path'] = target.relative_to(folder).as_posix()
            write_json(revision/'edit-plan.json', plan, replace=True)
            record_choice(revision, 'edit-plan', 'UI: Nhấn Xuất MP4 với bản dựng đã lưu trong editor.', summary='Xuất chính xác draft trực quan đã lưu và giữ các vùng khóa.')
            self.tasks[task]['message'] = 'Đang encode MP4 từ timeline đã chọn…'
            output = render(folder, revision)
            self.tasks[task].update(status='complete', message='Đã xuất ' + revision.name, revision=revision.name, path=str(output), relative=output.relative_to(folder).as_posix())
        except Exception as error:
            self.tasks[task].update(status='error', message=str(error))
