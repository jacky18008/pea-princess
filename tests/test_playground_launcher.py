"""Offline immutable playground snapshots; no servers or model calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import start_playground as launcher


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'source checkout'
        self.root.mkdir()
        self.git('init', '-q')
        for name in launcher.REQUIRED:
            self.write(name, 'Original runtime bytes: ' + name)
        self.write('evals/personas/fixtures/P1/listing.txt', 'Synthetic fixture bytes.')
        self.git('add', '.')
        # Production prompt pack is ignored/untracked, and explicitly named.
        self.git('rm', '--cached', launcher.GENERATED)
        self.archive = self.root / 'dist/pea-princess-skill.zip'
        # These snapshot tests deliberately select a release different from the
        # synthetic controller tree. Default freshness has separate regressions.
        self.make_archive(self.archive)

    def make_archive(self, path, text='Public packaged instructions.'):
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('pea-princess/SKILL.md', '---\nname: pea-princess\n---\n' + text)
            archive.writestr('pea-princess/scripts/public_only.py', 'PUBLIC_VERSION = 1\n')
            archive.writestr('pea-princess/viewer/viewer.html', '<p>Packaged public viewer</p>')

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.root), *args],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        return result.stdout

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def test_current_working_bytes_are_frozen_and_later_changes_do_not_affect_them(self):
        name = 'skills/vet-flat/SKILL.md'
        self.write(name, 'Uncommitted current skill.')
        result = launcher.freeze(self.root, skill_archive=self.archive)
        snapshot = Path(result['snapshot'])
        manifest_bytes = Path(result['manifest']).read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertEqual('Uncommitted current skill.', (snapshot / name).read_text())
        self.write(name, 'Another editor changed the skill.')
        self.assertEqual('Uncommitted current skill.', (snapshot / name).read_text())
        self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), result['manifest_sha256'])
        self.assertEqual(hashlib.sha256((snapshot / name).read_bytes()).hexdigest(),
                         manifest['files'][name]['sha256'])
        self.assertEqual('generated-runtime-input', manifest['files'][launcher.GENERATED]['origin'])
        self.assertTrue((snapshot / 'evals/personas/fixtures/P1/listing.txt').is_file())
        self.assertEqual(self.root / '.pea-playground', Path(result['state_dir']))
        public = snapshot / 'skills/pea-princess'
        self.assertIn('Public packaged instructions.', (public / 'SKILL.md').read_text())
        self.assertNotIn('Uncommitted current skill.', (public / 'SKILL.md').read_text())
        self.assertTrue((public / 'viewer/viewer.html').is_file())
        self.assertEqual(self.archive.read_bytes(), (snapshot / launcher.playground_skill.ARCHIVE_PATH).read_bytes())
        self.assertEqual('public_zip', result['public_skill']['kind'])
        self.assertEqual(3, manifest['public_skill']['file_count'])
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), result['public_skill']['sha256'])
        self.assertEqual(public, launcher.playground_skill.skill_root(snapshot))

    def test_untracked_private_and_symlink_files_are_excluded(self):
        excluded = ('tools/untracked.py', 'tools/.env', 'bench/private/history.txt',
                    'evals/runtime/session.json', 'skills/vet-flat/secrets.yaml',
                    '.pea-state/events.json', 'dist/private-package.txt',
                    'docs/personal-note.md')
        for name in excluded:
            self.write(name, 'Do not copy this.')
        self.git('add', 'tools/.env', 'bench/private/history.txt', 'evals/runtime/session.json',
                 'skills/vet-flat/secrets.yaml', '.pea-state/events.json',
                 'dist/private-package.txt', 'docs/personal-note.md')
        link = self.root / 'tools/linked.py'
        link.symlink_to(self.root / 'docs/personal-note.md')
        self.git('add', 'tools/linked.py')
        result = launcher.freeze(self.root, skill_archive=self.archive)
        snapshot = Path(result['snapshot'])
        for name in excluded + ('tools/linked.py',):
            self.assertFalse((snapshot / name).exists(), name)
        self.assertFalse(list((self.root / '.pea-playground').glob('*/session.json')))

    def test_source_change_during_freeze_fails_without_publishing_snapshot(self):
        original = launcher.read_source
        calls = {}
        changed = 'tools/persona_playground.py'
        def changing(root, name):
            calls[name] = calls.get(name, 0) + 1
            if name == changed and calls[name] == 2:
                self.write(name, 'Changed while snapshot was being prepared.')
            return original(root, name)
        with mock.patch.object(launcher, 'read_source', side_effect=changing):
            with self.assertRaisesRegex(launcher.FreezeError, 'changed during freeze'):
                launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))

    def test_required_symlink_or_missing_file_is_rejected_before_startup(self):
        file = self.root / 'tools/persona_playground.py'
        file.unlink()
        file.symlink_to(self.root / 'tools/session_runner.py')
        with self.assertRaisesRegex(launcher.FreezeError, 'Required runtime files unavailable'):
            launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))

    def test_existing_session_bytes_and_limits_remain_unchanged_and_argv_is_literal(self):
        session = self.write('.pea-playground/0123456789abcdef0123456789abcdef/session.json',
                             '{"limits":{"max_calls":2},"calls":[{},{}]}')
        before = session.read_bytes()
        result = launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual(before, session.read_bytes())
        command = launcher.server_command(result['snapshot'], result['state_dir'], 8765,
                                           python='/literal/path with spaces/python')
        self.assertEqual(['/literal/path with spaces/python', '-B',
                          str(Path(result['snapshot']) / 'tools/persona_playground.py'),
                          '--state-dir', str(self.root / '.pea-playground'), '--port', '8765'], command)
        self.assertFalse((Path(result['snapshot']) / '.pea-playground').exists())

    def test_explicit_public_archive_is_used_without_rebuilding_default(self):
        default_before = self.archive.read_bytes()
        selected = self.root / 'selected release.zip'
        self.make_archive(selected, text='Explicit selected release.')
        result = launcher.freeze(self.root, skill_archive=selected)
        snapshot = Path(result['snapshot'])
        self.assertIn('Explicit selected release.', (snapshot / 'skills/pea-princess/SKILL.md').read_text())
        self.assertEqual(default_before, self.archive.read_bytes())
        self.assertEqual(selected.read_bytes(), (snapshot / launcher.playground_skill.ARCHIVE_PATH).read_bytes())

    def test_missing_or_changing_public_archive_fails_without_publishing(self):
        self.archive.unlink()
        with self.assertRaises(launcher.FreezeError):
            launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))
        self.make_archive(self.archive)
        original = launcher.playground_skill.install_archive
        def changing(bundle, root):
            result = original(bundle, root)
            self.make_archive(self.archive, text='Changed during freeze.')
            return result
        with mock.patch.object(launcher.playground_skill, 'install_archive', side_effect=changing):
            with self.assertRaisesRegex(launcher.FreezeError, 'changed during freeze'):
                launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))


if __name__ == '__main__':
    unittest.main()
