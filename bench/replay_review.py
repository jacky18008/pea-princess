#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checkpoint review: an Opus reviewer reads one configuration's replay rows and says what the harness
could change — not the model.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

The replay (bench/history_replay.py) judges each new answer against the person's real reaction. This
script takes every row of one configuration (agent, model, depth, turn, label), packs the judge's
verdicts, issues and the answers themselves into one prompt, and asks a strong model for:
recurring problems with case ids; for each, whether a harness change can fix it (skill text, a
script check, an output contract, a checkpoint) and the exact edit; what to measure afterwards.
The output is a JSON verdict and a Markdown note under <out>/reviews/. Nothing here changes the
skill: the author reads the note and decides.

    python3 bench/replay_review.py --out bench/private/history-replay-2026-09-11 --model claude-sonnet-5 --depth standard --turn ask
    python3 bench/replay_review.py --out ... --model claude-sonnet-5 --depth standard --turn ask --label variant-a

Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import link_probe as LP  # noqa: E402

REVIEWER = "claude-opus-5"

PROMPT = """你是產品的評閱者。一位倫敦找房的使用者，2026 年 8–9 月和一個用強模型的助理對話；我們現在把他當時的訊息重播給「裝了同一套技能、但用較弱模型」的助理，並由評審依他當時的真實反應打分。目標不是換模型，是改「harness」：技能文字、腳本檢查、輸出合約、檢查點，讓弱模型逼近當時的品質。

下面是同一組設定的全部案例：每案有案例重點、使用者訊息（節錄）、新答（節錄）、評審分數與問題。請只根據這些材料回答，不要編造案例裡沒有的內容。

回傳 JSON（不要別的文字）：
{"patterns": [{"name": "一句話", "cases": ["case-02", ...], "why_it_hurts": "一句話", "harness_fix": {"where": "skill text | script | output contract | checkpoint | none", "edit": "具體要改成什麼，可直接寫進檔案的句子或規則", "expected_effect": "會改變哪個分數"}}],
 "keep": ["新答做得好、不要動的地方，最多三條"],
 "measure_next": ["改完後要怎麼量，最多三條"],
 "one_line": "一句話總評"}

規則：
- 最多五個 pattern，按影響大小排。每個都要附案例編號。
- 「沒出處的數字」「算錯」「代號」「沒 recap」「只問不做」「承諾了沒交付」「假裝讀了頁面」這幾類若出現，優先列。
- harness_fix 要具體到可以貼進檔案；改不了的就寫 none 並說為什麼（例如需要更強的模型）。

=== 設定 ===
{config}

=== 案例 ===
{cases}
"""


def load_rows(out_dir, model, depth, turn, label):
    rows = []
    with io.open(os.path.join(out_dir, "rows.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("model") == model and r.get("depth") == depth and r.get("turn", "ask") == turn and (label is None or r.get("label") == label):
                rows.append(r)
    return rows


def pack(rows, per_case=2200):
    parts = []
    for r in sorted(rows, key=lambda x: x["case"]):
        v = (r.get("judge") or {}).get("verdict") or {}
        ans = (r["answer"].get("reply") or "")[:per_case]
        parts.append("### %s — %s\n分數：task=%s quality=%s satisfy=%s vs_history=%s invented_numbers=%s questions=%s\n問題：%s\n評語：%s\n新答（節錄）：\n%s\n" % (
            r["case"], r.get("focus") or "", v.get("task"), v.get("quality"), v.get("satisfy"), v.get("vs_history"),
            v.get("invented_numbers"), v.get("questions_asked"), "；".join(v.get("issues") or []), v.get("one_line") or "", ans))
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--depth", default="standard")
    ap.add_argument("--turn", default="ask")
    ap.add_argument("--label", default=None)
    ap.add_argument("--reviewer", default=REVIEWER)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    rows = load_rows(args.out, args.model, args.depth, args.turn, args.label)
    if not rows:
        sys.stderr.write("no rows for that configuration\n")
        return 1
    config = "model=%s depth=%s turn=%s label=%s cases=%d" % (args.model, args.depth, args.turn, args.label, len(rows))
    prompt = PROMPT.replace("{config}", config).replace("{cases}", pack(rows))
    cmd = ["claude", "-p", "--output-format", "json", "--tools", "", "--allowedTools", "", "--disable-slash-commands",
           "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--model", args.reviewer, "--", prompt]
    stdout, stderr, code = LP._launch(cmd, os.getcwd(), dict(os.environ), args.timeout)
    text, usage = stdout, {}
    try:
        env = json.loads(stdout)
        text = env.get("result") or ""
        usage = env.get("usage") or {}
        usage["cost_usd"] = env.get("total_cost_usd")
    except ValueError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    verdict = json.loads(m.group(0)) if m else None
    folder = os.path.join(args.out, "reviews")
    os.makedirs(folder, exist_ok=True)
    stem = "%s-%s-%s-%s" % (args.model, args.depth, args.turn, args.label or "all")
    with io.open(os.path.join(folder, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"config": config, "reviewer": args.reviewer, "at": datetime.datetime.utcnow().isoformat() + "Z",
                   "verdict": verdict, "raw": text[:6000], "usage": usage, "exit": code}, fh, ensure_ascii=False, indent=1)
    md = ["# Checkpoint review — %s" % config, "", "Reviewer: %s · %s" % (args.reviewer, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")), ""]
    if verdict:
        md.append("**%s**" % (verdict.get("one_line") or ""))
        md.append("")
        for i, p in enumerate(verdict.get("patterns") or [], 1):
            fix = p.get("harness_fix") or {}
            md.append("%d. **%s** — cases %s. %s" % (i, p.get("name"), ", ".join(p.get("cases") or []), p.get("why_it_hurts") or ""))
            md.append("   - fix (%s): %s" % (fix.get("where"), fix.get("edit")))
            md.append("   - expect: %s" % fix.get("expected_effect"))
        if verdict.get("keep"):
            md.append("")
            md.append("Keep: " + " · ".join(verdict["keep"]))
        if verdict.get("measure_next"):
            md.append("")
            md.append("Measure next: " + " · ".join(verdict["measure_next"]))
    else:
        md.append("(reviewer returned no JSON; see the .json raw field)")
    with io.open(os.path.join(folder, stem + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
