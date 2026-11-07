from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core.common import ROOT, EditorError, digest, executable, read_json, write_json
from core.jobs import create_job
from core.decisions import record_choice
from core.editor_service import EditorStore, check_render_locks, canonical_numbers, content_signature, compile_plan
from core.editor_server import make_server


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT/'.test-output'
        base.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='editor-tests-', dir=base)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(base.resolve())
        cls.source = cls.base/'source.mp4'
        result = subprocess.run([executable('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=160x284:r=30:d=4', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(cls.source)], capture_output=True)
        if result.returncode:
            raise AssertionError(result.stderr.decode(errors='replace'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.job = self.id().split('.')[-1].replace('_', '-')
        with patch('core.jobs.ROOT', self.base):
            self.folder = create_job(self.job, self.source, 'motion-catalog-vi', 'Synthetic editor test; not a real user choice')
        revision = self.folder/'revisions/r001'
        plan = read_json(revision/'edit-plan.json')
        plan['export'].update(width=160, height=284)
        plan['captions'].update(font_size=14, margin_v=25, max_chars=24)
        write_json(revision/'edit-plan.json', plan, replace=True)
        self.store = EditorStore(self.base)

    def select_setup(self):
        state = self.store.load(self.job)
        record_choice(self.folder/'revisions/r001', 'setup', 'Synthetic test fixture explicitly selects these settings', answers={
            'style': 'style/motion-catalog', 'domain': 'domain/source-context',
            'output': {k: state['plan']['export'][k] for k in ('width','height','fps','fit')},
            'footage_analysis': False, 'transcription': False, 'editing': 'Synthetic fixture source order',
            'captions': state['plan']['captions']['enabled'], 'research': 'None, synthetic data', 'visuals': 'Synthetic fixture layers', 'audio': 'Fixture voice only'})

    def test_retired_profile_is_returned_from_revision_snapshot(self):
        revision = self.folder/'revisions/r001'
        config = read_json(revision/'resolved-config.json')
        config['profile']['id'] = 'retired-profile'
        config['profile']['skills']['style']['id'] = 'style/retired-style'
        write_json(revision/'resolved-config.json', config, replace=True)
        server = make_server(0, self.base)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = json.load(urlopen(f'http://127.0.0.1:{server.server_port}/api/project?job={self.job}'))
            self.assertEqual(result['profile']['id'], 'retired-profile')
            self.assertEqual(result['profile']['skills']['style']['id'], 'style/retired-style')
            state = {key: value for key, value in result.items() if key not in {'profile', 'source', 'media', 'setup', 'library', 'durations'}}
            self.assertEqual(self.store.save(self.job, state, 0)['version'], 1)
            self.assertEqual(read_json(revision/'resolved-config.json')['profile']['id'], 'retired-profile')
        finally:
            server.shutdown()
            server.server_close()

    def test_browser_upload_batch_import_thumbnails_and_originals(self):
        audio = self.base/'nhạc nền.wav'
        image = self.base/'ảnh mẫu.png'
        for target, args in ((audio, ['-vn']), (image, ['-frames:v', '1'])):
            result = subprocess.run([executable('ffmpeg'), '-v', 'error', '-y', '-i', str(self.source), *args, str(target)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        originals = {p: digest(p) for p in (self.source, audio, image)}
        server = make_server(0, self.base)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        def post(endpoint, data):
            return json.load(urlopen(Request(base+'/api/'+endpoint, data=json.dumps(data).encode(), headers={'Content-Type':'application/json','X-AI-Editor':'studio'})))
        try:
            self.assertFalse((self.folder/'assets/imported').exists())
            from urllib.parse import urlencode
            def upload(source, **query):
                return json.load(urlopen(Request(base+'/api/upload?'+urlencode({'name':source.name, **query}), data=source.read_bytes(), headers={'Content-Type':'application/octet-stream','X-AI-Editor':'studio'})))
            staged = upload(self.source, kind='source')
            self.assertEqual(digest(staged['path']), originals[self.source])
            post('discard-upload', {'path':staged['path']})
            self.assertFalse(Path(staged['path']).exists())
            post('discard-upload', {'path':str(self.source)})
            self.assertTrue(self.source.is_file())
            paths = [upload(source, job=self.job)['path'] for source in (image, audio, self.source)]
            imported = {'paths':paths}
            self.assertEqual(len(imported['paths']), 3)
            for source, relative in zip((image, audio, self.source), imported['paths']):
                self.assertEqual(digest(self.folder/relative), originals[source])
                from urllib.parse import urlencode
                response = urlopen(base+'/thumbnail?'+urlencode({'job':self.job,'path':relative}))
                data = response.read()
                self.assertEqual(response.status, 200)
                self.assertTrue(data.startswith(b'\x89PNG') or data.startswith(b'\xff\xd8'))
            thumbs = list((self.folder/'editor/thumbnails').glob('*.jpg'))
            self.assertEqual(len(thumbs), 2)
            before = {p.name:p.stat().st_mtime_ns for p in thumbs}
            urlopen(base+'/thumbnail?'+urlencode({'job':self.job,'path':imported['paths'][1]})).read()
            self.assertEqual({p.name:p.stat().st_mtime_ns for p in thumbs}, before)
            with self.assertRaises(HTTPError):
                post('asset', {'job':self.job,'paths':[str(image),str(self.base/'missing.png')]})
            self.assertEqual(len(list((self.folder/'assets/imported').iterdir())), 3)
            with self.assertRaises(HTTPError):
                urlopen(base+'/thumbnail?'+urlencode({'job':self.job,'path':'../../../README.md'}))
            with self.assertRaises(HTTPError):
                urlopen(Request(base+'/api/upload?'+urlencode({'job':self.job,'name':'bad.png'}), data=b'bad', headers={'Content-Type':'application/octet-stream','X-AI-Editor':'studio','Origin':'https://example.com'}))
            self.assertEqual({p:digest(p) for p in originals}, originals)
        finally:
            server.shutdown(); server.server_close()

    def test_caption_corrections_export_with_a_locked_cue_without_touching_transcript(self):
        state = self.store.load(self.job)
        state['plan']['captions']['enabled'] = True
        state['cues'] = [{'id':str(i),'timeline_in_frame':i*30,'timeline_out_frame':(i+1)*30,'text':'HPG giữ' if i == 1 else 'HPG tăng'} for i in range(3)]
        state = self.store.save(self.job, state, 0)
        state = self.store.lock(self.job, 35, 60, 'Approved words', 1)
        transcript = self.folder/'transcript/raw.json'
        write_json(transcript, {'segments':[], 'note':'Original transcript fixture'}, replace=True)
        original = digest(transcript)
        state['cues'][0]['text'] = 'Hòa Phát tăng'
        state['cues'][2]['text'] = 'Hòa Phát tăng'
        state = self.store.save(self.job, state, 1)
        self.select_setup()
        task = self.store.export(self.job, state['version'])['task']
        for _ in range(200):
            result = self.store.tasks[task]
            if result['status'] != 'running': break
            time.sleep(.1)
        self.assertEqual(result['status'], 'complete', result)
        exported = read_json(self.folder/'revisions'/result['revision']/'edit-plan.json')
        self.assertEqual([c['text'] for c in exported['captions']['items']], ['Hòa Phát tăng','HPG giữ','Hòa Phát tăng'])
        self.assertEqual(digest(transcript), original)
        self.assertEqual(self.store.load(self.job)['locks'], state['locks'])

    def test_loading_is_read_only_and_save_preserves_source_revision(self):
        source_hash = digest(self.folder/'revisions/r001/edit-plan.json')
        state = self.store.load(self.job)
        self.assertFalse((self.folder/'editor').exists())
        state['plan']['audio']['voice_gain'] = .7
        saved = self.store.save(self.job, state, 0)
        self.assertEqual(saved['version'], 1)
        self.assertTrue((self.folder/'editor/history/000001.json').is_file())
        self.assertEqual(self.store.load(self.job)['plan']['audio']['voice_gain'], .7)
        self.assertEqual(digest(self.folder/'revisions/r001/edit-plan.json'), source_hash)
        with self.assertRaisesRegex(EditorError, 'nơi khác'):
            self.store.save(self.job, state, 0)

    def test_lock_blocks_all_tracks_and_cli_export_but_allows_changes_after_range(self):
        state = self.store.load(self.job)
        state = self.store.save(self.job, state, 0)
        state = self.store.lock(self.job, 30, 60, 'Approved middle scene', state['version'])
        for mutate in ('voice', 'caption', 'clip', 'overlay'):
            changed = deepcopy(state)
            if mutate == 'voice': changed['plan']['audio']['voice_gain'] = .2
            if mutate == 'caption': changed['plan']['captions']['enabled'] = True
            if mutate == 'clip': changed['plan']['clips'][0].update(source_in_seconds=1, timeline_out_frame=90); changed['plan']['duration_frames'] = 90
            if mutate == 'overlay': changed['plan']['overlays'].append({'id':'new-layer','type':'image','path':'input/raw.mp4','timeline_in_frame':30,'timeline_out_frame':60,'x':0,'y':0,'width':50,'height':50,'fit':'contain'})
            with self.subTest(track=mutate), self.assertRaisesRegex(EditorError, 'khóa'):
                self.store.save(self.job, changed, state['version'])
        raw = deepcopy(state['plan']); raw['audio']['voice_gain'] = .1
        with self.assertRaisesRegex(EditorError, 'khóa'):
            check_render_locks(self.folder, raw)
        changed = deepcopy(state)
        changed['plan']['clips'][0].update(source_out_seconds=3, timeline_out_frame=90)
        changed['plan']['duration_frames'] = 90
        saved = self.store.save(self.job, changed, state['version'])
        self.assertEqual(saved['plan']['duration_frames'], 90)
        self.store.unlock(self.job, state['locks'][0]['id'])
        saved['plan']['audio']['voice_gain'] = .2
        self.assertEqual(self.store.save(self.job, saved, saved['version'])['plan']['audio']['voice_gain'], .2)

    def test_lock_survives_restart_and_cannot_be_removed_in_save_payload(self):
        state = self.store.save(self.job, self.store.load(self.job), 0)
        state = self.store.lock(self.job, 0, 30, 'Opening approved', 1)
        state['locks'] = []
        state['plan']['audio']['voice_gain'] = .1
        with self.assertRaisesRegex(EditorError, 'khóa'):
            EditorStore(self.base).save(self.job, state, 1)

    def test_explicit_revision_adoption_preserves_checkpoint_and_respects_locks(self):
        from core.jobs import clone_revision
        state = self.store.save(self.job, self.store.load(self.job), 0)
        self.store.lock(self.job, 0, 30, 'Approved opening', 1)
        revision = clone_revision(self.folder, self.folder/'revisions/r001', 'Synthetic AI revision')
        state = self.store.checkout(self.job, revision.name, 1)
        self.assertEqual(state['base_revision'], 'r002')
        self.assertEqual(state['version'], 2)
        self.assertEqual(len(list((self.folder/'editor/checkpoints').glob('*.json'))), 1)
        changed = clone_revision(self.folder, revision, 'Synthetic conflicting revision')
        plan = read_json(changed/'edit-plan.json'); plan['audio']['voice_gain'] = .1
        write_json(changed/'edit-plan.json', plan, replace=True)
        with self.assertRaisesRegex(EditorError, 'khóa'):
            self.store.checkout(self.job, changed.name, 2)
        self.assertEqual(self.store.load(self.job)['base_revision'], 'r002')

    def test_caption_edit_keeps_other_cues_and_rejects_outside_ranges(self):
        state = self.store.load(self.job)
        state['cues'] = [{'id':'first','timeline_in_frame':0,'timeline_out_frame':30,'text':'Một'}, {'id':'second','timeline_in_frame':30,'timeline_out_frame':60,'text':'Hai'}]
        state['plan']['captions']['enabled'] = True
        state = self.store.save(self.job, state, 0)
        unchanged = deepcopy(state['cues'][1])
        state['cues'][0]['text'] = 'Bắt đầu'
        state = self.store.save(self.job, state, 1)
        self.assertEqual(state['cues'][1], unchanged)
        state['cues'][0]['timeline_out_frame'] = 9999
        with self.assertRaises(EditorError): self.store.save(self.job, state, 2)

    def test_browser_numeric_round_trip_preserves_new_and_legacy_locks(self):
        state = self.store.load(self.job)
        state['plan']['captions']['enabled'] = True
        state['cues'] = [{'id':'first','timeline_in_frame':0,'timeline_out_frame':30,'text':'Một'}, {'id':'locked','timeline_in_frame':30,'timeline_out_frame':60,'text':'Hai'}]
        state = self.store.save(self.job,state,0)
        state = self.store.lock(self.job,30,60,'Approved in Python',1)
        # Simulate a lock written by the previous release without changing its
        # approved content. This is only synthetic fixture data.
        locks = read_json(self.folder/'editor/locks.json')
        locks[0]['signature'] = content_signature(self.folder,state['plan'],state['cues'],state['motions'],30,60)
        write_json(self.folder/'editor/locks.json',locks,replace=True)
        original = digest(self.folder/'editor/locks.json')
        candidate = canonical_numbers(state)
        candidate['cues'][0]['text'] = 'Sửa ngoài khóa'
        saved = self.store.save(self.job,candidate,1)
        # A second save must find the original approved history, even though
        # the current draft now has JavaScript's numeric spelling.
        candidate = deepcopy(saved); candidate['cues'][0]['text'] = 'Sửa lần nữa'
        saved = EditorStore(self.base).save(self.job,candidate,2)
        self.assertEqual(digest(self.folder/'editor/locks.json'),original)
        check_render_locks(self.folder, compile_plan(saved))
        for mutation in ('text','gain'):
            changed=deepcopy(saved)
            if mutation == 'text': changed['cues'][1]['text'] = 'Không được đổi'
            else: changed['plan']['audio']['voice_gain'] = .9
            with self.assertRaisesRegex(EditorError,'khóa'): self.store.save(self.job,changed,3)
        new = self.store.lock(self.job,0,30,'New canonical lock',3)
        new = self.store.save(self.job,canonical_numbers(new),3)
        self.assertEqual(len(new['locks']),2)

    def test_legacy_lock_from_unsaved_revision_is_verified_without_rewriting_approval(self):
        state = self.store.lock(self.job,0,30,'Original no draft',0)
        locks = read_json(self.folder/'editor/locks.json')
        locks[0]['signature'] = content_signature(self.folder,state['plan'],state['cues'],state['motions'],0,30)
        write_json(self.folder/'editor/locks.json',locks,replace=True)
        original = digest(self.folder/'editor/locks.json')
        saved = self.store.save(self.job,canonical_numbers(state),0)
        self.assertEqual(saved['version'],1)
        self.assertEqual(digest(self.folder/'editor/locks.json'),original)

    def test_export_requires_real_setup_and_preserves_draft_and_revision(self):
        with self.assertRaisesRegex(EditorError, 'thiết lập'):
            self.store.export(self.job, 0)
        self.select_setup()
        state = self.store.save(self.job, self.store.load(self.job), 0)
        original = digest(self.folder/'revisions/r001/edit-plan.json')
        task_id = self.store.export(self.job, 1)['task']
        for _ in range(100):
            task = self.store.tasks[task_id]
            if task['status'] != 'running': break
            time.sleep(.1)
        self.assertEqual(task['status'], 'complete', task)
        self.assertTrue(Path(task['path']).is_file())
        self.assertEqual(task['revision'], 'r002')
        self.assertEqual(digest(self.folder/'revisions/r001/edit-plan.json'), original)
        self.assertEqual(self.store.load(self.job)['version'], state['version'])
        plan = read_json(self.folder/'revisions/r002/edit-plan.json')
        self.assertFalse(plan['captions']['enabled'])

    def test_http_range_streaming_path_containment_and_mutation_guard(self):
        server = make_server(0, self.base)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            url = base+'/media?job='+self.job+'&path=input/raw.mp4'
            response = urlopen(Request(url, headers={'Range':'bytes=0-15'}))
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), self.source.read_bytes()[:16])
            with self.assertRaises(HTTPError): urlopen(base+'/media?job='+self.job+'&path=../../../README.md')
            body = json.dumps({'job':self.job,'state':self.store.load(self.job),'expected_version':0}).encode()
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base+'/api/project', data=body, headers={'Content-Type':'application/json','Origin':'https://example.com','X-AI-Editor':'studio'}))
            self.assertEqual(error.exception.code, 403)
            self.assertFalse((self.folder/'editor').exists())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_locked_live_motion_exports_and_unchanged_motion_cache_is_reused(self):
        from core.adapters.motion import render_motion
        if not (ROOT/'motion/node_modules/@remotion/renderer').is_dir():
            self.skipTest('Optional motion dependencies not installed')
        self.select_setup()
        state = self.store.load(self.job)
        state['plan']['overlays'] = [{'id':'live-motion','type':'video','path':'input/raw.mp4','timeline_in_frame':0,'timeline_out_frame':60,'x':0,'y':0,'width':160,'height':284,'fit':'contain'}]
        state['motions'] = {'live-motion':{'template':'KineticScene','width':360,'height':640,'fps':30,'duration_frames':60,'props':{'title':'Synthetic approved scene','emphasis':'One idea','theme':'light'}}}
        state = self.store.save(self.job, state, 0)
        self.store.lock(self.job, 0, 60, 'Approved live motion', 1)
        with patch('core.adapters.motion.render_motion', wraps=render_motion) as rendering:
            for expected_revision in ('r002','r003'):
                task_id = self.store.export(self.job, 1)['task']
                deadline = time.monotonic()+90
                while self.store.tasks[task_id]['status']=='running' and time.monotonic()<deadline:
                    time.sleep(.1)
                task = self.store.tasks[task_id]
                self.assertEqual(task['status'], 'complete', task)
                self.assertEqual(task['revision'], expected_revision)
                self.assertTrue(Path(task['path']).is_file())
            self.assertEqual(rendering.call_count, 1)
        a = read_json(self.folder/'revisions/r002/edit-plan.json')['overlays'][0]['path']
        b = read_json(self.folder/'revisions/r003/edit-plan.json')['overlays'][0]['path']
        self.assertEqual(a,b)


if __name__ == '__main__': unittest.main()
