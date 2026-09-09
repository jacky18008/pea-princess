"""Offline release-boundary regressions; synthetic checkouts and fake secrets only."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


DIST = module('build_dist')
AB = module('build_ab_package')


class PackageBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('skills/vet-flat/SKILL.md', '---\nname: vet-flat\n---\nTest skill\n')
        self.write('skills/vet-flat/references/inputs.md',
                   '## Rules for asking\nAsk once.\n## What to ask for\nInputs.\n')
        self.write('skills/vet-flat/references/report-contract.md',
                   '## The fixed form\nF1 deposit. F18 inventory.\n## Plain-language rules\nPlain text.\n')
        self.write('skills/vet-flat/scripts/calc.py', 'print(1)\n')
        self.write('skills/vet-flat/profile.template.yaml', 'budget: null\n')
        self.write('viewer/viewer.html', '<!doctype html>')
        self.write('bench/ab/CODEX_BRIEF.md', 'Synthetic brief')
        self.write('bench/run.py', 'print(1)\n')
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        self.patches = mock.patch.multiple(DIST, ROOT=str(self.root),
                                          SKILL=str(self.root / 'skills/vet-flat'),
                                          DIST=str(self.root / 'dist'))
        self.patches.start()
        self.ab_patch = mock.patch.object(AB, 'ROOT', str(self.root))
        self.ab_patch.start()

    def tearDown(self):
        self.ab_patch.stop()
        self.patches.stop()
        self.temp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def public_build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            DIST.main()
        with zipfile.ZipFile(self.root / 'dist/vet-flat-skill.zip') as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def test_public_excludes_untracked_notes_and_even_tracked_credentials(self):
        self.write('skills/vet-flat/references/private-notes.md', 'PRIVATE_SENTINEL')
        for rel in ('scripts/.env', 'scripts/.cache/response.json', 'profile.yaml'):
            self.write('skills/vet-flat/' + rel, 'SECRET_SENTINEL')
        subprocess.run(['git', '-C', str(self.root), 'add', '-f', 'skills/vet-flat/scripts/.env',
                        'skills/vet-flat/profile.yaml'], check=True)
        files = self.public_build()
        self.assertIn('vet-flat/scripts/calc.py', files)
        self.assertIn('vet-flat/viewer/viewer.html', files)
        self.assertNotIn(b'SECRET_SENTINEL', b''.join(files.values()))
        self.assertNotIn(b'PRIVATE_SENTINEL', b''.join(files.values()))
        pack = self.root / 'dist/prompt-pack'
        self.assertFalse((pack / 'references/private-notes.md').exists())
        self.assertTrue((pack / 'references/inputs.md').is_file())

    def test_symlink_file_and_parent_refused_before_existing_release_changes(self):
        self.public_build()
        before = (self.root / 'dist/vet-flat-skill.zip').read_bytes()
        external = self.write('outside.txt', 'SECRET_SENTINEL')
        link = self.root / 'skills/vet-flat/references/link.txt'
        link.symlink_to(external)
        subprocess.run(['git', '-C', str(self.root), 'add', str(link)], check=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.public_build()
        self.assertEqual(before, (self.root / 'dist/vet-flat-skill.zip').read_bytes())
        link.unlink()
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            DIST.checked_file(str(self.root), '../outside.txt')
        directory = self.root / 'skills/vet-flat/references'
        directory.rename(directory.with_name('real-references'))
        directory.symlink_to(directory.with_name('real-references'), target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            DIST.checked_file(str(self.root), 'skills/vet-flat/references/inputs.md')

    def test_public_build_preserves_private_bundle_but_does_not_checksum_it(self):
        private = self.write('dist/private-handoff.tar.gz', 'PRIVATE_SENTINEL')
        self.public_build()
        self.assertEqual('PRIVATE_SENTINEL', private.read_text())
        checksums = (self.root / 'dist/CHECKSUMS.txt').read_text()
        self.assertNotIn('private-handoff', checksums)
        self.assertIn('vet-flat-skill.zip', checksums)

    def test_required_digest_cannot_be_silently_dropped_to_fit(self):
        with self.assertRaisesRegex(ValueError, 'cannot be dropped'):
            DIST.compose_instructions(limit=100)
        (self.root / 'skills/vet-flat/references/report-contract.md').unlink()
        with self.assertRaisesRegex(ValueError, 'required manual digest section missing'):
            DIST.compose_instructions()

    def test_untracked_digest_refused_instead_of_embedded(self):
        self.write('skills/vet-flat/references/arithmetic.md',
                   '## Without a shell\nPRIVATE_SENTINEL\n## Constants\n')
        with self.assertRaisesRegex(ValueError, 'digest source'):
            self.public_build()

    def test_private_bundle_includes_only_intended_private_tree_and_is_owner_only(self):
        self.write('bench/private/gold.json', '{"synthetic": true}')
        self.write('bench/private/.env', 'SECRET_SENTINEL')
        self.write('bench/private/.cache/cached.json', 'SECRET_SENTINEL')
        self.write('bench/local-notes.txt', 'PRIVATE_UNINTENDED')
        self.write('bench/results/old/report.json', 'PRIVATE_UNINTENDED')
        out = self.root / 'handoff/private.tar.gz'
        with contextlib.redirect_stdout(io.StringIO()):
            AB.build(str(out))
        self.assertEqual(0o700, stat.S_IMODE(out.parent.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE(out.stat().st_mode))
        self.assertFalse((out.parent / '.README-CODEX.md.tmp').exists())
        with tarfile.open(out) as archive:
            members = archive.getmembers()
            self.assertIn('pea-princess-ab/bench/private/gold.json', archive.getnames())
            self.assertTrue(all(m.isfile() and m.mode & 0o077 == 0 for m in members))
            contents = b''.join(archive.extractfile(m).read() for m in members)
        self.assertNotIn(b'SECRET_SENTINEL', contents)
        self.assertNotIn(b'PRIVATE_UNINTENDED', contents)

    def test_public_invalid_output_type_preserves_existing_prompt_pack(self):
        self.public_build()
        sentinel = self.write('dist/prompt-pack/sentinel.txt', 'KEEP')
        output = self.root / 'dist/vet-flat-skill.zip'
        output.unlink()
        output.mkdir()
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.public_build()
        self.assertEqual('KEEP', sentinel.read_text())

    def test_public_promotion_failure_rolls_back_previous_release(self):
        self.public_build()
        before = {p.relative_to(self.root / 'dist').as_posix(): p.read_bytes()
                  for p in (self.root / 'dist').rglob('*') if p.is_file()}
        original = os.replace
        def fail_new_zip(source, destination):
            if Path(source).name == 'vet-flat-skill.zip' and Path(source).parent.name.startswith('.public-build-'):
                raise OSError('synthetic promotion failure')
            return original(source, destination)
        with mock.patch.object(DIST.os, 'replace', side_effect=fail_new_zip):
            with self.assertRaisesRegex(OSError, 'synthetic promotion'):
                self.public_build()
        after = {p.relative_to(self.root / 'dist').as_posix(): p.read_bytes()
                 for p in (self.root / 'dist').rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_private_rejects_parent_link_before_mkdir_and_rejects_fifo(self):
        self.write('bench/private/gold.json', '{}')
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'alias').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            AB.build(str(self.root / 'alias/new-child/archive.tar.gz'))
        self.assertFalse((outside / 'new-child').exists())
        fifo = self.root / 'archive.tar.gz'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            AB.build(str(fifo))
        self.assertTrue(stat.S_ISFIFO(fifo.stat().st_mode))

    def test_private_symlink_refused_without_overwriting_target(self):
        self.write('bench/private/gold.json', '{}')
        target = self.write('existing.txt', 'KEEP')
        output = self.root / 'out.tar.gz'
        output.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            AB.build(str(output))
        self.assertEqual('KEEP', target.read_text())
        output.unlink()
        self.write('bench/private/data.txt', 'ok').unlink()
        (self.root / 'bench/private/data.txt').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            AB.build(str(output))
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
