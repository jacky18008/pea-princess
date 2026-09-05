#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inline the glossary and the example report into viewer/viewer.html.

viewer.html has to be one self-contained file, so it cannot read glossary.yaml at
run time. This script writes the glossary and the sample report into the two
marked blocks in viewer.html, in place, so the browser viewer and scripts/render.py
always speak the same labels. Run it after editing either source file.

Usage:
  build_viewer.py            # rewrite viewer/viewer.html in place
  build_viewer.py --check    # exit 1 if viewer.html is out of date (for tests/CI)

Standard library only, Python 3.9. No network.
Exit codes: 0 ok, 1 out of date (--check) or too large, 2 wrong arguments.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIEWER = os.path.join(HERE, "viewer.html")
GLOSSARY = os.path.join(ROOT, "skills", "vet-flat", "references", "glossary.yaml")
SAMPLE = os.path.join(ROOT, "tests", "fixtures", "report-sample.json")
QUESTIONS = os.path.join(ROOT, "skills", "vet-flat", "references", "fixed-questions.yaml")
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")

# 140 KB: the layout, the glossary, the example report, the arithmetic check that
# mirrors scripts/render.py recompute(), and the share card that mirrors
# scripts/seed.py. Raised from 130 KB for the two contract sections the report owed
# the reader: the user's own questions answered at their stage, and "What only you
# can tell". Still one file a phone can open.
# 152 KB since the fixed form: fourteen questions per candidate in the example, their
# wording in three languages, and the `why` line the reader sees when one is unknown.
SIZE_LIMIT = 152 * 1024

# viewer.html has to stay one small self-contained file, so it carries only the
# glossary entries the layout actually looks up: the section titles, the verdict
# statuses, the evidence grades, the twelve axis names, the twelve landmine codes
# and the table labels, plus the four "only you can tell" requests both renderers
# fall back to. The domain jargon entries (EPC, heat network, Right to
# Manage...) stay in glossary.yaml for the skill and for human readers; no
# renderer resolves them, so inlining them would add weight and no behaviour.
LAYOUT_PREFIXES = ("section", "verdict", "evidence", "axis", "landmine", "ui", "only_you", "fixed")

# The fixed questions the same way: viewer.html draws one thing from them, the `why` line
# under an unknown answer, so the scanner's regexes, the caps and the groups stay in
# references/fixed-questions.yaml, where scripts/scan.py reads them.
QUESTION_FIELDS = ("why",)


def layout_terms(terms):
    return dict((k, v) for k, v in terms.items()
                if k.split(".")[0] in LAYOUT_PREFIXES)


def layout_questions(questions):
    return dict((qid, dict((k, v) for k, v in item.items() if k in QUESTION_FIELDS))
                for qid, item in questions.items())

sys.path.insert(0, SCRIPTS)
import render  # noqa: E402  (same mini-YAML parser as the shell renderer)
import scan  # noqa: E402    (owns references/fixed-questions.yaml and its parser)


def js_literal(name, obj):
    """A JSON literal that is safe to sit inside a <script> element."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028")
    return "var %s = %s;" % (name, text)


def replace_block(source, name, body):
    pattern = re.compile(r"(/\*BEGIN:%s\*/\n).*?(\n/\*END:%s\*/)" % (name, name), re.S)
    if not pattern.search(source):
        raise SystemExit("viewer.html has no /*BEGIN:%s*/ ... /*END:%s*/ block" % (name, name))
    # The replacement is a function, so re does not process backslash escapes in it.
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), source, count=1)


def build():
    terms = render.load_glossary(GLOSSARY)
    questions = layout_questions(scan.load_questions(QUESTIONS))
    with io.open(SAMPLE, encoding="utf-8") as fh:
        sample = json.load(fh)
    with io.open(VIEWER, encoding="utf-8") as fh:
        source = fh.read()
    source = replace_block(source, "GLOSSARY", js_literal("GLOSSARY", layout_terms(terms)))
    source = replace_block(source, "FIXED", js_literal("FIXED", questions))
    source = replace_block(source, "SAMPLE", js_literal("SAMPLE", sample))
    return source, len(layout_terms(terms)), len(sample.get("candidates", []))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit 1 if viewer.html is out of date")
    args = parser.parse_args(argv)

    built, n_terms, n_candidates = build()
    with io.open(VIEWER, encoding="utf-8") as fh:
        existing = fh.read()
    size = len(built.encode("utf-8"))

    if args.check:
        if built != existing:
            sys.stderr.write("viewer.html is out of date. Run: python3 viewer/build_viewer.py\n")
            return 1
        sys.stderr.write("viewer.html is up to date (%d terms, %d candidates, %.1f KB).\n"
                         % (n_terms, n_candidates, size / 1024.0))
        return 0

    if built != existing:
        with io.open(VIEWER, "w", encoding="utf-8") as fh:
            fh.write(built)
        sys.stderr.write("wrote %s\n" % VIEWER)
    else:
        sys.stderr.write("%s already up to date\n" % VIEWER)
    sys.stderr.write("  %d glossary terms, sample with %d candidates, %.1f KB total\n"
                     % (n_terms, n_candidates, size / 1024.0))
    if size > SIZE_LIMIT:
        sys.stderr.write("  WARNING: %.1f KB is over the %.0f KB budget for a single file.\n"
                         % (size / 1024.0, SIZE_LIMIT / 1024.0))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
