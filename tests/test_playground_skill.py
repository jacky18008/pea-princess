"""Exact public ZIP identity, extraction boundaries and frozen-runtime checks."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import playground_skill as skill


PUBLIC_SKILL = b"---\nname: pea-princess\n---\nPublic instructions.\n"


class PublicSkillTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.archive = self.root / "public release.zip"

    def package(self, extra=(), instruction=PUBLIC_SKILL):
        rows = [("pea-princess/SKILL.md", instruction),
                ("pea-princess/scripts/check.py", b"VALUE = 'public'\n"),
                ("pea-princess/viewer/viewer.html", b"<p>Exact viewer bytes\x00</p>")]
        rows.extend(extra)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, raw in rows:
                    archive.writestr(name, raw)
        return self.archive

    def frozen(self, extra=()):
        self.package(extra)
        bundle = skill.load_archive(self.archive)
        root = self.root / "frozen"
        root.mkdir(mode=0o700)
        identity = skill.install_archive(bundle, root)
        manifest = root / skill.MANIFEST
        manifest.write_text(json.dumps({"schema_version": 1, "public_skill": identity}))
        manifest.chmod(0o400)
        return root, identity

    def alter(self, path, raw):
        path.chmod(0o600)
        path.write_bytes(raw)
        path.chmod(0o400)

    def test_exact_zip_tree_bytes_identity_and_private_permissions(self):
        root, identity = self.frozen(extra=[("pea-princess/empty/", b"")])
        info = skill.artifact_info(root)
        self.assertEqual("public_zip", info["kind"])
        self.assertEqual("pea-princess", info["name"])
        self.assertEqual(3, info["file_count"])
        self.assertNotIn("files", info)
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), info["sha256"])
        self.assertEqual(self.archive.read_bytes(), (root / skill.ARCHIVE_PATH).read_bytes())
        self.assertEqual(root / skill.SKILL_PATH, skill.skill_root(root))
        with zipfile.ZipFile(self.archive) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename[len("pea-princess/"):]
                path = root / skill.SKILL_PATH / name
                self.assertEqual(archive.read(entry), path.read_bytes())
                self.assertEqual(identity["files"][name]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(0o400, stat.S_IMODE(path.stat().st_mode))
        self.assertEqual(0o500, stat.S_IMODE((root / skill.SKILL_PATH).stat().st_mode))
        self.assertEqual(0o500, stat.S_IMODE((root / skill.SKILL_PATH / "scripts").stat().st_mode))
        with self.assertRaises(PermissionError):
            (root / skill.SKILL_PATH / "scripts/__pycache__").mkdir()

    def test_archive_and_extracted_files_do_not_change_when_original_changes(self):
        root, _ = self.frozen()
        before = skill.artifact_info(root)
        self.package(instruction=b"---\nname: pea-princess\n---\nChanged release\n")
        self.assertEqual(before, skill.artifact_info(root))

    def test_source_change_during_freeze_and_archive_symlinks_are_rejected(self):
        self.package()
        bundle = skill.load_archive(self.archive)
        self.package(instruction=PUBLIC_SKILL + b"changed")
        with self.assertRaisesRegex(skill.PublicSkillError, "changed during freeze"):
            skill.verify_source(bundle)
        link = self.root / "link.zip"
        link.symlink_to(self.archive)
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(link)
        fifo = self.root / "pipe.zip"
        os.mkfifo(fifo)
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(fifo)

    def test_public_name_must_be_declared_once_without_aliasing(self):
        for raw in (b"no frontmatter", b"---\nname: vet-flat\n---\nPrivate old identity",
                    b"---\nname: pea-princess\nname: pea-princess\n---\n", b"---\nname: [pea-princess]\n---\n",
                    b"---\nname: &alias pea-princess\n---\n"):
            self.package(instruction=raw)
            with self.subTest(raw=raw), self.assertRaises(skill.PublicSkillError):
                skill.load_archive(self.archive)

    def test_traversal_wrong_roots_and_ambiguous_paths_are_rejected(self):
        names = ["../outside", "/pea-princess/outside", "vet-flat/SKILL.md", "pea-princess/../outside",
                 "pea-princess/a/../../outside", "pea-princess//double.md", "pea-princess/./dot.md",
                 "pea-princess/back\\slash.md", "pea-princess/C:/outside", "pea-princess/bad\nname.md",
                 "pea-princess/bad\u0085name.md", "pea-princess/dot./file", "pea-princess/space /file"]
        for name in names:
            self.package([(name, b"unsafe")])
            with self.subTest(name=name), self.assertRaises(skill.PublicSkillError):
                skill.load_archive(self.archive)
        self.assertFalse((self.root / "outside").exists())

    def test_duplicate_case_unicode_and_file_directory_collisions_are_rejected(self):
        pairs = [[("pea-princess/SKILL.md", PUBLIC_SKILL)],
                 [("pea-princess/Ref.md", b"a"), ("pea-princess/ref.md", b"b")],
                 [("pea-princess/Refs/a.md", b"a"), ("pea-princess/refs/b.md", b"b")],
                 [("pea-princess/caf\u00e9.md", b"a"), ("pea-princess/cafe\u0301.md", b"b")],
                 [("pea-princess/node", b"a"), ("pea-princess/node/child", b"b")]]
        for extra in pairs:
            self.package(extra)
            with self.subTest(extra=extra), self.assertRaises(skill.PublicSkillError):
                skill.load_archive(self.archive)

    def test_symlinks_devices_and_malformed_directory_attributes_are_rejected(self):
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o600, stat.S_IFCHR | 0o600, stat.S_IFDIR | 0o700):
            info = zipfile.ZipInfo("pea-princess/unsafe")
            info.create_system = 3
            info.external_attr = mode << 16
            self.package([(info, b"target")])
            with self.subTest(mode=mode), self.assertRaises(skill.PublicSkillError):
                skill.load_archive(self.archive)

    def test_nul_truncated_member_names_are_rejected(self):
        self.package([("pea-princess/badXfile.txt", b"content")])
        self.archive.write_bytes(self.archive.read_bytes().replace(b"badXfile.txt", b"bad\x00file.txt"))
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)

    def test_archive_file_total_and_entry_limits_fail_before_extraction(self):
        self.package([("pea-princess/large.txt", b"x" * 129)])
        with mock.patch.object(skill, "MAX_FILE_BYTES", 128), self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)
        with mock.patch.object(skill, "MAX_TOTAL_BYTES", 128), self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)
        with mock.patch.object(skill, "MAX_ENTRIES", 2), self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)
        with mock.patch.object(skill, "MAX_ARCHIVE_BYTES", 128), self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)

    def test_invalid_encryption_compression_and_crc_fail(self):
        self.package()
        raw = bytearray(self.archive.read_bytes())
        local, central = raw.index(b"PK\x03\x04"), raw.index(b"PK\x01\x02")
        raw[local + 6] |= 1
        raw[central + 8] |= 1
        self.archive.write_bytes(raw)
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)
        self.package()
        raw = bytearray(self.archive.read_bytes())
        central = raw.index(b"PK\x01\x02")
        raw[central + 16] ^= 1  # Alter the recorded CRC without changing bytes.
        self.archive.write_bytes(raw)
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)
        self.archive.write_bytes(b"not a zip")
        with self.assertRaises(skill.PublicSkillError):
            skill.load_archive(self.archive)

    def test_missing_manifest_and_missing_public_identity_never_fall_back(self):
        root, _ = self.frozen()
        legacy = root / "skills/vet-flat"
        legacy.mkdir()
        (legacy / "SKILL.md").write_bytes(PUBLIC_SKILL)
        manifest = root / skill.MANIFEST
        manifest.unlink()
        with self.assertRaises(skill.PublicSkillError):
            skill.artifact_info(root)
        manifest.write_text('{"schema_version":1}')
        manifest.chmod(0o400)
        with self.assertRaisesRegex(skill.PublicSkillError, "no public skill"):
            skill.skill_root(root)

    def test_manifest_mismatch_and_boolean_counts_are_rejected(self):
        root, _ = self.frozen()
        path = root / skill.MANIFEST
        original = json.loads(path.read_bytes())
        for key, value in (("archive_sha256", "0" * 64), ("skill_path", "skills/vet-flat"), ("schema_version", True), ("file_count", 2)):
            changed = copy.deepcopy(original)
            changed["public_skill"][key] = value
            self.alter(path, json.dumps(changed).encode())
            with self.subTest(key=key), self.assertRaises(skill.PublicSkillError):
                skill.artifact_info(root)

    def test_modified_missing_extra_or_symlinked_public_files_are_detected(self):
        root, _ = self.frozen()
        path = root / skill.SKILL_PATH / "scripts/check.py"
        original = path.read_bytes()
        self.alter(path, original + b"altered")
        with self.assertRaises(skill.PublicSkillError):
            skill.artifact_info(root)
        self.alter(path, original)
        path.parent.chmod(0o700)
        path.unlink()
        with self.assertRaises(skill.PublicSkillError):
            skill.artifact_info(root)
        path.symlink_to(self.archive)
        with self.assertRaises(skill.PublicSkillError):
            skill.artifact_info(root)
        path.unlink()
        path.write_bytes(original)
        path.chmod(0o400)
        extra = path.with_name("private-extra.py")
        extra.write_text("must not be present")
        with self.assertRaisesRegex(skill.PublicSkillError, "exactly"):
            skill.artifact_info(root)

    def test_retained_zip_mutation_is_detected_without_source_reloads(self):
        root, _ = self.frozen()
        self.alter(root / skill.ARCHIVE_PATH, b"broken archive")
        with self.assertRaises(skill.PublicSkillError):
            skill.artifact_info(root)

    def test_development_is_explicit_and_has_no_public_archive_hash(self):
        development = self.root / "development"
        path = development / "skills/vet-flat"
        path.mkdir(parents=True)
        (path / "SKILL.md").write_bytes(PUBLIC_SKILL)
        info = skill.artifact_info(development)
        self.assertEqual("development", info["kind"])
        self.assertIsNone(info["sha256"])
        self.assertEqual(path, skill.skill_root(development))


if __name__ == "__main__":
    unittest.main()
