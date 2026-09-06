#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find the few paragraphs in a pasted document that answer a question. Grep, but ranked.

A tenancy agreement is 40 KB and the answer is two sentences. scripts/scan.py already finds
those two for the eighteen fixed questions, whose regexes are written down; this is for
everything else: the user's own `my_questions`, a review page with hundreds of reviews, a
planning officer's report, an operator's terms.

It splits every file into paragraphs (a review is a paragraph, a table row is a paragraph),
windows any paragraph over ~1,200 characters so a 5,000-character clause stays findable, and
ranks them with BM25 (k1 1.2, b 0.75) over the question expanded through
references/find-synonyms.yaml - so "break clause" finds a clause headed "Early termination",
and 押金 finds an English deposit clause. A synonym weighs 0.6 against 1.0 for the words you
typed, so it never outranks a literal match on equal evidence.

It prints the whole paragraph and its neighbours - a THICK VIEW - not a snippet, which is a
hypothesis under test rather than a proven gain (references/find.md). A hit is a sentence to
READ, never an answer: quote it, then decide. grep -n still works, and nothing in this skill
is findable only through this script.

Not a network tool. Standard library only, Python 3.9.

Usage:
  find.py pasted/ --ask "break clause"
  find.py pasted/ --ask "潮濕 發霉 move-out" --top 8
  find.py pasted/ --fixed F1,F12          the fixed-form regexes, ranked, same output shape
  find.py a.txt b.txt --ask "who holds the deposit" --context 2 --json
  find.py pasted/ --ask damp --all        every unit that scored, grep -n style
  find.py --selftest

Output: one block per hit - `#rank  score  file:line`, then the paragraph. --all prints
`file:line: first 120 characters`; --json prints [{rank, score, file, line, start, end, text,
matched_terms}], start/end spanning the matched unit and text being the thick view.

Exit codes: 0 hits, 1 no hits or nothing readable, 2 wrong arguments.
"""
from __future__ import unicode_literals

import argparse
import bisect
import collections
import io
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")
SYNONYMS = os.path.join(REFS, "find-synonyms.yaml")
QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")

sys.path.insert(0, HERE)
import scan  # noqa: E402  the tiny YAML reader and the fixed-form regexes live there

K1, B = 1.2, 0.75           # BM25: term-frequency saturation, length normalisation
SYNONYM_WEIGHT = 0.6        # a synonym adds a hit; it never outranks the literal term
WHY_WEIGHT = 0.3            # the `why` sentence of a fixed question: context, not evidence
FIXED_BONUS = 2.0           # per look_for pattern that matched, on top of BM25
LONG_UNIT = 1200            # a paragraph longer than this is windowed...
WINDOW, OVERLAP = 800, 200  # ...into windows that overlap, so no term falls down a crack
MAX_VIEW = 1000             # characters of thick view per hit
LINE_WIDTH = 120            # characters per line in --all
TEXT_EXT = (".txt", ".md", ".markdown", ".text", ".log", ".csv")
CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"   # kana and han
TOKEN = re.compile("[" + CJK + "]+|\\d+(?:[.,]\\d+)*|[a-z]+|[£$€%²³]")
BLOCK = re.compile(r"[^\s][\s\S]*?(?=\n[ \t]*\n|\Z)")
SENTENCE_END = re.compile(r"[.!?;:\n。！？；]")
STOP = frozenset("a an and are as at be by for from in is it its of on or that the this to "
                 "was were will with you your".split())
LITERAL = re.compile(r"\\[a-zA-Z]|\\.|\[[^\]]*\]|\{[^}]*\}|[()|?*+^$]", re.S)


# ---------------------------------------------------------------- tokenising ---
def stem(word):
    """Light English stemming: one suffix, and only when four or more letters survive."""
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    if word.endswith("es") and len(word) >= 6 and word[-3] in "xzh":
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) >= 5:
        return word[:-1]
    return word


def tokens(text):
    """Lower-case tokens: stemmed ASCII words, numbers, £ and %, CJK character bigrams."""
    out = []
    for piece in TOKEN.findall(text.lower()):
        if piece[0] >= "\u3000":               # a CJK run becomes its bigrams
            out.extend([piece] if len(piece) == 1 else
                       [piece[i:i + 2] for i in range(len(piece) - 1)])
        elif piece[0].isalpha():
            out.append(stem(piece))
        else:
            out.append(piece)
    return out


# -------------------------------------------------------------------- units ---
def paragraphs(text):
    """(start, end) of every blank-line separated block, with the whitespace trimmed off."""
    return [(m.start(), m.start() + len(m.group().rstrip())) for m in BLOCK.finditer(text)]


def windows(text):
    """(offset, text) for a short paragraph; overlapping windows for a long one."""
    if len(text) <= LONG_UNIT:
        return [(0, text)]
    out = []
    for at in range(0, len(text), WINDOW - OVERLAP):     # overlapping, so nothing is cut off
        piece = text[at:at + WINDOW]
        if not piece.strip():
            break
        cut = piece[:60].find(" ") + 1 if at else 0     # never start mid-word
        out.append((at + cut, piece[cut:]))
        if at + WINDOW >= len(text):
            break
    return out


def index_text(text, path):
    """The units of one document: file, first line number, character span, term counts."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    units = []
    for start, end in paragraphs(text):
        for offset, piece in windows(text[start:end]):
            at = start + offset
            units.append({"file": path, "line": bisect.bisect_right(starts, at), "start": at,
                          "end": at + len(piece), "text": piece,
                          "tf": collections.Counter(tokens(piece))})
    return units


def index_files(paths):
    """(files, units) for every text file under these files and folders, in a stable order."""
    files, units = [], []
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                dirs.sort()
                files += [os.path.join(root, n) for n in sorted(names)
                          if n.lower().endswith(TEXT_EXT) and not n.startswith(".")]
        elif os.path.exists(path):
            files.append(path)
        else:
            sys.stderr.write("No such file or folder: %s\n" % path)
    for path in files:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            units += index_text(fh.read(), path)
    return files, units


# ------------------------------------------------------------------ ranking ---
def rank(units, weights):
    """BM25 over the weighted query terms. Document = unit, corpus = every unit given."""
    if not units or not weights:
        return []
    lengths = [sum(u["tf"].values()) or 1 for u in units]
    n, avg = len(units), sum(lengths) / float(len(units))
    df = collections.Counter(t for u in units for t in weights if t in u["tf"])
    idf = dict((t, math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))) for t in weights)
    out = []
    for i, unit in enumerate(units):
        score, matched = 0.0, []
        for term, weight in weights.items():
            f = unit["tf"].get(term, 0)
            if f:
                score += (weight * idf[term] * f * (K1 + 1)
                          / (f + K1 * (1 - B + B * lengths[i] / avg)))
                matched.append(term)
        if score > 0:
            out.append((score, i, sorted(matched)))
    return out


def load_synonyms(path=SYNONYMS):
    """{group: [term, ...]} from references/find-synonyms.yaml, via scan.py's tiny reader."""
    with io.open(path, encoding="utf-8") as fh:
        groups = scan.parse_questions(fh.read()).get("groups")
    if not isinstance(groups, dict):
        raise scan.QuestionsError("%s has no 'groups' map" % path)
    return groups


def expand(question, groups):
    """{term: weight}: what the user typed at 1.0, every synonym of a firing group at 0.6.

    A group fires when one of its terms is a run of adjacent tokens in the question, so
    "holding deposit" fires the holding-deposit group and not the deposit one alone.
    """
    asked = tokens(question)
    runs = set(tuple(asked[i:j]) for i in range(len(asked)) for j in range(i + 1, i + 7))
    weights = dict((t, 1.0) for t in asked if t not in STOP)
    for terms in groups.values():
        phrases = [tokens(term) for term in terms]
        if not any(tuple(p) in runs for p in phrases):
            continue
        for phrase in phrases:
            for t in phrase:
                if t not in STOP and weights.get(t, 0.0) < SYNONYM_WEIGHT:
                    weights[t] = SYNONYM_WEIGHT
    return weights


def question_terms(item):
    """One fixed question's terms: the literal words in its look_for regexes, plus `why`."""
    weights = {}
    for pattern in item.get("look_for") or []:
        for t in tokens(LITERAL.sub(" ", pattern)):
            weights[t] = 1.0
    for t in tokens(item.get("why") or ""):
        weights.setdefault(t, WHY_WEIGHT)
    return dict((t, w) for t, w in weights.items() if t not in STOP)


def rank_fixed(units, questions, ids):
    """The look_for hits, scored by BM25 over the question's terms plus a bonus per pattern."""
    found = {}
    for qid in ids:
        item = questions[qid]
        scores = dict((i, (s, m)) for s, i, m in rank(units, question_terms(item)))
        for i, unit in enumerate(units):
            n = sum(1 for p in item["patterns"] if p.search(unit["text"]))
            if not n:
                continue
            base, matched = scores.get(i, (0.0, []))
            total = base + FIXED_BONUS * n
            if total > found.get(i, (0.0, []))[0]:
                found[i] = (total, [qid] + matched)
    return [(s, i, m) for i, (s, m) in found.items()]


# ------------------------------------------------------------------- output ---
def trim(text):
    """At most MAX_VIEW characters, cut back to the last sentence end."""
    if len(text) <= MAX_VIEW:
        return text
    cut = text[:MAX_VIEW - 1]
    ends = [m.end() for m in SENTENCE_END.finditer(cut)]
    if ends and ends[-1] > MAX_VIEW // 2:
        cut = cut[:ends[-1]]
    return cut.rstrip() + "…"


def thick_view(units, i, context):
    """The paragraph plus up to `context` neighbours from the same file, capped at MAX_VIEW."""
    lo = hi = i
    while lo > max(0, i - context) and units[lo - 1]["file"] == units[i]["file"]:
        lo -= 1
    while hi < min(len(units) - 1, i + context) and units[hi + 1]["file"] == units[i]["file"]:
        hi += 1
    while True:
        text = "\n\n".join(u["text"] for u in units[lo:hi + 1])
        if lo == hi or len(text) <= MAX_VIEW:
            return trim(text)
        if hi - i >= i - lo:
            hi -= 1
        else:
            lo += 1


def render(hits, units, context):
    """One block per hit: the grep line, then the thick view."""
    return "\n\n".join("#%d  %.2f  %s:%d\n%s"
                       % (n, score, units[i]["file"], units[i]["line"],
                          thick_view(units, i, context))
                       for n, (score, i, _terms) in enumerate(hits, 1))


def render_all(hits, units):
    """grep -n shape: one line per unit that scored at all."""
    return "\n".join("%s:%d: %s" % (units[i]["file"], units[i]["line"],
                                    " ".join(units[i]["text"].split())[:LINE_WIDTH])
                     for _score, i, _terms in hits)


def as_json(hits, units, context):
    return [{"rank": n, "score": round(score, 4), "file": units[i]["file"],
             "line": units[i]["line"], "start": units[i]["start"], "end": units[i]["end"],
             "text": thick_view(units, i, context), "matched_terms": terms}
            for n, (score, i, terms) in enumerate(hits, 1)]


# ----------------------------------------------------------------- selftest ---
SAMPLE = ("5. Deposit\nThe Tenant shall pay a deposit of five weeks' rent, being £2,128.85, "
          "which the Landlord shall protect with the Deposit Protection Service.\n\n"
          "12. Early termination\nEither party may end this agreement on or after the sixth "
          "month of the term by giving two months' written notice.\n\n"
          "20. 房東\n本合約之出租人為一家英格蘭註冊公司。\n")


def selftest():
    """A smoke test with no arguments: the tokenizer, the map, the ranking, the fixtures."""
    got = tokens("押金 5 weeks £2,400 damp")
    assert set(["押金", "5", "week", "£", "2,400", "damp"]) <= set(got), got
    units, groups = index_text(SAMPLE, "<built-in>"), load_synonyms()
    assert len(units) == 3, len(units)
    for question, wanted in (("break clause", "Early termination"), ("押金", "Deposit"),
                             ("landlord", "房東")):
        hits = sorted(rank(units, expand(question, groups)), reverse=True)
        assert hits and wanted in units[hits[0][1]]["text"], (question, hits[:1])
    folder = os.path.join(HERE, "..", "..", "..", "tests", "fixtures", "find")
    shipped = index_files([folder])[1] if os.path.isdir(folder) else []
    if shipped:                                          # the fixtures, when they shipped too
        assert len(shipped) > 50 and rank(shipped, expand("damp mould", groups)), len(shipped)
    sys.stdout.write("selftest ok: %d checks\n" % (5 if shipped else 4))
    return 0


# ---------------------------------------------------------------------- CLI ---
def build_parser():
    p = argparse.ArgumentParser(
        description="Find the paragraphs that answer a question in pasted documents.")
    p.add_argument("paths", nargs="*", help="files or folders of pasted text")
    p.add_argument("--ask", help="the question, in English or Chinese, in your own words")
    p.add_argument("--fixed", help="fixed-form ids instead of a question, e.g. F1,F12")
    p.add_argument("--ids-from", help="where --fixed reads its ids: fixed-questions (the "
                   "bundled file, the default) or a path to one; alone, it means all of them")
    p.add_argument("--top", type=int, default=5, help="how many hits to print (default 5)")
    p.add_argument("--context", type=int, default=1,
                   help="neighbouring paragraphs to show either side (default 1)")
    p.add_argument("--min-score", type=float, default=0.0, help="drop hits below this score")
    p.add_argument("--all", action="store_true", help="every unit that scored, grep -n style")
    p.add_argument("--json", action="store_true", help="machine-readable hits on stdout")
    p.add_argument("--synonyms", default=SYNONYMS, help="path to find-synonyms.yaml")
    p.add_argument("--selftest", action="store_true", help="run the built-in smoke test")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.paths or not (args.ask or args.fixed or args.ids_from):
        sys.stderr.write('Give a file or folder, and --ask "your question" or --fixed F1,F12. '
                         'See --help.\n')
        return 2
    started = time.time()
    files, units = index_files(args.paths)
    if not files:
        sys.stderr.write("Nothing readable in %s\n" % ", ".join(args.paths))
        return 1
    hits = []
    try:
        if args.fixed or args.ids_from:
            path = QUESTIONS if args.ids_from in (None, "fixed-questions") else args.ids_from
            questions = scan.load_questions(path)
            ids = ([q.strip() for q in args.fixed.split(",") if q.strip()] if args.fixed
                   else sorted(questions, key=scan.sort_key))
            unknown = [q for q in ids if q not in questions]
            if unknown:
                sys.stderr.write("No such fixed question: %s\n" % ", ".join(unknown))
                return 2
            hits += rank_fixed(units, questions, ids)
        if args.ask:
            hits += rank(units, expand(args.ask, load_synonyms(args.synonyms)))
    except (IOError, OSError, scan.QuestionsError) as exc:
        sys.stderr.write("Cannot read the question file: %s\n" % exc)
        return 1
    best = {}
    for score, i, terms in hits:
        if score > best.get(i, (0.0, []))[0]:
            best[i] = (score, terms)
    ordered = sorted(((s, i, t) for i, (s, t) in best.items() if s >= args.min_score),
                     key=lambda h: (-h[0], units[h[1]]["file"], h[1]))
    sys.stderr.write("%d units, %d files, %d hits, %d ms\n"
                     % (len(units), len(files), len(ordered), (time.time() - started) * 1000))
    if not ordered:
        return 1
    shown = ordered if args.all else ordered[:max(1, args.top)]
    if args.json:
        json.dump(as_json(shown, units, args.context), sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
    elif args.all:
        sys.stdout.write(render_all(shown, units) + "\n")
    else:
        sys.stdout.write(render(shown, units, args.context) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
