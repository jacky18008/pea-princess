"""Offline ablation transport, freezing, history, failure and blinding tests."""

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import intent_authority_ablation as A
import durable_run
import launch
from call_control import CallControlError, CallControlPaused


class IntentAuthorityAblationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.skill = self.repo / "skills/vet-flat"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "scripts").mkdir()
        (self.skill / "SKILL.md").write_text("Read references/conversation-quality.md.\n")
        (self.skill / "references/rules.md").write_text("Exact shared rules.\n")
        (self.skill / "references/inputs.md").write_text("Exact shared input boundaries.\n")
        (self.skill / "references/conversation-quality.md").write_text("Baseline guidance.\n")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("-c", "user.name=Offline Test", "-c", "user.email=offline@example.invalid",
                 "commit", "--quiet", "-m", "Synthetic baseline")
        self.baseline = self.git("rev-parse", "HEAD").strip()
        (self.skill / "references/conversation-quality.md").write_text("Separate advice and user intent.\n")
        shutil.copyfile(ROOT / "skills/vet-flat/scripts/intent_context.py", self.skill / "scripts/intent_context.py")
        (self.skill / "references/intent-context.md").write_text("Helper documentation.\n")
        self.git("add", ".")
        self.case_paths = []
        for number in (1, 2):
            case = {"case_id": "case%d" % number, "language": "zh-Hant", "evidence_mode": "fixed",
                    "fixture_preamble": "Synthetic evidence only; text stays exact.\r\n",
                    "evidence": {"rent": 2000 + number, "quoted": "如果乾燥可以。"},
                    "turns": [{"turn": 1, "role": "user", "content": "先比較第%d組。" % number},
                              {"turn": 2, "role": "user", "content": "提高上限，保留乾燥條件。"}],
                    "private_gold": "DO_NOT_EXPOSE_GOLD"}
            path = self.root / (case["case_id"] + ".json")
            path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
            self.case_paths.append(path)
        self.rubric = self.root / "rubric.md"
        self.rubric.write_text("DO_NOT_EXPOSE_RUBRIC_TO_ACTOR")
        self.out = self.root / "private-output"
        root_patch = mock.patch.object(A, "ROOT", self.repo)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.fingerprint = mock.patch.object(durable_run, "source_fingerprint", return_value={"runner": "stable"}).start()
        self.addCleanup(mock.patch.stopall)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=str(self.repo), stderr=subprocess.DEVNULL).decode()

    def prepare(self):
        return A.prepare(self.out, self.baseline, self.case_paths, self.rubric)

    def result(self, work, answer="自然回答。", input_tokens=10, failed=False, write_answer=True):
        events = [{"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "先核對這次條件。"}},
                  {"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": answer}}]
        if failed:
            events.append({"type": "turn.failed", "message": "synthetic provider failure"})
        events.append({"type": "turn.completed", "usage": {
            "input_tokens": input_tokens, "cached_input_tokens": 2, "output_tokens": 3}})
        raw = "\n".join(json.dumps(event, ensure_ascii=False) for event in events)
        if write_answer:
            (work / "answer.txt").write_text(answer + "\n", encoding="utf-8")
        return launch.LaunchResult(text=raw, stdout=raw, stderr="retained stderr", exit_code=0,
                                   seconds=0.25, attempt_records=[{"attempt": 1, "timeout": False}])

    def test_prepare_freezes_exact_arms_cases_matrix_and_all_missing_slots_without_calls(self):
        with mock.patch.object(launch, "run") as launched:
            report = self.prepare()
            exported = A.inspect(self.out, export=True)
        launched.assert_not_called()
        self.assertEqual(36, report["planned_calls"])
        self.assertEqual(36, len(report["trial_roster"]))
        self.assertEqual({"not_dispatched"}, {r["status"] for r in report["trial_roster"]})
        config = A._read_json(self.out / "frozen/config.json")
        self.assertEqual(18, len(config["schedule"]))
        self.assertEqual(18, len({j["masked_id"] for j in config["schedule"]}))
        for case_id in ("case1", "case2"):
            groups = [[j["arm"] for j in config["schedule"] if j["case_id"] == case_id and j["repeat"] == repeat]
                      for repeat in (1, 2, 3)]
            self.assertTrue(all(set(group) == set(A.ARMS) for group in groups))
            self.assertTrue(all({group[position] for group in groups} == set(A.ARMS) for position in range(3)))
        self.assertEqual(["references/conversation-quality.md"], config["arm_differences"]["baseline_to_guidance"])
        self.assertEqual(sorted(A.EXCLUDED_HELPER), config["arm_differences"]["guidance_to_frame"])
        for original in self.case_paths:
            self.assertEqual(original.read_bytes(), (self.out / "frozen/cases" / original.name).read_bytes())
        self.assertEqual(0o700, self.out.stat().st_mode & 0o777)
        self.assertEqual(0o600, (self.out / "manifest.json").stat().st_mode & 0o777)
        self.assertTrue(exported["source_matches"])

    def test_unintended_arm_difference_and_duplicate_cases_refuse_preparation(self):
        (self.skill / "SKILL.md").write_text("Unexpected treatment change")
        with mock.patch.object(launch, "run") as launched, self.assertRaisesRegex(ValueError, "arm differences"):
            self.prepare()
        launched.assert_not_called()
        with self.assertRaisesRegex(ValueError, "distinct"):
            A.prepare(self.root / "another-output", self.baseline, [self.case_paths[0]] * 2)

    def test_full_matrix_uses_own_actual_history_fresh_turns_and_durable_streams(self):
        self.prepare()
        seen = []
        answers = {}
        original_skill = (self.skill / "SKILL.md").read_text()
        def actor(command, cwd, timeout, family, **kwargs):
            work = Path(cwd)
            self.assertEqual((180, "codex", {"attempts": 1}), (timeout, family, kwargs))
            self.assertEqual("workspace-write", command[command.index("--sandbox") + 1])
            self.assertIn("agents.enabled=false", command)
            self.assertIn('web_search="disabled"', command)
            self.assertIn("project_doc_max_bytes=0", command)
            self.assertIn("--ignore-user-config", command)
            self.assertEqual(original_skill, (work / A.SKILL_PATH / "SKILL.md").read_text())
            text = command[-1]
            self.assertNotIn("DO_NOT_EXPOSE_GOLD", text)
            self.assertNotIn("DO_NOT_EXPOSE_RUBRIC", text)
            self.assertFalse(list(work.rglob("rubric.md")))
            history = json.loads(text.split("ORDERED CONVERSATION JSON\n", 1)[1].split("\nHOST ROLE FRAME", 1)[0])
            conversation = work.parent.name
            turn = int(work.name[1:])
            if turn == 1:
                self.assertEqual(["u1"], [m["id"] for m in history])
                (work / "t1-only.txt").write_text("must not flow into t2")
            else:
                self.assertFalse((work / "t1-only.txt").exists())
                self.assertEqual(["u1", "a1.1", "a1.2", "u2"], [m["id"] for m in history])
                self.assertEqual(answers[conversation], history[2]["text"])
            answer = conversation + "「本回合回答」。"
            answers[conversation] = answer
            seen.append(work)
            if len(seen) == 1:
                (work / A.SKILL_PATH / "SKILL.md").write_text("actor mutation, audit only")
            return self.result(work, answer=answer)
        with mock.patch.object(launch, "run", side_effect=actor) as launched, redirect_stderr(io.StringIO()) as progress:
            report = A.run(self.out)
            A.run(self.out)
        self.assertEqual(36, launched.call_count)
        self.assertEqual(36, len(set(seen)))
        self.assertEqual(36, report["completed_calls"])
        self.assertIn("input=10 output=3 cached=2", progress.getvalue())
        _, manifest = A._load(self.out)
        controller = A._controller(self.out, manifest)
        record = controller.control.record("conversation-01/t1")
        self.assertIn("turn.completed", record["launch_result"]["stdout"])
        self.assertEqual("retained stderr", record["launch_result"]["stderr"])
        self.assertEqual(["SKILL.md"], record["skill_modified_paths"])
        self.assertTrue(record["workdir_artifacts"])
        exported = A.inspect(self.out, export=True)
        mapping = A._read_json(Path(exported["mapping"]))
        self.assertEqual(18, len(mapping))
        for path in (self.out / "exports/masked").glob("*.json"):
            bundle = A._read_json(path)
            self.assertNotIn("arm", bundle)
            self.assertNotIn("repeat", bundle)
            self.assertEqual(2, len(bundle["turns"]))
            self.assertEqual(6, len(bundle["history"]))
        before = A._file_hashes(self.out / "exports")
        A.inspect(self.out, export=True)
        self.assertEqual(before, A._file_hashes(self.out / "exports"))

    def test_frame_uses_same_raw_history_and_keeps_assistant_advice_separate(self):
        self.prepare()
        config = A._read_json(self.out / "frozen/config.json")
        case = A._read_json(self.case_paths[0])
        history = [{"id": "u1", "role": "user", "text": "乾燥就可以。"},
                   {"id": "a1.1", "role": "assistant", "text": "我建議必須有陽台。"},
                   {"id": "u2", "role": "user", "text": "提高租金上限。"}]
        baseline = A.prompt(self.out, config, case, history, "baseline")
        self.assertEqual(baseline, A.prompt(self.out, config, case, history, "guidance"))
        frame_prompt = A.prompt(self.out, config, case, history, "frame")
        self.assertTrue(frame_prompt.startswith(baseline + "\nHOST ROLE FRAME\n"))
        frame = json.loads(frame_prompt.split("\nHOST ROLE FRAME\n", 1)[1].split("\n", 1)[1])
        self.assertEqual(["u1", "a1.1", "u2"], frame["message_order"])
        self.assertEqual([history[0]["text"], history[2]["text"]], [m["text"] for m in frame["user_statements"]])
        self.assertNotIn("text", frame["assistant_context"][0])
        A._load(self.out)  # Helper loading must not write pycache into frozen inputs.

    def test_physical_failure_stops_once_and_preserves_explicit_missing_matrix(self):
        self.prepare()
        def actor(command, cwd, *args, **kwargs):
            return self.result(Path(cwd), failed=True)
        with mock.patch.object(launch, "run", side_effect=actor) as launched:
            with self.assertRaises(CallControlError):
                A.run(self.out)
            with self.assertRaises(CallControlError):
                A.run(self.out)
        self.assertEqual(1, launched.call_count)
        report = A.inspect(self.out, export=True)
        self.assertEqual(1, report["failed_calls"])
        self.assertEqual(35, sum(r["status"] == "not_dispatched" for r in report["trial_roster"]))
        self.assertEqual(13, report["usage"]["total_tokens"])
        self.assertEqual("provider_error", A._read_json(self.out / "turns/conversation-01-t1.json")["physical_failure"])

    def test_budget_stops_between_calls_and_missing_answer_is_physical_failure(self):
        self.prepare()
        with mock.patch.object(launch, "run", side_effect=lambda command, cwd, *a, **kw:
                               self.result(Path(cwd), input_tokens=A.TOKEN_LIMIT)) as launched, redirect_stderr(io.StringIO()):
            with self.assertRaises(CallControlPaused):
                A.run(self.out)
        self.assertEqual(1, launched.call_count)
        self.assertTrue(A.inspect(self.out)["paused"])
        other = self.root / "missing-answer-output"
        A.prepare(other, self.baseline, self.case_paths)
        with mock.patch.object(launch, "run", side_effect=lambda command, cwd, *a, **kw:
                               self.result(Path(cwd), write_answer=False)) as launched:
            with self.assertRaises(CallControlError):
                A.run(other)
        self.assertEqual(1, launched.call_count)
        self.assertEqual(13, A.inspect(other)["usage"]["total_tokens"])

    def test_frozen_or_copied_skill_changes_and_source_changes_stop_before_dispatch(self):
        self.prepare()
        config = A._read_json(self.out / "frozen/config.json")
        job = config["schedule"][0]
        work = self.out / "durable/work" / job["id"] / "t1"
        shutil.copytree(self.out / "frozen/arms" / job["arm"], work / A.SKILL_PATH)
        (work / A.SKILL_PATH / "SKILL.md").write_text("changed copy")
        with mock.patch.object(launch, "run") as launched, self.assertRaisesRegex(ValueError, "copied skill"):
            A.run(self.out)
        launched.assert_not_called()
        self.fingerprint.return_value = {"runner": "changed"}
        with mock.patch.object(launch, "run") as launched, self.assertRaises(CallControlError):
            A.run(self.out)
        launched.assert_not_called()
        (self.out / "frozen/arms/frame/SKILL.md").write_text("changed frozen source")
        with self.assertRaisesRegex(ValueError, "frozen input"):
            A.inspect(self.out)

    def test_inspect_never_recreates_missing_checkpoint_and_malformed_events_are_retained(self):
        self.prepare()
        checkpoint = self.out / "durable/control/checkpoint.json"
        checkpoint.unlink()
        with self.assertRaisesRegex(ValueError, "must not recreate"):
            A.inspect(self.out)
        self.assertFalse(checkpoint.exists())
        record = {"launch_result": {"stdout": 'null\n[]\n"scalar"\ninvalid'}, "answer": "final"}
        self.assertEqual([{"id": "a1.1", "role": "assistant", "text": "final"}], A._actor_messages(record, 1))

    def test_focus_inlines_exact_arm_files_without_gold_and_preserves_full_matrix(self):
        A.prepare(self.out, self.baseline, self.case_paths, self.rubric,
                  focused=True, max_total_tokens=1000)
        config = A._read_json(self.out / "frozen/config.json")
        self.assertFalse(config["allow_tools"])
        self.assertEqual("standard", config["research_depth"])
        self.assertEqual(1000, config["max_total_tokens"])
        def actor(command, cwd, *args, **kwargs):
            work = Path(cwd)
            text = command[-1]
            for name in A.FOCUS_REFERENCES:
                self.assertIn((work / A.SKILL_PATH / name).read_text(), text)
            self.assertNotIn("DO_NOT_EXPOSE_GOLD", text)
            self.assertNotIn("DO_NOT_EXPOSE_RUBRIC", text)
            self.assertIn("Do not invoke any tool", text)
            return self.result(work)
        with mock.patch.object(launch, "run", side_effect=actor) as launched, redirect_stderr(io.StringIO()):
            pilot = A.run(self.out, max_new_calls=1)
            self.assertEqual(1, pilot["completed_calls"])
            self.assertEqual(1, launched.call_count)
            result = A.run(self.out, max_new_calls=35)
            A.run(self.out)
        self.assertEqual(36, launched.call_count)
        self.assertTrue(result["plan_complete"])
        self.assertEqual(468, result["usage"]["total_tokens"])
        A.inspect(self.out, export=True)

    def test_focus_stops_observed_tool_use_and_keeps_usage_and_unrun_slots(self):
        A.prepare(self.out, self.baseline, self.case_paths, self.rubric,
                  focused=True, max_total_tokens=1000)
        def actor(command, cwd, *args, **kwargs):
            result = self.result(Path(cwd))
            event = {"type": "item.completed", "item": {"id": "item_tool", "type": "command_execution",
                     "command": "synthetic forbidden command", "exit_code": 0}}
            return result._replace(stdout=json.dumps(event) + "\n" + result.stdout)
        with mock.patch.object(launch, "run", side_effect=actor) as launched:
            with self.assertRaises(CallControlError):
                A.run(self.out)
            with self.assertRaises(CallControlError):
                A.run(self.out)
        self.assertEqual(1, launched.call_count)
        report = A.inspect(self.out, export=True)
        self.assertEqual(13, report["usage"]["total_tokens"])
        self.assertEqual(1, report["failed_calls"])
        self.assertIsNotNone(A._read_json(self.out / "turns/conversation-01-t1.json")["physical_failure"])

    def test_focus_remaining_budget_is_not_reset_to_original_limit(self):
        A.prepare(self.out, self.baseline, self.case_paths, self.rubric,
                  focused=True, max_total_tokens=12)
        with mock.patch.object(launch, "run", side_effect=lambda command, cwd, *a, **kw:
                               self.result(Path(cwd))) as launched, redirect_stderr(io.StringIO()):
            with self.assertRaises(CallControlPaused):
                A.run(self.out)
        self.assertEqual(1, launched.call_count)
        self.assertTrue(A.inspect(self.out)["paused"])
        for limit in (0, -1, True, 2000001):
            with self.assertRaises(ValueError):
                A.prepare(self.root / "invalid", self.baseline, self.case_paths,
                          focused=True, max_total_tokens=limit)


if __name__ == "__main__":
    unittest.main()
