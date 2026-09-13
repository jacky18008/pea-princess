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
            no source, web citation, formula or "you said": mark it as an estimate with its basis,
            cite the register or page, or take it out. Dates and clock times are skipped.
  jargon    circled numbers (信⑲), single-letter evidence marks (G/S/C/I/U as labels), landmine
            and route codes (L4, D3), backticked identifiers, file names, skill names, internal
            words (evidence class, fixed form, budget mode, landmine, money-gate, lite/standard/deep
            as labels): say the plain thing instead.
  script    simplified Chinese characters inside a reply written in traditional Chinese.
  asking    more than three question marks; or any question when the person's last message was a
            go-ahead (Go / gp / 都同意 / 繼續 / 照做 / continue / go ahead): execute and report.
  opening   the first sentence is praise or agreement (問得好, 你說得對, great question): open with
            the answer instead.
  paths     a machine path or file URL in the body (/var/folders, /private/var, /tmp, file://, ~/):
            the person cannot open it; say what the file contains instead.
  address   the person is called "使用者" / "the user" in the body: say 你 / you.
  terms     a board code (HOLD, CONDITIONAL, EDGE, NO-GO) or a planning/tenancy acronym (CEMP, CMP,
            CLP, AQDMP, PRS, BTR, HMO, AST, EICR, TDS, DPS) with no plain explanation in the same
            sentence: explain it once, in the person's language.
  claims    "已驗證 / 已核對 / 已合併 / verified / confirmed" with nothing verifiable beside it
            (no figure, quote, colon or name): say what was checked and what it showed.
  authority a sentence that states a necessity or an exclusion (必須, 只有…才, 排除, 底線, must, only if,
            rule out) with neither the person's words (你說, 你的條件, you said) nor a proposal marker
            (我建議, 值得, 如果你, I suggest, worth): a condition is the person's only when you can
            quote them; everything else is your suggestion and is written as one. Added 2026-09-13
            after Codex's Terra runs turned "偏好安靜" into "只有…才值得".
            Explicitly negated claims are skipped; a URL alone is not a verification result.
The 2026-09-11 checkpoint reviews of Opus and Codex terra on the same fifteen cases added the last
four kinds (local paths, third person, unexplained codes, empty claims).
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
                        r"掃描|保存|資料|工具|地圖|紀錄|記錄|查詢|回傳|顯示|模型|噪音圖|規劃|申請|"
                        r"\bper\b|\bfrom\b|\bsource|\bcertificate|\bregister|\baccording|\bestimate|\bapprox|\byou said|\blisting|"
                        r"\bscan|\bsaved|\bdata\b|\bmap\b|\brecord|\bshows|\bmodel)", re.I)
NECESSITY = re.compile(r"(必須|必要條件|硬條件|不能接受|一定要|底線|才值得|才能|才算|才考慮|只有.{0,24}才|排除|不考慮|不予考慮|淘汰|"
                       r"\bmust\b|\bonly if\b|hard (?:requirement|condition|filter)|deal-?breaker|rule[sd]? out|non-negotiable|\bexclude[sd]?\b)", re.I)
USER_CUE = re.compile(r"(你說|你的條件|你要求|你提過|你之前|你定的|你已|你設|你要的|依你|照你|按你|你給的|你原本|你的上限|你的預算|你的排除|"
                      r"\byou said\b|\byou asked\b|\byour (?:rule|condition|requirement|limit|ceiling|budget|deal-?breaker)|\bas you\b|\bper your\b)", re.I)
PROPOSAL_CUE = re.compile(r"(我建議|我會建議|我的建議|建議你|建議先|我認為|我覺得|我的看法|我擔心|我會先|我會把|可以考慮|如果你|要不要|看你|由你|你決定|你可以|"
                          r"\bI suggest|\bI would|\bI'd\b|\bmy (?:advice|view|suggestion)|\bconsider\b|\bif you\b|\bup to you\b|\byou (?:could|might|may)\b)", re.I)
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
PRAISE_OPENER = re.compile(r"^\s*[*_#>\-]*\s*(問得好|問得對|好問題|你說得對|你說的對|你的直覺是對的|說得好|這個問題很好|很好的問題|沒錯|對，|對的|"
                           r"great question|good question|you'?re right|you are right|that'?s a great|excellent question|fair point|absolutely)", re.I)
MACHINE_PATH = re.compile(r"(/private/var/|/var/folders/|/tmp/|file://|(?<![\w.])~/[\w.-]+|/Users/[\w.-]+/)")
THIRD_PERSON = re.compile(r"使用者|\bthe user\b", re.I)
BOARD_CODE = re.compile(r"(?<![A-Za-z-])(HOLD|CONDITIONAL|EDGE|NO-GO|NOGO)(?![A-Za-z-])")
ACRONYM = re.compile(r"(?<![A-Za-z])(CEMP|CMP|CLP|AQDMP|PRS|BTR|HMO|AST|EICR|TDS|DPS|CMP)(?![A-Za-z])")
EXPLAINED = re.compile(r"[（(][^）)]{2,60}[）)]|[：:]|即|也就是|指的是|意思是|means|i\.e\.|that is")
EMPTY_CLAIM = re.compile(r"(已(?:經)?(?:驗證|核對|確認|合併|更新|交代|寫進|寫入|記錄|同步)|\b(?:verified|confirmed|reconciled|merged)\b)", re.I)
CONTENT_CUE = re.compile(r"[：:「」“”\d£%]|→|改前|改後|from .* to ")
WEB_START = re.compile(r"https?://", re.I)
MARKDOWN_WEB_START = re.compile(r"\[[^\]\n]*\]\(\s*<?https?://", re.I)
CLAIM_NEGATION = re.compile(
    r"(?:並非|並不是|不是|尚未|仍未|還未|未曾|沒有|未|不|"
    r"不能(?:視為|當作|說)|不(?:代表|等於)|"
    r"\b(?:not|never)(?:\s+(?:yet|been|independently|fully|necessarily))*|"
    r"\b(?:hasn|haven|isn|aren|wasn|weren)['’]t(?:\s+been)?)\s*$", re.I)
GO_AHEAD = re.compile(r"(?i)\b(go|gp|continue|go ahead|do it|proceed|yes)\b|都同意|同意|繼續|照做|照這樣|去做|開始吧|可以|好，?做|沒問題")
SIMPLIFIED = set("这说们时间对问题见车电东门长结应该认为与从发产权让还进过现经国单号计设层楼费钱价买卖办处务实际总条约签订视听讲话语书录读写点线区块图机关开风气热体验检证据确识质数议论选择优标备参决则规围绕码头脑岁维护积极响")


def _web_spans(text):
    """Locate web citations without fetching them or treating their bytes as evidence."""
    for match in WEB_START.finditer(text):
        end, depth = match.end(), 0
        while end < len(text):
            char = text[end]
            if char.isspace() or char in '<>"\'[]{}「」“”。，！？；':
                break
            if char == '(':
                depth += 1
            elif char == ')':
                if not depth:
                    break
                depth -= 1
            end += 1
        # Bare URLs commonly end a sentence; its punctuation is not part of the link.
        while end > match.end() and text[end - 1] in '.,!?;:':
            end -= 1
        if end > match.end():
            yield match.start(), end


def _sentences(text):
    """Preserve decimal amounts, web URLs and inline-link labels when splitting prose."""
    protected = bytearray(len(text))
    for start, end in _web_spans(text):
        protected[start:end] = b'\1' * (end - start)
    for match in MARKDOWN_WEB_START.finditer(text):
        protected[match.start():match.end()] = b'\1' * (match.end() - match.start())
    start = 0
    for match in re.finditer(r"[。.!?！？\n]", text):
        pos = match.start()
        decimal = text[pos] == '.' and pos > 0 and pos + 1 < len(text) and text[pos - 1].isdigit() and text[pos + 1].isdigit()
        if not protected[pos] and not decimal:
            yield text[start:pos + 1]
            start = pos + 1
    if start < len(text):
        yield text[start:]


def _without_web_urls(text):
    # A URL's colon or numeric path is not a stated verification result or rent figure.
    chars = list(text)
    for start, end in _web_spans(text):
        chars[start:end] = ' ' * (end - start)
    return ''.join(chars)


def scan(text, previous=None):
    findings = []
    for sent in _sentences(text or ""):
        cleaned = DATE_LIKE.sub(" ", _without_web_urls(sent))
        nums = NUMBER.findall(cleaned)
        if nums and not SOURCE_CUE.search(cleaned) and not any(_web_spans(sent)):
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
    first = (text or "").strip()
    if PRAISE_OPENER.search(first):
        findings.append({"kind": "opening", "fragment": first[:60], "say": "開頭是稱讚或附和；第一句要直接給答案、洞見或取捨。"})
    for m in MACHINE_PATH.finditer(text or ""):
        findings.append({"kind": "paths", "fragment": text[max(0, m.start() - 10):m.end() + 30].strip(), "say": "機器路徑或檔案網址，使用者打不開；寫出檔案裡有什麼。"})
    body_has_chinese = len(re.findall(r"[一-鿿]", text or "")) > 20
    for m in THIRD_PERSON.finditer(text or ""):
        if body_has_chinese or m.group(0).lower() == "the user":
            findings.append({"kind": "address", "fragment": text[max(0, m.start() - 12):m.end() + 12].strip(), "say": "正文用第三人稱叫對方；改成「你」。"})
            break
    for sent in _sentences(text or ""):
        content = _without_web_urls(sent)
        codes = BOARD_CODE.findall(content) + ACRONYM.findall(content)
        explanation = re.sub(r"[（(]\s*[）)]", "", content)
        if codes and not EXPLAINED.search(explanation):
            findings.append({"kind": "terms", "fragment": sent.strip()[:120], "say": "代號或縮寫沒解釋：%s。同一句用白話說它是什麼。" % "、".join(sorted(set(codes)))})
        affirmative = any(not CLAIM_NEGATION.search(content[:match.start()]) for match in EMPTY_CLAIM.finditer(content))
        if affirmative and not CONTENT_CUE.search(content):
            findings.append({"kind": "claims", "fragment": sent.strip()[:120], "say": "說已經驗證／合併／更新，卻沒附內容；寫出查了什麼、結果是什麼。"})
    for sent in re.split(r"(?<=[。.!?！？\n])", text or ""):
        if NECESSITY.search(sent) and not USER_CUE.search(sent) and not PROPOSAL_CUE.search(sent):
            findings.append({"kind": "authority", "fragment": sent.strip()[:140],
                             "say": "這句把一個條件寫成定案（必須／只有…才／排除）。能引使用者原話就加「你說…」；不能就是你的建議，改寫成「我建議先確認…」，並放進提議欄，不改使用者的條件。"})
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
