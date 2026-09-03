#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack the A/B harness, the skill and the PRIVATE gold into one tarball for Codex.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WARNING: the tarball CONTAINS bench/private/ - one person's real shortlist, with real
addresses, real landlords and real money. It is built into dist/, which is gitignored,
and it is meant to be handed to one agent on one machine. Do not publish it, do not
attach it to an issue, do not put it in a bucket.

Contents:
  README-CODEX.md              a top-level pointer, written by this script
  bench/ab/CODEX_BRIEF.md      the brief, copied to the top level as well
  skills/vet-flat/             the skill: SKILL.md, references, scripts
  bench/                       run.py, grade.py, ab/, README.md, and private/
  evals/                       the public suite, for a sanity run
  tests/                       the offline tests and the fixtures the graders read
  docs/CONVENTIONS.md          the rules the repository works by

Excluded: .git, dist, __pycache__, .DS_Store, *.pyc, bench/results.

Standard library only (tarfile), Python 3.9.

Usage:
  tools/build_ab_package.py
  tools/build_ab_package.py --out dist/ab-package-for-codex.tar.gz --list
"""
from __future__ import unicode_literals

import argparse
import io
import os
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_OUT = os.path.join(ROOT, "dist", "ab-package-for-codex.tar.gz")
TOP = "pea-princess-ab"

INCLUDE = [
    "skills/vet-flat",
    "bench",
    "evals",
    "tests",
    "docs/CONVENTIONS.md",
    "docs/SCRIPTS.md",
    "docs/INSTALL.md",
    "README.md",
    "LICENSE",
    "LICENSE-DOCS",
]

SKIP_DIRS = (".git", "dist", "__pycache__", ".cache", "results")
SKIP_NAMES = (".DS_Store",)
SKIP_SUFFIX = (".pyc",)

README_CODEX = """# vet-flat A/B package for Codex

Unpack this anywhere. Everything is relative to the folder you unpacked into; where the
brief says `REPO`, it means that folder.

Read `CODEX_BRIEF.md` (also at `bench/ab/CODEX_BRIEF.md`) first. It is the whole task.

## What is in here

| path | what it is |
|---|---|
| `CODEX_BRIEF.md` | the brief: the arms, the exact commands, the constraints, what to report |
| `skills/vet-flat/` | the skill. `SKILL.md` is the instructions, `references/report-schema.json` is the output contract, `scripts/` are the fetchers |
| `bench/ab/configs/*.yaml` | the arms. The Codex ones are `codex-*.yaml` |
| `bench/ab/run_codex.py` | the runner: builds the workdir, writes `AGENTS.md`, calls `codex exec`, grades |
| `bench/ab/run_ab.py` | the sweep driver; `--agent codex` dispatches to `run_codex.py` |
| `bench/ab/grade_ab.py` | the A/B grader and the decision rule |
| `bench/ab/worker_eval.py` | the extraction-task comparison (written for Claude Code; the brief says how to do the GPT equivalent) |
| `bench/ab/README.md` | the protocol in full, and how to read the tables |
| `bench/run.py`, `bench/grade.py` | the single-run harness and the public grader |
| `bench/private/` | **PRIVATE.** The gold, the 20 cases, the profile, the worker tasks. Read-only |
| `evals/` | the public eight-flat suite, if you want a sanity run first |
| `tests/` | offline tests, including the fixtures the graders read |
| `docs/CONVENTIONS.md` | the rules this repository works by. The portal ban is in here |

## Before you spend anything

```
python3 bench/ab/run_ab.py --agent codex \\
    --configs codex-B-lean-sol,codex-C-terra-lite,codex-C-luna-lite \\
    --cases bench/private/cases_private.json \\
    --case-ids v2-buck,s09,e01,s02,nw03 --runs 3 \\
    --results bench/results/ab-codex-<date> --dry-run
```

Read the command list, then drop `--dry-run`.

## The three rules that matter most

1. **`bench/private/` is private and read-only.** Do not publish it, do not paste it,
   do not edit `gold.json`.
2. **No portal fetching.** Rightmove, Zoopla, OnTheMarket, PrimeLocation, OpenRent,
   HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com. Official registers and
   public APIs only.
3. **No permission-bypass flags.** `-s workspace-write` with
   `sandbox_workspace_write.network_access=true` is the whole story;
   `--dangerously-bypass-approvals-and-sandbox` is never acceptable.

Write results only under `bench/results/ab-codex-<date>/`.
"""


def keep(path):
    parts = path.split(os.sep)
    if any(p in SKIP_DIRS for p in parts):
        return False
    name = parts[-1]
    return name not in SKIP_NAMES and not name.endswith(SKIP_SUFFIX)


def collect():
    """[(absolute path, name inside the tarball)], sorted, deterministic."""
    out = []
    for rel in INCLUDE:
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            if keep(rel):
                out.append((src, "%s/%s" % (TOP, rel)))
            continue
        if not os.path.isdir(src):
            continue
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                full = os.path.join(base, name)
                inside = os.path.relpath(full, ROOT)
                if keep(inside):
                    out.append((full, "%s/%s" % (TOP, inside)))
    brief = os.path.join(ROOT, "bench", "ab", "CODEX_BRIEF.md")
    if os.path.exists(brief):
        out.append((brief, "%s/CODEX_BRIEF.md" % TOP))
    return sorted(set(out), key=lambda pair: pair[1])


def build(out_path, show=False):
    members = collect()
    folder = os.path.dirname(os.path.abspath(out_path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    readme = os.path.join(folder, ".README-CODEX.md.tmp")
    with io.open(readme, "w", encoding="utf-8") as fh:
        fh.write(README_CODEX)

    with tarfile.open(out_path, "w:gz") as tar:
        info = tar.gettarinfo(readme, arcname="%s/README-CODEX.md" % TOP)
        info.mtime = int(info.mtime)
        with open(readme, "rb") as fh:
            tar.addfile(info, fh)
        for src, inside in members:
            tar.add(src, arcname=inside, recursive=False)
    os.unlink(readme)

    size = os.path.getsize(out_path)
    private = sum(1 for _, inside in members if "/bench/private/" in inside)
    print("wrote %s" % out_path)
    print("  %d files, %.1f MB" % (len(members) + 1, size / 1024.0 / 1024.0))
    print("  %d of them are PRIVATE (bench/private/). Hand this to one agent on one "
          "machine; do not publish it." % private)
    if show:
        for _, inside in members:
            print("  %s" % inside)
    return size


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--list", action="store_true", help="print every file that went in")
    args = ap.parse_args(argv)
    if not os.path.exists(os.path.join(ROOT, "bench", "private", "gold.json")):
        print("warning: bench/private/gold.json is missing; run bench/private/build_gold.py "
              "first or the package will have no gold in it", file=sys.stderr)
    build(args.out, args.list)
    return 0


if __name__ == "__main__":
    sys.exit(main())
