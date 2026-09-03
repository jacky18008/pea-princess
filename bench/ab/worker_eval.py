#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sonnet against Opus on the extraction work the lean config hands to a subagent.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY THIS EXISTS
===============
The lean config's one real risk is the worker model: it spawns Sonnet, not Opus, to
read a pasted review page, a planning officer's report, a welcome-pack tariff page,
an energy-certificate search page or a TfL journey JSON, and pull one number out of
it. If Sonnet is worse at that, the whole arm is worse and the A/B will only show it
as noise spread over eleven axes. So measure it directly, on fixed tasks with answers
a person already checked.

HOW A TASK RUNS
===============
No tools, no shell, no internet: the model gets the instruction and the file text,
truncated to 60 KB of UTF-8, and must answer with the value and nothing else. That is
exactly the subagent's job in the lean config, minus everything that could confound it.
A task on a file bigger than that may name ``window_start_bytes``; every shipped task is
answerable from its own window alone.

  claude -p <prompt> --model <sonnet|opus> --output-format json

Model aliases: Claude Code accepts ``opus``, ``sonnet`` and ``fable`` as aliases for
the latest model in each family, or a full model name; ``claude --help`` is the
authority. This script uses the aliases so it keeps working when the families move.

SCORING
=======
exact          the answer, normalised (case, whitespace, thousands separators, a
               leading currency symbol, a trailing full stop), equals the expected
               string; for a list, the same set in any order.
within         numeric, and inside the task's tolerance.
miss           neither.
Also recorded: tokens, cost, wall time per task, and the raw answer.

Writes ``bench/results/<date>/worker-<model>.json`` and prints a comparison table.

Usage:
  bench/ab/worker_eval.py --dry-run
  bench/ab/worker_eval.py --models sonnet,opus
  bench/ab/worker_eval.py --models sonnet --tasks bench/private/worker_tasks.json

Exit codes: 0 ran, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(BENCH, ".."))

sys.path.insert(0, BENCH)
import run as runner  # noqa: E402

TASKS = os.path.join(BENCH, "private", "worker_tasks.json")
RESULTS = os.path.join(BENCH, "results")
TRUNCATE = 60 * 1024        # bytes of UTF-8, not characters: a CJK page must not get 3x
MODEL_ALIASES = ("sonnet", "opus", "fable")

PREAMBLE = ("You are reading one saved document. Answer using only what is in the document "
            "below. Do not guess, do not explain, do not add units that are not asked for. "
            "If the document does not contain the answer, reply exactly: NOT IN DOCUMENT.")


# ------------------------------------------------------------------- inputs --
def load_tasks(path):
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    return doc.get("tasks") or doc


def file_bytes(path):
    """The document as UTF-8 bytes. A PDF goes through pdftotext when it is available."""
    if path.lower().endswith(".pdf"):
        try:
            return subprocess.check_output(["pdftotext", "-layout", path, "-"],
                                           stderr=subprocess.PIPE), None
        except (OSError, subprocess.CalledProcessError) as exc:
            return b"", "pdftotext failed: %s" % exc
    try:
        with open(path, "rb") as fh:
            return fh.read(), None
    except IOError as exc:
        return b"", "could not read: %s" % exc


def window(task, limit=TRUNCATE):
    """(text, note) - at most `limit` BYTES of the file, from window_start_bytes.

    A minified 140 KB JSON does not fit in the budget, so a task may name where its
    window starts. Every shipped task is answerable from its own window alone; that is
    checked when the task file is built, not here.
    """
    raw, err = file_bytes(task["input_path"])
    if err:
        return None, err
    start = int(task.get("window_start_bytes") or 0)
    chunk = raw[start:start + limit]
    note = ""
    if start:
        note = ", bytes %d-%d of %d" % (start, start + len(chunk), len(raw))
    elif len(raw) > limit:
        note = ", first %d KB of %d KB" % (limit // 1024, len(raw) // 1024)
    return (chunk.decode("utf-8", "replace"), note)


def build_prompt(task):
    text, note = window(task)
    if text is None:
        return None, note
    return "\n".join([
        PREAMBLE, "",
        "QUESTION: %s" % task["instruction"], "",
        "DOCUMENT (%s%s):" % (os.path.basename(task["input_path"]), note),
        "---",
        text,
        "---",
        "Answer:"]), None


def build_command(model, prompt):
    return ["claude", "-p", prompt, "--model", model, "--output-format", "json"]


# ------------------------------------------------------------------ scoring --
CURRENCY = "£$€"


def normalise(value):
    text = str(value).strip().strip(".").strip()
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    while text[:1] in CURRENCY:
        text = text[1:].strip()
    return text.lower()


def as_number(value):
    m = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(m.group(0)) if m else None


def score_answer(answer, expected, tolerance):
    """(status, detail). status is exact | within | miss."""
    answer = (answer or "").strip()
    if isinstance(expected, list):
        want = set(normalise(x) for x in expected)
        got = set(normalise(x) for x in re.split(r"[,;\n]+", answer) if x.strip())
        if got == want:
            return "exact", "same set"
        missing = sorted(want - got)
        extra = sorted(got - want)
        return "miss", "missing %s, extra %s" % (missing or "none", extra or "none")

    if normalise(answer) == normalise(expected):
        return "exact", "string match"
    want, got = as_number(expected), as_number(answer)
    if want is not None and got is not None:
        slack = tolerance if isinstance(tolerance, (int, float)) else 0
        if abs(got - want) <= slack:
            return ("exact" if got == want else "within",
                    "%s vs %s, tolerance %s" % (got, want, slack))
        return "miss", "%s vs %s, outside tolerance %s" % (got, want, slack)
    return "miss", "%r is not %r" % (answer[:80], expected)


def answer_of(stdout):
    obj = runner.first_json_object(stdout)
    if isinstance(obj, dict) and isinstance(obj.get("result"), str):
        return obj["result"].strip()
    return (stdout or "").strip()


# --------------------------------------------------------------------- main --
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", default=TASKS)
    ap.add_argument("--models", default="sonnet,opus",
                    help="comma-separated Claude Code model aliases, default sonnet,opus. "
                         "Claude Code accepts %s as aliases for the latest model in each "
                         "family, or a full model name; see claude --help"
                         % ", ".join(MODEL_ALIASES))
    ap.add_argument("--task-ids", help="comma-separated task ids; default is every task")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--results", default=RESULTS)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the exact commands and stop")
    return ap


def run_one(task, model, timeout):
    prompt, err = build_prompt(task)
    if prompt is None:
        return collections.OrderedDict([("task", task["id"]), ("status", "miss"),
                                        ("detail", err), ("answer", None)])
    command = build_command(model, prompt)
    started = time.time()
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err_bytes = proc.communicate(timeout=timeout)
        stdout = (out or b"").decode("utf-8", "replace")
        note = None
        if proc.returncode != 0:
            note = "exited %d: %s" % (proc.returncode,
                                      (err_bytes or b"").decode("utf-8", "replace")[-200:])
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, note = "", "timed out after %d s" % timeout
    except OSError as exc:
        return collections.OrderedDict([("task", task["id"]), ("status", "miss"),
                                        ("detail", "could not start claude: %s" % exc),
                                        ("answer", None)])
    wall = time.time() - started
    answer = answer_of(stdout)
    status, detail = score_answer(answer, task["expected"], task.get("tolerance"))
    usage = runner.usage_from_stdout("claude", stdout) or {}
    return collections.OrderedDict([
        ("task", task["id"]), ("kind", task.get("kind")), ("model", model),
        ("status", status), ("detail", detail),
        ("answer", answer[:300]), ("expected", task["expected"]),
        ("wall_time_s", round(wall, 1)),
        ("total_tokens", usage.get("total_tokens")),
        ("total_cost_usd", usage.get("total_cost_usd")),
        ("note", note),
    ])


def table(by_model, tasks):
    order = list(by_model)
    lines = ["| task | kind | " + " | ".join(order) + " |",
             "|---|---|" + "---|" * len(order)]
    for task in tasks:
        cells = []
        for model in order:
            row = by_model[model].get(task["id"])
            cells.append(row["status"] if row else "-")
        lines.append("| %s | %s | %s |" % (task["id"], task.get("kind") or "-",
                                           " | ".join(cells)))
    lines.append("")
    lines.append("| model | exact | within | miss | tokens | cost $ | wall s |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for model in order:
        rows = list(by_model[model].values())
        counts = collections.Counter(r["status"] for r in rows)

        def total(key):
            values = [r.get(key) for r in rows if isinstance(r.get(key), (int, float))]
            return sum(values) if values else None
        lines.append("| %s | %d | %d | %d | %s | %s | %s |"
                     % (model, counts["exact"], counts["within"], counts["miss"],
                        total("total_tokens") if total("total_tokens") is not None else "-",
                        ("%.4f" % total("total_cost_usd"))
                        if total("total_cost_usd") is not None else "-",
                        ("%.0f" % total("wall_time_s"))
                        if total("wall_time_s") is not None else "-"))
    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not os.path.exists(args.tasks):
        print("no task file at %s  (bench/private/ is gitignored; the tasks are private)"
              % args.tasks, file=sys.stderr)
        return 2
    tasks = load_tasks(args.tasks)
    if args.task_ids:
        wanted = set(t.strip() for t in args.task_ids.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not tasks or not models:
        print("usage error: no tasks or no models", file=sys.stderr)
        return 2

    if args.dry_run:
        print("tasks:  %d   models: %s" % (len(tasks), ", ".join(models)))
        print("prompt: no tools, no shell. The instruction plus the file text, at most 60 KB "
              "of UTF-8 from window_start_bytes (default 0).")
        print("aliases: Claude Code accepts %s for the latest model in each family, or a full "
              "model name (claude --help)." % ", ".join(MODEL_ALIASES))
        print("")
        for task in tasks:
            prompt, err = build_prompt(task)
            size = os.path.getsize(task["input_path"]) \
                if os.path.exists(task["input_path"]) else 0
            print("%-28s %-9s %8d B  %s" % (task["id"], task.get("kind") or "-", size,
                                            task["input_path"]))
            print("    ask:      %s" % task["instruction"])
            print("    expected: %s   (tolerance %s)"
                  % (json.dumps(task["expected"], ensure_ascii=False), task.get("tolerance")))
            if err:
                print("    PROBLEM:  %s" % err)
            for model in models:
                print("    %s" % runner.shell(build_command(model,
                                                            "<%d-char prompt>"
                                                            % len(prompt or ""))))
            print("")
        return 0

    day = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    folder = os.path.join(args.results, day)
    if not os.path.isdir(folder):
        os.makedirs(folder)

    by_model = collections.OrderedDict()
    for model in models:
        rows = collections.OrderedDict()
        for task in tasks:
            row = run_one(task, model, args.timeout)
            rows[task["id"]] = row
            print("%-10s %-28s %s  %s" % (model, task["id"], row["status"],
                                          (row.get("answer") or "")[:60]))
        by_model[model] = rows
        path = os.path.join(folder, "worker-%s.json" % re.sub(r"[^A-Za-z0-9.-]+", "-", model))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(collections.OrderedDict([
                ("model", model), ("tasks", args.tasks),
                ("ran_at", datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"),
                ("rows", list(rows.values()))]), ensure_ascii=False, indent=1) + "\n")
        print("wrote %s" % path)

    print("")
    text = table(by_model, tasks)
    print(text)
    with io.open(os.path.join(folder, "worker-comparison.md"), "w", encoding="utf-8") as fh:
        fh.write("# Worker model comparison, %s\n\n" % day + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
