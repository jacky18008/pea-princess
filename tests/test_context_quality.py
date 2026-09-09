"""Offline regression checks for consequential pilot isolation and cost accounting."""
import copy
import json
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
import context_quality as q
from call_control import CallControl, CallControlPaused, PendingCallError


class ContextQualityTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "A1", "question": "What is supported?", "summary": "No verified result is available.",
                     "documents": [{"id": "D1", "title": "Receipt", "text": "The request never reached the service."},
                                   {"id": "D2", "title": "Source", "text": "Only these supplied facts are available."}],
                     "gold": {"required_findings": [{"id": "F1", "description": "secret rubric", "severity": "critical"}]}}

    def test_answer_prompts_do_not_leak_gold_or_unselected_sources(self):
        summary = q.analysis_prompt(self.case, "summary")
        self.assertNotIn("secret rubric", summary)
        self.assertNotIn("never reached", summary)
        full = q.analysis_prompt(self.case, "full")
        self.assertIn("never reached", full)
        retrieved = q.analysis_prompt(self.case, "adaptive", ["D2"], {"request_documents": ["D2"]})
        self.assertNotIn("never reached", retrieved)
        self.assertIn("Only these supplied facts", retrieved)

    def test_retrieval_cannot_escape_catalog_or_buy_extra_round(self):
        for ids in (["../../gold"], ["D1", "D1"], ["D1", "D2", "D1"], [1]):
            self.assertIsNotNone(q.validate_request(self.case, "adaptive", {"request_documents": ids}))
        self.assertIsNone(q.validate_request(self.case, "adaptive", {"request_documents": ["D1"]}))
        self.assertIsNotNone(q.validate_request(self.case, "adaptive", {"request_documents": ["D1"]}, final=True))
        self.assertIsNotNone(q.validate_request(self.case, "full", {"request_documents": ["D1"]}))

    def test_quotes_must_exist_in_actually_supplied_sources(self):
        answer = {"findings": [{"claim": "c", "evidence": [{"document_id": "D1", "quote": "request never reached"}]}]}
        self.assertEqual(q.citation_check(self.case, answer, ["D1"])["invalid"], 0)
        self.assertEqual(q.citation_check(self.case, answer, ["D2"])["invalid"], 1)
        answer["findings"][0]["evidence"][0]["quote"] = "fabricated quotation"
        self.assertEqual(q.citation_check(self.case, answer, ["D1"])["invalid"], 1)

    def test_adaptive_cost_includes_selection_and_final_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = {"id": "A1-adaptive-initial", "answer": {"request_documents": ["D1"], "answer": "need source", "findings": []},
                     "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}, "seconds": 1}
            final = copy.deepcopy(first)
            final.update(id="A1-adaptive-retrieved", answer={"request_documents": [], "answer": "supported", "findings": []})
            job = {"id": "A1-adaptive", "experiment": "analysis", "case_id": "A1", "arm": "adaptive"}
            with patch.object(q, "case_for", return_value=self.case), patch.object(q, "controlled_call", side_effect=[first, final]) as invoke:
                result = q.answer_job(out, job, {})
            self.assertEqual(invoke.call_count, 2)
            self.assertEqual(result["usage"]["total_tokens"], 220)
            self.assertEqual(result["supplied_document_ids"], ["D1"])

    def test_invalid_request_is_preserved_without_followup(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {"id": "A1-adaptive-initial", "answer": {"request_documents": ["outside"], "answer": "unknown", "findings": []},
                      "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}, "seconds": 1}
            job = {"id": "A1-adaptive", "experiment": "analysis", "case_id": "A1", "arm": "adaptive"}
            with patch.object(q, "case_for", return_value=self.case), patch.object(q, "controlled_call", return_value=record) as invoke:
                result = q.answer_job(Path(tmp), job, {"planned_call_ids": [job["id"] + "-initial", job["id"] + "-retrieved"]})
            self.assertEqual(invoke.call_count, 1)
            self.assertIsNotNone(result["protocol_violation"])

    def test_budget_stop_happens_before_process_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            q.write(out / "calls/previous/result.json", {"status": "complete", "usage": {"total_tokens": 100}})
            with patch.object(q.subprocess, "Popen") as popen, self.assertRaisesRegex(ValueError, "threshold"):
                q.invoke(out, "new", "prompt", q.RENTAL_SCHEMA, q.ANSWER_MODEL, "answer", {"maximum_cli_calls": 5, "reported_token_stop_threshold": 100})
            popen.assert_not_called()
            self.assertFalse((out / "calls/new").exists())

    def test_failed_call_never_automatically_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            q.write(out / "calls/failed/result.json", {"status": "stopped"})
            with patch.object(q.subprocess, "Popen") as popen, self.assertRaisesRegex(ValueError, "no automatic retry"):
                q.invoke(out, "failed", "prompt", q.RENTAL_SCHEMA, q.ANSWER_MODEL, "answer", {})
            popen.assert_not_called()

    def test_blind_judge_requires_each_candidate_and_criterion_once(self):
        good = {"assessments": [{"candidate_id": "candidate_1", "criteria": [{"id": "F1", "applicable": True, "met": True}]}]}
        q.validate_assessments(good, self.case, ["candidate_1"])
        bad = copy.deepcopy(good)
        bad["assessments"] *= 2
        with self.assertRaises(ValueError):
            q.validate_assessments(bad, self.case, ["candidate_1"])
        bad = copy.deepcopy(good)
        bad["assessments"][0]["criteria"] = []
        with self.assertRaises(ValueError):
            q.validate_assessments(bad, self.case, ["candidate_1"])

    def test_user_requested_format_has_independent_checks(self):
        self.assertTrue(q.rental_format_check("R4", {"answer": "1. Desk\n2. Washer\n3. Noise"})["pass"])
        self.assertFalse(q.rental_format_check("R4", {"answer": "1. Desk\n2. Washer"})["pass"])
        self.assertFalse(q.rental_format_check("R3", {"answer": "- one\n" * 7})["pass"])

    def test_nonterminal_fallback_cannot_replace_missing_terminal_usage(self):
        parsed = {"input_tokens": 100, "output_tokens": 10, "cached_input_tokens": 20, "total_tokens": 110}
        terminal = [{"type": "turn.completed", "usage": {k: parsed[k] for k in ("input_tokens", "output_tokens", "cached_input_tokens")}}]
        self.assertTrue(q.valid_terminal_usage(terminal, parsed))
        self.assertFalse(q.valid_terminal_usage([{"type": "turn.completed"}], parsed))
        self.assertFalse(q.valid_terminal_usage(terminal * 2, parsed))
        del terminal[0]["usage"]["cached_input_tokens"]
        self.assertFalse(q.valid_terminal_usage(terminal, parsed))

    def test_inconsistent_or_boolean_terminal_usage_is_not_complete(self):
        parsed = {"input_tokens": 100, "output_tokens": 10, "cached_input_tokens": 120, "total_tokens": 110}
        self.assertFalse(q.valid_terminal_usage([{"usage": parsed}], parsed))
        parsed["cached_input_tokens"] = False
        self.assertFalse(q.valid_terminal_usage([{"usage": parsed}], parsed))


class DurableContextQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "pilot"
        q.prepare(self.output)
        self.plan = q.read(self.output / "plan.json")
        self.started = []

    def start(self, command, stdin, stdout, stderr, request_documents=False, terminal=True):
        directory = Path(command[command.index("--cd") + 1])
        call_id = directory.name
        self.assertEqual([call_id], CallControl(self.output / "control", self.plan["planned_call_ids"]).report()["pending_call_ids"])
        self.started.append(call_id)
        fields = q.read(directory / "schema.json")["properties"]
        if "assessments" in fields:
            properties = fields["assessments"]["items"]["properties"]
            criteria = properties["criteria"]["items"]["properties"]["id"]["enum"]
            answer = {"assessments": [{"candidate_id": label,
                "criteria": [{"id": key, "applicable": True, "met": False, "reason": "offline stub"} for key in criteria],
                "unsupported_claims": [], "contradictions": [], "useful_next_step": False,
                "appropriate_uncertainty": True, "user_burden_ok": True, "overall_notes": "offline stub"}
                for label in properties["candidate_id"]["enum"]]}
        elif "findings" in fields:
            requested = []
            if request_documents and call_id.endswith("adaptive-initial"):
                case = next(c for c in q.read(self.output / "analysis-cases.json")["cases"] if c["id"] == call_id.split("-")[0])
                requested = [case["documents"][0]["id"]]
            answer = {"answer": "Unverified offline stub.", "request_documents": requested,
                      "findings": [], "limitations": [], "next_steps": []}
        else:
            answer = {"answer": "Unverified offline stub."}
        q.write(directory / "answer.txt", answer)
        events = [{"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(answer)}}]
        if terminal:
            events.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}})
        stdout.write("\n".join(json.dumps(event) for event in events))
        stdout.flush()
        return types.SimpleNamespace(wait=lambda timeout: 0, returncode=0)

    def first_call(self):
        job = self.plan["jobs"][0]
        return q.answer_job(self.output, job, self.plan)

    def test_entire_pilot_durable_dispatch_skip_and_idempotent_replay(self):
        with patch.object(q.launch, "start_process", side_effect=self.start), patch.object(q.launch, "finish_process"), redirect_stdout(io.StringIO()):
            q.run(self.output)
            q.run(self.output)
        self.assertEqual(34, len(self.started))
        summary = q.read(self.output / "summary.json")
        self.assertTrue(summary["complete"])
        self.assertEqual(4, summary["controller"]["skipped_calls"])
        self.assertEqual(408, summary["controller"]["usage"]["total_tokens"])
        self.assertTrue(summary["usage_coverage_complete"])
        self.assertEqual([], summary["raw_artifact_integrity_failures"])
        self.assertTrue({"bench/call_control.py", "bench/report_control.py"}.issubset(self.plan["source_sha256"]))
        for path in (self.output / "calls").glob("*/*"):
            self.assertEqual(0, path.stat().st_mode & 0o077)

    def test_adaptive_second_round_has_its_own_durable_dispatch(self):
        def start(*args, **kwargs):
            return self.start(*args, **kwargs, request_documents=True)
        with patch.object(q.launch, "start_process", side_effect=start), patch.object(q.launch, "finish_process"), redirect_stdout(io.StringIO()):
            q.run(self.output)
        summary = q.read(self.output / "summary.json")
        self.assertTrue(summary["complete"])
        self.assertEqual(38, len(self.started))
        self.assertEqual(0, summary["controller"]["skipped_calls"])

    def test_missing_telemetry_pauses_and_retains_failed_record(self):
        def start(*args, **kwargs):
            return self.start(*args, **kwargs, terminal=False)
        with patch.object(q.launch, "start_process", side_effect=start), patch.object(q.launch, "finish_process"), redirect_stdout(io.StringIO()):
            with self.assertRaises(CallControlPaused):
                self.first_call()
            with self.assertRaises(CallControlPaused):
                q.answer_job(self.output, self.plan["jobs"][1], self.plan)
        self.assertEqual(1, len(self.started))
        self.assertTrue(CallControl(self.output / "control", self.plan["planned_call_ids"]).report()["paused"])

    def test_pending_dispatch_blocks_every_later_call(self):
        control = CallControl(self.output / "control", self.plan["planned_call_ids"])
        control.dispatch(self.plan["planned_call_ids"][0], "job", "answer", "answer")
        with patch.object(q.launch, "start_process") as start, self.assertRaises(PendingCallError):
            q.answer_job(self.output, self.plan["jobs"][1], self.plan)
        start.assert_not_called()
        self.assertEqual(1, control.report()["dispatched_calls"])

    def test_budget_stop_does_not_create_a_dispatch(self):
        self.plan["reported_token_stop_threshold"] = 0
        with patch.object(q.launch, "start_process") as start, self.assertRaisesRegex(ValueError, "threshold"):
            self.first_call()
        start.assert_not_called()
        self.assertEqual(0, CallControl(self.output / "control", self.plan["planned_call_ids"]).report()["dispatched_calls"])

    def test_missing_raw_result_cannot_replay_controller_record(self):
        with patch.object(q.launch, "start_process", side_effect=self.start), patch.object(q.launch, "finish_process"), redirect_stdout(io.StringIO()):
            answer = self.first_call()
            (self.output / "calls" / answer["call_ids"][0] / "result.json").unlink()
            with self.assertRaisesRegex(ValueError, "missing its raw result"):
                self.first_call()
        self.assertEqual(1, len(self.started))

    def test_tampered_raw_events_are_rejected_before_replay(self):
        with patch.object(q.launch, "start_process", side_effect=self.start), patch.object(q.launch, "finish_process"), redirect_stdout(io.StringIO()):
            answer = self.first_call()
            (self.output / "calls" / answer["call_ids"][0] / "events.jsonl").write_text("changed")
            with self.assertRaisesRegex(ValueError, "artifact differs"):
                self.first_call()
        self.assertEqual(1, len(self.started))
        self.assertEqual(1, len(q.summarize(self.output)["raw_artifact_integrity_failures"]))


if __name__ == "__main__":
    unittest.main()
