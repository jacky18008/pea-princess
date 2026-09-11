#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The street question, two skill versions, one host: tokens, calls, wall time, and a blind quality
read. Used for "one call per street" (2026-09-11) and for the street-sampling / noise / depth-tier arm.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Each pair runs the same prompt (a private conversation prefix ending in the street question, with
outcode centroids for two streets) once per arm on Codex, each arm with its own skill snapshot
installed in a private HOME so the host cannot read the machine's global copy (verified 2026-09-11:
with HOME overridden and CODEX_HOME pointing at the real config, Codex lists only the skills under
that HOME). The raw event stream of every run is kept; commands are stored whole, never truncated.

    python3 bench/street_ab.py --before bench/ab/skill-variants/skill-<tag> --after bench/ab/skill-variants/skill-<commit> \\
        --prompt bench/private/street-ab-prompt.txt --out bench/private/street-ab-<day> --pairs 3
    python3 bench/street_ab.py --judge bench/private/street-ab-<day>      # blind pairwise read by Opus
    python3 bench/street_ab.py --report bench/private/street-ab-<day>

Rows: bench/private/<out>/rows.jsonl; streams under raw/. Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import datetime
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JUDGE_MODEL = "claude-opus-5"

JUDGE_PROMPT = """You are reading two assistant answers to the same question in a London flat search. The person had
compared two one-bedroom listings from two PDFs and then asked whether the assistant could scan the
surroundings of both streets for quietness. Both answers had the same open-data scripts available;
they differ in what they found and how they said it. You do not know which is which. Judge only the
text below.

Answer A:
<<<A
{A}
A>>>

Answer B:
<<<B
{B}
B>>>

Reply with one JSON object and nothing else:
{{
 "more_useful": "A" | "B" | "tie",
 "why": "one or two sentences, in the language of the answers",
 "found": {{
   "A": {{"centroid_off_street": true|false, "noise_db_with_source": true|false, "works_about_to_start": true|false,
          "quiet_vs_safety_separated": true|false, "answers_in_persons_language": true|false, "numbers_without_source": <int>}},
   "B": {{same keys}}
 }},
 "accuracy_concerns": {{"A": "specific sentences that are unsupported or contradictory, or ''", "B": "..."}},
 "shorter_and_clearer": "A" | "B" | "tie"
}}
Definitions: centroid_off_street = the answer says the given coordinates were not on the street itself
(a centroid or an approximation) and what it did about it; noise_db_with_source = a modelled noise
level in dB is given and attributed to an official noise map; works_about_to_start = a specific nearby
planning application or condition submission that signals building works is named with a distance;
numbers_without_source = count of figures (money, distances, counts, dB) with no source, formula or
"you said" in the same sentence."""


def read(path):
    return io.open(path, encoding="utf-8").read()


def parse_stream(stdout):
    usage, cmds, searches, final, types = None, [], 0, "", {}
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "turn.completed":
            usage = ev.get("usage")
        it = ev.get("item") or {}
        key = "%s/%s" % (ev.get("type"), it.get("type"))
        types[key] = types.get(key, 0) + 1
        if ev.get("type") == "item.completed":
            if it.get("type") == "command_execution":
                cmds.append((it.get("command") or "").replace("\n", " "))
            if it.get("type") in ("web_search", "web_search_call"):
                searches += 1
            if it.get("type") == "agent_message":
                final = it.get("text") or final
    return usage, cmds, searches, final, types


def run_arm(arm, skill_dir, prompt, model, out_dir, pair, timeout):
    work = tempfile.mkdtemp(prefix="vetflat-streetab-")
    home_skills = os.path.join(work, ".agents", "skills")
    os.makedirs(home_skills)
    shutil.copytree(skill_dir, os.path.join(home_skills, "pea-princess"))
    env = dict(os.environ)
    env["HOME"] = work
    env.setdefault("CODEX_HOME", os.path.join(os.path.expanduser("~"), ".codex"))
    cmd = ["codex", "exec", "--cd", work, "--sandbox", "workspace-write", "-c", "sandbox_workspace_write.network_access=true",
           "--skip-git-repo-check", "--json", "--model", model, "--", prompt]
    t0 = datetime.datetime.utcnow()
    try:
        proc = subprocess.run(cmd, cwd=work, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
        stdout, stderr, code = proc.stdout or "", proc.stderr or "", proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr, code = "", "timeout"
    seconds = (datetime.datetime.utcnow() - t0).total_seconds()
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    io.open(os.path.join(out_dir, "raw", "%s-%d.jsonl" % (arm, pair)), "w", encoding="utf-8").write(stdout)
    usage, cmds, searches, final, types = parse_stream(stdout)
    row = {"arm": arm, "pair": pair, "skill_dir": skill_dir, "model": model, "exit": code, "seconds": round(seconds, 1),
           "usage": usage, "commands": cmds, "script_runs": sum(1 for c in cmds if ".py" in c and "sed -n" not in c and "cat " not in c),
           "area_scan_calls": sum(1 for c in cmds if "area_scan" in c), "noise_calls": sum(1 for c in cmds if "noise.py" in c),
           "web_searches": searches, "reply_chars": len(final), "reply": final, "types": types,
           "stderr_tail": stderr[-400:], "started": t0.isoformat() + "Z"}
    shutil.rmtree(work, ignore_errors=True)
    return row


def load_rows(out_dir):
    path = os.path.join(out_dir, "rows.jsonl")
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in read(path).splitlines() if l.strip()]


def judge(out_dir, reviewer=JUDGE_MODEL, timeout=600):
    rows = load_rows(out_dir)
    pairs = sorted(set(r["pair"] for r in rows))
    verdicts = []
    rnd = random.Random(20260911)
    for p in pairs:
        b = [r for r in rows if r["pair"] == p and r["arm"] == "before" and r.get("reply")]
        a = [r for r in rows if r["pair"] == p and r["arm"] == "after" and r.get("reply")]
        if not b or not a:
            continue
        flip = rnd.random() < 0.5
        first, second = (a[-1], b[-1]) if flip else (b[-1], a[-1])
        prompt = JUDGE_PROMPT.replace("{A}", first["reply"]).replace("{B}", second["reply"])
        cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
               "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", reviewer, "--", prompt]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
            text = (json.loads(proc.stdout) or {}).get("result", "") if proc.stdout.strip().startswith("{") else proc.stdout
        except Exception as exc:  # noqa: BLE001
            text = "ERROR %s" % exc
        m = re.search(r"\{.*\}", text, re.S)
        try:
            v = json.loads(m.group(0)) if m else {"error": text[:300]}
        except ValueError:
            v = {"error": text[:300]}
        v["pair"] = p
        v["A_is"] = "after" if flip else "before"
        v["B_is"] = "before" if flip else "after"
        if v.get("more_useful") in ("A", "B"):
            v["winner"] = v["A_is"] if v["more_useful"] == "A" else v["B_is"]
        else:
            v["winner"] = v.get("more_useful")
        verdicts.append(v)
        print("pair %d: winner=%s | %s" % (p, v.get("winner"), (v.get("why") or v.get("error") or "")[:160]), flush=True)
    io.open(os.path.join(out_dir, "quality.json"), "w", encoding="utf-8").write(json.dumps(verdicts, ensure_ascii=False, indent=1))
    return verdicts


def report(out_dir):
    rows = load_rows(out_dir)
    print("| Arm | Pair | Tool calls | Script runs | Scan calls | Web searches | Input tokens (incl. cached) | New input | Output | Wall |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["pair"], r["arm"] != "before")):
        u = r.get("usage") or {}
        inp, cached = u.get("input_tokens") or 0, u.get("cached_input_tokens") or 0
        print("| %s | %d | %d | %d | %d | %d | %.2fM | %dk | %.1fk | %d s%s |" % (
            r["arm"], r["pair"], len(r["commands"]), r["script_runs"], r["area_scan_calls"], r["web_searches"],
            inp / 1e6, (inp - cached) / 1000, (u.get("output_tokens") or 0) / 1000, r["seconds"], "" if r["exit"] == 0 else " (exit %s)" % r["exit"]))
    qpath = os.path.join(out_dir, "quality.json")
    if os.path.exists(qpath):
        vs = json.loads(read(qpath))
        print("\nBlind quality (%s): " % JUDGE_MODEL + ", ".join("pair %d → %s" % (v["pair"], v.get("winner")) for v in vs))
        for key in ("centroid_off_street", "noise_db_with_source", "works_about_to_start", "quiet_vs_safety_separated", "numbers_without_source"):
            vals = {}
            for v in vs:
                f = v.get("found") or {}
                for side in ("A", "B"):
                    arm = v.get("%s_is" % side)
                    vals.setdefault(arm, []).append((f.get(side) or {}).get(key))
            print("  %s: %s" % (key, "; ".join("%s=%s" % (arm, vals[arm]) for arm in sorted(vals))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before")
    ap.add_argument("--after")
    ap.add_argument("--prompt")
    ap.add_argument("--out")
    ap.add_argument("--pairs", type=int, default=3)
    ap.add_argument("--model", default="gpt-5.6-terra")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--judge")
    ap.add_argument("--report")
    ap.add_argument("--reviewer", default=JUDGE_MODEL)
    a = ap.parse_args()
    if a.judge:
        judge(a.judge, a.reviewer)
        return 0
    if a.report:
        report(a.report)
        return 0
    if not (a.before and a.after and a.prompt and a.out):
        ap.print_help()
        return 2
    os.makedirs(a.out, exist_ok=True)
    prompt = read(a.prompt)
    io.open(os.path.join(a.out, "arms.json"), "w", encoding="utf-8").write(json.dumps({"before": a.before, "after": a.after, "model": a.model, "prompt_sha_chars": len(prompt)}, indent=1))
    done = load_rows(a.out)
    for pair in range(a.pairs):
        for arm, skill in (("before", a.before), ("after", a.after)):
            if any(r["pair"] == pair and r["arm"] == arm and r.get("exit") == 0 and r.get("reply") for r in done):
                continue
            row = run_arm(arm, skill, prompt, a.model, a.out, pair, a.timeout)
            with io.open(os.path.join(a.out, "rows.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            u = row.get("usage") or {}
            print("%s #%d: exit=%s %ds in=%s cached=%s out=%s | calls=%d scans=%d noise=%d searches=%d chars=%d" % (
                arm, pair, row["exit"], int(row["seconds"]), u.get("input_tokens"), u.get("cached_input_tokens"), u.get("output_tokens"),
                len(row["commands"]), row["area_scan_calls"], row["noise_calls"], row["web_searches"], row["reply_chars"]), flush=True)
    print("STREET-AB-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
