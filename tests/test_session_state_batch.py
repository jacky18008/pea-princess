"""Offline atomic batches retain ordinary authority, source and replay semantics."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vet-flat/scripts"))
import session_state as s


def user(quote="Use the current condition.", request_id=None):
    result = dict(actor="user", authorized=True, source_id="synthetic-user", quote=quote)
    if request_id is not None:
        result["request_id"] = request_id
    return result


def question(identifier):
    return dict(op="question.add", id=identifier, text="Synthetic optional check", blocking=False)


def competing_batch(project, revision, prefix, queue):
    try:
        result = s.SessionStore(project).apply_many([question(prefix + "-1"), question(prefix + "-2")], revision)
        queue.put(("committed", result["revision"]))
    except s.RevisionConflict:
        queue.put(("stale", None))


class SessionStateBatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.store = s.SessionStore(self.project)
        self.state = self.store.init("synthetic-batch")

    def apply(self, event):
        self.state = self.store.apply(event, self.state["revision"])
        return self.state

    def journal(self, store=None):
        return ((store or self.store).state_root / "events.json").read_bytes()

    def clone(self):
        other = self.project / "replica"
        other.mkdir()
        shutil.copytree(self.store.state_root, other / ".pea-state")
        return s.SessionStore(other)

    def fresh_store(self):
        project = self.project / "empty project"
        project.mkdir()
        return s.SessionStore(project)

    def initial_events(self):
        return [dict(op="project.init", project_id="synthetic-initial-batch")] + self.intake()

    def document(self):
        text = "Estimated monthly total: 1600 GBP.\nThis is a synthetic retained quote.\n"
        (self.project / "source.txt").write_text(text, encoding="utf-8")
        return dict(op="document.add", id="source", path="source.txt", line_ranges=[[1, 1]],
                    provenance=dict(actor="external", source_id="source", quote="Synthetic source"))

    def source_fact(self):
        return dict(op="fact.record", id="cost", value=dict(amount=1600, qualifier="estimate"),
                    source_ids=["source"], requirement_ids=["budget"], critical=True,
                    provenance=dict(actor="external", source_id="source", quote="Estimated monthly total: 1600 GBP."))

    def intake(self):
        quote = "Keep the overall budget at 1700 GBP."
        return [dict(op="request.capture", id="first", text=quote, source="synthetic-user"),
                dict(op="requirement.add", id="budget", value=1700, strength="must", scope="all candidates",
                     provenance=user(quote, "first")),
                dict(op="request.resolve", id="first", resolution="applied", note="Recorded exact budget condition.")]

    def rejected(self, events, expected_revision=None, error=s.SessionStateError, **kwargs):
        before, journal = self.store.show(), self.journal()
        with self.assertRaises(error):
            self.store.apply_many(events, before["revision"] if expected_revision is None else expected_revision, **kwargs)
        self.assertEqual(before, self.store.show())
        self.assertEqual(journal, self.journal())

    def cli(self, events=None, raw=None, receipt=False, revision=None):
        path = self.project / "private events.json"
        path.write_bytes(raw if raw is not None else json.dumps(events, ensure_ascii=False).encode("utf-8"))
        args = ["--project", str(self.project), "apply-many", "--events-file", str(path),
                "--expected-revision", str(self.store.show()["revision"] if revision is None else revision)]
        if receipt:
            args.append("--receipt-only")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = s.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_batch_matches_sequential_journal_sources_replay_and_invalidation_exactly(self):
        other = self.clone()
        document = self.document()
        shutil.copyfile(self.project / "source.txt", other.project_root / "source.txt")
        changed = "Lower the overall budget to 1550 GBP."
        events = self.intake() + [
            dict(op="task.add", id="vet", title="Review synthetic option", acceptance=["Use current budget"],
                 requirement_ids=["budget"]), document, self.source_fact(),
            dict(op="task.complete", id="vet", evidence_ids=["cost"], based_on_revision=7),
            dict(op="request.capture", id="change", text=changed, source="synthetic-user"),
            dict(op="requirement.update", id="budget", changes={"value": 1550}, provenance=user(changed, "change")),
            dict(op="request.resolve", id="change", resolution="applied", note="Updated the current ceiling.")]
        untouched = deepcopy(events)
        timestamp = s.datetime.datetime(2026, 9, 14, tzinfo=s.datetime.timezone.utc)
        with mock.patch.object(s.datetime, "datetime") as clock:
            clock.now.return_value = timestamp
            sequential = other.show()
            for event in events:
                sequential = other.apply(event, sequential["revision"])
            with mock.patch.object(self.store, "_write", wraps=self.store._write) as write:
                result = self.store.apply_many(events, self.state["revision"])
        self.assertEqual(1, len([call for call in write.call_args_list if call.args[1] == "events.json"]))
        self.assertEqual(sequential, result)
        self.assertEqual(self.journal(other), self.journal())
        self.assertEqual(untouched, events)
        self.assertEqual("needs_review", result["tasks"]["vet"]["status"])
        self.assertEqual("saved_source_quote", result["facts"]["cost"]["verification_kind"])
        self.assertEqual("estimate", result["facts"]["cost"]["value"]["qualifier"])
        self.assertEqual(result, s.SessionStore(self.project).show())
        self.assertTrue(self.store.verify()["ok"])
        self.assertEqual({}, self.store.context()["pending_requests"])
        (self.project / "source.txt").write_text("Changed original file\n")
        self.assertEqual("Estimated monthly total: 1600 GBP.", self.store.retrieve("source", 1, 1)["text"])

    def test_initial_batch_validates_before_publishing_identity_and_normal_journal_entries(self):
        fresh = self.fresh_store()
        events = self.initial_events()
        seen = []
        def check(state):
            self.assertFalse((fresh.state_root / "identity.json").exists())
            self.assertFalse((fresh.state_root / "events.json").exists())
            self.assertEqual("synthetic-initial-batch", state["project_id"])
            self.assertEqual("resolved", state["requests"]["first"]["status"])
            seen.append(deepcopy(state))
        result = fresh.apply_many(events, 0, validate=check)
        self.assertEqual([result], seen)
        self.assertEqual(len(events), result["revision"])
        self.assertEqual(result, fresh.show())
        self.assertEqual(events, [entry["event"] for entry in json.loads(self.journal(fresh))["events"]])
        self.assertEqual(dict(schema_version=s.VERSION, project_id=result["project_id"]),
                         json.loads((fresh.state_root / "identity.json").read_text()))
        self.assertTrue(fresh.verify()["ok"])

    def test_rejected_initial_validator_leaves_only_private_lock_then_allows_fresh_attempt(self):
        fresh = self.fresh_store()
        def reject(state):
            raise ValueError("Synthetic final projection is invalid")
        with self.assertRaises(ValueError):
            fresh.apply_many(self.initial_events(), 0, validate=reject)
        self.assertEqual({"state.lock"}, {path.name for path in fresh.state_root.iterdir()})
        self.assertEqual(0o700, fresh.state_root.stat().st_mode & 0o777)
        result = fresh.apply_many(self.initial_events(), 0)
        self.assertEqual(4, result["revision"])
        self.assertTrue(fresh.verify()["ok"])

    def test_initial_batch_requires_init_first_and_cannot_initialize_twice(self):
        fresh = self.fresh_store()
        validator = mock.Mock()
        for events in ([question("no-init")], [dict(op="project.init", project_id="one"),
                                                dict(op="project.init", project_id="two")]):
            with self.subTest(events=events):
                with self.assertRaises(s.SessionStateError):
                    fresh.apply_many(events, 0, validate=validator)
                self.assertFalse((fresh.state_root / "identity.json").exists())
                self.assertFalse((fresh.state_root / "events.json").exists())
        validator.assert_not_called()

    def test_zero_revision_is_stale_for_existing_project_and_cannot_reinitialize_lost_journal(self):
        self.rejected(self.initial_events(), expected_revision=0, error=s.RevisionConflict)
        identity = (self.store.state_root / "identity.json").read_bytes()
        (self.store.state_root / "events.json").unlink()
        with self.assertRaises(s.IntegrityError):
            self.store.apply_many(self.initial_events(), 0)
        self.assertEqual(identity, (self.store.state_root / "identity.json").read_bytes())
        self.assertFalse((self.store.state_root / "events.json").exists())

    def test_initial_validator_cannot_mutate_published_project_identity(self):
        fresh = self.fresh_store()
        def mutate(state):
            state["project_id"] = None
            state["revision"] = -1
            state["event_hash"] = "f" * 64
            state["requirements"].clear()
        result = fresh.apply_many(self.initial_events(), 0, validate=mutate)
        self.assertEqual("synthetic-initial-batch", result["project_id"])
        self.assertEqual(1700, result["requirements"]["budget"]["value"])
        self.assertEqual(result, fresh.show())
        self.assertTrue(fresh.verify()["ok"])

    def test_initial_journal_write_failure_keeps_identity_marker_and_fails_closed(self):
        fresh = self.fresh_store()
        original_write = fresh._write
        def fail_journal(directory, name, value):
            if name == "events.json":
                raise OSError("Synthetic journal publication failure")
            return original_write(directory, name, value)
        with mock.patch.object(fresh, "_write", side_effect=fail_journal):
            with self.assertRaises(s.SessionStateError):
                fresh.apply_many(self.initial_events(), 0)
        self.assertTrue((fresh.state_root / "identity.json").exists())
        self.assertFalse((fresh.state_root / "events.json").exists())
        with self.assertRaises(s.IntegrityError):
            fresh.apply_many(self.initial_events(), 0)

    def test_cli_initial_batch_returns_final_receipt_from_empty_project(self):
        self.store = self.fresh_store()
        self.project = self.store.project_root
        code, stdout, stderr = self.cli(self.initial_events(), receipt=True, revision=0)
        self.assertEqual((0, ""), (code, stderr))
        receipt = json.loads(stdout)
        self.assertEqual(4, receipt["revision"])
        self.assertEqual("synthetic-initial-batch", receipt["project_id"])
        self.assertEqual({}, self.store.context()["pending_requests"])
        self.assertTrue(self.store.verify()["ok"])

    def test_late_authority_failure_rolls_back_requests_and_requirements(self):
        self.store.checkpoint()
        checkpoint = (self.store.state_root / "checkpoint.json").read_bytes()
        events = self.intake()
        events.append(dict(op="requirement.update", id="budget", changes={"value": 3000},
                           provenance=dict(user(), actor="external")))
        self.rejected(events)
        self.assertEqual({}, self.store.show()["requests"])
        self.assertEqual({}, self.store.show()["requirements"])
        self.assertEqual(checkpoint, (self.store.state_root / "checkpoint.json").read_bytes())
        self.assertTrue(self.store.verify()["checkpoint"]["current"])

    def test_late_bad_fact_quote_publishes_no_documents_or_state(self):
        events = self.intake() + [self.document(), self.source_fact()]
        events[-1]["provenance"]["quote"] = "Guaranteed monthly ceiling: 1600 GBP."
        self.rejected(events)
        self.assertEqual({}, self.store.show()["documents"])
        self.assertEqual({}, self.store.show()["facts"])
        # Content-addressed source bytes may remain private but are not journal references.
        objects = list(self.store.state_root.glob("object-*.txt"))
        self.assertEqual(1, len(objects))
        self.assertEqual(0o600, objects[0].stat().st_mode & 0o777)
        self.assertTrue(self.store.verify()["ok"])

    def test_batch_cannot_supply_computed_fact_or_document_metadata(self):
        for forged in (dict(self.source_fact(), source_verified=True),
                       dict(self.source_fact(), verification_kind="saved_source_quote"),
                       dict(op="document.add", id="forged", document={"sha256": "a" * 64})):
            with self.subTest(op=forged["op"]):
                self.rejected(self.intake() + [forged])

    def test_validator_rejection_sees_final_state_but_publishes_nothing(self):
        events = self.intake() + [self.document(), self.source_fact()]
        seen = []
        def reject(state):
            seen.append(deepcopy(state))
            raise ValueError("Final review failed")
        self.rejected(events, error=ValueError, validate=reject)
        self.assertEqual(1, len(seen))
        self.assertEqual(1 + len(events), seen[0]["revision"])
        self.assertEqual("resolved", seen[0]["requests"]["first"]["status"])
        self.assertTrue(seen[0]["facts"]["cost"]["source_verified"])
        self.assertEqual({}, self.store.show()["requirements"])

    def test_validator_cannot_mutate_committed_state_or_caller_events(self):
        events = self.intake()
        original = deepcopy(events)
        def mutate(state):
            state["requirements"]["budget"]["value"] = 9999
            state["requests"].clear()
            state["event_hash"] = "f" * 64
            return {"accepted": False}  # Only a raised error rejects the batch.
        result = self.store.apply_many(events, self.state["revision"], validate=mutate)
        self.assertEqual(1700, result["requirements"]["budget"]["value"])
        self.assertEqual("resolved", result["requests"]["first"]["status"])
        self.assertEqual(original, events)
        self.assertEqual(result, self.store.show())
        self.assertTrue(self.store.verify()["ok"])

    def test_stale_batch_rejected_before_snapshot_and_validator_work(self):
        stale = self.state["revision"]
        self.apply(question("existing"))
        validator = mock.Mock()
        self.rejected([self.document()], expected_revision=stale, validate=validator, error=s.RevisionConflict)
        validator.assert_not_called()
        self.assertEqual([], list(self.store.state_root.glob("object-*.txt")))

    def test_explicit_per_event_revision_must_match_intermediate_state(self):
        events = self.intake() + [dict(op="fact.record", id="derived", value=1550, derived=True,
                                     based_on_revision=self.state["revision"], provenance=user())]
        self.rejected(events, error=s.RevisionConflict)
        events[-1]["based_on_revision"] = self.state["revision"] + len(events) - 1
        result = self.store.apply_many(events, self.state["revision"])
        self.assertEqual(self.state["revision"] + len(events), result["revision"])
        self.assertTrue(result["facts"]["derived"]["derived"])

    def spending_ready(self):
        self.apply(dict(op="budget.set", id="api", scope="api_tokens", unit="tokens", limit=100, provenance=user()))
        self.apply(dict(op="task.add", id="vet", title="Synthetic bounded call", acceptance=["Current conditions"], budget_ids=["api"]))
        self.apply(dict(op="dispatch.start", id="call", task_id="vet", based_on_revision=self.state["revision"], request_hash="a" * 64))
        return dict(op="budget.spend", id="api", amount=13, dispatch_id="call")

    def test_duplicate_spend_inside_batch_is_noop_and_does_not_shift_following_revision(self):
        spend = self.spending_ready()
        before = self.state["revision"]
        events = [spend, deepcopy(spend), dict(op="fact.record", id="result", value="Synthetic result",
                                             derived=True, based_on_revision=before + 1, provenance=user())]
        result = self.store.apply_many(events, before)
        self.assertEqual(before + 2, result["revision"])
        self.assertEqual(13, result["budgets"]["api"]["spent"])
        self.assertEqual(1, len(result["budgets"]["api"]["spends"]))
        self.assertTrue(self.store.verify()["ok"])
        journal = self.journal()
        checked = []
        same = self.store.apply_many([spend, deepcopy(spend)], result["revision"], validate=lambda state: checked.append(state))
        self.assertEqual(result, same)
        self.assertEqual([result], checked)
        self.assertEqual(journal, self.journal())

    def test_conflicting_duplicate_spend_rolls_back_first_spend_too(self):
        spend = self.spending_ready()
        self.rejected([spend, dict(spend, amount=14)])
        self.assertEqual(0, self.store.show()["budgets"]["api"]["spent"])
        self.assertEqual([], self.store.show()["budgets"]["api"]["spends"])

    def test_bounds_and_malformed_members_reject_without_any_partial_commit(self):
        oversized_event = dict(question("too-large"), extra=["x" * 40000] * 7)
        oversized_batch = [dict(question("large-%s" % index), extra=["x" * 45000] * 5) for index in range(10)]
        invalid = [[], {}, tuple([question("tuple")]), [None], [question("valid"), []],
                   [question("q%s" % index) for index in range(101)], [oversized_event], oversized_batch]
        for events in invalid:
            with self.subTest(shape=type(events).__name__, count=len(events)):
                self.rejected(events)
        self.rejected([question("callback")], validate=False)
        self.rejected([question("bad-revision")], expected_revision=True, error=s.RevisionConflict)
        result = self.store.apply_many([question("q%s" % index) for index in range(100)], self.state["revision"])
        self.assertEqual(self.state["revision"] + 100, result["revision"])
        self.assertEqual(100, len(result["questions"]))

    def test_competing_batches_cannot_interleave_or_partially_commit(self):
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        self.addCleanup(queue.close)
        children = [context.Process(target=competing_batch,
                                    args=(str(self.project), self.state["revision"], prefix, queue)) for prefix in ("a", "b")]
        for child in children:
            child.start()
        for child in children:
            child.join(10)
            if child.is_alive():
                child.terminate()
                child.join(5)
            self.assertEqual(0, child.exitcode)
        self.assertEqual(["committed", "stale"], sorted(queue.get(timeout=3)[0] for _ in children))
        result = self.store.show()
        self.assertIn(set(result["questions"]), ({"a-1", "a-2"}, {"b-1", "b-2"}))
        self.assertEqual(3, result["revision"])
        self.assertTrue(self.store.verify()["ok"])

    def test_cli_full_state_and_receipt_have_existing_success_envelopes(self):
        code, stdout, stderr = self.cli(self.intake())
        self.assertEqual((0, ""), (code, stderr))
        full = json.loads(stdout)
        self.assertEqual(self.store.show(), full)
        self.assertEqual(1700, full["requirements"]["budget"]["value"])
        code, stdout, stderr = self.cli([question("receipt-question")], receipt=True)
        self.assertEqual((0, ""), (code, stderr))
        result = self.store.show()
        self.assertEqual(dict(ok=True, **{key: result[key] for key in ("schema_version", "project_id", "revision", "event_hash")}),
                         json.loads(stdout))
        self.assertNotIn("receipt-question", stdout)

    def test_cli_receipt_identifies_own_commit_even_if_next_writer_advances(self):
        original_apply = s.SessionStore.apply_many
        def apply_then_write(store, events, expected_revision):
            result = original_apply(store, events, expected_revision)
            original_apply(store, [question("later")], result["revision"])
            return result
        with mock.patch.object(s.SessionStore, "apply_many", apply_then_write):
            code, stdout, stderr = self.cli([question("batch")], receipt=True)
        self.assertEqual((0, ""), (code, stderr))
        receipt = json.loads(stdout)
        entries = json.loads(self.journal())["events"]
        self.assertEqual(entries[-2]["revision"], receipt["revision"])
        self.assertEqual(entries[-2]["event_hash"], receipt["event_hash"])
        self.assertEqual(receipt["revision"] + 1, self.store.show()["revision"])

    def test_cli_stale_invalid_and_oversized_input_return_json_errors_without_writes(self):
        self.apply(question("existing"))
        before = self.journal()
        cases = [(self.intake(), None, 1), ([], None, None), (None, b'[{"op":"question.add","op":"request.capture"}]', None),
                 (None, b" " * (s.MAX_BATCH_BYTES + 1), None)]
        for events, raw, revision in cases:
            with self.subTest(revision=revision, raw_length=len(raw) if raw else None):
                code, stdout, stderr = self.cli(events, raw, receipt=True, revision=revision)
                self.assertEqual((2, ""), (code, stdout))
                envelope = json.loads(stderr)
                self.assertFalse(envelope["ok"])
                self.assertEqual({"ok", "error", "message"}, set(envelope))
                self.assertEqual(before, self.journal())

    def test_documented_batch_example_runs_in_a_private_project(self):
        reference = (ROOT / "skills/vet-flat/references/state-api.md").read_text()
        section = reference.split("## Atomic event batches\n", 1)[1].split("\n## ", 1)[0]
        events = json.loads(re.findall(r"^```json\n(.*?)^```", section, re.M | re.S)[0])
        command = re.findall(r"^```console\n(.*?)^```", section, re.M | re.S)[0]
        path = self.project / "documented batch.json"
        path.write_text(json.dumps(events), encoding="utf-8")
        result = subprocess.run(["bash", "-c", command], text=True, capture_output=True, timeout=10,
                                env=dict(os.environ, PEA_SKILL=str(ROOT / "skills/vet-flat"), PEA_PROJECT=str(self.project),
                                         PEA_REVISION=str(self.state["revision"]), PEA_EVENTS_FILE=str(path)))
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["ok"])
        self.assertEqual(self.state["revision"] + len(events), receipt["revision"])
        self.assertEqual({}, self.store.context()["pending_requests"])
        self.assertEqual(1700, self.store.context()["requirements"]["monthly-total"]["value"])


if __name__ == "__main__":
    unittest.main()
