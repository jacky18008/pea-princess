#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add the sub-agent threads to every Codex row of a scorecard: codex exec --json reports the main thread's
usage only, and Codex 0.153 delegates the skill's scripts to spawned threads whose tokens live in the
rollout files under ~/.codex/sessions. Found 2026-09-12; the street A/B was off by 1.6-3.6x before this.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

    python3 bench/ab/account_codex.py --results bench/results/<folder>          # print, write nothing
    python3 bench/ab/account_codex.py --results bench/results/<folder> --write  # add tokens_all_threads to scorecard.json (backup kept)

For each row with agent codex: the thread id is read from the raw stream (thread.started); the rollout
with that id and every rollout whose parent chain leads to it are summed (last cumulative token_count
per thread). Rows whose rollout is gone are left as they are and listed. Standard library only.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import shutil
import sys

SESSIONS = os.path.join(os.path.expanduser("~"), ".codex", "sessions")


def rollout_index(root=SESSIONS):
    idx = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not (name.startswith("rollout-") and name.endswith(".jsonl")):
                continue
            path = os.path.join(dirpath, name)
            try:
                meta = json.loads(io.open(path, encoding="utf-8", errors="replace").readline()).get("payload") or {}
            except (OSError, ValueError):
                continue
            if meta.get("id"):
                idx[meta["id"]] = (path, meta.get("parent_thread_id"))
    return idx


def thread_usage(path):
    last, calls = None, 0
    for line in io.open(path, encoding="utf-8", errors="replace"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        p = ev.get("payload") or {}
        if ev.get("type") == "event_msg" and p.get("type") == "token_count" and (p.get("info") or {}).get("total_token_usage"):
            last = p["info"]["total_token_usage"]
        if ev.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
            calls += 1
    return last or {}, calls


def thread_id_of(raw_path):
    try:
        for line in io.open(raw_path, encoding="utf-8", errors="replace"):
            if '"thread.started"' in line:
                return json.loads(line).get("thread_id")
    except (OSError, ValueError):
        return None
    return None


def account(rows, idx):
    children = {}
    for tid, (path, parent) in idx.items():
        if parent:
            children.setdefault(parent, []).append(tid)
    done, missing = [], []
    for r in rows:
        if r.get("agent") != "codex":
            continue
        raw = r.get("raw")
        tid = thread_id_of(raw) if raw and os.path.exists(raw) else None
        if not tid or tid not in idx:
            missing.append((r.get("config"), r.get("case"), r.get("run_index"), "no raw stream" if not tid else "rollout not on this machine"))
            continue
        stack, threads = [tid], []
        while stack:
            t = stack.pop()
            threads.append(t)
            stack.extend(children.get(t, []))
        tot = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0, "threads": len(threads), "subagent_calls": 0}
        for t in threads:
            u, calls = thread_usage(idx[t][0])
            for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
                tot[k] += u.get(k) or 0
            if t != tid:
                tot["subagent_calls"] += calls
        r["thread_id"] = tid
        r["tokens_all_threads"] = tot
        done.append(r)
    return done, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True, help="a results folder with scorecard.json")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    path = os.path.join(a.results, "scorecard.json")
    doc = json.load(io.open(path, encoding="utf-8"))
    rows = doc if isinstance(doc, list) else doc.get("rows") or []
    done, missing = account(rows, rollout_index())
    print("| config | case | run | main-thread input | all threads input | cached | output | threads | sub-agent calls |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in done:
        t = r["tokens_all_threads"]; m = (r.get("tokens") or {}).get("input_tokens") or 0
        print("| %s | %s | %s | %.2fM | %.2fM | %.2fM | %.1fk | %d | %d |" % (r.get("config"), r.get("case"), r.get("run_index"), m / 1e6,
              t["input_tokens"] / 1e6, t["cached_input_tokens"] / 1e6, t["output_tokens"] / 1e3, t["threads"], t["subagent_calls"]))
    for m in missing:
        print("not accounted: %s %s run %s (%s)" % m)
    if a.write and done:
        shutil.copy(path, path + ".bak")
        io.open(path, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("written: %s (%d rows accounted; backup .bak)" % (path, len(done)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
