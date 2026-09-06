#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-scan pasted text for the fixed questions, and say which ones it is silent on.

A model that reads 40 KB of a pasted listing skips things. This script does the reading:
it runs the `look_for` patterns in `references/fixed-questions.yaml` over the text and
hands back the candidate SENTENCES, with line numbers, per question. The model then fills
the fixed form from quotes it can point at, and asks the user only about the questions the
text is silent on.

A candidate is a sentence worth reading, never an answer: the patterns are deliberately
loose, and two of them can hit the same sentence. Read it, then decide.

The patterns are bilingual (English and Chinese) and case-insensitive, so there is no
--lang: the same run finds both.

Not a network tool. Standard library only, Python 3.9.

Usage:
  scan.py listing.txt                    > candidates.json
  cat listing.txt | scan.py -            > candidates.json
  scan.py listing.txt --table            # the same thing as a plain table
  scan.py listing.txt --tier gate        # only the eight the gate asks (default: full)
  scan.py listing.txt --questions PATH   # a different fixed-questions.yaml

The tiers are the `tiers` block of references/fixed-questions.yaml: gate = the eight,
standard = the fourteen, full = all eighteen. Scanning defaults to full because reading
is cheap: the report decides how many it has to ANSWER, this decides what to look for.

Output (one JSON object on stdout):
  {"ok": true, "source": "listing.txt", "lines": 84, "tier": "full",
   "items": [{"id": "F1", "group": "gate", "ask_if_missing": "always",
              "candidates": [{"line_no": 12, "text": "Deposit: five weeks' rent."}]}, ...],
   "summary": {"found_candidates": 11, "silent": ["F3", "F8"]}}

The ids with no candidate are also written to stderr as one plain line, because that is the
list the model has to turn into questions for the user.

Exit codes: 0 ok, 1 the text or the questions file could not be read, 2 wrong arguments.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")
DEFAULT_QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")

# Scanning is cheap, so it looks for everything by default; the tier decides which
# questions must be ANSWERED, and that is the report's business (scripts/render.py).
DEFAULT_TIER = "full"
# A tier name nobody recognises answers the fourteen rather than none: a report that
# says nothing about its depth is a standard one.
FALLBACK_TIER = "standard"

MAX_CANDIDATES = 5          # per question: enough to choose from, few enough to read
MAX_TEXT = 300              # the quote limit in report-schema.json
WINDOW = 120                # characters kept either side of a match in a very long line

# Sentence ends: ASCII punctuation only when a space follows it (so 2,400.00 stays whole),
# Chinese punctuation always.
SENTENCE_END = re.compile(r"(?<=[.!?;])\s+|(?<=[。！？；])\s*")


class QuestionsError(Exception):
    """The fixed-questions file could not be read."""


# ------------------------------------------------------------------ parsing ---
BARE_INT = re.compile(r"^-?\d+$")
BARE_WORD = re.compile(r"^[A-Za-z0-9_.#\-]+$")


def _scalar(raw, lineno):
    """One value: "double-quoted" (JSON), 'single-quoted' (literal), a bare int or word."""
    text = raw.strip()
    if text.startswith('"'):
        try:
            value, _end = json.JSONDecoder().raw_decode(text)
        except ValueError:
            raise QuestionsError("line %d: value is not a valid quoted string" % lineno)
        return value
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise QuestionsError("line %d: a single-quoted value must end with a quote" % lineno)
        return text[1:-1].replace("''", "'")
    if BARE_INT.match(text):
        return int(text)
    if BARE_WORD.match(text):
        return text
    raise QuestionsError("line %d: quote this value ('single' keeps a regex literal)" % lineno)


def parse_questions(text):
    """Parse the tiny YAML subset used by references/fixed-questions.yaml.

    Two-space indent, maps and lists of scalars, # comments. Deliberately small: the file
    has to be readable by this parser, by a human and by a real YAML library alike.
    """
    root = {}
    stack = [[-1, root, None, None]]        # indent, node, parent, key (parent/key: to relink)
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise QuestionsError("line %d: indent must be a multiple of 2" % lineno)
        line = raw.strip()
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        top = stack[-1]
        if line.startswith("- "):
            node = top[1]
            if isinstance(node, dict):
                if node:
                    raise QuestionsError("line %d: a key already has map entries, so it cannot "
                                         "also be a list" % lineno)
                node = []
                top[1] = node
                top[2][top[3]] = node
            node.append(_scalar(line[2:], lineno))
            continue
        if not isinstance(top[1], dict):
            raise QuestionsError("line %d: expected a list item under this key" % lineno)
        if ":" not in line:
            raise QuestionsError("line %d: expected 'key:' or 'key: value'" % lineno)
        key, _sep, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            node = {}
            top[1][key] = node
            stack.append([indent, node, top[1], key])
        else:
            top[1][key] = _scalar(rest, lineno)
    return root


def load_document(path=DEFAULT_QUESTIONS):
    """The whole file as plain data: `tiers` and `questions`."""
    with io.open(path, encoding="utf-8") as fh:
        return parse_questions(fh.read())


def load_tiers(path=DEFAULT_QUESTIONS):
    """{tier name: [group, ...]} from the file's `tiers` block.

    This is the ONE place the mapping from how deep a run goes to how many questions it
    answers is written down. Everything else - this scanner, scripts/render.py, the
    viewer - reads it from here, so raising a tier is one edit in one file.
    """
    tiers = load_document(path).get("tiers")
    if not isinstance(tiers, dict):
        raise QuestionsError("%s has no 'tiers' map" % path)
    out = {}
    for name, groups in tiers.items():
        if not isinstance(groups, list) or not groups:
            raise QuestionsError("%s: tier %s is not a list of groups" % (path, name))
        out[name] = list(groups)
    return out


def ids_for_tier(questions, tiers, tier=DEFAULT_TIER):
    """The ids a run at this tier has to answer, in question order.

    An unrecognised tier falls back to `standard`; if even that is missing the caller
    gets every question, because a broken tiers block must never silently drop a question.
    """
    groups = tiers.get(tier) or tiers.get(FALLBACK_TIER)
    ordered = sorted(questions, key=sort_key)
    if not groups:
        return ordered
    return [qid for qid in ordered if questions[qid].get("group") in groups]


def load_questions(path=DEFAULT_QUESTIONS):
    """{id: fields} in file order, with the regexes already compiled under `patterns`."""
    doc = load_document(path)
    questions = doc.get("questions")
    if not isinstance(questions, dict):
        raise QuestionsError("%s has no 'questions' map" % path)
    for qid, item in questions.items():
        if not isinstance(item, dict):
            raise QuestionsError("%s: question %s is not a map" % (path, qid))
        item["id"] = qid
        patterns = []
        for pattern in item.get("look_for") or []:
            try:
                patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as exc:
                raise QuestionsError("%s: %s look_for %r is not a regex: %s" % (path, qid, pattern, exc))
        item["patterns"] = patterns
    return questions


# ----------------------------------------------------------------- scanning ---
def sentences(line):
    """The sentences in one line, in order, each with the column it starts at."""
    out = []
    at = 0
    for piece in SENTENCE_END.split(line):
        if piece is None:
            continue
        start = line.find(piece, at)
        if start < 0:
            start = at
        at = start + len(piece)
        text = piece.strip()
        if text:
            out.append(text)
    return out


def excerpt(text, match):
    """The sentence, or a window around the match when the sentence is very long."""
    if len(text) <= MAX_TEXT:
        return text
    start = max(0, match.start() - WINDOW)
    stop = min(len(text), match.end() + WINDOW)
    cut = text[start:stop]
    if start > 0 and " " in cut[:40]:
        cut = cut[cut.index(" ") + 1:]
    if stop < len(text) and " " in cut[-40:]:
        cut = cut[:cut.rindex(" ")]
    return cut.strip()[:MAX_TEXT]


def scan_text(text, questions, ids=None):
    """[{id, group, ask_if_missing, candidates: [{line_no, text}]}] in question order."""
    lines = text.splitlines()
    items = []
    for qid in (ids if ids is not None else sorted(questions, key=sort_key)):
        item = questions[qid]
        found = []
        seen = set()
        for line_no, line in enumerate(lines, 1):
            if not line.strip():
                continue
            for sentence in sentences(line):
                hit = None
                for pattern in item.get("patterns") or []:
                    hit = pattern.search(sentence)
                    if hit:
                        break
                if not hit:
                    continue
                got = excerpt(sentence, hit)
                key = " ".join(got.lower().split())
                if key in seen:
                    continue
                seen.add(key)
                found.append({"line_no": line_no, "text": got})
                if len(found) >= MAX_CANDIDATES:
                    break
            if len(found) >= MAX_CANDIDATES:
                break
        items.append({"id": qid, "group": item.get("group"),
                      "ask_if_missing": item.get("ask_if_missing"), "candidates": found})
    return items


def sort_key(qid):
    """F2 sorts before F10: the number counts, not the string."""
    digits = "".join(ch for ch in qid if ch.isdigit())
    return (int(digits) if digits else 0, qid)


def scan(text, questions, source="stdin", tier=DEFAULT_TIER, ids=None):
    items = scan_text(text, questions, ids)
    silent = [item["id"] for item in items if not item["candidates"]]
    return {
        "ok": True,
        "source": source,
        "lines": len(text.splitlines()),
        "tier": tier,
        "items": items,
        "summary": {
            "found_candidates": sum(len(item["candidates"]) for item in items),
            "silent": silent,
        },
        "note": "candidate sentences only, never answers: read each one before you fill the form",
    }


def silent_line(result):
    """The one sentence the model has to act on: what nothing in the text answered."""
    silent = result["summary"]["silent"]
    if not silent:
        return "every question has at least one candidate sentence; read them before answering"
    return "no sentence found for %s — ask the user these, once, in one message" % ", ".join(silent)


def table(result):
    rows = [("id", "group", "line", "candidate sentence")]
    for item in result["items"]:
        if not item["candidates"]:
            rows.append((item["id"], item["group"] or "", "-", "(nothing found - ask the user)"))
            continue
        for i, cand in enumerate(item["candidates"]):
            text = cand["text"]
            if len(text) > 96:
                text = text[:95] + "…"
            rows.append((item["id"] if i == 0 else "", item["group"] if i == 0 else "",
                         str(cand["line_no"]), text))
    widths = [max(len(str(row[i])) for row in rows) for i in range(3)]
    out = []
    for row in rows:
        out.append("  ".join([str(row[i]).ljust(widths[i]) for i in range(3)] + [row[3]]).rstrip())
    out.insert(1, "  ".join(["-" * widths[i] for i in range(3)] + ["-" * 20]))
    return "\n".join(out)


def build_parser():
    p = argparse.ArgumentParser(
        description="Find the candidate sentences for the fixed questions in pasted text.")
    p.add_argument("text", help="path to a text file, or - to read stdin")
    p.add_argument("--tier", default=DEFAULT_TIER,
                   help="which questions to look for: gate (8), standard (14) or full (18, "
                        "the default). Any tier name in the file's `tiers` block works.")
    p.add_argument("--questions", default=DEFAULT_QUESTIONS,
                   help="path to references/fixed-questions.yaml")
    p.add_argument("--table", action="store_true", help="print a plain table instead of JSON")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        questions = load_questions(args.questions)
        tiers = load_tiers(args.questions)
    except (IOError, OSError, QuestionsError) as exc:
        sys.stderr.write("Cannot read the questions at %s: %s\n" % (args.questions, exc))
        return 1
    if args.tier not in tiers:
        sys.stderr.write("Unknown tier %r. The file offers: %s\n"
                         % (args.tier, ", ".join(sorted(tiers))))
        return 2
    ids = ids_for_tier(questions, tiers, args.tier)
    if args.text == "-":
        source = "stdin"
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        text = stream.read().decode("utf-8", "replace")
    else:
        source = os.path.basename(args.text)
        try:
            with io.open(args.text, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (IOError, OSError) as exc:
            sys.stderr.write("Cannot read the text: %s\n" % exc)
            return 1
    result = scan(text, questions, source, args.tier, ids)
    sys.stderr.write(silent_line(result) + "\n")
    if args.table:
        sys.stdout.write(table(result) + "\n")
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
