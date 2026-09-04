#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The pre-release gate: re-grade a results directory and refuse a release that invented a number.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHAT THIS DOES
==============
1. Reads the scorecard in a results directory (``scorecard.json``, or every
   ``*/scorecard.json`` under it when you point at ``bench/results`` itself).
2. Keeps the rows whose ``config`` is the one being released (``--config``;
   the default is the config marked ``default: true`` in ``bench/ab/configs``,
   and ``B-lean`` when none is marked).
3. Re-grades every one of those runs with ``bench/grade.py`` against the case's
   recorded truth, using the report kept next to the raw stdout
   (``raw/<config>-<case>-<run>.report.json``) or the ``report_path`` in the row.
   A run whose report is gone falls back to the numbers the scorecard recorded,
   and the table says so.
4. Prints one table and exits 1 unless EVERY run has ``fabrications == 0`` and a
   valid schema.

THE RULE
========
A model may reach any verdict it likes. It may not state a number the register
does not support, and it may not state a number nobody can trace. So the gate is
two questions per run: how many fabrications, and does the report still match
report-schema.json. The count of numbers carrying neither a source id nor a
computed_by note is shown beside them, because that is what the release notes
promise readers; it is reported, not gated, so an old results tree does not
become ungateable.

USAGE
=====
    python3 bench/release_gate.py bench/results/2026-09-04
    python3 bench/release_gate.py bench/results/2026-09-04 --config B-lean
    python3 bench/release_gate.py bench/results --evals evals/evals.json --json-out gate.json

Exit codes: 0 the gate passes, 1 it does not (or there is nothing to gate),
2 wrong arguments. Standard library only, Python 3.9. No network.
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CONFIG_DIR = os.path.join(HERE, "ab", "configs")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")
SCHEMA_PATH = os.path.join(ROOT, "skills", "vet-flat", "references", "report-schema.json")

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "vet-flat", "scripts"))
import grade as grader  # noqa: E402
import render  # noqa: E402

FALLBACK_CONFIG = "B-lean"


# --------------------------------------------------------------- the config --
def default_config(directory=None):
    """The config to gate on: the one marked `default: true`, else B-lean."""
    directory = directory or CONFIG_DIR
    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".yaml"):
                continue
            path = os.path.join(directory, name)
            try:
                with io.open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (IOError, OSError):
                continue
            for line in text.splitlines():
                if line.strip().replace(" ", "").lower() == "default:true":
                    return os.path.splitext(name)[0]
    return FALLBACK_CONFIG


# ------------------------------------------------------------- the scorecard --
def scorecards(directory):
    """Every scorecard.json under `directory`, newest folder last. [(path, rows)]"""
    out = []
    own = os.path.join(directory, "scorecard.json")
    if os.path.exists(own):
        out.append(own)
    else:
        for name in sorted(os.listdir(directory)):
            nested = os.path.join(directory, name, "scorecard.json")
            if os.path.exists(nested):
                out.append(nested)
    cards = []
    for path in out:
        with io.open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        cards.append((path, rows if isinstance(rows, list) else []))
    return cards


def report_for(row, scorecard_path):
    """The report this run wrote: the copy kept in the results tree, else its workdir."""
    folder = os.path.dirname(scorecard_path)
    name = "%s-%s-%s.report.json" % (safe(row.get("config")), safe(row.get("case")),
                                     int(row.get("run_index") or 1))
    kept = os.path.join(folder, "raw", name)
    if os.path.exists(kept):
        return kept
    original = row.get("report_path")
    if original and os.path.exists(original):
        return original
    return None


def safe(text):
    """The same file-name rule bench/run.py writes with."""
    return re.sub(r"[^A-Za-z0-9._#-]+", "-", str(text or "none"))


# ------------------------------------------------------------------ grading --
def shown(path):
    """The path as a reader will recognise it: relative inside the repo, absolute outside."""
    full = os.path.abspath(path)
    return os.path.relpath(full, ROOT) if full.startswith(ROOT + os.sep) else full


def load_schema():
    with io.open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def judge(row, scorecard_path, evals_path, schema):
    """One table row: fabrications, schema, unsourced numbers, and where they came from."""
    case_id = str(row.get("case") or "").split("#")[0]
    out = collections.OrderedDict([
        ("config", row.get("config")), ("case", row.get("case")),
        ("run", row.get("run_index")), ("fabrications", row.get("fabrications")),
        ("schema_ok", row.get("schema_valid")), ("unsourced", None),
        ("graded", "scorecard"), ("note", None),
    ])
    path = report_for(row, scorecard_path)
    if path:
        try:
            with io.open(path, encoding="utf-8") as fh:
                report = json.load(fh)
        except (IOError, OSError, ValueError) as exc:
            out["note"] = "could not read %s: %s" % (os.path.basename(path), exc)
            report = None
        if report is not None:
            out["unsourced"] = len(render.unsourced_numbers(report, schema))
            try:
                case, _ = grader.load_case(evals_path, case_id)
            except (KeyError, IOError, OSError, ValueError):
                out["note"] = "case %r is not in %s; kept the recorded scores" % (
                    case_id, shown(evals_path))
            else:
                card = grader.grade(report, case, grader.case_profile_path(evals_path, case))
                out["fabrications"] = card["scores"]["fabrications"]
                out["schema_ok"] = card["schema"]["valid"]
                out["graded"] = "re-graded"
    elif row.get("kind") == "conversation":
        out["note"] = "conversation case: no report to re-grade"
    else:
        out["note"] = "no report kept in the results tree"

    if out["fabrications"] is None or out["schema_ok"] is None:
        out["ok"] = False
        out["note"] = "; ".join([n for n in (out["note"], "never graded") if n])
    else:
        out["ok"] = out["fabrications"] == 0 and bool(out["schema_ok"])
    return out


# ------------------------------------------------------------------- output --
COLUMNS = [("case", 34), ("run", 3), ("fabrications", 12), ("schema", 6),
           ("no source", 9), ("graded", 10), ("result", 6)]


def table(rows):
    lines = ["  ".join(name.ljust(width) for name, width in COLUMNS),
             "  ".join("-" * width for _, width in COLUMNS)]
    for row in rows:
        cells = [str(row["case"])[:34], str(row["run"] if row["run"] is not None else "?"),
                 "?" if row["fabrications"] is None else str(row["fabrications"]),
                 "?" if row["schema_ok"] is None else ("ok" if row["schema_ok"] else "INVALID"),
                 "?" if row["unsourced"] is None else str(row["unsourced"]),
                 row["graded"], "PASS" if row["ok"] else "FAIL"]
        lines.append("  ".join(cell.ljust(width) for cell, (_, width) in zip(cells, COLUMNS)))
        if row.get("note"):
            lines.append("      %s" % row["note"])
    return "\n".join(lines)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="a results directory: bench/results/<date>, or bench/results")
    ap.add_argument("--config", default=None,
                    help="the configuration being released (default: the config marked "
                         "'default: true' in bench/ab/configs, else %s)" % FALLBACK_CONFIG)
    ap.add_argument("--evals", default=EVALS_JSON, help="the case file the runs used")
    ap.add_argument("--json-out", help="also write the gate result here")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not os.path.isdir(args.results):
        sys.stderr.write("usage error: %s is not a directory\n" % args.results)
        return 2
    config = args.config or default_config()
    try:
        cards = scorecards(args.results)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("could not read the scorecards: %s\n" % exc)
        return 1
    if not cards:
        sys.stderr.write("no scorecard.json under %s\n" % args.results)
        return 1

    schema = load_schema()
    rows = []
    for path, entries in cards:
        for entry in entries:
            if isinstance(entry, dict) and entry.get("config") == config:
                rows.append(judge(entry, path, args.evals, schema))

    passed = all(row["ok"] for row in rows) and bool(rows)
    print("Release gate: %s" % config)
    print("Results:      %s" % shown(args.results))
    print("")
    if rows:
        print(table(rows))
    else:
        print("no runs of %r in this results tree" % config)
    print("")
    print("Gate: every run of %s must have 0 fabrications and a valid schema. "
          "%d run(s), %d passing." % (config, len(rows), sum(1 for r in rows if r["ok"])))
    print("The 'no source' column counts numbers with neither a source id nor a computed_by "
          "note. It is reported, not gated.")
    print("VERDICT: %s" % ("PASS" if passed else "FAIL"))

    if args.json_out:
        payload = collections.OrderedDict([
            ("config", config),
            ("results", os.path.abspath(args.results)),
            ("checked_at", datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"),
            ("runs", rows),
            ("passed", passed),
        ])
        with io.open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
