#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the A/B (and C, and the ablations) sweep: runs x configs x cases, interleaved.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY INTERLEAVE
==============
The arms are compared against each other, not against a fixed number, so anything
that drifts during the sweep - the time of day, a register that updates at noon, a
model that gets busier at 5 pm - must hit every arm equally. So the loop is
run -> case -> config: A, B, C, A, B, C, ... and never all of A and then all of B.

RESUMABLE
=========
A run is identified by its raw output file,
``bench/results/<date>/raw/<config>-<case>-<run>.json``. If that file exists the run
is skipped. Kill the sweep and start it again and it picks up where it stopped.

AGENTS
======
A config carries its own ``agent``. ``claude`` configs go through ``bench/run.py``;
``codex`` configs go through ``bench/ab/run_codex.py``. ``--agent`` overrides the
config's own choice for every config in the sweep, which is how you run the whole
Claude-side set against Codex.

Nothing here passes a permission-bypass flag: the Claude side is scoped by
``--allowedTools``, the Codex side by ``-s workspace-write``.

Usage:
  bench/ab/run_ab.py --configs A-legacy,B-lean,C-twenty \\
      --cases bench/private/cases_private.json \\
      --case-ids v2-buck,s09 --runs 3 --agent claude --dry-run
  bench/ab/run_ab.py --phase core --cases bench/private/cases_private.json --runs 3
  bench/ab/run_ab.py --phase ablation --cases bench/private/cases_private.json --runs 2

Exit codes: 0 every run that was attempted produced a graded report, 1 at least one
did not, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(BENCH, ".."))

sys.path.insert(0, BENCH)
import run as runner  # noqa: E402

RUN_PY = os.path.join(BENCH, "run.py")
RUN_CODEX_PY = os.path.join(HERE, "run_codex.py")
GRADE_AB_PY = os.path.join(HERE, "grade_ab.py")
DEFAULT_CASES = os.path.join(ROOT, "evals", "evals.json")
PRIVATE_CASES = os.path.join(BENCH, "private", "cases_private.json")
PRIVATE_GOLD = os.path.join(BENCH, "private", "gold.json")


def load_cases(path):
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    return doc.get("evals") or []


def pick_configs(names, phase, config_dir=None):
    """[config] in the order the user named them, or config-file order for a phase."""
    every = runner.list_configs(config_dir)
    by_name = collections.OrderedDict((c["name"], c) for c in every)
    if names:
        out = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            if name in by_name:
                out.append(by_name[name])
            else:
                out.append(runner.load_config(name))
        return out
    if phase and phase != "all":
        return [c for c in every if c.get("phase") == phase]
    return every


def plan(configs, cases, runs, agent_override, cases_path, results_root=None, day=None,
         resume=True):
    """[(run_index, config, case, command, skipped)] in interleaved order."""
    day = day or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    steps = []
    for run_index in range(1, runs + 1):
        for case in cases:
            for cfg in configs:
                agent = agent_override or cfg.get("agent") or "claude"
                label = case["id"]
                skipped = resume and runner.raw_exists(cfg["name"], label, run_index,
                                                       day=day, results_root=results_root)
                steps.append(collections.OrderedDict([
                    ("run", run_index), ("config", cfg["name"]), ("case", label),
                    ("agent", agent), ("skipped", skipped),
                    ("command", command_for(cfg, case, agent, run_index, cases_path,
                                            results_root)),
                ]))
    return steps


def command_for(cfg, case, agent, run_index, cases_path, results_root=None):
    extra = ["--results", results_root] if results_root else []
    if agent == "codex":
        return [sys.executable, RUN_CODEX_PY,
                "--config", cfg.get("path") or cfg["name"],
                "--cases", cases_path,
                "--case", case["id"],
                "--run", str(run_index)] + extra
    return [sys.executable, RUN_PY,
            "--agent", agent,
            "--config", cfg.get("path") or cfg["name"],
            "--cases", cases_path,
            "--case", case["id"],
            "--run-index", str(run_index)] + extra


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--configs", help="comma-separated config names or paths, in the order "
                                      "they should be interleaved")
    ap.add_argument("--phase", choices=("core", "ablation", "all"),
                    help="run every config with this phase instead of naming them")
    ap.add_argument("--cases", default=DEFAULT_CASES,
                    help="a cases file in the evals/evals.json shape; the A/B suite uses "
                         "bench/private/cases_private.json")
    ap.add_argument("--case-ids", help="comma-separated case ids; default is every case")
    ap.add_argument("--runs", type=int, default=3, help="repeats per config x case, default 3")
    ap.add_argument("--agent", help="override every config's own agent (claude or codex)")
    ap.add_argument("--parallel", type=int, default=1,
                    help="how many runs to have in flight at once, default 1. Anything above "
                         "1 costs you the time-of-day control, so keep it small")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per run, default 1800")
    ap.add_argument("--gold", default=PRIVATE_GOLD, help="gold file for the grader")
    ap.add_argument("--no-resume", action="store_true",
                    help="run everything again even where a raw output already exists")
    ap.add_argument("--no-grade", action="store_true", help="skip the grader after each run")
    ap.add_argument("--config-dir", help="where the config yaml files live")
    ap.add_argument("--results", help="results root, default bench/results")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the exact command list and stop")
    return ap


def run_grader(results_dir, gold, quiet=True):
    if not os.path.exists(GRADE_AB_PY):
        return None
    cmd = [sys.executable, GRADE_AB_PY, "--results", results_dir]
    if gold and os.path.exists(gold):
        cmd += ["--gold", gold]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
    except OSError as exc:
        print("could not run the grader: %s" % exc, file=sys.stderr)
        return None
    if not quiet:
        sys.stdout.write((out or b"").decode("utf-8", "replace"))
    if proc.returncode != 0:
        sys.stderr.write((err or b"").decode("utf-8", "replace"))
    return proc.returncode


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.configs and not args.phase:
        print("usage error: give --configs a,b,c or --phase core|ablation|all",
              file=sys.stderr)
        return 2
    if not os.path.exists(args.cases):
        print("usage error: no cases file at %s%s" % (
            args.cases, "  (run bench/private/build_gold.py first)"
            if args.cases == PRIVATE_CASES else ""), file=sys.stderr)
        return 2

    configs = pick_configs((args.configs or "").split(",") if args.configs else None,
                           args.phase, args.config_dir)
    if not configs:
        print("usage error: no config matched", file=sys.stderr)
        return 2

    cases = load_cases(args.cases)
    if args.case_ids:
        wanted = [c.strip() for c in args.case_ids.split(",") if c.strip()]
        by_id = {c["id"]: c for c in cases}
        missing = [w for w in wanted if w not in by_id]
        if missing:
            print("usage error: no case %s in %s" % (", ".join(missing), args.cases),
                  file=sys.stderr)
            return 2
        cases = [by_id[w] for w in wanted]
    if not cases:
        print("usage error: no cases", file=sys.stderr)
        return 2

    results_root = args.results or runner.RESULTS
    day = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    steps = plan(configs, cases, args.runs, args.agent, args.cases,
                 results_root=results_root, day=day, resume=not args.no_resume)

    if args.dry_run:
        print("configs:  %s" % ", ".join("%s [%s]" % (c["name"], c.get("phase"))
                                         for c in configs))
        print("cases:    %s" % ", ".join(c["id"] for c in cases))
        print("runs:     %d   parallel: %d   resume: %s"
              % (args.runs, args.parallel, "off" if args.no_resume else "on"))
        print("results:  %s" % os.path.join(results_root, day))
        print("order:    run -> case -> config, so the configs interleave")
        print("")
        for i, step in enumerate(steps, 1):
            print("%3d. r%d  %-22s %-12s %-7s %s"
                  % (i, step["run"], step["config"], step["case"], step["agent"],
                     "SKIP, raw output exists" if step["skipped"] else ""))
            print("     %s" % runner.shell(step["command"]))
        todo = sum(1 for s in steps if not s["skipped"])
        print("")
        print("%d runs planned, %d to do, %d already have raw output"
              % (len(steps), todo, len(steps) - todo))
        if not args.no_grade:
            print("after each run: %s"
                  % runner.shell([sys.executable, GRADE_AB_PY, "--results",
                                  os.path.join(results_root, day), "--gold", args.gold]))
        return 0

    todo = [s for s in steps if not s["skipped"]]
    for step in steps:
        if step["skipped"]:
            print("skip  r%d %s %s (raw output exists)"
                  % (step["run"], step["config"], step["case"]))

    worst = 0
    width = max(1, args.parallel)
    for start in range(0, len(todo), width):
        batch = todo[start:start + width]
        live = []
        for step in batch:
            print("run   r%d %s %s" % (step["run"], step["config"], step["case"]))
            try:
                live.append((step, subprocess.Popen(step["command"], env=dict(os.environ, VETFLAT_RUN_TIMEOUT=str(args.timeout)))))
            except OSError as exc:
                print("      could not start: %s" % exc, file=sys.stderr)
                worst = 1
        for step, proc in live:
            try:
                code = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                print("      r%d %s %s timed out after %d s"
                      % (step["run"], step["config"], step["case"], args.timeout),
                      file=sys.stderr)
                code = 1
            worst = max(worst, 1 if code else 0)
        if not args.no_grade:
            run_grader(os.path.join(results_root, day), args.gold)
    if todo and not args.no_grade:
        run_grader(os.path.join(results_root, day), args.gold, quiet=False)
    return worst


if __name__ == "__main__":
    sys.exit(main())
