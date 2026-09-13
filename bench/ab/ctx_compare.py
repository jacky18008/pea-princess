#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare context-slimming arms against the baseline: paired by cell (config) and case, per repeat.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

    python3 bench/ab/ctx_compare.py --baseline <folder> <folder> --arm A <folder> <folder> [--arm B ...]

Each folder is a results dir with scorecard.json (one repeat of every cell x case, or more). Rows are keyed
(config, case); the first folder listed for an arm is repeat 1, the second repeat 2. Quality: fact_recall,
stable_fact_recall, fabrications, unknown_honesty (per cent), schema_valid. Cost: tokens — Claude rows use
total_tokens; Codex rows use tokens_all_threads.input_tokens when present (bench/ab/account_codex.py),
else the main-thread input_tokens, and say so. Noise = baseline repeat 1 vs repeat 2 on the same cells.
Standard library only.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import statistics
import sys


def load(folder):
    path = os.path.join(folder, "scorecard.json")
    doc = json.load(io.open(path, encoding="utf-8"))
    rows = doc if isinstance(doc, list) else doc.get("rows") or []
    out = {}
    for r in rows:
        if int(r.get("run_index") or 1) != 1:
            continue  # one repeat per folder: run 1 only (the design runs repeats as separate folders)
        out[(r.get("config"), r.get("case"))] = r
    return out


def pct(v):
    try:
        return float(str(v).rstrip("%")) / 100.0
    except (TypeError, ValueError):
        return None


def tokens(r):
    if r.get("agent") == "codex":
        t = r.get("tokens_all_threads")
        if t:
            return t.get("input_tokens"), "all threads"
        return (r.get("tokens") or {}).get("input_tokens"), "main thread only"
    return r.get("total_tokens") or (r.get("tokens") or {}).get("total_tokens"), "total"


def metrics(r):
    tok, how = tokens(r)
    return {"facts": r.get("fact_recall"), "stable": r.get("stable_fact_recall"), "fab": r.get("fabrications"),
            "unknown": pct(r.get("unknown_honesty")), "schema": 1.0 if r.get("schema_valid") else 0.0,
            "tokens": tok, "wall": r.get("wall_time_s"), "how": how}


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return (sum(xs) / len(xs)) if xs else None


def fmt(v, kind="f"):
    if v is None:
        return "-"
    if kind == "tok":
        return "%.2fM" % (v / 1e6)
    if kind == "i":
        return "%d" % v
    return "%.2f" % v


def cell_table(label, reps, configs):
    """Per config: mean over cases and repeats."""
    print("\n%s (%d repeat%s)" % (label, len(reps), "" if len(reps) == 1 else "s"))
    print("| cell | n | facts | stable | fabrications | unknown-honesty | schema ok | tokens | wall s |")
    print("|---|---|---|---|---|---|---|---|---|")
    for cfg in configs:
        ms = [metrics(rep[k]) for rep in reps for k in rep if k[0] == cfg]
        if not ms:
            continue
        print("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (cfg, len(ms), fmt(mean([m["facts"] for m in ms])), fmt(mean([m["stable"] for m in ms])),
              fmt(mean([m["fab"] for m in ms])), fmt(mean([m["unknown"] for m in ms])), fmt(mean([m["schema"] for m in ms])),
              fmt(mean([m["tokens"] for m in ms]), "tok"), fmt(mean([m["wall"] for m in ms]), "i")))


def paired(label, base_reps, arm_reps, configs):
    """Paired differences arm - baseline per (config, case, repeat index)."""
    print("\n%s: paired differences (arm − baseline), same cell, same case, same repeat index" % label)
    print("| cell | pairs | Δ facts | Δ stable | Δ fabrications | Δ unknown-honesty | tokens ratio (arm/base) | Δ wall s |")
    print("|---|---|---|---|---|---|---|---|")
    for cfg in configs:
        d = {"facts": [], "stable": [], "fab": [], "unknown": [], "ratio": [], "wall": []}
        for i in range(min(len(base_reps), len(arm_reps))):
            for k in base_reps[i]:
                if k[0] != cfg or k not in arm_reps[i]:
                    continue
                b, a = metrics(base_reps[i][k]), metrics(arm_reps[i][k])
                for m in ("facts", "stable", "fab", "unknown", "wall"):
                    if isinstance(a[m], (int, float)) and isinstance(b[m], (int, float)):
                        d[m].append(a[m] - b[m])
                if a["tokens"] and b["tokens"]:
                    d["ratio"].append(a["tokens"] / b["tokens"])
        n = len(d["facts"])
        if not n and not d["ratio"]:
            continue
        print("| %s | %d | %s | %s | %s | %s | %s | %s |" % (cfg, max(n, len(d["ratio"])), fmt(mean(d["facts"])), fmt(mean(d["stable"])), fmt(mean(d["fab"])),
              fmt(mean(d["unknown"])), fmt(statistics.median(d["ratio"])) if d["ratio"] else "-", fmt(mean(d["wall"]), "i")))


def noise(base_reps, configs):
    if len(base_reps) < 2:
        return
    print("\nBaseline noise: repeat 2 − repeat 1, same cell and case")
    print("| cell | pairs | Δ facts | Δ stable | Δ fabrications | tokens ratio (rep2/rep1) |")
    print("|---|---|---|---|---|---|")
    for cfg in configs:
        df, ds, dfab, ratio = [], [], [], []
        for k in base_reps[0]:
            if k[0] != cfg or k not in base_reps[1]:
                continue
            a, b = metrics(base_reps[1][k]), metrics(base_reps[0][k])
            if isinstance(a["facts"], (int, float)) and isinstance(b["facts"], (int, float)):
                df.append(a["facts"] - b["facts"]); ds.append((a["stable"] or 0) - (b["stable"] or 0)); dfab.append((a["fab"] or 0) - (b["fab"] or 0))
            if a["tokens"] and b["tokens"]:
                ratio.append(a["tokens"] / b["tokens"])
        if df or ratio:
            print("| %s | %d | %s (max |Δ| %s) | %s | %s | %s |" % (cfg, max(len(df), len(ratio)), fmt(mean(df)), fmt(max(abs(x) for x in df)) if df else "-",
                  fmt(mean(ds)), fmt(mean(dfab)), fmt(statistics.median(ratio)) if ratio else "-"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", nargs="+", required=True)
    ap.add_argument("--arm", nargs="+", action="append", default=[], help="label then folders, e.g. --arm A f1 f2")
    a = ap.parse_args()
    base = [load(f) for f in a.baseline]
    configs = sorted({k[0] for rep in base for k in rep})
    hows = {metrics(r)["how"] for rep in base for r in rep.values() if r.get("agent") == "codex"}
    print("Codex token basis in the baseline: %s" % ", ".join(sorted(hows)))
    cell_table("Baseline", base, configs)
    noise(base, configs)
    for spec in a.arm:
        label, folders = spec[0], spec[1:]
        reps = [load(f) for f in folders]
        cell_table("Arm %s" % label, reps, configs)
        paired("Arm %s" % label, base, reps, configs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
