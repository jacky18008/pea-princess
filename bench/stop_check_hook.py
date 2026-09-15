#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A Claude Code Stop hook that runs the skill's pre-send checker on the reply about to be sent and, when it
finds something, blocks the stop with the findings so the model revises. The skill's text asks the model to
run the checker itself; in 90 replayed runs it never did (2026-09-15), so this puts the check in the host.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Hook contract (Claude Code): stdin carries JSON with at least transcript_path (a JSONL of the session) and
stop_hook_active (true when a previous Stop hook already blocked this turn); stdout {"decision": "block",
"reason": "..."} keeps the turn going with the reason shown to the model; anything else lets it stop.
Environment: PEA_REPLY_CHECK = path to reply_check.py (default: the installed skill's copy);
PEA_STOP_MAX = how many blocks per turn before letting the reply through (default 2).
Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import io
import json
import os
import sys
import importlib.util


def load_checker():
    path = os.environ.get("PEA_REPLY_CHECK") or os.path.join(os.path.expanduser("~"), ".claude", "skills", "pea-princess", "scripts", "reply_check.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("reply_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def last_texts(transcript_path):
    """(last user text, last assistant text) from a Claude Code session transcript (JSONL)."""
    user, assistant = "", ""
    try:
        lines = io.open(transcript_path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return user, assistant
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        role = (msg or {}).get("role") or rec.get("type")
        content = (msg or {}).get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if not text.strip():
            continue
        if role == "user":
            if text.lstrip().startswith("Stop hook feedback"):
                continue   # our own block reason, not the person
            user = text
            assistant = ""   # a new user turn resets the reply we are checking
        elif role == "assistant":
            assistant = text if not assistant else assistant + "\n" + text
    return user, assistant


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if payload.get("stop_hook_active") and int(os.environ.get("PEA_STOP_MAX", "2")) <= 1:
        return 0
    counter = os.path.join(payload.get("cwd") or os.getcwd(), ".pea-stop-count")
    n = 0
    try:
        n = int(io.open(counter).read().strip() or 0)
    except (OSError, ValueError):
        n = 0
    if n >= int(os.environ.get("PEA_STOP_MAX", "2")):
        try:
            os.remove(counter)
        except OSError:
            pass
        return 0
    checker = load_checker()
    if checker is None:
        return 0
    user, assistant = last_texts(payload.get("transcript_path") or "")
    if payload.get("last_assistant_message"):
        assistant = payload["last_assistant_message"]   # the host hands over the reply about to be sent
    debug = os.environ.get("PEA_STOP_DEBUG")
    if debug:
        try:
            io.open(debug, "a", encoding="utf-8").write(json.dumps({"n": n, "user": user[:200], "assistant": assistant[:200]}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    if not assistant.strip():
        return 0
    findings = checker.scan(assistant, previous=user or None)
    findings = [f for f in findings if f["kind"] != "numbers" or True]
    if not findings:
        try:
            os.remove(counter)
        except OSError:
            pass
        return 0
    try:
        io.open(counter, "w").write(str(n + 1))
    except OSError:
        pass
    lines = ["Before this reply goes out, the pre-send check found %d thing(s). Fix them in the reply itself and send again (do not mention this check to the person):" % len(findings)]
    for f in findings[:8]:
        lines.append("- [%s] %s → %s" % (f["kind"], f["fragment"][:100], f["say"]))
    out = json.dumps({"decision": "block", "reason": "\n".join(lines)}, ensure_ascii=False)
    if debug:
        try:
            io.open(debug, "a", encoding="utf-8").write(out + "\n")
        except OSError:
            pass
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
