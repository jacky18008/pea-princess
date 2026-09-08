# -*- coding: utf-8 -*-
"""The role pipeline: the plan scaffold, the config loader, the schemas and the dry run.

Nothing here starts a model. The dry run is the contract that matters: one command per
role, the right tool list on each, no permission-bypass flag anywhere, and stdin closed
next to every launch.
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SKILL = os.path.join(ROOT, "skills", "vet-flat")
SCRIPTS = os.path.join(SKILL, "scripts")
REFS = os.path.join(SKILL, "references")
FIX = os.path.join(HERE, "fixtures", "pipeline")
CONFIGS = os.path.join(ROOT, "bench", "ab", "configs")

sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "bench"))
import plan as P  # noqa: E402
import render  # noqa: E402  the repository's own schema checker
import pipeline as PL  # noqa: E402


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def fixture(name):
    with io.open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def schema(name):
    with io.open(os.path.join(REFS, name), encoding="utf-8") as fh:
        return json.load(fh)


class quiet(object):
    """Swallow stdout and stderr. run_pipeline() prints a scorecard line and a note per
    role; that is the tool doing its job, not the test reporting."""

    def __enter__(self):
        self.out, self.err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self.out, self.err
        return False


class Args(object):
    """A stand-in for the argparse.Namespace bench/pipeline.py's own CLI builds, for
    calling run_verifier()/run_executor_rounds() directly without going through main()."""

    def __init__(self, **kw):
        self.budget_mode = None
        self.gold = None
        self.gold_id = None
        self.strict = False
        self.timeout = 5
        self.day = None
        self.results = None
        self.run = 1
        self.case_row = None
        self.workdir = None
        self.keep = False
        self.dry_run = False
        for key, value in kw.items():
            setattr(self, key, value)


class ThePlanScaffold(unittest.TestCase):
    def test_each_depth_works_the_axes_budget_modes_promises(self):
        lite = P.scaffold("lite")
        standard = P.scaffold("standard")
        deep = P.scaffold("deep")
        self.assertEqual([a["id"] for a in lite["axes"]], [1, 2, 3, 5, 7, 8, 10, 11])
        self.assertEqual([a["id"] for a in standard["axes"]], list(range(1, 13)))
        self.assertEqual([a["id"] for a in deep["axes"]], list(range(1, 13)))

    def test_the_fixed_form_comes_from_the_tiers_block_and_is_never_counted_in_code(self):
        self.assertEqual(len(P.scaffold("lite")["fixed_form_ids"]), 8)
        self.assertEqual(len(P.scaffold("standard")["fixed_form_ids"]), 14)
        self.assertEqual(len(P.scaffold("deep")["fixed_form_ids"]), 18)
        source = read(os.path.join(SCRIPTS, "plan.py"))
        self.assertIn("scan.ids_for_tier", source)
        self.assertNotIn('range(1, 19)', source)

    def test_a_deeper_mode_only_ever_adds(self):
        for axis in range(1, 13):
            lite = [c for c, _w in P.calls_for(axis, "lite")]
            standard = [c for c, _w in P.calls_for(axis, "standard")]
            deep = [c for c, _w in P.calls_for(axis, "deep")]
            self.assertEqual(standard[:len(lite)], lite, axis)
            self.assertEqual(deep[:len(standard)], standard, axis)

    def test_it_is_deterministic(self):
        self.assertEqual(json.dumps(P.scaffold("standard")),
                         json.dumps(P.scaffold("standard")))

    def test_placeholders_are_filled_without_doubling_the_quotes(self):
        plan = P.scaffold("lite", values={"postcode": "XE1 9AA"})
        calls = [c["cmd"] for a in plan["axes"] for c in a["scripts"]]
        self.assertIn('scripts/geo.py lookup "XE1 9AA"', calls)
        self.assertFalse(any('""' in c for c in calls))

    def test_an_unfilled_placeholder_stays_visible(self):
        plan = P.scaffold("lite")
        calls = [c["cmd"] for a in plan["axes"] for c in a["scripts"]]
        self.assertIn('scripts/geo.py lookup "<postcode>"', calls)

    def test_the_skipped_axes_are_named_rather_than_dropped_quietly(self):
        note = P.scaffold("lite")["notes"]
        for name in ("construction nearby", "management and neighbours", "aspect and light"):
            self.assertIn(name, note)
        self.assertIsNone(P.scaffold("standard")["notes"])

    def test_every_axis_belongs_to_an_executor_group(self):
        for axis in P.scaffold("standard")["axes"]:
            self.assertTrue(axis["group"])
        self.assertEqual(sorted(set(P.GROUP_OF.values())),
                         ["commute", "fabric", "identity-area", "money", "neighbourhood",
                          "people", "place"])

    def test_every_planned_script_is_a_script_that_exists(self):
        for mode in P.MODES:
            for axis in P.scaffold(mode)["axes"]:
                for call in axis["scripts"]:
                    name = call["cmd"].split()[0].split("/")[-1]
                    self.assertTrue(os.path.exists(os.path.join(SCRIPTS, name)),
                                    "%s does not exist" % name)


class ThePlanCheck(unittest.TestCase):
    def good(self):
        return copy.deepcopy(P.scaffold("standard", values={"postcode": "XE1 9AA"}))

    def test_the_scaffold_checks_out_against_itself(self):
        self.assertTrue(P.check(self.good(), "standard")["ok"])

    def test_a_dropped_axis_is_caught(self):
        plan = self.good()
        plan["axes"] = [a for a in plan["axes"] if a["id"] != 5]
        result = P.check(plan, "standard")
        self.assertFalse(result["ok"])
        self.assertEqual([a["id"] for a in result["missing_axes"]], [5])

    def test_a_dropped_call_is_caught(self):
        plan = self.good()
        for axis in plan["axes"]:
            if axis["id"] == 11:
                axis["scripts"] = axis["scripts"][:-1]
        result = P.check(plan, "standard")
        self.assertFalse(result["ok"])
        self.assertEqual([c["axis"] for c in result["missing_calls"]], [11])

    def test_a_dropped_fixed_question_is_caught(self):
        plan = self.good()
        plan["fixed_form_ids"] = plan["fixed_form_ids"][:-2]
        result = P.check(plan, "standard")
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing_fixed_form_ids"], ["F13", "F14"])

    def test_adding_is_allowed(self):
        plan = self.good()
        plan["axes"].append({"id": 12, "name": "extra", "group": "place", "required": False,
                             "scripts": [{"cmd": "scripts/geo.py nearby --lat 1 --lng 2"}]})
        plan["axes"][0]["scripts"].append({"cmd": 'scripts/epc.py search --street "X Street"'})
        result = P.check(plan, "standard")
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["added_calls"], 1)

    def test_a_filled_placeholder_still_matches_the_template(self):
        plan = P.scaffold("standard", values={"postcode": "XE1 9AA", "destination": "XW1 1AA"})
        self.assertTrue(P.check(plan, "standard")["ok"],
                        "the check compares the shape of a call, never its values")

    def test_the_wrong_schema_string_fails(self):
        plan = self.good()
        plan["schema"] = "something-else"
        self.assertFalse(P.check(plan, "standard")["ok"])

    def test_the_command_line_exits_one_when_the_plan_shrank(self):
        path = os.path.join(FIX, "plan-standard.json")
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "plan.py"),
                                 "--check", path, "--mode", "standard", "--table"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _err = proc.communicate()
        self.assertEqual(proc.returncode, 0, out.decode("utf-8"))
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "plan.py"),
                                 "--check", path, "--mode", "deep", "--table"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _err = proc.communicate()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SHRUNK", out.decode("utf-8"))


class TheSchemas(unittest.TestCase):
    def check(self, data, schema_name):
        validator = render.Validator(schema(schema_name))
        validator.check(data, schema(schema_name), "")
        self.assertEqual(validator.errors, [], schema_name)
        self.assertEqual(validator.warnings, [], schema_name)

    def test_the_sample_plan_validates(self):
        self.check(fixture("plan-standard.json"), "plan-schema.json")

    def test_a_freshly_built_scaffold_validates_at_every_depth(self):
        for mode in P.MODES:
            self.check(P.scaffold(mode, values={"postcode": "XE1 9AA"}),
                       "plan-schema.json")

    def test_the_sample_evidence_validates(self):
        self.check(fixture("evidence-good.json"), "evidence-schema.json")
        self.check(fixture("evidence-bad.json"), "evidence-schema.json")

    def test_the_sample_verified_file_validates(self):
        self.check(fixture("verified-good.json"), "verified-schema.json")

    def test_the_schemas_shut_the_door_on_extra_keys(self):
        for name in ("plan-schema.json", "evidence-schema.json", "verified-schema.json"):
            self.assertIs(schema(name)["additionalProperties"], False, name)

    def test_every_schema_carries_the_attribution(self):
        for name in ("plan-schema.json", "evidence-schema.json", "verified-schema.json"):
            self.assertIn("Pea Princess", schema(name)["description"], name)
            self.assertIn("CC BY 4.0", schema(name)["description"], name)

    def test_no_real_postcode_in_the_fixtures(self):
        for base, _dirs, files in os.walk(FIX):
            for name in files:
                text = read(os.path.join(base, name))
                for found in re.findall(r"\b[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}\b", text):
                    self.assertTrue(found.startswith("X"),
                                    "%s carries %s; fixture postcodes start with X"
                                    % (name, found))


class TheConfigLoader(unittest.TestCase):
    def test_every_shipped_pipeline_arm_loads_with_the_roles_it_claims(self):
        expected = {"P1-claude": ["planner", "executors", "integrator"],
                    "P2-claude": ["planner", "executors", "verifier", "integrator"],
                    "P3-claude": ["baseline", "verifier", "integrator"],
                    "P1-codex": ["planner", "executors", "integrator"],
                    "P2-codex": ["planner", "executors", "verifier", "integrator"],
                    "P3-codex": ["baseline", "verifier", "integrator"]}
        for name, roles in expected.items():
            config = PL.load_config(name)
            self.assertEqual([r for r, _c in PL.steps_for(config)], roles, name)
            self.assertTrue(config.get("factor"), name)
            self.assertEqual(config["phase"], "pipeline", name)

    def test_the_replan_round_is_capped_at_one(self):
        self.assertEqual(PL.replan_rounds(PL.load_config("P2-claude")), 1)
        self.assertEqual(PL.replan_rounds(PL.load_config("P1-claude")), 0)
        self.assertEqual(PL.replan_rounds({"pipeline": {"replan_rounds": 9}}), 1)

    def test_an_unknown_role_is_refused(self):
        text = ("name: X\nagent: claude\nphase: pipeline\nfactor: t\n"
                "pipeline:\n  aggregator:\n    agent: claude\n")
        with self.assertRaises(ValueError) as caught:
            PL.parse_and_check(text, "X.yaml")
        self.assertIn("aggregator", str(caught.exception))

    def test_an_unknown_key_inside_a_role_is_refused(self):
        text = ("name: X\nagent: claude\nphase: pipeline\nfactor: t\n"
                "pipeline:\n  planner:\n    temperature: 0\n")
        with self.assertRaises(ValueError) as caught:
            PL.parse_and_check(text, "X.yaml")
        self.assertIn("temperature", str(caught.exception))

    def test_the_pipeline_block_never_leaks_into_the_flat_keys(self):
        config = PL.load_config("P1-codex")
        self.assertEqual(config["agent"], "codex")
        self.assertEqual(config["main_model"], "gpt-5.6-terra")
        self.assertNotIn("parallel", config)
        self.assertNotIn("planner", config)

    def test_bench_run_py_refuses_to_run_a_pipeline_arm_as_one_agent(self):
        sys.path.insert(0, os.path.join(ROOT, "bench"))
        import run as runner
        config = runner.load_config("P2-claude")
        self.assertIs(config["pipeline"], True,
                      "run.py must notice the block rather than half-read it")
        self.assertEqual(config["agent"], "claude")
        self.assertNotIn("planner", config)
        code = runner.main(["--agent", "claude", "--config", "P2-claude",
                            "--case", "e14-marsh-wall-301", "--dry-run"])
        self.assertEqual(code, 2)


class TheDryRun(unittest.TestCase):
    def dry(self, *extra):
        cmd = [sys.executable, os.path.join(ROOT, "bench", "pipeline.py"),
               "--config", "P2-claude", "--cases", os.path.join(ROOT, "evals", "evals.json"),
               "--case", "e14-marsh-wall-301", "--dry-run"] + list(extra)
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        self.assertEqual(proc.returncode, 0, err.decode("utf-8"))
        return out.decode("utf-8")

    def setUp(self):
        self.out = self.dry()

    COMMAND = re.compile(r"^ {4}((?:claude|codex) .*?)(?=^ *\d+\. |^ {5}\(scripts|\Z)",
                         re.S | re.M)

    def commands(self, text=None):
        """Each role's whole command, which spans several lines: the prompts have
        newlines in them, so a line-by-line reading would stop before the flags."""
        return [m.group(1) for m in self.COMMAND.finditer(text or self.out)]

    def test_one_command_per_role_plus_one_per_executor_group(self):
        groups = len(PL.groups_of(P.scaffold("standard")))
        self.assertEqual(len(self.commands()), 3 + groups,
                         "planner, verifier, integrator and one executor per group")

    def test_each_role_gets_its_own_tool_list(self):
        for role, tools in (("planner", "--allowedTools Read --output-format"),
                            ("executors", "--allowedTools Read 'Bash(python3:*)'"),
                            ("integrator", "--allowedTools Read Write")):
            self.assertIn(tools, self.out, role)
        self.assertIn("Bash(python3 .claude/skills/vet-flat/scripts/verify.py:*)", self.out)
        self.assertIn("Bash(python3 .claude/skills/vet-flat/scripts/calc.py:*)", self.out)

    def test_only_the_integrator_may_write(self):
        for line in self.commands():
            tools = line.split("--allowedTools", 1)[1].split("--output-format", 1)[0]
            if "Read Write" in tools:
                self.assertIn("WRITE report.json", line)
            else:
                self.assertNotIn("Write", tools)

    def test_the_planner_cannot_run_anything(self):
        planner = [c for c in self.commands() if "Planner" in c]
        self.assertEqual(len(planner), 1)
        self.assertNotIn("Bash", planner[0])
        flags = planner[0].split("--allowedTools", 1)[1].split(" -- ", 1)[0]
        self.assertNotIn("Write", flags)

    def test_the_first_line_of_every_role_prompt_is_shown(self):
        self.assertEqual(self.out.count("    prompt: "), len(self.commands()))

    def test_the_executor_prompt_carries_a_worked_item_and_the_real_script_path(self):
        executors = [c for c in self.commands() if "Executors" in c]
        self.assertTrue(executors)
        one = executors[0]
        self.assertIn("ONE WORKED ITEM", one)
        self.assertIn("certified internal floor area of this flat", one)
        self.assertIn("pasted:epc-cert", one)
        self.assertIn("SAVE EVERY SCRIPT", one)
        self.assertIn(".claude/skills/vet-flat/scripts/", one,
                      "a bare scripts/ path does not exist in the working directory")

    def test_the_verifier_prompt_says_unknown_is_not_the_default(self):
        verifier = [c for c in self.commands() if "Verifier" in c]
        self.assertTrue(verifier)
        self.assertIn("UNKNOWN IS NOT THE DEFAULT", verifier[0])
        self.assertIn("A FAIL MUST CARRY ITS REASON", verifier[0])
        self.assertIn("quote its reason back", verifier[0])

    def test_the_deterministic_steps_are_announced(self):
        self.assertIn("scripts/plan.py wrote plan.scaffold.json and the first "
                      "plan.json", self.out)
        self.assertIn("scripts/verify.py runs first", self.out)
        self.assertIn("bench/grade.py, exactly as bench/run.py calls it", self.out)

    def test_no_permission_bypass_flag_anywhere(self):
        source = read(os.path.join(ROOT, "bench", "pipeline.py"))
        for flag in ("--dangerously", "bypassPermissions", "--permission-mode",
                     "acceptEdits", "--no-sandbox", "danger-full-access", "sudo "):
            self.assertNotIn(flag, self.out, flag)
            self.assertNotIn(flag, source, flag)
        self.assertIn("-s workspace-write",
                      self.dry_codex(), "the Codex sandbox stays on")

    def dry_codex(self):
        cmd = [sys.executable, os.path.join(ROOT, "bench", "pipeline.py"),
               "--config", "P2-codex", "--cases", os.path.join(ROOT, "evals", "evals.json"),
               "--case", "e14-marsh-wall-301", "--dry-run"]
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _err = proc.communicate()
        return out.decode("utf-8")

    def test_every_role_launches_through_bench_launch_py(self):
        """bench/launch.py is the one place that starts an agent: closed stdin, the
        retries with a growing pause and the provider_error outcome all live there once,
        instead of a second copy in this file that could drift out of sync with it."""
        source = read(os.path.join(ROOT, "bench", "pipeline.py"))
        self.assertNotIn("subprocess.Popen(", source,
                         "every role must launch through bench/launch.py, not its own "
                         "subprocess call")
        self.assertIn("import launch", source)
        self.assertGreaterEqual(len(re.findall(r"launch\.run\(", source)), 2,
                                "the single-role launch and the executors' launch_many "
                                "both call launch.run")

    def test_the_budget_mode_override_renames_the_arm_and_changes_the_plan(self):
        out = self.dry("--budget-mode", "lite")
        self.assertIn("arm:      P2-claude-lite", out)
        self.assertIn("mode:     lite", out)
        self.assertIn("(8 axes, 8 fixed questions)", out)
        self.assertIn("Budget mode: lite", out)

    def test_the_codex_twin_writes_its_discipline_where_codex_reads_it(self):
        out = self.dry_codex()
        self.assertIn(".agents/skills/vet-flat", out)
        self.assertNotIn("--allowedTools", out, "codex takes no such flag")

    def test_every_codex_role_gets_its_own_answer_file(self):
        out = self.dry_codex()
        files = re.findall(r"-o (\S*last[^ ]*\.txt)", out)
        self.assertEqual(len(files), len(set(files)),
                         "parallel executors share a working directory; a shared -o file "
                         "would lose all but one answer")
        self.assertEqual(len(files), len(self.commands(out)))
        self.assertNotIn(os.path.join("last.txt"), [os.path.basename(f) for f in files])

    def test_the_gold_probe_is_announced_only_when_a_gold_file_is_given(self):
        self.assertNotIn("information-sufficiency probe", self.out)
        out = self.dry("--gold", os.path.join(FIX, "gold-tiny.json"))
        self.assertIn("information-sufficiency probe", out)


class ThePlanPointsAtScriptsThatExist(unittest.TestCase):
    """The first pilot's executors ran `scripts/epc.py` and got 'no such file': the
    scaffold's paths are relative to the skill, and the executors run in the workdir."""

    def test_retarget_rewrites_every_call(self):
        plan = P.scaffold("standard", values={"postcode": "XE1 9AA"})
        PL.retarget(plan, ".claude/skills/vet-flat")
        calls = [c["cmd"] for a in plan["axes"] for c in a["scripts"]]
        self.assertTrue(calls)
        for cmd in calls:
            self.assertTrue(cmd.startswith(".claude/skills/vet-flat/scripts/"), cmd)

    def test_a_retargeted_plan_still_passes_the_scaffold_check(self):
        plan = P.scaffold("standard", values={"postcode": "XE1 9AA"})
        PL.retarget(plan, ".agents/skills/vet-flat")
        self.assertTrue(P.check(plan, "standard")["ok"],
                        "the check compares a call's shape, not where the file lives")

    def test_the_codex_home_is_used_for_codex(self):
        plan = P.scaffold("lite")
        PL.retarget(plan, PL.skill_rel("codex"))
        self.assertIn(".agents/skills/vet-flat/scripts/geo.py",
                      [c["cmd"] for a in plan["axes"] for c in a["scripts"]][0])


class TheSummariesInTheRow(unittest.TestCase):
    def test_evidence_summary_counts_what_was_got_and_what_nobody_tried_for(self):
        doc = {"items": [
            {"id": "a", "status": "ok", "quote": "q", "source": "s"},
            {"id": "b", "status": "ok"},
            {"id": "c", "status": "unknown", "tried": ["looked"]},
            {"id": "d", "status": "unknown", "tried": []}]}
        got = PL.evidence_summary(doc)
        self.assertEqual((got["items"], got["ok"], got["unknown"]), (4, 2, 2))
        self.assertEqual((got["with_quote"], got["with_source"]), (1, 1))
        self.assertEqual(got["untried"], 1)

    def test_verify_summary_names_the_rule_that_failed_each_item(self):
        doc = {"items": [{"id": "a", "state": "pass"},
                         {"id": "b", "state": "fail", "rules": ["quote_in_source"]},
                         {"id": "c", "state": "fail",
                          "rules": ["quote_in_source", "unit_present"]},
                         {"id": "d", "state": "unknown"}],
               "counts": {"quotes_unchecked": ["a"], "fixed_form_missing": ["F9"]}}
        got = PL.verify_summary(doc)
        self.assertEqual((got["pass"], got["fail"], got["unknown"]), (1, 2, 1))
        self.assertEqual(got["failed_by_rule"],
                         {"quote_in_source": 2, "unit_present": 1})
        self.assertEqual(got["quotes_unchecked"], 1)
        self.assertEqual(got["fixed_form_missing"], ["F9"])

    def test_a_fail_with_no_rule_is_still_counted(self):
        got = PL.verify_summary({"items": [{"id": "a", "state": "fail"}]})
        self.assertEqual(got["failed_by_rule"], {"(no rule named)": 1})


class TheRowItRecords(unittest.TestCase):
    def test_the_role_row_carries_the_model_the_wall_and_the_tools(self):
        conf = {"agent": "claude", "model": "sonnet", "parallel": 3}
        row = PL.role_row("executors", conf, 12.3, {"input_tokens": 10, "output_tokens": 5},
                          None, ["claude", "-p", "x"], group="money")
        self.assertEqual(row["role"], "executors")
        self.assertEqual(row["group"], "money")
        self.assertEqual(row["model"], "sonnet")
        self.assertEqual(row["wall_s"], 12.3)
        self.assertEqual(row["total_tokens"], 15)
        self.assertEqual(row["allowed_tools"], ["Read", "Bash(python3:*)"])

    def test_the_replan_round_can_be_labelled_without_a_lookup_error(self):
        """The second verifier pass is recorded as `verifier-again`, and the row builder
        asks for that label's tool list. A KeyError there would lose the whole run after
        every executor and verifier token had already been spent."""
        self.assertEqual(PL.role_tools("verifier-again", "claude"),
                         PL.role_tools("verifier", "claude"))
        row = PL.role_row("verifier-again", {"agent": "claude", "model": "opus"},
                          1.0, None, None, ["claude", "-p", "x"])
        self.assertEqual(row["role"], "verifier-again")
        self.assertIn("Read", row["allowed_tools"])
        self.assertEqual(PL.role_tools("executors[money]", "claude"),
                         PL.role_tools("executors", "claude"))

    def test_the_replan_round_writes_its_own_raw_files(self):
        """Round 0 and round 1 must not land on the same filename, or the first round's
        transcript is gone."""
        import run as runner
        first = runner.raw_name("P2-claude-executor-money", "case", 1)
        second = runner.raw_name("P2-claude-executor-money-2", "case", 1)
        self.assertNotEqual(first, second)
        source = read(os.path.join(ROOT, "bench", "pipeline.py"))
        self.assertIn('"executor-%s%s" % (group, "-2" if replan else "")', source)

    def test_the_baseline_report_is_moved_out_of_the_way(self):
        """P3 derives its evidence from the single agent's report. Left where it is, a
        silent integrator would end with that same file being graded under the pipeline
        arm - an ablation scoring its own control."""
        import tempfile
        folder = tempfile.mkdtemp(prefix="vetflat-test-")
        try:
            path = os.path.join(folder, "report.json")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write('{"candidates": []}')
            moved = PL.set_aside(folder, path)
            self.assertEqual(moved, "report.baseline.json")
            self.assertFalse(os.path.exists(path))
            import run as runner
            self.assertEqual(runner.find_report(folder, "")[0], None,
                             "nothing is left for finish() to grade by accident")
        finally:
            import shutil
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_report_that_cannot_be_graded_is_a_note_and_not_a_crash(self):
        source = read(os.path.join(ROOT, "bench", "pipeline.py"))
        block = source[source.index("card = grader.grade("):]
        self.assertIn("except Exception as exc", block[:400],
                      "one malformed report must not take the rest of the sweep with it")
        self.assertIn("the report could not be graded", block[:400])

    def test_the_tokens_of_every_role_add_up(self):
        roles = [{"tokens": {"input_tokens": 100, "output_tokens": 10}},
                 {"tokens": {"input_tokens": 200, "output_tokens": 20,
                             "total_cost_usd": 0.5}},
                 {"tokens": None}]
        totals = PL.totals(roles)
        self.assertEqual(totals["input_tokens"], 300)
        self.assertEqual(totals["total_tokens"], 330)
        self.assertEqual(totals["total_cost_usd"], 0.5)

    def test_the_model_string_names_every_role(self):
        roles = [{"role": "planner", "model": "sonnet"},
                 {"role": "executors", "model": "sonnet"},
                 {"role": "integrator", "model": None}]
        self.assertEqual(PL.pipeline_model(roles),
                         "planner=sonnet executors=sonnet integrator=default")

    def test_a_plan_that_shrank_is_replaced_by_the_scaffold_and_said_so(self):
        scaffold = P.scaffold("standard")
        shrunk = copy.deepcopy(scaffold)
        shrunk["axes"] = shrunk["axes"][:2]
        notes = []
        kept = PL.keep_the_plan_honest(shrunk, scaffold, "standard", notes)
        self.assertEqual(len(kept["axes"]), len(scaffold["axes"]))
        self.assertIn("dropped something required", notes[0])

    def test_a_plan_that_only_added_is_kept(self):
        scaffold = P.scaffold("standard")
        grown = copy.deepcopy(scaffold)
        grown["user_questions"].append("what does the lease say about the balcony?")
        notes = []
        self.assertIs(PL.keep_the_plan_honest(grown, scaffold, "standard", notes), grown)
        self.assertEqual(notes, [])

    def test_the_verifier_may_only_change_verdicts_it_spoke_about(self):
        """It is told to read only the flagged items, so it returns only those. If its
        file were taken as the whole answer, every item it sensibly ignored would go
        missing, and a missing item is unknown in the report."""
        deterministic = {"schema": "vet-flat/verified/1", "counts": {"items": 3},
                         "sufficiency": {"sufficiency": 0.5},
                         "items": [{"id": "e1", "state": "pass", "reason": None,
                                    "rules": [], "checked_by": "verify.py"},
                                   {"id": "e2", "state": "fail", "reason": "quote",
                                    "rules": ["quote_in_source"], "checked_by": "verify.py"},
                                   {"id": "e3", "state": "unknown", "reason": "nothing",
                                    "rules": [], "checked_by": "verify.py"}],
                         "replan": [{"axis": 2, "item": "e2", "ask": "go back", "round": 1}]}
        answered = {"items": [{"id": "e2", "state": "pass", "reason": "I read it"},
                              {"id": "e9", "state": "pass"}]}
        notes = []
        merged = PL.merge_verdicts(deterministic, answered, notes)
        by_id = dict((v["id"], v) for v in merged["items"])
        self.assertEqual(sorted(by_id), ["e1", "e2", "e3"], "nothing may go missing")
        self.assertEqual(by_id["e2"]["state"], "pass")
        self.assertEqual(by_id["e2"]["checked_by"], "verifier")
        self.assertEqual(by_id["e1"]["state"], "pass")
        self.assertEqual(by_id["e3"]["state"], "unknown")
        self.assertEqual(by_id["e1"]["checked_by"], "verify.py")
        self.assertEqual(merged["sufficiency"], {"sufficiency": 0.5})
        self.assertTrue(any("not in the evidence" in n for n in notes), notes)
        self.assertTrue(any("spoke about 1 of 3 verdicts and moved 1 of them" in n
                            for n in notes), notes)

    def test_a_verifier_that_echoes_the_file_back_is_not_recorded_as_changing_it(self):
        """The first pilot's note said 'changed 62 of 62' because the model restated the
        whole file. Restating is not changing, and the note has to tell them apart."""
        deterministic = {"items": [{"id": "e1", "state": "unknown", "reason": "x",
                                    "rules": [], "checked_by": "verify.py"},
                                   {"id": "e2", "state": "pass", "reason": None,
                                    "rules": [], "checked_by": "verify.py"}]}
        echo = {"items": [{"id": "e1", "state": "unknown"}, {"id": "e2", "state": "pass"}]}
        notes = []
        PL.merge_verdicts(deterministic, echo, notes)
        self.assertTrue(any("spoke about 2 of 2 verdicts and moved 0 of them" in n
                            for n in notes), notes)

    def test_a_verifier_that_says_nothing_leaves_the_deterministic_result_standing(self):
        deterministic = {"items": [{"id": "e1", "state": "fail", "reason": "x",
                                    "rules": ["unit_present"], "checked_by": "verify.py"}]}
        merged = PL.merge_verdicts(deterministic, {"items": []}, [])
        self.assertEqual(merged["items"][0]["state"], "fail")

    def test_evidence_from_several_executors_is_merged_with_unique_ids(self):
        merged = PL.merge_evidence([("money", {"items": [{"id": "e1", "axis": 8}]}),
                                    ("place", {"items": [{"id": "e1", "axis": 9}]})],
                                   "x-demo")
        self.assertEqual([i["id"] for i in merged["items"]], ["e1", "place-e1"])
        self.assertEqual(merged["schema"], "vet-flat/evidence/1")


class TheLauncher(unittest.TestCase):
    """Every role now launches through bench/launch.py. These monkeypatch launch.run
    with a fake that never starts a process, and check that the pipeline actually calls
    it - once per single-shot role, once per executor group - and that a provider_error
    result is recorded on the role's own row and in the run's notes, not read as an
    empty answer the model gave."""

    def setUp(self):
        self.results = tempfile.mkdtemp(prefix="vetflat-pipeline-test-results-")
        self.real_run = PL.launch.run

    def tearDown(self):
        PL.launch.run = self.real_run
        shutil.rmtree(self.results, ignore_errors=True)

    def fake(self, calls, provider_error_labels=()):
        """A launch.run stand-in: records every (family, label) it was called with and
        answers with plain unparseable text, so the pipeline's own fallbacks (the
        scaffold, the deterministic verify) take over exactly as they must when a real
        model answers badly. A label named in `provider_error_labels` instead comes
        back the way a launch that never reached the model does."""
        def run(cmd, cwd, timeout, family, label=None, **kwargs):
            calls.append((family, label))
            if label in provider_error_labels:
                return PL.launch.LaunchResult(
                    text="", note="exited 1: ", seconds=1.2, attempts=3,
                    provider_error=True, stdout_tail="", stderr_tail="rate limited",
                    exit_code=1)
            return PL.launch.LaunchResult(text="not json", usage={"input_tokens": 3},
                                          seconds=0.05, attempts=1)
        return run

    def test_record_role_leaves_a_clean_result_out_of_the_notes(self):
        roles, notes = [], []
        conf = {"agent": "claude", "model": "sonnet"}
        res = PL.launch.LaunchResult(text="ok", usage={"input_tokens": 1}, seconds=2.0)
        note = PL.record_role(roles, notes, "planner", conf, res, ["claude", "-p", "x"])
        self.assertIsNone(note)
        self.assertEqual(notes, [])
        self.assertFalse(roles[0]["provider_error"])
        self.assertEqual(roles[0]["wall_s"], 2.0)

    def test_saved_report_uses_the_same_named_output_folder(self):
        report = {"candidates": []}
        path = PL.runner.persist_report(report, "P1-claude", "synthetic", 1,
                                        results_root=self.results, day="handoff-isolated-run")
        self.assertEqual(path, os.path.join(self.results, "handoff-isolated-run", "raw",
                                           "P1-claude-synthetic-1.report.json"))
        with io.open(path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), report)

    def test_record_role_marks_a_provider_error_result_in_the_row_and_the_notes(self):
        roles, notes = [], []
        conf = {"agent": "codex", "model": None}
        res = PL.launch.LaunchResult(text="", note="exited 1: ", seconds=180.0, attempts=3,
                                     provider_error=True, stdout_tail="", stderr_tail="",
                                     exit_code=1)
        PL.record_role(roles, notes, "verifier", conf, res, ["codex", "exec"],
                       note_label="verifier")
        self.assertTrue(roles[0]["provider_error"])
        self.assertIn("attempts 3", roles[0]["note"])
        self.assertIn("stderr tail: (empty)", roles[0]["note"])
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("verifier: "), notes)
        self.assertIn("attempts 3", notes[0])

    def test_run_verifier_and_its_replan_round_both_go_through_the_launcher(self):
        calls = []
        PL.launch.run = self.fake(calls, provider_error_labels=("P-test verifier-again",))
        workdir = tempfile.mkdtemp(prefix="vetflat-pipeline-test-verifier-")
        try:
            args = Args(results=self.results)
            config = {"name": "P-test", "budget_mode": "standard"}
            conf = {"agent": "claude", "model": "opus", "parallel": 1}
            case = {"id": "test-case"}
            evidence = fixture("evidence-good.json")
            roles, notes = [], []
            verified = PL.run_verifier(args, case, config, conf, workdir, "vet this",
                                       evidence, roles, notes)
            self.assertEqual(calls, [("claude", "P-test verifier")])
            self.assertEqual(roles[-1]["role"], "verifier")
            self.assertFalse(roles[-1]["provider_error"])
            self.assertIsNotNone(verified)

            again = PL.run_verifier(args, case, config, conf, workdir, "vet this",
                                    evidence, roles, notes, again=True)
            self.assertEqual(calls, [("claude", "P-test verifier"),
                                     ("claude", "P-test verifier-again")])
            self.assertEqual(roles[-1]["role"], "verifier-again")
            self.assertTrue(roles[-1]["provider_error"], "the -again round must be "
                            "visible as a provider failure too")
            self.assertTrue(any(n.startswith("verifier: ") and "attempts 3" in n
                               for n in notes), notes)
            self.assertIsNotNone(again)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def test_run_executor_rounds_launches_one_command_per_group(self):
        scaffold = P.scaffold("standard")
        groups = PL.groups_of(scaffold)
        failing_group = groups[0][0]
        calls = []
        PL.launch.run = self.fake(
            calls, provider_error_labels=("P-test executors[%s]" % failing_group,))
        workdir = tempfile.mkdtemp(prefix="vetflat-pipeline-test-executors-")
        try:
            args = Args(results=self.results)
            config = {"name": "P-test", "budget_mode": "standard"}
            conf = {"agent": "claude", "model": "sonnet", "parallel": 1}
            case = {"id": "test-case"}
            roles, notes = [], []
            _plan, merged, rounds = PL.run_executor_rounds(
                args, case, config, conf, workdir, "vet this", scaffold, roles, notes)
            self.assertEqual(len(calls), len(groups))
            self.assertEqual(rounds, 0)
            self.assertEqual(len(roles), len(groups))
            by_group = dict((r["group"], r) for r in roles)
            self.assertTrue(by_group[failing_group]["provider_error"])
            for group, _axes in groups:
                if group != failing_group:
                    self.assertFalse(by_group[group]["provider_error"], group)
            self.assertTrue(any(n.startswith("executor %s: " % failing_group)
                               for n in notes), notes)
            self.assertEqual(merged["schema"], "vet-flat/evidence/1")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def test_launch_many_keeps_result_order_under_concurrency(self):
        commands = [["cmd", str(i)] for i in range(5)]
        labels = ["c%d" % i for i in range(5)]
        calls = []

        def fake_run(cmd, cwd, timeout, family, label=None, **kwargs):
            calls.append(label)
            return PL.launch.LaunchResult(text=label, seconds=0.01)

        real = PL.launch.run
        PL.launch.run = fake_run
        try:
            results = PL.launch_many(commands, "/tmp", 5, 3, "claude", labels)
        finally:
            PL.launch.run = real
        self.assertEqual([r.text for r in results], labels,
                         "results come back in command order, not completion order")
        self.assertEqual(sorted(calls), labels)

    def test_the_full_pipeline_routes_planner_executors_and_integrator_through_it(self):
        """P1-claude has no verifier, so no replan round complicates the count: exactly
        one planner call, one per executor group, and one integrator call."""
        cases_path = os.path.join(ROOT, "evals", "evals.json")
        case = PL.runner.load_cases(cases_path, "e14-marsh-wall-301", False)[0]
        config = PL.load_config("P1-claude")
        target = "%s planner" % config["name"]
        calls = []
        PL.launch.run = self.fake(calls, provider_error_labels=(target,))
        args = PL.build_parser().parse_args([
            "--config", "P1-claude", "--cases", cases_path, "--case", case["id"],
            "--run", "1", "--timeout", "5", "--results", self.results,
            "--day", "handoff-isolated-run"])
        args.case_row = case
        # Catch leaks to the default output root without touching real experiment data.
        original_results = PL.runner.RESULTS
        default_results = os.path.join(self.results, "default-must-stay-empty")
        PL.runner.RESULTS = default_results
        try:
            with quiet():
                code, row = PL.run_pipeline(args, case, config)
        finally:
            PL.runner.RESULTS = original_results
        self.assertFalse(os.path.exists(default_results))
        self.assertEqual(os.listdir(self.results), ["handoff-isolated-run"])
        output = os.path.join(self.results, "handoff-isolated-run")
        with io.open(os.path.join(output, "scorecard.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), [row])
        self.assertTrue(os.path.isfile(os.path.join(output, "scorecard.md")))
        self.assertTrue(os.path.isfile(os.path.join(output, "raw",
                                                   "P1-claude-e14-marsh-wall-301-1.json")))
        groups = len(PL.groups_of(P.scaffold("standard")))
        self.assertEqual(len(calls), 2 + groups, calls)
        self.assertEqual({fam for fam, _label in calls}, {"claude"})
        self.assertEqual(code, 1, "no report.json was ever written, so there is nothing "
                         "to grade - that is not a crash")
        by_role = {}
        for r in row["roles"]:
            by_role.setdefault(r["role"], []).append(r)
        self.assertIn("planner", by_role)
        self.assertEqual(len(by_role["executors"]), groups)
        self.assertEqual(len(by_role["integrator"]), 1)
        self.assertTrue(by_role["planner"][0]["provider_error"],
                        "the provider refusing the planner call must be visible on its "
                        "own row")
        self.assertIn("attempts 3", by_role["planner"][0]["note"])
        self.assertFalse(by_role["integrator"][0]["provider_error"])
        for r in by_role["executors"]:
            self.assertFalse(r["provider_error"], r)
        self.assertIn("planner:", row["note"], "the scorecard note must say which role "
                      "the provider refused")


class TheReferenceDocument(unittest.TestCase):
    def setUp(self):
        self.text = read(os.path.join(REFS, "pipeline.md"))

    def test_it_carries_the_attribution_line_first(self):
        self.assertTrue(self.text.startswith("Part of Pea Princess (vet-flat) by "
                                             "Hsien Hao (Jacky) Chen"))
        self.assertIn("CC BY 4.0", self.text.splitlines()[0])

    def test_every_role_has_its_own_section(self):
        for heading in ("## 1. Planner", "## 2. Executors", "## 3. Verifier",
                        "## 4. Integrator"):
            self.assertIn(heading, self.text, heading)

    def test_it_tells_an_agent_with_subagents_and_one_without_what_to_do(self):
        block = self.text[self.text.index("## With subagents"):
                          self.text.index("## Tool discipline")]
        self.assertIn("**With subagents**", block)
        self.assertIn("**Without subagents**", block)
        self.assertIn("write each phase's output to a file before the next phase starts",
                      block)

    def test_it_says_when_to_use_it(self):
        block = self.text[self.text.index("## When to use it"):
                          self.text.index("## The four roles")]
        for trigger in ("not the strongest one you have", "final shortlist", "`deep`"):
            self.assertIn(trigger, block, trigger)

    def test_the_planner_never_decides_what_survives(self):
        self.assertIn("the planner decides WHAT TO GET, never what survives",
                      self.text.replace("**", ""))

    def test_the_replan_is_capped_at_one_round(self):
        self.assertIn("One round only", self.text)

    def test_it_tells_the_executors_to_save_what_they_quote(self):
        self.assertIn("Save what you quoted", self.text)
        self.assertIn("sources/<name>.json", self.text)
        self.assertIn("A quote nobody can open is a quote nobody can check", self.text)
        self.assertIn("never a bare `scripts/epc.py`", self.text)

    def test_it_tells_the_verifier_that_unknown_is_not_the_default(self):
        self.assertIn("Unknown is not the default", self.text)
        self.assertIn("quote its reason back", self.text)
        self.assertIn("name its rule id in `rules`", self.text)

    def test_it_tells_the_verifier_to_write_the_whole_file(self):
        self.assertIn("Write the whole file, not just your part", self.text)
        self.assertIn("re-judge evidence, never create it", self.text)

    def test_it_names_the_three_contracts_and_the_two_tools(self):
        for needle in ("plan-schema.json", "evidence-schema.json", "verified-schema.json",
                       "scripts/plan.py", "scripts/verify.py"):
            self.assertIn(needle, self.text, needle)

    def test_it_states_the_legal_caps_with_the_branch(self):
        self.assertIn("five weeks where the annual rent is under £50,000 and six at or "
                      "above it", self.text)
        self.assertIn("holding deposit one week", self.text)
        self.assertIn("rent in advance at most one month", self.text)

    def test_it_claims_no_measured_result_yet(self):
        self.assertIn("Role pipeline (to be measured)", self.text)
        self.assertIn("treat this page as a design, not a recommendation", self.text)

    def test_the_prompt_pack_still_fits_after_this_page_was_added(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_dist", os.path.join(ROOT, "tools", "build_dist.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertLessEqual(len(module.compose_instructions()), 8000)

    def test_the_router_points_at_it_from_somewhere(self):
        for name in ("budget-modes.md", "report-contract.md"):
            text = read(os.path.join(REFS, name))
            self.assertIn("pipeline.md", text, name)


if __name__ == "__main__":
    unittest.main()


class TheDayLabel(unittest.TestCase):
    def test_a_label_that_is_not_a_date_names_the_folder_and_does_not_crash(self):
        import datetime
        self.assertEqual(datetime.datetime(2026, 9, 7), PL.results_when("2026-09-07"))
        self.assertIsInstance(PL.results_when("ablation-2026-09-07"), datetime.datetime)
        self.assertIsInstance(PL.results_when(None), datetime.datetime)
