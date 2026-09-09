"""Offline protection of causal comparisons, provenance and whole-pipeline accounting."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
import ablation_study as a
import context_quality as q
from call_control import CallControlPaused


class AblationTests(unittest.TestCase):
    def test_complete_matrix_has_unique_calls_and_optional_phases(self):
        rental = {"cases": [{"id": "S%d" % i, "turns": [{"id": "T1"}, {"id": "T2"}]} for i in range(1, 4)]}
        retrieval = {"cases": [{"id": "E%d" % i} for i in range(1, 4)]}
        calls, groups = a.schedule(rental, retrieval)
        self.assertEqual(len(calls), 158)
        self.assertEqual(len(set(calls)), 158)
        self.assertEqual(sum(c.endswith("-retrieved") for c in calls), 6)
        self.assertEqual(sum(len(g["jobs"]) for g in groups), 108)
        self.assertEqual(a.schedule(rental, retrieval), (calls, groups))

    def test_ablations_preserve_same_facts_and_do_not_mutate_generator_output(self):
        original = {"summary": "A compact narrative.", "facts": [
            {"id": "f1", "key": "budget", "value": "2000", "qualification": "reported", "source_id": "U1", "quote": "budget is 2000", "status": "superseded", "supersedes": []},
            {"id": "f2", "key": "budget", "value": "1900", "qualification": "reported", "source_id": "T1", "quote": "budget is now 1900", "status": "current", "supersedes": ["f1"]},
        ]}
        frozen = copy.deepcopy(original)
        for arm in a.RENTAL_ARMS[2:]:
            view = a.memory_view(original, arm)["facts"]
            self.assertEqual([f["value"] for f in view], ["2000", "1900"])
            self.assertEqual("source_id" in view[0], arm not in ("state_no_sources", "state_neither"))
            self.assertEqual("quote" in view[0], "source_id" in view[0])
            self.assertEqual("status" in view[0], arm not in ("state_no_updates", "state_neither"))
            self.assertEqual("supersedes" in view[0], "status" in view[0])
        self.assertEqual(original, frozen)
        self.assertEqual(a.memory_view(original, "prose"), original["summary"])

    def test_next_turn_packet_does_not_leak_future_or_rubric(self):
        case = {"history": [{"id": "U1", "role": "user", "text": "initial evidence"}],
                "turns": [{"id": "T1", "text": "first change", "gold": "SECRET GOLD"}, {"id": "T2", "text": "FUTURE CHANGE", "gold": "SECRET GOLD"}]}
        memory = {"summary": "memo", "facts": []}
        for arm in a.RENTAL_ARMS:
            first = a.rental_packet(case, 0, arm, memory, None)
            self.assertNotIn("FUTURE CHANGE", json.dumps(first))
            self.assertNotIn("SECRET GOLD", json.dumps(first))
            second = a.rental_packet(case, 1, arm, memory, {"answer": "previous answer"})
            self.assertFalse(second["previous_answer_is_source_evidence"])
            self.assertEqual(second["your_previous_answer"]["answer"], "previous answer")

    def test_generator_cannot_cite_assistant_or_future_as_user_evidence(self):
        memory = {"facts": [{"id": "f1", "source_id": "A1", "quote": "minimum area is 42", "supersedes": []}]}
        messages = [{"id": "U1", "role": "user", "text": "minimum area is 40"}, {"id": "A1", "role": "assistant", "text": "minimum area is 42"}]
        self.assertEqual(a.memory_check(memory, messages)["invalid_quotes"], 1)
        memory["facts"][0].update(source_id="U1", quote="minimum area is 40", supersedes=["missing"])
        checked = a.memory_check(memory, messages)
        self.assertEqual(checked["invalid_quotes"], 0)
        self.assertEqual(checked["invalid_supersedes"], 1)

    def test_scalar_check_distinguishes_requirement_from_property_measurement(self):
        expected = [{"key": "minimum_area_m2", "expected_value": "40", "source_ids": ["U1"]}]
        self.assertEqual(a.check_facts({"facts": [{"key": "minimum_area_m2", "value": "42"}]}, expected)["passed"], 0)
        self.assertEqual(a.check_facts({"facts": [{"key": "minimum_area_m2", "value": "40 m²"}]}, expected)["passed"], 1)
        duplicate = {"facts": [{"key": "minimum_area_m2", "value": "40"}] * 2}
        self.assertTrue(a.check_facts(duplicate, expected)["duplicate_or_unknown_keys"])
        self.assertEqual(a.check_facts(duplicate, expected)["passed"], 0)
        self.assertNotEqual(a.normalize_scalar("unknown"), a.normalize_scalar("0"))
        self.assertEqual(a.normalize_scalar("2027-03-03T15:00"), a.normalize_scalar("2027-03-03 15:00"))

    def test_fact_prompt_never_contains_expected_values_or_gold(self):
        case = {"fact_checks": [{"key": "minimum_area_m2", "expected_value": "SECRET_VALUE", "source_ids": ["SECRET_SOURCE"]}], "gold": "SECRET_RUBRIC"}
        prompt = a.fact_instructions(case)
        self.assertIn("minimum_area_m2", prompt)
        self.assertNotIn("SECRET", prompt)
        self.assertNotIn("SECRET", json.dumps(a.answer_schema(case)))

    def test_judge_visibility_can_be_ablated_without_altering_candidate_answer(self):
        case = {"id": "X", "gold": {"required_findings": []}}
        candidates = {"candidate_1": {"response": {"answer": "RESPONSE"}, "available_evidence": {"summary": "ONLY_THIS"}}}
        legacy = a.make_judge_prompt(case, candidates, False)
        visible = a.make_judge_prompt(case, candidates, True)
        self.assertIn("RESPONSE", legacy)
        self.assertIn("RESPONSE", visible)
        self.assertNotIn("ONLY_THIS", legacy)
        self.assertIn("ONLY_THIS", visible)

    def test_lexical_ranker_uses_only_actual_question_and_documents(self):
        docs = [{"id": "D1", "title": "Receipt", "text": "dispatch manifest collision"}, {"id": "D2", "title": "Other", "text": "quarterly food preferences"}, {"id": "D3", "title": "Cases", "text": "manifest collision repeated"}]
        selected, _ = a.lexical_select("manifest collision", docs)
        self.assertEqual(set(selected), {"D1", "D3"})
        self.assertEqual(a.lexical_select("manifest collision", docs), a.lexical_select("manifest collision", docs))

    def test_shared_memory_is_counted_once_per_pipeline_and_once_actual_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            q.write(out / "plan.json", {"source_commit": "test"})
            for name, tokens, purpose in [("memory1", 100, "memory"), ("memory2", 80, "memory"), ("answer1", 20, "answer"), ("answer2", 30, "answer")]:
                q.write(out / "calls" / name / "result.json", {"id": name, "status": "complete", "purpose": purpose, "usage": {"total_tokens": tokens}})
            for i, dependencies in [(1, ["memory1"]), (2, ["memory1", "memory2"])]:
                q.write(out / "answers" / (str(i) + ".json"), {"id": str(i), "experiment": "rental", "arm": "state", "call_ids": ["answer%d" % i], "dependency_call_ids": dependencies, "fact_check": {"passed": 0, "total": 0}, "citation_check": None, "protocol_violation": None})
            result = a.summarize(out)
            self.assertEqual(result["known_cli_processed_tokens"], 230)
            self.assertEqual(result["arms"]["rental/state"]["dependency_tokens"], 180)
            self.assertEqual(result["arms"]["rental/state"]["standalone_pipeline_tokens"], 230)
            self.assertFalse(result["complete"])

    def test_invocation_exception_retains_failed_usage_and_blocks_next_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            q.write(out / "plan.json", {"planned_call_ids": ["first", "second"], "answer_model": q.ANSWER_MODEL, "judge_model": q.JUDGE_MODEL,
                                         "maximum_cli_calls": 2, "reported_token_stop_threshold": 1000})
            study = a.Study(out)
            failed = {"id": "first", "status": "stopped", "errors": [{"type": "turn.failed"}], "terminal_usage_events": 1, "direct_terminal_usage": {"input_tokens": 90, "cached_input_tokens": 20, "output_tokens": 10}}
            def failing(output, call_id, *args):
                q.write(output / "calls" / call_id / "result.json", failed)
                raise ValueError("preserved failure")
            with patch.object(q, "invoke", side_effect=failing) as invoke:
                with self.assertRaises(CallControlPaused):
                    study.call("first", "p", q.RENTAL_SCHEMA, "answer")
                with self.assertRaises(CallControlPaused):
                    study.call("second", "p", q.RENTAL_SCHEMA, "answer")
                self.assertEqual(invoke.call_count, 1)
            self.assertEqual(study.control.report()["usage"]["total_tokens"], 100)

    def test_orphan_call_directory_cannot_be_reported_as_complete_zero_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            q.write(out / "plan.json", {"source_commit": "test"})
            (out / "calls/unresolved").mkdir(parents=True)
            summary = a.summarize(out)
            self.assertEqual(summary["calls"], 1)
            self.assertEqual(summary["missing_result_call_ids"], ["unresolved"])
            self.assertFalse(summary["usage_coverage_complete"])
            self.assertIsNone(summary["cli_processed_tokens"])
            self.assertEqual(summary["known_cli_processed_tokens"], 0)
            self.assertFalse(summary["complete"])

    def test_entire_frozen_matrix_runs_through_real_controller_with_stub_models(self):
        """Exercise every stage, grouped judge shape and adaptive second call offline."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "study"
            a.prepare(out)
            invoked = []
            def fake(output, call_id, prompt, schema, model, purpose, plan):
                invoked.append(call_id)
                fields = schema["properties"]
                if "assessments" in fields:
                    inner = fields["assessments"]["items"]["properties"]
                    labels = inner["candidate_id"]["enum"]
                    criterion_ids = inner["criteria"]["items"]["properties"]["id"]["enum"]
                    answer = {"assessments": [{"candidate_id": label, "criteria": [{"id": key, "applicable": True, "met": False, "reason": "offline stub"} for key in criterion_ids], "unsupported_claims": [], "contradictions": [], "useful_next_step": False, "appropriate_uncertainty": True, "user_burden_ok": True, "overall_notes": "offline stub"} for label in labels]}
                elif "summary" in fields:
                    answer = {"summary": "No independent verification in this offline stub."}
                    if "facts" in fields:
                        answer["facts"] = []
                else:
                    keys = fields["facts"]["items"]["properties"]["key"]["enum"]
                    answer = {"answer": "Unknown; offline stub answer.", "facts": [{"key": key, "value": "unknown", "source_ids": []} for key in keys]}
                    if "request_documents" in fields:
                        answer.update(request_documents=[call_id[:2] + "-D01"] if call_id.endswith("-adaptive") else [], findings=[], limitations=[], next_steps=[])
                record = {"id": call_id, "purpose": purpose, "status": "complete", "exit_code": 0, "timeout": False,
                          "errors": [], "tool_events": [], "malformed_event_lines": 0, "terminal_usage_events": 1,
                          "direct_terminal_usage": {"input_tokens": 90, "cached_input_tokens": 20, "output_tokens": 10},
                          "usage": {"input_tokens": 90, "cached_input_tokens": 20, "output_tokens": 10, "total_tokens": 100}, "answer": answer}
                q.write(output / "calls" / call_id / "result.json", record)
                return record
            with patch.object(q, "invoke", side_effect=fake):
                result = a.run(out)
            self.assertTrue(result["complete"])
            self.assertEqual(len(invoked), 158)
            summary = q.read(out / "summary.json")
            self.assertEqual(len(summary["answers"]), 108)
            self.assertEqual(summary["known_cli_processed_tokens"], 15800)
            self.assertEqual(summary["controller"]["usage"]["total_tokens"], 15800)
            self.assertEqual(summary["controller"]["decision"], "report_results")
            self.assertEqual(summary["arms"]["rental/state"]["dependency_tokens"], 1200)
            self.assertEqual(summary["arms"]["retrieval/raw_full"]["dependency_tokens"], 0)
            self.assertEqual(summary["arms"]["retrieval/adaptive"]["answer_calls"], 12)


if __name__ == "__main__":
    unittest.main()
