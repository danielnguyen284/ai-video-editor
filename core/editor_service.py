"""Persistent, non-destructive visual drafts and enforceable approval locks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import uuid

from core.common import EditorError, ROOT, digest, identifier, read_json, timestamp, within, write_json
from core.adapters.camera import clip_zoom_frames


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


def transcript_words(folder, plan):
    """Source-time words for editing by text; read-only, never rewrites a transcript.

    Prefers the plan's corrected transcript, then cleaned.json, then raw.json.
    A segment without word timings becomes one token so it can still be cut whole.
    """
    job = read_json(folder / 'job.json')
    for ref in (plan['captions'].get('transcript_ref'), 'transcript/cleaned.json', 'transcript/raw.json'):
        path = within(folder, ref) if ref else None
        if not path or not path.is_file():
            continue
        data = read_json(path)
        if data.get('asset_id') not in (None, job['assets'][0]['asset_id']):
            continue
        words = []
        for index, segment in enumerate(data.get('segments', [])):
            tokens = segment.get('words') or [{'start': segment['start'], 'end': segment['end'], 'text': segment.get('text', '')}]
            for word in tokens:
                text = ' '.join(str(word.get('text', '')).split())
                if text and word['end'] > word['start']:
                    words.append({'start': word['start'], 'end': word['end'], 'text': text, 'segment': index})
        words.sort(key=lambda word: word['start'])
        return {'ref': ref, 'words': words}
    return None


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


def canonical_numbers(value):
    """JSON/browser round trips preserve numeric values but not 1.0 versus 1."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [canonical_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical_numbers(item) for key, item in value.items()}
    return value


def content_fingerprints(folder, plan, cues, motions, start, end):
    """Fingerprint exactly what can affect this fixed output interval, on every track."""
    def asset(path):
        resolved = within(folder, path)
        return digest(resolved) if resolved.is_file() else 'missing:' + path

    def intersect(item):
        return max(start, item['timeline_in_frame']), min(end, item['timeline_out_frame'])

    clips, overlays, captions, sfx = [], [], [], []
    for clip in plan['clips']:
        a, b = intersect(clip)
        if a < b:
            rate = clip.get('playback_rate', 1)
            offset = clip['source_in_seconds'] + (a - clip['timeline_in_frame']) / plan['fps'] * rate
            value = {'in': a, 'out': b, 'source': round(offset, 8), 'asset': clip['asset_id'], 'crop': clip.get('crop')}
            # Speed and zoom join the fingerprint only when they change the picture,
            # so locks made before these features stay valid.
            if rate != 1:
                value['rate'] = rate
            frames = clip_zoom_frames(clip, plan['fps'])
            if frames:
                visible = frames[a - clip['timeline_in_frame']:b - clip['timeline_in_frame']]
                if any(scale != 1 for scale, _, _ in visible):
                    value['zoom'] = [[round(s, 6), round(x, 6), round(y, 6)] if s != 1 else [1] for s, x, y in visible]
            clips.append(value)
    # A transition shows both neighbours' picture around its cut, so it joins a
    # lock whose interval touches that window (absent key: older locks unchanged).
    from core.adapters.ffmpeg import transition_split
    transitions = []
    for i, clip in enumerate(plan['clips']):
        if i and clip.get('transition'):
            before, after = transition_split(clip['transition']['frames'])
            cut, previous = clip['timeline_in_frame'], plan['clips'][i - 1]
            if max(start, cut - before) < min(end, cut + after):
                transitions.append({'at': cut, 'type': clip['transition']['type'], 'frames': clip['transition']['frames'],
                                    'from': [previous['source_out_seconds'], previous.get('playback_rate', 1)],
                                    'to': [clip['source_in_seconds'], clip.get('playback_rate', 1)]})
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
    for item in plan['audio'].get('sfx', []):
        a, b = intersect(item)
        if a < b:
            sfx.append({'start': a, 'end': b, 'offset': a - item['timeline_in_frame'], 'gain': item['gain'], 'asset_sha256': asset(item['path'])})
    job = read_json(folder / 'job.json')
    content = {'interval': [start, end], 'available': plan['duration_frames'] >= end,
                        'source': asset(job['assets'][0]['path']), 'clips': clips, 'overlays': overlays, 'captions': captions,
                        'export': plan['export'], 'audio': {k: v for k, v in plan['audio'].items() if k != 'sfx'},
                        'music_sha256': asset(plan['audio']['music']['path']) if plan['audio'].get('music') else None,
                        'caption_style': {k: v for k, v in plan['captions'].items() if k not in ('items', 'transcript_ref')}}
    if sfx:
        content['sfx'] = sfx
    if transitions:
        content['transitions'] = transitions
    return fingerprint(content), fingerprint(canonical_numbers(content))


def content_signature(folder, plan, cues, motions, start, end, *, canonical=False):
    return content_fingerprints(folder, plan, cues, motions, start, end)[1 if canonical else 0]


def check_locks(folder, state):
    path = folder / 'editor/locks.json'
    locks = read_json(path) if path.is_file() else []
    for lock in locks:
        actual, normalized = content_fingerprints(folder, state['plan'], state['cues'], state['motions'], lock['start'], lock['end'])
        if lock['signature'] in (actual, normalized):
            continue
        # Older locks hashed Python's numeric spelling. Recover their approved
        # content only from a snapshot whose ORIGINAL hash matches the lock.
        # Do not rewrite a lock or trust the candidate as an approval reference.
        def approved_states():
            references = [folder/'editor/project.json', *sorted((folder/'editor/history').glob('*.json'), reverse=True)]
            for reference in references:
                if reference.is_file(): yield read_json(reference)
            # Old releases could lock an untouched revision before its first save.
            revision = state.get('base_revision', f"r{state['plan']['revision']:03d}")
            source = folder/'revisions'/revision/'edit-plan.json'
            if source.is_file():
                plan = read_json(source)
                yield {'plan': plan, 'cues': cues_for(folder, plan), 'motions': motion_for(folder, plan)}
        matched = False
        for approved in approved_states():
            args = (folder, approved['plan'], approved['cues'], approved['motions'], lock['start'], lock['end'])
            original, canonical = content_fingerprints(*args)
            if original == lock['signature']:
                matched = canonical == normalized
                break
        if not matched:
            raise EditorError(f"Vùng đã khóa ‘{lock['label']}’ sẽ thay đổi. Mở khóa vùng này trước khi sửa.")


def describe_changes(before, after):
    """Short Vietnamese summary of what a proposal changes, for the approval bar."""
    plan_a, plan_b = before['plan'], after['plan']
    fps = plan_a['fps']
    changes = []
    if plan_a['duration_frames'] != plan_b['duration_frames']:
        changes.append(f"Thời lượng {plan_a['duration_frames'] / fps:.1f}s → {plan_b['duration_frames'] / fps:.1f}s")
    # Splitting a clip repeats its speed/zoom/crop, so compare value sets, not lists.
    timing = lambda plan: [(c['source_in_seconds'], c['source_out_seconds']) for c in plan['clips']]
    values = lambda plan, key: {json.dumps(c.get(key), sort_keys=True) for c in plan['clips']}
    if timing(plan_a) != timing(plan_b):
        changes.append(f"Đoạn cắt {len(plan_a['clips'])} → {len(plan_b['clips'])} clip")
    for key, label in (('playback_rate', 'Tốc độ'), ('zoom', 'Zoom'), ('crop', 'Crop nguồn')):
        if values(plan_a, key) != values(plan_b, key):
            changes.append(f'{label} thay đổi')
    cues_a = {c['id']: c for c in before['cues']}
    cues_b = {c['id']: c for c in after['cues']}
    added, removed = len(cues_b.keys() - cues_a.keys()), len(cues_a.keys() - cues_b.keys())
    edited = sum(1 for key in cues_a.keys() & cues_b.keys() if cues_a[key] != cues_b[key])
    if added or removed or edited:
        changes.append(f"Caption: thêm {added}, bỏ {removed}, sửa {edited}")
    layers_a = {layer['id']: layer for layer in plan_a['overlays']}
    layers_b = {layer['id']: layer for layer in plan_b['overlays']}
    if layers_a != layers_b or before['motions'] != after['motions']:
        changes.append(f"Lớp hình/motion {len(layers_a)} → {len(layers_b)}")
    if plan_a['audio'] != plan_b['audio']:
        changes.append('Âm thanh thay đổi')
    if plan_a['export'] != plan_b['export'] or plan_a['captions'] != plan_b['captions']:
        changes.append('Khung hình hoặc kiểu caption thay đổi')
    return changes or ['Không có thay đổi nhìn thấy được']


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
        from core.adapters.ffmpeg import caption_lines
        for cue in state['cues']:
            if len(caption_lines(cue['text'], plan['captions']['max_chars'])) > plan['captions']['max_lines']:
                raise EditorError('Caption quá dài. Tách cue hoặc tăng giới hạn dòng trước khi lưu.')
        layers = {layer['id']: layer for layer in plan['overlays']}
        for key, spec in state['motions'].items():
            if key not in layers or layers[key]['type'] != 'video':
                raise EditorError('Motion cần tham chiếu đúng layer video.')
            validate_spec(spec)
            from core.adapters.motion import job_images
            for prop in job_images(spec):
                if not within(folder, spec['props'][prop]).is_file():
                    raise EditorError('Ảnh minh họa không tồn tại: ' + spec['props'][prop])
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
        for item in plan['audio'].get('sfx', []):
            if not within(folder, item['path']).is_file():
                raise EditorError('File SFX không tồn tại: ' + item['path'])

    def _check_candidate(self, folder, before, candidate, expected_version):
        if before['version'] != expected_version:
            raise EditorError('Project đã được thay đổi ở nơi khác. Tải lại trước khi lưu để tránh ghi đè.')
        for key in ('job_id', 'schema_version', 'base_revision', 'base_plan_sha256'):
            if candidate.get(key) != before[key]:
                raise EditorError('Không được thay metadata nguồn của draft.')
        if digest(folder/'revisions'/before['base_revision']/'edit-plan.json') != before['base_plan_sha256']:
            raise EditorError('Plan nguồn đã thay đổi ngoài editor. Dùng revision khác trước khi tiếp tục.')
        self._validate(folder, candidate)
        check_locks(folder, candidate)

    def _commit(self, folder, before, candidate):
        value = deepcopy(candidate)
        value.pop('locks', None)
        value.update(version=before['version']+1, updated_at=timestamp())
        history = folder/'editor/history'/f"{value['version']:06d}.json"
        write_json(history, value)
        atomic_json(folder/'editor/project.json', value)

    def save(self, job, candidate, expected_version):
        with self.mutex:
            folder = self.folder(job)
            before = self.load(job)
            self._check_candidate(folder, before, candidate, expected_version)
            self._commit(folder, before, candidate)
            return self.load(job)

    # An AI proposal is a validated candidate draft kept beside project.json.
    # It changes nothing until the user approves it in Studio; approval is one
    # saved version, so a single undo returns to the previous draft.
    def propose(self, job, candidate, expected_version, summary):
        with self.mutex:
            folder = self.folder(job)
            before = self.load(job)
            self._check_candidate(folder, before, candidate, expected_version)
            if not isinstance(summary, str) or not summary.strip():
                raise EditorError('Đề xuất cần một câu tóm tắt thay đổi cho người dùng.')
            state = {k: v for k, v in deepcopy(candidate).items() if k not in ('locks', 'version', 'updated_at')}
            proposal = {'id': uuid.uuid4().hex, 'created_at': timestamp(), 'base_version': before['version'],
                        'summary': summary.strip()[:500], 'changes': describe_changes(before, state), 'state': state}
            self._close_proposal(folder, 'superseded', 'Một đề xuất mới thay thế đề xuất này.')
            atomic_json(folder/'editor/proposal.json', proposal)
            return proposal

    def proposal(self, job):
        """Pending proposal, or the most recently decided one with its status."""
        folder = self.folder(job)
        pending = folder/'editor/proposal.json'
        if pending.is_file():
            return {**read_json(pending), 'status': 'pending'}
        decided = sorted((folder/'editor/proposals').glob('*.json'), key=lambda p: p.stat().st_mtime_ns)
        return read_json(decided[-1]) if decided else None

    def _close_proposal(self, folder, status, note):
        pending = folder/'editor/proposal.json'
        if not pending.is_file():
            return None
        # An accepted state lives on in editor/history; keep only the record.
        record = {k: v for k, v in read_json(pending).items() if k != 'state'}
        record.update(status=status, decided_at=timestamp(), note=note)
        atomic_json(folder/'editor/proposals'/f"{record['id']}.json", record)
        pending.unlink()
        return record

    def decide_proposal(self, job, proposal_id, accept, expected_version=None):
        with self.mutex:
            folder = self.folder(job)
            pending = folder/'editor/proposal.json'
            if not pending.is_file() or read_json(pending)['id'] != proposal_id:
                raise EditorError('Đề xuất này không còn chờ duyệt.')
            if not accept:
                self._close_proposal(folder, 'rejected', 'UI: Người dùng bấm Bỏ đề xuất.')
                return self.load(job)
            proposal = read_json(pending)
            before = self.load(job)
            if before['version'] != proposal['base_version'] or expected_version != before['version']:
                raise EditorError('Draft đã thay đổi sau khi AI đề xuất. Bỏ đề xuất này và nhờ AI đề xuất lại trên bản mới.')
            candidate = {**proposal['state'], 'version': before['version'], 'updated_at': before['updated_at']}
            self._check_candidate(folder, before, candidate, before['version'])
            self._commit(folder, before, candidate)
            self._close_proposal(folder, 'accepted', 'UI: Người dùng bấm Duyệt đề xuất.')
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
                    'signature': content_signature(folder, state['plan'], state['cues'], state['motions'], start, end, canonical=True), 'created_at': timestamp()}
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
