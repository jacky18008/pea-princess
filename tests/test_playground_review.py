"""Offline review views and immutable notes over synthetic physical-call evidence."""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "skills/vet-flat/scripts")]
import session_runner as runner
import playground_review as review
from session_state import SessionStore


def digest(value):
    return runner._digest(value)


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class PlaygroundReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve() / "session"
        self.folder.mkdir()
        self.store = SessionStore(self.folder)
        self.store.init("synthetic-review")
        self.apply({"op": "budget.set", "id": "tokens", "scope": "api_tokens",
                    "limit": 1000000, "unit": "tokens", "provenance": {
                        "actor": "user", "authorized": True, "source_id": "synthetic-user",
                        "quote": "Use up to 1000000 synthetic test tokens"}})
        self.apply({"op": "task.add", "id": "answer-task", "title": "Synthetic response",
                    "acceptance": ["Preserve the synthetic current question"], "budget_ids": ["tokens"]})
        patch = mock.patch("durable_run.source_fingerprint", return_value={"synthetic.py": "frozen"})
        patch.start()
        self.addCleanup(patch.stop)
        # Any accidental provider/process launch makes an offline test fail.
        patch = mock.patch.object(runner.launch, "run", side_effect=AssertionError("model calls forbidden"))
        patch.start()
        self.addCleanup(patch.stop)
        self.session = {"id": "test-session", "calls": [], "messages": []}

    def apply(self, event):
        return self.store.apply(event, expected_revision=self.store.show()["revision"])

    def add_call(self, call_id="call-001-assistant", usage=None, seconds=2.5,
                 answer="Synthetic answer with a concrete next step.",
                 current_input="Please compare the two supplied options.",
                 events=None, raw=None, record_changes=None):
        usage = ({"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10}
                 if usage is None else usage)
        events = [] if events is None else copy.deepcopy(events)
        if raw is None:
            raw = "\n".join(json.dumps(event, ensure_ascii=False) for event in [
                {"type": "thread.started", "thread_id": "synthetic-thread"},
                {"type": "turn.started"},
                *events,
                {"type": "item.completed", "item": {
                    "id": "message-1", "type": "agent_message", "text": answer}},
                {"type": "turn.completed", "usage": usage},
            ]) + "\n"
        launch_result = runner.launch.LaunchResult(stdout=raw, exit_code=0, seconds=seconds)
        record = runner.cli_record("answer", launch_result, "codex")
        record["answer"] = answer
        if record_changes:
            record.update(copy.deepcopy(record_changes))
        prompt = ("Synthetic supplied instructions.\n\nFULL CONVERSATION\n"
                  "USER: Earlier synthetic request.\n\nCURRENT INPUT TO ANSWER\n" + current_input)
        try:
            receipt = runner.run_step(
                project=self.folder, call_id=call_id, task_id="answer-task", model="synthetic-model",
                prompt=prompt, token_budget_id="tokens", tool_policy="live_research",
                max_prompt_chars=256000, invoke=lambda *_: copy.deepcopy(record))
        except runner.CallControlError:
            # Failed streams still produce immutable physical evidence and a
            # recoverable receipt. Nothing retries or invokes a real transport.
            receipt = json.loads((self.run_folder(call_id) / "receipt.json").read_text())
        self.session["calls"].append({"id": call_id, "actor": "assistant", "status": "complete",
                                      "receipt": copy.deepcopy(receipt)})
        self.session["messages"].extend([
            {"role": "human", "text": current_input},
            {"role": "assistant", "text": answer},
        ])
        return receipt

    def run_folder(self, call_id="call-001-assistant"):
        return self.folder / ".pea-state/runs" / call_id

    def detail(self, call_id="call-001-assistant"):
        return review.build_call(self.folder, self.session, call_id)

    @contextmanager
    def altered_file(self, path, content):
        original = path.read_bytes()
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        try:
            yield
        finally:
            path.write_bytes(original)

    def assert_unknown_with_reply(self, detail, answer="Synthetic answer with a concrete next step."):
        self.assertFalse(detail["integrity"]["ok"])
        self.assertTrue(detail["integrity"]["gaps"])
        self.assertEqual(answer, detail["reply"]["text"])
        for key in ("input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "processed_tokens"):
            self.assertIsNone(detail["usage"][key], key)

    def source_bytes(self):
        return {str(path.relative_to(self.folder)): path.read_bytes()
                for path in self.folder.rglob("*") if path.is_file()
                and "review-notes" not in path.relative_to(self.folder).parts}

    def payload(self, **changes):
        payload = {"client_id": str(uuid.uuid4()), "call_id": "call-001-assistant",
                   "reviewer": "human", "rating": "needs_work", "severity": "low",
                   "tags": ["missed_question"], "note": "Address the current question directly."}
        payload.update(changes)
        return payload

    def test_complete_call_binds_prompt_reply_and_direct_usage(self):
        self.add_call()
        before = self.source_bytes()
        detail = self.detail()
        self.assertTrue(detail["integrity"]["ok"], detail["integrity"]["gaps"])
        self.assertEqual([], detail["integrity"]["gaps"])
        expected = {"input_tokens": 100, "cached_input_tokens": 80, "uncached_input_tokens": 20,
                    "output_tokens": 10, "processed_tokens": 110, "seconds": 2.5}
        self.assertEqual(expected, detail["usage"])
        self.assertEqual("Please compare the two supplied options.", detail["current_input"]["text"])
        manifest = json.loads((self.run_folder() / "manifest.json").read_text())["value"]
        self.assertEqual(manifest["request"]["prompt"], detail["prompt"]["text"])
        for name in ("prompt", "current_input", "reply"):
            block = detail[name]
            self.assertFalse(block["truncated"])
            self.assertEqual(len(block["text"]), block["total_chars"])
            self.assertEqual(sha_text(block["text"]), block["sha256"])
            self.assertIsInstance(block["source_path"], str)
        index = review.build_index(self.folder, self.session)
        self.assertEqual(1, len(index["calls"]))
        self.assertEqual(expected, index["calls"][0]["usage"])
        for key, value in expected.items():
            self.assertEqual({"value": value, "known_sum": value, "unknown_calls": 0}, index["totals"][key])
        self.assertNotIn("prompt", index["calls"][0])
        self.assertNotIn("reply", index["calls"][0])
        self.assertEqual(before, self.source_bytes(), "Reading review evidence must not repair/write source artifacts")

    def test_totals_do_not_add_cached_input_twice(self):
        self.add_call()
        self.add_call("call-002-assistant", usage={"input_tokens": 40, "cached_input_tokens": 10,
                                                   "output_tokens": 5}, seconds=1)
        totals = review.build_index(self.folder, self.session)["totals"]
        for key, value in {"input_tokens": 140, "cached_input_tokens": 90, "uncached_input_tokens": 50,
                           "output_tokens": 15, "processed_tokens": 155, "seconds": 3.5}.items():
            self.assertEqual({"value": value, "known_sum": value, "unknown_calls": 0}, totals[key])

    def test_missing_usage_remains_unknown_in_totals(self):
        self.add_call()
        self.add_call("call-002-assistant", usage={})
        detail = self.detail("call-002-assistant")
        self.assertIsNone(detail["usage"]["processed_tokens"])
        totals = review.build_index(self.folder, self.session)["totals"]
        self.assertEqual({"value": None, "known_sum": 110, "unknown_calls": 1}, totals["processed_tokens"])
        self.assertEqual({"value": None, "known_sum": 80, "unknown_calls": 1}, totals["cached_input_tokens"])

    def test_missing_cached_counter_preserves_independently_verified_processed_usage(self):
        self.add_call(usage={"input_tokens": 100, "output_tokens": 10})
        detail = self.detail()
        self.assertFalse(detail["integrity"]["ok"])
        self.assertTrue(detail["integrity"]["gaps"])
        self.assertEqual(100, detail["usage"]["input_tokens"])
        self.assertEqual(10, detail["usage"]["output_tokens"])
        self.assertEqual(110, detail["usage"]["processed_tokens"])
        self.assertIsNone(detail["usage"]["cached_input_tokens"])
        self.assertIsNone(detail["usage"]["uncached_input_tokens"])
        totals = review.build_index(self.folder, self.session)["totals"]
        self.assertEqual({"value": 110, "known_sum": 110, "unknown_calls": 0}, totals["processed_tokens"])
        self.assertEqual({"value": None, "known_sum": 0, "unknown_calls": 1}, totals["cached_input_tokens"])

    def test_missing_or_invalid_duration_does_not_erase_known_tokens(self):
        for number, seconds in enumerate((None, -1, float("nan"), True), 1):
            call_id = "call-%03d-assistant" % number
            self.add_call(call_id, seconds=seconds)
            with self.subTest(seconds=seconds):
                detail = self.detail(call_id)
                self.assertTrue(detail["integrity"]["gaps"])
                self.assertIsNone(detail["usage"]["seconds"])
                self.assertEqual(110, detail["usage"]["processed_tokens"])
        totals = review.build_index(self.folder, self.session)["totals"]
        self.assertEqual({"value": 440, "known_sum": 440, "unknown_calls": 0}, totals["processed_tokens"])
        self.assertEqual({"value": None, "known_sum": 0, "unknown_calls": 4}, totals["seconds"])

    def test_tool_lifecycle_groups_by_item_id_and_keeps_completed_output(self):
        events = [
            {"type": "item.started", "item": {"id": "search-1", "type": "web_search",
                                               "status": "in_progress", "query": "synthetic public query"}},
            {"type": "item.updated", "item": {"id": "search-1", "type": "web_search",
                                               "status": "in_progress"}},
            {"type": "item.completed", "item": {"id": "search-1", "type": "web_search",
                                                 "status": "completed", "output": "Retained synthetic search result"}},
            {"type": "item.updated", "item": {"id": "search-1", "type": "web_search",
                                               "status": "in_progress"}},
            {"type": "item.completed", "item": {"id": "command-1", "type": "command_execution",
                                                 "status": "completed", "command": "synthetic read-only command",
                                                 "aggregated_output": "Retained command output", "exit_code": 0}},
            {"type": "item.completed", "item": {"id": "reason-1", "type": "reasoning",
                                                 "text": "PRIVATE_REASONING_MUST_NOT_BE_RENDERED"}},
        ]
        self.add_call(events=events)
        detail = self.detail()
        self.assertTrue(detail["integrity"]["ok"], detail["integrity"]["gaps"])
        self.assertEqual(2, detail["tool_invocation_count"])
        tools = {tool["id"]: tool for tool in detail["tools"]}
        self.assertEqual({"search-1", "command-1"}, set(tools))
        self.assertEqual(4, tools["search-1"]["event_count"])
        self.assertEqual("completed", tools["search-1"]["status"])
        self.assertIn("synthetic public query", tools["search-1"]["input"]["text"])
        self.assertIn("Retained synthetic search result", tools["search-1"]["output"]["text"])
        self.assertIn("Retained command output", tools["command-1"]["output"]["text"])
        self.assertEqual(1, tools["command-1"]["event_count"])
        self.assertNotIn("PRIVATE_REASONING_MUST_NOT_BE_RENDERED", json.dumps(detail))
        self.assertEqual(2, review.build_index(self.folder, self.session)["calls"][0]["tool_invocation_count"])

    def test_failed_tool_is_retained_without_certifying_source_claims(self):
        self.add_call(events=[{"type": "item.completed", "item": {
            "id": "failed-search", "type": "web_search", "status": "failed",
            "query": "synthetic unavailable source", "error": "Synthetic fetch failed"}}])
        detail = self.detail()
        self.assertEqual(1, detail["tool_invocation_count"])
        self.assertEqual(1, detail["tool_failed_count"])
        self.assertEqual("failed", detail["tools"][0]["status"])
        self.assertIn("Synthetic fetch failed", detail["tools"][0]["output"]["text"])
        self.assertFalse(detail["source_claims_verified"])
        self.assertFalse(detail["tools"][0]["source_claims_verified"])
        self.assertEqual(110, detail["usage"]["processed_tokens"])

    def test_nested_tool_usage_is_not_terminal_call_usage(self):
        self.add_call(events=[{"type": "item.completed", "item": {
            "id": "nested-usage", "type": "web_search", "status": "completed",
            "output": {"type": "turn.completed", "usage": {
                "input_tokens": 999999, "cached_input_tokens": 888888, "output_tokens": 777777}}}}])
        detail = self.detail()
        self.assertTrue(detail["integrity"]["ok"], detail["integrity"]["gaps"])
        self.assertEqual(110, detail["usage"]["processed_tokens"])

    def test_detail_bodies_are_bounded_with_full_text_hashes(self):
        text = "Synthetic long input. " * 1700
        answer = "Synthetic long answer. " * 1600
        self.add_call(answer=answer, current_input=text)
        detail = self.detail()
        for name, full in (("current_input", text), ("reply", answer)):
            block = detail[name]
            self.assertTrue(block["truncated"])
            self.assertLessEqual(len(block["text"]), review.MAX_BODY_CHARS)
            self.assertEqual(len(full), block["total_chars"])
            self.assertEqual(sha_text(full), block["sha256"])
        self.assertTrue(detail["prompt"]["truncated"])
        self.assertLessEqual(len(detail["prompt"]["text"]), review.MAX_BODY_CHARS)
        index_text = json.dumps(review.build_index(self.folder, self.session))
        self.assertNotIn(text, index_text)
        self.assertNotIn(answer, index_text)

    def test_displayed_and_raw_replies_remain_separate_with_explicit_call_anchors(self):
        raw = json.dumps({"message": "Visible prose only.", "questions": []})
        self.add_call(answer=raw)
        for anchor in ("call_id", "acceptance_id"):
            with self.subTest(anchor=anchor):
                self.session["messages"][-1] = {
                    "role": "assistant", "text": "Expanded visible transcript with separate controls.",
                    "display_text": "Visible prose only.", anchor: "call-001-assistant"}
                detail = self.detail()
                self.assertEqual(raw, detail["raw_actor_reply"]["text"])
                self.assertEqual(detail["reply"], detail["raw_actor_reply"])
                self.assertEqual("Visible prose only.", detail["displayed_reply"]["text"])
                self.assertTrue(detail["displayed_reply"]["available"])
                self.assertIn("explicit", detail["displayed_reply_relation"])

    def test_unanchored_displayed_projection_requires_one_unambiguous_match(self):
        raw = json.dumps({"message": "Visible prose only.", "questions": []})
        self.add_call(answer=raw)
        displayed = {"role": "assistant", "text": "Expanded visible transcript with separate controls.",
                     "display_text": "Visible prose only."}
        self.session["messages"][-1] = displayed
        detail = self.detail()
        self.assertEqual("Visible prose only.", detail["displayed_reply"]["text"])
        self.assertIn("no stored call anchor", detail["displayed_reply_relation"])
        self.session["messages"].append(copy.deepcopy(displayed))
        detail = self.detail()
        self.assertFalse(detail["displayed_reply"]["available"])
        self.assertEqual("", detail["displayed_reply"]["text"])
        self.assertIn("ambiguous", detail["displayed_reply_relation"])
        self.assertEqual(raw, detail["raw_actor_reply"]["text"])

    def test_missing_and_malformed_manifest_retain_reply_without_verified_usage(self):
        self.add_call()
        path = self.run_folder() / "manifest.json"
        original = path.read_bytes()
        path.unlink()
        try:
            self.assert_unknown_with_reply(self.detail())
        finally:
            path.write_bytes(original)
        for content in (b"{not JSON", b"[]", b"null"):
            with self.subTest(content=content), self.altered_file(path, content):
                self.assert_unknown_with_reply(self.detail())

    def test_tampered_manifest_and_bound_request_are_detected(self):
        self.add_call()
        manifest_path = self.run_folder() / "manifest.json"
        saved = json.loads(manifest_path.read_text())
        saved["value"]["request"]["prompt"] = "Changed prompt"
        with self.altered_file(manifest_path, json.dumps(saved)):
            self.assert_unknown_with_reply(self.detail())
        request_path = self.run_folder() / "physical/requests" / (sha_text("answer") + ".json")
        saved = json.loads(request_path.read_text())
        saved["value"]["request"]["model"] = "different-model"
        saved["sha256"] = digest(saved["value"])
        with self.altered_file(request_path, json.dumps(saved)):
            self.assert_unknown_with_reply(self.detail())

    def test_tampered_checkpoint_raw_stream_retains_receipt_reply(self):
        self.add_call()
        path = self.run_folder() / "physical/control/checkpoint.json"
        saved = json.loads(path.read_text())
        saved["state"]["calls"]["answer"]["record"]["launch_result"]["stdout"] += "changed bytes"
        with self.altered_file(path, json.dumps(saved)):
            self.assert_unknown_with_reply(self.detail())
            totals = review.build_index(self.folder, self.session)["totals"]["processed_tokens"]
            self.assertEqual({"value": None, "known_sum": 0, "unknown_calls": 1}, totals)

    def test_resealed_physical_version_or_checkpoint_policy_mismatch_is_a_gap(self):
        self.add_call()
        cases = [
            ("physical/run.json", "value", "sha256", "version", 999),
            ("physical/control/checkpoint.json", "state", "state_sha256", "version", 999),
            ("physical/control/checkpoint.json", "state", "state_sha256", "allow_tools", False),
        ]
        for relative, value_key, hash_key, field, replacement in cases:
            with self.subTest(relative=relative, field=field):
                path = self.run_folder() / relative
                saved = json.loads(path.read_text())
                saved[value_key][field] = replacement
                saved[hash_key] = digest(saved[value_key])
                with self.altered_file(path, json.dumps(saved)):
                    self.assert_unknown_with_reply(self.detail())

    def test_receipt_hash_mismatch_cannot_certify_counters(self):
        self.add_call()
        path = self.run_folder() / "receipt.json"
        saved = json.loads(path.read_text())
        saved["record_sha256"] = "0" * 64
        with self.altered_file(path, json.dumps(saved)):
            self.assert_unknown_with_reply(self.detail())
        self.session["calls"][0]["receipt"]["record_sha256"] = "f" * 64
        self.assert_unknown_with_reply(self.detail())

    def test_missing_raw_is_not_zero_cost(self):
        self.add_call(raw="")
        self.assert_unknown_with_reply(self.detail())

    def test_malformed_raw_is_not_zero_cost(self):
        self.add_call(raw="not JSON\n")
        self.assert_unknown_with_reply(self.detail())

    def test_malformed_raw_with_known_terminal_still_has_an_integrity_gap(self):
        raw = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10}}) + "\nnot JSON\n"
        self.add_call(raw=raw)
        self.assert_unknown_with_reply(self.detail())

    def test_direct_and_raw_terminal_counter_mismatch_is_a_gap(self):
        self.add_call(record_changes={"direct_terminal_usage": {
            "input_tokens": 999, "cached_input_tokens": 80, "output_tokens": 10}})
        self.assert_unknown_with_reply(self.detail())

    def test_malformed_tool_item_type_is_an_explicit_gap(self):
        self.add_call(record_changes={"tool_events": [
            {"type": "item.completed", "item": {"id": "bad", "type": ["web_search"]}}]})
        detail = self.detail()
        self.assertFalse(detail["integrity"]["ok"])
        self.assertIsNone(detail["tool_invocation_count"])
        self.assertEqual([], detail["tools"])
        self.assertEqual(110, detail["usage"]["processed_tokens"])

    def test_latest_completed_tool_output_replaces_earlier_output_fields(self):
        self.add_call(events=[
            {"type": "item.started", "item": {"id": "tool", "type": "web_search", "status": "in_progress"}},
            {"type": "item.completed", "item": {"id": "tool", "type": "web_search", "aggregated_output": "OLD_PARTIAL"}},
            {"type": "item.completed", "item": {"id": "tool", "type": "web_search", "output": "LATEST_RESULT"}},
            {"type": "item.updated", "item": {"id": "tool", "type": "web_search", "status": "in_progress", "output": "LATE_UPDATE"}},
        ])
        tool = self.detail()["tools"][0]
        self.assertEqual("completed", tool["status"])
        self.assertIn("LATEST_RESULT", tool["output"]["text"])
        self.assertNotIn("OLD_PARTIAL", tool["output"]["text"])
        self.assertNotIn("LATE_UPDATE", tool["output"]["text"])

    def test_tool_events_without_ids_do_not_claim_distinct_invocation_count(self):
        self.add_call(events=[
            {"type": "item.started", "item": {"type": "web_search"}},
            {"type": "item.completed", "item": {"type": "web_search", "output": "retained"}},
        ])
        detail = self.detail()
        self.assertIsNone(detail["tool_invocation_count"])
        self.assertFalse(detail["integrity"]["ok"])
        self.assertIn("retained", detail["raw_tool_events"]["text"])

    def test_validly_hashed_wrong_envelope_shape_is_a_gap(self):
        self.add_call()
        for name in ("manifest.json", "physical/control/checkpoint.json"):
            with self.subTest(name=name):
                key, hash_key = ("value", "sha256") if name == "manifest.json" else ("state", "state_sha256")
                value = []
                with self.altered_file(self.run_folder() / name,
                                       json.dumps({key: value, hash_key: digest(value)})):
                    self.assert_unknown_with_reply(self.detail())

    def test_invalid_call_ids_and_unknown_calls_cannot_select_paths(self):
        self.add_call()
        for call_id in ("../outside", "/tmp/outside", "", "call-001-assistant/../../outside", "missing-call"):
            with self.subTest(call_id=call_id), self.assertRaises(ValueError):
                self.detail(call_id)

    def test_symlink_evidence_is_not_read_or_repaired(self):
        self.add_call()
        outside = self.folder.parent / "outside.json"
        outside.write_text('{"secret":"DO_NOT_READ_OUTSIDE_EVIDENCE"}', encoding="utf-8")
        path = self.run_folder() / "manifest.json"
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(outside)
        try:
            detail = self.detail()
            self.assert_unknown_with_reply(detail)
            self.assertNotIn("DO_NOT_READ_OUTSIDE_EVIDENCE", json.dumps(detail))
            self.assertTrue(path.is_symlink())
            self.assertEqual('{"secret":"DO_NOT_READ_OUTSIDE_EVIDENCE"}', outside.read_text())
        finally:
            path.unlink()
            path.write_bytes(original)

    def test_oversized_evidence_is_rejected_before_loading_body(self):
        self.add_call()
        path = self.run_folder() / "manifest.json"
        original = path.read_bytes()
        try:
            with path.open("wb") as stream:
                stream.truncate(review.MAX_ARTIFACT_BYTES + 1)
            self.assert_unknown_with_reply(self.detail())
        finally:
            path.write_bytes(original)

    def test_reading_empty_reviews_has_no_filesystem_side_effect(self):
        self.add_call()
        before = self.source_bytes()
        result = review.read_reviews(self.folder)
        self.assertEqual([], result["reviews"])
        self.assertEqual([], result["gaps"])
        self.assertIn("version", result)
        self.assertFalse((self.folder / "review-notes").exists())
        self.assertEqual(before, self.source_bytes())

    def test_review_notes_are_immutable_idempotent_and_do_not_change_source(self):
        self.add_call()
        before = self.source_bytes()
        payload = self.payload()
        first = review.save_review(self.folder, self.session, payload)
        self.assertTrue(first["ok"])
        self.assertTrue(first["created"])
        files = {path: path.read_bytes() for path in (self.folder / "review-notes").iterdir() if path.is_file()}
        self.assertTrue(files)
        second = review.save_review(self.folder, self.session, payload)
        self.assertTrue(second["ok"])
        self.assertFalse(second["created"])
        self.assertEqual(first["review"], second["review"])
        self.assertEqual(self.session["calls"][0]["receipt"]["record_sha256"],
                         first["review"]["source"]["record_sha256"])
        self.assertEqual(sha_text(self.session["calls"][0]["receipt"]["answer"]),
                         first["review"]["source"]["message_sha256"])
        self.assertEqual(files, {path: path.read_bytes() for path in files})
        with self.assertRaises(ValueError):
            review.save_review(self.folder, self.session, dict(payload, note="Changed same request identity"))
        rows = review.read_reviews(self.folder)
        self.assertEqual([], rows["gaps"])
        self.assertEqual([first["review"]], rows["reviews"])
        self.assertEqual(before, self.source_bytes())
        self.assertNotIn("Synthetic supplied instructions", "".join(value.decode() for value in files.values()))

    def test_displayed_choices_and_host_prose_have_an_independent_review_pin(self):
        self.add_call(answer='{"candidates": []}')
        message = self.session['messages'][-1]
        questions = [{'question': 'Which next step?', 'options': ['Compare', 'Explain']}]
        message.update(acceptance_id='call-001-assistant', display_text='Host display A', questions=questions)
        detail = self.detail()
        self.assertEqual(questions, detail['displayed_questions']['items'])
        self.assertTrue(detail['displayed_questions']['available'])
        expected = digest({'text': 'Host display A', 'questions': questions, 'questions_status': 'present'})
        self.assertEqual(expected, detail['source']['displayed_sha256'])
        first_payload = self.payload()
        first = review.save_review(self.folder, self.session, first_payload)['review']
        message['display_text'] = 'Host display B'
        second = review.save_review(self.folder, self.session, self.payload())['review']
        self.assertEqual(first['source']['record_sha256'], second['source']['record_sha256'])
        self.assertEqual(first['source']['message_sha256'], second['source']['message_sha256'])
        self.assertNotEqual(first['source']['displayed_sha256'], second['source']['displayed_sha256'])
        self.assertEqual('Host display A', first['displayed_snapshot']['reply']['text'])
        self.assertEqual(questions, first['displayed_snapshot']['questions']['items'])
        self.assertEqual(first, review.save_review(self.folder, self.session, first_payload)['review'])
        message['questions'][0]['options'].reverse()
        self.assertNotEqual(second['source']['displayed_sha256'], self.detail()['source']['displayed_sha256'])
        self.assertEqual([], review.read_reviews(self.folder)['gaps'])

    def test_expected_preview_rejects_changed_display_before_new_review(self):
        self.add_call()
        message = self.session['messages'][-1]
        message.update(call_id='call-001-assistant', display_text='Inspected display', questions=[])
        expected = {k: self.detail()['source'][k] for k in review.EXPECTED_SOURCE_FIELDS}
        payload = self.payload(expected_source=expected)
        message['display_text'] = 'Changed after inspection'
        with self.assertRaisesRegex(ValueError, 'preview changed'):
            review.save_review(self.folder, self.session, payload)
        self.assertEqual([], review.read_reviews(self.folder)['reviews'])
        self.assertEqual([], list((self.folder / 'review-notes').glob('*.json')))

    def test_expected_preview_uuid_retry_returns_original_before_current_mismatch(self):
        self.add_call()
        expected = {k: self.detail()['source'][k] for k in review.EXPECTED_SOURCE_FIELDS}
        payload = self.payload(expected_source=expected)
        first = review.save_review(self.folder, self.session, payload)
        self.session['messages'][-1]['text'] = 'Changed display association'
        self.session['calls'][0]['receipt']['record_sha256'] = 'f' * 64
        second = review.save_review(self.folder, self.session, payload)
        self.assertFalse(second['created'])
        self.assertEqual(first['review'], second['review'])
        self.assertEqual([], review.read_reviews(self.folder)['gaps'])
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            review.save_review(self.folder, self.session, {k: v for k, v in payload.items() if k != 'expected_source'})

    def test_expected_preview_compares_each_hash_and_validates_shape(self):
        self.add_call()
        expected = {k: self.detail()['source'][k] for k in review.EXPECTED_SOURCE_FIELDS}
        for key in review.EXPECTED_SOURCE_FIELDS:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'preview changed'):
                review.save_review(self.folder, self.session,
                                   self.payload(expected_source=dict(expected, **{key: 'f' * 64})))
        for value in (None, {}, {'record_sha256': expected['record_sha256']},
                      dict(expected, unexpected='f' * 64), dict(expected, displayed_sha256='not-a-hash')):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'expected_source'):
                review.save_review(self.folder, self.session, self.payload(expected_source=value))
        self.assertEqual([], review.read_reviews(self.folder)['reviews'])

    def test_missing_displayed_questions_are_not_inferred_from_actor_json(self):
        raw = json.dumps({'message': 'Visible prose', 'questions': [
            {'question': 'Not saved in UI?', 'options': ['One', 'Two']} ]})
        self.add_call(answer=raw)
        self.session['messages'][-1].update(call_id='call-001-assistant', display_text='Visible prose')
        detail = self.detail()
        self.assertFalse(detail['displayed_questions']['available'])
        self.assertIsNone(detail['displayed_questions']['items'])
        self.assertEqual('missing', detail['displayed_questions']['status'])
        self.assertEqual(digest({'text': 'Visible prose', 'questions': None, 'questions_status': 'missing'}),
                         detail['source']['displayed_sha256'])

    def test_invalid_displayed_question_shapes_are_explicit_gaps(self):
        self.add_call()
        message = self.session['messages'][-1]
        message['call_id'] = 'call-001-assistant'
        for questions in (None, ['text'], [{'question': 'q', 'options': ['a', 'a']}],
                          [{'question': 'q', 'options': ['a', 'b'], 'html': '<script/>'}],
                          [{'question': 'q', 'options': ['a', 2]}]):
            with self.subTest(questions=questions):
                message['questions'] = questions
                detail = self.detail()
                self.assertFalse(detail['integrity']['ok'])
                self.assertEqual('invalid', detail['displayed_questions']['status'])
                self.assertIsNone(detail['source']['displayed_sha256'])
                self.assertTrue(detail['displayed_reply']['available'])

    def test_displayed_snapshot_is_bounded_but_hashes_complete_content(self):
        self.add_call()
        text = 'Full displayed text ' * review.MAX_BODY_CHARS
        self.session['messages'][-1].update(call_id='call-001-assistant', display_text=text, questions=[])
        saved = review.save_review(self.folder, self.session, self.payload())['review']
        snapshot = saved['displayed_snapshot']
        self.assertEqual(review.MAX_BODY_CHARS, len(snapshot['reply']['text']))
        self.assertTrue(snapshot['reply']['truncated'])
        self.assertEqual(sha_text(text), snapshot['reply']['sha256'])
        self.assertEqual(digest({'text': text, 'questions': [], 'questions_status': 'present'}), snapshot['sha256'])
        self.assertEqual([], review.read_reviews(self.folder)['gaps'])

    def test_legacy_review_remains_readable_without_invented_display_pin(self):
        self.add_call()
        saved = review.save_review(self.folder, self.session, self.payload())['review']
        path = next((self.folder / 'review-notes').glob('*.json'))
        saved['version'] = 1
        saved.pop('displayed_snapshot')
        saved['source'].pop('displayed_sha256')
        path.write_text(json.dumps({'value': saved, 'sha256': digest(saved)}))
        original = path.read_bytes()
        self.assertEqual([saved], review.read_reviews(self.folder)['reviews'])
        second = review.save_review(self.folder, self.session, self.payload())['review']
        self.assertEqual(2, second['version'])
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], review.read_reviews(self.folder)['gaps'])

    def test_displayed_snapshot_cannot_keep_old_pin_after_prose_change(self):
        self.add_call()
        review.save_review(self.folder, self.session, self.payload())
        path = next((self.folder / 'review-notes').glob('*.json'))
        saved = json.loads(path.read_text())
        block = saved['value']['displayed_snapshot']['reply']
        block.update(text='Changed display', total_chars=len('Changed display'), sha256=sha_text('Changed display'))
        saved['sha256'] = digest(saved['value'])
        path.write_text(json.dumps(saved))
        self.assertTrue(review.read_reviews(self.folder)['gaps'])

    def test_review_payload_allowlist_and_bounds(self):
        self.add_call()
        changes = [
            {"client_id": "not-a-uuid"}, {"client_id": "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"},
            {"call_id": "../outside"}, {"call_id": "missing-call"},
            {"reviewer": "user"}, {"rating": "excellent"}, {"severity": "critical"},
            {"reviewer": []}, {"rating": []}, {"rating": {}}, {"severity": []},
            {"tags": ["invented_tag"]}, {"tags": "cost"},
            {"note": "x" * 4001}, {"note": None}, {"unexpected": "field"},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                review.save_review(self.folder, self.session, self.payload(**change))
        allowed = ["missed_question", "condition_loss", "unsupported_claim", "process_jargon",
                   "no_progress", "tool_failure", "cost"]
        saved = review.save_review(self.folder, self.session, self.payload(
            reviewer="agent", rating="unrated", severity="none", tags=allowed, note="x" * 4000))
        self.assertTrue(saved["created"])
        self.assertCountEqual(allowed, saved["review"]["tags"])

    def test_corrupt_review_history_surfaces_gap_and_prevents_append(self):
        self.add_call()
        first = review.save_review(self.folder, self.session, self.payload())
        first_paths = set((self.folder / "review-notes").iterdir())
        review.save_review(self.folder, self.session, self.payload(note="Second independent observation"))
        second_paths = set((self.folder / "review-notes").iterdir()) - first_paths
        self.assertEqual(1, len(second_paths))
        corrupt = next(iter(second_paths))
        corrupt.write_text("{malformed", encoding="utf-8")
        read = review.read_reviews(self.folder)
        self.assertTrue(read["gaps"])
        self.assertIn(first["review"], read["reviews"])
        with self.assertRaises(ValueError):
            review.save_review(self.folder, self.session, self.payload(note="Must not hide corruption"))
        self.assertEqual("{malformed", corrupt.read_text())
        self.assertEqual(first_paths | second_paths, set((self.folder / "review-notes").iterdir()))

    def test_review_count_is_bounded_without_rewriting_existing_note(self):
        self.add_call()
        first = review.save_review(self.folder, self.session, self.payload())
        with mock.patch.object(review, "MAX_REVIEWS", 1):
            with self.assertRaises(ValueError):
                review.save_review(self.folder, self.session, self.payload(note="Beyond the cap"))
            self.assertEqual([first["review"]], review.read_reviews(self.folder)["reviews"])

    def test_symlink_review_directory_cannot_receive_notes(self):
        self.add_call()
        outside = self.folder.parent / "outside-reviews"
        outside.mkdir()
        keep = outside / "keep.txt"
        keep.write_text("unchanged", encoding="utf-8")
        (self.folder / "review-notes").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            review.read_reviews(self.folder)
        with self.assertRaises(ValueError):
            review.save_review(self.folder, self.session, self.payload())
        self.assertEqual([keep], list(outside.iterdir()))
        self.assertEqual("unchanged", keep.read_text())

    def export_packet(self):
        return {'session_id': 'synthetic-session', 'messages': [
            {'role': 'human', 'text': 'A question\nwith a second line'},
            {'role': 'assistant', 'text': 'Answer', 'display_text': 'Displayed answer',
             'questions': [{'question': 'Continue?', 'options': ['Yes', 'Later']}]}],
            'calls': [{'call_id': 'call-001-assistant'}], 'totals': {'input_tokens': {'value': None}},
            'reviews': {'reviews': [{'note': 'Retain this opinion'}]},
            'call_detail_routes': ['/api/synthetic/inspect/call-001-assistant'],
            'selected_call': {'call_id': 'call-001-assistant', 'tools': [
                {'id': 'tool-1', 'type': 'web_search', 'input': {'text': 'Query'},
                 'output': {'text': 'Evidence'}, 'raw': {'text': 'RAW TOOL'}}],
                'prompt': {'text': 'Bounded prompt', 'truncated': True, 'total_chars': 20000, 'sha256': 'a' * 64},
                'raw_actor_reply': {'text': 'Original actor answer'},
                'displayed_reply': {'text': 'Displayed answer'},
                'displayed_questions': {'items': [], 'status': 'present'},
                'raw_tool_events': {'text': 'FILTERED EVENTS'},
                'source': {'record_sha256': 'b' * 64}, 'integrity': {'ok': False, 'gaps': ['retained gap']}}}

    def test_exports_are_exact_private_artifacts_without_evidence_read_or_hardlinks(self):
        packet = self.export_packet()
        with mock.patch.object(review, '_read', side_effect=AssertionError('export must not reread evidence')), \
                mock.patch.object(review.os, 'link', side_effect=AssertionError('no hardlink dependency')):
            json_receipt = review.save_export(self.folder, packet, 'json')
            md_receipt = review.save_export(self.folder, packet, 'md')
        json_path, md_path = Path(json_receipt['path']), Path(md_receipt['path'])
        self.assertEqual(packet, json.loads(json_path.read_text()))
        self.assertEqual(review.export_markdown(packet), md_path.read_text())
        for receipt in (json_receipt, md_receipt):
            path = Path(receipt['path'])
            self.assertEqual(self.folder / 'review-exports', path.parent)
            self.assertEqual(0o700, path.parent.stat().st_mode & 0o777)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual(len(path.read_bytes()), receipt['bytes'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt['sha256'])
            self.assertEqual('.' + receipt['format'], path.suffix)
        self.assertNotEqual(json_path, Path(review.save_export(self.folder, packet, 'json')['path']))

    def test_export_collision_never_overwrites_a_file_or_hardlink(self):
        fixed = uuid.uuid4()
        directory = self.folder / 'review-exports'
        directory.mkdir()
        original = self.folder / 'keep.json'
        original.write_text('unchanged')
        target = directory / (str(fixed) + '.json')
        os.link(original, target)
        with mock.patch.object(review.uuid, 'uuid4', return_value=fixed), self.assertRaisesRegex(ValueError, 'already exists'):
            review.save_export(self.folder, self.export_packet(), 'json')
        self.assertEqual('unchanged', target.read_text())
        self.assertEqual('unchanged', original.read_text())

    def test_export_rejects_symlink_directory_or_target(self):
        outside = self.folder.parent / 'outside-export'
        outside.mkdir()
        directory = self.folder / 'review-exports'
        directory.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            review.save_export(self.folder, self.export_packet(), 'json')
        self.assertEqual([], list(outside.iterdir()))
        directory.unlink()
        directory.mkdir()
        fixed = uuid.uuid4()
        target = directory / (str(fixed) + '.json')
        target.symlink_to(outside / 'missing.json')
        with mock.patch.object(review.uuid, 'uuid4', return_value=fixed), self.assertRaises(ValueError):
            review.save_export(self.folder, self.export_packet(), 'json')
        self.assertFalse((outside / 'missing.json').exists())

    def test_hostile_export_roles_tool_ids_and_headers_remain_fenced(self):
        packet = self.export_packet()
        hostile = '\n```\n# HOSTILE_LABEL\n<script>alert(1)</script>\n````'
        packet['session_id'] = hostile
        packet['messages'][0]['role'] = hostile
        packet['selected_call']['call_id'] = hostile
        packet['selected_call']['tools'][0]['id'] = hostile
        packet['selected_call']['tools'][0]['type'] = hostile
        markdown = review.export_markdown(packet)
        fence, outside = None, []
        for line in markdown.splitlines():
            if fence is None:
                match = re.fullmatch(r'(`{3,})text', line)
                if match:
                    fence = match.group(1)
                else:
                    outside.append(line)
            elif line == fence:
                fence = None
        self.assertIsNone(fence)
        self.assertNotIn('HOSTILE_LABEL', '\n'.join(outside))
        self.assertNotIn('<script>', '\n'.join(outside))
        for retained in ('HOSTILE_LABEL', 'Original actor answer', 'Displayed answer',
                         'retained gap', '20000', 'Retain this opinion'):
            self.assertIn(retained, markdown)
        self.assertNotIn('FILTERED EVENTS', markdown)
        self.assertNotIn('RAW TOOL', markdown)
        self.assertEqual(1, markdown.count('Bounded prompt'))
        self.assertEqual(1, markdown.count('Original actor answer'))
        self.assertEqual(1, markdown.count('Evidence'))
        self.assertIn('exported_text_sha256', markdown)

    def test_export_limits_and_format_reject_without_partial_artifacts(self):
        with mock.patch.object(review, 'MAX_EXPORT_BYTES', 20):
            for format in ('json', 'md'):
                with self.subTest(format=format), self.assertRaisesRegex(ValueError, 'limit'):
                    review.save_export(self.folder, self.export_packet(), format)
        for format in ('../../bad', 'html', None, []):
            with self.subTest(format=format), self.assertRaises(ValueError):
                review.save_export(self.folder, self.export_packet(), format)
        self.assertFalse((self.folder / 'review-exports').exists())


if __name__ == "__main__":
    unittest.main()
