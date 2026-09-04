#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score an A/B sweep: per run, per config, paired per case, and print the decision.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHAT IT READS
=============
``bench/results/<date>/scorecard.json`` - one row per run, written by bench/run.py or
bench/ab/run_codex.py. Each row names its config, its case, its run index, its wall
time, its token counts and the path to the report it graded.
``bench/private/gold.json`` - the private gold set: verdict, landmine codes with a
confidence, and the killer questions the owner actually asked.

WHAT IT ADDS TO THE PUBLIC FACT SCORES
======================================
landmine_recall      of the gold's HIGH-confidence codes, the share the report raised.
                     Low-confidence gold codes are reported separately and never
                     counted, because they were derived from survey text rather than
                     from the reviewer's stated objection.
landmine_recall_script / _mixed / _reading
                     the same recall, split by HOW a landmine can be found:
                     `script` a repository script establishes it on its own, `mixed`
                     a script gives half and prose gives the rest, `reading` only
                     prose establishes it. The gold was written by a person reading
                     reviews, planning documents and paperwork, which flatters arms
                     that go and read raw pages; the split says how much of an arm's
                     score is that tilt. The mapping is bench/ab/landmine_layers.yaml
                     and a single gold landmine may override it with its own `layer:`.
                     Null - never zero - when a case has no gold code in that layer.
landmine_precision   of the codes the report raised, the share that are in the gold
                     (high or low: a low-confidence gold code is still not a
                     hallucination).
verdict_agreement    exact match on PASS/EDGE/CONDITIONAL/KILL, and the 2-level match
                     KILL vs not-KILL.
killer_question_overlap
                     a report question counts if it shares at least half of its
                     content words with a gold question, using bench/grade.py's own
                     content_words() so the two graders agree on what a word is. The
                     public bank check (killer_questions_from_bank) is carried through
                     next to it.
unknown_share        the share of the twelve axes graded U (unknown).
tokens, cost, wall time from the run row.

THE DECISION RULE
=================
Printed at the end, for B against A:

  ADOPT B  if fact recall B >= A - 0.02
           and fabrications B <= A
           and the mean landmine recall drop is at most one code per case
              (that is, at most 1 / mean gold codes per case)
           and tokens B <= 0.5 x tokens A
  UNDECIDED if the B - A differences are smaller than the within-config
           run-to-run spread (nothing was measured, only noise)
  KEEP A   otherwise

C is never in that rule. C answers a separate question - do the basic functions
survive on the cheapest realistic setup - and gets its own pass line:
stable fact recall >= 0.90, zero fabrications, hard filter consistency 1.0, at least
one killer question from the bank, a verdict present, and a schema-valid report.

Ablation configs get a factor table: each one paired against B-lean, one line per
factor saying "effect within noise", "helps" or "hurts".

REGRADING
=========
``--regrade`` re-scores every stored run against the CURRENT cases file before it
summarises. Use it after ``bench/refresh_truth.py`` fills a case's ``expected_facts``:
a run graded before that shows ``0/0`` facts forever, because the fact table it was
graded against was empty. The report comes from the run's own ``report_path``, then its
workdir, then the stored raw stdout (Claude's ``.result``, Codex's event stream). Only
the scores change - tokens, cost, wall time, the command and the raw file are kept - and
the scorecard is written through a temp file and renamed, so a sweep appending rows at
the same time is never truncated.

Usage:
  bench/ab/grade_ab.py --results bench/results/2026-09-04 --gold bench/private/gold.json
  bench/ab/grade_ab.py --results bench/results/2026-09-04 --regrade \
      --cases bench/private/cases_private.json
  bench/ab/grade_ab.py --results bench/results/2026-09-04 --baseline A-legacy \\
      --candidate B-lean --out bench/results/2026-09-04

Writes summary.md and summary.json next to the scorecard. Exit code 0 always unless
the inputs are missing (2).
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(BENCH, ".."))

sys.path.insert(0, BENCH)
import grade as grader  # noqa: E402
import run as runner  # noqa: E402

PRIVATE_GOLD = os.path.join(BENCH, "private", "gold.json")
PRIVATE_CASES = os.path.join(BENCH, "private", "cases_private.json")

# The twelve axes, from report-schema.json's own description of axis.id.
AXIS_NAMES = collections.OrderedDict([
    (1, "identity"), (2, "floor area"), (3, "age and fabric"), (4, "construction nearby"),
    (5, "crime"), (6, "management and neighbours"), (7, "agent and landlord compliance"),
    (8, "price"), (9, "aspect and light"), (10, "all-in cost"), (11, "commute and redundancy"),
    (12, "low-maintenance living")])

# Axes with no open-register input. A benchmark run has nobody to paste a listing, a
# tariff page or a review, and no register holds an aspect, so these come back U in
# every arm. That is a ceiling on the suite, not a model failure, and the summary says
# so rather than letting a reader score it as one. This mirrors "What the benchmark
# does not measure" in bench/README.md.
NO_INPUT_AXES = collections.OrderedDict([
    (6, "resident reviews sit on portals this repo will not fetch"),
    (7, "the landlord and agent on the tenancy come from a listing, not a register"),
    (8, "the advertised rent is on a portal, so price per square foot has no input"),
    (9, "no open register records which way the windows face"),
    (10, "the heat tariff and the bills come from a welcome pack somebody pastes"),
    (12, "washing machine, parcels and furniture are listing detail, not register data"),
])

VERDICTS = ("PASS", "EDGE", "CONDITIONAL", "KILL")
OVERLAP_FLOOR = 0.5          # same floor as the public bank check
MIN_CONTENT_WORDS = 4        # same as bench/grade.py

# How a landmine can be found. The order is the order the columns are printed in.
LAYERS = ("script", "mixed", "reading")
LAYER_MAP_PATH = os.path.join(HERE, "landmine_layers.yaml")
_LAYER_MAP_CACHE = {}

# The ADOPT rule, in one place so the tests and the README quote the same numbers.
DECISION = {
    "fact_recall_slack": 0.02,
    "landmine_codes_allowed_to_drop": 1.0,
    "token_ratio": 0.5,
}

# C's basic-functions pass line.
BASIC_FUNCTIONS = {
    "stable_fact_recall": 0.90,
    "fabrications": 0,
    "hard_filter_consistency": 1.0,
    "killer_questions_from_bank_min": 1,
}


# ------------------------------------------------------------------- inputs --
def load_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def parse_nested_yaml(text):
    """A deliberately small YAML reader for bench/ab/landmine_layers.yaml.

    It understands exactly what that file uses: comments, blank lines, ``key: scalar``
    and ``key:`` followed by a more-indented block of the same. No lists, no anchors,
    no multi-line scalars - anything else raises, so a mapping that needs real YAML
    fails loudly instead of being silently half-read. Standard library only, per
    docs/CONVENTIONS.md, and the same policy as bench/run.py's config reader.
    """
    root = collections.OrderedDict()
    stack = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            raise ValueError("landmine_layers line %d: lists are not supported: %r"
                             % (lineno, raw))
        if ":" not in stripped:
            raise ValueError("landmine_layers line %d: not key: value: %r" % (lineno, raw))
        indent = len(line) - len(line.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        parent = stack[-1][1]
        if value == "":
            child = collections.OrderedDict()
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = runner.scalar(value)
    return root


def load_layer_map(path=None):
    """{code: {layer, name, why}} from bench/ab/landmine_layers.yaml.

    The layer here is the code's DEFAULT. A single gold landmine may carry its own
    ``layer:`` and that wins for that case - see layer_of().
    """
    path = path or LAYER_MAP_PATH
    with io.open(path, encoding="utf-8") as fh:
        doc = parse_nested_yaml(fh.read())
    codes = doc.get("codes") or collections.OrderedDict()
    if not codes:
        raise ValueError("%s has no `codes:` block" % path)
    out = collections.OrderedDict()
    for code in sorted(codes, key=code_order):
        entry = codes[code] or {}
        layer = entry.get("layer")
        if layer not in LAYERS:
            raise ValueError("%s: %s has layer %r, expected one of %s"
                             % (path, code, layer, ", ".join(LAYERS)))
        out[code] = collections.OrderedDict([
            ("layer", layer), ("name", entry.get("name")), ("why", entry.get("why"))])
    return out


def layer_map(path=None):
    """load_layer_map(), cached per path: the grader asks for it once per landmine."""
    key = path or LAYER_MAP_PATH
    if key not in _LAYER_MAP_CACHE:
        _LAYER_MAP_CACHE[key] = load_layer_map(key)
    return _LAYER_MAP_CACHE[key]


def layer_of(mine, mapping=None):
    """The layer for ONE gold landmine entry, or None if the code is not mapped.

    A per-case override wins: an L2 whose only evidence was a sentence in a planning
    officer's report is `reading` for that case even though L2 is `mixed` in general,
    and gold.json says so by putting ``"layer": "reading"`` on that entry.
    """
    mapping = layer_map() if mapping is None else mapping
    if isinstance(mine, dict):
        own = str(mine.get("layer") or "").strip().lower()
        if own in LAYERS:
            return own
        code = mine.get("code")
    else:
        code = mine
    entry = mapping.get(code)
    return entry["layer"] if entry else None


def load_gold(path):
    """{case_id_lowercased: gold row}. Cases are named from the gold id."""
    doc = load_json(path)
    out = collections.OrderedDict()
    for row in doc.get("candidates") or []:
        out[row["id"]] = row
        out[row["id"].lower().replace("_", "-")] = row
    return out, doc


def gold_for(row, gold):
    for key in (row.get("gold_id"), row.get("case"), (row.get("case") or "").split("#")[0]):
        if key and key in gold:
            return gold[key]
    return None


def load_report(row):
    path = row.get("report_path") or (row.get("workdir") and
                                      os.path.join(row["workdir"], "report.json"))
    if path and os.path.exists(path):
        try:
            return load_json(path)
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------ metrics --
def first_candidate(report):
    cands = (report or {}).get("candidates") or []
    return cands[0] if cands and isinstance(cands[0], dict) else {}


def reported_codes(cand):
    """Every landmine code the report stood behind, as bench/grade.py counts them."""
    return grader.raised_codes(cand)


def gold_by_layer(gold_row, mapping=None):
    """{layer: set of HIGH-confidence gold codes in that layer} for one case.

    Only high-confidence codes, so the layered recalls are a partition of exactly the
    same gold that ``landmine_recall`` scores against. A code whose layer is unknown
    (not in the mapping, no override) is counted in no layer and is flagged by the
    caller rather than silently dropped into one.
    """
    mapping = layer_map() if mapping is None else mapping
    buckets = collections.OrderedDict((name, set()) for name in LAYERS)
    unmapped = set()
    for mine in gold_row.get("gold_landmines") or []:
        if not isinstance(mine, dict) or mine.get("confidence") != "high":
            continue
        name = layer_of(mine, mapping)
        if name in buckets:
            buckets[name].add(mine["code"])
        else:
            unmapped.add(mine.get("code"))
    return buckets, unmapped


def landmine_scores(cand, gold_row, found=None, mapping=None):
    """The landmine block for one run.

    ``found`` overrides the codes read out of the report - pass the row's stored
    ``landmines_found`` when the workdir is gone. ``None`` means "read the report".
    """
    high = set(m["code"] for m in gold_row["gold_landmines"] if m["confidence"] == "high")
    low = set(m["code"] for m in gold_row["gold_landmines"] if m["confidence"] == "low")
    if found is None:
        got = set(c for c in reported_codes(cand) if c.startswith("L"))
    else:
        got = set(str(c).upper() for c in found if str(c).upper().startswith("L"))

    recall = len(got & high) / float(len(high)) if high else None
    low_recall = len(got & low) / float(len(low)) if low else None
    precision = len(got & (high | low)) / float(len(got)) if got else None
    out = collections.OrderedDict([
        ("gold_high", sorted(high, key=code_order)),
        ("gold_low", sorted(low, key=code_order)),
        ("reported", sorted(got, key=code_order)),
        # The durable copy: bench/ab/grade_ab.py --regrade writes this onto the
        # scorecard row, so a run stays layer-scorable after its workdir is deleted.
        ("landmines_found", sorted(got, key=code_order)),
        ("hit_high", sorted(got & high, key=code_order)),
        ("missed_high", sorted(high - got, key=code_order)),
        ("extra", sorted(got - high - low, key=code_order)),
        ("landmine_recall", round(recall, 4) if recall is not None else None),
        ("landmine_recall_low_confidence",
         round(low_recall, 4) if low_recall is not None else None),
        ("landmine_precision", round(precision, 4) if precision is not None else None),
        ("codes_dropped", len(high - got)),
    ])
    out.update(layered_recall(gold_row, got, mapping))
    return out


def layered_recall(gold_row, got, mapping=None):
    """Recall inside each layer, over the HIGH-confidence gold codes only.

    ``got`` is the set of codes the run raised, or None when nothing was stored for
    this run. The recall is **null, never zero**, when the case has no gold code in
    that layer or when the run's codes were never persisted: a case with nothing to
    find in a layer must not drag that layer's mean down, and a run nobody can score
    must not be scored as a miss.
    """
    buckets, unmapped = gold_by_layer(gold_row, mapping)
    out = collections.OrderedDict()
    for name, codes in buckets.items():
        out["gold_%s" % name] = sorted(codes, key=code_order)
    for name, codes in buckets.items():
        if got is None or not codes:
            out["landmine_recall_%s" % name] = None
        else:
            out["landmine_recall_%s" % name] = round(len(got & codes) / float(len(codes)), 4)
    if unmapped:
        out["gold_codes_without_a_layer"] = sorted(unmapped, key=code_order)
    return out


def code_order(code):
    try:
        return int(str(code)[1:])
    except ValueError:
        return 99


def verdict_scores(cand, gold_row):
    got = ((cand.get("verdict") or {}).get("status") or "").upper() or None
    want = gold_row.get("gold_verdict")
    exact = (got == want) if (got and want) else None
    two = None
    if got and want:
        two = ((got == "KILL") == (want == "KILL"))
    return collections.OrderedDict([
        ("verdict_reported", got), ("verdict_gold", want),
        ("verdict_agreement", exact), ("verdict_agreement_kill_split", two),
        ("verdict_present", bool(got)),
    ])


CJK_RE = None


def content_words(text):
    """bench/grade.py's content words, plus CJK bigrams so Chinese questions match.

    The gold questions come from a bilingual campaign: the reviewer's own questions
    are in Chinese, the letters that were actually sent are in English. The reports
    are written in the profile's language. A Chinese gold question and an English
    report question will never match on words, and neither should they: the English
    letter pool is what covers the English reports, and it is in the gold for every
    candidate. What the bigrams buy is Chinese-to-Chinese matching, for the day
    somebody runs the suite with `language: zh-TW`.
    """
    global CJK_RE
    if CJK_RE is None:
        CJK_RE = grader.re.compile(r"[㐀-䶿一-鿿]+")
    words = set(grader.content_words(text or ""))
    for run in CJK_RE.findall(text or ""):
        if len(run) == 1:
            words.add(run)
        for i in range(len(run) - 1):
            words.add(run[i:i + 2])
    return words


def question_scores(cand, gold_row, bank):
    questions = [q for q in (cand.get("killer_questions") or []) if isinstance(q, str)
                 and q.strip()]
    gold_words = []
    for entry in gold_row.get("gold_killer_questions") or []:
        text = entry.get("text") if isinstance(entry, dict) else entry
        words = content_words(text or "")
        if words:
            gold_words.append((text, words))

    rows, matched = [], 0
    for question in questions:
        words = content_words(question)
        best, ratio = None, 0.0
        if len(words) >= MIN_CONTENT_WORDS:
            for text, gwords in gold_words:
                share = len(words & gwords) / float(len(words))
                if share > ratio:
                    best, ratio = text, share
        ok = ratio >= OVERLAP_FLOOR
        matched += 1 if ok else 0
        rows.append(collections.OrderedDict([
            ("question", question), ("best_gold", (best or "")[:110]),
            ("overlap", round(ratio, 3)), ("matches_gold", ok)]))
    return collections.OrderedDict([
        ("killer_questions", len(questions)),
        ("killer_question_overlap",
         round(matched / float(len(questions)), 4) if questions else None),
        ("killer_questions_matched", matched),
        ("gold_questions", len(gold_words)),
        ("detail", rows),
    ])


def unknown_axes(cand):
    """([axis ids graded U], how many axes were graded at all)."""
    graded = [a for a in (cand.get("axes") or []) if isinstance(a, dict)]
    out = []
    for i, axis in enumerate(graded):
        letter = str(axis.get("evidence_class") or axis.get("grade") or "").strip().upper()
        unknown = (letter == "U") or (
            not letter and grader.looks_unknown(str(axis.get("finding") or "")))
        if unknown:
            try:
                out.append(int(axis.get("id") or (i + 1)))
            except (TypeError, ValueError):
                out.append(i + 1)
    return out, len(graded)


def unknown_share(cand):
    ids, total = unknown_axes(cand)
    return round(len(ids) / float(total), 4) if total else None


def grade_row(row, gold, bank):
    """One scorecard row -> the A/B metrics for that run."""
    out = collections.OrderedDict([
        ("config", row.get("config")), ("phase", row.get("config_phase")),
        ("factor", row.get("config_factor")), ("agent", row.get("agent")),
        ("model", row.get("model")), ("budget_mode", row.get("budget_mode")),
        ("case", row.get("case")), ("run", row.get("run_index")),
        ("fact_recall", row.get("fact_recall")),
        ("stable_fact_recall", row.get("stable_fact_recall")),
        ("fabrications", row.get("fabrications")),
        ("hard_filter_consistency", row.get("hard_filter_consistency")),
        ("killer_questions_from_bank", row.get("killer_questions_from_bank")),
        ("schema_valid", row.get("schema_valid")),
        ("total_tokens", row.get("total_tokens")),
        ("total_cost_usd", row.get("total_cost_usd")),
        ("wall_time_s", row.get("wall_time_s")),
        ("note", row.get("note")),
    ])
    gold_row = gold_for(row, gold)
    report = load_report(row)
    cand = first_candidate(report)
    if gold_row is None:
        out["gold"] = None
        return out
    out["gold"] = gold_row["id"]
    if report is None:
        out["report_missing"] = True
        # The report is gone (a temp workdir was cleaned up), but a previous grading
        # may have persisted the codes onto the row. Score the landmines from those
        # rather than throwing the run away. Nothing else is recoverable: the verdict,
        # the questions and the axes stay unscored.
        stored = row.get("landmines_found")
        if isinstance(stored, list):
            out["landmine_source"] = "stored codes on the row"
            out.update(landmine_scores(None, gold_row, found=stored))
        else:
            out["landmine_source"] = None
            out.update(layered_recall(gold_row, None))
        return out
    out["landmine_source"] = "report"
    out.update(landmine_scores(cand, gold_row))
    out.update(verdict_scores(cand, gold_row))
    out.update(question_scores(cand, gold_row, bank))
    ids, graded = unknown_axes(cand)
    out["unknown_share"] = round(len(ids) / float(graded), 4) if graded else None
    out["unknown_axis_ids"] = sorted(set(ids))
    out["axes_graded"] = graded
    return out


# ---------------------------------------------------------------- aggregate --
NUMERIC = ("fact_recall", "stable_fact_recall", "fabrications", "hard_filter_consistency",
           "killer_questions_from_bank", "landmine_recall", "landmine_precision",
           "landmine_recall_low_confidence",
           "landmine_recall_script", "landmine_recall_mixed", "landmine_recall_reading",
           "killer_question_overlap", "unknown_share",
           "codes_dropped", "total_tokens", "total_cost_usd", "wall_time_s")
LAYER_METRICS = tuple("landmine_recall_%s" % name for name in LAYERS)
BOOLEAN = ("verdict_agreement", "verdict_agreement_kill_split", "schema_valid",
           "verdict_present")


def stats(values):
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not values:
        return None
    return collections.OrderedDict([
        ("n", len(values)),
        ("mean", round(sum(values) / float(len(values)), 4)),
        ("min", round(min(values), 4)), ("max", round(max(values), 4)),
        ("spread", round(max(values) - min(values), 4)),
    ])


def rate(values):
    values = [v for v in values if isinstance(v, bool)]
    if not values:
        return None
    return round(sum(1 for v in values if v) / float(len(values)), 4)


def aggregate(rows):
    """config -> {metric: stats}, plus the boolean rates."""
    out = collections.OrderedDict()
    by_config = collections.OrderedDict()
    for row in rows:
        by_config.setdefault(row.get("config"), []).append(row)
    for name, group in by_config.items():
        summary = collections.OrderedDict([("runs", len(group)),
                                           ("cases", len(set(r["case"] for r in group))),
                                           ("phase", group[0].get("phase")),
                                           ("factor", group[0].get("factor")),
                                           ("agent", group[0].get("agent"))])
        for metric in NUMERIC:
            summary[metric] = stats([r.get(metric) for r in group])
        for metric in BOOLEAN:
            summary[metric] = rate([r.get(metric) for r in group])
        counts = collections.Counter()
        with_axes = 0
        for row in group:
            if row.get("axes_graded"):
                with_axes += 1
                for axis in row.get("unknown_axis_ids") or []:
                    counts[axis] += 1
        summary["runs_with_axes"] = with_axes
        summary["unknown_axis_counts"] = collections.OrderedDict(
            (str(a), counts[a]) for a in sorted(counts))
        out[name] = summary
    return out


def per_case_mean(rows, config, metric):
    """{case: mean of that metric over that config's runs}."""
    buckets = collections.OrderedDict()
    for row in rows:
        if row.get("config") != config:
            continue
        value = row.get(metric)
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            buckets.setdefault(row["case"], []).append(value)
    return collections.OrderedDict(
        (case, sum(vals) / float(len(vals))) for case, vals in buckets.items())


def paired(rows, base, cand, metric):
    """B - A per case, plus how often B >= A."""
    a = per_case_mean(rows, base, metric)
    b = per_case_mean(rows, cand, metric)
    shared = [c for c in b if c in a]
    diffs = collections.OrderedDict((c, round(b[c] - a[c], 4)) for c in shared)
    better = sum(1 for c in shared if b[c] >= a[c])
    return collections.OrderedDict([
        ("metric", metric), ("cases", len(shared)),
        ("per_case", diffs),
        ("mean_diff", round(sum(diffs.values()) / float(len(diffs)), 4) if diffs else None),
        ("candidate_at_least_baseline", better),
        ("candidate_worse", len(shared) - better),
    ])


def within_spread(rows, config, metric):
    """The largest run-to-run spread this config showed on one case: the noise floor."""
    buckets = collections.OrderedDict()
    for row in rows:
        if row.get("config") != config:
            continue
        value = row.get(metric)
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            buckets.setdefault(row["case"], []).append(value)
    spreads = [max(v) - min(v) for v in buckets.values() if len(v) > 1]
    return round(max(spreads), 4) if spreads else None


# ----------------------------------------------------------------- decision --
def decide(rows, agg, base, cand, gold_doc):
    """The ADOPT / UNDECIDED / KEEP rule, with every input it used."""
    reasons = []
    a, b = agg.get(base), agg.get(cand)
    if not a or not b:
        return collections.OrderedDict([
            ("decision", "NO DATA"),
            ("why", "no runs for %s" % (base if not a else cand)),
            ("inputs", collections.OrderedDict())])

    def mean(config, metric):
        block = agg[config].get(metric)
        return block["mean"] if block else None

    # Only the cases this sweep actually ran, so "one code per case" means one code of
    # the cases in front of us, not one code of the whole twenty.
    ran = set(r.get("gold") for r in rows if r.get("gold"))
    gold_codes = [len([m for m in row["gold_landmines"] if m["confidence"] == "high"])
                  for row in gold_doc.get("candidates") or []
                  if not ran or row["id"] in ran]
    mean_gold_codes = (sum(gold_codes) / float(len(gold_codes))) if gold_codes else None

    fr_a, fr_b = mean(base, "fact_recall"), mean(cand, "fact_recall")
    fab_a, fab_b = mean(base, "fabrications"), mean(cand, "fabrications")
    lm_a, lm_b = mean(base, "landmine_recall"), mean(cand, "landmine_recall")
    tok_a, tok_b = mean(base, "total_tokens"), mean(cand, "total_tokens")

    facts_ok = (fr_a is None or fr_b is None or
                fr_b >= fr_a - DECISION["fact_recall_slack"])
    fabs_ok = (fab_a is None or fab_b is None or fab_b <= fab_a)
    if mean_gold_codes and lm_a is not None and lm_b is not None:
        allowed = DECISION["landmine_codes_allowed_to_drop"] / mean_gold_codes
        mines_ok = (lm_a - lm_b) <= allowed
    else:
        allowed, mines_ok = None, True
    tokens_ok = (tok_a is None or tok_b is None or
                 tok_b <= DECISION["token_ratio"] * tok_a)

    noise = collections.OrderedDict()
    signal_beats_noise = False
    for metric in ("fact_recall", "landmine_recall", "verdict_agreement"):
        floor = max([x for x in (within_spread(rows, base, metric),
                                 within_spread(rows, cand, metric)) if x is not None] or [0])
        diff = paired(rows, base, cand, metric)["mean_diff"]
        noise[metric] = collections.OrderedDict([("run_to_run_spread", floor),
                                                 ("mean_diff", diff)])
        if diff is not None and abs(diff) > floor:
            signal_beats_noise = True

    if facts_ok and fabs_ok and mines_ok and tokens_ok:
        decision = "ADOPT B"
        reasons.append("every clause of the rule held")
    elif not signal_beats_noise:
        decision = "UNDECIDED"
        reasons.append("the B - A differences are inside the run-to-run spread of the arms "
                       "themselves: nothing was measured yet, only noise. Add runs.")
    else:
        decision = "KEEP A"
        for ok, why in ((facts_ok, "fact recall fell by more than %.2f"
                         % DECISION["fact_recall_slack"]),
                        (fabs_ok, "fabrications went up"),
                        (mines_ok, "landmine recall fell by more than one code per case"),
                        (tokens_ok, "tokens did not fall to half of A")):
            if not ok:
                reasons.append(why)

    return collections.OrderedDict([
        ("decision", decision),
        ("baseline", base), ("candidate", cand),
        ("why", "; ".join(reasons)),
        ("inputs", collections.OrderedDict([
            ("fact_recall", [fr_a, fr_b, facts_ok]),
            ("fabrications", [fab_a, fab_b, fabs_ok]),
            ("landmine_recall", [lm_a, lm_b, mines_ok]),
            ("landmine_recall_drop_allowed", round(allowed, 4) if allowed else None),
            ("mean_gold_high_codes_per_case",
             round(mean_gold_codes, 2) if mean_gold_codes else None),
            ("total_tokens", [tok_a, tok_b, tokens_ok]),
        ])),
        ("noise", noise),
    ])


def basic_functions(agg, config):
    """C's own pass line. Never part of the ADOPT rule."""
    block = agg.get(config)
    if not block:
        return None
    checks = collections.OrderedDict()
    stable = block.get("stable_fact_recall")
    checks["stable_fact_recall >= %.2f" % BASIC_FUNCTIONS["stable_fact_recall"]] = (
        stable is not None and stable["mean"] >= BASIC_FUNCTIONS["stable_fact_recall"])
    fabs = block.get("fabrications")
    checks["fabrications == 0"] = (fabs is not None and fabs["max"] == 0)
    hard = block.get("hard_filter_consistency")
    checks["hard_filter_consistency == 1.0"] = (
        hard is not None and hard["min"] >= BASIC_FUNCTIONS["hard_filter_consistency"])
    bank = block.get("killer_questions_from_bank")
    checks["at least one killer question from the bank"] = (
        bank is not None and bank["min"] > 0)
    checks["a verdict is present"] = bool(block.get("verdict_present"))
    checks["schema valid"] = (block.get("schema_valid") == 1.0)
    return collections.OrderedDict([
        ("config", config),
        ("result", "PASS" if all(checks.values()) else "FAIL"),
        ("checks", checks),
    ])


def factor_table(rows, agg, base):
    """One line per ablation config: within noise / helps / hurts."""
    out = []
    # The three layered recalls are reported, never voted on: the effect word stays a
    # function of fact recall, overall landmine recall and verdict agreement, exactly
    # as before, so the ablation verdicts do not move because a column was added.
    metrics = ("fact_recall", "fabrications", "landmine_recall", "verdict_agreement",
               "total_tokens", "wall_time_s") + LAYER_METRICS
    for name, block in agg.items():
        if name == base or block.get("phase") != "ablation":
            continue
        row = collections.OrderedDict([("config", name), ("factor", block.get("factor"))])
        verdicts = []
        for metric in metrics:
            diff = paired(rows, base, name, metric)
            floor = max([x for x in (within_spread(rows, base, metric),
                                     within_spread(rows, name, metric))
                         if x is not None] or [0])
            row[metric] = collections.OrderedDict([
                ("mean_diff", diff["mean_diff"]),
                ("cases", diff["cases"]),
                ("candidate_at_least_baseline", diff["candidate_at_least_baseline"]),
                ("run_to_run_spread", floor),
            ])
            if metric in ("fact_recall", "landmine_recall", "verdict_agreement") \
                    and diff["mean_diff"] is not None:
                if abs(diff["mean_diff"]) <= floor:
                    verdicts.append(0)
                else:
                    verdicts.append(1 if diff["mean_diff"] > 0 else -1)
        if not verdicts or all(v == 0 for v in verdicts):
            row["effect"] = "effect within noise"
        elif sum(verdicts) > 0:
            row["effect"] = "helps"
        elif sum(verdicts) < 0:
            row["effect"] = "hurts"
        else:
            row["effect"] = "mixed, effect within noise on balance"
        out.append(row)
    return out


# --------------------------------------------------------------- regrading --
def looks_like_report(obj):
    """A report, not the schema the agent read on its way to writing one.

    ``report-schema.json`` also has a top-level ``candidates`` key, so a naive search
    of an event stream finds the schema fragment and scores it. A report has
    ``candidates`` as a LIST whose first entry is a candidate with a verdict; the
    schema has it as an object with ``type``/``items``.
    """
    if not isinstance(obj, dict):
        return False
    if any(k in obj for k in ("$schema", "definitions", "properties")):
        return False
    cands = obj.get("candidates")
    if not isinstance(cands, list) or not cands or not isinstance(cands[0], dict):
        return False
    first = cands[0]
    return bool(first.get("verdict") or first.get("axes") or first.get("identity"))


def report_in(node):
    """The last report hiding in an already-parsed wrapper, or None.

    Claude Code's ``--output-format json`` puts the answer in ``.result``, often inside
    a ```json fence; Codex's ``--json`` prints one event object per line with the text
    in a nested string. Both are "a JSON object hiding in a string field", so both are
    handled the same way. The LAST one wins: an agent that revises its report prints
    the good one last.
    """
    if looks_like_report(node):
        return node
    found = None
    for value in strings_in(node):
        if "candidates" not in value:
            continue
        inner = runner.first_json_object(value)
        if looks_like_report(inner):
            found = inner
    return found


def scan_for_report(text):
    """(report, where) - the report object inside an agent's stored stdout."""
    if not text:
        return None, None

    try:                                        # the whole file is one JSON document
        whole = json.loads(text)
    except ValueError:
        whole = None
    if whole is not None:
        found = report_in(whole)
        if found is not None:
            return found, "raw stdout, wrapper document"

    last = None                                 # ... or is a JSONL event stream
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{") or "candidates" not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        found = report_in(event)
        if found is not None:
            last = found                        # the last one wins: agents revise
    if last is not None:
        return last, "raw stdout, event stream"

    obj = runner.first_json_object(text)        # ... or starts with one
    if isinstance(obj, dict):
        found = report_in(obj)
        if found is not None:
            return found, "raw stdout, first object"

    for m in list(re.finditer(r'"candidates"', text))[:8]:      # last resort
        base = max(0, m.start() - 20000)
        window = text[base:m.start()]
        for i in [pos for pos, ch in enumerate(window) if ch == "{"][-60:]:
            inner = runner.first_json_object(text[base + i:])
            if looks_like_report(inner):
                return inner, "raw stdout, scanned"
    return None, None


def strings_in(node, depth=0):
    if depth > 6:
        return []
    if isinstance(node, str):
        return [node]
    out = []
    if isinstance(node, dict):
        for value in node.values():
            out.extend(strings_in(value, depth + 1))
    elif isinstance(node, list):
        for value in node:
            out.extend(strings_in(value, depth + 1))
    return out


def locate_report(row, results_dir):
    """(report, where) for one scorecard row, most reliable source first."""
    persisted = os.path.join(results_dir, "raw", runner.raw_name(row.get("config"), row.get("case"),
                                                                 row.get("run_index") or 1).replace(".json", ".report.json"))
    for path, label in ((persisted, "persisted copy"),
                        (row.get("report_path"), "report_path"),
                        (os.path.join(row.get("workdir") or "", "report.json"), "workdir")):
        if path and os.path.exists(path):
            try:
                return load_json(path), "%s %s" % (label, path)
            except ValueError:
                pass
    workdir = row.get("workdir")
    if workdir and os.path.isdir(workdir):
        for base, _dirs, files in os.walk(workdir):
            if ".claude" in base or ".agents" in base:
                continue
            if "report.json" in files:
                try:
                    return load_json(os.path.join(base, "report.json")), "workdir walk"
                except ValueError:
                    pass
    raw = row.get("raw")
    if not (raw and os.path.exists(raw)):
        guess = os.path.join(results_dir, "raw",
                             runner.raw_name(row.get("config"), row.get("case"),
                                             row.get("run_index") or 1))
        raw = guess if os.path.exists(guess) else None
    if raw:
        with io.open(raw, encoding="utf-8", errors="replace") as fh:
            report, where = scan_for_report(fh.read())
        if report is not None:
            return report, "%s (%s)" % (where, os.path.basename(raw))
    return None, None


def row_key(row):
    return (row.get("run_at"), row.get("config"), row.get("case"), row.get("run_index"))


def config_of(row):
    return collections.OrderedDict([
        ("name", row.get("config")), ("phase", row.get("config_phase")),
        ("factor", row.get("config_factor")), ("budget_mode", row.get("budget_mode")),
        ("worker_model", row.get("worker_model"))])


def regrade(results_dir, cases_path):
    """Re-score every stored run against the CURRENT cases file, in place.

    Runs graded before ``bench/refresh_truth.py`` filled a case's ``expected_facts``
    show ``0/0`` facts forever, because the fact table they were graded against was
    empty. This rebuilds those rows from the report the run actually produced, keeps
    what only the run knows (tokens, cost, wall time, the command, the raw file), and
    writes the scorecard back atomically so a live sweep appending rows alongside is
    never truncated.
    """
    scorecard = os.path.join(results_dir, "scorecard.json")
    if not os.path.exists(scorecard):
        return None
    cases = collections.OrderedDict(
        (case["id"], case) for case in load_json(cases_path).get("evals") or [])

    updates, notes = {}, []
    for row in load_json(scorecard):
        label = "%s / %s / run %s" % (row.get("config"), row.get("case"),
                                      row.get("run_index"))
        case = cases.get((row.get("case") or "").split("#")[0])
        if case is None:
            notes.append("%s: no case of that id in %s" % (label, os.path.basename(cases_path)))
            continue
        report, where = locate_report(row, results_dir)
        if report is None:
            notes.append("%s: no stored report to re-score (%s)"
                         % (label, row.get("note") or "no note"))
            continue
        card = grader.grade(report, case, grader.case_profile_path(cases_path, case))
        fresh = runner.make_row(row.get("agent") or "claude", row.get("model"), case, card,
                                row.get("wall_time_s"), row.get("tokens"), row.get("workdir"),
                                row.get("command"), row.get("note"), None, config_of(row),
                                row.get("run_index"), row.get("raw"))
        fresh["run_at"] = row.get("run_at")          # the row keeps its identity
        fresh["report_path"] = row.get("report_path") or fresh.get("report_path")
        # Only the scores are recomputed. What only the run itself knew is carried over
        # whenever re-deriving it would give less than the row already has.
        for field in ("total_tokens", "total_cost_usd", "cost_note", "tokens",
                      "wall_time_s", "raw", "workdir", "command"):
            if fresh.get(field) in (None, "") and row.get(field) not in (None, ""):
                fresh[field] = row[field]
        fresh["regraded_at"] = (datetime.datetime.utcnow().replace(microsecond=0).isoformat()
                                + "Z")
        fresh["regraded_from"] = where
        # Persist the codes the report raised. The report itself lives in a temp workdir
        # that gets cleaned up; without this, a run can never be re-scored - by layer or
        # at all - once the machine is tidied. Gold-free: these are the run's own codes.
        fresh["landmines_found"] = sorted(
            (c for c in grader.raised_codes(first_candidate(report)) if c.startswith("L")),
            key=code_order)
        updates[row_key(row)] = fresh
        notes.append("%s: %s facts, from %s" % (label, fresh.get("facts"), where))

    # Re-read as late as possible: a live sweep may have appended rows since.
    rows = load_json(scorecard)
    merged = [updates.get(row_key(row), row) for row in rows]
    runner.write_scorecard(merged, results_dir, os.path.basename(results_dir.rstrip(os.sep)))
    return collections.OrderedDict([("rows", len(rows)), ("regraded", len(updates)),
                                    ("cases", cases_path), ("notes", notes)])


# ---------------------------------------------------------------- layers --
def layer_breakdown(rows, gold_doc, mapping=None):
    """What the three layered recalls are scored against, and how many runs can be.

    Counts only the cases this sweep actually ran, so "mean codes per case" is the
    mean of the cases in front of the reader, not of the whole gold set.
    """
    mapping = layer_map() if mapping is None else mapping
    ran = collections.OrderedDict((r["gold"], None) for r in rows if r.get("gold"))
    per_layer = collections.OrderedDict(
        (name, collections.OrderedDict([("codes", 0), ("cases_with_any", 0)]))
        for name in LAYERS)
    unmapped = set()
    for cand in gold_doc.get("candidates") or []:
        if cand.get("id") not in ran:
            continue
        buckets, missing = gold_by_layer(cand, mapping)
        unmapped |= missing
        for name, codes in buckets.items():
            per_layer[name]["codes"] += len(codes)
            per_layer[name]["cases_with_any"] += 1 if codes else 0
    for name in LAYERS:
        per_layer[name]["mean_codes_per_case"] = (
            round(per_layer[name]["codes"] / float(len(ran)), 3) if ran else None)
    overrides = []
    for cand in gold_doc.get("candidates") or []:
        if cand.get("id") not in ran:
            continue
        for mine in cand.get("gold_landmines") or []:
            own = str((mine or {}).get("layer") or "").strip().lower()
            code = (mine or {}).get("code")
            default = (mapping.get(code) or {}).get("layer")
            if own in LAYERS and own != default:
                overrides.append("%s %s: %s (default %s)" % (cand["id"], code, own, default))
    return collections.OrderedDict([
        ("map", os.path.relpath(LAYER_MAP_PATH, ROOT)),
        ("layer_of_code", collections.OrderedDict(
            (code, entry["layer"]) for code, entry in mapping.items())),
        ("cases", len(ran)),
        ("per_layer", per_layer),
        ("runs", len(rows)),
        ("runs_with_codes", sum(1 for r in rows if r.get("landmine_source"))),
        ("per_case_overrides", overrides),
        ("codes_without_a_layer", sorted(unmapped, key=code_order)),
    ])


# ------------------------------------------------------------ why unknown --
def unknown_breakdown(agg):
    """Which axes come back U, per config, and which are U in every arm.

    An axis that is unknown in every arm is a ceiling on the suite, not a difference
    between the arms: nobody pastes resident reviews or a planning officer's report
    into a benchmark run, so the axes that need pasted text have no input to work
    from. Saying that out loud stops a reader scoring it as a model failure.
    """
    configs = [name for name, block in agg.items() if block.get("runs_with_axes")]
    rows = []
    for axis, label in AXIS_NAMES.items():
        per_config = collections.OrderedDict()
        for name in configs:
            block = agg[name]
            runs = block.get("runs_with_axes") or 0
            hits = (block.get("unknown_axis_counts") or {}).get(str(axis), 0)
            per_config[name] = collections.OrderedDict([
                ("runs", runs), ("unknown", hits),
                ("share", round(hits / float(runs), 4) if runs else None)])
        shares = [v["share"] for v in per_config.values() if v["share"] is not None]
        rows.append(collections.OrderedDict([
            ("axis", axis), ("name", label),
            ("no_input", axis in NO_INPUT_AXES),
            ("no_input_reason", NO_INPUT_AXES.get(axis)),
            ("per_config", per_config),
            ("every_arm", bool(shares) and min(shares) == 1.0),
            ("no_arm", bool(shares) and max(shares) == 0.0),
            ("spread", round(max(shares) - min(shares), 4) if shares else None)]))
    shared = [r["axis"] for r in rows if r["every_arm"]]
    differs = sorted((r for r in rows if r["spread"]), key=lambda r: -r["spread"])
    return collections.OrderedDict([
        ("configs", configs), ("axes", rows),
        ("unknown_in_every_arm", shared),
        ("shared_ceiling_has_no_input",
         bool(shared) and all(a in NO_INPUT_AXES for a in shared)),
        ("shared_ceiling_reasons", collections.OrderedDict(
            (str(a), NO_INPUT_AXES[a]) for a in shared if a in NO_INPUT_AXES)),
        ("differs_between_arms", [r["axis"] for r in differs[:4]]),
    ])


# ------------------------------------------------------------------ reports --
def fmt(value, spec="%.3f"):
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return spec % value
    return str(value)


def mstat(block, key="mean", spec="%.3f"):
    if not block:
        return "-"
    return fmt(block.get(key), spec)


def markdown(summary):
    agg = summary["per_config"]
    lines = ["# vet-flat A/B, %s" % summary["results_dir"], "",
             "%d runs, %d configs, %d cases, gold %s."
             % (summary["runs"], len(agg), summary["cases"], summary["gold"]), "",
             "## Per config (mean over runs, min-max in brackets)", "",
             "| config | phase | runs | facts | stable | fab | landmine recall | script "
             "| mixed | reading | landmine prec "
             "| verdict exact | KILL split | questions vs gold | from bank | unknown | tokens "
             "| cost $ | wall s |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:"
             "|---:|---:|---:|"]
    for name, block in agg.items():
        lines.append("| %s | %s | %d | %s | %s | %s | %s [%s-%s] | %s [%s-%s] | %s [%s-%s] "
                     "| %s [%s-%s] | %s | %s | %s | %s | %s | %s "
                     "| %s [%s-%s] | %s | %s |"
                     % (name, block.get("phase") or "-", block["runs"],
                        mstat(block["fact_recall"]), mstat(block["stable_fact_recall"]),
                        mstat(block["fabrications"], spec="%.2f"),
                        mstat(block["landmine_recall"]),
                        mstat(block["landmine_recall"], "min"),
                        mstat(block["landmine_recall"], "max"),
                        mstat(block["landmine_recall_script"]),
                        mstat(block["landmine_recall_script"], "min"),
                        mstat(block["landmine_recall_script"], "max"),
                        mstat(block["landmine_recall_mixed"]),
                        mstat(block["landmine_recall_mixed"], "min"),
                        mstat(block["landmine_recall_mixed"], "max"),
                        mstat(block["landmine_recall_reading"]),
                        mstat(block["landmine_recall_reading"], "min"),
                        mstat(block["landmine_recall_reading"], "max"),
                        mstat(block["landmine_precision"]),
                        fmt(block["verdict_agreement"]),
                        fmt(block["verdict_agreement_kill_split"]),
                        mstat(block["killer_question_overlap"]),
                        mstat(block["killer_questions_from_bank"]),
                        mstat(block["unknown_share"]),
                        mstat(block["total_tokens"], spec="%.0f"),
                        mstat(block["total_tokens"], "min", "%.0f"),
                        mstat(block["total_tokens"], "max", "%.0f"),
                        mstat(block["total_cost_usd"], spec="%.4f"),
                        mstat(block["wall_time_s"], spec="%.0f")))

    lay = summary.get("layers") or {}
    if lay.get("per_layer"):
        lines += ["", "## Landmine recall by layer", "",
                  "The gold set was written by a person who read the resident reviews, the "
                  "planning documents and the tenancy paperwork, and who walked the route "
                  "home. That is what makes it a real test, and it is also a tilt: an arm "
                  "that works only from parsed registers is being marked against sources it "
                  "never saw. So every gold landmine carries a **layer** saying how it can "
                  "be found, and recall is reported inside each layer as well as overall.",
                  "",
                  "* **script** - a repository script establishes it on its own "
                  "(`epc.py`, `crime.py`, `roads.py`, `planning.py`, `company.py`). An arm "
                  "with no web tools should still find it, so a miss here is a harness or a "
                  "reasoning failure, never a missing input. **This is the column that "
                  "compares arms fairly.**",
                  "* **mixed** - a script narrows it or gives half the number and prose "
                  "gives the rest. Read it next to the script column before concluding "
                  "anything.",
                  "* **reading** - only prose establishes it: reviews, an agreement, a fee "
                  "schedule, a criteria page. Nobody pastes those into a benchmark run, so "
                  "this column is close to a ceiling and a low number here is mostly the "
                  "suite talking about itself, not a model that failed.", "",
                  "The mapping is `%s`; a single gold landmine may override its code's "
                  "layer with its own `layer:`. Recall in a layer is **null, not zero**, "
                  "when a case has no gold code in that layer, so a case with nothing to "
                  "find never drags the mean down." % lay.get("map"), "",
                  "| layer | gold codes across the %d cases run | cases with at least one "
                  "| mean codes per case |" % lay.get("cases", 0),
                  "|---|---:|---:|---:|"]
        for name in LAYERS:
            block = lay["per_layer"][name]
            lines.append("| %s | %d | %d | %s |"
                         % (name, block["codes"], block["cases_with_any"],
                            fmt(block["mean_codes_per_case"], "%.2f")))
        lines += ["", "%d of %d runs had landmine codes to score (a run whose report is gone "
                      "and whose codes were never persisted scores null in every layer, "
                      "including the overall recall)."
                  % (lay.get("runs_with_codes", 0), lay.get("runs", 0))]
        if lay.get("per_case_overrides"):
            lines += ["", "Per-case overrides in the gold: %s."
                      % "; ".join(lay["per_case_overrides"])]
        if lay.get("codes_without_a_layer"):
            lines += ["", "**Gold codes with no layer:** %s. Add them to `%s`; they are "
                          "counted in the overall recall and in none of the three columns."
                      % (", ".join(lay["codes_without_a_layer"]), lay.get("map"))]

    unk = summary.get("unknown") or {}
    if unk.get("configs"):
        lines += ["", "## Why an axis is unknown", "",
                  "Share of runs in which each axis came back `U`. **no input** marks the "
                  "axes with nothing for a benchmark run to work from: the material is on a "
                  "portal this repo will not fetch, or it is a document somebody has to paste, "
                  "or no register records it at all. Those come back unknown in every arm. "
                  "That is a ceiling on the suite, not a model that failed - read the "
                  "**spread** column, which is where the arms actually differ.", "",
                  "| axis | what it is | no input | " + " | ".join(unk["configs"])
                  + " | spread |",
                  "|---:|---|---|" + "---:|" * (len(unk["configs"]) + 1)]
        for row in unk["axes"]:
            lines.append("| %d | %s | %s | %s | %s |"
                         % (row["axis"], row["name"], "yes" if row["no_input"] else "",
                            " | ".join(fmt(row["per_config"][c]["share"], "%.2f")
                                       for c in unk["configs"]),
                            fmt(row["spread"], "%.2f")))
        shared = unk.get("unknown_in_every_arm") or []
        if shared:
            lines += ["", "Unknown in **every** arm: %s."
                      % ", ".join("axis %d (%s)" % (a, AXIS_NAMES[a]) for a in shared)]
            if unk.get("shared_ceiling_has_no_input"):
                lines += ["", "Every one of them is an axis with no input, so this is the "
                              "suite's ceiling and not a difference between the arms:"]
            else:
                lines += ["", "Not all of them are axes with no input, so at least one is a "
                              "real gap worth chasing. The ones that are expected:"]
            lines.append("")
            for axis in shared:
                lines.append("* axis %d (%s) - %s" % (axis, AXIS_NAMES[axis],
                                                      NO_INPUT_AXES.get(axis)
                                                      or "**no reason on file: investigate**"))
        differ = unk.get("differs_between_arms") or []
        if differ:
            lines += ["", "Where the arms actually differ: %s. Those are the axes to read."
                      % ", ".join("axis %d (%s)" % (a, AXIS_NAMES[a]) for a in differ)]

    if summary.get("paired"):
        lines += ["", "## Paired differences, %s minus %s, per case"
                  % (summary["candidate"], summary["baseline"]), "",
                  "| metric | mean diff | cases | candidate >= baseline | run-to-run spread |",
                  "|---|---:|---:|---:|---:|"]
        for metric, block in summary["paired"].items():
            lines.append("| %s | %s | %d | %d/%d | %s |"
                         % (metric, fmt(block["mean_diff"]), block["cases"],
                            block["candidate_at_least_baseline"], block["cases"],
                            fmt(summary["noise_floor"].get(metric))))
        lines += ["", "Per case, %s minus %s:" % (summary["candidate"], summary["baseline"]),
                  "", "| case | " + " | ".join(summary["paired"]) + " |",
                  "|---" * (len(summary["paired"]) + 1) + "|"]
        cases = sorted(set(c for b in summary["paired"].values() for c in b["per_case"]))
        for case in cases:
            lines.append("| %s | %s |"
                         % (case, " | ".join(fmt(summary["paired"][m]["per_case"].get(case))
                                             for m in summary["paired"])))

    if summary.get("factors"):
        lines += ["", "## Ablation: one factor at a time against %s" % summary["baseline_lean"],
                  "",
                  "| config | factor | effect | facts | landmine recall | script | mixed "
                  "| reading | verdict | tokens | wall s |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for row in summary["factors"]:
            lines.append("| %s | %s | **%s** | %s | %s | %s | %s | %s | %s | %s | %s |"
                         % (row["config"], row["factor"], row["effect"],
                            fmt(row["fact_recall"]["mean_diff"]),
                            fmt(row["landmine_recall"]["mean_diff"]),
                            fmt(row["landmine_recall_script"]["mean_diff"]),
                            fmt(row["landmine_recall_mixed"]["mean_diff"]),
                            fmt(row["landmine_recall_reading"]["mean_diff"]),
                            fmt(row["verdict_agreement"]["mean_diff"]),
                            fmt(row["total_tokens"]["mean_diff"], "%.0f"),
                            fmt(row["wall_time_s"]["mean_diff"], "%.0f")))
        lines += ["", "The three layered columns are reported, not voted on: the effect "
                      "word is still decided by facts, overall landmine recall and verdict "
                      "agreement alone. They are there to say *where* a factor moved things "
                      "- a factor that only moves the `reading` column moved the arm's access "
                      "to prose, not its judgment."]

    if summary.get("basic_functions"):
        lines += ["", "## Basic functions on the cheapest setup", ""]
        for block in summary["basic_functions"]:
            lines += ["**%s: %s**" % (block["config"], block["result"]), ""]
            for check, ok in block["checks"].items():
                lines.append("* %s %s" % ("PASS" if ok else "FAIL", check))
            lines.append("")

    dec = summary.get("decision") or {}
    lines += ["", "## Decision", "", "**%s**" % dec.get("decision", "NO DATA"), ""]
    if dec.get("why"):
        lines += [dec["why"], ""]
    for key, value in (dec.get("inputs") or {}).items():
        lines.append("* %s: %s" % (key, json.dumps(value)))
    lines += ["", "The rule: ADOPT B if fact recall B >= A - %.2f and fabrications B <= A, and "
                  "the mean landmine recall drop is at most one code per case, and tokens "
                  "B <= %.1f x A. UNDECIDED if the differences are smaller than the "
                  "within-config run-to-run spread. Otherwise KEEP A."
              % (DECISION["fact_recall_slack"], DECISION["token_ratio"])]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------- main --
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True, help="bench/results/<date>")
    ap.add_argument("--gold", default=PRIVATE_GOLD)
    ap.add_argument("--regrade", action="store_true",
                    help="before summarising, re-score every stored run against the CURRENT "
                         "cases file and rewrite its scorecard row in place. Use this after "
                         "bench/refresh_truth.py fills a case's expected_facts: runs graded "
                         "before that show 0/0 facts forever otherwise")
    ap.add_argument("--cases", default=PRIVATE_CASES,
                    help="the cases file --regrade scores against; default "
                         "bench/private/cases_private.json")
    ap.add_argument("--baseline", default="A-legacy")
    ap.add_argument("--candidate", default="B-lean")
    ap.add_argument("--basic", default="C-twenty,codex-C-terra-lite,codex-C-luna-lite",
                    help="comma-separated configs judged by the basic-functions line "
                         "instead of the adoption rule")
    ap.add_argument("--out", help="where to write summary.md and summary.json; default is "
                                  "--results")
    ap.add_argument("--quiet", action="store_true")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    scorecard = os.path.join(args.results, "scorecard.json")
    if not os.path.exists(scorecard):
        print("no scorecard at %s" % scorecard, file=sys.stderr)
        return 2
    if not os.path.exists(args.gold):
        print("no gold at %s  (run bench/private/build_gold.py)" % args.gold, file=sys.stderr)
        return 2

    if args.regrade:
        if not os.path.exists(args.cases):
            print("no cases file at %s" % args.cases, file=sys.stderr)
            return 2
        done = regrade(args.results, args.cases)
        if done:
            print("regraded %d of %d rows against %s"
                  % (done["regraded"], done["rows"], os.path.basename(done["cases"])))
            for note in done["notes"]:
                print("  %s" % note)
            print("")

    gold, gold_doc = load_gold(args.gold)
    bank = grader.parse_question_bank()
    raw_rows = load_json(scorecard)
    rows = [grade_row(row, gold, bank) for row in raw_rows]
    agg = aggregate(rows)

    metrics = ("fact_recall", "stable_fact_recall", "fabrications", "landmine_recall",
               "landmine_precision", "verdict_agreement", "killer_question_overlap",
               "unknown_share", "total_tokens", "total_cost_usd", "wall_time_s")
    paired_blocks = collections.OrderedDict()
    noise_floor = collections.OrderedDict()
    if args.baseline in agg and args.candidate in agg:
        for metric in metrics:
            paired_blocks[metric] = paired(rows, args.baseline, args.candidate, metric)
            noise_floor[metric] = max(
                [x for x in (within_spread(rows, args.baseline, metric),
                             within_spread(rows, args.candidate, metric))
                 if x is not None] or [0])

    summary = collections.OrderedDict([
        ("results_dir", args.results),
        ("gold", args.gold),
        ("runs", len(rows)),
        ("cases", len(set(r["case"] for r in rows))),
        ("baseline", args.baseline), ("candidate", args.candidate),
        ("baseline_lean", args.candidate),
        ("per_config", agg),
        ("paired", paired_blocks),
        ("noise_floor", noise_floor),
        ("layers", layer_breakdown(rows, gold_doc)),
        ("unknown", unknown_breakdown(agg)),
        ("factors", factor_table(rows, agg, args.candidate)),
        ("basic_functions", [b for b in (basic_functions(agg, n.strip())
                                         for n in args.basic.split(",") if n.strip())
                             if b]),
        ("decision", decide(rows, agg, args.baseline, args.candidate, gold_doc)),
        ("per_run", rows),
    ])

    out_dir = args.out or args.results
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    text = markdown(summary)
    with io.open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    with io.open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    if not args.quiet:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
