#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replay the person's real flat-hunting messages against the current skill, and judge the new answer
by what the person actually reacted to.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

The private corpus (never committed) holds curated cases: the conversation before one answer, the
answer, the person's real reaction, and what happened next. This probe freezes the prefix, hands
the person's message to an agent that has the skill installed and a profile at the chosen depth,
records the new answer, then asks a strong judge three things: did it do what was asked, how good
is the reply, and — given what this person praised or complained about right after the original
answer — would they be satisfied. The judge also says whether the new answer beats the original.

The answerer never sees the reaction or what happened next. Listing sites are not fetched: the same
deny-and-log hook as link_probe.py; the skill's own scripts may read open registers.

    python3 bench/history_replay.py --corpus <dir> --cases case-02,case-06,case-08 --agent claude --model claude-sonnet-5 --depth standard
    python3 bench/history_replay.py --corpus <dir> --cases all --agent codex --model gpt-5.6-terra --depth lite
    python3 bench/history_replay.py --report bench/private/history-replay-<day>

Rows and raw streams land under bench/private/ (ignored by git). Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import datetime
import glob
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

DEFAULT_CORPUS = os.path.join(HERE, "..", ".pea-playground", "claude-rental-history-20260910")
JUDGE_MODEL = "claude-opus-5"
HEAD = re.compile(r"^### (user|assistant) · source line (\d+) · `([0-9a-f-]+)`\s*$")


# ------------------------------------------------------------------ corpus --
def parse_case(path):
    """The case as one flat sequence of (role, text) blocks in file order, fences respected."""
    text = io.open(path, encoding="utf-8").read()
    role, fence, buf, seq = None, False, [], []
    for line in text.splitlines():
        if line.startswith("```"):
            if fence:
                fence = False
                if role:
                    seq.append((role, "\n".join(buf).strip()))
                buf = []
            else:
                fence = True
            continue
        if fence:
            buf.append(line)
            continue
        m = HEAD.match(line)
        if m:
            role = m.group(1)
    return seq


def case_focus(corpus, case_id):
    idx = os.path.join(corpus, "case-index.md")
    if os.path.exists(idx):
        for line in io.open(idx, encoding="utf-8"):
            if "[%s]" % case_id in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2:
                    return cells[1]
    return ""


def case_path(corpus, case_id):
    for folder in ("cases-v3", "short-stay-cases"):
        p = os.path.join(corpus, folder, case_id + ".md")
        if os.path.exists(p):
            return p
    raise IOError("case not found: %s" % case_id)


def _user_blocks(seq):
    return [t for r, t in seq if r == "user"]


def split_case(seq, turn="ask"):
    """The answer under review is the last assistant block that a user block follows (that user
    block is the real reaction). turn="ask": replay the message that produced the answer; the
    reaction is the judge's evidence, the answer is the original. turn="reaction": replay the
    reaction itself; the original is what the assistant said next, and the evidence is what the
    person said after that (when the record has it)."""
    k = max(i for i, (r, _) in enumerate(seq) if r == "assistant" and any(rr == "user" for rr, _ in seq[i + 1:]))
    react_i = min(i for i, (r, _) in enumerate(seq) if i > k and r == "user")
    reaction = "\n\n".join(t for r, t in seq[react_i:next((i for i, (rr, _) in enumerate(seq) if i > react_i and rr == "assistant"), len(seq))] if r == "user")
    if turn == "ask":
        msg_i = max(i for i, (r, _) in enumerate(seq[:k]) if r == "user")
        history = seq[:msg_i]
        message = seq[msg_i][1]
        original = "\n\n".join(t for r, t in seq[msg_i + 1:k + 1] if r == "assistant")
        evidence = reaction
    else:
        history = seq[:react_i]
        message = reaction
        after = [i for i, (r, _) in enumerate(seq) if i > react_i and r == "assistant"]
        if after:
            a0 = after[0]
            nxt_user = next((i for i, (r, _) in enumerate(seq) if i > a0 and r == "user"), len(seq))
            original = "\n\n".join(t for r, t in seq[a0:nxt_user] if r == "assistant")
            evidence = "\n\n".join(t for r, t in seq[nxt_user:nxt_user + 2] if r == "user") if nxt_user < len(seq) else ""
        else:
            original, evidence = "", ""
    return history, message, original, evidence


def transcript(history, limit=14000):
    lines = []
    for role, text in history:
        lines.append(("[使用者]\n%s" if role == "user" else "[助理]\n%s") % text)
    out = "\n\n".join(lines)
    if len(out) > limit:
        out = "（更早的部分略）…\n\n" + out[-limit:]
    return out


def case_date(corpus, case_id, turn="ask"):
    """The calendar date of the message being answered, from the case's JSON sidecar: the reaction's own
    timestamp for the reaction turn, else the last prefix record's (the target follows it by minutes).
    None when the sidecar or the timestamps are missing."""
    path = os.path.join(corpus, "cases", case_id + ".json")
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ts = (d.get("reaction") or {}).get("timestamp") if turn == "reaction" else None
    if not ts:
        stamps = [x.get("timestamp") for x in (d.get("prefix") or []) if x.get("timestamp")]
        ts = stamps[-1] if stamps else None
    return ts[:10] if ts else None


def answer_prompt(history, message, today=None):
    date_line = (("今天是 %s（對話最新一則訊息的日期），不要用執行當天的日期" % today) if today
                 else "對話的日期以對話裡提到的為準，不要用執行當天的日期")
    return ("用 pea-princess 技能。以下是你和使用者先前的對話紀錄（2026 年 8 到 9 月初，倫敦找房，原文）。"
            "請接著回覆最後一則使用者訊息，用使用者的語言；房源網站的頁面由使用者提供，不要自己去讀。"
            "%s；沒有狀態檔就以上文為帳本，不要向使用者談環境、技能清單、工具權限或檔案。\n\n"
            "=== 先前對話 ===\n%s\n\n=== 最新訊息 ===\n%s" % (date_line, transcript(history), message))


# ------------------------------------------------------------------ runner --
def prepare_workdir(agent, depth, skill_dir=None):
    path = tempfile.mkdtemp(prefix="vetflat-replay-%s-" % agent)
    home = os.path.join(path, LP.SKILL_HOME[agent])
    os.makedirs(home)
    shutil.copytree(skill_dir or LP.SKILL_DIR, os.path.join(home, "pea-princess"))
    with io.open(os.path.join(path, "profile.yaml"), "w", encoding="utf-8") as fh:
        fh.write('budget_mode: %s\nlanguage: "zh-TW"\n' % depth)
    return path


def claude_command(prompt, workdir, model, hook_path):
    settings = {"disableAllHooks": False,
                "hooks": {"PreToolUse": [{"matcher": "WebFetch|WebSearch|Bash|mcp__.*",
                                          "hooks": [{"type": "command", "command": "python3 %s" % hook_path}]}]}}
    allowed = "Read,Glob,Grep,Skill,Write,Edit,Bash(python3 .claude/skills/pea-princess/scripts/*),Bash(python3 scripts/*)"
    return ["claude", "-p", "--output-format", "stream-json", "--verbose", "--allowedTools", allowed,
            "--setting-sources", "project", "--settings", json.dumps(settings),
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--add-dir", workdir,
            "--session-id", str(uuid.uuid4())] + (["--model", model] if model else []) + ["--", prompt]


def codex_command(prompt, workdir, model):
    return ["codex", "exec", "--cd", workdir, "--sandbox", "workspace-write",
            "-c", "sandbox_workspace_write.network_access=true", "--skip-git-repo-check", "--json"] + \
        (["--model", model] if model else []) + ["--", prompt]


def run_answer(agent, model, depth, prompt, timeout, skill_dir=None):
    workdir = prepare_workdir(agent, depth, skill_dir)
    side = tempfile.mkdtemp(prefix="vetflat-replay-side-")
    hook_log = os.path.join(side, "hook.log")
    if agent == "claude":
        hook_path = os.path.join(side, "probe_hook.py")
        with io.open(hook_path, "w", encoding="utf-8") as fh:
            fh.write(LP.HOOK % {"net": repr(LP.HOOK_DENY.pattern)})
        cmd = claude_command(prompt, workdir, model, hook_path)
    else:
        cmd = codex_command(prompt, workdir, model)
    env = dict(os.environ, LINK_PROBE_LOG=hook_log)
    t0 = datetime.datetime.utcnow()
    stdout, stderr, code = LP._launch(cmd, workdir, env, timeout)
    if agent == "claude":
        attempts, hook_seen, final, usage = LP.parse_claude(stdout, hook_log)
    else:
        attempts, final = LP.parse_codex(stdout)
        hook_seen, usage = [], {}
    out = {"exit": code, "seconds": (datetime.datetime.utcnow() - t0).total_seconds(), "tools": [a.get("tool") for a in attempts],
           "listing_fetch_attempts": [a for a in attempts if LP.is_fetch(a)], "reply": final, "usage": usage,
           "stderr_tail": stderr[-600:], "stdout": stdout}
    shutil.rmtree(workdir, ignore_errors=True)
    shutil.rmtree(side, ignore_errors=True)
    return out


# ------------------------------------------------------------------- judge --
JUDGE_PROMPT = """你是嚴格的評審。一位正在倫敦找房的使用者，在 2026 年 8–9 月和一個助理對話。下面給你：這個案例的重點、先前對話的尾段、使用者的那句話、當時助理的原答、使用者對原答的真實反應，以及現在新版助理對同一句話的新答。

請只評新答，回傳 JSON（不要別的文字）：
{"task": 0|1|2, "quality": 1|2|3|4|5, "satisfy": 0|1|2, "vs_history": "new"|"history"|"tie", "invented_numbers": 整數, "questions_asked": 整數, "issues": ["最多四條，每條一句"], "one_line": "一句話總評"}

規則：
- task：新答有沒有做到使用者這句話要的事（0 沒做、1 做一半、2 做到）。
- quality：白話、有上下文回顧、主詞名詞清楚、數字有解釋和出處、沒有代號和罐頭句、問題不超過三個、不確定的地方誠實說。5 是很好，1 是很差。
- satisfy：只看使用者的真實反應透露出他在意什麼（例如要 recap、不要代號、要修正費用算法、目標已改變），推斷他看到新答會不會滿意（0 不會、1 一半、2 會）。反應是證據，不是標準答案；原答也不是範本。
- vs_history：新答和原答，哪個對這位使用者更有用。
- invented_numbers：新答裡沒有出處、沒有算式、也不是使用者給的數字有幾個。
- 新答如果宣稱去讀了房源網站，或假裝看過沒提供的照片、頁面，算嚴重問題。
- 新答如果只複述舊資訊、只問問題不推進，quality 不高於 2。

=== 案例重點 ===
{focus}

=== 先前對話（尾段）===
{tail}

=== 使用者的那句話 ===
{message}

=== 當時的原答 ===
{history_answer}

=== 使用者的真實反應 ===
{reaction}

=== 新答 ===
{new_answer}
"""


def judge(row_inputs, timeout=600):
    prompt = JUDGE_PROMPT
    for key, value in row_inputs.items():
        prompt = prompt.replace("{%s}" % key, value or "（無）")
    cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
           "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", JUDGE_MODEL, "--", prompt]
    stdout, stderr, code = LP._launch(cmd, os.getcwd(), dict(os.environ), timeout)
    text, usage = "", {}
    try:
        env = json.loads(stdout)
        text = env.get("result") or ""
        usage = env.get("usage") or {}
        usage["cost_usd"] = env.get("total_cost_usd")
    except ValueError:
        text = stdout
    m = re.search(r"\{.*\}", text, re.S)
    verdict = None
    if m:
        try:
            verdict = json.loads(m.group(0))
        except ValueError:
            verdict = None
    return {"exit": code, "verdict": verdict, "raw": text[:2000], "usage": usage, "stderr_tail": stderr[-300:]}


# ------------------------------------------------------------- judge v2 --
# Adopted from docs/conversation-evaluation-design.md and conversation-acceptance-ux-gate.md
# (Codex, 2026-09-09/10): three non-offsetting gates, eight per-turn dimensions on 0-3 with
# null for not observable, the first visible sentence, the reaction as evidence with a quote.
JUDGE_V2_PROMPT = """你是嚴格的評審。一位在倫敦找房的使用者，2026 年 8–9 月和一個助理對話；下面是某一輪：案例重點、先前對話尾段、使用者的那句話、當時助理的原答、使用者對原答的真實反應、以及新版助理對同一句話的新答。請只評「新答」。

回傳 JSON（不要別的文字）：
{"gates": {"G1": {"status": "pass|fail|unknown", "reason": "一句", "quote": "新答原句或空"},
           "G2": {"status": "pass|fail|unknown", "reason": "一句", "quote": ""},
           "G3": {"status": "pass|fail|unknown", "reason": "一句", "quote": ""}},
 "first_sentence": {"quote": "新答第一句原文", "status": "pass|fail", "reason": "一句"},
 "T": {"T1": 0-3或null, "T2": 0-3或null, "T3": 0-3或null, "T4": 0-3或null, "T5": 0-3或null, "T6": 0-3或null, "T7": 0-3或null, "T8": 0-3或null},
 "T_notes": {"T1": "一句或空", "T4": "一句或空", "T6": "一句或空", "T8": "一句或空"},
 "task": 0|1|2,
 "satisfy": {"score": 0|1|2, "reaction_quote": "你依據的使用者反應原句", "reason": "一句"},
 "vs_history": "new|history|tie|unclear",
 "questions_asked": 整數,
 "issues": ["最多四條"],
 "one_line": "一句話總評"}

門檻（任一 fail 就是整輪不過，文筆不能抵銷）：
- G1 事實與證據：沒出處、沒算式、也不是使用者給的數字；把估計講成事實；引文不在來源裡；算錯。
- G2 授權與安全：宣稱去讀了房源網站或看過沒提供的頁面／照片；做了使用者沒授權的事；違背使用者明確指示。
- G3 當前必要條件：先前對話裡使用者說過的硬條件（預算、必要條件、已改變的目標）被忽略或推翻。
看不出來就 unknown，不能因為「沒發現」就 pass。

T 面向（0 實質失敗、1 明顯不足、2 可用、3 做得好；沒有觀察機會填 null）：
T1 回答當前問題；T2 熟悉自然的語言（沒代號、沒欄位名、沒罐頭句）；T3 資訊量與順序（不重述全部未知、不漏估計限制）；T4 實際進展與主動性（有分析、比較、查核成果，不只說「下一步會做」）；T5 有目的的釐清（最多三題、每題一個決定、不重問已答）；T6 證據與不確定性放在對應說法旁；T7 用上先前對話裡的新資訊與修正；T8 幫使用者做決定（一個相關取捨、可修正的下一步）。

第一句：新答第一則可見文字的第一句要切題、有依據、給答案或取捨；先講內部狀態、流程、客套或稱讚就是 fail。

satisfy：只看使用者的真實反應透露他在意什麼，推斷他看到新答會不會滿意；必須引用你依據的那一句反應。反應是證據不是標準答案；原答不是範本。
vs_history：新答和原答哪個對這位使用者更有用；不確定填 unclear。

=== 案例重點 ===
{focus}

=== 先前對話（尾段）===
{tail}

=== 使用者的那句話 ===
{message}

=== 當時的原答 ===
{history_answer}

=== 使用者的真實反應 ===
{reaction}

=== 新答 ===
{new_answer}
"""

SOURCE_CUE = re.compile(r"(來源|依據|根據|出處|法規|規定|上限|法律|條例|Act|EPC|能源證書|證書|警方|police|TfL|官方|統計|ONS|登記|Companies House|"
                        r"◆|■|●|▲|使用者|你說|你給|你提供|算式|公式|÷|×|=|約|估|大概|大約|左右|範圍|區間|依|按|引用|"
                        r"\bper\b|\bfrom\b|\bsource|\bcertificate|\bregister|\baccording)", re.I)
NUMBER = re.compile(r"(£\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:%|分鐘|分|週|周|週租|個月|月|年|m²|sq ?ft|平方|坪|英鎊|鎊|k\b|萬))")
DATE_LIKE = re.compile(r"\b(19|20)\d{2}[-/年.]\d{1,2}([-/月.]\d{1,2})?|\d{1,2}[/月]\d{1,2}[日號]?|\d{1,2}:\d{2}")
QUESTION_MARKS = re.compile(r"[?？]")


def numbers_without_cue(text):
    """Programmatic G1 signal: numbers in the reply whose sentence carries no source cue, no
    formula and no 'you said'. Dates and times are skipped. A heuristic, reported beside the
    judge's own view, never instead of it."""
    out = []
    for sent in re.split(r"(?<=[。.!?！？\n])", text or ""):
        cleaned = DATE_LIKE.sub(" ", sent)
        nums = NUMBER.findall(cleaned)
        if nums and not SOURCE_CUE.search(cleaned):
            out.extend(n.strip() for n in nums)
    return out


# What this person has said, across the whole search, about how they want to be answered. A standing
# prior for the judge (the person's own rules), not the reaction to any one answer.
PERSON_PROFILE = """=== 這位使用者的既有要求（他在整段找房過程中說過的，不是對某一答的反應）===
- 每次都要講清楚上下文：先一兩句回顧上次看到哪、現在在談什麼；主詞和名詞寫全，不用代號、不用代名詞帶過。
- 數字要解釋意思：這是好是壞、跟什麼比、對決定有什麼影響；不能只丟數字。
- 不要罐頭句、不要「很 AI」的空話；他很忙，要看得快。
- 指出錯誤時，要修正所有受影響的結論，不是只道歉。
- 喜歡具體、跟自己經驗連得起來的提醒（例如「別讓一頓好吃的飯掩蓋房子本身的缺陷」）。
- 需求會隨看房演進（採光從直射改成有晨光、面積可談），這是正常，不該被當成之前答錯。
"""


def judge_v2(row_inputs, timeout=600, use_profile=False):
    prompt = JUDGE_V2_PROMPT
    if use_profile:
        prompt = prompt.replace("=== 案例重點 ===", PERSON_PROFILE + "\n=== 案例重點 ===", 1)
    for key, value in row_inputs.items():
        prompt = prompt.replace("{%s}" % key, value or "（無）")
    cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
           "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", JUDGE_MODEL, "--", prompt]
    stdout, stderr, code = LP._launch(cmd, os.getcwd(), dict(os.environ), timeout)
    text, usage = "", {}
    try:
        env = json.loads(stdout)
        text = env.get("result") or ""
        usage = env.get("usage") or {}
        usage["cost_usd"] = env.get("total_cost_usd")
    except ValueError:
        text = stdout
    m = re.search(r"\{.*\}", text, re.S)
    verdict = None
    if m:
        try:
            verdict = json.loads(m.group(0))
        except ValueError:
            verdict = None
    return {"exit": code, "verdict": verdict, "raw": text[:3000], "usage": usage, "stderr_tail": stderr[-300:]}


def programmatic(reply, tools, fetch_attempts, message):
    zh = len(re.findall(r"[一-鿿]", reply or ""))
    zh_msg = len(re.findall(r"[一-鿿]", message or ""))
    return {"numbers_without_cue": numbers_without_cue(reply), "questions": len(QUESTION_MARKS.findall(reply or "")),
            "chars": len(reply or ""), "language_matches": (zh > 20) == (zh_msg > 5), "tools": len(tools or []),
            "listing_fetch_attempts": len(fetch_attempts or [])}


def v2_inputs(focus, history, message, hist_answer, reaction, new_answer):
    return {"focus": focus, "tail": transcript(history[-4:], 3000), "message": message[:3000],
            "history_answer": hist_answer[:7000], "reaction": reaction[:2000], "new_answer": new_answer[:9000]}


def row_key(r):
    return "%s|%s|%s|%s|%s|%s" % (r["case"], r.get("turn", "ask"), r["agent"], r["model"], r["depth"], r.get("label", ""))


def row_failed(r):
    a = r.get("answer") or {}
    reply = (a.get("reply") or "").strip()
    return a.get("exit") not in (0, "0") or not reply or reply.startswith("API Error") or "ENOTFOUND" in reply[:200]


def reply_sha(r):
    import hashlib
    return hashlib.sha256(((r.get("answer") or {}).get("reply") or "").encode("utf-8")).hexdigest()[:16]


def load_rows_merged(out_dir, keep_failed=False):
    """rows.jsonl plus judge_v2.jsonl merged; one row per key — the latest successful one when there is
    one (a retry after an outage supersedes the failed row); a v2 verdict attaches only to the reply it judged."""
    path = os.path.join(out_dir, "rows.jsonl")
    rows = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
    best = {}
    for r in rows:
        k = row_key(r)
        cur = best.get(k)
        if cur is None or (row_failed(cur) and not row_failed(r)) or (row_failed(cur) == row_failed(r)):
            best[k] = r
    rows = list(best.values())
    if not keep_failed:
        pass  # failed rows stay visible in the report as failures unless superseded
    v2path = os.path.join(out_dir, "judge_v2.jsonl")
    if os.path.exists(v2path):
        v2 = {}
        for l in io.open(v2path, encoding="utf-8"):
            if l.strip():
                d = json.loads(l); v2[(d["key"], d.get("sha"))] = d
        for r in rows:
            d = v2.get((row_key(r), reply_sha(r))) or (v2.get((row_key(r), None)) if not any(kk[0] == row_key(r) and kk[1] for kk in v2) else None)
            if d:
                r["judge_v2"] = d["judge_v2"]; r["programmatic"] = d["programmatic"]
    return rows


def rejudge(out_dir, only_missing=True, limit=None):
    """Judge v2 for every row that has an answer; verdicts go to judge_v2.jsonl (append-only, so a
    running batch that appends to rows.jsonl is never raced). Returns the count done."""
    rows = load_rows_merged(out_dir)
    corpus = os.path.abspath(DEFAULT_CORPUS)
    v2path = os.path.join(out_dir, "judge_v2.jsonl")
    done = 0
    for r in rows:
        if only_missing and r.get("judge_v2", {}).get("verdict"):
            continue
        if row_failed(r):
            continue
        if limit and done >= limit:
            break
        seq = parse_case(case_path(corpus, r["case"]))
        history, message, hist_answer, reaction = split_case(seq, r.get("turn", "ask"))
        r["judge_v2"] = judge_v2(v2_inputs(r.get("focus", ""), history, message, hist_answer, reaction, r["answer"]["reply"]))
        r["programmatic"] = programmatic(r["answer"]["reply"], r["answer"].get("tools"), r["answer"].get("listing_fetch_attempts"), message)
        done += 1
        with io.open(v2path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": row_key(r), "sha": reply_sha(r), "judge_v2": r["judge_v2"], "programmatic": r["programmatic"]}, ensure_ascii=False) + "\n")
        v = r["judge_v2"].get("verdict") or {}
        print("rejudged %s %s %s/%s: gates=%s T=%s sat=%s vs=%s nums=%d" % (
            r["case"], r.get("turn"), r["model"], r["depth"], "".join((v.get("gates") or {}).get(g, {}).get("status", "?")[0] for g in ("G1", "G2", "G3")),
            [(v.get("T") or {}).get("T%d" % i) for i in range(1, 9)], (v.get("satisfy") or {}).get("score"), v.get("vs_history"),
            len(r["programmatic"]["numbers_without_cue"])), flush=True)
    return done


def calibrate(out_dir, cases, turn="ask", use_profile=False):
    """How far is the judge from the person? Give the judge the ORIGINAL answer as if it were new,
    with the reaction hidden, and ask satisfy; then classify the real reaction; compare."""
    corpus = os.path.abspath(DEFAULT_CORPUS)
    rows = []
    for case_id in cases:
        seq = parse_case(case_path(corpus, case_id))
        history, message, original, reaction = split_case(seq, turn)
        if not original.strip():
            continue
        inputs = v2_inputs(case_focus(corpus, case_id), history, message, "（校準：此欄不提供）", "（校準：此欄不提供）", original)
        pred = judge_v2(inputs, use_profile=use_profile)
        cls_prompt = ("下面是使用者在看到助理的回答後說的話。請判斷它主要是：praise（滿意或肯定）、complaint（不滿、抱怨、批評）、"
                      "correction（指出錯誤要求修正）、shift（目標或條件改變，不評價回答）、neutral（追問或探索，看不出滿不滿意）。"
                      "回傳 JSON：{\"polarity\": \"praise|complaint|correction|shift|neutral\", \"quote\": \"依據原句\"}\n\n=== 反應 ===\n" + reaction[:2000])
        cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
               "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", JUDGE_MODEL, "--", cls_prompt]
        stdout, _, _ = LP._launch(cmd, os.getcwd(), dict(os.environ), 300)
        polarity = None
        try:
            txt = json.loads(stdout).get("result") or ""
            m = re.search(r"\{.*\}", txt, re.S)
            polarity = json.loads(m.group(0)) if m else None
        except (ValueError, AttributeError):
            polarity = None
        expected = {"praise": 2, "complaint": 0, "correction": 0, "shift": None, "neutral": 1}.get((polarity or {}).get("polarity"), None)
        v = pred.get("verdict") or {}
        rows.append({"case": case_id, "turn": turn, "predicted_satisfy": (v.get("satisfy") or {}).get("score"),
                     "predicted_T": v.get("T"), "predicted_gates": v.get("gates"), "reaction_polarity": polarity, "expected_satisfy": expected})
        print("calibrate %s: predicted satisfy=%s | real reaction=%s -> expected=%s" % (
            case_id, rows[-1]["predicted_satisfy"], (polarity or {}).get("polarity"), expected), flush=True)
    folder = os.path.join(out_dir, "calibration")
    os.makedirs(folder, exist_ok=True)
    with io.open(os.path.join(folder, "judge-vs-reactions-%s%s.json" % (turn, "-profile" if use_profile else "")), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    scored = [r for r in rows if r["expected_satisfy"] is not None and r["predicted_satisfy"] is not None]
    agree = sum(1 for r in scored if r["predicted_satisfy"] == r["expected_satisfy"])
    near = sum(1 for r in scored if abs(r["predicted_satisfy"] - r["expected_satisfy"]) <= 1)
    print("calibration: %d comparable cases; exact agreement %d; within one step %d" % (len(scored), agree, near))
    return rows


# ----------------------------------------------------------------- driver --
def run_case(args, case_id, out_dir):
    corpus = os.path.abspath(args.corpus)
    seq = parse_case(case_path(corpus, case_id))
    history, message, hist_answer, reaction = split_case(seq, args.turn)
    focus = case_focus(corpus, case_id)
    today = case_date(os.path.abspath(args.corpus or DEFAULT_CORPUS), case_id, args.turn) if getattr(args, "inject_date", False) else None
    prompt = answer_prompt(history, message, today)
    ans = run_answer(args.agent, args.model, args.depth, prompt, args.timeout, args.skill_dir)
    raw = os.path.join(out_dir, "raw", "%s-%s-%s-%s-%s.jsonl" % (case_id, args.turn, args.agent, (args.model or "default").replace("/", "_"), args.depth))
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    with io.open(raw, "w", encoding="utf-8") as fh:
        fh.write(ans.pop("stdout") or "")
    verdict = None
    if ans["reply"].strip() and not args.no_judge:
        verdict = judge({"focus": focus, "tail": transcript(history[-4:], 3000), "message": message[:3000],
                         "history_answer": hist_answer[:7000], "reaction": reaction[:2000], "new_answer": ans["reply"][:9000]})
    row = {"case": case_id, "turn": args.turn, "focus": focus, "agent": args.agent, "model": args.model, "depth": args.depth, "label": args.label, "today": today,
           "started": datetime.datetime.utcnow().isoformat() + "Z", "message_chars": len(message), "history_blocks": len(history),
           "answer": ans, "judge": verdict}
    with io.open(os.path.join(out_dir, "rows.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def report_v2(rows):
    rows = [r for r in rows if r.get("judge_v2", {}).get("verdict")]
    print("| agent | model | depth | turn | label | cases | G1/G2/G3 pass | first sentence pass | T mean (0-3) | T1 T2 T4 T5 T6 T8 | task | satisfy | beats original | numbers w/o cue (prog.) | questions |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    keys = sorted({(r["agent"], r["model"], r["depth"], r.get("turn", "ask"), r.get("label", "")) for r in rows})
    for agent, model, depth, turn, label in keys:
        g = [r for r in rows if (r["agent"], r["model"], r["depth"], r.get("turn", "ask"), r.get("label", "")) == (agent, model, depth, turn, label)]
        vs = [r["judge_v2"]["verdict"] for r in g]
        def gate(gid):
            return sum(1 for v in vs if ((v.get("gates") or {}).get(gid) or {}).get("status") == "pass")
        first = sum(1 for v in vs if (v.get("first_sentence") or {}).get("status") == "pass")
        tvals = [x for v in vs for x in (v.get("T") or {}).values() if isinstance(x, (int, float))]
        def tm(k):
            xs = [(v.get("T") or {}).get(k) for v in vs]; xs = [x for x in xs if isinstance(x, (int, float))]
            return ("%.1f" % (sum(xs) / len(xs))) if xs else "-"
        task = sum(float(v.get("task") or 0) for v in vs) / len(vs)
        sat = sum(float((v.get("satisfy") or {}).get("score") or 0) for v in vs) / len(vs)
        wins = sum(1 for v in vs if v.get("vs_history") == "new")
        nums = sum(len((r.get("programmatic") or {}).get("numbers_without_cue") or []) for r in g) / len(g)
        qs = sum(float((r.get("programmatic") or {}).get("questions") or 0) for r in g) / len(g)
        print("| %s | %s | %s | %s | %s | %d | %d/%d/%d | %d | %.2f | %s %s %s %s %s %s | %.2f | %.2f | %d/%d | %.1f | %.1f |" % (
            agent, model, depth, turn, label, len(g), gate("G1"), gate("G2"), gate("G3"), first,
            (sum(tvals) / len(tvals)) if tvals else 0, tm("T1"), tm("T2"), tm("T4"), tm("T5"), tm("T6"), tm("T8"), task, sat, wins, len(vs), nums, qs))


def report(out_dir):
    rows = load_rows_merged(out_dir)
    if any(r.get("judge_v2", {}).get("verdict") for r in rows):
        report_v2(rows)
        print()
    print("| agent | model | depth | turn | label | cases | task (0-2) | quality (1-5) | satisfy (0-2) | beats original | invented numbers | listing fetch tries | median chars | answer cost USD |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    keys = sorted({(r["agent"], r["model"], r["depth"], r.get("turn", "ask"), r.get("label", "")) for r in rows})
    for agent, model, depth, turn, label in keys:
        g = [r for r in rows if (r["agent"], r["model"], r["depth"], r.get("turn", "ask"), r.get("label", "")) == (agent, model, depth, turn, label)]
        v = [r["judge"]["verdict"] for r in g if r.get("judge") and r["judge"].get("verdict")]
        mean = lambda k: (sum(float(x.get(k, 0) or 0) for x in v) / len(v)) if v else 0.0
        wins = sum(1 for x in v if x.get("vs_history") == "new")
        chars = sorted(len(r["answer"]["reply"] or "") for r in g)
        cost = sum((r["answer"]["usage"] or {}).get("cost_usd") or 0 for r in g)
        fetch = sum(1 for r in g if r["answer"]["listing_fetch_attempts"])
        print("| %s | %s | %s | %s | %s | %d | %.2f | %.2f | %.2f | %d/%d | %.1f | %d | %d | %.2f |" % (
            agent, model, depth, turn, label, len(g), mean("task"), mean("quality"), mean("satisfy"), wins, len(v), mean("invented_numbers"), fetch,
            chars[len(chars) // 2] if chars else 0, cost))
    print()
    for r in rows:
        v = (r.get("judge") or {}).get("verdict") or {}
        print("%s %s %s/%s %s: task=%s q=%s sat=%s vs=%s | %s" % (r["case"], r.get("turn", "ask"), r["model"], r["depth"], r["label"], v.get("task"), v.get("quality"),
                                                             v.get("satisfy"), v.get("vs_history"), (v.get("one_line") or "")[:120]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--cases", default="all", help="comma-separated case ids, or all")
    ap.add_argument("--agent", choices=("claude", "codex"))
    ap.add_argument("--model")
    ap.add_argument("--depth", choices=("lite", "standard", "deep"), default="standard")
    ap.add_argument("--turn", choices=("ask", "reaction"), default="ask", help="replay the message before the reviewed answer, or the reaction itself")
    ap.add_argument("--label", default="")
    ap.add_argument("--skill-dir", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--rejudge", default=None, help="results folder: judge v2 every row that lacks one (answers are not re-run)")
    ap.add_argument("--retry-failed", default=None, help="results folder: re-run every configuration row that failed (API error, empty, non-zero exit); new rows are appended")
    ap.add_argument("--rejudge-limit", type=int, default=None)
    ap.add_argument("--calibrate", default=None, help="results folder: judge the ORIGINAL answers blind and compare with the real reactions")
    ap.add_argument("--inject-date", action="store_true",
                    help="tell the answerer the date of the message it answers (from the case's JSON sidecar); the reviews found models using the run date otherwise")
    ap.add_argument("--judge-profile", action="store_true", help="give the judge the person's standing preferences (their own rules, not any reaction)")
    args = ap.parse_args()
    if args.report:
        report(args.report); return 0
    if args.rejudge:
        n = rejudge(args.rejudge, limit=args.rejudge_limit); print("rejudged %d rows" % n); report(args.rejudge); return 0
    if args.retry_failed:
        failed = [r for r in load_rows_merged(args.retry_failed) if row_failed(r)]
        if args.agent:
            failed = [r for r in failed if r["agent"] == args.agent]
        print("retrying %d failed rows" % len(failed), flush=True)
        for r in failed:
            class A: pass
            a = A(); a.corpus = args.corpus; a.agent = r["agent"]; a.model = r["model"]; a.depth = r["depth"]; a.turn = r.get("turn", "ask")
            a.label = r.get("label", ""); a.skill_dir = args.skill_dir; a.timeout = args.timeout; a.no_judge = args.no_judge
            row = run_case(a, r["case"], args.retry_failed)
            print("retried %s %s %s/%s %s: exit=%s chars=%d" % (r["case"], a.turn, a.model, a.depth, a.label, row["answer"]["exit"], len(row["answer"]["reply"] or "")), flush=True)
        report(args.retry_failed); return 0
    if args.calibrate:
        corpus = os.path.abspath(args.corpus)
        ids = sorted(os.path.basename(p)[:-3] for folder in ("cases-v3", "short-stay-cases") for p in glob.glob(os.path.join(corpus, folder, "*.md"))) if args.cases == "all" else [c.strip() for c in args.cases.split(",") if c.strip()]
        calibrate(args.calibrate, ids, args.turn, use_profile=args.judge_profile); return 0
    if not args.agent:
        ap.error("--agent is required unless --report")
    out_dir = args.out or os.path.join(HERE, "private", "history-replay-%s" % datetime.date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)
    corpus = os.path.abspath(args.corpus)
    if args.cases == "all":
        ids = sorted(os.path.basename(p)[:-3] for folder in ("cases-v3", "short-stay-cases") for p in glob.glob(os.path.join(corpus, folder, "*.md")))
    else:
        ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    for case_id in ids:
        row = run_case(args, case_id, out_dir)
        v = (row.get("judge") or {}).get("verdict") or {}
        print("%s %s %s %s: exit=%s chars=%d tools=%d fetch=%d | task=%s q=%s sat=%s vs=%s %s" % (
            case_id, args.agent, args.model, args.depth, row["answer"]["exit"], len(row["answer"]["reply"] or ""), len(row["answer"]["tools"]),
            len(row["answer"]["listing_fetch_attempts"]), v.get("task"), v.get("quality"), v.get("satisfy"), v.get("vs_history"),
            (v.get("one_line") or "")[:90]), flush=True)
    report(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
