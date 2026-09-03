#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline tests for the A/B harness: config loading, gold rules, aggregation, dry runs.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

Nothing here touches the network or a real agent. The gold-rule tests need
bench/private/build_gold.py, which is private and gitignored, so they skip when it is
not there; everything else runs on synthetic data in a temp directory.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
AB = os.path.join(BENCH, "ab")
PRIVATE = os.path.join(BENCH, "private")

for path in (BENCH, AB, PRIVATE, os.path.join(ROOT, "skills", "vet-flat", "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

import run as runner                      # noqa: E402
import grade_ab                           # noqa: E402
import run_ab                             # noqa: E402

HAS_PRIVATE = os.path.exists(os.path.join(PRIVATE, "build_gold.py"))
if HAS_PRIVATE:
    import build_gold                     # noqa: E402


# --------------------------------------------------------------- fixtures --
def report(codes, verdict="CONDITIONAL", questions=None, unknown_axes=0):
    return {
        "schema_version": "1",
        "candidates": [{
            "id": "c1",
            "verdict": {"status": verdict, "headline": "h", "reason_codes": list(codes)},
            "landmines": [{"code": c, "label": "l", "detail": "d", "reversible": False}
                          for c in codes],
            "killer_questions": list(questions or []),
            "axes": [{"id": i + 1, "name": "a", "finding": "f",
                      "evidence_class": "U" if i < unknown_axes else "G"}
                     for i in range(12)],
        }],
    }


def gold_doc(cases):
    """cases = [(id, verdict, [high codes], [low codes], [questions])]"""
    return {
        "description": "synthetic",
        "candidates": [{
            "id": cid,
            "address": "somewhere",
            "gold_verdict": verdict,
            "gold_landmines": ([{"code": c, "confidence": "high", "name": c} for c in high]
                               + [{"code": c, "confidence": "low", "name": c} for c in low]),
            "gold_killer_questions": [{"text": q, "source": "test"} for q in questions],
            "notes": "",
        } for cid, verdict, high, low, questions in cases],
    }


def scorecard_row(config, case, run, report_path, **kw):
    row = {
        "run_at": "2026-09-04T00:00:00Z", "agent": "claude", "model": None,
        "config": config, "config_phase": kw.pop("phase", "core"),
        "config_factor": "f", "budget_mode": "standard", "run_index": run,
        "case": case, "gold_id": case, "kind": "report",
        "fact_recall": 0.95, "stable_fact_recall": 0.96, "fabrications": 0,
        "hard_filter_consistency": 1.0, "killer_questions_from_bank": 1.0,
        "schema_valid": True, "total_tokens": 100000, "total_cost_usd": 0.3,
        "wall_time_s": 100.0, "report_path": report_path, "note": None,
    }
    row.update(kw)
    return row


class Workspace(object):
    """A results directory with a scorecard, reports and a gold file."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="vetflat-ab-test-")
        self.results = os.path.join(self.dir, "results", "2026-09-04")
        os.makedirs(self.results)
        self.n = 0

    def report(self, *args, **kw):
        self.n += 1
        path = os.path.join(self.dir, "report-%d.json" % self.n)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report(*args, **kw)))
        return path

    def write(self, rows, gold):
        with io.open(os.path.join(self.results, "scorecard.json"), "w",
                     encoding="utf-8") as fh:
            fh.write(json.dumps(rows))
        self.gold = os.path.join(self.dir, "gold.json")
        with io.open(self.gold, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(gold))

    def grade(self, argv=None):
        code = grade_ab.main((argv or []) + ["--results", self.results,
                                             "--gold", self.gold, "--quiet"])
        assert code == 0, "grade_ab exited %s" % code
        with io.open(os.path.join(self.results, "summary.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


# ------------------------------------------------------------ config loading --
class ConfigLoading(unittest.TestCase):
    def test_every_shipped_config_loads(self):
        configs = runner.list_configs()
        self.assertGreaterEqual(len(configs), 13)
        names = [c["name"] for c in configs]
        for expected in ("A-legacy", "B-lean", "C-twenty", "B-raw", "B-opus-workers",
                         "B-lite", "B-main-opus", "B-main-sonnet", "codex-A-raw-sol",
                         "codex-B-lean-sol", "codex-C-terra-lite", "codex-C-luna-lite",
                         "codex-D-luna-standard"):
            self.assertIn(expected, names)
        for cfg in configs:
            self.assertIn(cfg["phase"], ("core", "ablation"), cfg["name"])
            self.assertIn(cfg["agent"], ("claude", "codex"), cfg["name"])
            self.assertIn(cfg["budget_mode"], ("standard", "lite"), cfg["name"])
            self.assertTrue(cfg.get("factor"), cfg["name"])
            self.assertTrue(cfg.get("append_system_prompt"), cfg["name"])

    def test_core_set_is_the_six_named_arms(self):
        core = sorted(c["name"] for c in runner.list_configs() if c["phase"] == "core")
        self.assertEqual(core, ["A-legacy", "B-lean", "C-twenty", "codex-B-lean-sol",
                                "codex-C-luna-lite", "codex-C-terra-lite"])

    def test_legacy_arm_has_web_tools_and_lean_arm_does_not(self):
        a = runner.load_config("A-legacy")
        b = runner.load_config("B-lean")
        self.assertIn("WebFetch", a["allowed_tools"])
        self.assertNotIn("WebFetch", b["allowed_tools"])
        self.assertIn("Bash(python3:*)", b["allowed_tools"])
        self.assertIsNone(a["main_model"])
        self.assertIsNone(b["main_model"])

    def test_twenty_pound_arm_cannot_spawn_subagents(self):
        c = runner.load_config("C-twenty")
        self.assertNotIn("Agent", c["allowed_tools"])
        self.assertEqual(c["main_model"], "sonnet")
        self.assertEqual(c["budget_mode"], "lite")

    def test_block_scalars_and_lists_and_nulls(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "x.yaml")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("# a comment\n"
                         "name: X\n"
                         "main_model: null\n"
                         "budget_mode: lite\n"
                         "allowed_tools:\n"
                         '  - "Bash(python3:*)"\n'
                         "  - Read\n"
                         "append_system_prompt: |\n"
                         "  one line\n"
                         "  and another\n"
                         "notes: |\n"
                         "  tail\n")
            cfg = runner.load_config(path)
            self.assertEqual(cfg["name"], "X")
            self.assertIsNone(cfg["main_model"])
            self.assertEqual(cfg["allowed_tools"], ["Bash(python3:*)", "Read"])
            self.assertEqual(cfg["append_system_prompt"], "one line and another")
            self.assertEqual(cfg["notes"], "tail")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_command_carries_the_appendix_the_tools_and_the_model(self):
        cfg = runner.load_config("C-twenty")
        cmd = runner.build_command("claude", {"prompt": "p"}, None, "/tmp/wd", "p", cfg)
        self.assertEqual(cmd[:3], ["claude", "-p", "p"])
        self.assertIn("--append-system-prompt", cmd)
        self.assertIn(cfg["append_system_prompt"], cmd)
        self.assertIn("--allowedTools", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        self.assertNotIn("--dangerously-skip-permissions", cmd)
        self.assertNotIn("--allow-dangerously-skip-permissions", cmd)

    def test_a_codex_config_through_run_py_is_a_usage_error_not_a_silent_drop(self):
        code = runner.main(["--agent", "codex", "--config", "codex-B-lean-sol",
                            "--case", "nothing", "--dry-run"])
        self.assertEqual(code, 2)

    def test_no_config_asks_for_a_permission_bypass(self):
        for cfg in runner.list_configs():
            blob = json.dumps(cfg).lower()
            self.assertNotIn("dangerously", blob, cfg["name"])
            self.assertNotIn("skip-permissions", blob, cfg["name"])

    def test_budget_mode_is_written_into_the_profile(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "profile.yaml")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("min_floor_area_sqft: 490\nbudget_mode: standard\nlanguage: \"en\"\n")
            runner.apply_budget_mode(tmp, "lite")
            with io.open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("budget_mode: lite", text)
            self.assertNotIn("budget_mode: standard", text)
            self.assertIn("min_floor_area_sqft: 490", text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_budget_mode_is_appended_when_the_profile_has_no_key(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "profile.yaml")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("min_floor_area_sqft: 490\n")
            runner.apply_budget_mode(tmp, "lite")
            with io.open(path, encoding="utf-8") as fh:
                self.assertIn("budget_mode: lite", fh.read())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------- gold rules --
@unittest.skipUnless(HAS_PRIVATE, "bench/private/build_gold.py is private and gitignored")
class GoldRules(unittest.TestCase):
    def codes(self, **fields):
        reviewed = {"verdict": "", "risk": "", "negative": "", "decision": "",
                    "review": {}, "adversarial_v5": {}, "axes": {}}
        reviewed.update(fields.pop("reviewed", {}))
        normalized = fields.pop("normalized", None)
        mines = build_gold.derive_landmines(reviewed, normalized)
        return dict((m["code"], m["confidence"]) for m in mines)

    def test_a_topic_word_without_a_problem_is_not_a_landmine(self):
        got = self.codes(reviewed={"risk": "本戶熱網由社區供應，EPC面積52m²，管理由代管公司負責。"})
        self.assertEqual(got, {})

    def test_heat_network_with_an_unknown_tariff_is_L6(self):
        got = self.codes(reviewed={"risk": "熱網固定費未確認。"})
        self.assertEqual(got.get("L6"), "high")

    def test_area_contradiction_is_L1_high(self):
        got = self.codes(reviewed={"review": {"strongest_objection":
                                              "廣告面積643sqft與圖載有差，戶號/EPC仍缺。"}})
        self.assertEqual(got.get("L1"), "high")

    def test_a_survey_line_only_is_low_confidence(self):
        got = self.codes(reviewed={"axes": {"aspect_open_sky": "遮擋與夏溫未確認。"}})
        self.assertEqual(got.get("L2"), "low")

    def test_a_decisive_line_beats_a_survey_line(self):
        got = self.codes(reviewed={"risk": "遮擋未確認。",
                                   "axes": {"aspect_open_sky": "遮擋與夏溫未確認。"}})
        self.assertEqual(got.get("L2"), "high")

    def test_money_gate_words_are_L12(self):
        got = self.codes(reviewed={"negative": "商保與押金方案未確認，房東法人不明。"})
        self.assertEqual(got.get("L12"), "high")

    def test_english_problem_markers_work_too(self):
        got = self.codes(reviewed={"risk": "The heat network standing charge is unknown."})
        self.assertEqual(got.get("L6"), "high")

    def test_status_tokens_map_straight_to_codes(self):
        got = self.codes(normalized={"status": "KILL_AREA"})
        self.assertEqual(got.get("L1"), "high")
        got = self.codes(normalized={"status": "HOLD_REMEDIATION_COMMUTE"})
        self.assertEqual(got.get("L5"), "high")

    def test_verdict_layers_and_hold_becomes_conditional(self):
        status, rule, layers = build_gold.map_verdict(
            {"verdict": "EDGE|only at a lower rent", "decision": "x"}, {"status": "HOLD_X"})
        self.assertEqual(status, "EDGE")
        self.assertEqual(layers["P3_normalized_status"], "CONDITIONAL")
        status, rule, _ = build_gold.map_verdict({"verdict": "", "decision": "資格HOLD，先問再看"},
                                                None)
        self.assertEqual(status, "CONDITIONAL")
        self.assertIn("P2", rule)

    def test_status_vocabulary_falls_through_to_the_normalized_file(self):
        status, rule, _ = build_gold.map_verdict({"verdict": "", "decision": ""},
                                                 {"status": "KILL_AREA"})
        self.assertEqual(status, "KILL")
        self.assertIn("P3", rule)

    def test_address_cleaning_drops_campaign_shorthand(self):
        self.assertEqual(build_gold.clean_address("Valentine Place / Dexters279709"),
                         "Valentine Place")
        self.assertEqual(build_gold.clean_address("25 Goswell Road, EC1M 7AJ (unit501/502未定)"),
                         "25 Goswell Road, EC1M 7AJ")


# --------------------------------------------------------- grader arithmetic --
class LandmineAndVerdictScores(unittest.TestCase):
    def setUp(self):
        self.gold = {"id": "c1", "gold_verdict": "CONDITIONAL",
                     "gold_landmines": [{"code": "L1", "confidence": "high"},
                                        {"code": "L6", "confidence": "high"},
                                        {"code": "L2", "confidence": "low"}],
                     "gold_killer_questions": [
                         {"text": "What is the internal floor area on the energy certificate, "
                                  "and which certificate is it?"},
                         {"text": "Please send the heat network standing charge and unit rate "
                                  "in writing."}]}

    def cand(self, *args, **kw):
        return grade_ab.first_candidate(report(*args, **kw))

    def test_recall_counts_only_high_confidence_gold(self):
        got = grade_ab.landmine_scores(self.cand(["L1"]), self.gold)
        self.assertEqual(got["landmine_recall"], 0.5)
        self.assertEqual(got["codes_dropped"], 1)
        self.assertEqual(got["missed_high"], ["L6"])

    def test_a_low_confidence_gold_code_is_not_an_invention(self):
        got = grade_ab.landmine_scores(self.cand(["L1", "L6", "L2"]), self.gold)
        self.assertEqual(got["landmine_recall"], 1.0)
        self.assertEqual(got["landmine_precision"], 1.0)
        self.assertEqual(got["extra"], [])
        self.assertEqual(got["landmine_recall_low_confidence"], 1.0)

    def test_a_code_nobody_asked_for_costs_precision(self):
        got = grade_ab.landmine_scores(self.cand(["L1", "L6", "L9"]), self.gold)
        self.assertEqual(got["landmine_recall"], 1.0)
        self.assertAlmostEqual(got["landmine_precision"], 2 / 3.0, places=3)
        self.assertEqual(got["extra"], ["L9"])

    def test_verdict_exact_and_kill_split(self):
        got = grade_ab.verdict_scores(self.cand([], verdict="CONDITIONAL"), self.gold)
        self.assertTrue(got["verdict_agreement"])
        self.assertTrue(got["verdict_agreement_kill_split"])
        got = grade_ab.verdict_scores(self.cand([], verdict="EDGE"), self.gold)
        self.assertFalse(got["verdict_agreement"])
        self.assertTrue(got["verdict_agreement_kill_split"])
        got = grade_ab.verdict_scores(self.cand([], verdict="KILL"), self.gold)
        self.assertFalse(got["verdict_agreement_kill_split"])

    def test_question_overlap_uses_content_words(self):
        cand = self.cand([], questions=[
            "What is the internal floor area on the energy certificate for this exact flat, "
            "and which certificate number is it?",
            "Do you have a dog?"])
        got = grade_ab.question_scores(cand, self.gold, [])
        self.assertEqual(got["killer_questions"], 2)
        self.assertEqual(got["killer_questions_matched"], 1)
        self.assertEqual(got["killer_question_overlap"], 0.5)

    def test_chinese_questions_match_chinese_gold(self):
        gold = dict(self.gold)
        gold["gold_killer_questions"] = [{"text": "完整戶號與政府EPC？本戶實際冷熱網費率？"}]
        cand = self.cand([], questions=["完整戶號與政府EPC？本戶實際冷熱網費率？"])
        got = grade_ab.question_scores(cand, gold, [])
        self.assertEqual(got["killer_question_overlap"], 1.0)

    def test_unknown_share_counts_axes_graded_U(self):
        self.assertEqual(grade_ab.unknown_share(self.cand([], unknown_axes=3)), 0.25)
        self.assertEqual(grade_ab.unknown_share(self.cand([], unknown_axes=0)), 0.0)


class Aggregation(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def build(self, spec, gold=None):
        """spec = [(config, case, run, codes, verdict, extra row fields)]"""
        rows = []
        for config, case, run, codes, verdict, extra in spec:
            path = self.ws.report(codes, verdict=verdict,
                                  questions=["What is the internal floor area on the energy "
                                             "certificate, and which certificate is it?"])
            rows.append(scorecard_row(config, case, run, path, **extra))
        self.ws.write(rows, gold or gold_doc([
            ("c1", "CONDITIONAL", ["L1", "L6"], ["L2"], ["What is the internal floor area on "
                                                         "the energy certificate, and which "
                                                         "certificate is it?"]),
            ("c2", "EDGE", ["L1", "L6"], [], ["What is the internal floor area on the energy "
                                              "certificate, and which certificate is it?"]),
        ]))
        return self.ws.grade()

    def test_paired_difference_and_count_of_cases_b_wins(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("A-legacy", "c2", 1, ["L1", "L6"], "EDGE", {"total_tokens": 200000}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
            ("B-lean", "c2", 1, ["L1"], "EDGE", {"total_tokens": 80000}),
        ])
        lm = summary["paired"]["landmine_recall"]
        self.assertEqual(lm["per_case"]["c1"], 0.0)
        self.assertEqual(lm["per_case"]["c2"], -0.5)
        self.assertEqual(lm["mean_diff"], -0.25)
        self.assertEqual(lm["candidate_at_least_baseline"], 1)
        self.assertEqual(lm["candidate_worse"], 1)
        self.assertEqual(summary["paired"]["total_tokens"]["mean_diff"], -120000.0)

    def test_adopt_when_cheap_and_no_worse(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("A-legacy", "c1", 2, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 210000}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
            ("B-lean", "c1", 2, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 82000}),
        ])
        self.assertEqual(summary["decision"]["decision"], "ADOPT B")

    def test_keep_a_when_b_is_not_cheap_enough(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("A-legacy", "c1", 2, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("B-lean", "c1", 1, [], "PASS", {"total_tokens": 199000,
                                             "fact_recall": 0.5}),
            ("B-lean", "c1", 2, [], "PASS", {"total_tokens": 199000,
                                             "fact_recall": 0.5}),
        ])
        self.assertEqual(summary["decision"]["decision"], "KEEP A")
        self.assertIn("tokens did not fall", summary["decision"]["why"])

    def test_undecided_when_the_difference_is_inside_the_run_to_run_spread(self):
        # B is dearer, so the ADOPT rule fails; but every difference is smaller than the
        # spread the arms show against themselves, so nothing was measured.
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 100000,
                                                                "fact_recall": 0.90}),
            ("A-legacy", "c1", 2, ["L1"], "CONDITIONAL", {"total_tokens": 100000,
                                                          "fact_recall": 0.98}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 100000,
                                                              "fact_recall": 0.90}),
            ("B-lean", "c1", 2, ["L1"], "CONDITIONAL", {"total_tokens": 100000,
                                                        "fact_recall": 0.98}),
        ])
        self.assertEqual(summary["decision"]["decision"], "UNDECIDED")
        self.assertIn("noise", summary["decision"]["why"])

    def test_basic_functions_line_is_separate_from_the_adopt_rule(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
            ("C-twenty", "c1", 1, ["L1"], "CONDITIONAL", {"total_tokens": 20000}),
        ])
        block = [b for b in summary["basic_functions"] if b["config"] == "C-twenty"][0]
        self.assertEqual(block["result"], "PASS")
        self.assertNotIn("C-twenty", json.dumps(summary["decision"]))

    def test_basic_functions_fails_on_a_fabrication(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {}),
            ("C-twenty", "c1", 1, ["L1"], "CONDITIONAL", {"fabrications": 2}),
        ])
        block = [b for b in summary["basic_functions"] if b["config"] == "C-twenty"][0]
        self.assertEqual(block["result"], "FAIL")
        self.assertFalse(block["checks"]["fabrications == 0"])

    def test_factor_table_names_the_effect(self):
        summary = self.build([
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
            ("B-lean", "c1", 2, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
            ("B-raw", "c1", 1, [], "PASS", {"total_tokens": 400000, "phase": "ablation",
                                            "fact_recall": 0.4}),
            ("B-raw", "c1", 2, [], "PASS", {"total_tokens": 400000, "phase": "ablation",
                                            "fact_recall": 0.4}),
        ])
        row = [r for r in summary["factors"] if r["config"] == "B-raw"][0]
        self.assertEqual(row["effect"], "hurts")
        self.assertEqual(row["total_tokens"]["mean_diff"], 320000.0)

    def test_factor_table_says_within_noise_when_nothing_moved(self):
        summary = self.build([
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {}),
            ("B-lean", "c1", 2, ["L1", "L6"], "CONDITIONAL", {}),
            ("B-lite", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"phase": "ablation"}),
            ("B-lite", "c1", 2, ["L1", "L6"], "CONDITIONAL", {"phase": "ablation"}),
        ])
        row = [r for r in summary["factors"] if r["config"] == "B-lite"][0]
        self.assertEqual(row["effect"], "effect within noise")

    def test_min_max_and_spread_are_reported_per_config(self):
        summary = self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 100000}),
            ("A-legacy", "c1", 2, ["L1"], "CONDITIONAL", {"total_tokens": 300000}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 50000}),
        ])
        block = summary["per_config"]["A-legacy"]
        self.assertEqual(block["total_tokens"]["min"], 100000)
        self.assertEqual(block["total_tokens"]["max"], 300000)
        self.assertEqual(block["total_tokens"]["spread"], 200000)
        self.assertEqual(block["landmine_recall"]["min"], 0.5)
        self.assertEqual(block["landmine_recall"]["max"], 1.0)

    def test_summary_markdown_is_written_and_names_the_decision(self):
        self.build([
            ("A-legacy", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 200000}),
            ("B-lean", "c1", 1, ["L1", "L6"], "CONDITIONAL", {"total_tokens": 80000}),
        ])
        with io.open(os.path.join(self.ws.results, "summary.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("## Decision", text)
        self.assertIn("landmine recall", text)
        self.assertIn("A-legacy", text)


# ----------------------------------------------------------------- dry runs --
class Regrade(unittest.TestCase):
    """--regrade re-scores stored runs against the CURRENT cases file."""

    def setUp(self):
        self.ws = Workspace()
        self.cases = os.path.join(self.ws.dir, "cases.json")

    def tearDown(self):
        self.ws.close()

    def write_cases(self, facts):
        with io.open(self.cases, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"evals": [
                {"id": "c1", "address": "a", "prompt": "p", "files": [], "kind": "report",
                 "truth_inputs": {}, "expected_facts": facts}]}))

    def test_a_row_graded_against_an_empty_fact_table_is_rescored(self):
        path = self.ws.report(["L1"], questions=["q"])
        row = scorecard_row("B-lean", "c1", 1, path, facts="0/0", fact_recall=None,
                            total_tokens=1234, wall_time_s=99.0, total_cost_usd=0.5)
        self.ws.write([row], gold_doc([("c1", "CONDITIONAL", ["L1"], [], ["q"])]))
        self.write_cases({"epc": {"floor_area_m2": 52.0, "floor_area_sqft": 560}})
        done = grade_ab.regrade(self.ws.results, self.cases)
        self.assertEqual(done["regraded"], 1)
        with io.open(os.path.join(self.ws.results, "scorecard.json"), encoding="utf-8") as fh:
            after = json.load(fh)
        self.assertEqual(len(after), 1)
        self.assertNotEqual(after[0]["facts"], "0/0")     # a real fact table was applied
        self.assertEqual(after[0]["total_tokens"], 1234)  # the run's own numbers survive
        self.assertEqual(after[0]["wall_time_s"], 99.0)
        self.assertEqual(after[0]["run_at"], row["run_at"])
        self.assertTrue(after[0]["regraded_at"])

    def test_a_row_with_no_stored_report_is_left_alone(self):
        row = scorecard_row("A-legacy", "c1", 1, os.path.join(self.ws.dir, "gone.json"),
                            note="timed out")
        row["workdir"] = os.path.join(self.ws.dir, "nowhere")
        self.ws.write([row], gold_doc([("c1", "CONDITIONAL", ["L1"], [], ["q"])]))
        self.write_cases({})
        done = grade_ab.regrade(self.ws.results, self.cases)
        self.assertEqual(done["regraded"], 0)
        self.assertIn("no stored report", done["notes"][0])
        with io.open(os.path.join(self.ws.results, "scorecard.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)[0]["note"], "timed out")

    def test_rows_appended_during_the_regrade_are_not_lost(self):
        path = self.ws.report(["L1"], questions=["q"])
        first = scorecard_row("B-lean", "c1", 1, path)
        self.ws.write([first], gold_doc([("c1", "CONDITIONAL", ["L1"], [], ["q"])]))
        self.write_cases({})
        scorecard = os.path.join(self.ws.results, "scorecard.json")
        real_grade = grade_ab.grader.grade

        def racing(*args, **kw):
            rows = json.load(io.open(scorecard, encoding="utf-8"))
            rows.append(scorecard_row("B-lean", "c1", 2, path))   # a live sweep appends
            with io.open(scorecard, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(rows))
            grade_ab.grader.grade = real_grade
            return real_grade(*args, **kw)

        grade_ab.grader.grade = racing
        try:
            grade_ab.regrade(self.ws.results, self.cases)
        finally:
            grade_ab.grader.grade = real_grade
        rows = json.load(io.open(scorecard, encoding="utf-8"))
        self.assertEqual(sorted(r["run_index"] for r in rows), [1, 2])

    def test_the_markdown_is_rebuilt_with_one_line_per_row(self):
        path = self.ws.report(["L1"], questions=["q"])
        self.ws.write([scorecard_row("B-lean", "c1", 1, path),
                       scorecard_row("A-legacy", "c1", 1, path)],
                      gold_doc([("c1", "CONDITIONAL", ["L1"], [], ["q"])]))
        self.write_cases({})
        grade_ab.regrade(self.ws.results, self.cases)
        with io.open(os.path.join(self.ws.results, "scorecard.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text.count("| c1 |"), 2)
        self.assertEqual(text.count("# vet-flat benchmark"), 1)


class ReportExtraction(unittest.TestCase):
    def report_blob(self):
        return {"schema_version": "1",
                "candidates": [{"id": "x", "verdict": {"status": "EDGE", "headline": "h",
                                                       "reason_codes": []}}]}

    def test_claude_output_format_json_wrapper(self):
        blob = json.dumps({"type": "result", "usage": {},
                           "result": "here:\n```json\n%s\n```" % json.dumps(
                               self.report_blob())})
        got, where = grade_ab.scan_for_report(blob)
        self.assertEqual(got["candidates"][0]["id"], "x")
        self.assertIn("wrapper", where)

    def test_codex_jsonl_event_stream(self):
        lines = [json.dumps({"type": "start", "msg": {"text": "go"}}),
                 json.dumps({"type": "agent_message",
                             "msg": {"text": "wrote " + json.dumps(self.report_blob())}})]
        got, where = grade_ab.scan_for_report("\n".join(lines))
        self.assertEqual(got["candidates"][0]["id"], "x")
        self.assertIn("event stream", where)

    def test_the_schema_is_not_mistaken_for_a_report(self):
        schema = {"$schema": "http://json-schema.org/draft-07/schema#",
                  "properties": {"candidates": {"type": "array", "minItems": 1}}}
        self.assertFalse(grade_ab.looks_like_report(schema))
        self.assertEqual(grade_ab.scan_for_report(json.dumps(schema))[0], None)
        # the same fragment inside an event stream must also be rejected
        line = json.dumps({"msg": {"text": json.dumps(
            {"candidates": {"type": "array", "items": {"$ref": "#/definitions/candidate"}}})}})
        self.assertEqual(grade_ab.scan_for_report(line)[0], None)

    def test_the_last_report_in_a_stream_wins(self):
        first, second = self.report_blob(), self.report_blob()
        second["candidates"][0]["id"] = "final"
        lines = [json.dumps({"msg": {"text": json.dumps(first)}}),
                 json.dumps({"msg": {"text": json.dumps(second)}})]
        got, _ = grade_ab.scan_for_report("\n".join(lines))
        self.assertEqual(got["candidates"][0]["id"], "final")

    def test_nothing_to_find_is_none_not_a_crash(self):
        self.assertEqual(grade_ab.scan_for_report("")[0], None)
        self.assertEqual(grade_ab.scan_for_report("no json here at all")[0], None)


class WhyUnknown(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def summary(self, spec):
        rows = []
        for config, unknown in spec:
            rows.append(scorecard_row(config, "c1", 1,
                                      self.ws.report(["L1"], unknown_axes=0)))
            path = os.path.join(self.ws.dir, "r-%s.json" % config)
            blob = report(["L1"], questions=["q"])
            for axis in blob["candidates"][0]["axes"]:
                axis["evidence_class"] = "U" if axis["id"] in unknown else "G"
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(blob))
            rows[-1]["report_path"] = path
        self.ws.write(rows, gold_doc([("c1", "CONDITIONAL", ["L1"], [], ["q"])]))
        return self.ws.grade()

    def test_an_axis_unknown_everywhere_is_flagged_as_the_suite_ceiling(self):
        s = self.summary([("A-legacy", (8, 9)), ("B-lean", (8, 9))])
        unk = s["unknown"]
        self.assertEqual(unk["unknown_in_every_arm"], [8, 9])
        self.assertTrue(unk["shared_ceiling_has_no_input"])
        self.assertIn("8", unk["shared_ceiling_reasons"])

    def test_an_axis_that_differs_between_arms_is_surfaced(self):
        s = self.summary([("A-legacy", (2,)), ("B-lean", ())])
        unk = s["unknown"]
        by_axis = dict((r["axis"], r) for r in unk["axes"])
        self.assertEqual(by_axis[2]["spread"], 1.0)
        self.assertEqual(by_axis[2]["per_config"]["A-legacy"]["share"], 1.0)
        self.assertEqual(by_axis[2]["per_config"]["B-lean"]["share"], 0.0)
        self.assertIn(2, unk["differs_between_arms"])
        self.assertEqual(unk["unknown_in_every_arm"], [])

    def test_a_real_gap_is_not_excused_as_a_ceiling(self):
        s = self.summary([("A-legacy", (5,)), ("B-lean", (5,))])
        self.assertEqual(s["unknown"]["unknown_in_every_arm"], [5])
        self.assertFalse(s["unknown"]["shared_ceiling_has_no_input"])

    def test_the_table_reaches_the_markdown(self):
        self.summary([("A-legacy", (8,)), ("B-lean", (8,))])
        with io.open(os.path.join(self.ws.results, "summary.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Why an axis is unknown", text)
        self.assertIn("no open register records which way the windows face"
                      if "axis 9" in text else "price", text)


class RunAbDryRun(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="vetflat-ab-plan-")
        self.cases = os.path.join(self.dir, "cases.json")
        with io.open(self.cases, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"evals": [
                {"id": "case-a", "prompt": "p", "files": [], "kind": "report"},
                {"id": "case-b", "prompt": "p", "files": [], "kind": "report"}]}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def plan(self, configs, runs=1, resume=True, agent=None):
        cfgs = [runner.load_config(name) for name in configs]
        cases = run_ab.load_cases(self.cases)
        return run_ab.plan(cfgs, cases, runs, agent, self.cases,
                           results_root=os.path.join(self.dir, "results"),
                           day="2026-09-04", resume=resume)

    def test_configs_interleave_within_a_case(self):
        steps = self.plan(["A-legacy", "B-lean", "C-twenty"], runs=2)
        got = [(s["run"], s["case"], s["config"]) for s in steps]
        self.assertEqual(got[:3], [(1, "case-a", "A-legacy"), (1, "case-a", "B-lean"),
                                   (1, "case-a", "C-twenty")])
        self.assertEqual(got[3:6], [(1, "case-b", "A-legacy"), (1, "case-b", "B-lean"),
                                    (1, "case-b", "C-twenty")])
        self.assertEqual(got[6], (2, "case-a", "A-legacy"))
        self.assertEqual(len(steps), 12)

    def test_no_arm_ever_runs_twice_in_a_row(self):
        steps = self.plan(["A-legacy", "B-lean", "C-twenty"], runs=3)
        names = [s["config"] for s in steps]
        for i in range(1, len(names)):
            self.assertNotEqual(names[i], names[i - 1])

    def test_an_existing_raw_output_is_skipped(self):
        raw = os.path.join(self.dir, "results", "2026-09-04", "raw")
        os.makedirs(raw)
        with io.open(os.path.join(raw, runner.raw_name("B-lean", "case-a", 1)), "w",
                     encoding="utf-8") as fh:
            fh.write("{}")
        steps = self.plan(["A-legacy", "B-lean"], runs=1)
        done = [s for s in steps if s["skipped"]]
        self.assertEqual([(s["config"], s["case"]) for s in done], [("B-lean", "case-a")])
        self.assertEqual(sum(1 for s in steps if not s["skipped"]), 3)

    def test_no_resume_runs_everything_again(self):
        raw = os.path.join(self.dir, "results", "2026-09-04", "raw")
        os.makedirs(raw)
        with io.open(os.path.join(raw, runner.raw_name("B-lean", "case-a", 1)), "w",
                     encoding="utf-8") as fh:
            fh.write("{}")
        steps = self.plan(["A-legacy", "B-lean"], runs=1, resume=False)
        self.assertEqual(sum(1 for s in steps if s["skipped"]), 0)

    def test_codex_configs_dispatch_to_the_codex_runner(self):
        steps = self.plan(["B-lean", "codex-B-lean-sol"], runs=1)
        by_config = dict((s["config"], s) for s in steps)
        self.assertIn("run.py", " ".join(by_config["B-lean"]["command"]))
        self.assertIn("run_codex.py", " ".join(by_config["codex-B-lean-sol"]["command"]))
        self.assertEqual(by_config["codex-B-lean-sol"]["agent"], "codex")

    def test_agent_override_wins_over_the_config(self):
        steps = self.plan(["codex-B-lean-sol"], runs=1, agent="claude")
        self.assertIn("run.py", " ".join(steps[0]["command"]))

    def test_phase_selection(self):
        core = [c["name"] for c in run_ab.pick_configs(None, "core")]
        ablation = [c["name"] for c in run_ab.pick_configs(None, "ablation")]
        every = [c["name"] for c in run_ab.pick_configs(None, "all")]
        self.assertIn("B-lean", core)
        self.assertNotIn("B-raw", core)
        self.assertIn("B-raw", ablation)
        self.assertEqual(sorted(core + ablation), sorted(every))

    def test_named_configs_keep_the_order_they_were_given(self):
        got = [c["name"] for c in run_ab.pick_configs(["C-twenty", "A-legacy"], None)]
        self.assertEqual(got, ["C-twenty", "A-legacy"])

    def test_raw_file_names_are_config_case_run(self):
        self.assertEqual(runner.raw_name("B-lean", "v2-buck", 3), "B-lean-v2-buck-3.json")
        self.assertEqual(runner.raw_name("A/B", "c#zh", 1), "A-B-c#zh-1.json")


class WorkerEvalScoring(unittest.TestCase):
    def setUp(self):
        import worker_eval
        self.we = worker_eval

    def test_exact_string(self):
        self.assertEqual(self.we.score_answer("2.9", "2.9", 0)[0], "exact")
        self.assertEqual(self.we.score_answer(" 2.9. ", "2.9", 0)[0], "exact")
        self.assertEqual(self.we.score_answer("£1,250", "1250", 0)[0], "exact")

    def test_within_tolerance(self):
        self.assertEqual(self.we.score_answer("31", "30", 1)[0], "within")
        self.assertEqual(self.we.score_answer("33", "30", 1)[0], "miss")

    def test_a_set_answer_ignores_order(self):
        self.assertEqual(self.we.score_answer("Flat 3, Flat 1", ["Flat 1", "Flat 3"], 0)[0],
                         "exact")
        self.assertEqual(self.we.score_answer("Flat 1", ["Flat 1", "Flat 3"], 0)[0], "miss")

    def test_a_refusal_is_a_miss_not_a_crash(self):
        self.assertEqual(self.we.score_answer("NOT IN DOCUMENT", "2020-05-01", 0)[0], "miss")

    def test_command_uses_the_documented_alias_and_no_bypass(self):
        cmd = self.we.build_command("sonnet", "p")
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        self.assertIn("--output-format", cmd)
        self.assertNotIn("--dangerously-skip-permissions", cmd)


if __name__ == "__main__":
    unittest.main()
