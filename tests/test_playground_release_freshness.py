"""Default releases match indexed working bytes; explicit history stays opt-in."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import start_playground as launcher


class ReleaseFreshnessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'source'
        self.root.mkdir()
        self.git('init', '-q')
        for name in launcher.REQUIRED:
            self.write(name, 'Synthetic controller: ' + name)
        self.write('skills/vet-flat/SKILL.md', '---\nname: pea-princess\n---\nCurrent public skill.\n')
        self.write('viewer/viewer.html', '<p>Current viewer</p>')
        self.git('add', '.')
        self.git('rm', '--cached', launcher.GENERATED)
        self.archive = self.root / 'dist/pea-princess-skill.zip'
        self.pack_current()
        self.previous_zip = self.archive.read_bytes()
        self.session = self.write('.pea-playground/old/session.json', 'Saved historical session bytes.')

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.root), *args], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def pack_current(self):
        self.archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for full, rel in launcher.build_dist.public_members(self.root):
                short = rel[len('skills/vet-flat/'):] if rel.startswith('skills/vet-flat/') else rel
                archive.write(full, 'pea-princess/' + short)

    def assert_stale(self, reason):
        with self.assertRaisesRegex(launcher.FreezeError, reason):
            launcher.freeze(self.root)
        self.assertEqual(self.previous_zip, self.archive.read_bytes())
        self.assertEqual('Saved historical session bytes.', self.session.read_text())
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))

    def test_current_default_succeeds_without_mtime_or_head_dependency(self):
        source = self.root / 'skills/vet-flat/SKILL.md'
        os.utime(source, (100, 100))
        self.write('tools/persona_playground.py', 'New controller; actor package did not change.')
        result = launcher.freeze(self.root)
        manifest = json.loads(Path(result['manifest']).read_bytes())
        self.assertEqual({'mode': 'default_current_source', 'working_source_verified': True},
                         manifest['public_skill_selection'])
        self.assertEqual(self.previous_zip, Path(result['public_skill']['archive_path']).read_bytes())
        self.assertEqual('Saved historical session bytes.', self.session.read_text())

    def test_uncommitted_tracked_skill_change_rejects_stale_default(self):
        self.write('skills/vet-flat/SKILL.md', '---\nname: pea-princess\n---\nUpdated research routing.\n')
        self.assert_stale('changed: SKILL.md')

    def test_new_indexed_member_missing_from_zip_rejects_default(self):
        self.write('skills/vet-flat/scripts/noise.py', 'VALUE = 1\n')
        self.git('add', 'skills/vet-flat/scripts/noise.py')
        self.assert_stale('missing: scripts/noise.py')

    def test_member_removed_from_index_is_not_kept_by_old_zip(self):
        self.git('rm', '--cached', 'viewer/viewer.html')
        self.assert_stale('extra: viewer/viewer.html')

    def test_untracked_local_notes_are_neither_required_nor_added(self):
        self.write('skills/vet-flat/references/local-note.md', 'Private untracked note.')
        result = launcher.freeze(self.root)
        with zipfile.ZipFile(result['public_skill']['archive_path']) as archive:
            self.assertNotIn('pea-princess/references/local-note.md', archive.namelist())

    def test_explicit_selection_can_reuse_older_default_path(self):
        self.write('skills/vet-flat/SKILL.md', '---\nname: pea-princess\n---\nA newer skill.\n')
        result = launcher.freeze(self.root, skill_archive=self.archive)
        manifest = json.loads(Path(result['manifest']).read_bytes())
        self.assertEqual({'mode': 'explicit_archive', 'working_source_verified': None},
                         manifest['public_skill_selection'])
        self.assertEqual(self.previous_zip, Path(result['public_skill']['archive_path']).read_bytes())

    def test_explicit_selection_still_rejects_unsafe_archive(self):
        with zipfile.ZipFile(self.archive, 'a') as archive:
            archive.writestr('pea-princess/../outside.py', 'unsafe')
        with self.assertRaises(launcher.FreezeError):
            launcher.freeze(self.root, skill_archive=self.archive)
        self.assertEqual([], list((self.root / '.pea-playground/runtime').iterdir()))

    def test_source_change_after_initial_check_fails_without_publishing(self):
        install = launcher.playground_skill.install_archive
        def changed(bundle, root):
            result = install(bundle, root)
            self.write('viewer/viewer.html', '<p>Changed during freeze</p>')
            return result
        with mock.patch.object(launcher.playground_skill, 'install_archive', side_effect=changed):
            self.assert_stale('changed: viewer/viewer.html')

    def test_cli_distinguishes_omitted_archive_from_explicit_default_path(self):
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        with mock.patch.object(launcher, 'freeze', return_value={}) as freeze, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, launcher.main(['--freeze-only']))
            self.assertIsNone(freeze.call_args.args[2])
            self.assertEqual(0, launcher.main(['--freeze-only', '--skill-archive', str(self.archive)]))
            self.assertEqual(self.archive, freeze.call_args.args[2])


if __name__ == '__main__':
    unittest.main()
