"""Offline regression checks for consequential pilot isolation and cost accounting."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
import context_quality as q


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
            with patch.object(q, "case_for", return_value=self.case), patch.object(q, "invoke", side_effect=[first, final]) as invoke:
                result = q.answer_job(out, job, {})
            self.assertEqual(invoke.call_count, 2)
            self.assertEqual(result["usage"]["total_tokens"], 220)
            self.assertEqual(result["supplied_document_ids"], ["D1"])

    def test_invalid_request_is_preserved_without_followup(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {"id": "A1-adaptive-initial", "answer": {"request_documents": ["outside"], "answer": "unknown", "findings": []},
                      "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}, "seconds": 1}
            job = {"id": "A1-adaptive", "experiment": "analysis", "case_id": "A1", "arm": "adaptive"}
            with patch.object(q, "case_for", return_value=self.case), patch.object(q, "invoke", return_value=record) as invoke:
                result = q.answer_job(Path(tmp), job, {})
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


if __name__ == "__main__":
    unittest.main()
