#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The document-reading ablation: four reading disciplines, three model tiers, two vendors.

THE QUESTION
An agent is handed a long pasted document - a tenancy agreement, an operator's terms, a
planning officer's report, a saved review page - and has to find the few sentences that
answer a question. Which reading discipline works, and for which model tier?

  R0  full read     the agent may only `Read` the document (ranges allowed)
  R1  grep only     `grep`/`rg`, then `Read` ranges around the hits
  R2  find.py       the skill's BM25-over-paragraphs finder with its thick view, then
                    `Read` ranges; grep stays allowed as a fallback
  R3  scan.py       the fixed regexes only, then `Read` ranges. Fixed-form questions only

Three hypotheses are UNDER TEST here, not assumed - they come from another project, on
another corpus, and this repository owes them a re-test:
  H1  a thick view (whole paragraph plus neighbours) helps cheap models most
  H2  a rule-heavy interface hurts weak models and leaves strong ones unchanged
  H3  grep is enough, and R2 buys nothing over R1

THE SESSION CONTRACT
One model call per case x arm x model. The working directory holds the document as
`doc.txt` and, for R2 and R3, a copy of the skill (pinned by $VETFLAT_SKILL_DIR when it
is set). The prompt carries the questions, the discipline for the arm in one paragraph,
and the required output: one JSON array, the `answers.json` shape, as the last thing in
the reply.

  [{"qid": ..., "status": "found|absent|unknown", "value"|"text"|"list": ...,
    "quote": ..., "line_start": n, "line_end": n, "how": "read|grep|find|scan"}]

The reply is the channel on purpose: R0, R1 and R3 have no Write tool and codex runs
`--sandbox read-only`, so nothing in this bench can write to its own workdir.

HOW THE DISCIPLINE IS HELD
  claude  ENFORCED by --allowedTools. R0 gets `Read` and nothing else; the arm's tool
          string is recorded on the row. No permission-bypass flag is ever passed.
  codex   NOT enforced. Codex takes no tool allow-list, so the discipline is written
          into AGENTS.md and the row records `discipline_enforced: false`. The `--json`
          event stream is audited afterwards: every shell command the model ran is
          counted by kind and any command the arm does not allow is listed in
          `discipline_violations`. Compare a codex row with a claude row knowing that.

THE ZERO-TOKEN MENU PROBE
For R2 rows the runner also runs `find.py` itself, once per question, and records whether
a gold span is inside the top five hits (`menu_recall@5`). It costs no tokens and it
separates "the tool never surfaced it" from "the model never read it". A run where
menu_recall is 1.0 and fact_recall is 0.4 is a model problem; the other way round is a
ranker problem.

USAGE
  bench/docs_bench.py --cases bench/private/docs --arm R2 --agent claude --model sonnet \
                      --case R1 --dry-run
  bench/docs_bench.py --cases bench/private/docs --matrix --dry-run
  bench/docs_bench.py --cases bench/private/docs --arm R1 --agent codex \
                      --model gpt-5.6-luna --run 3
  bench/docs_bench.py --menu-probe --cases bench/private/docs
  bench/docs_bench.py --regrade bench/results/docs-2026-09-06 --cases bench/private/docs
  bench/docs_bench.py --retry-failed bench/results/docs-2026-09-07 \
                      --cases bench/private/docs --dry-run

WHEN THE PROVIDER REFUSES
A row that never reached the model is not a row the model failed. Every launch goes
through bench/launch.py, which makes one physical attempt and, if it
still will not serve, hands back the captured tails. That row is written with
`outcome: provider_error` and a null `summary`: it shows as NOT RUN, it is left out of
every mean. Durable failures now stop in the ledger before grading; a fresh
`--retry-failed FOLDER` writes recovered rows to an owned copy under the new durable
directory and preserves the historical source. Ten of the twenty-six rows in the 2026-09-07 pilot died that way and
were averaged in as 0 facts.

The private test bed is described in evals/docs/README.md; it is never committed. The
public fixtures under tests/fixtures/docs_bench/ have the same shape and are what the
tests read.

Standard library only, Python 3.9. Exit codes: 0 ok, 1 a row failed, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import docs_grade  # noqa: E402
import journeys  # noqa: E402  - shell(), shell_preview(), claude_command(), claude_answer()
import legacy_control  # durable live-call boundary; offline modes remain local
import launch  # noqa: E402  the shared launcher: one attempt, captured tails, provider_error

RESULTS = os.path.join(HERE, "results")
DEFAULT_CASES = os.path.join(HERE, "private", "docs")
# The matrix configs sit in their own folder under bench/ab/configs/ because
# bench/run.py list_configs() claims every *.yaml directly in that directory as an
# A/B arm, and these are not A/B arms - a subfolder is invisible to that sweep.
MATRIX_YAML = os.path.join(HERE, "ab", "configs", "docs", "docs-matrix.yaml")
GLOSSARY = os.path.join(ROOT, "skills", "vet-flat", "references", "glossary.yaml")
DEFAULT_TIMEOUT_S = 900

# Where each agent looks for a skill, and therefore where the copy goes and what the
# allow-list pattern has to say. Same layout as bench/journeys.py.
SKILL_HOME = {"claude": os.path.join(".claude", "skills"),
              "codex": os.path.join(".agents", "skills")}


def skill_dir():
    """The skill folder to copy in. $VETFLAT_SKILL_DIR pins it for a run against a
    variant or an older checkout; without it, this repository's own."""
    return os.environ.get("VETFLAT_SKILL_DIR") or os.path.join(ROOT, "skills", "vet-flat")


# ------------------------------------------------------------------- the arms --
# `tools` is the --allowedTools string handed to Claude Code verbatim. It is the whole
# of the enforcement: there is no bypass flag anywhere in this file, and a test asserts
# that. `shell` is which command kinds the arm permits, used to audit codex afterwards.
ARMS = collections.OrderedDict([
    ("R0", collections.OrderedDict([
        ("label", "full read"),
        ("tools", "Read"),
        ("shell", ("read_full", "read_range", "inspect")),
        ("needs_skill", False),
        ("fixed_only", False),
        ("how", "read"),
        ("discipline",
         "Read the document with the Read tool. That is the only tool you have: there is "
         "no shell, no grep, no script. Ranges are allowed and encouraged - read the file "
         "in chunks rather than asking for all of it at once - but every sentence you "
         "quote must be one you actually read."),
        ("codex",
         "You have a read-only shell rather than a Read tool, so reading means "
         "`sed -n '1,120p' doc.txt` and the next chunk after it, or `cat doc.txt`. This "
         "arm is the full read, so reading it all is the point. Do not use grep, rg, or "
         "any script."),
    ])),
    ("R1", collections.OrderedDict([
        ("label", "grep only"),
        ("tools", "Read,Bash(grep:*),Bash(rg:*)"),
        ("shell", ("grep", "read_range", "inspect")),
        ("needs_skill", False),
        ("fixed_only", False),
        ("how", "grep"),
        ("discipline",
         "Search first, read second. Use `grep -n` (or `rg -n`) on doc.txt to find the "
         "lines that might carry an answer, then use Read with a line range around each "
         "hit to read the sentence in its context. Those two tools are all you have. Do "
         "not read the document end to end."),
        ("codex",
         "You have a read-only shell rather than a Read tool, so a ranged read means "
         "`sed -n '70,90p' doc.txt`. Use grep to find the lines and sed to read around "
         "them. Do not `cat` the whole document: reading it end to end is the thing this "
         "arm is measured against."),
    ])),
    ("R2", collections.OrderedDict([
        ("label", "find.py"),
        ("tools", "Read,Bash(python3 .claude/skills/vet-flat/scripts/find.py:*),"
                  "Bash(python3 .claude/skills/vet-flat/scripts/reviews.py:*),"
                  "Bash(grep:*),Bash(rg:*)"),
        ("shell", ("find", "reviews", "grep", "read_range", "inspect")),
        ("needs_skill", True),
        ("fixed_only", False),
        ("how", "find"),
        ("discipline",
         "Rank first, read second. Run `python3 {finder} doc.txt --ask \"<the question in "
         "your own words, English or Chinese>\"`; it prints the best-matching paragraphs "
         "whole, with their neighbours and line numbers. A hit is a sentence to READ, "
         "never an answer: the ranker counts words, it does not understand the document, "
         "and the top hit can be the wrong clause. Read the paragraph with Read before you "
         "quote it. `grep -n` stays available as a fallback if the ranker gives you "
         "nothing useful. Do not read the document end to end.\n"
         "If the document is a review page AND `reviews.py` exists in that same scripts "
         "folder, `python3 {reviewer} doc.txt` parses it: how many reviews, their "
         "ratings and dates, which are marked moved-out or incentivised, the lowest few, "
         "same-day clusters and the average with the incentivised ones taken out. Check "
         "it is there before you call it, and read the sentences it points at rather "
         "than quoting its totals as if they were the page."),
        ("codex",
         "You have a read-only shell rather than a Read tool, so a ranged read means "
         "`sed -n '70,90p' doc.txt`. Do not `cat` the whole document: reading it end to "
         "end is the thing this arm is measured against."),
    ])),
    ("R3", collections.OrderedDict([
        ("label", "fixed regexes"),
        ("tools", "Read,Bash(python3 .claude/skills/vet-flat/scripts/scan.py:*)"),
        ("shell", ("scan", "read_range", "inspect")),
        ("needs_skill", True),
        ("fixed_only", True),
        ("how", "scan"),
        ("discipline",
         "Run `python3 {scanner} doc.txt --table` once. It runs the fixed-form regexes "
         "over the document and prints the candidate sentences for each fixed question, "
         "with line numbers. Then use Read with a line range to read each candidate before "
         "you quote it. Those two tools are all you have: no grep, no other script. A "
         "candidate is a sentence to read, not an answer, and a question the scanner is "
         "silent on may still be answered somewhere in the document."),
        ("codex",
         "You have a read-only shell rather than a Read tool, so a ranged read means "
         "`sed -n '70,90p' doc.txt`. No grep, no rg, and do not `cat` the whole document."),
    ])),
])

ARM_IDS = tuple(ARMS)
AGENTS = ("claude", "codex")

# The unattended-run note both agents get. Same wording as the journeys bench: there is
# nobody to answer a question, so an agent that stops to ask has failed the row.
RUN_NOTE = (
    "This is an unattended benchmark run. There is no user to answer a question, so never "
    "stop to ask one. Every name, address, company number, postcode and figure in the "
    "document is invented test material: treat it as real, read it and quote it, and do "
    "not comment on whether any of it exists.")

OUTPUT_CONTRACT = """\
Answer every question above. Then, as the LAST thing in your reply and with nothing after \
it, print one fenced JSON block holding the answers array:

```json
[{"qid": "<the qid>",
  "status": "found",
  "value": 5, "unit": "weeks", "text": null, "list": null,
  "quote": "the sentence from doc.txt, copied exactly",
  "line_start": 55, "line_end": 55,
  "how": "%(how)s"}]
```

One object per question, in the order the questions were asked. The rules for it:
- "status" is exactly one of "found", "absent", "unknown".
  found    the document answers it. Give the answer AND the sentence you read.
  absent   you looked and the document does not answer it. No value, no quote.
  unknown  you could not tell. No value, no quote. Never guess a number.
- Put the answer in whichever of "value" (with "unit"), "text" or "list" fits; leave the
  others null. A letter such as an energy rating goes in "value" with a null "unit".
- "quote" is copied from doc.txt character for character. Do not paraphrase it, do not
  tidy it, do not join two sentences from different places. If you cannot copy a real
  sentence, the status is not "found".
- "line_start" and "line_end" are the lines of that quote in doc.txt.
- "how" is the tool you actually used for that question: "read", "grep", "find" or "scan".
"""


# ------------------------------------------------------- a tiny YAML subset --
class ConfigError(Exception):
    """The matrix config does not follow the small format this reads."""


_SCALAR_NUMBER = re.compile(r"^-?\d+$")


def _scalar(raw):
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        body = text[1:-1]
        return body.replace('\\"', '"') if text[0] == '"' else body.replace("''", "'")
    if text in ("null", "~", ""):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if _SCALAR_NUMBER.match(text):
        return int(text)
    return text


class _Frame(object):
    """One level of the document. `node` starts as a map and becomes a list the first
    time a `- ` item arrives under it, which is how a `key:` on its own line can be
    either without the parser having to look ahead."""

    __slots__ = ("indent", "node", "parent", "key")

    def __init__(self, indent, node, parent=None, key=None):
        self.indent, self.node, self.parent, self.key = indent, node, parent, key

    def as_list(self, lineno):
        if isinstance(self.node, list):
            return self.node
        if self.node:
            raise ConfigError("line %d: this key already has map entries, so it cannot "
                              "also be a list" % lineno)
        self.node = []
        if self.parent is not None:
            self.parent[self.key] = self.node
        return self.node


def parse_yaml(text):
    """Maps, lists of scalars, lists of maps, `|` block scalars, `#` comments.

    The same shape as the parser in scripts/scan.py, plus lists of maps, which the model
    list needs. Two-space indent. A file this cannot read is a file that has outgrown the
    format, and that is a signal, not a bug.
    """
    root = collections.OrderedDict()
    stack = [_Frame(-1, root)]
    block = None                            # (indent, container, key, lines)
    for lineno, raw in enumerate(text.splitlines(), 1):
        if block is not None:
            indent = len(raw) - len(raw.lstrip(" "))
            if not raw.strip() or indent > block[0]:
                block[3].append(raw[block[0] + 2:] if len(raw) > block[0] + 2 else "")
                continue
            block[1][block[2]] = "\n".join(block[3]).strip() + "\n"
            block = None
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ConfigError("line %d: indent must be a multiple of 2" % lineno)
        line = raw.strip()
        while len(stack) > 1 and stack[-1].indent >= indent:
            stack.pop()
        top = stack[-1]

        if line.startswith("- "):
            items = top.as_list(lineno)
            body = line[2:].strip()
            if ":" in body and not body[0] in "\"'":
                item = collections.OrderedDict()
                items.append(item)
                key, _sep, rest = body.partition(":")
                frame = _Frame(indent + 1, item)
                if rest.strip() == "":
                    child = collections.OrderedDict()
                    item[key.strip()] = child
                    stack.append(frame)
                    stack.append(_Frame(indent + 2, child, item, key.strip()))
                else:
                    item[key.strip()] = _scalar(rest)
                    stack.append(frame)
            else:
                items.append(_scalar(body))
            continue

        if isinstance(top.node, list):
            raise ConfigError("line %d: a bare key inside a list" % lineno)
        if ":" not in line:
            raise ConfigError("line %d: expected 'key:' or 'key: value'" % lineno)
        key, _sep, rest = line.partition(":")
        key, rest = key.strip(), rest.strip()
        if rest == "|":
            block = (indent, top.node, key, [])
            continue
        if rest == "":
            child = collections.OrderedDict()
            top.node[key] = child
            stack.append(_Frame(indent, child, top.node, key))
            continue
        top.node[key] = _scalar(rest)
    if block is not None:
        block[1][block[2]] = "\n".join(block[3]).strip() + "\n"
    return root


def load_yaml(path):
    with io.open(path, encoding="utf-8") as fh:
        return parse_yaml(fh.read())


# ------------------------------------------------------------ the test bed --
def case_ids(bed):
    folder = os.path.join(bed, "cases")
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder)
                  if os.path.isdir(os.path.join(folder, name))
                  and os.path.exists(os.path.join(folder, name, "gold.json")))


def load_case(bed, case_id, strict=True):
    """(gold, document text). Raises GoldError when the gold does not follow the contract
    or its spans do not point where it says, before a single token is spent.

    `strict=False` skips only the span check, for `--check`, which wants to report every
    problem in the bed rather than stop at the first case that has one.
    """
    folder = os.path.join(bed, "cases", case_id)
    with io.open(os.path.join(folder, "gold.json"), encoding="utf-8") as fh:
        gold = json.load(fh, object_pairs_hook=collections.OrderedDict)
    docs_grade.check_gold(gold)
    doc_path = os.path.join(bed, gold.get("file") or os.path.join("cases", case_id, "doc.txt"))
    if not os.path.exists(doc_path):
        doc_path = os.path.join(folder, "doc.txt")
    with io.open(doc_path, encoding="utf-8") as fh:
        doc = fh.read()
    if strict:
        problems = docs_grade.verify_spans(gold, doc)
        if problems:
            raise docs_grade.GoldError(
                "case %s: %d span problem(s), so every span score on it would be wrong. "
                "Run `bench/docs_bench.py --cases %s --check` for the list. First: %s"
                % (case_id, len(problems), bed, problems[0]))
    return gold, doc


def questions_for(gold, arm):
    """R3 only asks the fixed-form questions, because fixed regexes are the whole of what
    that arm has. Every other arm asks all of them."""
    questions = list(gold["questions"])
    if ARMS[arm]["fixed_only"]:
        questions = [q for q in questions if q.get("kind") == "fixed" and q.get("fixed_id")]
    return questions


# --------------------------------------------------------- the glossary side --
_GLOSSARY_LINE = re.compile(r'^\s{2}fixed\.(F\d+):\s*$')
_GLOSSARY_EN = re.compile(r'^\s{4}en:\s*"(.*)"\s*$')


def glossary_wording(path=None):
    """{"F1": "How many weeks' rent is the deposit?"} from references/glossary.yaml.

    A targeted read, not a YAML parse: the file is 70 KB of three languages and this
    needs eighteen English lines out of it. Missing or unreadable, the caller falls back
    to the wording in the gold file and says so on the row.
    """
    out = collections.OrderedDict()
    try:
        with io.open(path or GLOSSARY, encoding="utf-8") as fh:
            current = None
            for line in fh:
                head = _GLOSSARY_LINE.match(line.rstrip("\n"))
                if head:
                    current = head.group(1)
                    continue
                if current:
                    body = _GLOSSARY_EN.match(line.rstrip("\n"))
                    if body:
                        out[current] = body.group(1)
                    current = None
    except (IOError, OSError):
        return out
    return out


# --------------------------------------------------------------- the prompt --
def question_block(questions, glossary, lang="en"):
    lines = []
    for question in questions:
        wording = question.get("question")
        if lang == "zh" and question.get("question_zh"):
            wording = question["question_zh"]
        tag = ""
        if question.get("fixed_id"):
            tag = " [fixed form %s]" % question["fixed_id"]
            if lang == "en" and glossary.get(question["fixed_id"]):
                wording = glossary[question["fixed_id"]]
        lines.append("%s%s  %s" % (question["qid"], tag, wording))
    return "\n".join(lines)


# What each `type` in a gold file is called in the prompt. "a reviews" is not English,
# and the phrase is the only thing the model is told about the shape of the document.
TYPE_PHRASE = {
    "reviews": "a saved page of resident reviews",
    "terms": "an operator's terms and conditions",
    "planning": "a planning officer's report",
    "listing": "a property listing",
    "agreement": "a tenancy agreement",
    "shortlet": "a short-let operator's page",
}


def discipline_text(arm, agent):
    """The arm's one paragraph, with the script paths this agent will actually see.

    Codex has no Read tool, so it gets a second sentence naming the shell equivalent.
    Without it the R0 paragraph would tell a shell agent it has no shell, and every
    codex row would be graded on a discipline nobody could follow.
    """
    home = SKILL_HOME.get(agent, SKILL_HOME["claude"])
    scripts = os.path.join(home, "vet-flat", "scripts")
    text = ARMS[arm]["discipline"].format(
        finder=os.path.join(scripts, "find.py"), scanner=os.path.join(scripts, "scan.py"),
        reviewer=os.path.join(scripts, "reviews.py"))
    if agent == "codex" and ARMS[arm].get("codex"):
        text += "\n" + ARMS[arm]["codex"]
    return text


def build_prompt(gold, doc, arm, agent, questions, glossary, lang="en"):
    discipline = discipline_text(arm, agent)
    return (
        "You are answering questions about one document, and nothing else.\n\n"
        "The document is `doc.txt` in this folder: %(lines)d lines, %(chars)d characters, "
        "%(type)s.\n\n"
        "HOW YOU MAY READ IT\n%(discipline)s\n\n"
        "QUESTIONS\n%(questions)s\n\n"
        "%(contract)s" % {
            "lines": len(doc.splitlines()), "chars": len(doc),
            "type": TYPE_PHRASE.get(gold.get("type"), "a document"),
            "discipline": discipline,
            "questions": question_block(questions, glossary, lang),
            "contract": OUTPUT_CONTRACT % {"how": ARMS[arm]["how"]},
        })


def build_system(arm, agent):
    """The appendix. For claude it rides on --append-system-prompt; for codex it is
    written into AGENTS.md, which is the only channel codex exec has."""
    lines = ["Reading discipline for this run (arm %s, %s):" % (arm, ARMS[arm]["label"]),
             discipline_text(arm, agent), "", RUN_NOTE]
    if agent == "codex":
        lines += ["",
                  "This discipline is not enforced by the harness - codex exec takes no "
                  "tool allow-list - so it is on you to keep it. The shell is read-only. "
                  "Every command you run is recorded and audited against the arm."]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- the workdir --
def prepare_workdir(gold, doc, arm, agent, workdir=None, system=None, copy_skill=True):
    """A clean folder holding doc.txt, the skill when the arm needs it, and AGENTS.md
    for codex. Returns (path, the plan as printable lines).

    `copy_skill=False` is for --dry-run: the plan still names the copy and where it would
    land, but a dry run of the whole matrix would otherwise copy two megabytes of skill
    forty times to print forty commands.
    """
    workdir = legacy_control.workdir(workdir)
    path = os.path.abspath(workdir) if workdir else tempfile.mkdtemp(
        prefix="vetflat-docs-%s-%s-" % (gold["id"], arm))
    if not os.path.isdir(path):
        os.makedirs(path)
    plan = []
    with io.open(os.path.join(path, "doc.txt"), "w", encoding="utf-8") as fh:
        fh.write(doc)
    plan.append("write doc.txt (%d lines, %d characters)" % (len(doc.splitlines()), len(doc)))
    if ARMS[arm]["needs_skill"] and agent in SKILL_HOME:
        source = skill_dir()
        if copy_skill:
            home = os.path.join(path, SKILL_HOME[agent])
            if not os.path.isdir(home):
                os.makedirs(home)
            dst = os.path.join(home, "vet-flat")
            if os.path.lexists(dst):
                (shutil.rmtree if os.path.isdir(dst) and not os.path.islink(dst)
                 else os.unlink)(dst)
            shutil.copytree(source, dst)
        plan.append("copy %s -> %s/vet-flat%s"
                    % (source, SKILL_HOME[agent], "" if copy_skill else "  (not in a dry run)"))
    if agent == "codex" and system is not None:
        with io.open(os.path.join(path, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(system)
        plan.append("write AGENTS.md (codex exec has no --append-system-prompt)")
    return path, plan


# -------------------------------------------------------------- the commands --
def codex_command(prompt, workdir, model, last_message=None):
    """`codex exec --sandbox read-only --json`. --json gives the event stream the audit
    reads; -o gives the final message without having to find it in the stream. No
    approval-bypass flag, ever: a read-only sandbox is the point of the row."""
    cmd = ["codex", "exec", "--cd", workdir, "--sandbox", "read-only",
           "--skip-git-repo-check", "--json"]
    if last_message:
        cmd += ["--output-last-message", last_message]
    if model:
        cmd += ["--model", model]
    return cmd + ["--", prompt]


def build_command(agent, prompt, workdir, model, system, arm, last_message=None):
    if agent == "claude":
        return journeys.claude_command(prompt, workdir, model, system,
                                       tools=ARMS[arm]["tools"])
    if agent == "codex":
        return codex_command(prompt, workdir, model, last_message)
    raise ConfigError("no agent %r; pick one of %s" % (agent, ", ".join(AGENTS)))


# ------------------------------------------------------ the codex audit side --
COMMAND_KINDS = collections.OrderedDict([
    # The skill's own scripts first, so `python3 .../find.py` is a find and not a python.
    ("find", re.compile(r"\bfind\.py\b")),
    ("scan", re.compile(r"\bscan\.py\b")),
    ("reviews", re.compile(r"\breviews\.py\b")),
    ("grep", re.compile(r"(?:^|[|;&(\s])(?:grep|egrep|fgrep|rg|ripgrep)\b")),
    # A ranged read: `sed -n '70,90p'`, `head -n 40`, `awk 'NR>=70 && NR<=90'`. This is
    # what a shell agent has instead of Read with a line range.
    ("read_range", re.compile(r"(?:^|[|;&(\s])(?:sed\s+-n|head\b|tail\b|awk\b[^|]*\bNR\b)")),
    # An end-to-end read. The distinction from read_range is approximate on purpose: it
    # is an audit line for a row a human will read, not a gate.
    ("read_full", re.compile(r"(?:^|[|;&(\s])(?:cat|less|more|nl|strings|od|sed)\b")),
    ("inspect", re.compile(r"(?:^|[|;&(\s])(?:ls|pwd|wc|file|stat|find|echo|which|env)\b")),
    ("python", re.compile(r"(?:^|[|;&(\s])(?:python3?|py)\b")),
])


def classify_command(text):
    """Which kind of reading a shell command is. First match wins; the order of
    COMMAND_KINDS is the priority, so a pipeline is named by its most specific part."""
    for kind, pattern in COMMAND_KINDS.items():
        if pattern.search(text or ""):
            return kind
    return "other"


def _walk_commands(node, out):
    """Every command-shaped value anywhere in one event. Codex has changed the shape of
    its event stream before; a recursive walk survives that where a fixed path does not."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("command", "cmd", "argv") and value:
                if isinstance(value, (list, tuple)):
                    out.append(" ".join(str(v) for v in value))
                elif isinstance(value, str):
                    out.append(value)
            else:
                _walk_commands(value, out)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk_commands(item, out)
    return out


def commands_from_events(stdout):
    """The shell commands a `codex exec --json` run actually ran, in order.

    Every line that is not JSON is skipped, so a banner or a stray warning does not
    break the audit; a run whose stream carries no command at all reports none, which is
    itself a finding worth seeing on the row.
    """
    seen = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        _walk_commands(event, seen)
    return seen


def audit_commands(arm, commands):
    """(counts by kind, the commands the arm does not allow).

    `read_range` and `inspect` are allowed in every arm: a read-only shell is all codex
    has in place of a Read tool, and `ls` is not a reading strategy. `read_full` is
    allowed only in R0, because reading the document end to end is exactly what R1, R2
    and R3 are measured against; it is the one violation that says the arm collapsed
    into R0 rather than that the model reached for an extra tool.
    """
    allowed = set(ARMS[arm]["shell"])
    counts = collections.OrderedDict()
    violations = []
    for command in commands:
        kind = classify_command(command)
        counts[kind] = counts.get(kind, 0) + 1
        if kind not in allowed:
            violations.append(collections.OrderedDict([("kind", kind),
                                                       ("command", command[:200])]))
    return counts, violations


# ------------------------------------------------------- the zero-token probe --
def finder_path():
    return os.path.join(skill_dir(), "scripts", "find.py")


def menu_probe(gold, doc, doc_path=None, top=5, questions=None, finder=None, lang="en"):
    """qid -> did find.py put a gold span in its top `top` hits?

    Costs no tokens: it is the ranker being asked the same questions the model is asked,
    in the same language, so a miss here is the ranker's and not the model's. A question
    whose gold answer is `absent` has no span to hit and is left out, so a perfect probe
    on a case full of absent probes does not read as 1.0.
    """
    finder = finder or finder_path()
    questions = questions if questions is not None else gold["questions"]
    out = collections.OrderedDict()
    if not os.path.exists(finder):
        return out
    holder = None
    try:
        if not doc_path:
            holder = tempfile.mkdtemp(prefix="vetflat-docs-menu-")
            doc_path = os.path.join(holder, "doc.txt")
            with io.open(doc_path, "w", encoding="utf-8") as fh:
                fh.write(doc)
        offsets = _line_starts(doc)
        for question in questions:
            spans = question.get("spans") or []
            if not spans:
                continue
            asked = question.get("question") or ""
            if lang == "zh" and question.get("question_zh"):
                asked = question["question_zh"]
            hits = _run_finder(finder, doc_path, asked, top)
            out[question["qid"]] = _spans_in_hits(spans, hits, offsets)
    finally:
        if holder:
            shutil.rmtree(holder, ignore_errors=True)
    return out


def _line_starts(doc):
    """Character offset of the start of every line, 1-based line numbers."""
    starts, at = [0], 0
    for line in doc.splitlines():
        at += len(line) + 1
        starts.append(at)
    return starts


def _line_of(offset, starts):
    low, high = 0, len(starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if starts[mid] <= offset:
            low = mid
        else:
            high = mid - 1
    return low + 1


def _run_finder(finder, doc_path, question, top):
    cmd = [sys.executable, finder, doc_path, "--ask", question, "--top", str(top), "--json"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL)
        out, _err = proc.communicate(timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    text = (out or b"").decode("utf-8", "replace").strip()
    if not text:
        return []
    try:
        hits = json.loads(text)
    except ValueError:
        return []
    return hits if isinstance(hits, list) else []


def _spans_in_hits(spans, hits, offsets):
    """A gold span is in the menu when it overlaps the lines of any returned hit. The
    hit's character offsets are used, not its `line` field, because a hit prints its
    neighbouring paragraphs too and the model sees all of them."""
    for hit in hits:
        start, end = hit.get("start"), hit.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        first, last = _line_of(start, offsets), _line_of(max(end - 1, start), offsets)
        for span in spans:
            if first <= span["line_end"] and last >= span["line_start"]:
                return True
    return False


# -------------------------------------------------------- reading the answer --
FENCE = re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", re.S)


def parse_answers(reply):
    """(answers, note). The array in the last fenced block; failing that, the last
    top-level JSON array anywhere in the reply. A model that writes prose after its JSON
    is still graded - being fussy here would score formatting, not reading."""
    if not reply:
        return [], "empty reply"
    blocks = FENCE.findall(reply)
    for block in reversed(blocks):
        try:
            parsed = json.loads(block)
        except ValueError:
            continue
        if isinstance(parsed, list):
            return parsed, None
    for start in range(len(reply) - 1, -1, -1):
        if reply[start] != "[":
            continue
        for end in range(len(reply), start, -1):
            if reply[end - 1] != "]":
                continue
            try:
                parsed = json.loads(reply[start:end])
            except ValueError:
                continue
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                return parsed, "no fenced block; took a bare JSON array from the reply"
            break
    return [], "no answers array in the reply"


# --------------------------------------------------------------- the run row --
def row_name(arm, agent, model, case_id, run):
    def safe(text):
        return re.sub(r"[^A-Za-z0-9._#-]+", "-", str(text or "default"))
    return "docs-%s-%s-%s-%s-%d" % (safe(arm), safe(agent), safe(model), safe(case_id), run)


def results_dir(root=None, day=None):
    return os.path.join(root or RESULTS, "docs-" + (day or journeys.today()))


def plan_rows(args, bed):
    """Every (arm, agent, model, tier, case, run) this invocation means to run."""
    cases = [args.case] if args.case else case_ids(bed)
    if args.case and args.case not in case_ids(bed):
        raise ConfigError("no case %r in %s" % (args.case, bed))
    if args.matrix:
        combos = matrix_combos(args.matrix_config or MATRIX_YAML)
    else:
        combos = [(args.arm, args.agent, args.model, args.tier)]
    rows = []
    for arm, agent, model, tier in combos:
        for case_id in cases:
            for run in range(1, (args.run or 1) + 1):
                rows.append(collections.OrderedDict([
                    ("arm", arm), ("agent", agent), ("model", model), ("tier", tier),
                    ("case", case_id), ("run", run)]))
    return rows


def matrix_combos(path):
    """(arm, agent, model, tier) for every arm x model in docs-matrix.yaml.

    `r3_fixed_only` is not a switch here: R3 always asks only the fixed questions
    (ARMS["R3"]["fixed_only"]). The config records it so a reader of the config knows,
    and `skip_arms` on a model row is how a model opts out of one.
    """
    config = load_yaml(path)
    arms = config.get("arms") or list(ARM_IDS)
    if isinstance(arms, dict):
        arms = list(arms)
    models = config.get("models") or []
    if isinstance(models, dict):
        models = list(models.values())
    combos = []
    for arm in arms:
        if arm not in ARMS:
            raise ConfigError("%s: no arm %r; pick from %s"
                              % (path, arm, ", ".join(ARM_IDS)))
        for entry in models:
            if not isinstance(entry, dict):
                raise ConfigError("%s: a models entry is not a map" % path)
            agent = entry.get("agent")
            if agent not in AGENTS:
                raise ConfigError("%s: agent %r must be one of %s"
                                  % (path, agent, ", ".join(AGENTS)))
            skip = entry.get("skip_arms") or []
            if isinstance(skip, str):
                skip = [skip]
            if arm in skip:
                continue
            combos.append((arm, agent, entry.get("model"), entry.get("tier")))
    return combos


def run_row(row, bed, args, glossary):
    """One model call, or one printed command under --dry-run. Returns the record."""
    arm, agent, model = row["arm"], row["agent"], row["model"]
    legacy_control.job(row_name(arm, agent, model, row["case"], row["run"]))
    gold, doc = load_case(bed, row["case"])
    questions = questions_for(gold, arm)
    if not questions:
        # R3 on a case with no fixed-form question. Expected, not a failure: five of the
        # private bed's cases are free-question-only, and a matrix run should not exit 1
        # because R3 had nothing to ask them.
        print("  %s: no question this arm can ask; skipped"
              % row_name(arm, agent, model, row["case"], row["run"]))
        return None, None
    system = build_system(arm, agent)
    prompt = build_prompt(gold, doc, arm, agent, questions, glossary, args.lang)
    workdir, plan = prepare_workdir(gold, doc, arm, agent, system=system,
                                    copy_skill=not args.dry_run)
    last_message = os.path.join(workdir, ".codex-last-message.txt") if agent == "codex" else None
    command = build_command(agent, prompt, workdir, model, system, arm, last_message)
    label = row_name(arm, agent, model, row["case"], row["run"])

    record = collections.OrderedDict([
        ("row", label), ("bench", "reading-ablation"),
        ("arm", arm), ("arm_label", ARMS[arm]["label"]),
        ("agent", agent), ("model", model), ("tier", row.get("tier")),
        ("case", gold["id"]), ("case_type", gold.get("type")),
        ("doc_chars", len(doc)), ("doc_lines", len(doc.splitlines())),
        ("questions_asked", [q["qid"] for q in questions]),
        ("run", row["run"]), ("run_at", journeys.now()),
        ("allowed_tools", ARMS[arm]["tools"] if agent == "claude" else None),
        ("sandbox", "read-only" if agent == "codex" else None),
        ("discipline_enforced", agent == "claude"),
        ("skill_dir", skill_dir() if ARMS[arm]["needs_skill"] else None),
        # The R2 arm names reviews.py in its allow-list whether or not the script has
        # landed yet: a tool pattern is only a string. This says which it was, so a row
        # run before it existed is not compared with one run after.
        ("reviews_py_present", os.path.exists(
            os.path.join(skill_dir(), "scripts", "reviews.py"))
         if ARMS[arm]["needs_skill"] else None),
        ("command", journeys.shell_preview(command)),
        ("workdir", workdir),
    ])

    if args.dry_run:
        print("  %s" % label)
        for step in plan:
            print("      %s" % step)
        print("      allowedTools: %s" % (ARMS[arm]["tools"] if agent == "claude"
                                          else "(none: codex takes no allow-list; "
                                               "discipline_enforced=false)"))
        print("      cd %s && %s" % (workdir, journeys.shell_preview(command)))
        if not legacy_control.active():
            shutil.rmtree(workdir, ignore_errors=True)
        record["dry_run"] = True
        return record, None

    # One launcher for every runner: stdin closed, both streams captured, a busy
    # provider retried with a growing pause, and the tails kept when it never let the
    # row through at all. Ten of the twenty-six rows in the 2026-09-07 pilot died here
    # and were written down as 0 facts; that mean was a fiction.
    res = legacy_control.run_cli(command, workdir, args.timeout, agent, label=label)
    stdout = res.text if agent == "codex" else ""
    reply, usage = res.text, res.usage
    if agent == "codex" and last_message and os.path.exists(last_message):
        with io.open(last_message, encoding="utf-8") as fh:
            reply = fh.read() or res.text
    note = res.tail_note("the agent " if (res.note or "").startswith("exited") else "")

    commands = commands_from_events(stdout) if agent == "codex" else []
    counts, violations = audit_commands(arm, commands)
    record["wall_time_s"] = res.seconds
    record["usage"] = usage
    record["total_tokens"] = (usage or {}).get("total_tokens")
    record["commands"] = counts
    record["commands_seen"] = [c[:200] for c in commands]
    record["discipline_violations"] = violations
    record["attempts"] = res.attempts
    record["attempt_records"] = res.attempt_records
    record["exit_code"] = res.exit_code
    record["reply_chars"] = len(reply or "")

    if res.provider_error:
        # No grade at all rather than a zero: `summary` is null, the row is out of every
        # mean, and the tails stay on the record so the failure can be read months later.
        # `--retry-failed` re-runs exactly these rows into this same folder.
        record["outcome"] = "provider_error"
        record["note"] = note
        record["stdout_tail"] = res.stdout_tail
        record["stderr_tail"] = res.stderr_tail
        record["valid"] = False
        record["invalid_reason"] = "provider error: %s" % (res.note or "the launch failed")
        record["summary"] = None
        record["questions_graded"] = []
        record["answers"] = []
        if not args.keep and not legacy_control.active():
            shutil.rmtree(workdir, ignore_errors=True)
        return record, None

    answers, parse_note = parse_answers(reply)
    menu = (menu_probe(gold, doc, questions=questions, lang=args.lang)
            if arm == "R2" else None)
    grade = docs_grade.grade_session(gold, answers, doc, menu)
    record["outcome"] = "completed"
    record["note"] = "; ".join(n for n in (note, parse_note) if n) or None
    record["valid"] = grade.get("valid", True)
    record["invalid_reason"] = grade.get("invalid_reason")
    record["summary"] = grade["summary"]
    record["questions_graded"] = grade["questions_graded"]
    record["answers"] = answers
    if not args.keep and not legacy_control.active():
        shutil.rmtree(workdir, ignore_errors=True)
    return record, None


# ------------------------------------------------------------- results i/o --
MD_HEADER = (
    "| run (UTC) | arm | agent | model | case | facts | spans | fabrications | invented "
    "quotes | absent honesty | menu@5 | enforced | commands | tokens | wall s |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")


def _num(value, fmt="%.2f"):
    return (fmt % value) if isinstance(value, (int, float)) else "-"


def is_valid(record):
    """Did this row produce something to grade? A launch that failed is not a zero.

    A row is invalid when the grader refused to score it (no answers array), or when the
    record says so outright - `valid: false`, or an `outcome` bench/launch.py classifies
    as a provider error rather than a model result.
    """
    if record.get("valid") is False:
        return False
    if record.get("outcome") in ("provider_error", "launch_error", "timeout"):
        return False
    return bool(record.get("summary"))


def md_row(record):
    summary = record.get("summary") or {}
    counts = record.get("commands") or {}
    if not is_valid(record):
        return ("| %s | %s | %s | %s | %s | NOT RUN | - | - | - | - | - | %s | - | %s | %s |\n"
                % (record.get("run_at"), record.get("arm"), record.get("agent"),
                   record.get("model") or "-", record.get("case"),
                   "yes" if record.get("discipline_enforced") else "AUDIT ONLY",
                   record.get("total_tokens")
                   if record.get("total_tokens") is not None else "-",
                   _num(record.get("wall_time_s"))))
    return ("| %s | %s | %s | %s | %s | %s | %s | %d | %d | %s | %s | %s | %s | %s | %s |\n"
            % (record.get("run_at"), record.get("arm"), record.get("agent"),
               record.get("model") or "-", record.get("case"),
               _num(summary.get("fact_recall")), _num(summary.get("span_recall")),
               summary.get("fabrications", 0), summary.get("invented_quotes", 0),
               _num(summary.get("absent_honesty")), _num(summary.get("menu_recall@5")),
               "yes" if record.get("discipline_enforced") else "AUDIT ONLY",
               ", ".join("%s %d" % (k, v) for k, v in counts.items()) or "-",
               record.get("total_tokens") if record.get("total_tokens") is not None else "-",
               _num(record.get("wall_time_s"))))


ARM_MEANS = ("fact_recall", "span_recall", "absent_honesty", "menu_recall@5")


def arm_table(rows):
    """Per-arm means over the VALID rows only, with n on every line.

    A row whose launch failed carries no summary and is counted only in `not run`. It is
    never averaged in as a zero: thirteen R2 rows of which ten never started would read
    as an arm that scored 0.11 when the three that ran scored 0.48.
    """
    by_arm = collections.OrderedDict()
    for record in rows:
        arm = record.get("arm")
        bucket = by_arm.setdefault(arm, {"valid": [], "invalid": 0})
        if is_valid(record):
            bucket["valid"].append(record)
        else:
            bucket["invalid"] += 1
    lines = ["| arm | n | not run | " + " | ".join(ARM_MEANS) +
             " | fabrications | invented quotes |",
             "|---|---|---|" + "---|" * (len(ARM_MEANS) + 2)]
    for arm in sorted(by_arm):
        bucket = by_arm[arm]
        valid = bucket["valid"]
        cells = []
        for key in ARM_MEANS:
            values = [r["summary"][key] for r in valid
                      if isinstance((r.get("summary") or {}).get(key), (int, float))]
            cells.append("%.3f" % (sum(values) / float(len(values))) if values else "-")
        fabrications = sum((r.get("summary") or {}).get("fabrications", 0) for r in valid)
        invented = sum((r.get("summary") or {}).get("invented_quotes", 0) for r in valid)
        lines.append("| %s %s | %d | %d | %s | %d | %d |"
                     % (arm, ARMS.get(arm, {}).get("label", ""), len(valid),
                        bucket["invalid"], " | ".join(cells), fabrications, invented))
    return "\n".join(lines) + "\n"


def summary_of(record, raw_path=None, answers_path=None):
    out = collections.OrderedDict(
        (k, v) for k, v in record.items()
        if k not in ("answers", "questions_graded", "commands_seen"))
    if raw_path:
        out["raw"] = os.path.relpath(raw_path, ROOT)
    if answers_path:
        out["answers_file"] = os.path.relpath(answers_path, ROOT)
    return out


def write_scorecard(folder, rows):
    day = os.path.basename(os.path.abspath(folder)).replace("docs-", "") or journeys.today()
    with io.open(os.path.join(folder, "scorecard.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    with io.open(os.path.join(folder, "scorecard.md"), "w", encoding="utf-8") as fh:
        fh.write("# Document-reading ablation, %s\n\n"
                 "One row per case x arm x model x run. `facts` is the share of questions "
                 "answered correctly; `spans` is the quote score over the questions the "
                 "document does answer (1 in the right place, 0.5 misplaced but real, 0 "
                 "invented); `absent honesty` is the share of absent probes the model "
                 "declined to answer; `menu@5` is the zero-token find.py probe, filled in "
                 "for R2 rows only. `enforced` says whether the reading discipline was held "
                 "by the tool allow-list (claude) or only written down and audited "
                 "afterwards (codex). A row marked NOT RUN produced no answers array - a "
                 "failed launch, not a model that scored zero - and is left out of every "
                 "mean below.\n\n## Per arm, valid rows only\n\n%s\n## Every row\n\n%s%s"
                 % (day, arm_table(rows), MD_HEADER,
                    "".join(md_row(r) for r in rows)))


def write_results(record, root=None, day=None):
    folder = results_dir(root, day)
    raw_dir, answers_dir = os.path.join(folder, "raw"), os.path.join(folder, "answers")
    for path in (raw_dir, answers_dir):
        if not os.path.isdir(path):
            os.makedirs(path)
    raw_path = os.path.join(raw_dir, record["row"] + ".json")
    index = 1
    while not legacy_control.active() and os.path.exists(raw_path):
        index += 1
        raw_path = os.path.join(raw_dir, "%s#%d.json" % (record["row"], index))
    with io.open(raw_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    answers_path = os.path.join(answers_dir,
                                os.path.basename(raw_path).replace(".json", ".answers.json"))
    with io.open(answers_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record.get("answers") or [], ensure_ascii=False, indent=1) + "\n")

    jpath = os.path.join(folder, "scorecard.json")
    rows = []
    if os.path.exists(jpath):
        try:
            with io.open(jpath, encoding="utf-8") as fh:
                rows = json.load(fh)
        except ValueError:
            rows = []
    if legacy_control.active():
        rows = [r for r in rows if r.get("row") != record.get("row")]
    rows.append(summary_of(record, raw_path, answers_path))
    write_scorecard(folder, rows)
    return raw_path, answers_path


def check_bed(bed, case=None):
    """Validate every gold file against its document and say what is wrong. No model.

    Meant for whoever is building the bed: a stale line number or a quote that is not in
    the document does not crash anything, it just quietly halves that case's span score
    in every arm at once, which reads as a hard case rather than a broken gold.
    """
    total = 0
    for case_id in ([case] if case else case_ids(bed)):
        try:
            gold, doc = load_case(bed, case_id, strict=False)
        except docs_grade.GoldError as exc:
            print("%-6s CONTRACT: %s" % (case_id, exc))
            total += 1
            continue
        except (IOError, OSError, ValueError) as exc:
            print("%-6s UNREADABLE: %s" % (case_id, exc))
            total += 1
            continue
        problems = docs_grade.verify_spans(gold, doc)
        fixed = len([q for q in gold["questions"] if q.get("kind") == "fixed"])
        absent = len([q for q in gold["questions"] if (q.get("answer") or {}).get("absent")])
        print("%-6s %-10s %7d chars %5d lines  %2d questions (%d fixed, %d absent)  %s"
              % (case_id, gold.get("type"), gold.get("chars") or len(doc),
                 gold.get("lines") or len(doc.splitlines()), len(gold["questions"]),
                 fixed, absent,
                 "ok" if not problems else "%d SPAN PROBLEM(S)" % len(problems)))
        for problem in problems:
            print("         %s" % problem)
        total += len(problems)
    if total:
        print("\n%d problem(s). A case with a span problem is skipped by a run rather "
              "than graded wrongly." % total)
    return 1 if total else 0


def regrade(folder, bed):
    """Re-score every raw record under `folder` with today's rules.

    The replies stay what they were - only the grader runs again - so a frozen rule that
    turns out to be wrong reaches runs that were already paid for. The menu probe is
    re-run too, because it costs nothing and the ranker may have changed.
    """
    raw_dir = os.path.join(folder, "raw")
    if not os.path.isdir(raw_dir):
        print("usage error: no raw/ folder under %s" % folder, file=sys.stderr)
        return 2
    rows, regraded = [], 0
    for name in sorted(os.listdir(raw_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(raw_dir, name)
        with io.open(path, encoding="utf-8") as fh:
            record = json.load(fh, object_pairs_hook=collections.OrderedDict)
        try:
            gold, doc = load_case(bed, record["case"])
        except (IOError, OSError, KeyError, docs_grade.GoldError):
            rows.append(summary_of(record, path))
            continue
        asked = set(record.get("questions_asked") or [])
        questions = [q for q in gold["questions"] if not asked or q["qid"] in asked]
        menu = (menu_probe(gold, doc, questions=questions)
                if record.get("arm") == "R2" else None)
        subset = collections.OrderedDict(gold)
        subset["questions"] = questions
        grade = docs_grade.grade_session(subset, record.get("answers") or [], doc, menu)
        # The same rule reaches rows that were already paid for: a stored row with no
        # answers array loses its zeros and becomes a row that did not run.
        record["valid"] = grade.get("valid", True)
        record["invalid_reason"] = grade.get("invalid_reason")
        record["summary"] = grade["summary"]
        record["questions_graded"] = grade["questions_graded"]
        record["regraded_at"] = journeys.now()
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
        rows.append(summary_of(record, path))
        regraded += 1
    write_scorecard(folder, rows)
    print("regraded %d row(s) in %s" % (regraded, folder))
    return 0


# ----------------------------------------------------------- retry the failed --
# The two shapes a lost row takes on disk. Today's runner writes outcome
# provider_error; the 2026-09-07 pilot, which had no such outcome, left only its note:
# "the agent exited 1: ; no answers array in the reply".
FAILED_NOTE = re.compile(r"exited|no answers array|provider error", re.I)


def is_provider_error(record):
    """True for a row the provider never let through, whichever runner wrote it."""
    if (record or {}).get("outcome") == "provider_error":
        return True
    if (record or {}).get("valid") is False and "provider" in (
            (record or {}).get("invalid_reason") or ""):
        return True
    return bool(FAILED_NOTE.search((record or {}).get("note") or ""))


def failed_rows(folder):
    """[(raw path, record)] for every row in FOLDER that has to be run again."""
    raw_dir = os.path.join(folder, "raw")
    if not os.path.isdir(raw_dir):
        return None
    out = []
    for name in sorted(os.listdir(raw_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(raw_dir, name)
        try:
            with io.open(path, encoding="utf-8") as fh:
                record = json.load(fh, object_pairs_hook=collections.OrderedDict)
        except ValueError:
            continue
        if is_provider_error(record):
            out.append((path, record))
    return out


def replace_scorecard_row(folder, raw_path, record, answers_path=None):
    """Put this row back where the failed one was, rather than appending a second row.

    A retry is not a rerun: the failed row was never a result, so it is replaced and
    not kept beside its replacement."""
    jpath = os.path.join(folder, "scorecard.json")
    rows = []
    if os.path.exists(jpath):
        try:
            with io.open(jpath, encoding="utf-8") as fh:
                rows = json.load(fh)
        except ValueError:
            rows = []
    fresh = summary_of(record, raw_path, answers_path)
    rel = os.path.relpath(raw_path, ROOT)
    for index, row in enumerate(rows):
        if row.get("raw") == rel or row.get("row") == record.get("row"):
            rows[index] = fresh
            break
    else:
        rows.append(fresh)
    write_scorecard(folder, rows)
    return rows


def retry_failed(folder, bed, args):
    """Re-run refused rows in the working copy supplied by the durable entrypoint.

    The raw file and the scorecard row are replaced where they stand, so the folder ends
    up with one row per (arm, agent, model, case, run) and no zeros that were never
    earned. Nothing else in the folder is touched.
    """
    rows = failed_rows(folder)
    if rows is None:
        print("usage error: no raw/ folder under %s" % folder, file=sys.stderr)
        return 2
    if not rows:
        print("nothing to re-run in %s: no row carries a provider error" % folder)
        return 0
    print("%s %d row(s) the provider refused, out of %s"
          % ("would re-run" if args.dry_run else "re-running", len(rows), folder))
    for path, record in rows:
        print("  %-46s %s" % (record.get("row"), (record.get("note") or "")[:110]))
    if args.dry_run:
        return 0

    glossary = glossary_wording()
    again, failures = 0, 0
    for path, record in rows:
        plan = collections.OrderedDict([
            ("arm", record.get("arm")), ("agent", record.get("agent")),
            ("model", record.get("model")), ("tier", record.get("tier")),
            ("case", record.get("case")), ("run", record.get("run") or 1)])
        fresh, problem = _safe_row(plan, bed, args, glossary)
        if problem or fresh is None:
            print("  %s: %s" % (record.get("row"), problem or "nothing to ask this arm"),
                  file=sys.stderr)
            failures += 1
            if legacy_control.active():
                raise ValueError(problem or "no recovery result")
            continue
        fresh["retried_at"] = journeys.now()
        fresh["replaces"] = collections.OrderedDict([
            ("run_at", record.get("run_at")), ("note", record.get("note")),
            ("outcome", record.get("outcome"))])
        answers_path = os.path.join(folder, "answers",
                                    os.path.basename(path).replace(".json",
                                                                   ".answers.json"))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(fresh, ensure_ascii=False, indent=1) + "\n")
        if os.path.isdir(os.path.dirname(answers_path)):
            with io.open(answers_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(fresh.get("answers") or [], ensure_ascii=False,
                                    indent=1) + "\n")
        replace_scorecard_row(folder, path, fresh, answers_path)
        summary = fresh.get("summary") or {}
        print("  %-46s %s -> facts %s%s"
              % (fresh["row"], record.get("outcome") or "note",
                 _num(summary.get("fact_recall")),
                 "  (the provider refused it again)"
                 if fresh.get("outcome") == "provider_error" else ""))
        again += 1
    print("re-ran %d row(s) in %s" % (again, folder))
    return 1 if failures else 0


# ------------------------------------------------------------------------ cli --
def build_parser():
    ap = argparse.ArgumentParser(
        description="The document-reading ablation: R0 full read, R1 grep, R2 find.py, "
                    "R3 fixed regexes.")
    ap.add_argument("--cases", default=DEFAULT_CASES,
                    help="the test bed folder (default: bench/private/docs)")
    ap.add_argument("--arm", choices=ARM_IDS, help="which reading discipline")
    ap.add_argument("--agent", choices=AGENTS, default="claude")
    ap.add_argument("--model", help="the model id for that agent")
    ap.add_argument("--tier", choices=("cheap", "middle", "strong"),
                    help="what tier this model is, for the scorecard")
    ap.add_argument("--case", help="one case id instead of the whole bed")
    ap.add_argument("--run", type=int, default=1, help="how many runs per row (default 1)")
    ap.add_argument("--matrix", action="store_true",
                    help="expand arms x models from bench/ab/configs/docs/docs-matrix.yaml")
    ap.add_argument("--matrix-config", help="a different matrix yaml")
    ap.add_argument("--lang", choices=("en", "zh"), default="en",
                    help="ask the questions in English (default) or Chinese")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the command and the workdir plan; call no model")
    ap.add_argument("--results", help="where results go (default: bench/results)")
    ap.add_argument("--day", help="the results day folder (default: today, UTC)")
    ap.add_argument("--parallel", type=int, default=1, help="rows at a time (default 1)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                    help="seconds per reply (default %d)" % DEFAULT_TIMEOUT_S)
    ap.add_argument("--keep", action="store_true", help="keep the working directories")
    ap.add_argument("--check", action="store_true",
                    help="validate every gold file in the bed against the document and "
                         "stop; call no model")
    ap.add_argument("--menu-probe", action="store_true",
                    help="run the zero-token find.py probe over the bed and stop")
    ap.add_argument("--regrade", metavar="FOLDER",
                    help="re-score a results folder with today's rules and stop")
    ap.add_argument("--retry-failed", metavar="FOLDER",
                    help="re-run every row of FOLDER the provider refused (outcome "
                         "provider_error, or a note that says the agent exited or gave "
                         "no answers array) and replace it where it stands. With "
                         "--dry-run it only says which rows it would re-run")
    legacy_control.add_arguments(ap)
    return ap


@legacy_control.entrypoint
def main(argv=None):
    args = build_parser().parse_args(argv)
    bed = os.path.abspath(args.cases)
    if not os.path.isdir(os.path.join(bed, "cases")):
        print("usage error: no cases/ folder under %s. The private bed is described in "
              "evals/docs/README.md; the public fixtures are tests/fixtures/docs_bench."
              % bed, file=sys.stderr)
        return 2

    if args.check:
        return check_bed(bed, args.case)

    if args.regrade:
        return regrade(os.path.abspath(args.regrade), bed)

    if args.retry_failed:
        return retry_failed(os.path.abspath(args.retry_failed), bed, args)

    if args.menu_probe:
        total, hit = 0, 0
        for case_id in ([args.case] if args.case else case_ids(bed)):
            try:
                gold, doc = load_case(bed, case_id)
            except docs_grade.GoldError as exc:
                print("%-12s skipped: %s" % (case_id, exc), file=sys.stderr)
                continue
            menu = menu_probe(gold, doc, lang=args.lang)
            for qid, ok in menu.items():
                total += 1
                hit += 1 if ok else 0
                print("%-12s %-10s %s" % (case_id, qid, "hit" if ok else "MISS"))
        if total:
            print("menu_recall@5: %.4f over %d question(s) with a gold span" % (hit / float(total),
                                                                                total))
        return 0

    if not args.matrix and not args.arm:
        print("usage error: give --arm R0|R1|R2|R3, or --matrix", file=sys.stderr)
        return 2

    try:
        rows = plan_rows(args, bed)
    except ConfigError as exc:
        print("usage error: %s" % exc, file=sys.stderr)
        return 2
    if not rows:
        print("usage error: nothing to run", file=sys.stderr)
        return 2

    for row in rows:
        legacy_control.require_model(row.get("model"), row.get("agent"))
    glossary = glossary_wording()
    print("%s %d row(s) from %s%s"
          % ("planning" if args.dry_run else "running", len(rows), bed,
             "" if glossary else "  (no glossary wording found; using the gold's own)"))

    records, failures = [], 0

    def land(record, problem):
        """Write and print one finished row. Returns 1 for a row that failed to run.

        Each row is written the moment it finishes, in both the sequential and the
        parallel path: a 260-row matrix that only wrote at the end lost every row to a
        crash and showed no progress for hours (2026-09-07). The scorecard therefore
        holds rows in completion order; the tables group them by arm anyway.
        """
        if problem:
            if legacy_control.active():
                raise ValueError(problem)
            print("  skipped: %s" % problem, file=sys.stderr)
            return 1
        if record is None:
            return 0
        records.append(record)
        if args.dry_run:
            return 0
        raw_path, _answers = write_results(record, args.results, args.day)
        summary = record.get("summary") or {}
        print("  %-46s facts %s  spans %s  fab %d  -> %s"
              % (record["row"], _num(summary.get("fact_recall")),
                 _num(summary.get("span_recall")), summary.get("fabrications", 0),
                 os.path.relpath(raw_path, ROOT)))
        if record.get("discipline_violations"):
            print("      discipline violations: %s"
                  % ", ".join(v["kind"] for v in record["discipline_violations"]))
        sys.stdout.flush()
        return 0

    if args.parallel > 1 and not args.dry_run and not legacy_control.active():
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        lock = threading.Lock()
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = [pool.submit(_safe_row, r, bed, args, glossary) for r in rows]
            for future in as_completed(futures):
                record, problem = future.result()
                with lock:
                    failures += land(record, problem)
    else:
        for r in rows:
            failures += land(*_safe_row(r, bed, args, glossary))
    if not args.dry_run and records:
        print("scorecard: %s" % os.path.relpath(
            os.path.join(results_dir(args.results, args.day), "scorecard.md"), ROOT))
    return 1 if failures else 0


def _safe_row(row, bed, args, glossary):
    try:
        return run_row(row, bed, args, glossary)
    except (docs_grade.GoldError, ConfigError) as exc:
        return None, str(exc)
    except (IOError, OSError) as exc:
        return None, "case %s: %s" % (row.get("case"), exc)


if __name__ == "__main__":
    sys.exit(main())
