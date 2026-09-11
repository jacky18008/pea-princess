"""Selected-file snapshots stay bounded, private, inert and byte-identical."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import playground_attachments as attachments


class AttachmentStorage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = attachments.AttachmentStore(self.root / "lab")

    def upload(self, raw=b"exact\x00\xffbytes\r\n", name="evidence.pdf", store=None):
        return (store or self.store).ingest({"name": name, "content_base64": base64.b64encode(raw).decode("ascii")})

    def alter(self, path, raw):
        path = Path(path)
        path.chmod(0o600)
        path.write_bytes(raw)
        path.chmod(0o400)

    def metadata_path(self, metadata):
        return Path(metadata["stored_path"]).parent / "metadata.json"

    def test_exact_upload_bytes_private_permissions_and_persistence(self):
        raw = bytes(range(256)) + b"\r\n\x00"
        metadata = self.upload(raw, "Photo.PDF")
        self.assertEqual(len(raw), metadata["bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata["sha256"])
        self.assertEqual(".pdf", metadata["extension"])
        self.assertEqual(raw, Path(metadata["stored_path"]).read_bytes())
        self.assertEqual(0o400, stat.S_IMODE(Path(metadata["stored_path"]).stat().st_mode))
        self.assertEqual(0o400, stat.S_IMODE(self.metadata_path(metadata).stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE(self.store.path.stat().st_mode))
        self.assertEqual([metadata], attachments.AttachmentStore(self.store.root).resolve([metadata["id"]]))
        metadata["name"] = "changed returned dictionary"
        self.assertEqual("Photo.PDF", self.store.resolve([metadata["id"]])[0]["name"])

    def test_names_are_inert_and_storage_names_are_opaque(self):
        name = "$(touch not-a-command); document.sh"
        metadata = self.upload(b"#!/bin/sh\necho inert", name)
        self.assertEqual(name, metadata["name"])
        self.assertEqual("data.sh", Path(metadata["stored_path"]).name)
        copied = self.store.materialize([metadata["id"]], self.root / "actor")[0]
        self.assertEqual(metadata["id"] + ".sh", Path(copied["copy_path"]).name)
        self.assertEqual(0, Path(copied["copy_path"]).stat().st_mode & 0o111)
        self.assertFalse((self.root / "not-a-command").exists())

    def test_path_like_names_cannot_escape_store(self):
        for name in ("../escape", "/absolute", "a/b", "a\\b", ".", "..", "", "bad\x00name", "bad\nname", "notes\u0085.pdf", "notes\u009f.pdf", "x" * 256, "é" * 128):
            with self.subTest(name=name), self.assertRaises(attachments.AttachmentError):
                self.upload(name=name)
        self.assertEqual([], list(self.store.path.iterdir()))

    def test_local_paths_urls_home_and_finder_quoting(self):
        source = self.root / "選擇 document's file.txt"
        source.write_bytes(b"local bytes\x00\xff")
        paths = [str(source), source.as_uri(), "file://localhost" + source.as_uri()[7:], shlex.quote(str(source)), str(source).replace(" ", "\\ ").replace("'", "\\'")]
        with mock.patch.object(Path, "home", return_value=self.root):
            paths.append("~/" + source.name)
            for path in paths:
                with self.subTest(path=path):
                    metadata = self.store.ingest({"path": path})
                    self.assertEqual(source.read_bytes(), Path(metadata["stored_path"]).read_bytes())
                    self.assertEqual(str(source), metadata["original_path"])
        source.unlink()
        self.assertEqual(metadata, self.store.resolve([metadata["id"]])[0])

    def test_source_symlink_is_explicitly_supported_and_descriptor_is_pinned(self):
        first, second, selected = (self.root / name for name in ("first.txt", "second.txt", "selected.txt"))
        first.write_bytes(b"first selected bytes")
        second.write_bytes(b"other bytes")
        selected.symlink_to(first)
        original_read = attachments._read
        def swap_after_open(fd, limit, retained=False):
            if not retained:
                selected.unlink()
                selected.symlink_to(second)
            return original_read(fd, limit, retained)
        with mock.patch.object(attachments, "_read", side_effect=swap_after_open):
            metadata = self.store.ingest({"path": str(selected)})
        self.assertEqual(first.read_bytes(), Path(metadata["stored_path"]).read_bytes())
        self.assertEqual(str(selected), metadata["original_path"])

    def test_invalid_local_paths_and_nonregular_files_are_rejected(self):
        fifo = self.root / "pipe.txt"
        os.mkfifo(fifo)
        loop = self.root / "loop.txt"
        loop.symlink_to(loop)
        for path in (str(self.root), str(fifo), str(loop), "/dev/null", "relative.txt", "$HOME/file.txt", "file://remote.example/etc/passwd", "file:///tmp/a?query=yes", "file:///tmp/a#fragment", "file:///tmp/a%00b", "/tmp/\x00bad", "x" * 8193):
            with self.subTest(path=path), self.assertRaises(attachments.AttachmentError):
                self.store.ingest({"path": path})

    def test_invalid_upload_shape_encoding_and_byte_limits(self):
        store = attachments.AttachmentStore(self.root / "tiny", max_bytes=4)
        for payload in (None, [], {}, {"path": str(self.root), "name": "x"}, {"name": "x", "content_base64": "YQ==", "stored_path": "/tmp/x"}, {"name": "x", "content_base64": True}, {"name": "x", "content_base64": "%%%="}, {"name": "x", "content_base64": "YQ==\n"}, {"name": "x", "content_base64": "☃"}):
            with self.subTest(payload=payload), self.assertRaises(attachments.AttachmentError):
                store.ingest(payload)
        self.assertEqual(4, self.upload(b"1234", store=store)["bytes"])
        self.assertEqual(0, self.upload(b"", store=store)["bytes"])
        with self.assertRaises(attachments.AttachmentError):
            self.upload(b"12345", store=store)
        source = self.root / "large.txt"
        source.write_bytes(b"12345")
        with self.assertRaises(attachments.AttachmentError):
            store.ingest({"path": str(source)})
        source.write_bytes(b"1234")
        self.assertEqual(4, store.ingest({"path": str(source)})["bytes"])

    def test_local_path_controls_and_handoff_length_are_rejected_before_open(self):
        # Controls in parent components also reach original_path provenance;
        # rejecting only the final filename would fail later at actor dispatch.
        invalid = [str(self.root / ("parent" + control) / "notes.pdf")
                   for control in ("\n", "\x7f", "\u0085", "\u009f")]
        invalid += [(self.root / "parent\u0085" / "notes.pdf").as_uri(), "/" + "a" * 4096]
        with mock.patch.object(os, "open", side_effect=AssertionError("invalid paths must fail before opening")):
            for path in invalid:
                with self.subTest(path=path), self.assertRaises(attachments.AttachmentError):
                    self.store.ingest({"path": path})
            with mock.patch.object(Path, "home", return_value=Path("/" + "a" * 4095)):
                with self.assertRaises(attachments.AttachmentError):
                    self.store.ingest({"path": "~/notes.pdf"})
        self.assertEqual(4096, len(str(attachments._paths("/" + "a" * 4095)[0])))

    def test_default_25_mib_limit_rejects_sparse_oversize_before_reading(self):
        source = self.root / "large.pdf"
        with source.open("wb") as stream:
            stream.truncate(attachments.MAX_ATTACHMENT_BYTES + 1)
        with mock.patch.object(os, "fdopen", side_effect=AssertionError("oversize bytes must not be read")):
            with self.assertRaises(attachments.AttachmentError):
                self.store.ingest({"path": str(source)})

    def test_source_mutation_during_read_is_rejected(self):
        source = self.root / "changing.txt"
        source.write_bytes(b"initial")
        original_fstat = os.fstat
        calls = 0
        def mutate(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                source.write_bytes(b"changed and enlarged")
            return original_fstat(fd)
        with mock.patch.object(os, "fstat", side_effect=mutate):
            with self.assertRaises(attachments.AttachmentError):
                self.store.ingest({"path": str(source)})

    def test_ids_cannot_select_arbitrary_paths_or_duplicate_a_message(self):
        metadata = self.upload()
        for ids in (metadata["id"], None, ["../outside"], ["/etc/passwd"], ["a" * 31], ["A" * 32], [None], [metadata["id"], metadata["id"]], [str(index).zfill(32) for index in range(7)], ["0" * 32]):
            for method in (self.store.resolve, lambda values: self.store.materialize(values, self.root / "actor")):
                with self.subTest(ids=ids), self.assertRaises(attachments.AttachmentError):
                    method(ids)
        self.assertEqual([], self.store.resolve([]))

    def test_file_mutation_is_detected_on_resolve_and_materialize(self):
        metadata = self.upload(b"before")
        self.alter(metadata["stored_path"], b"after!")
        with self.assertRaisesRegex(attachments.AttachmentError, "integrity"):
            self.store.resolve([metadata["id"]])
        with self.assertRaises(attachments.AttachmentError):
            self.store.materialize([metadata["id"]], self.root / "actor")
        self.assertFalse((self.root / "actor").exists())

    def test_metadata_digest_and_identity_prevent_tampering(self):
        for key, value, rehash in (("name", "new.pdf", False), ("id", "0" * 32, True), ("extension", "../../outside", True), ("stored_path", "/etc/passwd", True), ("bytes", True, True), ("image", True, True)):
            metadata = self.upload()
            path = self.metadata_path(metadata)
            envelope = json.loads(path.read_bytes())
            envelope["value"][key] = value
            if rehash:
                envelope["sha256"] = attachments._sha(attachments._canonical(envelope["value"]))
            self.alter(path, json.dumps(envelope).encode())
            with self.subTest(key=key), self.assertRaises(attachments.AttachmentError):
                self.store.resolve([metadata["id"]])

    def test_symlinks_and_hardlinks_in_private_store_are_rejected(self):
        for component in ("blob", "metadata", "directory"):
            metadata = self.upload()
            target = Path(metadata["stored_path"]) if component == "blob" else self.metadata_path(metadata)
            if component == "directory":
                target = target.parent
            moved = target.with_name(target.name + "-moved")
            target.rename(moved)
            target.symlink_to(moved, target_is_directory=component == "directory")
            with self.subTest(component=component), self.assertRaises(attachments.AttachmentError):
                self.store.resolve([metadata["id"]])
            target.unlink()
            moved.rename(target)
        metadata = self.upload()
        os.link(metadata["stored_path"], self.root / "hardlink")
        with self.assertRaises(attachments.AttachmentError):
            self.store.resolve([metadata["id"]])

    def test_store_root_attachment_symlink_is_rejected(self):
        other = self.root / "other"
        other.mkdir(mode=0o700)
        root = self.root / "badlab"
        root.mkdir(mode=0o700)
        (root / "attachments").symlink_to(other, target_is_directory=True)
        with self.assertRaises(attachments.AttachmentError):
            attachments.AttachmentStore(root)
        self.assertEqual([], list(other.iterdir()))

    def test_materialize_reuses_only_identical_private_copies(self):
        metadata = self.upload()
        destination = self.root / "actor"
        copied = self.store.materialize([metadata["id"]], destination)[0]
        copy_path = Path(copied["copy_path"])
        inode = copy_path.stat().st_ino
        self.assertEqual([copied], self.store.materialize([metadata["id"]], destination))
        self.assertEqual(inode, copy_path.stat().st_ino)
        self.alter(copy_path, b"corrupt")
        with self.assertRaises(attachments.AttachmentError):
            self.store.materialize([metadata["id"]], destination)
        self.assertEqual(b"corrupt", copy_path.read_bytes())
        copy_path.unlink()
        copy_path.symlink_to(metadata["stored_path"])
        with self.assertRaises(attachments.AttachmentError):
            self.store.materialize([metadata["id"]], destination)
        self.assertTrue(copy_path.is_symlink())

    def test_materialize_rejects_symlink_destination_and_rolls_back_new_copies(self):
        first, second = self.upload(b"first"), self.upload(b"second")
        destination = self.root / "actor"
        destination.mkdir(mode=0o700)
        symlink = self.root / "alias"
        symlink.symlink_to(destination, target_is_directory=True)
        with self.assertRaises(attachments.AttachmentError):
            self.store.materialize([first["id"]], symlink)
        existing = destination / (second["id"] + second["extension"])
        existing.write_bytes(b"do not overwrite")
        existing.chmod(0o400)
        with self.assertRaises(attachments.AttachmentError):
            self.store.materialize([first["id"], second["id"]], destination)
        self.assertEqual([existing], list(destination.iterdir()))
        self.assertEqual(b"do not overwrite", existing.read_bytes())

    def test_storage_bytes_and_count_quotas_include_unused_uploads(self):
        store = attachments.AttachmentStore(self.root / "quota", max_store_bytes=8, max_files=3)
        self.upload(b"1234", store=store)
        self.upload(b"5678", store=store)
        with self.assertRaisesRegex(attachments.AttachmentError, "quota"):
            self.upload(b"9", store=store)
        self.upload(b"", store=store)
        with self.assertRaisesRegex(attachments.AttachmentError, "quota"):
            self.upload(b"", store=store)

    def test_concurrent_uploads_cannot_overrun_quota(self):
        store = attachments.AttachmentStore(self.root / "concurrent", max_store_bytes=7)
        def attempt(_):
            try:
                return self.upload(b"1234", store=store)
            except attachments.AttachmentError:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))
        self.assertEqual(1, sum(result is not None for result in results))
        self.assertEqual(2, len(list(store.path.iterdir())))  # snapshot + quota lock

    def test_image_hint_requires_extension_and_raster_signature(self):
        self.assertTrue(self.upload(b"\x89PNG\r\n\x1a\nrest", "image.png")["image"])
        self.assertFalse(self.upload(b"not image bytes", "image.png")["image"])
        self.assertFalse(self.upload(b"\x89PNG\r\n\x1a\nrest", "image.jpg")["image"])
        self.assertFalse(self.upload(b"<svg><script>inert here</script></svg>", "image.svg")["image"])
        self.assertFalse(self.upload(b"\x89PNG\r\n\x1a\nrest", "image.txt")["image"])

    def test_failed_snapshot_is_cleaned_without_mutating_existing_files(self):
        metadata = self.upload()
        original_write = attachments._write_at
        def fail_metadata(directory, filename, raw):
            if filename == "metadata.json":
                raise OSError("synthetic disk failure")
            return original_write(directory, filename, raw)
        with mock.patch.object(attachments, "_write_at", side_effect=fail_metadata):
            with self.assertRaises(attachments.AttachmentError):
                self.upload(b"next")
        self.assertEqual([metadata], self.store.resolve([metadata["id"]]))
        self.assertEqual({metadata["id"], ".lock"}, {path.name for path in self.store.path.iterdir()})

    def test_incomplete_materialization_write_is_removed(self):
        metadata = self.upload()
        destination = self.root / "actor"
        with mock.patch.object(os, "fsync", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(attachments.AttachmentError):
                self.store.materialize([metadata["id"]], destination)
        self.assertEqual([], list(destination.iterdir()))
        self.assertEqual([metadata], self.store.resolve([metadata["id"]]))


if __name__ == "__main__":
    unittest.main()
