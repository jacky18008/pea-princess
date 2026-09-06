#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run one A/B config x case against the Codex CLI, grade it, append to the scorecard.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHAT THIS DOES
==============
1. Builds a clean working directory: the case's ``profile.yaml`` (with the config's
   ``budget_mode`` written into it) and a COPY of ``skills/vet-flat`` at
   ``<workdir>/.agents/skills/vet-flat``. A copy, not a symlink: Codex's
   workspace-write sandbox will not follow a link out of the workspace.
2. Writes ``<workdir>/AGENTS.md``. Codex reads that file on start, and it is the
   documented way to give this run extra instructions, since ``codex exec`` has no
   ``--append-system-prompt``. The file is the config's ``append_system_prompt`` plus
   one line telling the run where to write the report.
3. Runs::

     codex exec -m <model> -C <workdir> --skip-git-repo-check -s workspace-write \\
       -c sandbox_workspace_write.network_access=true \\
       -o <workdir>/last.txt --json "<case prompt>"

   ``-s workspace-write`` keeps the sandbox on; the documented config key turns the
   network on INSIDE it, which every fetcher in this skill needs.
   ``--dangerously-bypass-approvals-and-sandbox`` is never used, here or anywhere.
   ``--json`` makes Codex print its event stream as JSONL on stdout; the whole
   stream is kept under ``bench/results/<date>/raw/`` and the token counts are read
   out of it (the key names differ between Codex versions, so every integer under a
   key that looks like a token count is collected and the shape is recorded).
4. Grades ``<workdir>/report.json`` with ``bench/grade.py`` and appends one row to
   ``bench/results/<date>/scorecard.json`` with ``agent: codex``. The A/B metrics on
   top of that are ``bench/ab/grade_ab.py``, which reads the same scorecard.

Verified against the installed CLI: codex 0.151, model ids ``gpt-5.6-sol`` (the
default in ``~/.codex/config.toml``), ``gpt-5.6-terra``, ``gpt-5.6-luna``.

Usage:
  bench/ab/run_codex.py --config codex-B-lean-sol \\
      --cases bench/private/cases_private.json --case v2-buck --run 1 --dry-run

Exit codes: 0 graded, 1 no gradeable report, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(BENCH, ".."))
SKILL_DIR = os.path.join(ROOT, "skills", "vet-flat")

sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
import run as runner  # noqa: E402
import grade as grader  # noqa: E402

AGENTS_MD_TAIL = ("Write report.json in this directory following "
                  ".agents/skills/vet-flat/references/report-schema.json. "
                  "The skill is installed at .agents/skills/vet-flat; read its SKILL.md first. "
                  "Write exactly one report.json and nothing else large.")

TOKEN_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens",
              "reasoning_output_tokens", "total_tokens", "prompt_tokens",
              "completion_tokens", "cache_read_input_tokens")


def prepare_workdir(case, cases_path, config, workdir=None):
    if workdir:
        path = os.path.abspath(workdir)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
    else:
        path = tempfile.mkdtemp(prefix="vetflat-codex-%s-" % case["id"])
    plan = []
    base = os.path.dirname(os.path.abspath(cases_path))
    for rel in case.get("files") or []:
        src = os.path.join(base, rel)
        dst = os.path.join(path, os.path.basename(rel))
        shutil.copyfile(src, dst)
        plan.append("copy %s -> %s" % (src, os.path.basename(rel)))

    home = os.path.join(path, ".agents", "skills")
    if not os.path.isdir(home):
        os.makedirs(home, exist_ok=True)
    dst = os.path.join(home, "vet-flat")
    if os.path.lexists(dst):
        (shutil.rmtree if os.path.isdir(dst) and not os.path.islink(dst) else os.unlink)(dst)
    shutil.copytree(SKILL_DIR, dst)
    plan.append("copy skills/vet-flat -> .agents/skills/vet-flat  (copy, not a symlink: the "
                "workspace-write sandbox will not follow a link out of the workspace)")

    mode = runner.apply_budget_mode(path, config.get("budget_mode"))
    if mode:
        plan.append("set budget_mode: %s in the run's profile.yaml" % mode)

    agents_md = os.path.join(path, "AGENTS.md")
    text = "\n\n".join(x for x in [(config.get("append_system_prompt") or "").strip(),
                                   AGENTS_MD_TAIL] if x)
    with io.open(agents_md, "w", encoding="utf-8") as fh:
        fh.write("# Instructions for this run\n\n" + text + "\n")
    plan.append("write AGENTS.md (the config appendix; codex exec has no "
                "--append-system-prompt, and Codex reads AGENTS.md on start)")
    return path, plan


def build_command(config, case, workdir, model=None, prompt=None, out=None):
    """`out` names the file Codex writes its last message to; default <workdir>/last.txt.

    bench/pipeline.py passes one per role: its executors run at the same time in the same
    working directory, and a shared last.txt would have them overwrite each other's
    answers.
    """
    model = model or config.get("main_model")
    cmd = ["codex", "exec"]
    if model:
        cmd += ["-m", model]
    cmd += ["-C", workdir,
            "--skip-git-repo-check",
            "-s", "workspace-write",
            "-c", "sandbox_workspace_write.network_access=true",
            "-o", out or os.path.join(workdir, "last.txt"),
            "--json",
            prompt or case["prompt"]]
    return cmd


def usage_from_events(stdout):
    """Token counts out of the --json event stream, whatever the version calls them."""
    totals = collections.OrderedDict()
    shapes = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for holder in walk_usage(event):
            keys = tuple(sorted(k for k in holder if isinstance(holder[k], int)))
            if keys and keys not in shapes:
                shapes.append(keys)
            for key in TOKEN_KEYS:
                if isinstance(holder.get(key), int):
                    totals[key] = holder[key]      # last one wins: Codex reports cumulative
    if not totals:
        return None
    if "total_tokens" not in totals:
        total = sum(v for k, v in totals.items()
                    if k in ("input_tokens", "output_tokens", "reasoning_output_tokens"))
        if total:
            totals["total_tokens"] = total
    totals["usage_shapes_seen"] = ["+".join(s) for s in shapes]
    return totals


def walk_usage(node):
    """Every dict under a key that looks like a usage block."""
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, dict) and ("usage" in key or "token" in key):
                out.append(value)
                for k2, v2 in value.items():
                    if isinstance(v2, dict):
                        out.append(v2)
            elif isinstance(value, (dict, list)):
                out.extend(walk_usage(value))
        if any(k in node for k in TOKEN_KEYS):
            out.append(node)
    elif isinstance(node, list):
        for item in node:
            out.extend(walk_usage(item))
    return out


def last_message(workdir, stdout):
    path = os.path.join(workdir, "last.txt")
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    return stdout or ""


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="a config from bench/ab/configs")
    ap.add_argument("--cases", required=True, help="a cases file in the evals.json shape")
    ap.add_argument("--case", required=True, help="the case id")
    ap.add_argument("--run", type=int, default=1, help="which repeat this is")
    ap.add_argument("--model", help="override the config's main_model")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("VETFLAT_RUN_TIMEOUT", 1800)))
    ap.add_argument("--workdir", help="use this directory instead of a fresh temp one")
    ap.add_argument("--keep", action="store_true", help="do not delete the temp workdir")
    ap.add_argument("--results", help="results root; default bench/results")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and command; stop")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.results:
        runner.RESULTS = os.path.abspath(args.results)
    config = runner.load_config(args.config)
    with io.open(args.cases, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    case = None
    for row in doc.get("evals") or []:
        if row.get("id") == args.case:
            case = row
            break
    if case is None:
        print("usage error: no case %r in %s" % (args.case, args.cases), file=sys.stderr)
        return 2

    workdir, plan = prepare_workdir(case, args.cases, config, args.workdir)
    command = build_command(config, case, workdir, args.model)

    if args.dry_run:
        print("case:     %s  (%s)" % (case["id"], case.get("address")))
        print("agent:    codex")
        print("config:   %s   [%s]  factor: %s"
              % (config.get("name"), config.get("phase"), config.get("factor")))
        print("model:    %s" % (args.model or config.get("main_model") or "(codex default)"))
        print("raw file: %s" % os.path.join(
            "bench", "results", "<date>", "raw",
            runner.raw_name(config.get("name"), case["id"], args.run)))
        print("workdir:  %s" % workdir)
        for line in plan:
            print("          %s" % line)
        print("AGENTS.md:")
        with io.open(os.path.join(workdir, "AGENTS.md"), encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                print("          %s" % line)
        print("command:  %s" % runner.shell(command))
        if not args.keep and not args.workdir:
            shutil.rmtree(workdir, ignore_errors=True)
        return 0

    started = time.time()
    stdout, note = "", None
    try:
        # stdin is closed on purpose: `claude -p` treats anything piped on stdin as part of the
        # prompt, and a runner launched from a shell heredoc hands that heredoc to every child.
        # On 2026-09-05 four journey runs and ten sweep rows carried a launcher script that way.
        proc = subprocess.Popen(command, cwd=workdir, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate(timeout=args.timeout)
        stdout = (out or b"").decode("utf-8", "replace")
        stderr = (err or b"").decode("utf-8", "replace")
        if proc.returncode != 0:
            note = "codex exited %d: %s" % (proc.returncode, stderr.strip()[-300:])
    except subprocess.TimeoutExpired:
        proc.kill()
        note = "timed out after %d s" % args.timeout
    except OSError as exc:
        note = "could not start codex: %s" % exc
        print(note, file=sys.stderr)
        return 1
    wall = time.time() - started

    raw_path = runner.write_raw(stdout, config.get("name"), case["id"], args.run)
    usage = usage_from_events(stdout)

    report, path = runner.find_report(workdir, last_message(workdir, stdout))
    try:
        runner.persist_report(report, config.get('name'), case['id'], args.run, results_root=getattr(args, 'results', None))
    except Exception as exc:
        print('could not persist report: %s' % exc, file=sys.stderr)
    if report is None:
        note = (note + "; " if note else "") + "no report.json and no JSON object in the output"
        row = runner.make_row("codex", args.model or config.get("main_model"), case, None,
                              wall, usage, workdir, runner.shell(command), note, None,
                              config, args.run, raw_path)
        runner.append_scorecard(row)
        print(note, file=sys.stderr)
        return 1

    profile_path = grader.case_profile_path(args.cases, case)
    card = grader.grade(report, case, profile_path)
    card["report"] = path
    with io.open(os.path.join(workdir, "scorecard.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(card, ensure_ascii=False, indent=1) + "\n")
    row = runner.make_row("codex", args.model or config.get("main_model"), case, card, wall,
                          usage, workdir, runner.shell(command), note, None,
                          config, args.run, raw_path)
    runner.append_scorecard(row)
    print(card["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
