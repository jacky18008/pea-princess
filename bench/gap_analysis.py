#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gap between a cheap model's replayed reply and the answer the person got at the time (from a stronger
model with more context), listed and classified so the harness-fixable part can be counted.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

    python3 bench/gap_analysis.py --out bench/private/history-replay-2026-09-11 --ids bench/private/calibration-2026-09-14/key.json
    python3 bench/gap_analysis.py --out <folder> --model claude-sonnet-5 --label variant-c --depth standard
    python3 bench/gap_analysis.py --report bench/private/gap-analysis-2026-09-14.jsonl

For every selected row an Opus reader sees the conversation tail, the person's message, the replayed reply and
the original answer, and returns the gaps as a list: each with a category —
  missing_work      the reply did not do something the original did and the skill could have done (run a script,
                    read the ledger, cover a named item, give a fallback)
  missing_knowledge a fact or rule of thumb the original knew and the reply did not (a price band, how a scheme works)
  missing_context   the original had files, earlier research or a ledger the replay did not give the model
  judgement         synthesis, trade-off reasoning or explanation depth the model itself lacks
  reply_better      the reply had something the original did not
— a one-line description, and whether it would change what the person does next (material: yes/no).
Output: one JSON line per row; --report aggregates by model and category. Standard library only.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_replay as H  # noqa: E402

READER = "claude-opus-5"
PROMPT = """你是嚴格但公平的讀者。下面是一位在倫敦找房的人和助理的對話尾段、這個人的一句話、兩個回答：A 是當時（較強模型、有較多上下文）給的原答，B 是現在用較便宜模型重播出的新答。請列出 B 相對 A 的每一項差距，也列出 B 比 A 好的地方。

只回 JSON（不要別的文字）：
{"gaps": [{"category": "missing_work|missing_knowledge|missing_context|judgement|reply_better", "what": "一句話，講具體缺了什麼或多了什麼", "material": true|false, "harness_fix": "一句話：技能文字、腳本或檢查可以怎麼補；模型本身的問題就寫 none"}],
 "summary": "一句話總評 B 相對 A"}

分類定義：
- missing_work：B 沒做 A 做了的事，而技能本來做得到（跑腳本查資料、讀先前的紀錄、回答被點名的每一項、給備案）。
- missing_knowledge：A 知道、B 不知道的事實或行規（價格帶、某個制度怎麼運作、常見陷阱）。
- missing_context：A 手上有檔案、先前研究或帳本，重播時沒有給 B；不是 B 的錯。
- judgement：綜合判斷、取捨推理、解釋的深度，屬於模型本身的能力。
- reply_better：B 有 A 沒有的優點（更白話、更誠實、更正了錯誤）。
material 只在「會改變這個人下一步怎麼做」時為 true。最多 8 條，先寫 material 的。

=== 案例重點 ===
{focus}

=== 對話尾段 ===
{tail}

=== 這個人的一句話 ===
{message}

=== A：當時的原答 ===
{original}

=== B：重播的新答 ===
{reply}
"""


def ask(prompt, timeout=600):
    cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
           "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", READER, "--", prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    text = proc.stdout
    try:
        text = json.loads(text).get("result", "")
    except ValueError:
        pass
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {"error": (text or proc.stderr)[:300]}
    except ValueError:
        return {"error": text[:300]}


def select(rows, args):
    if args.ids:
        key = json.load(io.open(args.ids, encoding="utf-8"))
        want = {(v["model"], v.get("label"), v["case"]) for v in key.values()}
        return [r for r in rows if (r["model"], r.get("label"), r["case"]) in want and r.get("turn") == "ask" and r["depth"] == "standard"]
    return [r for r in rows if r.get("turn") == "ask" and (not args.model or r["model"] == args.model)
            and (not args.label or r.get("label") == args.label) and (not args.depth or r["depth"] == args.depth)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="replay results folder")
    ap.add_argument("--ids", help="a key.json (r01..) naming model/label/case to select")
    ap.add_argument("--model"); ap.add_argument("--label"); ap.add_argument("--depth")
    ap.add_argument("--corpus", default=H.DEFAULT_CORPUS)
    ap.add_argument("--save", default=None, help="jsonl to append to (default <out>/gap_analysis.jsonl)")
    ap.add_argument("--report")
    a = ap.parse_args()
    if a.report:
        rows = [json.loads(l) for l in io.open(a.report, encoding="utf-8") if l.strip()]
        by = collections.defaultdict(lambda: collections.Counter()); mat = collections.defaultdict(lambda: collections.Counter()); n = collections.Counter()
        fixes = collections.defaultdict(list)
        for r in rows:
            k = "%s %s" % (r["model"], r.get("label")); n[k] += 1
            for g in (r.get("analysis") or {}).get("gaps") or []:
                by[k][g.get("category")] += 1
                if g.get("material"): mat[k][g.get("category")] += 1
                if g.get("category") in ("missing_work", "missing_knowledge") and g.get("harness_fix") and g["harness_fix"] != "none":
                    fixes[k].append(g["harness_fix"][:120])
        cats = ["missing_work", "missing_knowledge", "missing_context", "judgement", "reply_better"]
        print("| model / arm | replies | " + " | ".join(cats) + " | material gaps per reply |")
        print("|---|---|" + "---|" * len(cats) + "---|")
        for k in sorted(n):
            tot_m = sum(v for c, v in mat[k].items() if c != "reply_better")
            print("| %s | %d | %s | %.1f |" % (k, n[k], " | ".join("%d (%d mat.)" % (by[k][c], mat[k][c]) for c in cats), tot_m / n[k]))
        print("\nHarness-fixable items named most often:")
        allf = collections.Counter(f for k in fixes for f in fixes[k])
        for f, c in allf.most_common(15): print("  %dx %s" % (c, f))
        return 0
    rows = [r for r in H.load_rows_merged(a.out) if not H.row_failed(r) and (r.get("answer") or {}).get("reply")]
    picked = select(rows, a)
    save = a.save or os.path.join(a.out, "gap_analysis.jsonl")
    done = set()
    if os.path.exists(save):
        for l in io.open(save, encoding="utf-8"):
            if l.strip(): d = json.loads(l); done.add(d["key"])
    corpus = os.path.abspath(a.corpus)
    for r in picked:
        key = H.row_key(r)
        if key in done: continue
        try:
            history, message, original, reaction = H.split_case(H.parse_case(os.path.join(corpus, "cases", r["case"] + ".md")), "ask")
        except Exception as exc:  # noqa: BLE001
            print("skip %s: %s" % (key, exc)); continue
        tail = "\n\n".join(("[使用者]\n%s" if role == "user" else "[助理]\n%s") % t[-1500:] for role, t in history[-3:])
        prompt = PROMPT
        for k, v in (("{focus}", r.get("focus") or ""), ("{tail}", tail), ("{message}", message), ("{original}", original[:6000]), ("{reply}", r["answer"]["reply"][:6000])):
            prompt = prompt.replace(k, v)
        res = ask(prompt)
        with io.open(save, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": key, "case": r["case"], "model": r["model"], "label": r.get("label"), "analysis": res}, ensure_ascii=False) + "\n")
        gaps = (res.get("gaps") or []) if isinstance(res, dict) else []
        print("%s: %d gaps (%d material) | %s" % (key, len(gaps), sum(1 for g in gaps if g.get("material")), (res.get("summary") or res.get("error") or "")[:100]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
