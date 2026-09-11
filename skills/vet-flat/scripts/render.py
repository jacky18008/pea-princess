#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn a Pea Princess report.json into the fixed report layout.

The standard is `references/report-schema.json`, not the HTML: models emit JSON,
this script decides the layout. `viewer/viewer.html` renders the same sections in
the same order in a browser, from the same JSON and the same glossary.

Not a network tool. Standard library only, Python 3.9.

Usage:
  render.py report.json                  > report.html
  render.py report.json --lang zh-TW     > report.zh-TW.html
  render.py report.json --md             > report.md
  render.py report.json --validate-only            # check, print nothing
  render.py report.json --strict --validate-only   # ...and fail on any warning

Every number needs a source: each axis number and each metric must carry at least one
id in `sources` or a `computed_by` note. One that carries neither is a warning here and
an error under --strict, and both renderers mark it "no source".

Exit codes: 0 ok, 1 the report failed validation, 2 wrong arguments.
Errors and warnings go to stderr; the report goes to stdout.
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
DEFAULT_SCHEMA = os.path.join(REFS, "report-schema.json")
DEFAULT_GLOSSARY = os.path.join(REFS, "glossary.yaml")
DEFAULT_FIXED = os.path.join(REFS, "fixed-questions.yaml")

FOOTER_TEMPLATE = "Generated with pea-princess {version} \u2014 {url}"
DEFAULT_SOURCE_URL = "https://github.com/jacky18008/pea-princess"

# The twelve sections, in order. (glossary id, html anchor)
SECTIONS = [
    ("section.verdict", "verdict"),
    ("section.hard_filters", "hard-filters"),
    ("section.fixed", "fixed"),
    ("section.comparison", "comparison"),
    ("section.worst_reviews", "worst-reviews"),
    ("section.landmines", "landmines"),
    ("section.axes", "axes"),
    ("section.questions", "questions"),
    ("section.only_you", "only-you"),
    ("section.gaps", "gaps"),
    ("section.sources", "sources"),
    ("section.about", "about"),
]

METRIC_KEYS = [
    ("price_per_sqft_epc", "ui.price_per_sqft"),
    ("crime_6mo_count", "ui.crime_6mo"),
    ("commute_min", "ui.commute"),
    ("commute_redundancy_grade", "ui.redundancy"),
    ("management_organic_score", "ui.organic_score"),
    ("management_incentivised_share", "ui.incentivised_share"),
    ("nearest_works_m", "ui.nearest_works"),
    ("landlord_type", "ui.landlord_type"),
]

COST_KEYS = [
    ("rent_pcm", "ui.rent_pcm"),
    ("bills_low", "ui.bills_low"),
    ("bills_planning", "ui.bills_planning"),
    ("bills_stress", "ui.bills_stress"),
    ("council_tax", "ui.council_tax"),
    ("all_in_planning", "ui.all_in_planning"),
]

PROFILE_KEYS = [
    "min_floor_area_sqft", "max_building_age_years", "rent_pcm_target", "all_in_pcm_ceiling",
    "move_in_earliest", "move_in_latest", "commute_destination", "commute_max_min",
    "reject_ground_floor", "must_haves", "guarantor_route", "notes",
]

# The user's own questions (profile.yaml my_questions) are answered where they are read:
# filter with the hard filters, vet under the verdict, compare as rows of the side-by-side
# table, viewing with the viewing-day checks, sign in its own list before signing.
QUESTION_STAGES = ["filter", "vet", "compare", "viewing", "sign"]

# Section 3, "The questions we always answer": the eighteen ids of
# references/fixed-questions.yaml and the three states each one can be in. found is read
# off a document and carries the sentence; asked is the user's own answer; unknown is
# nobody's answer yet, and is drawn like a failure because that is what it costs.
# How many of them a given report has to answer is NOT a number written here: it is the
# `tiers` block of references/fixed-questions.yaml, resolved by active_fixed_ids() below.
FIXED_IDS = ["F%d" % i for i in range(1, 19)]

# The three groups, in the order the section draws them, and the label above each.
FIXED_GROUPS = [("gate", "ui.fixed_gate"),
                ("listing", "ui.fixed_listing"),
                ("extended", "ui.fixed_extended")]
FIXED_STATES = {
    "found": ("ok", "ui.found"),
    "asked": ("unk", "ui.asked_you"),
    "unknown": ("bad", "ui.unknown"),
}

# Section 8, "What only you can tell": what no register, feed or photo can carry. Asked
# only when the report named nothing of its own, and always as a request, not a gap.
ONLY_YOU_DEFAULTS = ["only_you.smell", "only_you.noise_night",
                     "only_you.light_today", "only_you.street_feel"]


# --------------------------------------------------------------- glossary ---
class GlossaryError(Exception):
    pass


def parse_mini_yaml(text):
    """Parse the deliberately tiny subset of YAML used by glossary.yaml.

    Rules: two-space indent, three levels, every scalar is a double-quoted JSON
    string on one line, a line whose first non-space character is # is a comment.
    """
    root = {}
    stack = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise GlossaryError("line %d: indent must be a multiple of 2" % lineno)
        line = raw.strip()
        if ":" not in line:
            raise GlossaryError("line %d: expected 'key:' or 'key: \"value\"'" % lineno)
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise GlossaryError("line %d: indentation does not close" % lineno)
        parent = stack[-1][1]
        if rest == "":
            node = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            if not rest.startswith('"'):
                raise GlossaryError("line %d: values must be double-quoted" % lineno)
            try:
                value, _ = json.JSONDecoder().raw_decode(rest)
            except ValueError:
                raise GlossaryError("line %d: value is not a valid quoted string" % lineno)
            parent[key] = value
    return root


def load_glossary(path):
    with io.open(path, encoding="utf-8") as fh:
        doc = parse_mini_yaml(fh.read())
    terms = doc.get("terms")
    if not isinstance(terms, dict):
        raise GlossaryError("%s has no 'terms' map" % path)
    return terms


class Labels(object):
    """Look a label or a plain-language gloss up in the reader's language."""

    def __init__(self, terms, lang):
        self.terms = terms
        self.lang = lang or "en"
        self.chain = self._chain(self.lang)

    @staticmethod
    def _chain(lang):
        out = [lang]
        if "-" in lang:
            out.append(lang.split("-")[0])
        # zh-HK / zh-MO readers get traditional; bare zh gets simplified.
        if lang.lower().startswith("zh") and "zh-TW" not in out:
            out.append("zh-TW" if lang.lower() in ("zh-hk", "zh-mo", "zh-hant") else "zh-CN")
        out.append("en")
        return out

    def label(self, term_id, default=None):
        entry = self.terms.get(term_id)
        if not entry:
            return default if default is not None else term_id
        for lang in self.chain:
            if entry.get(lang):
                return entry[lang]
        return default if default is not None else term_id

    def plain(self, term_id, default=""):
        entry = self.terms.get(term_id)
        if not entry:
            return default
        for lang in self.chain:
            got = entry.get("plain-" + lang)
            if got:
                return got
        return entry.get("plain", default)

    def tip(self, term_id):
        """What to show on hover: the original jargon plus the plain sentence."""
        entry = self.terms.get(term_id) or {}
        bits = [b for b in (entry.get("term"), self.plain(term_id)) if b]
        return " \u2014 ".join(bits)


# ------------------------------------------------------- the fixed form ---
def fixed_questions(path=DEFAULT_FIXED):
    """The fixed questions by id. scripts/scan.py owns the file and its parser.

    Only the `why` line is used here: it is what the reader sees in the answer cell of an
    unknown row, so they know what to go and find. A missing or broken file must never stop
    a report rendering, so this degrades to no questions and the rows still draw.
    """
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import scan
        return scan.load_questions(path)
    except Exception:                                    # noqa: BLE001 - see the docstring
        return {}


def fixed_tiers(path=DEFAULT_FIXED):
    """{tier name: [group, ...]} from references/fixed-questions.yaml, or {} if unreadable.

    Same rule as fixed_questions(): a broken or missing file must never stop a report
    rendering, so this degrades to no tiers and the caller falls back to all eighteen.
    """
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import scan
        return scan.load_tiers(path)
    except Exception:                                    # noqa: BLE001 - see the docstring
        return {}


def active_tier(data):
    """Which tier's questions this report owes an answer to, as a name.

    In order: the user's own override in the profile snapshot (advanced.fixed_form.questions,
    when it is anything but `auto`), then their budget_mode, then the tier the run actually
    finished at, then `standard`. The user's setting beats the run because the fixed form is
    a promise made to the reader, not a side effect of how far the escalation ladder went.
    """
    snapshot = data.get("profile_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    advanced = snapshot.get("advanced")
    fixed_form = advanced.get("fixed_form") if isinstance(advanced, dict) else None
    if isinstance(fixed_form, dict):
        chosen = fixed_form.get("questions")
        if chosen and chosen != "auto":
            return chosen
    mode = snapshot.get("budget_mode")
    if mode:
        return mode
    gb = data.get("generated_by")
    tier = gb.get("tier") if isinstance(gb, dict) else None
    return tier or "standard"


def active_fixed_ids(data, questions=None, tiers=None):
    """The ids this report has to answer, in question order.

    Everything about "how many" comes from references/fixed-questions.yaml, so raising a
    tier is one edit in one file. If that file cannot be read the answer is all eighteen:
    asking for too much is a warning the user can read, dropping a question silently is not.
    """
    questions = fixed_questions() if questions is None else questions
    tiers = fixed_tiers() if tiers is None else tiers
    if not questions or not tiers:
        return list(FIXED_IDS)
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import scan
        return scan.ids_for_tier(questions, tiers, active_tier(data))
    except Exception:                                    # noqa: BLE001
        return list(FIXED_IDS)


def fixed_order(entry_id):
    """F2 sorts before F10: the number counts, not the string."""
    return (FIXED_IDS.index(entry_id), "") if entry_id in FIXED_IDS else (len(FIXED_IDS), entry_id or "")


def fixed_rows(cand):
    """[(index in the JSON, entry)] in question order, so the locators still point home."""
    rows = [(i, e) for i, e in enumerate(cand.get("fixed_answers") or []) if isinstance(e, dict)]
    return sorted(rows, key=lambda pair: fixed_order(pair[1].get("id")))


def fixed_group_rows(cand, questions):
    """[(label term id, [(index, entry), ...])] - the candidate's answers, in group order.

    Rows are what the candidate actually carries, never a filter on the active tier: an
    answer from a deeper run still belongs to the reader, and a missing one is already a
    warning (an error under --strict), not something to hide. Groups with no rows are
    dropped, and anything whose group is unknown is drawn last, under no label.
    """
    rows = fixed_rows(cand)
    out = []
    placed = set()
    for group, label in FIXED_GROUPS:
        got = [(i, e) for i, e in rows
               if (questions.get(e.get("id")) or {}).get("group") == group]
        placed.update(i for i, _e in got)
        if got:
            out.append((label, got))
    left = [(i, e) for i, e in rows if i not in placed]
    if left:
        out.append((None, left))
    return out


def fixed_answer_text(entry, questions):
    """The answer cell: what was found, or - when nobody knows - what it costs not to know."""
    if entry.get("status") == "unknown":
        return (questions.get(entry.get("id")) or {}).get("why") or ""
    return entry.get("answer") or ""


# -------------------------------------------------------------- validation ---
TYPE_MAP = {
    "object": dict, "array": list, "string": str,
    "boolean": bool, "null": type(None),
}


def _is_type(value, name):
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    py = TYPE_MAP.get(name)
    if py is None:
        return True
    if py is str:
        return isinstance(value, str)
    return isinstance(value, py) and not isinstance(value, bool) if py is not bool else isinstance(value, bool)


class Validator(object):
    """A small JSON Schema draft-07 checker: enough for this one schema.

    Understands $ref, type, enum, const, required, properties,
    additionalProperties (false becomes a warning), items, minItems, maxItems,
    minLength, maxLength, minimum, maximum and pattern.
    """

    def __init__(self, schema):
        self.schema = schema
        self.errors = []
        self.warnings = []

    def _resolve(self, node):
        seen = 0
        while isinstance(node, dict) and "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/"):
                return node
            target = self.schema
            for part in ref[2:].split("/"):
                target = target.get(part, {})
            node = target
            seen += 1
            if seen > 20:
                break
        return node

    def err(self, path, message):
        self.errors.append("%s: %s" % (path or "(root)", message))

    def warn(self, path, message):
        self.warnings.append("%s: %s" % (path or "(root)", message))

    def check(self, value, schema, path=""):
        schema = self._resolve(schema)
        if not isinstance(schema, dict):
            return
        if "type" in schema:
            names = schema["type"]
            if isinstance(names, str):
                names = [names]
            if not any(_is_type(value, n) for n in names):
                self.err(path, "must be %s, got %s" % (" or ".join(names), type(value).__name__))
                return
        if "enum" in schema and value not in schema["enum"]:
            self.err(path, "must be one of %s, got %r" % (json.dumps(schema["enum"], ensure_ascii=False), value))
        if "const" in schema and value != schema["const"]:
            self.err(path, "must be %r, got %r" % (schema["const"], value))
        if isinstance(value, str):
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                self.err(path, "is %d characters, the limit is %d" % (len(value), schema["maxLength"]))
            if "minLength" in schema and len(value) < schema["minLength"]:
                self.err(path, "is empty or too short (minimum %d characters)" % schema["minLength"])
            if "pattern" in schema and not re.search(schema["pattern"], value):
                self.err(path, "does not match the required format %s (got %r)" % (schema["pattern"], value))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                self.err(path, "must be at least %s, got %s" % (schema["minimum"], value))
            if "maximum" in schema and value > schema["maximum"]:
                self.err(path, "must be at most %s, got %s" % (schema["maximum"], value))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                self.err(path, "needs at least %d entries, got %d" % (schema["minItems"], len(value)))
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                self.err(path, "allows at most %d entries, got %d" % (schema["maxItems"], len(value)))
            if "items" in schema:
                for i, item in enumerate(value):
                    self.check(item, schema["items"], "%s[%d]" % (path, i))
        if isinstance(value, dict):
            props = schema.get("properties") or {}
            for name in schema.get("required", []):
                if name not in value:
                    self.err(path, "is missing the required key '%s'" % name)
            for name, sub in value.items():
                if name in props:
                    self.check(sub, props[name], "%s.%s" % (path, name) if path else name)
                elif schema.get("additionalProperties") is False:
                    self.warn(path, "has an unexpected key '%s'; the renderers ignore it" % name)


def check_fixed_answers(cand, path, v, active=None):
    """The fixed form: every id of the active tier, once each, three states, nothing missing.

    `active` is the list of ids this report owes an answer to (active_fixed_ids). A missing
    one is a warning (an older report still validates, and --strict makes it an error, like
    every other warning); an id from a deeper tier than this run is welcome and never
    reported. The same id twice is an error: two answers to one question is not an answer.
    The state rules are the ones in report-schema.json.
    """
    active = list(FIXED_IDS) if active is None else active
    entries = cand.get("fixed_answers")
    if entries is None:
        v.warn(path, "has no fixed_answers, so the %d questions this report has to answer "
                     "are all missing. Fill references/fixed-questions.yaml: the gate "
                     "questions F1-F8 always, the listing questions F9-F14 whenever a page "
                     "was pasted, and the extended four F15-F18 in a deep check."
                     % len(active))
        return
    if not isinstance(entries, list):
        return
    seen = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        here = "%s.fixed_answers[%d]" % (path, i)
        eid = entry.get("id")
        if eid in seen:
            v.err(here, "answers %s a second time; one entry per question" % eid)
        seen.append(eid)
        status = entry.get("status")
        quote = (entry.get("quote") or "").strip()
        source = (entry.get("source") or "").strip()
        if status == "found":
            if not quote:
                v.err(here, "is 'found' but carries no quote. Copy the sentence you read the "
                            "answer in, or set the status to 'asked' or 'unknown'.")
            if not source:
                v.err(here, "is 'found' but names no source. Cite the id of the page or document "
                            "the quote came from.")
            elif source == "user":
                v.err(here, "is 'found' with source 'user'. What the user told you is 'asked'; "
                            "'found' means it is in writing somewhere you can cite.")
        elif status == "asked":
            if source != "user":
                v.err(here, "is 'asked' but its source is %r. An asked item is the user's own "
                            "answer, so the source is the literal \"user\"." % (entry.get("source"),))
        elif status == "unknown":
            if quote:
                v.err(here, "is 'unknown' but carries a quote. If you have the sentence, the "
                            "status is 'found'.")
    missing = [fid for fid in active if fid not in seen]
    if missing:
        v.warn(path + ".fixed_answers",
               "does not answer %s. This report runs at %d questions (references/"
               "fixed-questions.yaml, the `tiers` block): say 'unknown' rather than leaving "
               "one out. Answering more than the tier asks for is fine."
               % (", ".join(missing), len(active)))


def semantic_checks(data, v):
    """The rules that a schema cannot state, in the words the model needs."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return
    active = active_fixed_ids(data)
    ids = []
    for i, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue
        path = "candidates[%d]" % i
        cid = cand.get("id")
        if cid in ids:
            v.err(path, "reuses the id %r; every candidate needs its own id" % cid)
        ids.append(cid)
        axes = cand.get("axes")
        if isinstance(axes, list):
            axis_ids = [a.get("id") for a in axes if isinstance(a, dict)]
            if sorted([a for a in axis_ids if isinstance(a, int)]) != list(range(1, 13)):
                v.err(path + ".axes",
                      "must be exactly 12 entries with ids 1 to 12, each once. Got ids %s" % (axis_ids,))
        check_fixed_answers(cand, path, v, active)
        kq = cand.get("killer_questions")
        if isinstance(kq, list) and len(kq) > 2:
            v.err(path + ".killer_questions",
                  "has %d questions; at most 2 are allowed. Keep the two that would change the verdict." % len(kq))
        verdict = cand.get("verdict") or {}
        status = verdict.get("status")
        if status == "CONDITIONAL" and not verdict.get("conditions"):
            v.err(path + ".verdict", "status CONDITIONAL needs at least one entry in conditions")
        if status == "EDGE" and verdict.get("break_even_rent_pcm") in (None, ""):
            v.err(path + ".verdict", "status EDGE needs break_even_rent_pcm, the rent at which this becomes worth taking")
        if status == "KILL" and not verdict.get("fatal_axis"):
            v.err(path + ".verdict", "status KILL needs fatal_axis, the number of the axis that killed it")
        codes = set(verdict.get("reason_codes") or [])
        found = set(l.get("code") for l in (cand.get("landmines") or []) if isinstance(l, dict))
        for code in sorted(codes - found):
            v.warn(path + ".verdict.reason_codes",
                   "%s is given as a reason but there is no landmine entry with that code" % code)
        if len(candidates) > 1 and not cand.get("metrics"):
            v.warn(path, "has no metrics, so it will be blank in the side-by-side table")
        for j, qa in enumerate(cand.get("question_answers") or []):
            if not isinstance(qa, dict):
                continue
            if qa.get("when") == "compare" and len(candidates) < 2:
                v.warn("%s.question_answers[%d]" % (path, j),
                       "is a compare question, but this report has one candidate and no "
                       "side-by-side table to put it in. Answer it under the verdict instead: "
                       "set when to 'vet'.")

    if len(candidates) > 1:
        asked = {}
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            for qa in cand.get("question_answers") or []:
                if isinstance(qa, dict) and qa.get("when") == "compare" and qa.get("question"):
                    asked.setdefault(qa["question"], set()).add(cand.get("id"))
        for question in sorted(asked):
            silent = [c for c in ids if c not in asked[question]]
            if silent:
                v.warn("candidates.question_answers",
                       "%r is answered for some candidates but not for %s, so the comparison "
                       "row will have a hole. Answer it for every candidate, or say what you "
                       "tried." % (question[:60], ", ".join(repr(c) for c in silent)))

    comparison = data.get("comparison")
    if len(candidates) > 1:
        if not comparison:
            v.err("comparison", "is required when there is more than one candidate")
        else:
            ranked = [r.get("candidate_id") for r in (comparison.get("ranking") or []) if isinstance(r, dict)]
            for cid in ids:
                if cid not in ranked:
                    v.err("comparison.ranking", "does not rank candidate %r" % cid)
            for cid in ranked:
                if cid not in ids:
                    v.err("comparison.ranking", "ranks %r, which is not a candidate id" % cid)
    elif comparison:
        v.warn("comparison", "is present but there is only one candidate; it will not be shown")

    known = set()
    for i, src in enumerate(data.get("sources") or []):
        if not isinstance(src, dict):
            continue
        sid = src.get("id")
        if sid in known:
            v.err("sources[%d]" % i, "reuses the id %r" % sid)
        known.add(sid)

    def walk(node, path):
        if isinstance(node, dict):
            for key, sub in node.items():
                if key == "sources" and isinstance(sub, list) and all(isinstance(x, str) for x in sub):
                    for sid in sub:
                        if sid not in known:
                            v.warn(path, "cites source %r, which is not in the top-level sources list" % sid)
                else:
                    walk(sub, "%s.%s" % (path, key) if path else key)
        elif isinstance(node, list):
            for i, sub in enumerate(node):
                walk(sub, "%s[%d]" % (path, i))

    walk(data.get("candidates"), "candidates")
    walk(data.get("comparison"), "comparison")


def validate(data, schema):
    v = Validator(schema)
    v.check(data, schema, "")
    semantic_checks(data, v)
    return v.errors, v.warnings


# ------------------------------------------------ no source, no number ---
# The rule lives in report-schema.json as an `anyOf` on the two number
# definitions, so the required list is unchanged and an older report still
# validates. The schema is still the source of truth here: the keys below are
# read out of it, not hard-coded, and the fallback is only for a caller that
# renders without a schema file.
DEFAULT_SOURCE_KEYS = ["sources", "computed_by"]


def source_alternatives(schema, definition):
    """The keys the schema will accept as backing for one number."""
    node = ((schema or {}).get("definitions") or {}).get(definition) or {}
    keys = []
    for branch in node.get("anyOf") or []:
        for key in branch.get("required") or []:
            if key not in keys:
                keys.append(key)
    return keys or list(DEFAULT_SOURCE_KEYS)


def _backed(item, keys):
    """True when at least one of the keys carries something a reader can follow."""
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            if any(isinstance(x, str) and x.strip() for x in value):
                return True
        elif isinstance(value, str) and value.strip():
            return True
    return False


HAS_A_DIGIT = re.compile(r"[0-9]")


def states_a_number(text):
    """True when a sentence puts a figure in front of the reader.

    Prose carries numbers too: "the site runs until 2028", "5 weeks' deposit". An
    answer that states one has to name a source or a formula, like any other number.
    """
    return bool(text) and bool(HAS_A_DIGIT.search(text))


def unsourced_numbers(report, schema=None):
    """One entry per stated number with neither a source id nor a computed_by note.

    Walks the axis numbers, the comparison metrics and the answers to the user's own
    questions. A null value is not flagged: there is no number in it to source, and an
    answer with no figure in it is not flagged either. Each entry carries
    `candidate_id`, `loc` (the same locator the arithmetic chips use) and a `message`
    written for the model that has to fix it.
    """
    out = []
    axis_keys = source_alternatives(schema, "labelled_number")
    metric_keys = source_alternatives(schema, "measure")
    answer_keys = source_alternatives(schema, "question_answer")
    for i, cand in enumerate(report.get("candidates") or []):
        if not isinstance(cand, dict):
            continue
        cid = cand.get("id")
        for j, axis in enumerate(sorted([a for a in cand.get("axes") or [] if isinstance(a, dict)],
                                        key=lambda a: a.get("id") or 0)):
            aid = axis.get("id")
            for index, number in enumerate(axis.get("numbers") or []):
                if not isinstance(number, dict) or number.get("value") is None:
                    continue
                if _backed(number, axis_keys):
                    continue
                out.append({
                    "candidate_id": cid,
                    "loc": ("axis", aid, index),
                    "label": number.get("label") or "",
                    "keys": axis_keys,
                    "message": ('candidates[%d] %s, axis %s, number %d "%s": no source id and no '
                                "computed_by note. Cite a source from the top-level sources list, or "
                                "say in computed_by how you worked it out."
                                % (i, cid, aid, index + 1, number.get("label") or "")),
                })
        metrics = cand.get("metrics") or {}
        if not isinstance(metrics, dict):
            continue
        for key, _tid in METRIC_KEYS:
            measure = metrics.get(key)
            if not isinstance(measure, dict) or measure.get("value") is None:
                continue
            if _backed(measure, metric_keys):
                continue
            out.append({
                "candidate_id": cid,
                "loc": ("metrics", key),
                "label": key,
                "keys": metric_keys,
                "message": ("candidates[%d] %s, metrics.%s: no source id and no computed_by note. "
                            "Cite a source from the top-level sources list, or say in computed_by "
                            "how you worked it out." % (i, cid, key)),
            })
        for index, entry in enumerate(cand.get("fixed_answers") or []):
            if not isinstance(entry, dict) or not states_a_number(entry.get("answer")):
                continue
            status = entry.get("status")
            source = (entry.get("source") or "").strip()
            if status == "asked" or (status == "found" and source and source != "user"):
                continue
            out.append({
                "candidate_id": cid,
                "loc": ("fixed", index),
                "label": entry.get("id") or "",
                "keys": ["quote", "source"],
                "message": ('candidates[%d] %s, fixed_answers[%d] %s: the answer states a number '
                            "but the question is not answered from anything. A number needs status "
                            "'found' with the sentence quoted and a source id, or status 'asked' "
                            "because the user told you. An unknown carries no number."
                            % (i, cid, index, entry.get("id") or "?")),
            })
        for index, qa in enumerate(cand.get("question_answers") or []):
            if not isinstance(qa, dict) or not states_a_number(qa.get("answer")):
                continue
            if _backed(qa, answer_keys):
                continue
            out.append({
                "candidate_id": cid,
                "loc": ("question", index),
                "label": qa.get("question") or "",
                "keys": answer_keys,
                "message": ('candidates[%d] %s, question_answers[%d] "%s": the answer states a '
                            "number but names no source id and no computed_by note. Cite a source "
                            "from the top-level sources list, or say in computed_by how you worked "
                            "it out." % (i, cid, index, (qa.get("question") or "")[:60])),
            })
    return out


def unsourced_locations(report, schema=None):
    """{candidate id: set of locators} for the inline "no source" chips."""
    out = {}
    for gap in unsourced_numbers(report, schema):
        out.setdefault(gap["candidate_id"], set()).add(gap["loc"])
    return out


# ---------------------------------------------------- the configuration line ---
# Which rung of the escalation ladder the run finished on, and what that implies
# about the models. references/budget-modes.md, "The escalation ladder".
TIER_WORKERS = {"standard": "cheap", "breadth": "cheap", "lite": "cheap", "manual": "none"}


def configuration_line(data, L):
    """'Configuration: <tier> - <reason or default>; workers: <cheap>; judge: <model>'.

    The whole sentence is one glossary term with four slots, so a translator moves the
    words and the renderers only fill the holes. Missing tier prints as "not stated".
    """
    gb = data.get("generated_by") or {}
    unknown = L.label("ui.not_stated")
    tier = gb.get("tier")
    reason = (gb.get("escalation_reason") or "").strip()
    if not reason:
        reason = L.label("ui.tier_default") if tier else unknown
    return (L.label("ui.configuration")
            .replace("{tier}", tier or unknown)
            .replace("{reason}", reason)
            .replace("{workers}", TIER_WORKERS.get(tier, unknown))
            .replace("{judge}", (gb.get("model_name") or "").strip() or unknown))


# ------------------------------------------------------ arithmetic check ---
# The same formulas as scripts/calc.py, in the same order of operations. Small
# models get rent maths wrong, so every number that follows from a raw input is
# recomputed here and compared with what the model wrote.
WEEKS_PER_YEAR = 52.0
SQFT_PER_M2 = 10.7639
SIX_WEEK_ANNUAL_RENT = 50000.0      # annual rent at or above this: 6 weeks' deposit
TOL_PCT = 0.01                      # 1 per cent
TOL_FLOOR_PCM = 1.0                 # ...or GBP 1 on a figure in pounds per month
TOL_FLOOR_RATE = 0.01               # ...or 1 penny on a figure in pounds per square foot

# Every formula in words, exactly as calc.py computes it.
FORMULAS = {
    "weekly_rent": "weekly rent = monthly rent × 12 ÷ 52",
    "deposit_cap": "deposit cap = 5 weeks' rent when the year's rent is under £50,000, "
                   "6 weeks at or above it (Tenant Fees Act 2019)",
    "holding_deposit_cap": "holding deposit cap = one week's rent",
    "all_in": "total monthly cost = rent + bills + council tax + broadband",
    "price_per_sqft": "£ per square foot = rent ÷ (floor area in m² × 10.7639)",
    "price_per_sqft_sqft": "£ per square foot = rent ÷ floor area in square feet",
    "break_even_rent": "break-even rent = your total monthly budget − bills − council tax",
    "bridge_total": "bridge total = weeks × weekly rate + months × total monthly cost",
}


def _norm(text):
    """Lower case, punctuation to spaces: 'Rent per sq. ft' -> 'rent per sq ft'."""
    return re.sub(r"[^a-z0-9]+", " ", str(text if text is not None else "").lower()).strip()


def _num(value):
    """The first number in a value, or None. '£2,528 a month' -> 2528.0."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _has(text, *groups):
    """True when the text contains at least one word from every group."""
    norm = _norm(text)
    return all(any(word in norm for word in group) for group in groups)


BRIDGE_WORDS = ["bridge", "bridging", "temporary", "airbnb", "hotel", "hostel"]
MONEY_WORDS = ["cost", "rent", "deposit", "price", "fee", "total", "rate", "bill"]


def _money(entry):
    """Money, or a count? A stated unit decides; an empty unit falls back to the label."""
    raw = entry.get("unit") or ""
    unit = _norm(raw)
    if "\u00a3" in raw or "gbp" in unit or "pound" in unit or "pcm" in unit:
        return True
    if unit:
        return False
    return any(word in _norm(entry.get("label")) for word in MONEY_WORDS)


def _written_numbers(cand):
    """Every number the model wrote under an axis, with where it came from."""
    out = []
    for axis in cand.get("axes") or []:
        if not isinstance(axis, dict):
            continue
        for index, number in enumerate(axis.get("numbers") or []):
            if not isinstance(number, dict):
                continue
            label = number.get("label") or ""
            unit = number.get("unit") or ""
            out.append({"label": label, "unit": unit, "value": _num(number.get("value")),
                        "text": "%s %s" % (label, unit),
                        "where": "axis %s · %s" % (axis.get("id"), label),
                        "loc": {"kind": "axis", "axis": axis.get("id"), "index": index}})
    return out


def _pick(numbers, want, avoid=(), money=None):
    """The first written number whose label+unit matches every group in want."""
    for entry in numbers:
        if entry["value"] is None:
            continue
        if avoid and _has(entry["text"], avoid):
            continue
        if money is not None and _money(entry) != money:
            continue
        if _has(entry["text"], *want):
            return entry
    return None


def _pick_all(numbers, want, avoid=(), money=None):
    out = []
    for entry in numbers:
        if entry["value"] is None:
            continue
        if avoid and _has(entry["text"], avoid):
            continue
        if money is not None and _money(entry) != money:
            continue
        if _has(entry["text"], *want):
            out.append(entry)
    return out


def _source(value, where, loc):
    return None if value is None else {"value": value, "where": where, "loc": loc}


def _check(field, label, formula, recomputed, source, kind="equal", floor=TOL_FLOOR_PCM,
           unit="GBP per month", label_id=None, weeks=None):
    """One row of the arithmetic check: what the model wrote against the formula."""
    tolerance = max(floor, abs(recomputed) * TOL_PCT)
    model = source["value"] if source else None
    if model is None:
        delta, ok = None, True          # nothing written to contradict the formula
    else:
        delta = round(model - recomputed, 4)
        ok = abs(delta) <= tolerance if kind == "equal" else model <= recomputed + tolerance
    return {"field": field, "label": label, "label_id": label_id, "weeks": weeks,
            "formula": formula, "unit": unit, "kind": kind,
            "model_value": model, "recomputed": round(recomputed, 2), "delta": delta, "ok": ok,
            "tolerance": round(tolerance, 4),
            "where": source["where"] if source else None,
            "loc": source["loc"] if source else None}


def _epc_area(cand, numbers):
    """The indoor floor area, in square feet, and where it came from.

    Preference: an axis number whose label says indoor / internal / EPC /
    certificate, then any floor-area number that is not the advertised one, then
    the 'observed' text of a hard filter about floor area. Square metres are
    turned into square feet with the calc.py factor.
    """
    def as_sqft(value, unit):
        raw = (unit or "").lower()
        if "m²" in raw or "m2" in raw or "sq m" in raw or "square met" in raw:
            return value * SQFT_PER_M2, "m²"
        if "ft" in raw or "foot" in raw or "feet" in raw:
            return value, "square feet"
        return None, None

    avoid = ["advertised", "listing", "brochure", "floor plan", "balcony", "external", "gross", "claimed"]
    ranked = []
    for entry in numbers:
        if entry["value"] is None or _has(entry["text"], ["per"]):
            continue
        if not _has(entry["text"], ["area", "size", "floor space"]):
            continue
        if _has(entry["text"], avoid):
            continue
        sqft, basis = as_sqft(entry["value"], entry["unit"])
        if sqft is None:
            continue
        rank = 0 if _has(entry["text"], ["indoor", "internal", "epc", "certificate"]) else 1
        ranked.append((rank, sqft, basis, entry["where"]))
    for filt in cand.get("hard_filters") or []:
        if not isinstance(filt, dict):
            continue
        if not _has("%s %s" % (filt.get("name"), filt.get("requirement")), ["area", "size"]):
            continue
        observed = filt.get("observed") or ""
        value = _num(observed)
        if value is None:
            continue
        sqft, basis = as_sqft(value, observed)
        if sqft is None:
            continue
        ranked.append((2, sqft, basis, "hard filter · %s" % (filt.get("name") or "")))
    if not ranked:
        return None
    ranked.sort(key=lambda row: row[0])
    return {"sqft": ranked[0][1], "basis": ranked[0][2], "where": ranked[0][3]}


def _ceiling(cand, profile):
    """The user's all-in ceiling: the profile first, then a hard filter that quotes it."""
    value = _num(profile.get("all_in_pcm_ceiling"))
    if value is not None:
        return value
    for filt in cand.get("hard_filters") or []:
        if not isinstance(filt, dict):
            continue
        text = "%s %s" % (filt.get("name"), filt.get("requirement"))
        if _has(text, ["total", "all in", "ceiling"], ["cost", "month", "pcm"]):
            got = _num(filt.get("requirement"))
            if got is not None:
                return got
    return None


def recompute_candidate(cand, profile):
    """Recompute every derivable number for one candidate. See recompute()."""
    costs = cand.get("costs") if isinstance(cand.get("costs"), dict) else {}
    metrics = cand.get("metrics") if isinstance(cand.get("metrics"), dict) else {}
    numbers = _written_numbers(cand)
    checks = []

    rent = _num(costs.get("rent_pcm"))
    if rent is None:
        got = _pick(numbers, [["rent"]], avoid=BRIDGE_WORDS + ["week", "square", "sqft", "sq ft", "deposit"])
        rent = got["value"] if got else None

    if rent is not None:
        weekly = rent * 12.0 / WEEKS_PER_YEAR
        checks.append(_check(
            "weekly_rent", "Weekly rent", FORMULAS["weekly_rent"], weekly,
            _pick(numbers, [["week"], ["rent", "rate"]], avoid=BRIDGE_WORDS + ["deposit"]),
            unit="GBP per week", label_id="ui.arith_weekly_rent"))
        weeks_cap = 5 if rent * 12.0 < SIX_WEEK_ANNUAL_RENT else 6
        checks.append(_check(
            "deposit_cap", "Deposit, legal maximum (%d weeks)" % weeks_cap, FORMULAS["deposit_cap"],
            weeks_cap * weekly,
            _pick(numbers, [["deposit"]], avoid=BRIDGE_WORDS + ["holding", "protection", "scheme"], money=True),
            kind="cap", unit="GBP", label_id="ui.arith_deposit_cap", weeks=weeks_cap))
        checks.append(_check(
            "holding_deposit_cap", "Holding deposit, legal maximum (1 week)", FORMULAS["holding_deposit_cap"],
            weekly, _pick(numbers, [["holding"], ["deposit", "fee"]], money=True), kind="cap", unit="GBP",
            label_id="ui.arith_holding_deposit_cap"))

    council_tax = _num(costs.get("council_tax")) or 0.0
    broadband_entry = _pick(numbers, [["broadband", "internet"]], money=True)
    broadband = broadband_entry["value"] if broadband_entry else 0.0
    all_in = {}
    total_words = ["all in", "total", "monthly cost", "cost per month", "everything"]
    for name, key, extra, ban in (
            ("low", "bills_low", ["low", "best", "mild", "careful"], ["stress", "worst"]),
            ("planning", "bills_planning", None, ["stress", "worst", "low", "best", "mild"]),
            ("stress", "bills_stress", ["stress", "worst", "cold", "bad winter"], ["low", "best", "mild"])):
        bills = _num(costs.get(key))
        if rent is None or bills is None:
            continue
        total = rent + bills + council_tax + broadband
        all_in[name] = total
        want = [total_words] if extra is None else [total_words, extra]
        sources = []
        if name == "planning":
            sources.append(_source(_num(costs.get("all_in_planning")), "costs.all_in_planning",
                                   {"kind": "costs", "key": "all_in_planning"}))
            for index, filt in enumerate(cand.get("hard_filters") or []):
                if not isinstance(filt, dict):
                    continue
                if _has("%s %s" % (filt.get("name"), filt.get("requirement")), total_words, ["cost", "month"]):
                    sources.append(_source(_num(filt.get("observed")),
                                           "hard filter · %s" % (filt.get("name") or ""),
                                           {"kind": "hard_filter", "index": index}))
        for entry in _pick_all(numbers, want, avoid=BRIDGE_WORDS + ban, money=True):
            sources.append(_source(entry["value"], entry["where"], entry["loc"]))
        sources = [s for s in sources if s] or [None]
        label = {"low": "All-in cost, mild month", "planning": "All-in cost, the planning number",
                 "stress": "All-in cost, cold month"}[name]
        for source in sources:
            checks.append(_check("all_in_" + name, label, FORMULAS["all_in"], total, source,
                                 label_id="ui.arith_all_in_" + name))

    area = _epc_area(cand, numbers)
    if rent is not None and area and area["sqft"]:
        rate = rent / area["sqft"]
        formula = FORMULAS["price_per_sqft"] if area["basis"] == "m²" else FORMULAS["price_per_sqft_sqft"]
        sources = []
        measure = metrics.get("price_per_sqft_epc")
        if isinstance(measure, dict):
            sources.append(_source(_num(measure.get("value")), "metrics.price_per_sqft_epc",
                                   {"kind": "metrics", "key": "price_per_sqft_epc"}))
        for entry in _pick_all(numbers, [["per square", "per sq", "psf", "sqft"]], avoid=BRIDGE_WORDS):
            sources.append(_source(entry["value"], entry["where"], entry["loc"]))
        sources = [s for s in sources if s] or [None]
        for source in sources:
            checks.append(_check("price_per_sqft", "Rent per square foot", formula, rate, source,
                                 floor=TOL_FLOOR_RATE, unit="GBP per square foot",
                                 label_id="ui.arith_price_per_sqft"))

    ceiling = _ceiling(cand, profile)
    bills_planning = _num(costs.get("bills_planning"))
    if ceiling is not None and bills_planning is not None:
        break_even = ceiling - bills_planning - council_tax
        entry = _pick(numbers, [["break even", "breakeven"]], money=True)
        checks.append(_check("break_even_rent", "Break-even rent against your ceiling",
                             FORMULAS["break_even_rent"], break_even,
                             _source(entry["value"], entry["where"], entry["loc"]) if entry else None,
                             label_id="ui.arith_break_even"))

    weeks = _pick(numbers, [BRIDGE_WORDS, ["week"]], avoid=["rate", "cost"], money=False)
    weekly_rate = _pick(numbers, [BRIDGE_WORDS, ["week"]], money=True)
    months = _pick(numbers, [["month"], ["tenancy", "remaining", "rest of", "after"]], money=False)
    if weeks and weekly_rate and months and all_in.get("planning") is not None:
        total = weeks["value"] * weekly_rate["value"] + months["value"] * all_in["planning"]
        entry = _pick(numbers, [BRIDGE_WORDS, ["total", "twelve", "12 month", "year"]], money=True)
        checks.append(_check("bridge_total", "Bridging plus tenancy, twelve months",
                             FORMULAS["bridge_total"], total,
                             _source(entry["value"], entry["where"], entry["loc"]) if entry else None,
                             unit="GBP", label_id="ui.arith_bridge_total"))

    return {"arithmetic_ok": all(c["ok"] for c in checks), "checks": checks}


def recompute(report):
    """Recompute every derivable number in the report and compare it with the model's.

    Writes the result to each candidate as `arithmetic_check` (the renderer owns
    that key; a model may leave it out) and returns the same list, one entry per
    candidate: {"candidate_id", "arithmetic_ok", "checks"}.

    What is recomputed, and where the model's own figure is looked for. Labels are
    lower-cased and stripped of punctuation before matching, so 'Rent per sq. ft'
    and 'rent per sq ft' are the same string. A figure with no match anywhere is
    still listed, as computed only; it can never fail.

      weekly_rent          rent_pcm x 12 / 52.
                           Model: an axis number whose label has 'week' and
                           'rent' or 'rate' (not deposit, not bridging).
      deposit_cap          5 weeks' rent under GBP 50,000 a year, 6 at or above.
                           Model: an axis number with 'deposit' (not 'holding',
                           'protection', 'scheme'). Checked as a CAP: less is fine,
                           more is illegal.
      holding_deposit_cap  one week's rent. Model: 'holding' + 'deposit'/'fee'. CAP.
      all_in_low |
      all_in_planning |
      all_in_stress        rent + the matching bills figure + council tax +
                           broadband (broadband only when a number says so; the
                           schema already folds it into bills). Model, for the
                           planning number: costs.all_in_planning, the 'observed'
                           text of a hard filter about total monthly cost, and any
                           axis number saying 'all in' / 'total' / 'monthly cost'.
                           Low and stress additionally need 'low', 'best', 'mild'
                           or 'stress', 'worst', 'cold' in the label.
      price_per_sqft       rent / floor area. The area is the indoor EPC area: an
                           axis number saying 'area' or 'size' that is not the
                           advertised one, preferring 'indoor', 'internal', 'EPC'
                           or 'certificate', else a floor-area hard filter's
                           'observed' text. Square metres are multiplied by
                           10.7639 first. Model: metrics.price_per_sqft_epc and any
                           axis number saying 'per square', 'per sq' or 'psf'.
      break_even_rent      profile_snapshot.all_in_pcm_ceiling (else the ceiling
                           quoted in a hard filter) - bills_planning - council tax.
                           Model: an axis number saying 'break even'.
                           verdict.break_even_rent_pcm is deliberately NOT compared:
                           that field is the rent at which the flat becomes worth
                           taking, a judgement, not this formula.
      bridge_total         weeks x weekly rate + months x all-in, computed only
                           when an axis number gives bridging weeks, a bridging
                           weekly rate and a number of tenancy months.
                           Model: a bridging number saying 'total', 'year' or
                           '12 month'.

    Tolerance: 1 per cent of the recomputed figure, or GBP 1, whichever is larger.
    For a figure in pounds per square foot the floor is 1 penny instead of GBP 1,
    because GBP 1 there is a quarter of the whole number.
    """
    profile = report.get("profile_snapshot") if isinstance(report.get("profile_snapshot"), dict) else {}
    out = []
    for cand in report.get("candidates") or []:
        if not isinstance(cand, dict):
            continue
        result = recompute_candidate(cand, profile)
        cand["arithmetic_check"] = {"arithmetic_ok": result["arithmetic_ok"], "checks": result["checks"]}
        entry = {"candidate_id": cand.get("id")}
        entry.update(result)
        out.append(entry)
    return out


def arithmetic_warnings(report):
    """One WARNING line per number that does not follow from the formula."""
    lines = []
    for i, entry in enumerate(recompute(report)):
        for check in entry["checks"]:
            if check["ok"]:
                continue
            lines.append(
                "candidates[%d] %s: %s %s: model said %s, formula gives %s (%s)"
                % (i, entry["candidate_id"], check["where"] or check["field"],
                   "is above the legal cap" if check["kind"] == "cap" else "does not match",
                   fmt_value(check["model_value"]), fmt_value(check["recomputed"]), check["formula"]))
    return lines


def bad_locations(report):
    """{candidate id: {locator: check}} for every number that failed, for the inline chips."""
    out = {}
    for entry in recompute(report):
        marks = {}
        for check in entry["checks"]:
            loc = check.get("loc")
            if check["ok"] or not loc:
                continue
            if loc["kind"] == "axis":
                marks[("axis", loc.get("axis"), loc.get("index"))] = check
            elif loc["kind"] == "hard_filter":
                marks[("hard_filter", loc.get("index"))] = check
            else:
                marks[(loc["kind"], loc.get("key"))] = check
        out[entry["candidate_id"]] = marks
    return out


def money_exact(value):
    """Money for a maths check: whole pounds when it is whole, pence when it is not."""
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    if abs(value - round(value)) < 0.005:
        return "\u00a3{:,.0f}".format(value)
    return "\u00a3{:,.2f}".format(value)


def check_label(check, L):
    """The figure's name in the reader's language, with the week count where there is one."""
    text = L.label(check.get("label_id") or "", check["label"])
    if check.get("weeks") and check.get("label_id"):
        text = "%s (%d %s)" % (text, check["weeks"], L.label("ui.arith_weeks"))
    return text


def check_status(check, L):
    """'matches', or 'does not match: model said X, formula gives Y', in the reader's language."""
    gives = "%s %s" % (L.label("ui.arith_formula_gives"), money_exact(check["recomputed"]))
    if check["model_value"] is None:
        return "%s; %s" % (L.label("ui.arith_not_stated"), gives)
    if check["ok"]:
        return "%s (%s %s)" % (L.label("ui.arith_matches"), L.label("ui.arith_model_said"),
                               money_exact(check["model_value"]))
    verdict = L.label("ui.arith_over_cap") if check["kind"] == "cap" else L.label("ui.arith_mismatch")
    return "%s: %s %s, %s" % (verdict, L.label("ui.arith_model_said"),
                              money_exact(check["model_value"]), gives)


def check_sentence(check, L):
    """The one-line tooltip behind an inline warning chip."""
    return "%s \u2014 %s \u2014 %s" % (check_label(check, L), check_status(check, L), check["formula"])


# ------------------------------------------------------------------ helpers ---
def esc(text):
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt_value(value, unit=None):
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = ("%.2f" % value).rstrip("0").rstrip(".")
    elif isinstance(value, int):
        text = "{:,}".format(value)
    else:
        text = str(value)
    if unit:
        text = "%s %s" % (text, unit)
    return text


def money(value):
    if value is None:
        return None
    return "\u00a3{:,.0f}".format(value) if isinstance(value, (int, float)) else str(value)


def footer_text(data):
    gb = data.get("generated_by") or {}
    return FOOTER_TEMPLATE.format(version=gb.get("version") or "unknown",
                                  url=gb.get("source_url") or DEFAULT_SOURCE_URL)


def candidate_name(cand):
    return ((cand.get("identity") or {}).get("display_name")
            or cand.get("id") or "?")


def staged_questions(cand, when):
    """(index, entry) for the user's own questions answered at one stage, in report order.

    The index is the position in `question_answers`, so an answer with an unsourced
    number can be marked with the same ("question", index) locator the chips use.
    """
    out = []
    for index, qa in enumerate(cand.get("question_answers") or []):
        if isinstance(qa, dict) and qa.get("when") == when:
            out.append((index, qa))
    return out


def trigger_state(qa, L):
    """Did the question's trigger fire? A question with no trigger is asked every time."""
    fired = qa.get("triggered")
    if fired is None:
        return L.label("ui.no_trigger")
    return L.label("ui.trigger_fired") if fired else L.label("ui.trigger_not_fired")


def only_you_asks(cand, L):
    """(label, request) lines for section 8, in the order the reader needs them.

    First the axes graded unknown, each named and followed by what was tried; then what
    the report itself asked for; and if it asked for nothing, the four standard requests.
    Every line is a request to the person who will stand there, never a list of failures.
    """
    out = []
    for axis in sorted(cand.get("axes") or [], key=lambda a: a.get("id") or 0):
        if not isinstance(axis, dict) or axis.get("evidence_class") != "U":
            continue
        tid = "axis.%s" % axis.get("id")
        text = (axis.get("finding") or "").strip() or L.plain(tid)
        out.append((L.label(tid, axis.get("name", "")), text))
    supplied = [line for line in (cand.get("only_you_can_tell") or [])
                if isinstance(line, str) and line.strip()]
    for line in supplied or [L.label(tid) for tid in ONLY_YOU_DEFAULTS]:
        out.append(("", line))
    return out


def profile_rows(snapshot, L):
    rows = []
    seen = set()
    for key in PROFILE_KEYS:
        if key in snapshot:
            seen.add(key)
            rows.append((key, snapshot[key]))
    for key in sorted(snapshot):
        if key not in seen:
            rows.append((key, snapshot[key]))
    out = []
    for key, value in rows:
        if value is None or value == [] or value == "":
            continue
        if isinstance(value, list):
            text = "; ".join(str(x) for x in value)
        elif isinstance(value, bool):
            text = L.label("ui.yes") if value else L.label("ui.no")
        else:
            text = str(value)
        out.append((key.replace("_", " "), text))
    return out


# --------------------------------------------------------------------- CSS ---
CSS = """
:root{
  --bg:#f6f6f4; --panel:#ffffff; --ink:#17181a; --muted:#5b6068; --line:#e0e0dc;
  --chip:#eceef0; --chip-ink:#3c4148; --accent:#245a86; --thead:#f0f1f2;
  --pass:#1c6b45; --pass-bg:#e6f2eb; --edge:#7a5600; --edge-bg:#faf1dd;
  --cond:#1d5581; --cond-bg:#e6eff7; --kill:#9c1f1f; --kill-bg:#fbe9e9;
  --ok:#1c6b45; --bad:#9c1f1f; --unk:#6b6b6b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#15171a; --panel:#1d2024; --ink:#e9eaec; --muted:#a3a9b2; --line:#31353b;
    --chip:#282d33; --chip-ink:#c4cad2; --accent:#7cb2dd; --thead:#242930;
    --pass:#6cc294; --pass-bg:#16301f; --edge:#dcb85f; --edge-bg:#332a12;
    --cond:#7cb2dd; --cond-bg:#152735; --kill:#e88b8b; --kill-bg:#331818;
    --ok:#6cc294; --bad:#e88b8b; --unk:#9aa0a8;
  }
}
:root[data-theme="dark"]{
  --bg:#15171a; --panel:#1d2024; --ink:#e9eaec; --muted:#a3a9b2; --line:#31353b;
  --chip:#282d33; --chip-ink:#c4cad2; --accent:#7cb2dd; --thead:#242930;
  --pass:#6cc294; --pass-bg:#16301f; --edge:#dcb85f; --edge-bg:#332a12;
  --cond:#7cb2dd; --cond-bg:#152735; --kill:#e88b8b; --kill-bg:#331818;
  --ok:#6cc294; --bad:#e88b8b; --unk:#9aa0a8;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",
  "Noto Sans TC","Noto Sans SC","PingFang TC","Microsoft JhengHei",Arial,sans-serif;}
.wrap{max-width:1100px;margin:0 auto;padding:24px 18px 64px}
h1{font-size:26px;line-height:1.25;margin:0 0 4px}
h2{font-size:20px;margin:38px 0 6px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:17px;margin:22px 0 6px}
h4{font-size:15px;margin:14px 0 4px}
p{margin:8px 0}
small,.sub{color:var(--muted);font-size:13px;line-height:1.45}
.lede{color:var(--muted);font-size:14px;margin:0 0 2px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:14px 16px;margin:12px 0}
.vcard{border-left:6px solid var(--line)}
.vcard.PASS{border-left-color:var(--pass);background:var(--pass-bg)}
.vcard.EDGE{border-left-color:var(--edge);background:var(--edge-bg)}
.vcard.CONDITIONAL{border-left-color:var(--cond);background:var(--cond-bg)}
.vcard.KILL{border-left-color:var(--kill);background:var(--kill-bg)}
.status{display:inline-block;font-weight:700;letter-spacing:.02em;padding:3px 10px;
  border-radius:999px;font-size:13px;border:1px solid currentColor}
.status.PASS{color:var(--pass)} .status.EDGE{color:var(--edge)}
.status.CONDITIONAL{color:var(--cond)} .status.KILL{color:var(--kill)}
.headline{font-size:18px;font-weight:600;margin:10px 0 6px}
.chips{margin:6px 0 0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-block;background:var(--chip);color:var(--chip-ink);border-radius:6px;
  padding:2px 8px;font-size:12.5px;border:1px solid var(--line);cursor:help}
.chip.ev-G{border-color:var(--ok)} .chip.ev-U{border-color:var(--unk)}
.chip.maths{background:var(--kill-bg);color:var(--kill);border-color:var(--kill);font-weight:600}
.chip.nosource{color:var(--edge);border-color:var(--edge)}
.arith td.bad{color:var(--kill);font-weight:600} .arith td.good{color:var(--ok)}
.chip.ev-S,.chip.ev-I{border-color:var(--edge)} .chip.ev-C{border-color:var(--accent)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);
  border-radius:10px;background:var(--panel);margin:10px 0}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--line)}
th{background:var(--thead);font-weight:600;white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
td.num{white-space:nowrap}
.meaning{border-bottom:1px dotted var(--muted);cursor:help}
.ok{color:var(--ok);font-weight:600} .bad{color:var(--bad);font-weight:600}
.unk{color:var(--unk);font-weight:600}
ul,ol{margin:8px 0;padding-left:22px} li{margin:4px 0}
.q{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:8px;padding:10px 12px;margin:8px 0}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;
  background:var(--chip);padding:1px 5px;border-radius:4px;word-break:break-all}
a{color:var(--accent)}
.foot{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px}
.rev{border-left:3px solid var(--line);padding-left:10px;margin:6px 0;font-style:italic}
.axis{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
.axis:first-of-type{border-top:none}
@media (max-width:640px){
  body{font-size:15px} .wrap{padding:16px 12px 48px} h1{font-size:22px} h2{font-size:18px}
}
@media print{
  body{background:#fff;color:#000;font-size:11pt}
  .wrap{max-width:none;padding:0}
  .card,.tw,.q{break-inside:avoid;page-break-inside:avoid}
  .tw{overflow:visible} table{min-width:0}
  h2{page-break-after:avoid} a{color:#000;text-decoration:none}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:9pt;color:#444}
}
"""


# -------------------------------------------------------------------- HTML ---
class HtmlRenderer(object):
    def __init__(self, data, L, schema=None):
        self.d = data
        self.L = L
        self.out = []
        self.bad = bad_locations(data)      # also fills candidate.arithmetic_check
        self.nosource = unsourced_locations(data, schema)
        self.fixed = fixed_questions()      # only for the `why` line on an unknown row

    def w(self, text=""):
        self.out.append(text)

    # -- small pieces --------------------------------------------------------
    def chip_evidence(self, ec):
        if not ec:
            return ""
        tid = "evidence." + ec
        return '<span class="chip ev-%s" title="%s">%s</span>' % (
            esc(ec), esc(self.L.tip(tid)), esc(self.L.label(tid, ec)))

    def chip_maths(self, check):
        """A visible warning chip on a number that does not follow from the formula."""
        if not check:
            return ""
        return ' <span class="chip maths" title="%s">%s</span>' % (
            esc(check_sentence(check, self.L)), esc(self.L.label("ui.check_the_maths")))

    def chip_nosource(self, missing):
        """A visible chip on a number that names no source and no formula."""
        if not missing:
            return ""
        return ' <span class="chip nosource" title="%s">%s</span>' % (
            esc(self.L.plain("ui.no_source")), esc(self.L.label("ui.no_source")))

    def measure_cell(self, mea, check=None, missing=False):
        if not isinstance(mea, dict):
            return '<td>%s</td>' % esc(self.L.label("ui.no_data"))
        value = fmt_value(mea.get("value"), mea.get("unit"))
        if value is None:
            value = self.L.label("ui.no_data")
        bits = ['<span class="meaning" title="%s">%s</span>' % (esc(mea.get("meaning") or ""), esc(value))]
        if check:
            bits.append(self.chip_maths(check))
        bits.append(self.chip_nosource(missing))
        if mea.get("compared_to"):
            bits.append('<br><small>%s</small>' % esc(mea["compared_to"]))
        if mea.get("evidence_class"):
            bits.append('<br>%s' % self.chip_evidence(mea["evidence_class"]))
        return "<td>%s</td>" % "".join(bits)

    def section(self, index, term_id, anchor):
        L = self.L
        self.w('<h2 id="%s">%d. %s</h2>' % (anchor, index, esc(L.label(term_id))))
        gloss = L.plain(term_id)
        if gloss:
            self.w('<p class="lede">%s</p>' % esc(gloss))

    def questions_block(self, cand, when, title=None):
        """The user's own questions, answered, at the stage where they are read."""
        L = self.L
        rows = staged_questions(cand, when)
        if not rows:
            return
        gaps = self.nosource.get(cand.get("id")) or set()
        if title:
            self.w('<p class="sub"><strong>%s</strong></p>' % esc(title))
        for index, qa in rows:
            self.w('<div class="q"><strong>%s</strong>' % esc(qa.get("question", "")))
            self.w("<p>%s%s</p>" % (esc(qa.get("answer", "")),
                                    self.chip_nosource(("question", index) in gaps)))
            bits = [self.chip_evidence(qa.get("evidence_class")), esc(trigger_state(qa, L))]
            if qa.get("trigger"):
                bits.append(esc(qa["trigger"]))
            self.w('<p class="sub">%s</p></div>' % " \u00b7 ".join(b for b in bits if b))

    def table(self, headers, rows):
        self.w('<div class="tw"><table><thead><tr>')
        for head in headers:
            if isinstance(head, tuple):
                self.w('<th title="%s">%s</th>' % (esc(head[1]), esc(head[0])))
            else:
                self.w("<th>%s</th>" % esc(head))
        self.w("</tr></thead><tbody>")
        for row in rows:
            self.w("<tr>%s</tr>" % "".join(row))
        self.w("</tbody></table></div>")

    # -- sections ------------------------------------------------------------
    def s1_verdict(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            verdict = cand.get("verdict") or {}
            status = verdict.get("status", "")
            self.w('<div class="card vcard %s">' % esc(status))
            self.w('<h3>%s</h3>' % esc(candidate_name(cand)))
            identity = cand.get("identity") or {}
            line = " \u00b7 ".join([x for x in (identity.get("address"), identity.get("postcode"),
                                                identity.get("floor")) if x])
            if line:
                self.w('<p class="sub">%s</p>' % esc(line))
            self.w('<p><span class="status %s" title="%s">%s</span></p>' % (
                esc(status), esc(L.tip("verdict." + status)), esc(L.label("verdict." + status, status))))
            self.w('<p class="headline">%s</p>' % esc(verdict.get("headline", "")))
            codes = verdict.get("reason_codes") or []
            if codes:
                self.w('<p class="sub">%s</p><ul class="chips">' % esc(L.label("ui.reason_codes")))
                for code in codes:
                    self.w('<li class="chip" title="%s">%s</li>' % (
                        esc(L.plain("landmine." + code)), esc(L.label("landmine." + code, code))))
                self.w("</ul>")
            if verdict.get("break_even_rent_pcm") is not None:
                self.w('<p><strong>%s:</strong> %s <small>%s</small></p>' % (
                    esc(L.label("ui.break_even_rent")), esc(money(verdict["break_even_rent_pcm"])),
                    esc(L.plain("ui.break_even_rent"))))
            if verdict.get("fatal_axis"):
                axis_id = verdict["fatal_axis"]
                self.w('<p><strong>%s:</strong> %s</p>' % (
                    esc(L.label("ui.fatal_axis")),
                    esc("%d. %s" % (axis_id, L.label("axis.%d" % axis_id)))))
            if verdict.get("conditions"):
                self.w("<p><strong>%s</strong></p><ol>" % esc(L.label("ui.conditions")))
                for cond in verdict["conditions"]:
                    self.w("<li>%s</li>" % esc(cond))
                self.w("</ol>")
            self.questions_block(cand, "vet", L.label("ui.your_questions"))
            self.w("</div>")

    def s2_hard_filters(self):
        L = self.L
        marks = {True: ('ok', "ui.pass"), False: ('bad', "ui.fail"), "unknown": ('unk', "ui.unknown")}
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            bad = self.bad.get(cand.get("id")) or {}
            gaps = self.nosource.get(cand.get("id")) or set()
            rows = []
            for index, hf in enumerate(cand.get("hard_filters") or []):
                css, tid = marks.get(hf.get("pass"), ('unk', "ui.unknown"))
                rows.append([
                    "<td><strong>%s</strong></td>" % esc(hf.get("name", "")),
                    "<td>%s</td>" % esc(hf.get("requirement", "")),
                    "<td>%s%s</td>" % (esc(hf.get("observed", "")),
                                       self.chip_maths(bad.get(("hard_filter", index)))),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        css, esc(L.plain(tid)), esc(L.label(tid))),
                    "<td>%s</td>" % self.chip_evidence(hf.get("evidence_class")),
                ])
            for index, qa in staged_questions(cand, "filter"):
                rows.append([
                    "<td><strong>%s</strong></td>" % esc(qa.get("question", "")),
                    "<td>%s</td>" % esc(qa.get("trigger") or "\u2014"),
                    "<td>%s%s</td>" % (esc(qa.get("answer", "")),
                                       self.chip_nosource(("question", index) in gaps)),
                    '<td class="num">%s</td>' % esc(trigger_state(qa, L)),
                    "<td>%s</td>" % self.chip_evidence(qa.get("evidence_class")),
                ])
            if not rows:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            self.table(["", L.label("ui.requirement"), L.label("ui.observed"),
                        L.label("ui.result"), L.label("ui.evidence")], rows)

    def s3_fixed(self):
        """The fixed form, per candidate: the questions this run answers, three states each.

        Drawn in its three groups - the gate every flat gets, the listing questions a
        pasted page answers, the four extras a deep check has time for - so a reader who
        sees eight rather than eighteen can see which group is missing and why.
        """
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            self.w('<p class="sub">%s</p>' % esc(L.label("ui.fixed_lead")))
            self.w('<p class="sub">%s</p>' % esc(L.label("ui.fixed_tiers")))
            gaps = self.nosource.get(cand.get("id")) or set()
            groups = fixed_group_rows(cand, self.fixed)
            if not groups:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            for label, entries in groups:
                rows = []
                for index, entry in entries:
                    tid = "fixed." + (entry.get("id") or "")
                    css, state = FIXED_STATES.get(entry.get("status"), FIXED_STATES["unknown"])
                    quote = entry.get("quote") or ""
                    rows.append([
                        '<td><strong><span class="meaning" title="%s">%s</span></strong></td>' % (
                            esc(L.plain(tid)), esc(L.label(tid, entry.get("id") or ""))),
                        '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                            css, esc(L.plain(state)), esc(L.label(state))),
                        "<td>%s%s</td>" % (esc(fixed_answer_text(entry, self.fixed)),
                                           self.chip_nosource(("fixed", index) in gaps)),
                        "<td><small>%s</small></td>" % (
                            ("\u201c%s\u201d" % esc(quote)) if quote else ""),
                        "<td>%s</td>" % self.chip_evidence(entry.get("evidence_class")),
                    ])
                if label:
                    self.w('<p class="sub"><strong title="%s">%s</strong></p>'
                           % (esc(L.plain(label)), esc(L.label(label))))
                self.table(["", L.label("ui.result"), L.label("ui.observed"),
                            L.label("ui.quote"), L.label("ui.evidence")], rows)

    def s3_comparison(self):
        L = self.L
        comparison = self.d.get("comparison") or {}
        candidates = self.d.get("candidates", [])
        if len(candidates) < 2:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
            return
        by_id = dict((c.get("id"), c) for c in candidates)
        ranking = comparison.get("ranking") or []
        order = [r.get("candidate_id") for r in ranking] or [c.get("id") for c in candidates]

        rows = []
        for i, entry in enumerate(ranking, 1):
            cand = by_id.get(entry.get("candidate_id")) or {}
            rows.append([
                '<td class="num">%d</td>' % i,
                "<td><strong>%s</strong></td>" % esc(candidate_name(cand)),
                '<td class="num">%s</td>' % esc(fmt_value(entry.get("quality_score"))),
                '<td class="num">%s</td>' % esc("%d%%" % round((entry.get("closing_probability") or 0) * 100)),
                '<td class="num">%s</td>' % esc(fmt_value(entry.get("expected_value"))),
                "<td>%s</td>" % esc(entry.get("reason", "")),
            ])
        if rows:
            self.table([L.label("ui.rank"), L.label("ui.candidate"),
                        (L.label("ui.quality_score"), L.plain("ui.quality_score")),
                        (L.label("ui.closing_probability"), L.plain("ui.closing_probability")),
                        (L.label("ui.expected_value"), L.plain("ui.expected_value")),
                        L.label("ui.reason")], rows)

        headers = [L.label("ui.candidate")]
        for _, tid in METRIC_KEYS:
            headers.append((L.label(tid), L.plain(tid)))
        headers.append((L.label("ui.all_in_pcm"), L.plain("ui.all_in_pcm")))
        rows = []
        for cid in order:
            cand = by_id.get(cid)
            if not cand:
                continue
            metrics = cand.get("metrics") or {}
            bad = self.bad.get(cand.get("id")) or {}
            gaps = self.nosource.get(cand.get("id")) or set()
            cells = ["<td><strong>%s</strong></td>" % esc(candidate_name(cand))]
            for key, _tid in METRIC_KEYS:
                cells.append(self.measure_cell(metrics.get(key), bad.get(("metrics", key)),
                                               ("metrics", key) in gaps))
            costs = cand.get("costs") or {}
            cells.append('<td class="num"><span class="meaning" title="%s">%s</span>%s<br><small>%s</small></td>' % (
                esc(costs.get("basis_note") or ""), esc(money(costs.get("all_in_planning")) or L.label("ui.no_data")),
                self.chip_maths(bad.get(("costs", "all_in_planning"))),
                esc(L.plain("ui.all_in_pcm"))))
            rows.append(cells)
        self.table(headers, rows)

        shown = [cid for cid in order if by_id.get(cid)]
        texts = []
        for cid in shown:
            for _index, qa in staged_questions(by_id[cid], "compare"):
                if qa.get("question") and qa["question"] not in texts:
                    texts.append(qa["question"])
        if texts:
            self.w("<h3>%s</h3>" % esc(L.label("ui.your_questions")))
            self.w('<p class="lede">%s</p>' % esc(L.plain("ui.your_questions")))
            rows = []
            for text in texts:
                cells = ["<td><strong>%s</strong></td>" % esc(text)]
                for cid in shown:
                    gaps = self.nosource.get(cid) or set()
                    answers = [(i, qa) for i, qa in staged_questions(by_id[cid], "compare")
                               if qa.get("question") == text]
                    if not answers:
                        cells.append("<td>%s</td>" % esc(L.label("ui.no_data")))
                        continue
                    index, qa = answers[0]
                    cells.append("<td>%s%s<br>%s <small>%s</small></td>" % (
                        esc(qa.get("answer", "")),
                        self.chip_nosource(("question", index) in gaps),
                        self.chip_evidence(qa.get("evidence_class")),
                        esc(trigger_state(qa, L))))
                rows.append(cells)
            self.table([L.label("ui.your_questions")]
                       + [candidate_name(by_id[cid]) for cid in shown], rows)

        for key, tid in (("structural_findings", "ui.structural_findings"),
                         ("single_building_findings", "ui.single_building_findings")):
            findings = comparison.get(key) or []
            if not findings:
                continue
            self.w("<h3>%s</h3>" % esc(self.L.label(tid)))
            self.w('<p class="lede">%s</p>' % esc(self.L.plain(tid)))
            for finding in findings:
                self.w('<div class="card"><h4>%s</h4><p>%s</p>' % (
                    esc(finding.get("theme", "")), esc(finding.get("detail", ""))))
                if key == "structural_findings":
                    self.w('<p class="sub">%s &middot; %s</p>' % (
                        esc("%s: %s" % (self.L.label("ui.building"), finding.get("buildings_count"))),
                        esc(", ".join(str(y) for y in finding.get("years") or []))))
                else:
                    self.w('<p class="sub">%s: %s</p>' % (
                        esc(self.L.label("ui.building")), esc(finding.get("building", ""))))
                self.w("</div>")

    def s4_worst_reviews(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            reviews = cand.get("worst_reviews") or []
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            if not reviews:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            rows = []
            for rev in reviews:
                organic = rev.get("organic")
                rows.append([
                    "<td>%s</td>" % esc(rev.get("building") or ""),
                    "<td>%s</td>" % esc(rev.get("source_name") or ""),
                    '<td class="num">%s</td>' % esc(rev.get("date") or ""),
                    '<td class="num">%s</td>' % esc(fmt_value(rev.get("score")) or ""),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        "ok" if organic else "bad", esc(L.plain("ui.organic")),
                        esc(L.label("ui.yes") if organic else L.label("ui.no"))),
                    '<td><div class="rev">%s</div></td>' % esc(rev.get("excerpt") or ""),
                    "<td>%s</td>" % esc(rev.get("why_it_matters") or ""),
                ])
            self.table([L.label("ui.building"), L.label("ui.source_name"), L.label("ui.date"),
                        L.label("ui.score"), (L.label("ui.organic"), L.plain("ui.organic")),
                        L.label("ui.excerpt"), L.label("ui.why_it_matters")], rows)

    def s5_landmines(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            mines = cand.get("landmines") or []
            if not mines:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            rows = []
            for mine in mines:
                code = mine.get("code", "")
                rows.append([
                    '<td class="num"><span class="chip" title="%s">%s</span></td>' % (
                        esc(L.plain("landmine." + code)), esc(code)),
                    "<td><strong>%s</strong><br><small>%s</small></td>" % (
                        esc(mine.get("label", "")), esc(L.label("landmine." + code, ""))),
                    "<td>%s</td>" % esc(mine.get("detail", "")),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        "ok" if mine.get("reversible") else "bad", esc(L.plain("ui.reversible")),
                        esc(L.label("ui.yes") if mine.get("reversible") else L.label("ui.no"))),
                    "<td>%s</td>" % self.chip_evidence(mine.get("evidence_class")),
                ])
            self.table(["", L.label("section.landmines"),
                        L.label("ui.detail"),
                        (L.label("ui.reversible"), L.plain("ui.reversible")),
                        L.label("ui.evidence")], rows)

    def s6_axes(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w('<div class="card"><h3>%s</h3>' % esc(candidate_name(cand)))
            bad = self.bad.get(cand.get("id")) or {}
            gaps = self.nosource.get(cand.get("id")) or set()
            for axis in sorted(cand.get("axes") or [], key=lambda a: a.get("id") or 0):
                aid = axis.get("id")
                self.w('<div class="axis"><h4>%s. %s %s</h4>' % (
                    esc(aid), esc(L.label("axis.%s" % aid, axis.get("name", ""))),
                    self.chip_evidence(axis.get("evidence_class"))))
                self.w("<p>%s</p>" % esc(axis.get("finding", "")))
                numbers = axis.get("numbers") or []
                if numbers:
                    rows = []
                    for index, n in enumerate(numbers):
                        rows.append([
                            "<td><strong>%s</strong></td>" % esc(n.get("label", "")),
                            '<td class="num"><span class="meaning" title="%s">%s</span>%s%s</td>' % (
                                esc(n.get("meaning") or ""), esc(fmt_value(n.get("value"), n.get("unit"))
                                                                 or L.label("ui.no_data")),
                                self.chip_maths(bad.get(("axis", aid, index))),
                                self.chip_nosource(("axis", aid, index) in gaps)),
                            "<td><small>%s</small></td>" % esc(n.get("meaning", "")),
                            "<td><small>%s</small></td>" % esc(n.get("compared_to", "")),
                            "<td>%s</td>" % self.chip_evidence(n.get("evidence_class")),
                        ])
                    self.table([L.label("ui.numbers"), "", L.label("ui.why_it_matters"),
                                L.label("ui.compared_to"), L.label("ui.evidence")], rows)
                if axis.get("unknowns"):
                    self.w("<p class=\"sub\"><strong>%s</strong></p><ul>" % esc(L.label("ui.unknowns")))
                    for unk in axis["unknowns"]:
                        self.w("<li>%s</li>" % esc(unk))
                    self.w("</ul>")
                if axis.get("sources"):
                    self.w('<p class="sub">%s: %s</p>' % (
                        esc(L.label("ui.sources")), esc(", ".join(axis["sources"]))))
                self.w("</div>")
            costs = cand.get("costs") or {}
            if costs:
                self.w("<h4>%s</h4>" % esc(L.label("ui.costs")))
                rows = []
                for key, tid in COST_KEYS:
                    if costs.get(key) is None:
                        continue
                    rows.append(['<td title="%s">%s</td>' % (esc(L.plain(tid)), esc(L.label(tid))),
                                 '<td class="num">%s%s</td>' % (esc(money(costs.get(key))),
                                                                self.chip_maths(bad.get(("costs", key))))])
                if rows:
                    self.table([L.label("ui.costs"), ""], rows)
                if costs.get("basis_note"):
                    self.w('<p class="sub"><strong>%s:</strong> %s</p>' % (
                        esc(L.label("ui.basis_note")), esc(costs["basis_note"])))
            self.arithmetic_block(cand)
            if cand.get("photos_vs_reality_notes"):
                self.w("<h4>%s</h4><p>%s</p>" % (esc(L.label("ui.photos_vs_reality")),
                                                 esc(cand["photos_vs_reality_notes"])))
            if cand.get("provenance_notes"):
                self.w("<h4>%s</h4><ul>" % esc(L.label("ui.provenance")))
                for note in cand["provenance_notes"]:
                    self.w("<li><small>%s</small></li>" % esc(note))
                self.w("</ul>")
            self.w("</div>")

    def arithmetic_block(self, cand):
        """Section 6: every recomputed figure, with the formula in words."""
        L = self.L
        entry = cand.get("arithmetic_check") or {}
        checks = entry.get("checks") or []
        if not checks:
            return
        chip = ("" if entry.get("arithmetic_ok") else
                ' <span class="chip maths">%s</span>' % esc(L.label("ui.check_the_maths")))
        self.w("<h4>%s%s</h4>" % (esc(L.label("ui.arithmetic_check")), chip))
        self.w('<p class="lede">%s</p>' % esc(L.plain("ui.arithmetic_check")))
        rows = []
        for check in checks:
            source = ("<br><small>%s</small>" % esc(check["where"])) if check.get("where") else ""
            rows.append([
                "<td><strong>%s</strong>%s</td>" % (esc(check_label(check, L)), source),
                "<td><small>%s</small></td>" % esc(check["formula"]),
                '<td class="%s">%s</td>' % ("good" if check["ok"] else "bad",
                                            esc(check_status(check, L))),
            ])
        self.w('<div class="arith">')
        self.table([L.label("ui.numbers"), L.label("ui.formula"), L.label("ui.result")], rows)
        self.w("</div>")

    def s7_questions(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            self.w("<h4>%s</h4>" % esc(L.label("ui.killer_questions")))
            self.w('<p class="lede">%s</p>' % esc(L.plain("ui.killer_questions")))
            questions = cand.get("killer_questions") or []
            if questions:
                for question in questions:
                    self.w('<div class="q">%s</div>' % esc(question))
            else:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
            self.w("<h4>%s</h4>" % esc(L.label("ui.viewing_checks")))
            checks = cand.get("viewing_day_checks") or []
            if checks:
                self.w("<ol>")
                for check in checks:
                    self.w("<li>%s</li>" % esc(check))
                self.w("</ol>")
            else:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
            self.questions_block(cand, "viewing", L.label("ui.your_questions"))
            if staged_questions(cand, "sign"):
                self.w("<h4>%s</h4>" % esc(L.label("ui.before_signing")))
                self.w('<p class="lede">%s</p>' % esc(L.plain("ui.before_signing")))
                self.questions_block(cand, "sign")

    def s8_only_you(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            self.w("<p>%s</p><ul>" % esc(L.label("ui.unknown_axes_request")))
            for label, text in only_you_asks(cand, L):
                self.w("<li><strong>%s</strong>: %s</li>" % (esc(label), esc(text))
                       if label else "<li>%s</li>" % esc(text))
            self.w("</ul>")

    def s9_gaps(self):
        L = self.L
        rows = []
        for entry in self.d.get("not_found") or []:
            queries = "".join("<li><code>%s</code></li>" % esc(q) for q in entry.get("queries_used") or [])
            rows.append([
                "<td><strong>%s</strong></td>" % esc(entry.get("what", "")),
                "<td><ul>%s</ul></td>" % queries,
                "<td><small>%s</small></td>" % esc(entry.get("where_looked") or ""),
                "<td><small>%s</small></td>" % esc(entry.get("next_step") or ""),
            ])
        if rows:
            self.table([L.label("ui.not_found_what"), (L.label("ui.queries_used"), L.plain("ui.queries_used")),
                        L.label("ui.sources"), L.label("ui.next_step")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
        rows = []
        for entry in self.d.get("blocked_sources") or []:
            rows.append([
                "<td><strong>%s</strong></td>" % esc(entry.get("source", "")),
                '<td class="num">%s</td>' % esc(entry.get("http_status") if entry.get("http_status") is not None else ""),
                "<td>%s</td>" % esc(entry.get("reason", "")),
                "<td><small>%s</small></td>" % esc(entry.get("workaround") or ""),
            ])
        self.w("<h3>%s</h3>" % esc(L.label("ui.blocked_source")))
        if rows:
            self.table([L.label("ui.blocked_source"), L.label("ui.http_status"),
                        L.label("ui.blocked_reason"), L.label("ui.workaround")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))

    def s10_sources(self):
        L = self.L
        rows = []
        for src in self.d.get("sources") or []:
            url = src.get("url") or ""
            link = ('<a href="%s">%s</a>' % (esc(url), esc(url))) if url.startswith("http") else esc(url)
            note = " ".join(x for x in (src.get("provenance"), src.get("note")) if x)
            rows.append([
                '<td class="num"><code>%s</code></td>' % esc(src.get("id", "")),
                "<td>%s</td>" % esc(src.get("name") or ""),
                "<td><small>%s</small></td>" % link,
                '<td class="num"><small>%s</small></td>' % esc(src.get("retrieved_at", "")),
                "<td>%s</td>" % self.chip_evidence(src.get("evidence_class")),
                "<td><small>%s</small></td>" % esc(note),
            ])
        if rows:
            self.table(["", L.label("ui.source_name"), L.label("ui.url"),
                        (L.label("ui.retrieved_at"), L.plain("ui.retrieved_at")),
                        L.label("ui.evidence"), L.label("ui.provenance")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))

    def s11_about(self):
        L = self.L
        self.w("<p class=\"sub\"><strong>%s</strong></p>" % esc(configuration_line(self.d, L)))
        gb = self.d.get("generated_by") or {}
        rows = [
            ("ui.tool", gb.get("tool")),
            ("ui.version", gb.get("version")),
            ("ui.runtime", gb.get("runtime")),
            ("ui.mode", gb.get("mode")),
            ("ui.model", gb.get("model_name")),
            ("ui.language", self.d.get("language")),
            ("ui.generated_at", self.d.get("generated_at")),
        ]
        cells = []
        for tid, value in rows:
            if value in (None, ""):
                continue
            cells.append(['<td title="%s">%s</td>' % (esc(L.plain(tid)), esc(L.label(tid))),
                          "<td>%s</td>" % esc(value)])
        self.table(["", ""], cells)
        snapshot = self.d.get("profile_snapshot") or {}
        prows = profile_rows(snapshot, L)
        if prows:
            self.w("<h3>%s</h3>" % esc(L.label("ui.profile_snapshot")))
            self.w('<p class="lede">%s</p>' % esc(L.plain("ui.profile_snapshot")))
            self.table(["", ""], [["<td>%s</td>" % esc(k), "<td>%s</td>" % esc(v)] for k, v in prows])
        self.w("<h3>%s</h3>" % esc(L.label("ui.evidence")))
        rows = []
        for code in ("G", "S", "C", "I", "U"):
            rows.append(["<td>%s</td>" % self.chip_evidence(code),
                         "<td>%s</td>" % esc(L.plain("evidence." + code))])
        self.table(["", ""], rows)

    # -- document ------------------------------------------------------------
    def render(self):
        L = self.L
        names = ", ".join(candidate_name(c) for c in self.d.get("candidates", []))
        title = "%s \u2014 %s" % (L.label("ui.report_title"), names) if names else L.label("ui.report_title")
        self.w("<!doctype html>")
        self.w('<html lang="%s"><head><meta charset="utf-8">' % esc(L.lang))
        self.w('<meta name="viewport" content="width=device-width,initial-scale=1">')
        self.w("<title>%s</title>" % esc(title))
        self.w("<style>%s</style></head><body><div class=\"wrap\">" % CSS)
        self.w("<h1>%s</h1>" % esc(L.label("ui.report_title")))
        self.w('<p class="sub">%s &middot; %s</p>' % (esc(names), esc(self.d.get("generated_at", ""))))
        renderers = [self.s1_verdict, self.s2_hard_filters, self.s3_fixed, self.s3_comparison,
                     self.s4_worst_reviews, self.s5_landmines, self.s6_axes, self.s7_questions,
                     self.s8_only_you, self.s9_gaps, self.s10_sources, self.s11_about]
        for i, ((term_id, anchor), fn) in enumerate(zip(SECTIONS, renderers), 1):
            self.section(i, term_id, anchor)
            fn()
        self.w('<p class="foot">%s</p>' % esc(footer_text(self.d)))
        self.w("</div></body></html>")
        return "\n".join(self.out)


# ---------------------------------------------------------------- Markdown ---
def markdown_data(value):
    """Report strings are literal text, never Markdown links, images or raw HTML.

    Escaping only at the final HTML step would miss Markdown image requests and
    unsafe links in hosts that enable raw HTML. Keep our generated layout markup.
    """
    if isinstance(value, dict):
        return {markdown_data(key): markdown_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [markdown_data(item) for item in value]
    if isinstance(value, str):
        value = value.replace("\\", "\\\\").replace("&", "&amp;")
        value = value.replace("<", "&lt;").replace(">", "&gt;")
        for char in ("`", "[", "]"):
            value = value.replace(char, "\\" + char)
    return value


def md_escape(text):
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def md_table(headers, rows):
    out = ["", "| " + " | ".join(md_escape(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md_escape(c) for c in row) + " |")
    out.append("")
    return out


def render_markdown(data, L, schema=None):
    data = markdown_data(data)
    o = []
    bad_by_candidate = bad_locations(data)   # also fills candidate.arithmetic_check
    gaps_by_candidate = unsourced_locations(data, schema)

    def maths_flag(bad, key):
        """The Markdown twin of the inline warning chip."""
        check = bad.get(key)
        return "" if not check else " **[%s]**" % L.label("ui.check_the_maths")

    def source_flag(gaps, key):
        """The Markdown twin of the inline "no source" chip."""
        return " **[%s]**" % L.label("ui.no_source") if key in gaps else ""

    def questions_block(cand, when, title=None):
        """The Markdown twin of the staged block of the user's own questions."""
        rows = staged_questions(cand, when)
        if not rows:
            return
        gaps = gaps_by_candidate.get(cand.get("id")) or set()
        if title:
            o.append("")
            o.append("**%s**" % title)
        for index, qa in rows:
            bits = [L.label("evidence." + (qa.get("evidence_class") or "U")), trigger_state(qa, L)]
            if qa.get("trigger"):
                bits.append(qa["trigger"])
            o.append("")
            o.append("- **%s**" % qa.get("question", ""))
            o.append("  - %s%s" % (qa.get("answer", ""), source_flag(gaps, ("question", index))))
            o.append("  - %s" % " \u00b7 ".join(bits))

    names = ", ".join(candidate_name(c) for c in data.get("candidates", []))
    o.append("# %s \u2014 %s" % (L.label("ui.report_title"), names))
    o.append("")
    o.append("_%s_" % data.get("generated_at", ""))

    def head(i, term_id):
        o.append("")
        o.append("## %d. %s" % (i, L.label(term_id)))
        gloss = L.plain(term_id)
        if gloss:
            o.append("")
            o.append("_%s_" % gloss)

    candidates = data.get("candidates", [])

    head(1, "section.verdict")
    for cand in candidates:
        verdict = cand.get("verdict") or {}
        status = verdict.get("status", "")
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append("**%s** \u2014 %s" % (L.label("verdict." + status, status), verdict.get("headline", "")))
        codes = verdict.get("reason_codes") or []
        if codes:
            o.append("")
            o.append("%s: %s" % (L.label("ui.reason_codes"),
                                 ", ".join("%s (%s)" % (L.label("landmine." + c, c), c) for c in codes)))
        if verdict.get("break_even_rent_pcm") is not None:
            o.append("")
            o.append("%s: %s" % (L.label("ui.break_even_rent"), money(verdict["break_even_rent_pcm"])))
        if verdict.get("fatal_axis"):
            o.append("")
            o.append("%s: %s. %s" % (L.label("ui.fatal_axis"), verdict["fatal_axis"],
                                     L.label("axis.%s" % verdict["fatal_axis"])))
        for cond in verdict.get("conditions") or []:
            o.append("- %s" % cond)
        questions_block(cand, "vet", L.label("ui.your_questions"))

    head(2, "section.hard_filters")
    marks = {True: "ui.pass", False: "ui.fail", "unknown": "ui.unknown"}
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        bad = bad_by_candidate.get(cand.get("id")) or {}
        gaps = gaps_by_candidate.get(cand.get("id")) or set()
        rows = [[hf.get("name", ""), hf.get("requirement", ""),
                 (hf.get("observed", "") or "") + maths_flag(bad, ("hard_filter", i)),
                 L.label(marks.get(hf.get("pass"), "ui.unknown")),
                 L.label("evidence." + (hf.get("evidence_class") or "U"))]
                for i, hf in enumerate(cand.get("hard_filters") or [])]
        rows += [[qa.get("question", ""), qa.get("trigger") or "\u2014",
                  (qa.get("answer", "") or "") + source_flag(gaps, ("question", i)),
                  trigger_state(qa, L),
                  L.label("evidence." + (qa.get("evidence_class") or "U"))]
                 for i, qa in staged_questions(cand, "filter")]
        o += md_table(["", L.label("ui.requirement"), L.label("ui.observed"),
                       L.label("ui.result"), L.label("ui.evidence")], rows)

    head(3, "section.fixed")
    questions = fixed_questions()
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append("_%s_" % L.label("ui.fixed_lead"))
        o.append("")
        o.append("_%s_" % L.label("ui.fixed_tiers"))
        gaps = gaps_by_candidate.get(cand.get("id")) or set()
        for label, entries in fixed_group_rows(cand, questions):
            rows = []
            for index, entry in entries:
                tid = "fixed." + (entry.get("id") or "")
                state = FIXED_STATES.get(entry.get("status"), FIXED_STATES["unknown"])[1]
                quote = entry.get("quote") or ""
                rows.append([L.label(tid, entry.get("id") or ""), L.label(state),
                             fixed_answer_text(entry, questions) + source_flag(gaps, ("fixed", index)),
                             ("\u201c%s\u201d" % quote) if quote else "",
                             L.label("evidence." + (entry.get("evidence_class") or "U"))])
            if label:
                o.append("")
                o.append("**%s**" % L.label(label))
            o += md_table(["", L.label("ui.result"), L.label("ui.observed"),
                           L.label("ui.quote"), L.label("ui.evidence")], rows)

    head(4, "section.comparison")
    comparison = data.get("comparison") or {}
    if len(candidates) > 1 and comparison:
        by_id = dict((c.get("id"), c) for c in candidates)
        rows = []
        for i, entry in enumerate(comparison.get("ranking") or [], 1):
            cand = by_id.get(entry.get("candidate_id")) or {}
            rows.append([i, candidate_name(cand), fmt_value(entry.get("quality_score")),
                         "%d%%" % round((entry.get("closing_probability") or 0) * 100),
                         fmt_value(entry.get("expected_value")), entry.get("reason", "")])
        o += md_table([L.label("ui.rank"), L.label("ui.candidate"), L.label("ui.quality_score"),
                       L.label("ui.closing_probability"), L.label("ui.expected_value"),
                       L.label("ui.reason")], rows)
        headers = [L.label("ui.candidate")] + [L.label(t) for _, t in METRIC_KEYS] + [L.label("ui.all_in_pcm")]
        rows = []
        for entry in comparison.get("ranking") or []:
            cand = by_id.get(entry.get("candidate_id"))
            if not cand:
                continue
            metrics = cand.get("metrics") or {}
            bad = bad_by_candidate.get(cand.get("id")) or {}
            gaps = gaps_by_candidate.get(cand.get("id")) or set()
            row = [candidate_name(cand)]
            for key, _t in METRIC_KEYS:
                mea = metrics.get(key) or {}
                text = fmt_value(mea.get("value"), mea.get("unit")) or L.label("ui.no_data")
                if mea.get("compared_to"):
                    text = "%s (%s)" % (text, mea["compared_to"])
                row.append(text + maths_flag(bad, ("metrics", key))
                           + source_flag(gaps, ("metrics", key)))
            row.append((money((cand.get("costs") or {}).get("all_in_planning")) or L.label("ui.no_data"))
                       + maths_flag(bad, ("costs", "all_in_planning")))
            rows.append(row)
        o += md_table(headers, rows)
        shown = [c for c in (by_id.get(e.get("candidate_id"))
                             for e in comparison.get("ranking") or []) if c]
        texts = []
        for cand in shown:
            for _i, qa in staged_questions(cand, "compare"):
                if qa.get("question") and qa["question"] not in texts:
                    texts.append(qa["question"])
        if texts:
            o.append("")
            o.append("### %s" % L.label("ui.your_questions"))
            rows = []
            for text in texts:
                row = [text]
                for cand in shown:
                    gaps = gaps_by_candidate.get(cand.get("id")) or set()
                    answers = [(i, qa) for i, qa in staged_questions(cand, "compare")
                               if qa.get("question") == text]
                    if not answers:
                        row.append(L.label("ui.no_data"))
                        continue
                    index, qa = answers[0]
                    row.append("%s%s (%s \u00b7 %s)" % (
                        qa.get("answer", ""), source_flag(gaps, ("question", index)),
                        L.label("evidence." + (qa.get("evidence_class") or "U")),
                        trigger_state(qa, L)))
                rows.append(row)
            o += md_table([L.label("ui.your_questions")]
                          + [candidate_name(c) for c in shown], rows)
        for key, tid in (("structural_findings", "ui.structural_findings"),
                         ("single_building_findings", "ui.single_building_findings")):
            findings = comparison.get(key) or []
            if not findings:
                continue
            o.append("")
            o.append("### %s" % L.label(tid))
            o.append("")
            o.append("_%s_" % L.plain(tid))
            for finding in findings:
                o.append("")
                o.append("- **%s** \u2014 %s" % (finding.get("theme", ""), finding.get("detail", "")))
    else:
        o.append("")
        o.append("_%s_" % L.label("ui.nothing_listed"))

    head(5, "section.worst_reviews")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        rows = [[r.get("building") or "", r.get("source_name") or "", r.get("date") or "",
                 fmt_value(r.get("score")) or "",
                 L.label("ui.yes") if r.get("organic") else L.label("ui.no"),
                 r.get("excerpt") or "", r.get("why_it_matters") or ""]
                for r in cand.get("worst_reviews") or []]
        if rows:
            o += md_table([L.label("ui.building"), L.label("ui.source_name"), L.label("ui.date"),
                           L.label("ui.score"), L.label("ui.organic"), L.label("ui.excerpt"),
                           L.label("ui.why_it_matters")], rows)
        else:
            o.append("")
            o.append("_%s_" % L.label("ui.nothing_listed"))

    head(6, "section.landmines")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        rows = [[m.get("code", ""), "%s (%s)" % (m.get("label", ""), L.label("landmine." + m.get("code", ""), "")),
                 m.get("detail", ""),
                 L.label("ui.yes") if m.get("reversible") else L.label("ui.no"),
                 L.label("evidence." + (m.get("evidence_class") or "U"))]
                for m in cand.get("landmines") or []]
        if rows:
            o += md_table(["", L.label("section.landmines"), L.label("ui.detail"),
                           L.label("ui.reversible"), L.label("ui.evidence")], rows)
        else:
            o.append("")
            o.append("_%s_" % L.label("ui.nothing_listed"))

    head(7, "section.axes")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        bad = bad_by_candidate.get(cand.get("id")) or {}
        gaps = gaps_by_candidate.get(cand.get("id")) or set()
        for axis in sorted(cand.get("axes") or [], key=lambda a: a.get("id") or 0):
            aid = axis.get("id")
            o.append("")
            o.append("#### %s. %s [%s]" % (aid, L.label("axis.%s" % aid, axis.get("name", "")),
                                           L.label("evidence." + (axis.get("evidence_class") or "U"))))
            o.append("")
            o.append(axis.get("finding", ""))
            for index, n in enumerate(axis.get("numbers") or []):
                o.append("- **%s**: %s%s%s \u2014 %s %s" % (
                    n.get("label", ""), fmt_value(n.get("value"), n.get("unit")) or L.label("ui.no_data"),
                    maths_flag(bad, ("axis", aid, index)),
                    source_flag(gaps, ("axis", aid, index)),
                    n.get("meaning", ""), n.get("compared_to", "")))
            for unk in axis.get("unknowns") or []:
                o.append("- %s: %s" % (L.label("ui.unknowns"), unk))
        costs = cand.get("costs") or {}
        if costs:
            o.append("")
            o.append("**%s**" % L.label("ui.costs"))
            rows = [[L.label(t), money(costs.get(k)) + maths_flag(bad, ("costs", k))]
                    for k, t in COST_KEYS if costs.get(k) is not None]
            o += md_table([L.label("ui.costs"), ""], rows)
            if costs.get("basis_note"):
                o.append("%s: %s" % (L.label("ui.basis_note"), costs["basis_note"]))
        arith = cand.get("arithmetic_check") or {}
        if arith.get("checks"):
            o.append("")
            o.append("**%s**%s" % (L.label("ui.arithmetic_check"),
                                   "" if arith.get("arithmetic_ok") else
                                   " **[%s]**" % L.label("ui.check_the_maths")))
            o.append("")
            o.append("_%s_" % L.plain("ui.arithmetic_check"))
            o += md_table([L.label("ui.numbers"), L.label("ui.formula"), L.label("ui.result")],
                          [["%s%s" % (check_label(c, L), " (%s)" % c["where"] if c.get("where") else ""),
                            c["formula"], check_status(c, L)] for c in arith["checks"]])
        if cand.get("photos_vs_reality_notes"):
            o.append("")
            o.append("**%s**: %s" % (L.label("ui.photos_vs_reality"), cand["photos_vs_reality_notes"]))
        for note in cand.get("provenance_notes") or []:
            o.append("- %s: %s" % (L.label("ui.provenance"), note))

    head(8, "section.questions")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append("**%s**" % L.label("ui.killer_questions"))
        for question in cand.get("killer_questions") or []:
            o.append("1. %s" % question)
        o.append("")
        o.append("**%s**" % L.label("ui.viewing_checks"))
        for check in cand.get("viewing_day_checks") or []:
            o.append("- [ ] %s" % check)
        questions_block(cand, "viewing", L.label("ui.your_questions"))
        if staged_questions(cand, "sign"):
            o.append("")
            o.append("**%s**" % L.label("ui.before_signing"))
            questions_block(cand, "sign")

    head(9, "section.only_you")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append(L.label("ui.unknown_axes_request"))
        for label, text in only_you_asks(cand, L):
            o.append("- **%s**: %s" % (label, text) if label else "- %s" % text)

    head(10, "section.gaps")
    rows = [[e.get("what", ""), "; ".join("`%s`" % q for q in e.get("queries_used") or []),
             e.get("where_looked") or "", e.get("next_step") or ""]
            for e in data.get("not_found") or []]
    if rows:
        o += md_table([L.label("ui.not_found_what"), L.label("ui.queries_used"),
                       L.label("ui.sources"), L.label("ui.next_step")], rows)
    o.append("")
    o.append("### %s" % L.label("ui.blocked_source"))
    rows = [[e.get("source", ""), e.get("http_status") if e.get("http_status") is not None else "",
             e.get("reason", ""), e.get("workaround") or ""]
            for e in data.get("blocked_sources") or []]
    if rows:
        o += md_table([L.label("ui.blocked_source"), L.label("ui.http_status"),
                       L.label("ui.blocked_reason"), L.label("ui.workaround")], rows)

    head(11, "section.sources")
    rows = [[s.get("id", ""), s.get("name") or "", s.get("url") or "", s.get("retrieved_at", ""),
             L.label("evidence." + (s.get("evidence_class") or "U")),
             " ".join(x for x in (s.get("provenance"), s.get("note")) if x)]
            for s in data.get("sources") or []]
    o += md_table(["", L.label("ui.source_name"), L.label("ui.url"), L.label("ui.retrieved_at"),
                   L.label("ui.evidence"), L.label("ui.provenance")], rows)

    head(12, "section.about")
    o.append("")
    o.append(configuration_line(data, L))
    gb = data.get("generated_by") or {}
    rows = [[L.label("ui.tool"), gb.get("tool")], [L.label("ui.version"), gb.get("version")],
            [L.label("ui.runtime"), gb.get("runtime")], [L.label("ui.mode"), gb.get("mode")],
            [L.label("ui.model"), gb.get("model_name")], [L.label("ui.language"), data.get("language")],
            [L.label("ui.generated_at"), data.get("generated_at")]]
    o += md_table(["", ""], [r for r in rows if r[1]])
    prows = profile_rows(data.get("profile_snapshot") or {}, L)
    if prows:
        o.append("### %s" % L.label("ui.profile_snapshot"))
        o += md_table(["", ""], [[k, v] for k, v in prows])
    o += md_table(["", ""], [[L.label("evidence." + c), L.plain("evidence." + c)] for c in "GSCIU"])
    o.append("")
    o.append("---")
    o.append("")
    o.append(footer_text(data))
    o.append("")
    return "\n".join(o)


# -------------------------------------------------------------------- main ---
def build_parser():
    p = argparse.ArgumentParser(
        description="Render a Pea Princess report.json as one self-contained HTML page, or as Markdown.")
    p.add_argument("report", help="path to report.json")
    p.add_argument("--lang", default=None,
                   help="BCP-47 language for labels (en, zh-TW, zh-CN...). Default: the report's own language.")
    p.add_argument("--md", action="store_true", help="write Markdown instead of HTML")
    p.add_argument("--validate-only", action="store_true", help="check the report and write nothing")
    p.add_argument("--schema", default=DEFAULT_SCHEMA, help="path to report-schema.json")
    p.add_argument("--glossary", default=DEFAULT_GLOSSARY, help="path to glossary.yaml")
    p.add_argument("--strict", action="store_true",
                   help="treat warnings as errors, including every number with no source and no "
                        "computed_by note")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with io.open(args.report, encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError) as exc:
        sys.stderr.write("Cannot read the report: %s\n" % exc)
        return 2
    except ValueError as exc:
        sys.stderr.write("The report is not valid JSON: %s\n" % exc)
        return 1
    try:
        with io.open(args.schema, encoding="utf-8") as fh:
            schema = json.load(fh)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("Cannot read the schema at %s: %s\n" % (args.schema, exc))
        return 2

    errors, warnings = validate(data, schema)
    for warning in warnings:
        sys.stderr.write("warning  %s\n" % warning)
    sums = arithmetic_warnings(data)
    for line in sums:
        sys.stderr.write("WARNING  arithmetic: %s\n" % line)
    gaps = unsourced_numbers(data, schema)
    for gap in gaps:
        sys.stderr.write("WARNING  no source: %s\n" % gap["message"])
    if errors:
        sys.stderr.write("\nThis report does not match report-schema.json. %d problem%s:\n"
                         % (len(errors), "" if len(errors) == 1 else "s"))
        for error in errors:
            sys.stderr.write("  error  %s\n" % error)
        sys.stderr.write("\nFix the JSON and run again. The schema explains every field:\n  %s\n" % args.schema)
        return 1
    if (warnings or sums or gaps) and args.strict:
        sys.stderr.write("\n--strict: %d warning(s) treated as errors, %d of them arithmetic, "
                         "%d number(s) with no source.\n"
                         % (len(warnings) + len(sums) + len(gaps), len(sums), len(gaps)))
        return 1
    if args.validate_only:
        sys.stderr.write("OK: the report matches report-schema.json.\n")
        if gaps:
            sys.stderr.write("But %d number(s) name no source and no formula; both renderers mark "
                             "them \"no source\".\n" % len(gaps))
        if sums:
            sys.stderr.write("But %d number(s) do not follow from the formulas above.\n" % len(sums))
        else:
            sys.stderr.write("Every number that follows from a formula was recomputed and matches.\n")
        return 0

    try:
        terms = load_glossary(args.glossary)
    except (IOError, OSError, GlossaryError) as exc:
        sys.stderr.write("Cannot read the glossary at %s: %s\n" % (args.glossary, exc))
        return 2
    lang = args.lang or data.get("language") or "en"
    labels = Labels(terms, lang)
    text = (render_markdown(data, labels, schema) if args.md
            else HtmlRenderer(data, labels, schema).render())
    out = getattr(sys.stdout, "buffer", sys.stdout)
    out.write(text.encode("utf-8"))
    out.write(b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
