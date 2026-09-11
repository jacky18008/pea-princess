"""Replay uses only completed fixed human turns and verified selected snapshots."""
import base64
import copy
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import playground_attachments as attachments
import playground_replay as replay


class ReplayExtraction(unittest.TestCase):
    def session(self, messages=None, **changes):
        value = {"research_mode": "live", "output_mode": "agent", "messages": messages or [
            {"role": "human", "text": "  Exact first request\n"},
            {"role": "assistant", "text": "Original assistant answer", "call_id": "call-001"},
            {"role": "human", "text": "First addition", "kind": "question"},
            {"role": "human", "text": "A revised condition", "kind": "amendment"},
            {"role": "assistant", "text": "Second original answer", "call_id": "call-002"},
        ], "queue": []}
        value.update(changes)
        return value

    def file(self, index=1, **changes):
        aid = "%032x" % index
        value = dict(id=aid, name="document.pdf", bytes=0, sha256=hashlib.sha256(b"").hexdigest(),
                     path="/unopened/source/supplied-files/" + aid + ".pdf", image=False,
                     source_kind="local_path", original_path="/never-read/original.pdf")
        value.update(changes)
        return value

    def test_groups_exact_human_inputs_and_keeps_assistant_answers_separate(self):
        source = self.session()
        before = copy.deepcopy(source)
        with mock.patch.object(os, "open", side_effect=AssertionError("extraction must be pure")):
            result = replay.extract_turns(source)
        self.assertEqual(before, source)
        self.assertEqual(0, result["excluded_pending_count"])
        self.assertEqual([1, 2], [turn["index"] for turn in result["turns"]])
        self.assertEqual([{"text": "  Exact first request\n", "kind": "question", "attachments": []}], result["turns"][0]["inputs"])
        self.assertEqual(["question", "amendment"], [item["kind"] for item in result["turns"][1]["inputs"]])
        self.assertEqual("Original assistant answer", result["turns"][0]["original_reply"])
        self.assertEqual("call-002", result["turns"][1]["source_call_id"])
        self.assertNotIn("Original assistant answer", repr([turn["inputs"] for turn in result["turns"]]))
        result["turns"][0]["inputs"][0]["text"] = "mutated return value"
        self.assertEqual(before, source)

    def test_legacy_checked_and_missing_call_ids_are_supported(self):
        source = self.session(output_mode="checked")
        source["messages"][1] = {"role": "assistant", "text": "Legacy shown comparison", "acceptance_id": "legacy-1"}
        source["messages"][4].pop("call_id")
        result = replay.extract_turns(source)
        self.assertEqual("legacy-1", result["turns"][0]["source_call_id"])
        self.assertIsNone(result["turns"][1]["source_call_id"])
        source.pop("output_mode")
        self.assertEqual(result, replay.extract_turns(source))

    def test_unanswered_and_queued_inputs_are_counted_but_excluded(self):
        source = self.session()
        source["messages"].extend([{"role": "human", "text": "Trailing unsent answer request"},
                                   {"role": "human", "text": "/do/not/read/future.pdf", "pending": True}])
        source["queue"] = [{"text": "Queued future requirement", "kind": "amendment", "client_id": "opaque"}]
        result = replay.extract_turns(source)
        self.assertEqual(3, result["excluded_pending_count"])
        self.assertEqual(2, len(result["turns"]))
        self.assertNotIn("future", repr(result["turns"]))
        empty = replay.extract_turns(self.session(messages=[{"role": "human", "text": "No reply yet"}]))
        self.assertEqual({"turns": [], "excluded_pending_count": 1}, empty)

    def test_attachment_only_default_and_no_future_metadata_leak(self):
        first, future = self.file(), self.file(2, name="future.pdf")
        source = self.session(messages=[
            {"role": "human", "text": "", "attachments": [first], "attachment_only_default": "Please inspect the attachment."},
            {"role": "assistant", "text": "First answer"},
            {"role": "human", "text": "Later file", "attachments": [future]},
            {"role": "assistant", "text": "Second answer"}])
        result = replay.extract_turns(source)
        item = result["turns"][0]["inputs"][0]
        self.assertEqual("", item["text"])
        self.assertEqual("Please inspect the attachment.", item["attachment_only_default"])
        self.assertEqual([first], item["attachments"])
        self.assertNotIn("future.pdf", repr(result["turns"][0]))
        item["attachments"][0]["original_path"] = "/modified"
        self.assertEqual("/never-read/original.pdf", first["original_path"])

    def test_fixture_and_malformed_transcript_inputs_fail_without_coercion(self):
        bad_sources = [None, [], self.session(research_mode="fixture"), self.session(output_mode="persona"),
                       self.session(messages="not a list"), self.session(queue=None)]
        bad_messages = [
            [{"role": "persona", "text": "Synthetic"}],
            [{"role": "assistant", "text": "Orphan answer"}],
            [{"role": "human", "text": 42}],
            [{"role": "human", "text": "", "attachments": []}],
            [{"role": "human", "text": "Question", "kind": None}],
            [{"role": "human", "text": "x" * 8001}],
            [{"role": "human", "text": "Question", "pending": "true"}],
            [{"role": "human", "text": "Question", "pending": True}, {"role": "assistant", "text": "Premature answer"}],
            [{"role": "human", "text": "Question"}, {"role": "assistant", "text": []}],
            [{"role": "human", "text": "Question"}, {"role": "assistant", "text": "Answer", "call_id": "../outside"}],
        ]
        for source in bad_sources + [self.session(messages=messages) for messages in bad_messages]:
            with self.subTest(source=source), self.assertRaises(replay.ReplayError):
                replay.extract_turns(source)
        source = self.session()
        source["messages"][4]["call_id"] = "call-001"
        with self.assertRaises(replay.ReplayError):
            replay.extract_turns(source)

    def test_malformed_attachment_metadata_and_conflicting_ids_are_rejected(self):
        changes = [{"id": "../file"}, {"bytes": True}, {"bytes": -1}, {"bytes": attachments.MAX_ATTACHMENT_BYTES + 1},
                   {"sha256": "x" * 64}, {"image": 1}, {"source_kind": None}, {"path": "relative"},
                   {"path": "/source/../outside"}, {"name": "bad\u0085.pdf"}, {"original_path": None},
                   {"unknown": "do not silently preserve"}]
        for change in changes:
            source = self.session(messages=[{"role": "human", "text": "Question", "attachments": [self.file(**change)]}])
            with self.subTest(change=change), self.assertRaises(replay.ReplayError):
                replay.extract_turns(source)
        source = self.session(messages=[{"role": "human", "text": "First", "attachments": [self.file()]},
                                        {"role": "human", "text": "Second", "attachments": [self.file(name="different.pdf")]}])
        with self.assertRaisesRegex(replay.ReplayError, "conflicting"):
            replay.extract_turns(source)

    def test_48_distinct_files_are_supported_and_larger_sets_fail(self):
        def source(count, size=0):
            files = [self.file(index + 1, bytes=size) for index in range(count)]
            messages = [{"role": "human", "text": "Selected files", "attachments": files[index:index + 6]}
                        for index in range(0, count, 6)]
            messages.append({"role": "assistant", "text": "Completed answer"})
            return self.session(messages=messages)
        result = replay.extract_turns(source(48))
        self.assertEqual(48, sum(len(item["attachments"]) for item in result["turns"][0]["inputs"]))
        for saved in (source(49), source(21, attachments.MAX_ATTACHMENT_BYTES)):
            with self.assertRaisesRegex(replay.ReplayError, "limit"):
                replay.extract_turns(saved)


class ReplayAttachmentCloning(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.source, self.target = self.root / "source", self.root / "replay"
        self.source.mkdir(mode=0o700)
        self.target.mkdir(mode=0o700)
        self.store = attachments.AttachmentStore(self.root / "store")

    def file(self, raw=b"exact\x00\xffbytes\r\n", name="document.pdf"):
        selected = self.store.ingest({"name": name, "content_base64": base64.b64encode(raw).decode("ascii")})
        copied = self.store.materialize([selected["id"]], self.source / "supplied-files")[0]
        return {**{key: copied[key] for key in ("id", "name", "bytes", "sha256", "image", "source_kind", "mime_type")},
                "path": copied["copy_path"], "original_path": "/never-read/current/original.pdf"}

    def input(self, files, **changes):
        result = {"text": "Review the selected evidence", "kind": "question", "attachments": files}
        result.update(changes)
        return result

    def alter(self, path, raw):
        path = Path(path)
        path.chmod(0o600)
        path.write_bytes(raw)
        path.chmod(0o400)

    def test_clones_only_chosen_turn_bytes_and_preserves_source_metadata(self):
        first, future = self.file(), self.file(b"future selected bytes", "later.png")
        source_bytes = {path.name: path.read_bytes() for path in (self.source / "supplied-files").iterdir()}
        inputs = [self.input([first])]
        before = copy.deepcopy(inputs)
        with mock.patch.object(attachments, "_source", side_effect=AssertionError("never reopen original paths")):
            copied = replay.clone_input_files(self.source, self.target, inputs)
        self.assertEqual(before, inputs)
        row = copied[0]["attachments"][0]
        self.assertEqual({key: value for key, value in first.items() if key != "path"},
                         {key: value for key, value in row.items() if key != "path"})
        self.assertEqual(Path(first["path"]).read_bytes(), Path(row["path"]).read_bytes())
        self.assertEqual(0o400, stat.S_IMODE(Path(row["path"]).stat().st_mode))
        self.assertEqual({Path(first["path"]).name}, {path.name for path in (self.target / "supplied-files").iterdir()})
        self.assertNotIn(future["id"], repr(copied))
        self.assertEqual(source_bytes, {path.name: path.read_bytes() for path in (self.source / "supplied-files").iterdir()})
        replay.clone_input_files(self.source, self.target, [self.input([future])])
        self.assertEqual(2, len(list((self.target / "supplied-files").iterdir())))

    def test_path_looking_historical_text_without_attachments_never_reads_files(self):
        inputs = [self.input([], text="/never-open/earlier/file.pdf")]
        with mock.patch.object(os, "open", side_effect=AssertionError("plain text cannot select files")):
            self.assertEqual(inputs, replay.clone_input_files(self.source, self.target, inputs))
        self.assertFalse((self.target / "supplied-files").exists())

    def test_repeated_id_copies_once_and_reuses_identical_destination(self):
        item = self.file()
        inputs = [self.input([item]), self.input([copy.deepcopy(item)], kind="amendment")]
        copied = replay.clone_input_files(self.source, self.target, inputs)
        path = Path(copied[0]["attachments"][0]["path"])
        inode = path.stat().st_ino
        self.assertEqual(copied, replay.clone_input_files(self.source, self.target, inputs))
        self.assertEqual(inode, path.stat().st_ino)
        self.assertEqual(1, len(list(path.parent.iterdir())))

    def test_outside_paths_wrong_ids_and_traversal_are_rejected(self):
        item = self.file()
        outside = self.root / "outside.pdf"
        outside.write_bytes(Path(item["path"]).read_bytes())
        changes = [{"path": str(outside)}, {"path": str(self.source / "supplied-files" / ".." / outside.name)},
                   {"id": "f" * 32}, {"name": "wrong-extension.png"}]
        with mock.patch.object(attachments, "_read_at", side_effect=AssertionError("invalid path must fail before reading")):
            for change in changes:
                with self.subTest(change=change), self.assertRaises(replay.ReplayError):
                    replay.clone_input_files(self.source, self.target, [self.input([dict(item, **change)])])
        self.assertFalse((self.target / "supplied-files").exists())

    def test_snapshot_hash_failure_rolls_back_new_copies(self):
        first, corrupt = self.file(b"first"), self.file(b"second")
        self.alter(corrupt["path"], b"change")
        with self.assertRaises(replay.ReplayError):
            replay.clone_input_files(self.source, self.target, [self.input([first, corrupt])])
        self.assertEqual([], list((self.target / "supplied-files").iterdir()))
        self.assertEqual(b"first", Path(first["path"]).read_bytes())

    def test_source_symlink_fifo_and_hardlink_are_rejected(self):
        for replacement in ("symlink", "fifo", "hardlink"):
            item = self.file()
            path = Path(item["path"])
            moved = self.root / (replacement + "-original")
            path.rename(moved)
            if replacement == "symlink":
                path.symlink_to(moved)
            elif replacement == "fifo":
                os.mkfifo(path)
            else:
                os.link(moved, path)
            with self.subTest(replacement=replacement), self.assertRaises(replay.ReplayError):
                replay.clone_input_files(self.source, self.target, [self.input([item])])

    def test_source_and_destination_directory_symlinks_are_rejected(self):
        item = self.file()
        supplied = self.source / "supplied-files"
        moved = self.source / "original-files"
        supplied.rename(moved)
        supplied.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(replay.ReplayError):
            replay.clone_input_files(self.source, self.target, [self.input([item])])
        supplied.unlink()
        moved.rename(supplied)
        (self.target / "supplied-files").symlink_to(supplied, target_is_directory=True)
        with self.assertRaises(replay.ReplayError):
            replay.clone_input_files(self.source, self.target, [self.input([item])])
        self.assertEqual(1, len(list(supplied.iterdir())))

    def test_corrupt_existing_target_is_never_overwritten_or_deleted(self):
        item = self.file()
        copied = replay.clone_input_files(self.source, self.target, [self.input([item])])
        path = Path(copied[0]["attachments"][0]["path"])
        self.alter(path, b"preserve this existing corruption")
        with self.assertRaises(replay.ReplayError):
            replay.clone_input_files(self.source, self.target, [self.input([item])])
        self.assertEqual(b"preserve this existing corruption", path.read_bytes())

    def test_same_source_destination_and_invalid_input_shape_are_rejected(self):
        item = self.file()
        with self.assertRaises(replay.ReplayError):
            replay.clone_input_files(self.source, self.source, [self.input([item])])
        for inputs in (None, {}, [], [self.input([item], old_assistant_answer="not an input")],
                       [self.input([item], text="", attachment_only_default=7)]):
            with self.subTest(inputs=inputs), self.assertRaises(replay.ReplayError):
                replay.clone_input_files(self.source, self.target, inputs)

    def test_failed_copy_write_cleans_partial_file(self):
        item = self.file()
        with mock.patch.object(os, "fsync", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(replay.ReplayError):
                replay.clone_input_files(self.source, self.target, [self.input([item])])
        self.assertEqual([], list((self.target / "supplied-files").iterdir()))


if __name__ == "__main__":
    unittest.main()
