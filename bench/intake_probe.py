#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""How does the host ask the first questions when the person has no idea? Typed vs forced-into-options.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

One turn: the person says they have no idea where to start. The probe records every question the
host asked — through its native question tool (Claude Code's AskUserQuestion, Codex's question
items) or in the reply text — and grades the shape of the intake:

  questions      how many were asked (tool + text)
  forced         typed answers (a destination, a figure, a date) squeezed into invented options
  choice_ok      fixed-set answers (home type, deal-breakers, yes/no) asked through the tool
  moves          the reply also did something (a number, an area, a step), not only asked

Nothing is fetched: the same deny-and-log hook as link_probe.py. `--skill-dir` lets a run use a
snapshot of the skill, so a before/after comparison is two folders, not two commits.

    python3 bench/intake_probe.py --agent claude --model claude-sonnet-5 --repeats 2 --label before --skill-dir /tmp/skill-before
    python3 bench/intake_probe.py --agent claude --model claude-sonnet-5 --repeats 2 --label after
    python3 bench/intake_probe.py --report bench/private/intake-probe-<day>
"""
from __future__ import unicode_literals

import argparse
import datetime
import io
import json
import os
import re
import shutil
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import link_probe as LP  # noqa: E402

PROMPTS = [
    ("zh_noidea", "我完全沒想法。剛拿到倫敦國王學院的 offer，九月底開學，第一次去英國，不知道從哪開始。"),
    ("en_noidea", "I have no idea where to start. I'm moving to London in October for a job near Liverpool Street."),
]

TYPED = re.compile(r"(?i)where|destination|address|postcode|campus|office|work|commute|get to|校區|校区|地址|郵遞|邮递|上班|通勤|去哪|哪裡|哪里|工作地點|工作地点|"
                   r"budget|how much|maximum|£|pcm|per month|預算|预算|多少|上限|"
                   r"when|date|move.?in|start|arrive|幾月|几月|什麼時候|什么时候|日期|入住|搬")
FIXED_SET = re.compile(r"(?i)type of (home|place|flat)|studio|one.?bed|room|shared|deal.?breaker|must.?have|quiet|light|ground floor|"
                       r"furnished|yes/no|how deep|房型|套房|雅房|合租|整租|禁忌|地雷|安靜|採光|采光|家具|幾房|几房")


def prepare_workdir(agent, skill_dir):
    path = tempfile.mkdtemp(prefix="vetflat-intake-%s-" % agent)
    home = os.path.join(path, LP.SKILL_HOME[agent])
    os.makedirs(home)
    shutil.copytree(skill_dir, os.path.join(home, "vet-flat"))
    return path


def claude_command(prompt, workdir, model, hook_path):
    settings = {"disableAllHooks": False,
                "hooks": {"PreToolUse": [{"matcher": "WebFetch|WebSearch|Bash|mcp__.*",
                                          "hooks": [{"type": "command", "command": "python3 %s" % hook_path}]}]}}
    allowed = "Read,Glob,Grep,Skill,AskUserQuestion,Bash(python3 .claude/skills/vet-flat/scripts/*)"
    return ["claude", "-p", "--output-format", "stream-json", "--verbose", "--allowedTools", allowed,
            "--setting-sources", "project", "--settings", json.dumps(settings),
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--add-dir", workdir,
            "--session-id", str(uuid.uuid4())] + (["--model", model] if model else []) + ["--", prompt]


def questions_from_claude(attempts):
    out = []
    for a in attempts:
        if a.get("tool") == "AskUserQuestion":
            for q in (a.get("input") or {}).get("questions") or []:
                out.append({"via": "tool", "text": q.get("question") or "", "header": q.get("header"),
                            "options": [o.get("label") for o in (q.get("options") or [])],
                            "multi": bool(q.get("multiSelect"))})
    return out


def questions_from_codex_stream(stdout):
    out = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        for d in LP.walk(ev, []):
            t = str(d.get("type") or "")
            if "question" in t.lower() or "request_user_input" in t.lower() or "ask_user" in t.lower():
                qs = d.get("questions") or d.get("items") or []
                if isinstance(qs, list) and qs:
                    for q in qs:
                        if isinstance(q, dict):
                            opts = q.get("options") or q.get("choices") or []
                            out.append({"via": "tool", "text": q.get("question") or q.get("text") or q.get("prompt") or "",
                                        "header": q.get("header") or q.get("id"),
                                        "options": [o.get("label") if isinstance(o, dict) else str(o) for o in opts],
                                        "multi": bool(q.get("multiSelect") or q.get("multiple"))})
                elif d.get("question") or d.get("prompt"):
                    out.append({"via": "tool", "text": d.get("question") or d.get("prompt") or "", "header": None,
                                "options": [], "multi": False})
    return out


def questions_from_text(final):
    qs = []
    for line in re.split(r"\n+", final or ""):
        for sent in re.split(r"(?<=[?？])\s*", line):
            if sent.strip().endswith(("?", "？")) and len(sent.strip()) > 4:
                qs.append({"via": "text", "text": sent.strip()[:160], "options": [], "multi": False})
    return qs


def grade(questions, final):
    forced = [q for q in questions if q["via"] == "tool" and q["options"] and TYPED.search(q["text"]) and not FIXED_SET.search(q["text"])]
    choice_ok = [q for q in questions if q["via"] == "tool" and q["options"] and FIXED_SET.search(q["text"])]
    moves = bool(re.search(r"£\s?\d|\d+\s?(分鐘|分钟|min)|Zone \d|\b(step|首先|先|第一步|first)\b", final or ""))
    return {"questions": len(questions), "tool_questions": sum(1 for q in questions if q["via"] == "tool"),
            "text_questions": sum(1 for q in questions if q["via"] == "text"),
            "forced": len(forced), "forced_detail": [{"q": q["text"][:80], "options": q["options"][:4]} for q in forced],
            "choice_ok": len(choice_ok), "moves": moves, "reply_chars": len(final or "")}


def run_one(agent, model, key, prompt, out_dir, index, timeout, skill_dir, label):
    workdir = prepare_workdir(agent, skill_dir)
    side = tempfile.mkdtemp(prefix="vetflat-intake-side-")
    hook_log = os.path.join(side, "hook.log")
    if agent == "claude":
        hook_path = os.path.join(side, "probe_hook.py")
        with io.open(hook_path, "w", encoding="utf-8") as fh:
            fh.write(LP.HOOK % {"net": repr(LP.HOOK_DENY.pattern)})
        cmd = claude_command(prompt, workdir, model, hook_path)
    else:
        cmd = LP.codex_command(prompt, workdir, model)
    env = dict(os.environ, LINK_PROBE_LOG=hook_log)
    started = datetime.datetime.utcnow()
    stdout, stderr, code = LP._launch(cmd, workdir, env, timeout)
    if agent == "claude":
        attempts, hook_seen, final, usage = LP.parse_claude(stdout, hook_log)
        questions = questions_from_claude(attempts)
    else:
        attempts, final = LP.parse_codex(stdout)
        hook_seen, usage = [], {}
        questions = questions_from_codex_stream(stdout)
    questions += questions_from_text(final)
    row = {"label": label, "agent": agent, "model": model, "prompt": key, "index": index,
           "started": started.isoformat() + "Z", "seconds": (datetime.datetime.utcnow() - started).total_seconds(),
           "exit": code, "tools": [a.get("tool") for a in attempts], "questions": questions,
           "grade": grade(questions, final), "reply": final, "usage": usage, "stderr_tail": stderr[-600:],
           "network_attempts": [h for h in hook_seen if h.get("denied")]}
    raw = os.path.join(out_dir, "raw", "%s-%s-%s-%s-%d.jsonl" % (label, agent, (model or "default").replace("/", "_"), key, index))
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    with io.open(raw, "w", encoding="utf-8") as fh:
        fh.write(stdout)
    with io.open(os.path.join(out_dir, "rows.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    shutil.rmtree(workdir, ignore_errors=True)
    shutil.rmtree(side, ignore_errors=True)
    return row


def report(out_dir):
    with io.open(os.path.join(out_dir, "rows.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    print("| label | agent | model | prompt | runs | questions (median) | via tool | forced typed→options | choice via tool | reply moves | median chars |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    keys = sorted({(r["label"], r["agent"], r["model"], r["prompt"]) for r in rows})
    for label, agent, model, key in keys:
        g = [r for r in rows if (r["label"], r["agent"], r["model"], r["prompt"]) == (label, agent, model, key)]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
        print("| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d/%d | %d |" % (
            label, agent, model, key, len(g), med([r["grade"]["questions"] for r in g]),
            sum(r["grade"]["tool_questions"] for r in g), sum(r["grade"]["forced"] for r in g),
            sum(r["grade"]["choice_ok"] for r in g), sum(1 for r in g if r["grade"]["moves"]), len(g),
            med([r["grade"]["reply_chars"] for r in g])))
    for r in rows:
        for d in r["grade"]["forced_detail"]:
            print("FORCED: %s %s %s #%d -> %s %s" % (r["label"], r["model"], r["prompt"], r["index"], d["q"], d["options"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", choices=("claude", "codex"))
    ap.add_argument("--model")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--prompts", default="all")
    ap.add_argument("--label", default="after", help="which skill wording this run tests, e.g. before / after")
    ap.add_argument("--skill-dir", default=LP.SKILL_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    if args.report:
        report(args.report); return 0
    if not args.agent:
        ap.error("--agent is required unless --report")
    out_dir = args.out or os.path.join(HERE, "private", "intake-probe-%s" % datetime.date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)
    wanted = [p for p in PROMPTS if args.prompts == "all" or p[0] in args.prompts.split(",")]
    for index in range(args.repeats):
        for key, prompt in wanted:
            row = run_one(args.agent, args.model, key, prompt, out_dir, index, args.timeout, args.skill_dir, args.label)
            g = row["grade"]
            print("%s %s %s %s #%d: exit=%s questions=%d (tool %d, text %d) forced=%d choice_ok=%d moves=%s chars=%d %ss" % (
                args.label, args.agent, args.model, key, index, row["exit"], g["questions"], g["tool_questions"],
                g["text_questions"], g["forced"], g["choice_ok"], g["moves"], g["reply_chars"], int(row["seconds"])), flush=True)
    report(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
