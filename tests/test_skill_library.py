from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from core.common import ROOT, EditorError, digest, executable, read_json, write_json
from core.skill_library import content_digest, inventory, snapshot


class LibraryIntegrityTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / '.test-output'
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='skill-library-', dir=base)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(base.resolve()) and self.root != base.resolve()
        self.folder = self.root / '.tools/library/example/edit'
        self.folder.mkdir(parents=True)
        (self.folder / 'SKILL.md').write_text('---\nname: example\ndescription: fixture\n---\nRead references/timing.md\n', encoding='utf-8')
        (self.folder / 'references').mkdir()
        (self.folder / 'references/timing.md').write_text('Pinned timing rules', encoding='utf-8')
        package = {'id': 'example/edit', 'name': 'edit', 'source_path': 'skills/edit',
                   'entrypoint_sha256': digest(self.folder / 'SKILL.md'),
                   'content_sha256': content_digest(self.folder)}
        write_json(self.root / 'skills/library.json', {'schema_version': '1.0', 'install_root': '.tools/library',
                   'groups': [], 'sources': [{'key': 'example', 'repo': 'example/skills', 'commit': 'a' * 40,
                                              'license': 'MIT', 'packages': [package]}]})

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_is_pinned_and_detects_reference_changes(self):
        frozen = snapshot('example/edit', self.root)
        self.assertEqual(frozen['version'], 'a' * 40)
        self.assertEqual(frozen['files']['references/timing.md'], 'Pinned timing rules')
        (self.folder / 'references/timing.md').write_text('Unreviewed source change', encoding='utf-8')
        self.assertEqual(inventory(self.root, full=True)['packages'][0]['status'], 'modified')
        with self.assertRaisesRegex(EditorError, 'modified'):
            snapshot('example/edit', self.root)
        self.assertEqual(frozen['files']['references/timing.md'], 'Pinned timing rules')

    def test_missing_package_is_reported_without_installing_or_writing(self):
        (self.folder / 'SKILL.md').unlink()
        self.assertEqual(inventory(self.root, full=True)['packages'][0]['status'], 'missing')
        with self.assertRaisesRegex(EditorError, 'install_skill_library'):
            snapshot('example/edit', self.root)
        self.assertFalse((self.folder / 'SKILL.md').exists())
        with self.assertRaisesRegex(EditorError, 'Unknown upstream'):
            snapshot('example/unknown', self.root)


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / '.test-output'
        base.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='comparison-', dir=base)
        cls.root = Path(cls.temp.name).resolve()
        assert cls.root.is_relative_to(base.resolve()) and cls.root != base.resolve()
        cls.source = cls.root / 'source.mp4'
        result = subprocess.run([executable('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
                                 'color=red:s=160x90:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(cls.source)], capture_output=True)
        if result.returncode:
            raise AssertionError(result.stderr.decode(errors='replace'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_independent_drafts_share_input_and_format_without_approval_or_render(self):
        from core.comparisons import create_comparison, comparison_view
        source_hash = digest(self.source)
        with patch('core.comparisons.ROOT', self.root), patch('core.jobs.ROOT', self.root):
            folder = create_comparison('variants', self.source, ['melvynx-raw-vi', 'motion-catalog-vi'],
                                       '<script>private brief</script>', 'horizontal')
            manifest = read_json(folder / 'comparison.json')
            self.assertEqual(manifest['status'], 'drafts')
            self.assertEqual(manifest['source_sha256'], source_hash)
            for variant in manifest['variants']:
                job = self.root / 'jobs' / variant['job_id']
                self.assertEqual(digest(job / 'input/raw.mp4'), source_hash)
                revision = job / 'revisions/r001'
                plan = read_json(revision / 'edit-plan.json')
                self.assertEqual((plan['export']['width'], plan['export']['height'], plan['fps']), (1920, 1080, 30))
                self.assertFalse(plan['captions']['enabled'])
                self.assertEqual(read_json(revision / 'decisions.json')['setup']['status'], 'pending')
                self.assertFalse((revision / 'renders').exists())
            self.assertEqual(digest(self.source), source_hash)
            self.assertIn('&lt;script&gt;private brief&lt;/script&gt;', (folder / 'index.html').read_text(encoding='utf-8'))
            # Only actual exports are offered; select the newest rendered revision, not a pending one.
            first = self.root / 'jobs' / manifest['variants'][0]['job_id'] / 'revisions'
            (first / 'r002/renders').mkdir(parents=True)
            shutil.copy2(self.source, first / 'r002/renders/video.mp4')
            (first / 'r003').mkdir()
            page = comparison_view('variants').read_text(encoding='utf-8')
            self.assertIn('r002/renders/video.mp4', page)
            self.assertNotIn('r003/renders/video.mp4', page)
            original = (folder / 'comparison.json').read_bytes()
            with self.assertRaisesRegex(EditorError, 'already exists'):
                create_comparison('variants', self.source, ['melvynx-raw-vi', 'motion-catalog-vi'], 'Changed', 'vertical')
            self.assertEqual((folder / 'comparison.json').read_bytes(), original)

    def test_invalid_selection_is_rejected_before_creating_jobs(self):
        from core.comparisons import create_comparison
        with patch('core.comparisons.ROOT', self.root), patch('core.jobs.ROOT', self.root):
            for profiles, output_format in ((['melvynx-raw-vi'] * 2, 'vertical'),
                                            (['melvynx-raw-vi', 'motion-catalog-vi'], 'unknown')):
                with self.assertRaises(EditorError):
                    create_comparison('bad', self.source, profiles, 'Fixture', output_format)
            self.assertFalse((self.root / 'comparisons/bad').exists())


if __name__ == '__main__':
    unittest.main()
