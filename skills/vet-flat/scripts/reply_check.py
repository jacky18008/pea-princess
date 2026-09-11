#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check a draft reply before it is sent: numbers without a source, jargon, simplified characters,
too many questions, and a question after the person already said "go".

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Not a network tool. The assistant writes its draft to a file (or pipes it), runs this, fixes what it
lists, and only then sends. Findings are plain sentences with the offending fragment quoted; the
exit code is 1 when anything was found, so a host can gate on it.

    reply_check.py draft.md
    reply_check.py draft.md --previous "都同意，Go"          # the person's last message, for the go-ahead rule
    cat draft.md | reply_check.py - --json

What it checks (2026-09-11, from the replay review of fifteen real cases):
  numbers   a money amount, percentage, duration, count, distance or area whose sentence carries
            no source, no formula and no "you said": mark it as an estimate with its basis, cite
            the register or page, or take it out. Dates and clock times are skipped.
  jargon    circled numbers (信⑲), single-letter evidence marks (G/S/C/I/U as labels), landmine
            and route codes (L4, D3), backticked identifiers, file names, skill names, internal
            words (evidence class, fixed form, budget mode, landmine, money-gate, lite/standard/deep
            as labels): say the plain thing instead.
  script    simplified Chinese characters inside a reply written in traditional Chinese.
  asking    more than three question marks; or any question when the person's last message was a
            go-ahead (Go / gp / 都同意 / 繼續 / 照做 / continue / go ahead): execute and report.
Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import re
import sys

SOURCE_CUE = re.compile(r"(來源|依據|根據|出處|法規|規定|上限|法律|條例|Act|EPC|能源證書|證書|警方|police|TfL|官方|統計|ONS|登記|Companies House|"
                        r"◆|■|●|▲|使用者|你說|你給|你提供|你的|算式|公式|÷|×|=|約|估|大概|大約|左右|範圍|區間|依|按|引用|查到|查得|寫著|寫有|刊登|廣告|"
                        r"\bper\b|\bfrom\b|\bsource|\bcertificate|\bregister|\baccording|\bestimate|\bapprox|\byou said|\blisting)", re.I)
NUMBER = re.compile(r"(£\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:%|分鐘|分|週|周|個月|月|年|m²|平方公尺|sq ?ft|平方呎|平方英尺|坪|英鎊|鎊|件|戶|棟|間|公尺|米|km|公里|k\b|萬))")
DATE_LIKE = re.compile(r"\b(19|20)\d{2}[-/年.]\d{1,2}([-/月.]\d{1,2})?|\d{1,2}[/月]\d{1,2}[日號]?|\d{1,2}:\d{2}|\b(19|20)\d{2}\s?年")
CIRCLED = re.compile(r"[①-⑳⓪-⓿㉑-㉟]")
EVIDENCE_MARK = re.compile(r"(?<![A-Za-z])([GSCIU])(?![A-Za-z])\s*[:：）)]|[（(]\s*([GSCIU])\s*[)）]|\b(evidence class|evidence_class)\b", re.I)
CODES = re.compile(r"(?<![A-Za-z])([LD]\d{1,2})(?![A-Za-z\d])|\bF\d{1,2}\b")
BACKTICK = re.compile(r"`[^`\n]{1,60}`")
FILENAME = re.compile(r"\b[\w\-]+\.(?:py|yaml|yml|md|json|html)\b")
SKILL_NAMES = re.compile(r"\b(vet-flat|pea-princess|vet_flat)\b", re.I)
INTERNAL = re.compile(r"(fixed form|budget mode|money-gate|money gate|landmine|\blite\b|\bstandard\b|\bdeep\b|殺手項|固定表單|預算模式|地雷碼|證據等級)", re.I)
QUESTION = re.compile(r"[?？]")
GO_AHEAD = re.compile(r"(?i)\b(go|gp|continue|go ahead|do it|proceed|yes)\b|都同意|同意|繼續|照做|照這樣|去做|開始吧|可以|好，?做|沒問題")
SIMPLIFIED = set("这说们时间对问题见车电东门长结应该认为与从发产权让还进过现经国单号计设层楼费钱价买卖办处务实际总条约签订视听讲话语书录读写点线区块图机关开风气热体验检证据确识质数议论选择优标备参决则规围绕码头脑岁维护积极响")


def scan(text, previous=None):
    findings = []
    for sent in re.split(r"(?<=[。.!?！？\n])", text or ""):
        cleaned = DATE_LIKE.sub(" ", sent)
        nums = NUMBER.findall(cleaned)
        if nums and not SOURCE_CUE.search(cleaned):
            findings.append({"kind": "numbers", "fragment": sent.strip()[:160],
                             "say": "這句有數字但沒有出處、算式或「你說的」：%s。標「估」並給依據、引用登記冊或頁面，或拿掉。" % "、".join(n.strip() for n in nums[:4])})
    for m in CIRCLED.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": text[max(0, m.start() - 12):m.end() + 12].strip(), "say": "圈號代號，改成那件事的白話全名。"})
    for m in EVIDENCE_MARK.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": text[max(0, m.start() - 20):m.end() + 6].strip(), "say": "單字母證據標記或 evidence class，改成「官方登記」「刊登自述」「第三方」「推估」「未知」。"})
    for m in CODES.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": text[max(0, m.start() - 16):m.end() + 16].strip(), "say": "內部編號，改成它代表的那件事。"})
    for m in BACKTICK.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": m.group(0), "say": "反引號包的識別字，使用者不需要看到；用白話。"})
    for m in FILENAME.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": m.group(0), "say": "檔名不該出現在給使用者的正文。"})
    for m in SKILL_NAMES.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": m.group(0), "say": "技能名稱不該出現在正文。"})
    for m in INTERNAL.finditer(text or ""):
        findings.append({"kind": "jargon", "fragment": text[max(0, m.start() - 16):m.end() + 16].strip(), "say": "內部說法，改成使用者自己會說的詞。"})
    trad = len(re.findall(r"[一-鿿]", text or ""))
    simp = [c for c in (text or "") if c in SIMPLIFIED]
    if trad > 40 and simp:
        findings.append({"kind": "script", "fragment": "".join(sorted(set(simp)))[:40], "say": "繁體回覆裡混了簡體字：%d 個。" % len(simp)})
    q = len(QUESTION.findall(text or ""))
    if q > 3:
        findings.append({"kind": "asking", "fragment": "%d 個問號" % q, "say": "問題超過三個；留下會改變下一步的那幾個，其餘用預設。"})
    if previous and GO_AHEAD.search(previous) and q:
        findings.append({"kind": "asking", "fragment": previous.strip()[:80], "say": "使用者上一則已經放行，這一則不該再問；執行上一輪提議的事，回報結果。"})
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", help="file with the draft reply, or - for stdin")
    ap.add_argument("--previous", default=None, help="the person's last message (for the go-ahead rule)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = sys.stdin.read() if args.draft == "-" else io.open(args.draft, encoding="utf-8").read()
    findings = scan(text, args.previous)
    counts = {}
    for f in findings:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    if args.json:
        print(json.dumps({"ok": not findings, "counts": counts, "findings": findings}, ensure_ascii=False, indent=1))
    else:
        if not findings:
            print("reply_check: clean")
        for f in findings:
            print("- [%s] %s\n    ↳ %s" % (f["kind"], f["fragment"], f["say"]))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
