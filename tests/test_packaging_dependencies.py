"""Local import omissions stop public builds without changing prior releases."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dependency_build_dist', ROOT / 'tools/build_dist.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageDependencyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.write('SKILL.md', '---\nname: pea-princess\n---\nSynthetic skill\n')
        self.write('references/rules.md', '# Defaults, and the four things that do not move\nRules.\n')
        self.write('references/inputs.md', '## Rules for asking\nAsk once.\n## What to ask for\n')
        self.write('references/report-contract.md', '## The fixed form\nAll rows.\n## Plain-language rules\n')
        self.write('scripts/area_scan.py', 'def main():\n    return 1\n')
        self.track('.')
        patch = mock.patch.multiple(builder, ROOT=str(self.root),
                                    SKILL=str(self.root / 'skills/vet-flat'), DIST=str(self.root / 'dist'))
        patch.start()
        self.addCleanup(patch.stop)
        self.build()
        self.before = self.release_bytes()

    def write(self, name, text):
        path = self.root / 'skills/vet-flat' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def track(self, *names):
        paths = [name if name == '.' else 'skills/vet-flat/' + name for name in names]
        subprocess.run(['git', '-C', str(self.root), 'add', '--'] + paths, check=True)

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            builder.main()

    def release_bytes(self):
        return {str(path.relative_to(self.root / 'dist')): path.read_bytes()
                for path in (self.root / 'dist').rglob('*') if path.is_file()}

    def assert_omitted(self, expected):
        with self.assertRaisesRegex(ValueError, expected):
            self.build()
        self.assertEqual(self.before, self.release_bytes())
        self.assertEqual([], list((self.root / 'dist').glob('.public-build-*')))

    def test_function_local_noise_import_is_rejected_without_adding_untracked_file(self):
        self.write('scripts/area_scan.py', 'def main():\n    import noise as noise_mod\n    return noise_mod.scan()\n')
        self.write('scripts/noise.py', 'PRIVATE_UNREVIEWED = True\n')
        self.assert_omitted('area_scan.py.*noise.py')
        self.assertNotIn('skills/vet-flat/scripts/noise.py',
                         builder.tracked_files(str(self.root), ['skills/vet-flat']))

    def test_all_packaged_nested_imports_succeed_without_executing_scripts(self):
        self.write('scripts/area_scan.py',
                   'raise RuntimeError("must not execute")\ndef main():\n    import noise as n\n    from _fetch import now_iso\n')
        self.write('scripts/noise.py', 'def scan():\n    from _fetch import now_iso\n')
        self.write('scripts/_fetch.py', 'def now_iso():\n    return "synthetic"\n')
        self.track('scripts/noise.py', 'scripts/_fetch.py')
        self.build()
        with zipfile.ZipFile(self.root / 'dist' / builder.ARCHIVE_NAME) as archive:
            self.assertIn('pea-princess/scripts/noise.py', archive.namelist())
            self.assertIn('pea-princess/scripts/_fetch.py', archive.namelist())

    def test_from_package_import_checks_present_submodule_not_function_names(self):
        self.write('scripts/area_scan.py', 'from helpers import local, existing_function\n')
        self.write('scripts/helpers/__init__.py', 'existing_function = None\n')
        self.write('scripts/helpers/local.py', 'VALUE = 1\n')
        self.track('scripts/helpers/__init__.py')
        self.assert_omitted('helpers/local.py')
        self.track('scripts/helpers/local.py')
        self.build()

    def test_missing_package_initializer_is_not_silently_removed(self):
        self.write('scripts/area_scan.py', 'import helpers.local as local\n')
        self.write('scripts/helpers/__init__.py', 'raise RuntimeError("do not execute")\n')
        self.write('scripts/helpers/local.py', 'VALUE = 1\n')
        self.track('scripts/helpers/local.py')
        self.assert_omitted('helpers/__init__.py')

    def test_relative_nested_import_and_transitive_dependency_are_checked(self):
        self.write('scripts/area_scan.py', 'import helpers.local\n')
        self.write('scripts/helpers/__init__.py', '')
        self.write('scripts/helpers/local.py', 'def scan():\n    from . import missing\n')
        self.write('scripts/helpers/missing.py', 'VALUE = 1\n')
        self.track('scripts/helpers/__init__.py', 'scripts/helpers/local.py')
        self.assert_omitted('helpers/local.py.*helpers/missing.py')

    def test_excluded_namespace_package_is_not_auto_included(self):
        self.write('scripts/area_scan.py', 'def main():\n    import results.private_data\n')
        self.write('scripts/results/private_data.py', 'PRIVATE = True\n')
        self.track('scripts/results/private_data.py')
        self.assert_omitted('scripts/results')

    def test_nonlocal_imports_are_not_guessed_or_executed(self):
        self.write('scripts/area_scan.py', 'import json\nfrom pathlib import Path\nimport nonexistent_external_module\n')
        self.build()

    def test_invalid_python_stops_before_touching_existing_release(self):
        self.write('scripts/area_scan.py', 'def broken(\n')
        with self.assertRaises(SyntaxError):
            self.build()
        self.assertEqual(self.before, self.release_bytes())


if __name__ == '__main__':
    unittest.main()
