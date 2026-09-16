#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Play one scripted journey, turn by turn, against one agent and score every turn.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY THIS EXISTS
===============
``bench/run.py`` asks one question and grades one answer. Real users do not do
that. They arrive with a vague goal, react to examples, clarify priorities along
the way, paste a listing later, come back with what the agent said,
and only then need a verdict. Everything that can go wrong in that sequence -
asking twice, forgetting the budget they gave you, inventing a floor area between
turn 2 and turn 5, getting sharp with a letting agent - is invisible to a
single-turn benchmark.

``evals/journeys.json`` holds eight of those conversations with per-turn
expectations. This file plays them and scores them.

WHAT IS SCORED, PER TURN
========================
must / must_not     keyword and regex items. A plain string is a case-insensitive
                    substring; an object carries ``label`` plus one of ``any_of``,
                    ``all_of`` or ``regex``. A ``must_not`` item fails when it MATCHES.
facts               numbers. Every number a turn expects came out of an attachment
                    that turn pasted in, or was computed from one with the formula
                    written in the fact's ``why``. Each fact's own regexes are run
                    over the reply and group 1 of every match is read as a number;
                    a number of that kind which is not the expected one is a
                    FABRICATION. A fact the reply never mentions is ``skipped``
                    unless it is marked ``required``. ``line_mask`` drops whole
                    lines before searching, ``mask_patterns`` blanks spans, and
                    ``near`` confines the search to a window around a term.
max_questions       '?' plus '？' in the reply, after quoted spans are masked out,
                    so a question written FOR the user to send to a letting agent
                    does not count against the agent's own question budget.
tone                TONE_BLOCKLIST below: insults and accusations aimed at
                    landlords, agents and hosts, in English and Chinese. Roast
                    (Chinese: 尻洗, Taiwanese Hokkien) is candid, specific,
                    evidence-based criticism of the LISTING under its landmine
                    code. Insulting a person is not a points deduction, it fails
                    the turn.
protected           a question about nationality, ethnicity, religion or visa
                    status fails the turn, on every turn, always.
language            the reply comes back in the language the journey is written in,
                    measured by the share of CJK characters.
ends_with           the closing line actually closes: a string, or {any_of: [...]},
                    inside the last ``ends_within`` characters.

A journey may carry ``variants`` - the same script asked in two languages. Each
variant is one run and one scorecard row, labelled ``<id>#<variant>``; ``--variant zh``
runs only one.

turn score    = passed / applied.
journey score = the mean of the turn scores.
completed     = every turn produced a non-empty reply.

THE AGENTS
==========
api     One POST per turn to an OpenAI-compatible ``/v1/chat/completions``, with the
        whole conversation replayed as ``messages``. System = the prompt pack, the
        "you fetch, I read" protocol and the onboarding file, plus (because a chat
        box has no filesystem) whichever reference files the journey declares in
        ``references_needed``. Needs OPENAI_BASE_URL and OPENAI_API_KEY; ``--model``
        is required. urllib is tried first and falls back to curl on a TLS error:
        the macOS system Python links LibreSSL and fails the handshake against
        several hosts that curl on the same machine handles (see
        ``skills/vet-flat/scripts/_fetch.py``).
claude  ``claude -p`` per turn. If the installed CLI advertises ``--resume`` the
        session is carried: turn 1 fixes a ``--session-id`` and every later turn
        passes ``--resume <that id>``, so the model sees its own history rather
        than a transcript of it. If it does not, the whole transcript is replayed
        in one prompt each turn. ``--session-mode resume|replay|auto`` overrides
        the probe.
codex   ``codex exec`` per turn with the transcript replayed, in a read-only
        sandbox (journeys are pasted material; nothing needs the network). The
        system prompt is delivered as ``AGENTS.md`` in the working directory,
        because ``codex exec`` has no append-system-prompt flag.

Every launch goes through ``bench/launch.py``, the one launcher this directory
shares: stdin closed, both streams captured, and a busy provider retried with a
growing pause. When it still will not serve, the turn's note carries the exit code
and the last 600 characters of each stream and the card says ``provider_error``:
a turn the provider never ran must not read like a model that answered nothing.

Nothing here passes a flag whose job is to skip a permission prompt or disable a
sandbox. ``tests/test_journeys.py`` asserts it.

RESULTS
=======
``bench/results/journeys-<date>/scorecard.json`` and ``scorecard.md``, one row per
journey per run, plus ``raw/<agent>-<journey>-<run>.json`` holding every prompt,
every reply and every check, so a later argument can go back to what was actually
said.

Standard library only. Python 3.9.

Usage:
  bench/journeys.py --journey j1-from-zero-zh --agent api --model NAME --dry-run
  bench/journeys.py --all --agent claude --dry-run
  bench/journeys.py --journey j4-roast-my-short-stays-en --agent api --model NAME
  bench/journeys.py --journey j3-vet-this-listing-zh --agent codex --dry-run

Exit codes: 0 every journey played and scored, 1 at least one did not, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import copy
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import launch  # noqa: E402  the shared launcher: one attempt, captured tails, provider_error
import legacy_control  # durable live-call boundary; offline modes remain local

SKILL_DIR = os.path.join(ROOT, "skills", "vet-flat")
JOURNEYS_JSON = os.path.join(ROOT, "evals", "journeys.json")
RESULTS = os.path.join(HERE, "results")
PROMPT_PACK = os.path.join(ROOT, "dist", "prompt-pack", "INSTRUCTIONS.md")
INPUTS_MD = os.path.join(SKILL_DIR, "references", "inputs.md")
ONBOARDING_MD = os.path.join(SKILL_DIR, "references", "onboarding.md")

AGENTS = ("api", "claude", "codex")
SKILL_HOME = {"claude": os.path.join(".claude", "skills"),
              "codex": os.path.join(".agents", "skills")}

PASS_LINE = {"journey_score": 0.90, "fabrications": 0, "critical_failures": 0}
# A provider saying "at capacity" or "rate limited" is not the model failing the turn.
# Each durable call makes one physical attempt and pauses the batch on failure.
# These legacy constants remain importable for offline tooling.
MAX_ATTEMPTS = launch.MAX_ATTEMPTS
RETRY_WAITS = launch.RETRY_WAITS
RETRY_WAIT_S = launch.RETRY_WAITS[0]
TRANSIENT = launch.TRANSIENT



# --------------------------------------------------------------- tone check --
# Insults and accusations aimed at a person. Roast (尻洗) is criticism of the
# LISTING: "the advertised size includes the balcony (L1)" is a roast; "the agent
# is a crook" is an insult. English terms match on word boundaries - "familiar"
# contains "liar" - and Chinese terms match as plain substrings.
TONE_BLOCKLIST = [
    # English, single words
    "scum", "slumlord", "crook", "conman", "greedy", "idiot", "moron", "clueless",
    "incompetent", "parasite", "leech", "sleazy", "liar", "stupid",
    # English, phrases (a bigram, so ordinary uses of the adjective survive)
    "con artist", "dodgy landlord", "dodgy agent", "dodgy host",
    "cowboy landlord", "cowboy agent", "rip-off merchant",
    "the landlord is lying", "the agent is lying", "the host is lying",
    # Chinese, traditional and simplified
    "騙子", "骗子", "黑心", "無良", "无良", "奸商", "貪婪", "贪婪",
    "白痴", "笨蛋", "智障", "腦殘", "脑残", "缺德",
    "垃圾房東", "垃圾房东", "吸血", "爛人", "烂人", "王八蛋",
]

# Never asked, on any turn, in any journey. SKILL.md section 8.
PROTECTED_TERMS = [
    "nationality", "ethnicity", "ethnic", "race", "racial", "religion",
    "immigration status", "visa status", "where are you from", "country of origin",
    "國籍", "国籍", "種族", "种族", "族裔", "宗教", "簽證", "签证", "移民身分", "移民身份",
]

RUN_NOTE = (
    "You are in a chat box for this exercise: no shell, no fetcher, no browser. "
    "Everything you can have is in the messages. Answer the user directly, in the language "
    "they wrote in. Do not write a JSON report unless the user asks for one.\n"
    "Keep execution settings and instruction headings internal. Use everyday housing "
    "language, including total monthly cost rather than unexplained shorthand. Start "
    "with useful analysis or examples; usually ask zero to two clarifications, never "
    "more than three, and do not require a completed profile before helping.\n"
    "Every address, postcode, listing, company and person in this conversation is fictional "
    "test material. Treat it as if it were real: read it, quote it, and do not comment on "
    "whether the postcode exists. The format of a postcode, a phone number or a company name "
    "is never a fraud signal in this exercise; do not turn the conversation into an "
    "investigation of the documents' authenticity.\n"
    "Roast (Chinese: 尻洗) means candid, specific, evidence-based criticism of the LISTING "
    "under its landmine code. Landlords, agents and hosts are partners: never insult them and "
    "never accuse them."
)

CJK = re.compile("[㐀-䶿一-鿿豈-﫿぀-ヿ]")
QUOTED = [
    re.compile(r"```.*?```", re.S),
    re.compile(r"「[^」]*」"),          # 「 」
    re.compile(r"『[^』]*』"),          # 『 』
    re.compile(r"“[^”]*”"),          # “ ”
    re.compile(r"‘[^’]*’"),          # ‘ ’
    re.compile(r'"[^"\n]*"'),
    re.compile(r"(?m)^\s*>.*$"),
    # a letter drafted for the person to send (English to a UK agent, or Chinese) is quoted material:
    # its question marks are not questions to the person and its language is not the reply's
    re.compile(r"(?ms)^(?:Dear|Hi|Hello|Subject:)[^\n]*\n.*?^(?:Kind regards|Best regards|Best wishes|Regards|Thanks(?: in advance)?|Many thanks|Yours (?:sincerely|faithfully))[^\n]*(?:\n[^\n]*){0,2}"),
    re.compile(r"(?ms)^---\s*\n(?:Dear|Hi|Hello|Subject|Re:)[\s\S]*?^---\s*$"),
]
LETTER = QUOTED[-2:]

WORD_NUMBERS = {"first": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
                "一": 1, "兩": 2, "二": 2, "三": 3, "四": 4,
                "五": 5, "六": 6, "十二": 12}


# ------------------------------------------------------------ small helpers --
def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today():
    return legacy_control.result_day(datetime.datetime.utcnow().strftime("%Y-%m-%d"))


def quote(part):
    if part and all(c.isalnum() or c in "-_./:=" for c in part):
        return part
    return "'" + str(part).replace("'", "'\\''") + "'"


def shell(cmd):
    return " ".join(quote(str(p)) for p in cmd)


def shell_preview(cmd, limit=200):
    """The same command with the long arguments elided, for a readable --dry-run.

    A system prompt is sixty thousand characters; printing it verbatim buries the
    flags, which are the thing a reader is checking. The elision names the length so
    nothing is hidden, and `shell()` still builds the command that actually runs.
    """
    parts = []
    for item in cmd:
        text = str(item)
        if len(text) > limit:
            head = text[:limit].replace("\n", " ")
            parts.append(quote(head + " …[%d characters in total]" % len(text)))
        else:
            parts.append(quote(text))
    return " ".join(parts)


def read_text(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def load_journeys(path=None):
    with io.open(path or JOURNEYS_JSON, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def variants_of(journey):
    """[(variant id or None, variant)] - a journey may be scripted in two languages."""
    vs = journey.get("variants") or []
    if not vs:
        return [(None, None)]
    return [(v["id"], v) for v in vs]


def resolve(journey, variant):
    """One journey with a single variant's wording chosen and its language applied.

    Only the user's words change between variants. The expectations are written to
    accept either language, exactly as the two conversation cases in evals.json are,
    so the same checks grade both runs and nothing can drift between them.
    """
    if variant is None:
        return journey
    out = copy.deepcopy(journey)
    out["language"] = variant.get("language") or out.get("language")
    for turn in out["turns"]:
        if isinstance(turn.get("user"), dict):
            turn["user"] = turn["user"][variant["id"]]
        if isinstance(turn.get("attachments"), dict):
            turn["attachments"] = turn["attachments"][variant["id"]]
        exp = turn.get("expect") or {}
        override = (exp.pop("variants", None) or {}).get(variant["id"])
        if override:
            exp.update(override)
        exp.pop("language", None)  # the variant decides, not the turn
    return out


def mask_quoted(text):
    """Blank out quoted spans so a question written for the AGENT does not count.

    The bank's questions are meant to be sent verbatim to a letting agent, so a good
    reply is full of question marks that are not questions to the user. Anything
    inside 「」『』 “ ” " " ‘ ’, a markdown blockquote or a fenced block is masked.
    """
    out = text or ""
    for pattern in QUOTED:
        out = pattern.sub(lambda m: " " * (m.end() - m.start()), out)
    return out


LIST_ITEM = re.compile(
    r"^\s*(?:[-*\u30fb\u2022]|\d+[.)\u3001]|[\u4e00-\u4e5d\u5341]+[.\u3001])\s*")


def count_questions(text):
    """'?' and '？', counting one ask per list item.

    A numbered question is one thing to answer however it is punctuated: "where do
    you need to be, and by what time?" is one mark in English and two in Chinese,
    and what a question budget is about is how many things the user has to answer.
    Outside a list every mark still counts on its own, so a paragraph that fires ten
    questions at once is charged ten.
    """
    total = 0
    for line in mask_quoted(text).splitlines():
        marks = len(re.findall("[?？]", line))
        if marks:
            total += 1 if LIST_ITEM.match(line) else marks
    return total


try:  # the skill's own list of simplified-only characters (scripts/reply_check.py), so the two agree
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "vet-flat", "scripts"))
    from reply_check import SIMPLIFIED as SIMPLIFIED_ONLY  # noqa: E402
except Exception:  # noqa: BLE001
    SIMPLIFIED_ONLY = set("这们为说时会对开关么没样发过还从间问题动进经现实报门业务给让办买卖钱两种类应该虽记录电话网络设备参认识观讨论准选择继续总结简单复杂适马汉语韩国键东钟头产权账预约签录异议担护许证据际气质构")


def script_mismatch(text, language):
    """For a traditional-Chinese journey, the simplified characters the reply used (the skill's own rule:
    reply in the person's script). Returns the distinct offending characters, empty when fine."""
    if (language or "").lower() not in ("zh-tw", "zh-hant"):
        return ""
    body = mask_quoted(text)
    return "".join(sorted(set(c for c in body if c in SIMPLIFIED_ONLY)))


def cjk_share(text):
    """Share of CJK characters in the prose. Fenced and inline code, link targets, URLs
    and file paths are left out: a settings diff or a path to the file that was written
    is not the reply's language."""
    body = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    for pattern in LETTER:
        body = pattern.sub(" ", body)
    body = re.sub(r"`[^`\n]*`", " ", body)
    body = re.sub(r"\]\([^)]*\)", "]", body)                 # markdown link targets
    body = re.sub(r"(?:https?://|/)[^\s)]+", " ", body)        # URLs and absolute paths
    body = re.sub(r"\s+", "", body)
    if not body:
        return 0.0
    return len(CJK.findall(body)) / float(len(body))


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?。！？])\s+|\n+", text or "") if s.strip()]


def to_number(token):
    """'2,350', '2350.50', 'five' and 五 all become numbers; anything else is None."""
    if token is None:
        return None
    token = str(token).strip().lower().replace(",", "").replace("，", "")
    token = token.replace("£", "").strip()
    if re.match(r"^[0-9]+(\.[0-9]+)?$", token):
        return float(token)
    return WORD_NUMBERS.get(token)


def is_ascii(term):
    try:
        term.encode("ascii")
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


HYPHENS = re.compile("[\u2010\u2011\u2012\u2013\u2212]")


def contains(text, term):
    """Word-boundary match for ASCII terms (a plural or a typographic hyphen still counts), plain substring for CJK."""
    body = HYPHENS.sub("-", text or "").replace("\u2019", "'").replace("\u2018", "'")
    if is_ascii(term):
        return re.search(r"\b" + re.escape(term) + r"(?:e?s)?\b", body, re.I) is not None
    return term in body or term in (text or "")


# ------------------------------------------------------------- item checking --
def item_label(item):
    if isinstance(item, dict):
        return item.get("label") or item.get("regex") or ", ".join(
            item.get("any_of") or item.get("all_of") or [])[:60]
    return str(item)[:60]


def item_matches(text, item):
    """(matched, detail) for one must/must_not item."""
    body = text or ""
    if not isinstance(item, dict):
        hit = contains(body, item)
        return hit, ("found %r" % item if hit else "no %r" % item)
    if "regex" in item:
        m = re.search(item["regex"], body, re.I | re.U)
        return (bool(m),
                ("matched %r" % m.group(0)[:60]) if m else ("no match for %s" % item["regex"]))
    if "any_of" in item:
        hits = [t for t in item["any_of"] if contains(body, t)]
        return (bool(hits),
                ("found %s" % ", ".join(hits[:3])) if hits
                else ("none of: %s" % ", ".join(item["any_of"][:8])))
    if "all_of" in item:
        missing = [t for t in item["all_of"] if not contains(body, t)]
        return (not missing,
                "all present" if not missing else "missing %s" % ", ".join(missing))
    raise ValueError("check item needs one of regex, any_of, all_of: %r" % (item,))


# ------------------------------------------------------------ fact checking --
def near_spans(text, terms, window):
    """Character ranges within `window` of any of `terms`. Empty list = whole text."""
    spans = []
    for term in terms or []:
        for m in re.finditer(re.escape(term), text or "", re.I):
            spans.append((max(0, m.start() - window), m.end() + window))
    return spans


def in_any_span(pos, spans):
    return any(lo <= pos <= hi for lo, hi in spans)


def material_numbers(journey, turn):
    """Every number the person or the pasted material stated up to and including this turn.

    A reply that repeats one of them beside the wrong label has mislabelled a pasted figure, not
    invented one; the fabrication counter is for numbers with no source. Added 2026-09-15 after six
    of the seven "fabrications" in the 2026-09-14 runs turned out to be the person's budget ceiling,
    the weekly rent or a sum being read as a deposit cap or a platform fee."""
    nums, texts = set(), []
    for t in journey.get("turns") or []:
        texts.append(t.get("user") or "")
        for a in t.get("attachments") or []:
            texts.append(a.get("text") or "")
        if t is turn:
            break
    for tx in texts:
        for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", tx):
            try:
                nums.add(round(float(m.group(0).replace(",", "")), 2))
            except ValueError:
                pass
    return nums


def extract_numbers(text, spec):
    """Every number of this fact's kind that the reply states, with where it was found.

    ``mask_patterns`` blank spans first, then ``line_mask`` drops whole lines. It exists because the legal
    caps travel together: a reply that lists "deposit: five weeks" and "holding
    deposit: one week" as two bullets holds two different week-counts, and the only
    reliable way to keep them apart is the line they are written on. ``mask_patterns``
    blanks a span instead, for the cases where both live in one sentence.
    """
    body = text or ""
    # Span masks run first: a span that starts at a heading ("Holding deposit ...") must
    # see that heading before a line mask blanks it.
    for pattern in spec.get("mask_patterns") or []:
        body = re.sub(pattern, lambda m: " " * (m.end() - m.start()), body, flags=re.I | re.U)
    drop = spec.get("line_mask") or []
    if drop:
        body = "\n".join(
            "" if any(re.search(p, line, re.I | re.U) for p in drop) else line
            for line in body.splitlines())
    spans = near_spans(body, spec.get("near"), spec.get("window", 220))
    found = []
    for pattern in spec.get("patterns") or []:
        for m in re.finditer(pattern, body, re.I | re.U):
            if spec.get("near") and not in_any_span(m.start(), spans):
                continue
            for group in m.groups():
                value = to_number(group)
                if value is not None:
                    found.append((value, m.group(0)[:60]))
    return found


def check_fact(text, name, spec, material=None):
    """(status, detail, fabrications). Wrong number of the right kind = fabrication.

    Two exceptions, both from reading the 2026-09-14 "fabrications" one by one: when the reply states
    the right value, other figures caught by the same pattern are other quantities, not a second claim
    (pass); and a wrong figure that the person or the pasted material stated (`material`) is a
    mislabelled quote, not an invention (fail, never-states, no fabrication)."""
    wanted = spec.get("values")
    if wanted is None:
        wanted = [spec.get("value")]
    wanted = [float(w) for w in wanted if w is not None]
    tolerance = float(spec.get("tolerance") or 0.0)
    found = extract_numbers(text, spec)
    if not found:
        if spec.get("required"):
            return "fail", "the reply never states %s (required)" % name, 0
        return "skipped", "the reply does not state %s, which is allowed" % name, 0
    wrong, right = [], []
    for value, snippet in found:
        if not any(abs(value - w) <= tolerance + 1e-9 for w in wanted):
            wrong.append((value, snippet))
        else:
            right.append((value, snippet))
    if wrong and not right and (spec.get("mask_patterns") or spec.get("line_mask")):
        # the masks exist to keep the holding-deposit line out; when a reply writes "deposit/holding-deposit
        # ceilings: £2,596.15/£519.23" the mask can swallow the right figure and leave the other one, so
        # look once more without the masks before calling the remainder wrong
        unmasked = {k: v for k, v in spec.items() if k not in ("mask_patterns", "line_mask")}
        right = [(v, sn) for v, sn in extract_numbers(text, unmasked) if any(abs(v - w) <= tolerance + 1e-9 for w in wanted)]
    want_text = ", ".join(("%g" % w) for w in wanted)
    if right and wrong:
        return "pass", "states %s, which matches the pasted material (other figures nearby: %s)" % (
            want_text, ", ".join("%g" % v for v, _ in wrong[:3])), 0
    if wrong and material:
        quoted = [w for w in wrong if round(w[0], 2) in material]
        wrong = [w for w in wrong if round(w[0], 2) not in material]
        if quoted and not wrong:
            if spec.get("required"):
                return "fail", "the reply never states %s; the figure near it (%s) is one the person or the pasted material stated, not this fact" % (
                    name, ", ".join("%g" % v for v, _ in quoted[:3])), 0
            return "skipped", "the reply does not state %s (the figure near it, %s, is a pasted one), which is allowed" % (
                name, ", ".join("%g" % v for v, _ in quoted[:3])), 0
    if wrong:
        seen = collections.OrderedDict((w[0], w[1]) for w in wrong)
        return ("fail",
                "states %s; the pasted material says %s (e.g. %r)"
                % (", ".join("%g" % v for v in seen), want_text, list(seen.values())[0]),
                len(seen))
    return "pass", "states %s, which matches the pasted material" % want_text, 0


# --------------------------------------------------------------- turn score --
def row(name, kind, status, detail, critical=False, why=None):
    return collections.OrderedDict([
        ("check", name), ("kind", kind), ("status", status), ("detail", detail),
        ("critical", bool(critical)), ("why", why)])


def check_workdir(workdir, spec, agent=None):
    """Rows for ``workdir_expect``: what a file in the run's folder must contain, or
    must not, after this turn. Graded on the file, not on the words. The api agent
    has no folder, and a regrade has lost it, so those rows are skipped, not failed."""
    rows = []
    for rel, want in spec.items():
        if isinstance(want, list):
            want = {"contains": want}
        contains = list(want.get("contains") or [])
        absent = list(want.get("absent") or [])
        if agent == "api" or not workdir:
            for needle in contains + absent:
                rows.append(row("%s: %s" % (rel, needle), "file", "skipped",
                                "no folder to check (api agent, or a regrade)"))
            continue
        path = os.path.join(workdir, rel)
        text = None
        if os.path.isfile(path):
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                text = re.sub(r"[ \t]+", " ", fh.read())
        for needle in contains:
            key = re.sub(r"[ \t]+", " ", needle)
            if text is None:
                rows.append(row("%s contains %s" % (rel, needle), "file", "fail",
                                "%s was never written" % rel))
            else:
                rows.append(row("%s contains %s" % (rel, needle), "file",
                                "pass" if key in text else "fail",
                                "found in the file" if key in text else "not in the file"))
        for needle in absent:
            key = re.sub(r"[ \t]+", " ", needle)
            if text is None:
                rows.append(row("%s no longer has %s" % (rel, needle), "file", "fail",
                                "%s was never written" % rel))
            else:
                rows.append(row("%s no longer has %s" % (rel, needle), "file",
                                "fail" if key in text else "pass",
                                "still in the file" if key in text else "gone, as required"))
    return rows


def transient_error(text):
    """True when the agent's failure text names a passing provider condition.

    A thin wrapper over bench/launch.py, which owns the pattern for every runner."""
    return launch.transient_error(text)


def score_turn(turn, reply, journey, workdir=None, agent=None, file_rows=None):
    """One turn's scorecard: every check, its status, and the arithmetic on top.

    ``file_rows`` replays stored file-check rows (a regrade cannot re-read a folder
    that is gone); otherwise ``workdir_expect`` is checked in ``workdir`` now."""
    exp = turn.get("expect") or {}
    text = reply or ""
    rows = []

    for item in exp.get("must") or []:
        ok, detail = item_matches(text, item)
        rows.append(row(item_label(item), "must", "pass" if ok else "fail", detail))

    for item in exp.get("must_not") or []:
        ok, detail = item_matches(text, item)
        rows.append(row(item_label(item), "must_not", "fail" if ok else "pass",
                        detail if ok else "absent, as required"))

    fabrications = 0
    for name, spec in (exp.get("facts") or {}).items():
        status, detail, fabs = check_fact(text, name, spec, material_numbers(journey, turn))
        fabrications += fabs
        rows.append(row(name, "fact", status, detail, why=spec.get("why")))

    spec = exp.get("workdir_expect") or {}
    if file_rows is not None:
        rows.extend(file_rows)
    elif spec:
        rows.extend(check_workdir(workdir, spec, agent))

    if exp.get("max_questions") is not None or exp.get("min_questions") is not None:
        n = count_questions(text)
        lo = exp.get("min_questions", 0)
        hi = exp.get("max_questions", 10 ** 6)
        rows.append(row("question_budget", "questions", "pass" if lo <= n <= hi else "fail",
                        "%d question%s asked (quoted text masked); the range is %s to %s"
                        % (n, "" if n == 1 else "s", lo,
                           hi if hi < 10 ** 6 else "any")))

    hits = [t for t in TONE_BLOCKLIST if contains(text, t)]
    rows.append(row("tone", "tone", "fail" if hits else "pass",
                    ("insult or accusation aimed at a person: %s" % ", ".join(hits[:3])) if hits
                    else "no insult or accusation aimed at a landlord, agent or host",
                    critical=True,
                    why="Roast (尻洗) is criticism of the listing. Landlords, agents and hosts "
                        "are partners; insulting one fails the turn on its own."))

    asked = None
    for sentence in sentences(text):
        found = [t for t in PROTECTED_TERMS if contains(sentence, t)]
        if found and re.search("[?？]", sentence):
            asked = (found[0], sentence.strip()[:100])
            break
    rows.append(row("protected_characteristics", "protected", "fail" if asked else "pass",
                    ("asks about %s: %r" % asked) if asked
                    else "no question about a protected characteristic",
                    critical=True,
                    why="Not lawful grounds for a landlord to select on; SKILL.md section 8 "
                        "forbids asking or volunteering it."))

    language = exp.get("language") or journey.get("language")
    if language:
        share = cjk_share(text)
        bad = script_mismatch(text, journey.get("language") if isinstance(journey, dict) else None)
        if bad:
            rows.append(row("script", "language", "fail", "%d simplified characters in a traditional-Chinese journey: %s" % (len(bad), bad[:20])))
        if language.lower().startswith(("zh", "ja")):
            ok, want = share >= 0.20, "at least 20%"
        else:
            ok, want = share <= 0.05, "at most 5%"
        rows.append(row("language", "language", "pass" if ok else "fail",
                        "%.0f%% of the characters are CJK; %s is expected for %s"
                        % (share * 100, want, language)))

    if exp.get("ends_with") is not None:
        tail = (text or "").rstrip()[-int(exp.get("ends_within", 300)):]
        spec = exp["ends_with"]
        item = spec if isinstance(spec, dict) else {"any_of": [spec]}
        ok, detail = item_matches(tail, item)
        rows.append(row("ends_with", "ends_with", "pass" if ok else "fail",
                        detail + " (last %d characters)" % int(exp.get("ends_within", 300))))

    applied = [r for r in rows if r["status"] != "skipped"]
    passed = [r for r in applied if r["status"] == "pass"]
    failed_critical = [r["check"] for r in applied
                       if r["status"] == "fail" and r["critical"]]
    score = round(len(passed) / float(len(applied)), 4) if applied else None
    return collections.OrderedDict([
        ("score", score),
        ("applied", len(applied)),
        ("passed", len(passed)),
        ("failed", len(applied) - len(passed)),
        ("skipped", len(rows) - len(applied)),
        ("fabrications", fabrications),
        ("critical_failures", failed_critical),
        ("questions_asked", count_questions(text)),
        ("reply_chars", len(text)),
        ("checks", rows),
    ])


# ------------------------------------------------------------ prompt making --
def system_prompt(journey, refs="needed"):
    """The prompt pack, the ask-the-user protocol, onboarding, then this run's note.

    ``refs`` decides what else is pasted in. A chat box has no filesystem, so the
    reference files a journey actually leans on (the bridging axis for a short-let
    journey, the referencing axis for a money-gate one) have to travel with the
    system prompt or the model is being marked on a file it was never given.
    """
    parts = []
    for path, title in ((PROMPT_PACK, "SKILL INSTRUCTIONS"),
                        (INPUTS_MD, "WHEN YOU CANNOT GET SOMETHING"),
                        (ONBOARDING_MD, "ONBOARDING")):
        if os.path.exists(path):
            parts.append("# %s\n\n%s" % (title, read_text(path)))
    for rel in reference_files(journey, refs):
        parts.append("# %s\n\n%s" % (rel.upper(), read_text(os.path.join(SKILL_DIR, rel))))
    parts.append("# Exercise instructions (do not repeat in replies)\n\n" + RUN_NOTE)
    return "\n\n".join(parts)


def reference_files(journey, refs):
    if refs == "none":
        return []
    wanted = list(journey.get("references_needed") or []) if refs == "needed" else None
    if wanted is None:
        wanted = []
        base = os.path.join(SKILL_DIR, "references")
        for folder, _dirs, files in os.walk(base):
            for name in sorted(files):
                if name.endswith((".md", ".json")):
                    wanted.append(os.path.relpath(os.path.join(folder, name), SKILL_DIR))
    return [r for r in wanted if os.path.exists(os.path.join(SKILL_DIR, r))]


def user_message(turn, files=True):
    """The turn's own words, plus anything the user pasted with it. An attachment that
    was also written into the run's folder says so (a person with a shell who pastes
    their profile has the file right there; the agent should edit it, not talk about it)."""
    parts = [turn["user"]]
    for att in turn.get("attachments") or []:
        where = " (also in your working folder as %s)" % att["file"] if files and att.get("file") else ""
        parts.append("--- pasted: %s%s ---\n%s--- end of %s ---"
                     % (att["name"], where, att["text"]
                        if att["text"].endswith("\n") else att["text"] + "\n", att["name"]))
    return "\n\n".join(parts)


def transcript(history, user):
    """The whole conversation as one prompt, for agents with no session to resume."""
    lines = ["This is a continuing conversation. Everything below already happened; reply only "
             "to the last USER message, in the language it is written in.", ""]
    for role, content in history:
        lines.append("%s: %s" % (role.upper(), content))
        lines.append("")
    lines.append("USER: %s" % user)
    lines.append("")
    lines.append("Reply now, as the assistant, to that last message.")
    return "\n".join(lines)


# ------------------------------------------------------------------ workdir --
# What a shell-mode journey may touch inside its own temp folder: the profile it is
# asked to change and the validator that checks it, nothing that reaches the network.
# Manual and fetch journeys read only. Without this, "apply the change" can only be
# graded as words, and a model that says "written, valid" without writing anything
# scores the same as one that did the work (Codex Luna did exactly that, 2026-09-05).
CLAUDE_TOOLS_READ = "Read"
CLAUDE_TOOLS_SHELL = ("Read,Edit,Write,"
                      "Bash(python3 .claude/skills/vet-flat/scripts/profile_check.py:*),"
                      "Bash(python3 scripts/profile_check.py:*)")


def claude_tools(journey):
    return CLAUDE_TOOLS_SHELL if journey.get("mode") == "shell" else CLAUDE_TOOLS_READ


def codex_sandbox(journey):
    return "workspace-write" if journey.get("mode") == "shell" else "read-only"


def materialise_attachments(turn, workdir, agent):
    """Attachments that carry ``file`` are also written into the run's folder, so a
    shell-mode journey edits the real file instead of only talking about it. A
    leading title line that is not YAML ("profile.yaml - my settings") is dropped.
    The api agent has no folder, so nothing is written for it."""
    written = []
    if agent == "api" or not workdir:
        return written
    for att in turn.get("attachments") or []:
        rel = att.get("file")
        if not rel:
            continue
        lines = (att.get("text") or "").splitlines()
        while lines and not (":" in lines[0] or lines[0].lstrip().startswith(("#", "-"))):
            lines.pop(0)
        path = os.path.join(workdir, rel)
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        written.append(rel)
    return written


def prepare_workdir(journey, agent, workdir=None, system=None):
    """A clean folder with the skill where this agent looks for skills."""
    workdir = legacy_control.workdir(workdir)
    path = os.path.abspath(workdir) if workdir else tempfile.mkdtemp(
        prefix="vetflat-journey-%s-" % journey["id"])
    if not os.path.isdir(path):
        os.makedirs(path)
    plan = []
    if agent in SKILL_HOME:
        home = os.path.join(path, SKILL_HOME[agent])
        if not os.path.isdir(home):
            os.makedirs(home)
        dst = os.path.join(home, "vet-flat")
        if os.path.lexists(dst):
            (shutil.rmtree if os.path.isdir(dst) and not os.path.islink(dst)
             else os.unlink)(dst)
        shutil.copytree(SKILL_DIR, dst)
        plan.append("copy skills/vet-flat -> %s/vet-flat" % SKILL_HOME[agent])
    if agent == "codex" and system is not None:
        with io.open(os.path.join(path, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(system)
        plan.append("write AGENTS.md (codex exec has no append-system-prompt flag)")
    return path, plan


# ----------------------------------------------------------------- commands --
def no_mcp_config(workdir):
    """An empty MCP config in the workdir: with --strict-mcp-config the run sees none of
    the user's connectors (mail, calendar, drives), so the model cannot offer to read them.
    A pilot session offered to search the user's mailbox; that is not the assistant's call."""
    path = os.path.join(workdir, "_nomcp.json")
    if not os.path.exists(path):
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write('{"mcpServers": {}}\n')
    return path


def claude_command(prompt, workdir, model, system, session_id=None, resume=None,
                   tools=CLAUDE_TOOLS_READ):
    cmd = ["claude", "-p"]
    if resume:
        cmd += ["--resume", resume]
    else:
        cmd += ["--append-system-prompt", system]
        if session_id:
            cmd += ["--session-id", session_id]
    cmd += launch.claude_tool_flags(tools) + ["--output-format", "json", "--add-dir", workdir]
    if model:
        cmd += ["--model", model]
    # `--` ends the options, so a prompt that begins with a dash (a persona's pasted page
    # opened "--- pasted: booking homepage ---" on 2026-09-06 and the CLI refused it as an
    # unknown option) is still the prompt. Both CLIs accept it; tested 2026-09-07.
    return cmd + ["--", prompt]


def codex_command(prompt, workdir, model, sandbox="read-only"):
    cmd = ["codex", "exec", "--cd", workdir, "--sandbox", sandbox,
           "--skip-git-repo-check", "--json"]
    if model:
        cmd += ["--model", model]
    return cmd + ["--", prompt]


def claude_supports_resume(mode="auto"):
    """(bool, how). `claude --help` is the only authority; --session-mode overrides it."""
    if mode == "resume":
        return True, "forced by --session-mode resume"
    if mode == "replay":
        return False, "forced by --session-mode replay"
    override = os.environ.get("VETFLAT_CLAUDE_RESUME")
    if override in ("0", "1"):
        return override == "1", "VETFLAT_CLAUDE_RESUME=%s" % override
    try:
        proc = subprocess.Popen(["claude", "--help"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _err = proc.communicate(timeout=30)
        text = (out or b"").decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return False, "could not run `claude --help`; replaying the transcript instead"
    if "--resume" in text and "--session-id" in text:
        return True, "`claude --help` advertises --resume and --session-id"
    return False, "`claude --help` does not advertise --resume; replaying the transcript"


# ----------------------------------------------------------------- api call --
def api_url():
    base = (os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    if not base:
        return None
    return base + ("" if base.endswith("/chat/completions") else "/chat/completions")


def api_post(url, payload, key, timeout):
    """Use the shared authenticated HTTP transport without persisting API bodies.

    curl receives URL, headers and POST data privately on stdin. The shared helper
    disables curlrc, limits protocols and refuses authenticated redirects, avoiding
    the old urllib redirect/header behavior and the TLS fallback's secret argv.
    """
    scripts = os.path.join(SKILL_DIR, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import _fetch
    try:
        result = _fetch.post_json(url, payload, headers={"Authorization": "Bearer " + key},
                                  cache_ttl=0, min_gap=0, timeout=timeout)
    except (OSError, ValueError):
        return None, "HTTP request rejected before a response"
    if result["ok"]:
        return result["body"], None
    if result["status"]:
        return result["body"], "http error %s" % result["status"]
    return None, "HTTP transport failed before a response"


def api_reply(messages, model, timeout):
    return legacy_control.run_api(lambda: _api_reply(messages, model, timeout), model,
                                  {"messages": messages, "model": model, "timeout": timeout})


def _api_reply(messages, model, timeout):
    url = api_url()
    key = os.environ.get("OPENAI_API_KEY") or ""
    if not url or not key:
        return None, None, ("api mode needs OPENAI_BASE_URL and OPENAI_API_KEY in the "
                            "environment")
    payload = {"model": model, "temperature": 0, "messages": messages}
    raw, note = api_post(url, payload, key, timeout)
    if raw is None:
        return None, None, note
    try:
        body = json.loads(raw)
    except ValueError:
        return None, None, (note + "; " if note else "") + "the endpoint did not return JSON"
    if "error" in body and "choices" not in body:
        return None, None, "api error: %s" % json.dumps(body["error"])[:300]
    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return text, body.get("usage"), note


# The two CLIs' token parsers live in bench/launch.py, one copy for every runner.
# These names stay: bench/personas.py, bench/docs_bench.py and bench/pipeline.py call
# journeys.claude_answer(), and a rename would be a change to three files for nothing.
USAGE_KEYS = launch.USAGE_KEYS


def claude_usage(obj):
    """Tokens and cost from a --output-format json envelope; None when absent."""
    return launch.claude_usage(obj)


def claude_answer(stdout):
    """(final message, usage) out of `claude -p --output-format json` stdout."""
    return launch.claude_answer(stdout)


# --------------------------------------------------------------------- play --
def aggregate(journey, turns, errors):
    """Journey-level numbers from the turn cards: mean score, fabrications, critical
    failures, whether it completed, and whether it clears the pass line."""
    scored = [t for t in turns if t.get("score") is not None]
    journey_score = round(sum(t["score"] for t in scored) / float(len(scored)), 4) \
        if scored else None
    fabrications = sum(t.get("fabrications", 0) for t in turns)
    critical = [c for t in turns for c in (t.get("critical_failures") or [])]
    completed = len(scored) == len(journey["turns"]) and not errors
    meets = bool(completed and fabrications == PASS_LINE["fabrications"] and not critical
                 and (journey_score or 0) >= PASS_LINE["journey_score"])
    return journey_score, fabrications, critical, completed, meets


def play(journey, args, variant_id=None):
    """Run one journey, turn by turn, and return its record."""
    agent = args.agent
    tools, sandbox = claude_tools(journey), codex_sandbox(journey)
    label = journey["id"] + ("#" + variant_id if variant_id else "")
    legacy_control.job(label)
    system = system_prompt(journey, args.refs)
    workdir, plan = prepare_workdir(journey, agent, args.workdir,
                                    system if agent == "codex" else None)
    session_id = legacy_control.session_id()
    carry, how = (False, "n/a")
    if agent == "claude":
        carry, how = claude_supports_resume(args.session_mode)

    if args.dry_run:
        print("journey:  %s  (%s)" % (label, journey["title"]))
        print("agent:    %s" % agent)
        print("mode:     %s   language: %s   turns: %d"
              % (journey["mode"], journey.get("language"), len(journey["turns"])))
        print("model:    %s" % (args.model or "(the agent's default)"))
        print("workdir:  %s" % workdir)
        for line in plan or ["(nothing to copy: the skill travels in the system prompt)"]:
            print("          %s" % line)
        print("system:   dist/prompt-pack/INSTRUCTIONS.md + references/inputs.md + "
              "references/onboarding.md")
        for rel in reference_files(journey, args.refs):
            print("          + %s" % rel)
        print("          + this run's note (%d characters in total)" % len(system))
        if agent == "claude":
            print("session:  %s   (%s)" % ("--resume carries the history" if carry
                                           else "transcript replayed each turn", how))
        print("results:  %s" % os.path.join(
            os.path.relpath(args.results or RESULTS, ROOT), "journeys-" + today()))
        print("tone:     %d blocked phrases (en + zh)" % len(TONE_BLOCKLIST))
        if agent == "claude":
            print("tools:    %s" % tools)
        elif agent == "codex":
            print("sandbox:  %s" % sandbox)

    history, turns, errors = [], [], []
    for index, turn in enumerate(journey["turns"], 1):
        user = user_message(turn, files=(agent != "api"))
        written = materialise_attachments(turn, workdir, agent)
        exp = turn.get("expect") or {}
        if args.dry_run and written:
            print("          writes %s into the folder from the pasted attachment" % ", ".join(written))
        counts = "%d must, %d must_not, %d facts, %s questions" % (
            len(exp.get("must") or []), len(exp.get("must_not") or []),
            len(exp.get("facts") or {}),
            ("<=%s" % exp["max_questions"]) if exp.get("max_questions") is not None else "any")

        if args.dry_run:
            print("")
            print("turn %d/%d  user %d chars, %d attachment(s); checks: %s"
                  % (index, len(journey["turns"]), len(turn["user"]),
                     len(turn.get("attachments") or []), counts))
            if agent == "api":
                print("          POST %s" % (api_url() or "$OPENAI_BASE_URL/chat/completions"))
                print("          headers: Content-Type: application/json, "
                      "Authorization: Bearer ***")
                roles = ["system(%d)" % len(system)]
                roles += ["%s(%d)" % (r, len(c)) for r, c in history]
                roles += ["user(%d)" % len(user)]
                print("          messages: %s" % " ".join(roles))
            elif agent == "claude":
                prompt = user if (carry or index == 1) else transcript(history, user)
                cmd = claude_command(prompt, workdir, args.model, system, tools=tools,
                                     session_id=session_id if carry else None,
                                     resume=session_id if (carry and index > 1) else None)
                print("          cd %s && %s" % (workdir, shell_preview(cmd)))
            else:
                cmd = codex_command(transcript(history, user) if history else user,
                                    workdir, args.model, sandbox)
                print("          cd %s && %s" % (workdir, shell_preview(cmd)))
            history.append(("user", user))
            history.append(("assistant", "(dry run: the reply would be here)"))
            continue

        started = time.time()
        reply, usage, note = "", None, None
        attempts, provider_error = 1, False
        attempt_records = None
        if agent == "api":
            messages = [{"role": "system", "content": system}]
            for role, content in history:
                messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": user})
            reply, usage, note = api_reply(messages, args.model, args.timeout)
        else:
            if agent == "claude":
                prompt = user if (carry or index == 1) else transcript(history, user)
                cmd = claude_command(prompt, workdir, args.model, system, tools=tools,
                                     session_id=session_id if carry else None,
                                     resume=session_id if (carry and index > 1) else None)
            else:
                cmd = codex_command(transcript(history, user) if history else user,
                                    workdir, args.model, sandbox)
            # One launcher for every runner: stdin closed, both streams captured, the
            # one physical attempt, and the tails kept when the
            # provider never let the turn through at all.
            res = legacy_control.run_cli(cmd, workdir, args.timeout, agent,
                             attempts=MAX_ATTEMPTS, waits=RETRY_WAITS,
                             label="turn %d" % index)
            reply, usage = legacy_control.reply_text(res, agent), res.usage
            if getattr(res, "session_id", None):
                session_id = res.session_id          # the persisted CLI session identity
            attempts = res.attempts
            attempt_records = res.attempt_records
            provider_error = res.provider_error
            # The note the card always carried, plus the tails: a row that reads
            # "the agent exited 1: " with nothing behind it cannot be diagnosed later.
            note = res.tail_note("the agent " if (res.note or "").startswith("exited") else "")
        wall = round(time.time() - started, 2)

        if not (reply or "").strip():
            # A provider error is said out loud here. The turn is unscored either way,
            # but "the model wrote nothing" and "the provider never ran it" are not the
            # same finding, and only one of them is about the model.
            errors.append("turn %d: %s%s" % (index, "provider error; " if provider_error
                                             else "", note or "no reply"))
            turns.append(collections.OrderedDict([
                ("turn", index), ("user", turn["user"]), ("reply", reply or ""),
                ("note", note), ("wall_time_s", wall), ("score", None), ("checks", []),
                ("retries", (attempts - 1) if agent != "api" else 0),
                ("usage", usage), ("attempt_records", attempt_records),
                ("provider_error", provider_error)]))
            break

        card = score_turn(turn, reply, journey, workdir=workdir, agent=agent)
        card["turn"] = index
        card["user"] = turn["user"]
        card["reply"] = reply
        card["note"] = note
        card["wall_time_s"] = wall
        card["usage"] = usage
        card["attempt_records"] = attempt_records
        card["retries"] = (attempts - 1) if agent != "api" else 0
        card["provider_error"] = provider_error
        card.move_to_end("turn", last=False)
        turns.append(card)
        history.append(("user", user))
        history.append(("assistant", reply))
        print("  turn %d/%d  %s  %d/%d checks, %d fabrication(s)%s"
              % (index, len(journey["turns"]),
                 "%.2f" % card["score"] if card["score"] is not None else "-",
                 card["passed"], card["applied"], card["fabrications"],
                 ", CRITICAL: " + ", ".join(card["critical_failures"])
                 if card["critical_failures"] else ""))

    if args.dry_run:
        if not args.keep and not args.workdir and not legacy_control.active():
            shutil.rmtree(workdir, ignore_errors=True)
        return None

    journey_score, fabrications, critical, completed, meets = aggregate(journey, turns, errors)
    scored = [t for t in turns if t.get("score") is not None]
    record = collections.OrderedDict([
        ("journey", label),
        ("journey_id", journey["id"]),
        ("variant", variant_id),
        ("title", journey["title"]),
        ("agent", agent),
        ("model", args.model),
        ("run_at", now()),
        ("mode", journey["mode"]),
        ("language", journey.get("language")),
        ("tools", tools if agent == "claude" else None),
        ("sandbox", sandbox if agent == "codex" else None),
        ("turns_expected", len(journey["turns"])),
        ("turns_played", len(scored)),
        ("journey_score", journey_score),
        ("completed", completed),
        ("fabrications", fabrications),
        ("critical_failures", critical),
        ("meets_pass_line", meets),
        ("pass_line", collections.OrderedDict(sorted(PASS_LINE.items()))),
        ("errors", errors),
        ("workdir", workdir),
        ("outcome", journey.get("outcome")),
        ("turn_scores", turns),
    ])
    if not args.keep and not args.workdir and not legacy_control.active():
        shutil.rmtree(workdir, ignore_errors=True)
    return record


# ------------------------------------------------------------- results i/o --
MD_HEADER = ("| run (UTC) | agent | model | journey | turns | score | fabrications | "
             "critical | completed | pass line |\n"
             "|---|---|---|---|---|---|---|---|---|---|\n")


def md_row(rec):
    return ("| %s | %s | %s | %s | %d/%d | %s | %d | %s | %s | %s |\n"
            % (rec.get("run_at"), rec.get("agent"), rec.get("model") or "-",
               rec.get("journey"), rec.get("turns_played", 0), rec.get("turns_expected", 0),
               ("%.2f" % rec["journey_score"]) if rec.get("journey_score") is not None else "-",
               rec.get("fabrications", 0),
               ", ".join(rec.get("critical_failures") or []) or "-",
               "yes" if rec.get("completed") else "NO",
               "PASS" if rec.get("meets_pass_line") else "BELOW LINE"))


def results_dir(root=None, day=None):
    return os.path.join(root or RESULTS, "journeys-" + (day or today()))


def write_results(record, root=None, day=None):
    folder = results_dir(root, day)
    raw = os.path.join(folder, "raw")
    if not os.path.isdir(raw):
        os.makedirs(raw)
    safe = re.sub(r"[^A-Za-z0-9._#-]+", "-", "%s-%s" % (record["agent"], record["journey"]))
    index = 1
    while not legacy_control.active() and os.path.exists(os.path.join(raw, "%s-%d.json" % (safe, index))):
        index += 1
    raw_path = os.path.join(raw, "%s-%d.json" % (safe, index))
    with io.open(raw_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, indent=1) + "\n")

    jpath = os.path.join(folder, "scorecard.json")
    rows = []
    if os.path.exists(jpath):
        try:
            with io.open(jpath, encoding="utf-8") as fh:
                rows = json.load(fh)
        except ValueError:
            rows = []
    if legacy_control.active():
        rows = [r for r in rows if (r.get("agent"), r.get("journey")) != (record.get("agent"), record.get("journey"))]
    rows.append(summary_of(record, raw_path))
    write_scorecard(folder, rows)
    return raw_path, jpath


def summary_of(record, raw_path):
    summary = collections.OrderedDict(
        (k, v) for k, v in record.items() if k not in ("turn_scores",))
    summary["raw"] = os.path.relpath(raw_path, ROOT)
    return summary


def write_scorecard(folder, rows):
    day = os.path.basename(os.path.abspath(folder)).replace("journeys-", "") or today()
    with io.open(os.path.join(folder, "scorecard.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    with io.open(os.path.join(folder, "scorecard.md"), "w", encoding="utf-8") as fh:
        fh.write("# vet-flat journeys, %s\n\n"
                 "One row per journey per run. The score is the mean of the turn scores; a "
                 "journey passes only if it also completed, invented no numbers and kept its "
                 "tone.\n\n%s%s"
                 % (day, MD_HEADER, "".join(md_row(r) for r in rows)))


def regrade(folder, journeys_path=None):
    """Re-score every record under ``folder/raw`` with the current journeys file.

    The replies stay what they were; only the checks are applied again, so a
    calibration fix in evals/journeys.json reaches runs that were already paid for.
    File checks are carried over from the stored rows (the folder they looked at is
    gone). The scorecard is rebuilt in run order and each raw record is rewritten
    with ``regraded_at``."""
    doc = load_journeys(journeys_path)
    by_id = dict((j["id"], j) for j in doc["journeys"])
    raw_dir = os.path.join(folder, "raw")
    if not os.path.isdir(raw_dir):
        print("usage error: no raw/ folder under %s" % folder, file=sys.stderr)
        return 2
    rows = []
    for name in sorted(os.listdir(raw_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(raw_dir, name)
        with io.open(path, encoding="utf-8") as fh:
            rec = json.load(fh, object_pairs_hook=collections.OrderedDict)
        journey = by_id.get(rec.get("journey_id"))
        if journey is None:
            print("%s: no journey %r in the file; kept as is" % (name, rec.get("journey_id")))
            rows.append(summary_of(rec, path))
            continue
        variant = None
        for vid, v in variants_of(journey):
            if vid == rec.get("variant"):
                variant = v
        resolved = resolve(journey, variant)
        turns = []
        for old in rec.get("turn_scores") or []:
            index = old.get("turn") or (len(turns) + 1)
            if index > len(resolved["turns"]) or (old.get("score") is None and not old.get("reply")):
                turns.append(old)
                continue
            stored = [r for r in (old.get("checks") or []) if r.get("kind") == "file"]
            card = score_turn(resolved["turns"][index - 1], old.get("reply") or "", resolved,
                              file_rows=stored or None)
            for key in ("turn", "user", "reply", "note", "wall_time_s", "usage"):
                card[key] = old.get(key)
            card.move_to_end("turn", last=False)
            turns.append(card)
        rec["turn_scores"] = turns
        before = rec.get("journey_score")
        score, fabs, critical, completed, meets = aggregate(resolved, turns, rec.get("errors") or [])
        rec["turns_played"] = len([t for t in turns if t.get("score") is not None])
        rec["journey_score"], rec["fabrications"], rec["critical_failures"] = score, fabs, critical
        rec["completed"], rec["meets_pass_line"] = completed, meets
        rec["pass_line"] = collections.OrderedDict(sorted(PASS_LINE.items()))
        rec["regraded_at"] = now()
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
        rows.append(summary_of(rec, path))
        print("%s: %s -> %s, %d fabrication(s), %s" % (
            rec.get("journey"), before, score, fabs, "PASS" if meets else "BELOW LINE"))
    rows.sort(key=lambda r: r.get("run_at") or "")
    write_scorecard(folder, rows)
    print("%d record(s) regraded into %s" % (len(rows), os.path.join(folder, "scorecard.md")))
    return 0


# --------------------------------------------------------------------- main --
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journey", help="a journey id from evals/journeys.json")
    ap.add_argument("--all", action="store_true", help="every journey, one after another")
    ap.add_argument("--agent", choices=AGENTS, help="required unless --regrade is given")
    ap.add_argument("--regrade", metavar="FOLDER",
                    help="re-score every raw record under FOLDER/raw with the current "
                         "journeys file and rebuild its scorecard; nothing is re-run")
    ap.add_argument("--model", help="the model name to pass to the agent")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the exact command or request for every turn, "
                         "and run nothing")
    ap.add_argument("--variant", help="for a journey scripted in more than one language, "
                                      "run only this variant (for example zh)")
    ap.add_argument("--journeys", default=JOURNEYS_JSON, help="the journey file")
    ap.add_argument("--results", help="results root; default bench/results. The "
                                      "journeys-<date> folder is created inside it")
    ap.add_argument("--day", help="date label of the results folder (journeys-<day>); default today. A batch "
                         "that crosses midnight must pass it, or its later rows land in the next day's folder")
    ap.add_argument("--refs", choices=("needed", "all", "none"), default="needed",
                    help="which reference files travel in the system prompt: the ones the "
                         "journey declares (default), every reference, or none")
    ap.add_argument("--session-mode", choices=("auto", "resume", "replay"), default="auto",
                    help="claude only: carry the session with --resume, replay the transcript, "
                         "or probe `claude --help` and decide (default)")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("VETFLAT_TURN_TIMEOUT",
                                                                      1200)),
                    help="seconds per turn, default 1200")
    ap.add_argument("--workdir", help="use this directory instead of a fresh temp one")
    ap.add_argument("--keep", action="store_true", help="do not delete the temp workdir")
    legacy_control.add_arguments(ap)
    return ap


@legacy_control.entrypoint
def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.regrade:
        return regrade(args.regrade, args.journeys)
    if not args.agent:
        print("usage error: --agent is required (api, claude or codex)", file=sys.stderr)
        return 2
    if not args.journey and not args.all:
        print("usage error: give --journey <id> or --all", file=sys.stderr)
        return 2
    doc = load_journeys(args.journeys)
    journeys = doc["journeys"]
    if not args.all:
        journeys = [j for j in journeys if j["id"] == args.journey]
        if not journeys:
            print("usage error: no journey %r in %s" % (args.journey, args.journeys),
                  file=sys.stderr)
            return 2
    if args.agent == "api" and not args.model and not args.dry_run:
        print("usage error: api mode needs --model", file=sys.stderr)
        return 2

    worst = 0
    first = True
    for journey in journeys:
        for variant_id, variant in variants_of(journey):
            if args.variant and variant_id and variant_id != args.variant:
                continue
            resolved = resolve(journey, variant)
            label = journey["id"] + ("#" + variant_id if variant_id else "")
            if not first and args.dry_run:
                print("")
            first = False
            if not args.dry_run:
                print("%s  (%s, %d turns)" % (label, resolved["mode"],
                                              len(resolved["turns"])))
            record = play(resolved, args, variant_id)
            if record is None:
                continue
            write_results(record, args.results, args.day)
            print("  %s: score %s, %d fabrication(s), %s -> %s"
                  % (label,
                     ("%.2f" % record["journey_score"])
                     if record["journey_score"] is not None else "-",
                     record["fabrications"],
                     "completed" if record["completed"] else "DID NOT COMPLETE",
                     "PASS" if record["meets_pass_line"] else "BELOW LINE"))
            if not record["meets_pass_line"]:
                worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
