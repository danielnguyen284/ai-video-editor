from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from core.common import ROOT, EditorError, read_json, write_json
from core.decisions import initial_decisions, questions, record_choice, require_render_choices
from core.workflow_defaults import transcription_options, workflow_defaults
from core.adapters.transcription import transcribe


class StandingWorkflowTests(unittest.TestCase):
    def setUp(self):
        base = (ROOT/'.test-output').resolve()
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='standing-workflow-', dir=base)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(base) and self.root != base
        self.model_dir = self.root/'models/large-v3'
        self.model_dir.mkdir(parents=True)
        for name in ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json'):
            (self.model_dir/name).write_text('Synthetic model fixture; never loaded by a real model.', encoding='utf-8')
        self.defaults = workflow_defaults()
        self.defaults['transcription']['local_model_dir'] = self.model_dir.relative_to(ROOT).as_posix()
        self.config = {'workflow_defaults': self.defaults,
                       'profile': {'language': 'vi', 'skills': {'style': {'id': 'style/fixture'}, 'domain': {'id': 'domain/source-context'}}},
                       'skills': []}
        self.folder = self.root/'jobs/test'
        self.revision = self.folder/'revisions/r001'
        write_json(self.revision/'edit-plan.json', {'schema_version': '1.0', 'job_id': 'test', 'revision': 1})
        write_json(self.revision/'resolved-config.json', self.config)
        write_json(self.revision/'decisions.json', initial_decisions('test', 1))
        self.source = self.folder/'input/raw.mp4'
        self.source.parent.mkdir()
        self.source.write_bytes(b'Synthetic source; FFmpeg execution is mocked for STT contract tests.')
        write_json(self.folder/'job.json', {'job_id': 'test', 'assets': [{'asset_id': 'raw-001', 'path': 'input/raw.mp4'}],
                                          'input': {'media': {'has_audio': True}}})
        self.speech = SimpleNamespace(start=.2, end=.6, text='Xin chào', avg_logprob=-.1,
                                     words=[SimpleNamespace(start=.2, end=.3, word='Xin', probability=.98),
                                            SimpleNamespace(start=.3, end=.6, word='chào', probability=.97)])
        self.model = MagicMock()
        self.model.transcribe.return_value = ([self.speech], SimpleNamespace(language='vi'))
        self.constructor = MagicMock(return_value=self.model)
        self.fake_whisper = SimpleNamespace(WhisperModel=self.constructor)

    def tearDown(self):
        self.temp.cleanup()

    def test_local_defaults_resolve_without_changing_model_or_downloading(self):
        options = transcription_options(self.config)
        self.assertEqual(options['model'], str(self.model_dir))
        self.assertEqual((options['model_id'], options['device'], options['compute_type']), ('large-v3', 'cpu', 'int8'))
        self.assertEqual(options['selection_source'], 'standing-workflow')
        self.assertTrue(options['word_timestamps'])
        (self.model_dir/'model.bin').unlink()
        with self.assertRaisesRegex(EditorError, 'No model was changed or downloaded'):
            transcription_options(self.config)

    def test_stt_prepares_transcript_but_never_approves_creative_setup(self):
        before = (self.revision/'decisions.json').read_bytes()
        with patch.dict('sys.modules', {'faster_whisper': self.fake_whisper}), patch('core.adapters.transcription.execute') as execute:
            output = transcribe(self.folder)
        self.constructor.assert_called_once_with(str(self.model_dir), device='cpu', compute_type='int8')
        self.assertTrue(self.model.transcribe.call_args.kwargs['word_timestamps'])
        execute.assert_called_once()
        self.assertEqual((self.revision/'decisions.json').read_bytes(), before)
        self.assertEqual(read_json(output)['segments'][0]['words'][1]['text'], 'chào')
        note = read_json(self.folder/'transcript/processing.json')['attempts'][0]
        self.assertEqual(note['options']['selection_source'], 'standing-workflow')
        self.assertEqual(note['workflow_ref'], 'revisions/r001/resolved-config.json#workflow_defaults')
        self.assertNotIn('user_message', note)
        with self.assertRaisesRegex(EditorError, 'Waiting for user setup'):
            require_render_choices(self.revision)

    def test_transcript_is_preserved_and_never_retranscribed_on_a_retry(self):
        raw = self.folder/'transcript/raw.json'
        write_json(raw, {'segments': [{'text': 'Keep this transcript'}]})
        original = raw.read_bytes()
        with patch.dict('sys.modules', {'faster_whisper': self.fake_whisper}), patch('core.adapters.transcription.execute') as execute:
            with self.assertRaisesRegex(EditorError, 'Transcript already exists'):
                transcribe(self.folder)
        self.assertEqual(raw.read_bytes(), original)
        execute.assert_not_called()
        self.constructor.assert_not_called()

    def test_explicit_no_stt_wins_over_standing_local_processing(self):
        record_choice(self.revision, 'setup', 'Synthetic fixture selects no transcription.', answers={
            'style': 'style/fixture', 'domain': 'domain/source-context',
            'output': {'width': 1080, 'height': 1920, 'fps': 30, 'fit': 'pad'},
            'footage_analysis': False, 'transcription': False, 'editing': 'Keep source', 'captions': False,
            'research': 'None', 'visuals': 'None', 'audio': 'Source only'})
        with patch.dict('sys.modules', {'faster_whisper': self.fake_whisper}), patch('core.adapters.transcription.execute') as execute:
            with self.assertRaisesRegex(EditorError, 'Local transcription was not selected'):
                transcribe(self.folder)
        execute.assert_not_called()
        self.constructor.assert_not_called()

    def test_explicit_model_directory_and_device_are_preserved(self):
        other = self.root/'models/user-selected'
        other.mkdir()
        options = transcription_options(self.config, str(other), 'cuda')
        self.assertEqual(options['model'], str(other))
        self.assertEqual((options['device'], options['compute_type']), ('cuda', 'float16'))
        self.assertEqual(options['selection_source'], 'explicit-cli-argument')
        self.assertEqual(options['device_selection_source'], 'explicit-cli-argument')
        self.assertEqual(transcription_options(self.config, 'large-v3')['model'], str(self.model_dir))

    def test_missing_local_weights_fail_before_audio_extraction_or_model_creation(self):
        (self.model_dir/'tokenizer.json').unlink()
        with patch.dict('sys.modules', {'faster_whisper': self.fake_whisper}), patch('core.adapters.transcription.execute') as execute:
            with self.assertRaisesRegex(EditorError, 'tokenizer.json'):
                transcribe(self.folder)
        execute.assert_not_called()
        self.constructor.assert_not_called()
        self.assertFalse((self.folder/'transcript/processing.json').exists())

    def test_preprocessing_permission_can_be_disabled_in_a_frozen_job(self):
        self.config['workflow_defaults']['transcription']['allow_before_creative_setup'] = False
        write_json(self.revision/'resolved-config.json', self.config, replace=True)
        with patch.dict('sys.modules', {'faster_whisper': self.fake_whisper}), patch('core.adapters.transcription.execute') as execute:
            with self.assertRaisesRegex(EditorError, 'Waiting for user setup'):
                transcribe(self.folder)
        execute.assert_not_called()
        self.constructor.assert_not_called()

    def test_questions_separate_fixed_settings_from_unresolved_creative_choices(self):
        self.config.update(job_id='test', revision=1)
        write_json(self.revision/'resolved-config.json', self.config, replace=True)
        result = questions(self.revision)
        self.assertEqual(result['standing_workflow']['transcription']['model'], 'large-v3')
        self.assertNotIn('transcription', result['suggested_choices'])
        self.assertIn('style', result['suggested_choices'])
        self.assertEqual(result['decisions']['edit_plan']['status'], 'pending')
        frozen = workflow_defaults(self.config)
        frozen['transcription']['model'] = 'changed-copy'
        self.assertEqual(self.config['workflow_defaults']['transcription']['model'], 'large-v3')


if __name__ == '__main__':
    unittest.main()
