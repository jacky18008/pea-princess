#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run one case as a ROLE PIPELINE - planner, executors, verifier, integrator - and grade it.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY THIS EXISTS
===============
``bench/run.py`` gives one agent the skill and the case and reads the report it writes.
This file gives four SEPARATE model calls one role each, with one file passing between
them, and grades the result exactly the same way. That is the only honest way to ask
whether splitting the roles is worth anything: same cases, same grader, same scorecard,
one factor changed.

Each role is one model call. It gets the role's own instructions out of
``skills/vet-flat/references/pipeline.md``, the previous role's file, and NOTHING ELSE.
The tool list per role is the discipline, and it is enforced by the flag, not by asking
nicely:

  planner     Read                                   decides what to fetch, reads no page
  executors   Read, Bash(python3:*)                  run the scripts, write evidence only
  verifier    Read, Bash(verify.py), Bash(calc.py)   checks; may not fetch anything new
  integrator  Read, Write                            writes report.json from verified items

Only the integrator may write a file. Every other role prints one JSON object and this
harness writes it, so a role cannot quietly leave itself notes between steps.

THE DETERMINISTIC HALF
======================
Before the planner runs, ``scripts/plan.py`` writes the scaffold the planner starts
from; after it answers, ``plan.py --check`` says whether it dropped anything required,
and a plan that shrank is replaced by the scaffold (recorded in the row, never hidden).
Before the verifier runs, ``scripts/verify.py`` does every check that has one answer and
hands the model only its flagged items. With ``--gold`` it also runs the
information-sufficiency probe, which asks - deterministically, at no token cost -
whether the gold was even derivable from the evidence the executors collected. That is
the number that tells a fetching failure from a writing failure.

CONFIGS
=======
The config is a ``bench/ab/configs/*.yaml`` file with one new block on top of the
schema ``bench/run.py`` already reads::

    pipeline:
      planner:
        agent: claude
        model: sonnet
      executors:
        agent: claude
        model: sonnet
        parallel: 3
      verifier:
        agent: claude
        model: opus
      integrator:
        agent: claude
      replan_rounds: 1

A role that is absent, or empty, is SKIPPED. ``P1`` has no verifier; ``P3`` has no
planner and no executors, and runs the single-agent baseline first instead, deriving
evidence from its report so that the verifier has something to check. An unknown role
name is a usage error, not a silently ignored key.

``--budget-mode lite|standard|deep`` overrides the config's own mode for one sweep and
renames the arm to ``<config>-<mode>`` in the scorecard, which is how the ``-lite`` and
``-deep`` variants of every arm are produced without six more config files.

Nothing here passes a permission-bypass flag. The Claude side is scoped by
``--allowedTools``, the Codex side by ``-s workspace-write``, and stdin is closed on
every launch (an open stdin becomes part of the prompt).

Every role - planner, each executor, the verifier and any replan round of it, the
integrator - launches through ``bench/launch.py``, the one launcher every runner in this
directory shares. That is where the single physical attempt, the closed stdin and the
token parsing for both CLIs live now; a role that never reached the model comes back with
``provider_error=True`` and is recorded as such on its own row and in the run's notes,
not as an empty answer graded like a model's.

Usage:
  bench/pipeline.py --config P2-claude --cases bench/private/cases_private.json \\
      --case v2-buck --run 1 --dry-run
  bench/pipeline.py --config P2-claude --cases bench/private/cases_private.json \\
      --case v2-buck --run 1 --gold bench/private/gold.json
  bench/pipeline.py --config P1-codex --cases evals/evals.json --case e14-marsh-wall-301 \\
      --budget-mode lite --dry-run

Exit codes: 0 the pipeline ran and was graded, 1 it did not produce a gradeable report,
2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SKILL_DIR = os.path.join(ROOT, "skills", "vet-flat")
SCRIPTS = os.path.join(SKILL_DIR, "scripts")

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ab"))
sys.path.insert(0, SCRIPTS)
import run as runner  # noqa: E402
import legacy_control  # durable live-call boundary; offline modes remain local
import grade as grader  # noqa: E402
import run_codex  # noqa: E402
import plan as planner_tool  # noqa: E402
import verify as verifier_tool  # noqa: E402
import launch  # noqa: E402  the one launcher every role goes through now

ROLES = ("planner", "executors", "verifier", "integrator")
ROLE_KEYS = ("agent", "model", "parallel", "skip", "note")
PIPELINE_KEYS = ROLES + ("replan_rounds", "baseline")

# The discipline, as flags. Claude Code takes --allowedTools; Codex takes none, and its
# sandbox does the scoping, so for Codex the same list is written into AGENTS.md instead.
ROLE_TOOLS = collections.OrderedDict([
    ("planner", ["Read"]),
    ("executors", ["Read", "Bash(python3:*)"]),
    ("verifier", ["Read",
                  "Bash(python3 {skill}/scripts/verify.py:*)",
                  "Bash(python3 {skill}/scripts/calc.py:*)"]),
    ("integrator", ["Read", "Write"]),
    ("baseline", ["Bash(python3:*)", "Read", "Write", "Agent"]),
])


def role_tools(role, agent="claude"):
    """The tool list for a role, with the skill path this agent installs into.

    The label may carry a group ("executors[money]") or a round ("verifier-again"),
    because that is what the scorecard rows are named; strip both before looking up.
    """
    key = role.split("[")[0]
    if key.endswith("-again"):
        key = key[:-len("-again")]
    skill = skill_rel(agent).replace(os.sep, "/")
    return [tool.format(skill=skill) for tool in ROLE_TOOLS[key]]

KEPT = []            # every intermediate file this process persisted, for the row

SKILL_HOME = {"claude": os.path.join(".claude", "skills"),
              "codex": os.path.join(".agents", "skills")}


def skill_rel(agent):
    """Where this agent looks for an installed skill, relative to the working directory."""
    return os.path.join(SKILL_HOME.get(agent, SKILL_HOME["claude"]), "vet-flat")


def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# ------------------------------------------------------------- config loading --
def split_pipeline_block(lines):
    """(lines without the pipeline block, the block's own lines)."""
    kept, block, inside = [], [], False
    for line in lines:
        if not inside and re.match(r"^pipeline\s*:\s*$", line):
            inside = True
            continue
        if inside:
            if line.strip() == "" or line[:1] in (" ", "\t"):
                block.append(line)
                continue
            inside = False
        kept.append(line)
    return kept, block


def parse_pipeline_block(block):
    """{role: {key: value}} from the indented block. Two-space indent, scalars only."""
    out = collections.OrderedDict()
    current = None
    for lineno, raw in enumerate(block, 1):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            raise ValueError("pipeline block, line %d: expected 'key:' or 'key: value'"
                             % lineno)
        key, _sep, rest = line.partition(":")
        key, rest = key.strip(), rest.strip()
        if indent <= 2:
            if rest == "":
                current = collections.OrderedDict()
                out[key] = current
            else:
                out[key] = runner.scalar(rest)
                current = None
        else:
            if current is None:
                raise ValueError("pipeline block, line %d: %r is indented under nothing"
                                 % (lineno, key))
            current[key] = runner.scalar(rest)
    return out


def parse_and_check(text, name, path=None):
    """The config text -> config dict, with every pipeline role name and key checked.

    A role this file does not know about is a usage error, not a key that gets ignored:
    a config that names an `aggregator` is asking for something the harness will silently
    not do, and a silent no-op in an ablation is worse than a crash.
    """
    kept, block = split_pipeline_block(text.splitlines())
    config = runner.load_config(path or name, lines=kept)
    pipeline = parse_pipeline_block(block)
    for role, value in pipeline.items():
        if role not in PIPELINE_KEYS:
            raise ValueError("config %s: %r is not a pipeline role. The roles are %s, "
                             "plus replan_rounds and baseline." % (name, role, ", ".join(ROLES)))
        if isinstance(value, dict):
            for key in value:
                if key not in ROLE_KEYS:
                    raise ValueError("config %s: role %s has no key %r (it takes %s)"
                                     % (name, role, key, ", ".join(ROLE_KEYS)))
    config["pipeline"] = pipeline
    return config


def load_config(path):
    """The A/B config plus its `pipeline:` block, with the role names checked."""
    path = runner.config_path(path)
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    return parse_and_check(text, os.path.basename(path), path)


def role_config(config, role):
    """{agent, model, parallel} for a role, or None when the arm skips it."""
    block = (config.get("pipeline") or {}).get(role)
    if not isinstance(block, dict) or not block or block.get("skip") is True:
        return None
    return collections.OrderedDict([
        ("agent", block.get("agent") or config.get("agent") or "claude"),
        ("model", block.get("model")),
        ("parallel", int(block.get("parallel") or 1)),
        ("note", block.get("note"))])


def replan_rounds(config):
    value = (config.get("pipeline") or {}).get("replan_rounds")
    try:
        return max(0, min(1, int(value)))
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------- workdir --
def prepare_workdir(case, config, cases_path, workdir=None):
    """profile.yaml, the pasted sources and a COPY of the skill, per agent home."""
    workdir = legacy_control.workdir(workdir)
    if workdir:
        path = os.path.abspath(workdir)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
    else:
        path = tempfile.mkdtemp(prefix="vetflat-pipeline-%s-" % case["id"])
    plan_lines = []
    base = os.path.dirname(os.path.abspath(cases_path))
    for rel in case.get("files") or []:
        src = os.path.join(base, rel)
        dst = os.path.join(path, os.path.basename(rel))
        shutil.copyfile(src, dst)
        plan_lines.append("copy %s -> %s" % (rel, os.path.basename(rel)))

    homes = set()
    for role in ROLES + ("baseline",):
        conf = role_config(config, role)
        homes.add((conf or {}).get("agent") or config.get("agent") or "claude")
    src_dir = os.environ.get("VETFLAT_SKILL_DIR") or SKILL_DIR
    label = ("skills/vet-flat" if src_dir == SKILL_DIR
             else os.path.relpath(src_dir, ROOT) + " (pinned by VETFLAT_SKILL_DIR)")
    for agent in sorted(homes):
        home = os.path.join(path, SKILL_HOME.get(agent, SKILL_HOME["claude"]))
        if not os.path.isdir(home):
            os.makedirs(home, exist_ok=True)
        dst = os.path.join(home, "vet-flat")
        if os.path.lexists(dst):
            shutil.rmtree(dst, ignore_errors=True)
        # A copy, never a symlink: a workspace sandbox will not follow a link out of
        # the workspace, and the pinned folder must not move under a running sweep.
        shutil.copytree(src_dir, dst)
        plan_lines.append("copy %s -> %s/vet-flat"
                          % (label, SKILL_HOME.get(agent, SKILL_HOME["claude"])))

    os.makedirs(os.path.join(path, "sources"), exist_ok=True)
    return path, plan_lines


# ------------------------------------------------------------------- prompts --
COMMON = ("You are one role in the vet-flat role pipeline. Read {skill}/references/"
          "pipeline.md, the section named '{section}', and follow it exactly. This is an "
          "unattended benchmark run: there is no user to answer questions, so never stop "
          "to ask; when an input is unavailable, record it as unknown and carry on.")

PROMPTS = {
    "planner": (COMMON + "\n\nRead profile.yaml and plan.scaffold.json. The scaffold is "
                "the floor: you may ADD axes, script calls, paste requests and questions, "
                "and you may not drop anything it marks required. You may not read any "
                "page, run any script, or decide what survives - only what to go and get. "
                "The request is: {prompt}\nBudget mode: {mode}. Fixed-form tier: {tier}.\n"
                "Print ONE JSON object matching {skill}/references/plan-schema.json and "
                "nothing else: no prose before it, no code fence around it."),
    "executors": (COMMON + "\n\nYou are the executor for the axis group '{group}' "
                  "(axes {axes}). Read plan.json and work only your own axes. THE SCRIPTS "
                  "ARE AT {skill}/scripts/ - run them from there, and note that a bare "
                  "`scripts/...` path does not exist in this directory. Fill the "
                  "placeholders from profile.yaml and from what earlier calls returned.\n"
                  "SAVE EVERY SCRIPT'S OUTPUT: write the JSON a script printed to "
                  "sources/<name>.json before you quote it, and cite it as "
                  "\"pasted:<name>\". A quote nobody can open is a quote nobody can check.\n"
                  "Write NO verdicts, NO scores and NO arithmetic of your own: the only "
                  "sums allowed are scripts/calc.py calls, recorded in computed_by with "
                  "their output. Every found item carries the line you read it in, "
                  "verbatim. Anything you cannot get is an item with status unknown and a "
                  "`tried` list saying what you actually attempted - and an item you did "
                  "not even try for is worse than one you did.\n"
                  "FAILED FETCHES ARE NOT ANSWERS. A script whose JSON says ok: false, or "
                  "carries a curl error or http_status 0, failed: never record a count or a "
                  "null read out of it as a value (certificates_found: 0 after a dead search "
                  "is not zero certificates). When a primary call returns nothing or fails, "
                  "run the plan's calls marked `fallback`, then the other subcommands the "
                  "axis file in {skill}/references/axes/ names, before you write unknown; "
                  "put every attempt with its error in `tried`. Your time budget is large: "
                  "spending it is cheaper than an empty report.\n"
                  "ONE WORKED ITEM, exactly the shape yours must have:\n{example}\n"
                  "{extra}"
                  "Print ONE JSON object matching {skill}/references/evidence-schema.json "
                  "holding only your group's items, and nothing else."),
    "verifier": (COMMON + "\n\nscripts/verify.py has already run every check that has one "
                 "answer. Its table is in verify-table.txt and its JSON in "
                 "verified.deterministic.json. Read ONLY the items it flagged, and the "
                 "sources those items cite (they are files in sources/). You may re-run "
                 "scripts/verify.py and scripts/calc.py; you may not fetch anything new.\n"
                 "UNKNOWN IS NOT THE DEFAULT. An item verify.py passed stays passed unless "
                 "you have a reason to say otherwise; write unknown only where the evidence "
                 "itself says nobody could get the fact, or where you looked and still "
                 "cannot tell. Marking a whole file unknown is not caution, it is an empty "
                 "report.\n"
                 "A FAIL MUST CARRY ITS REASON. When you agree with a verify.py failure, "
                 "quote its reason back in your own `reason` field and name the rule id in "
                 "`rules`; a fail with no reason will be read as an opinion and dropped.\n"
                 "Then list at most one round of things worth going back for. You may "
                 "re-judge evidence; you may not invent an item.\n"
                 "Print ONE JSON object matching {skill}/references/verified-schema.json "
                 "and nothing else."),
    "integrator": (COMMON + "\n\nRead verified.json and evidence.json. WRITE report.json in "
                   "this directory, following {skill}/references/report-schema.json and "
                   "{skill}/references/report-contract.md. Use verified items only: "
                   "anything that is not there, or is there as fail or unknown, is unknown "
                   "in the report, and the reader is told what it costs not to know it. "
                   "Cite the evidence item ids in `sources` and `computed_by`. The first "
                   "line states the tier and that the pipeline ran: "
                   "'pipeline: planner/executor/verifier'. The request was: {prompt}"),
    "baseline": ("{prompt}\n\nWrite report.json in this directory following "
                 "{skill}/references/report-schema.json. The skill is installed at "
                 "{skill}; read its SKILL.md first."),
}

EXAMPLE_ITEM = json.dumps(collections.OrderedDict([
    ("id", "e-area"), ("axis", 2),
    ("claim", "certified internal floor area of this flat"),
    ("status", "ok"), ("value", 54.0), ("unit", "m2"),
    ("source", "pasted:epc-cert"),
    ("quote", "\"total_floor_area_m2\": 54.0"),
    ("fetched_at", "2026-09-06T09:00:00Z"),
    ("script", "scripts/epc.py cert 0000-0000-0000-0000-0000")]), ensure_ascii=False)
EXAMPLE_UNKNOWN = json.dumps(collections.OrderedDict([
    ("id", "e-reviews"), ("axis", 6),
    ("claim", "organic management review score for the building"),
    ("status", "unknown"),
    ("tried", ["review sites forbid automated access, so no script can get this",
               "sources/ holds no pasted reviews"])]), ensure_ascii=False)

REPLAN_EXTRA = ("\nThis is the ONE replan round. The verifier asked for these and nothing "
                "else:\n{asks}\nWork only those, and print only the items they produce.")


def role_prompt(role, config, case, prompt, group=None, axes=None, extra="",
                agent="claude"):
    return PROMPTS[role].format(
        skill=skill_rel(agent).replace(os.sep, "/"),
        section={"planner": "Planner", "executors": "Executors", "verifier": "Verifier",
                 "integrator": "Integrator", "baseline": "Integrator"}[role],
        prompt=prompt, mode=config.get("budget_mode") or "standard",
        tier=config.get("budget_mode") or "standard",
        group=group or "", axes=", ".join(str(a) for a in (axes or [])), extra=extra,
        example="  " + EXAMPLE_ITEM + "\n  " + EXAMPLE_UNKNOWN)


# ------------------------------------------------------------------ commands --
def answer_file(workdir, role, group=None):
    """Where a Codex role's last message lands. One per role: the executors run at the
    same time in the same directory, and a shared file would lose all but one answer."""
    name = "last-%s%s.txt" % (role, "-" + group if group else "")
    return os.path.join(workdir, re.sub(r"[^A-Za-z0-9._-]+", "-", name))


def build_role_command(role, conf, config, case, workdir, prompt, group=None):
    """The one command for one role, out of the runners bench/run.py already uses."""
    agent = conf["agent"]
    scoped = collections.OrderedDict(config)
    scoped["allowed_tools"] = role_tools(role, agent)
    scoped["main_model"] = conf.get("model")
    if agent == "codex":
        write_agents_md(workdir, role, config)
        return run_codex.build_command(scoped, case, workdir, conf.get("model"), prompt,
                                       out=answer_file(workdir, role, group))
    return runner.build_command("claude", case, conf.get("model"), workdir, prompt, scoped)


def write_agents_md(workdir, role, config):
    """Codex takes no --allowedTools, so the role's discipline is written where it reads."""
    text = ["# Instructions for this run",
            "",
            (config.get("append_system_prompt") or "").strip(),
            "",
            "You are the %s role of the vet-flat role pipeline. The tools this role may "
            "use are: %s. Use nothing else, and write no file except the one your role "
            "owns." % (role, ", ".join(role_tools(role, "codex")))]
    with io.open(os.path.join(workdir, "AGENTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(x for x in text if x is not None) + "\n")


def launch_many(commands, workdir, timeout, parallel, family, labels=None):
    """Run these commands through bench/launch.py, at most `parallel` in flight at once;
    results come back in the same order as `commands`.

    The executors run concurrently in one shared workdir - each already writes to its own
    answer file, see `answer_file` - so this is a thread pool over the one launcher every
    role uses, the same shape bench/docs_bench.py uses for its own row-level concurrency.
    Each call still gets bench/launch.py's closed stdin and provider_error
    outcome; only the fan-out is new here.
    """
    labels = list(labels or [None] * len(commands))
    width = 1 if legacy_control.active() else max(1, int(parallel or 1))
    if width <= 1 or len(commands) <= 1:
        return [legacy_control.run_cli(cmd, workdir, timeout, family, label=label)
                for cmd, label in zip(commands, labels)]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=width) as pool:
        return list(pool.map(
            lambda pair: legacy_control.run_cli(pair[0], workdir, timeout, family, label=pair[1]),
            zip(commands, labels)))


def record_role(roles, notes, role, conf, res, command, group=None, note_label=None):
    """Append this launch's row - with `provider_error` visible on it - and, if the
    launch left a note, add it to the run's notes too.

    `res` is the LaunchResult bench/launch.py returned. Every role's row and every note
    go through here, so a role that failed at the provider (rate limit, 5xx, ENOTFOUND)
    is recorded as such - attempts, exit code, both tails - and not read as an empty
    answer the model gave.
    """
    note = res.tail_note()
    roles.append(role_row(role, conf, res.seconds, res.usage, note, command, group,
                          provider_error=res.provider_error))
    roles[-1]["attempt_records"] = res.attempt_records
    if note:
        notes.append("%s: %s" % (note_label or role, note))
    return note


def last_text(agent, workdir, role, text, group=None):
    """A role's final message: the file Codex was told to write it to, else `text` -
    the LaunchResult's own text, already Claude Code's extracted answer, or Codex's raw
    stdout."""
    if agent == "codex":
        path = answer_file(workdir, role, group)
        if os.path.exists(path):
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        return run_codex.last_message(workdir, text)
    return text


def answer_object(agent, text, answer_path=None):
    """The one JSON object a role printed, out of the LaunchResult's text.

    bench/launch.py already unwraps Claude Code's `--output-format json` envelope, so
    `text` is the role's own printed answer for claude. Codex prints a JSONL EVENT
    STREAM on stdout instead, whose first object is an event and not the answer at all,
    so its answer is read from the file `-o` named.
    """
    if agent == "codex":
        if answer_path and os.path.exists(answer_path):
            with io.open(answer_path, encoding="utf-8", errors="replace") as fh:
                found = runner.first_json_object(fh.read())
            if found is not None:
                return found
        return None
    found = runner.first_json_object(text)
    if isinstance(found, dict) and isinstance(found.get("result"), str):
        inner = runner.first_json_object(found["result"])
        if inner is not None:
            return inner
    return found


# --------------------------------------------------------------------- steps --
def write_json(path, payload):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return path


def retarget(plan, skill):
    """Point every planned call at the skill where this agent actually installs it."""
    prefix = skill.replace(os.sep, "/") + "/"
    for axis in plan.get("axes") or []:
        for call in (axis or {}).get("scripts") or []:
            cmd = call.get("cmd") or ""
            if cmd.startswith("scripts/"):
                call["cmd"] = prefix + cmd
            else:
                call["cmd"] = re.sub(r"(?<![\w./])scripts/", prefix, cmd)
    return plan


def groups_of(plan):
    """[(group, [axis ids])] in plan order, so executors split the work the plan did."""
    out = collections.OrderedDict()
    for axis in plan.get("axes") or []:
        if isinstance(axis, dict) and axis.get("group"):
            out.setdefault(axis["group"], []).append(axis.get("id"))
    return list(out.items())


def merge_evidence(files, case=None, flat=None):
    """One evidence.json out of the executors', ids kept unique by prefixing the group."""
    items, seen = [], set()
    for group, doc in files:
        for item in (doc or {}).get("items") or []:
            if not isinstance(item, dict):
                continue
            item = collections.OrderedDict(item)
            ident = str(item.get("id") or "x")
            if ident in seen:
                ident = "%s-%s" % (group, ident)
            while ident in seen:
                ident += "x"
            item["id"] = ident
            seen.add(ident)
            items.append(item)
    return collections.OrderedDict([("schema", verifier_tool.EVIDENCE_SCHEMA),
                                    ("case", case), ("flat", flat), ("items", items)])


def steps_for(config):
    """[(role, conf)] in the order they run, skipping the roles this arm does not use."""
    out = []
    if role_config(config, "planner") is None and role_config(config, "executors") is None:
        base = (config.get("pipeline") or {}).get("baseline")
        conf = collections.OrderedDict([("agent", config.get("agent") or "claude"),
                                        ("model", ((base or {}).get("model")
                                          if isinstance(base, dict) else None)
                                         or config.get("main_model")),
                                        ("parallel", 1), ("note", None)])
        out.append(("baseline", conf))
    for role in ROLES:
        conf = role_config(config, role)
        if conf is not None:
            out.append((role, conf))
    return out


# ----------------------------------------------------------------- the run --
def run_pipeline(args, case, config):
    """Every role in turn, then the grader. Returns (exit code, scorecard row)."""
    for _role, conf in steps_for(config):
        legacy_control.require_model(conf.get("model"), conf.get("agent"))
    started = time.time()
    mode = args.budget_mode or config.get("budget_mode") or "standard"
    arm = config["name"] + ("-" + args.budget_mode if args.budget_mode else "")
    config = collections.OrderedDict(config)
    config["budget_mode"] = mode          # the prompts state the mode this run is in
    legacy_control.job("%s/%s/%s" % (arm, case["id"], args.run))
    args.arm = arm                        # every raw file this run writes carries it
    del KEPT[:]                       # one list per run, not per process
    workdir, plan_lines = prepare_workdir(case, config, args.cases, args.workdir)
    applied = runner.apply_budget_mode(workdir, mode)
    if applied:
        plan_lines.append("set budget_mode: %s in the run's profile.yaml" % applied)

    prompt = case["prompt"]
    scaffold = planner_tool.scaffold(mode if mode in planner_tool.MODES else "standard",
                                     tier=mode, case=case["id"])
    # The scaffold writes "scripts/epc.py ...", which is right relative to the skill and
    # wrong from the working directory the executors run in. On the first pilot four
    # executors burned a call on "can't open file scripts/epc.py" and two never found the
    # scripts at all, so the paths are resolved here, once, for everybody.
    retarget(scaffold, skill_rel(config.get("agent") or "claude"))
    write_json(os.path.join(workdir, "plan.scaffold.json"), scaffold)
    if not args.dry_run:
        keep(args, arm, case, "plan-scaffold", scaffold)
    # plan.json starts as the scaffold, so an arm with no planner - or a planner that
    # never starts - still leaves the executors something real to work from.
    write_json(os.path.join(workdir, "plan.json"), scaffold)
    plan_lines.append("scripts/plan.py wrote plan.scaffold.json and the first plan.json "
                      "(%d axes, %d fixed questions)"
                      % (len(scaffold["axes"]), len(scaffold["fixed_form_ids"])))

    steps = steps_for(config)
    roles, notes, worst = [], [], 0
    plan_doc, evidence_doc, verified_doc = scaffold, None, None
    rounds_used = 0

    if args.dry_run:
        return dry_run(args, case, config, arm, mode, workdir, plan_lines, steps, prompt,
                       scaffold)

    for role, conf in steps:
        if role == "executors":
            plan_doc, evidence_doc, rounds_used = run_executor_rounds(
                args, case, config, conf, workdir, prompt, plan_doc, roles, notes)
            continue
        if role == "verifier":
            verified_doc = run_verifier(args, case, config, conf, workdir, prompt,
                                        evidence_doc, roles, notes)
            if verified_doc and verified_doc.get("replan") and replan_rounds(config) \
                    and rounds_used == 0 and role_config(config, "executors"):
                plan_doc, evidence_doc, rounds_used = run_executor_rounds(
                    args, case, config, role_config(config, "executors"), workdir, prompt,
                    plan_doc, roles, notes, replan=verified_doc.get("replan"),
                    evidence=evidence_doc)
                verified_doc = run_verifier(args, case, config, conf, workdir, prompt,
                                            evidence_doc, roles, notes, again=True)
            continue

        if role == "integrator":
            if verified_doc is None:
                # P1 has no verifier, and the integrator is still told to read
                # verified.json. Run the deterministic half so the file it is pointed at
                # exists and says something true, rather than nothing at all.
                tier = mode
                verified_doc = deterministic_verify(args, workdir, evidence_doc or {}, tier)
                write_json(os.path.join(workdir, "verified.json"), verified_doc)
                keep(args, arm, case, "verified", verified_doc)
                notes.append("no verifier in this arm; scripts/verify.py alone produced "
                             "verified.json (%s)"
                             % json.dumps(verify_summary(verified_doc)["failed_by_rule"]))
            keep(args, arm, case, "integrator-input-evidence", evidence_doc or {})
            keep(args, arm, case, "integrator-input-verified", verified_doc or {})
        command = build_role_command(role, conf, config, case, workdir,
                                     role_prompt(role, config, case, prompt,
                                                 agent=conf["agent"]))
        res = legacy_control.run_cli(command, workdir, args.timeout, conf["agent"],
                         label="%s %s" % (arm, role))
        record_role(roles, notes, role, conf, res, command)
        write_raw(args, arm, case, role, res.text)

        if role == "planner":
            answered = answer_object(conf["agent"], res.text,
                                     answer_file(workdir, role))
            plan_doc = keep_the_plan_honest(answered, scaffold, mode, notes)
            retarget(plan_doc, skill_rel(conf["agent"]))
            write_json(os.path.join(workdir, "plan.json"), plan_doc)
            keep(args, arm, case, "plan", plan_doc)
        elif role == "baseline":
            report, _path = runner.find_report(workdir, last_text(conf["agent"], workdir,
                                                                  role, res.text))
            if report is None:
                notes.append("the baseline run wrote no report, so there is nothing to "
                             "verify")
                worst = 1
            else:
                evidence_doc = verifier_tool.evidence_from_report(report, case["id"])
                write_json(os.path.join(workdir, "evidence.json"), evidence_doc)
                # Move it out of the way. Left where it is, a silent integrator would
                # end with the BASELINE's report being found and graded under this arm -
                # an ablation quietly scoring its own control.
                moved = set_aside(workdir, _path)
                notes.append("evidence derived from the baseline report: %d items%s"
                             % (len(evidence_doc["items"]),
                                "; the baseline report was moved to %s" % moved
                                if moved else ""))

    if evidence_doc is None:
        evidence_doc = collections.OrderedDict([("schema", verifier_tool.EVIDENCE_SCHEMA),
                                                ("case", case["id"]), ("items", [])])
        write_json(os.path.join(workdir, "evidence.json"), evidence_doc)
    if verified_doc is None:
        verified_doc = deterministic_verify(args, workdir, evidence_doc, mode)
        write_json(os.path.join(workdir, "verified.json"), verified_doc)

    wall = time.time() - started
    return finish(args, case, config, arm, mode, workdir, roles, notes, wall, worst,
                  evidence_doc, verified_doc, rounds_used)


def set_aside(workdir, path):
    """Move the baseline's report out of the way and return its new name."""
    if not path or not os.path.exists(path):
        return None
    target = os.path.join(workdir, "report.baseline.json")
    try:
        shutil.move(path, target)
    except (IOError, OSError):
        return None
    return os.path.basename(target)


def role_row(role, conf, wall, usage, note, command, group=None, provider_error=False):
    return collections.OrderedDict([
        ("role", role), ("group", group), ("agent", conf["agent"]),
        ("model", conf.get("model")), ("wall_s", round(wall, 1)),
        ("total_tokens", runner.total_tokens(usage)),
        ("tokens", usage), ("note", note),
        ("provider_error", bool(provider_error)),
        ("allowed_tools", role_tools(role, conf["agent"])),
        ("command", runner.shell(command) if command else None)])


def keep_the_plan_honest(answered, scaffold, mode, notes):
    """The planner's plan if it kept everything required; otherwise the scaffold."""
    if not isinstance(answered, dict) or not answered.get("axes"):
        notes.append("the planner printed no usable plan; the scaffold was used instead")
        return scaffold
    result = planner_tool.check(answered, mode if mode in planner_tool.MODES else "standard",
                               tier=mode)
    # call_shape ignores values but not the script's own path, so compare like with like.
    if result["ok"]:
        return answered
    notes.append("the planner's plan dropped something required (%d axes, %d calls, %d "
                 "fixed questions); the scaffold was used instead"
                 % (len(result["missing_axes"]), len(result["missing_calls"]),
                    len(result["missing_fixed_form_ids"])))
    return scaffold


def run_executor_rounds(args, case, config, conf, workdir, prompt, plan_doc, roles, notes,
                        replan=None, evidence=None):
    """One round of executors, in parallel, one per axis group. Returns the merged file."""
    groups = groups_of(plan_doc)
    if replan:
        asks = collections.OrderedDict()
        for entry in replan:
            axis = entry.get("axis")
            for group, axes in groups:
                if axis in axes:
                    asks.setdefault(group, []).append(entry.get("ask") or "")
        groups = [(g, a) for g, a in groups if g in asks]
    else:
        asks = {}
    if not groups:
        return plan_doc, evidence, 1 if replan else 0

    commands, prompts, labels = [], [], []
    for group, axes in groups:
        extra = (REPLAN_EXTRA.format(asks="\n".join("- " + a for a in asks.get(group, [])))
                 if replan else "")
        text = role_prompt("executors", config, case, prompt, group, axes, extra,
                           conf["agent"])
        prompts.append(text)
        commands.append(build_role_command("executors", conf, config, case, workdir, text,
                                           group))
        labels.append("%s executors[%s]%s" % (config["name"], group,
                                              "-again" if replan else ""))
    results = launch_many(commands, workdir, args.timeout, conf.get("parallel"),
                          conf["agent"], labels)

    collected = []
    for (group, _axes), command, res in zip(groups, commands, results):
        record_role(roles, notes, "executors", conf, res, command, group,
                   note_label="executor %s" % group)
        write_raw(args, config["name"], case,
                  "executor-%s%s" % (group, "-2" if replan else ""), res.text)
        doc = answer_object(conf["agent"], res.text,
                            answer_file(workdir, "executors", group))
        if isinstance(doc, dict):
            collected.append((group, doc))
            folder = os.path.join(workdir, "evidence")
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            write_json(os.path.join(folder, "%s.json" % group), doc)
            keep(args, config["name"], case,
                 "evidence-%s%s" % (group, "-2" if replan else ""), doc)
            roles[-1]["produced"] = evidence_summary(doc)
        else:
            notes.append("executor %s printed no usable evidence object" % group)
            roles[-1]["produced"] = evidence_summary(None)

    if replan and evidence:
        merged = merge_evidence([("round0", evidence)] + collected, case["id"],
                                evidence.get("flat"))
    else:
        merged = merge_evidence(collected, case["id"])
    write_json(os.path.join(workdir, "evidence.json"), merged)
    keep(args, config["name"], case, "evidence%s" % ("-round2" if replan else ""), merged)
    return plan_doc, merged, 1 if replan else 0


def deterministic_verify(args, workdir, evidence_doc, tier):
    """scripts/verify.py, in process, over what the executors wrote."""
    report = None
    report_path = os.path.join(workdir, "report.json")
    if os.path.exists(report_path):
        try:
            report = verifier_tool.read_json(report_path)
        except ValueError:
            report = None
    gold = None
    if args.gold and os.path.exists(args.gold):
        try:
            gold = verifier_tool.read_json(args.gold)
        except ValueError:
            gold = None
    return verifier_tool.verify(
        evidence_doc, report, verifier_tool.load_sources(os.path.join(workdir, "sources")),
        tier, args.strict, gold=gold,
        gold_id=args.gold_id or (getattr(args, "case_row", None) or {}).get("gold_id"))


def run_verifier(args, case, config, conf, workdir, prompt, evidence_doc, roles, notes,
                 again=False):
    """verify.py first, then the model on the flagged items only."""
    tier = args.budget_mode or config.get("budget_mode") or "standard"
    round_tag = "-2" if again else ""
    deterministic = deterministic_verify(args, workdir, evidence_doc or {}, tier)
    write_json(os.path.join(workdir, "verified.deterministic.json"), deterministic)
    table_text = verifier_tool.table(deterministic)
    with io.open(os.path.join(workdir, "verify-table.txt"), "w", encoding="utf-8") as fh:
        fh.write(table_text + "\n")
    keep(args, config["name"], case, "verify-deterministic" + round_tag, deterministic)
    keep(args, config["name"], case, "verify-table" + round_tag, table_text + "\n")

    command = build_role_command("verifier", conf, config, case, workdir,
                                 role_prompt("verifier", config, case, prompt,
                                             agent=conf["agent"]))
    res = legacy_control.run_cli(command, workdir, args.timeout, conf["agent"],
                     label="%s verifier%s" % (config["name"], "-again" if again else ""))
    record_role(roles, notes, "verifier" + ("-again" if again else ""), conf, res, command,
               note_label="verifier")
    write_raw(args, config["name"], case, "verifier" + ("-2" if again else ""), res.text)

    answered = answer_object(conf["agent"], res.text, answer_file(workdir, "verifier"))
    if isinstance(answered, dict) and answered.get("items"):
        verified = merge_verdicts(deterministic, answered, notes)
    else:
        notes.append("the verifier printed no usable object; the deterministic result "
                     "stands on its own")
        verified = deterministic
    write_json(os.path.join(workdir, "verified.json"), verified)
    keep(args, config["name"], case, "verified" + round_tag, verified)
    roles[-1]["verified"] = verify_summary(verified)
    roles[-1]["deterministic"] = verify_summary(deterministic)
    return verified


def merge_verdicts(deterministic, answered, notes):
    """The model's verdicts laid over the deterministic ones, by id.

    The verifier is told to read ONLY the flagged items, so it returns only those. Taking
    its file as the whole answer would leave every item it sensibly ignored out of
    verified.json - and the integrator treats a missing item as unknown, which would
    empty the report. So the deterministic result is the base and the model may only
    change the entries it actually spoke about.

    An id the model invented is dropped and said so: the verifier may re-judge evidence,
    never create it.
    """
    merged = collections.OrderedDict(
        (v.get("id"), collections.OrderedDict(v)) for v in deterministic.get("items") or [])
    changed, spoke, invented = 0, 0, []
    for verdict in answered.get("items") or []:
        if not isinstance(verdict, dict):
            continue
        ident = verdict.get("id")
        if ident not in merged:
            invented.append(str(ident))
            continue
        if verdict.get("state") in ("pass", "fail", "unknown"):
            if merged[ident].get("state") != verdict["state"]:
                changed += 1          # only a state that MOVED has changed
            merged[ident]["state"] = verdict["state"]
            merged[ident]["reason"] = verdict.get("reason") or merged[ident].get("reason")
            merged[ident]["rules"] = verdict.get("rules") or merged[ident].get("rules") or []
            merged[ident]["checked_by"] = "verifier"
            spoke += 1
    if invented:
        notes.append("the verifier named %d item(s) that are not in the evidence (%s); "
                     "dropped" % (len(invented), ", ".join(invented[:5])))
    notes.append("the verifier spoke about %d of %d verdicts and moved %d of them"
                 % (spoke, len(merged), changed))
    out = collections.OrderedDict(deterministic)
    out["items"] = list(merged.values())
    if answered.get("replan"):
        out["replan"] = [r for r in answered["replan"] if isinstance(r, dict)]
    return out


def keep(args, arm, case, name, payload):
    """Persist one intermediate file into raw/, next to the roles' event streams.

    The first pilot kept only the event streams, so answering "what did the executors
    actually write, and what did verify.py say about it" meant re-deriving both from
    JSONL. The workdir is a temp directory that does not survive the run, so anything
    not copied here is gone.
    """
    day = args.day or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    folder = os.path.join(args.results or runner.RESULTS, day, "raw")
    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    stem = runner.raw_name("%s-%s" % (getattr(args, "arm", None) or arm, name),
                           case["id"], args.run)
    path = os.path.join(folder, stem if isinstance(payload, str)
                        else stem)
    if isinstance(payload, str):
        path = path[:-len(".json")] + ".txt"
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(payload if isinstance(payload, str)
                 else json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    KEPT.append(os.path.basename(path))
    return path


def evidence_summary(doc):
    """items produced, how many were actually got, how many nobody even tried for."""
    items = [i for i in (doc or {}).get("items") or [] if isinstance(i, dict)]
    ok = [i for i in items if (i.get("status") or "ok") != "unknown"]
    return collections.OrderedDict([
        ("items", len(items)), ("ok", len(ok)),
        ("unknown", len(items) - len(ok)),
        ("with_quote", sum(1 for i in ok if i.get("quote"))),
        ("with_source", sum(1 for i in ok if i.get("source"))),
        ("untried", sum(1 for i in items
                        if (i.get("status") == "unknown") and not (i.get("tried") or [])))])


def verify_summary(doc):
    """pass / fail / unknown, and which rules did the failing."""
    items = [v for v in (doc or {}).get("items") or [] if isinstance(v, dict)]
    rules = collections.Counter()
    for verdict in items:
        if verdict.get("state") == "fail":
            for rule in verdict.get("rules") or ["(no rule named)"]:
                rules[rule] += 1
    counts = (doc or {}).get("counts") or {}
    return collections.OrderedDict([
        ("items", len(items)),
        ("pass", sum(1 for v in items if v.get("state") == "pass")),
        ("fail", sum(1 for v in items if v.get("state") == "fail")),
        ("unknown", sum(1 for v in items if v.get("state") == "unknown")),
        ("failed_by_rule", collections.OrderedDict(sorted(rules.items()))),
        ("quotes_unchecked", len(counts.get("quotes_unchecked") or [])),
        ("fixed_form_missing", list(counts.get("fixed_form_missing") or []))])


def write_raw(args, arm, case, role, stdout):
    """One raw file per role, named like every other raw file in the results tree."""
    arm = getattr(args, "arm", None) or arm
    day = args.day or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    folder = os.path.join(args.results or runner.RESULTS, day, "raw")
    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    name = runner.raw_name("%s-%s" % (arm, role), case["id"], args.run)
    with io.open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
        fh.write(stdout or "")


def results_when(day):
    """The timestamp behind a --day label. A label that is not a date ("ablation-2026-09-07")
    names the folder and nothing else: the row is stamped with now. Before 2026-09-07 such
    a label crashed finish() after forty minutes of model calls, and lost the run."""
    try:
        return datetime.datetime.strptime(day, "%Y-%m-%d")
    except (TypeError, ValueError):
        return datetime.datetime.utcnow()


# -------------------------------------------------------------------- output --
def finish(args, case, config, arm, mode, workdir, roles, notes, wall, worst,
           evidence_doc, verified_doc, rounds_used):
    kept_names = list(KEPT)
    day = args.day or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    when = results_when(day)
    report, path = runner.find_report(workdir, "")
    raw_path = runner.write_raw(json.dumps({"roles": roles, "notes": notes},
                                           ensure_ascii=False, indent=1),
                                arm, case["id"], args.run, when=when,
                                results_root=args.results, day=day)
    try:
        runner.persist_report(report, arm, case["id"], args.run, when=when,
                              results_root=args.results, day=day)
    except Exception as exc:                                # bookkeeping never kills a run
        print("could not persist report: %s" % exc, file=sys.stderr)

    usage = totals(roles)
    labelled = collections.OrderedDict(config)
    labelled["name"], labelled["budget_mode"] = arm, mode
    card = None
    if report is None:
        stray = os.path.join(workdir, "report.json")
        if os.path.exists(stray):
            # The integrator wrote a report that does not parse. Keep it: a role that
            # wrote 2,000 lines of almost-JSON is a different failure from one that wrote
            # nothing, and the next reader needs to see which (P3-codex, 2026-09-07).
            try:
                with io.open(stray, encoding="utf-8") as fh:
                    broken = fh.read()
                runner.write_raw(broken, arm + "-report-invalid", case["id"], args.run, when=when,
                                 results_root=args.results, day=day)
                notes.append("report.json is present but not valid JSON (%d chars, kept under raw/)"
                             % len(broken))
            except (IOError, OSError) as exc:
                notes.append("report.json is present but unreadable: %s" % exc)
        else:
            notes.append("no report.json in the working directory")
        worst = 1
    else:
        try:
            card = grader.grade(report, case, grader.case_profile_path(args.cases, case))
            card["report"] = path
        except Exception as exc:      # a malformed report is a result, not a crash
            notes.append("the report could not be graded: %s" % exc)
            card, worst = None, 1

    row = runner.make_row("pipeline", pipeline_model(roles), case, card, wall, usage,
                          workdir, "; ".join(r["command"] or "" for r in roles),
                          "; ".join(notes) or None, None, labelled, args.run, raw_path)
    row["roles"] = roles
    row["pipeline"] = collections.OrderedDict([
        ("arm", arm), ("budget_mode", mode),
        ("roles_run", [r["role"] for r in roles]),
        ("replan_rounds_used", rounds_used),
        ("evidence", evidence_summary(evidence_doc)),
        ("verified", verify_summary(verified_doc)),
        ("per_role", [collections.OrderedDict(
            [("role", r["role"]), ("group", r.get("group"))]
            + ([("produced", r["produced"])] if r.get("produced") else [])
            + ([("verified", r["verified"])] if r.get("verified") else [])
            + ([("deterministic", r["deterministic"])] if r.get("deterministic") else []))
            for r in roles]),
        ("artefacts_kept", sorted(set(kept_names))),
        # kept for the arms already in bench/results: the old flat keys still read.
        ("evidence_items", len(evidence_doc.get("items") or [])),
        ("verified_pass", sum(1 for v in verified_doc.get("items") or []
                              if v.get("state") == "pass")),
        ("verified_fail", sum(1 for v in verified_doc.get("items") or []
                              if v.get("state") == "fail")),
        ("verified_unknown", sum(1 for v in verified_doc.get("items") or []
                                 if v.get("state") == "unknown"))])
    suff = (verified_doc or {}).get("sufficiency")
    row["information_sufficiency"] = (suff or {}).get("sufficiency")
    row["information_sufficiency_detail"] = suff
    baseline_path = os.path.join(workdir, "report.baseline.json")
    if os.path.exists(baseline_path):
        # The check-only arm ran the single agent first; grade that report too, so the
        # row carries its own control: what the check changed is the difference.
        try:
            with io.open(baseline_path, encoding="utf-8") as fh:
                base_report = json.load(fh, object_pairs_hook=collections.OrderedDict)
            base_card = grader.grade(base_report, case, grader.case_profile_path(args.cases, case))
            row["baseline"] = collections.OrderedDict(
                (k, base_card.get(k)) for k in ("summary", "fact_recall", "stable_fact_recall",
                                                "fabrications", "citations", "unknown_honesty")
                if k in base_card)
            runner.persist_report(base_report, arm + "-baseline", case["id"], args.run, when=when,
                                  results_root=args.results, day=day)
            notes.append("baseline graded: %s" % base_card.get("summary"))
        except Exception as exc:                            # bookkeeping never kills a run
            notes.append("the baseline report could not be graded: %s" % exc)
        row["note"] = "; ".join(n for n in notes if n) or None
    runner.append_scorecard(row, when=when, results_root=args.results, day=day)
    if card:
        print(card["summary"])
    for note in notes:
        print("note: %s" % note, file=sys.stderr)
    if not args.keep and not args.workdir and not legacy_control.active():
        shutil.rmtree(workdir, ignore_errors=True)
    return worst, row


def totals(roles):
    """One usage block for the whole pipeline: every role's tokens added up."""
    out = collections.OrderedDict()
    for role in roles:
        usage = role.get("tokens") or {}
        for key in runner.USAGE_KEYS + ("total_cost_usd",):
            value = usage.get(key)
            if isinstance(value, (int, float)):
                out[key] = out.get(key, 0) + value
    total = runner.total_tokens(out)
    if total is not None:
        out["total_tokens"] = total
    return out or None


def pipeline_model(roles):
    """The models this pipeline actually used, as one readable string."""
    seen = []
    for role in roles:
        label = "%s=%s" % (role["role"], role.get("model") or "default")
        if label not in seen:
            seen.append(label)
    return " ".join(seen) or None


def dry_run(args, case, config, arm, mode, workdir, plan_lines, steps, prompt, scaffold):
    print("case:     %s  (%s)" % (case["id"], case.get("address") or "no address"))
    print("arm:      %s   [%s]  factor: %s"
          % (arm, config.get("phase"), config.get("factor")))
    print("mode:     %s   replan rounds: %d" % (mode, replan_rounds(config)))
    print("workdir:  %s" % workdir)
    for line in plan_lines:
        print("          %s" % line)
    print("grader:   bench/grade.py, exactly as bench/run.py calls it")
    if args.gold:
        print("gold:     %s  (information-sufficiency probe, deterministic, no tokens)"
              % args.gold)
    print("")
    groups = groups_of(scaffold)
    step_no = 0
    for role, conf in steps:
        if role == "executors":
            for group, axes in groups:
                step_no += 1
                text = role_prompt("executors", config, case, prompt, group, axes, "",
                                   conf["agent"])
                command = build_role_command("executors", conf, config, case, workdir,
                                             text, group)
                show_step(step_no, "executors[%s]" % group, conf, command, text,
                          conf.get("parallel"))
            continue
        if role == "verifier":
            print("     (scripts/verify.py runs first and writes verify-table.txt; the "
                  "verifier model reads only what it flagged)")
        step_no += 1
        text = role_prompt(role, config, case, prompt, agent=conf["agent"])
        command = build_role_command(role, conf, config, case, workdir, text)
        show_step(step_no, role, conf, command, text)
    if not args.keep and not args.workdir and not legacy_control.active():
        shutil.rmtree(workdir, ignore_errors=True)
    return 0, None


def show_step(number, label, conf, command, prompt, parallel=None):
    print("%2d. %-22s agent %-7s model %-14s tools %s%s"
          % (number, label, conf["agent"], conf.get("model") or "(default)",
             ", ".join(role_tools(label, conf["agent"])),
             "   parallel %d" % parallel if parallel and parallel > 1 else ""))
    print("    prompt: %s" % (prompt.splitlines() or [""])[0][:150])
    print("    %s" % runner.shell(command))


# --------------------------------------------------------------------- main --
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="a config from bench/ab/configs with a "
                                                    "`pipeline:` block")
    ap.add_argument("--cases", default=os.path.join(ROOT, "evals", "evals.json"),
                    help="a cases file in the evals/evals.json shape")
    ap.add_argument("--case", help="the case id; default every case in the file")
    ap.add_argument("--run", type=int, default=1, help="which repeat this is")
    ap.add_argument("--budget-mode", dest="budget_mode", choices=("lite", "standard", "deep"),
                    help="override the config's budget_mode and name the arm "
                         "<config>-<mode> in the scorecard")
    ap.add_argument("--parallel", type=int, help="override the executors' parallel width")
    ap.add_argument("--timeout", type=int,
                    default=int(os.environ.get("VETFLAT_RUN_TIMEOUT", 1800)),
                    help="seconds per ROLE, default 1800")
    ap.add_argument("--gold", help="BENCH ONLY: gold file for the information-sufficiency "
                                   "probe")
    ap.add_argument("--gold-id", dest="gold_id", help="which candidate in the gold file")
    ap.add_argument("--strict", action="store_true",
                    help="verify.py --strict: an unknown nobody tried is a failure")
    ap.add_argument("--results", help="results root; default bench/results")
    ap.add_argument("--day", help="the date folder to write into, YYYY-MM-DD")
    ap.add_argument("--workdir", help="use this directory instead of a fresh temp one")
    ap.add_argument("--keep", action="store_true", help="do not delete the temp workdir")
    ap.add_argument("--dry-run", action="store_true",
                    help="print every role's command and the first line of its prompt")
    legacy_control.add_arguments(ap)
    return ap


@legacy_control.entrypoint
def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.results:
        runner.RESULTS = os.path.abspath(args.results)
    if not os.path.exists(args.cases):
        print("usage error: no cases file at %s" % args.cases, file=sys.stderr)
        return 2
    try:
        config = load_config(args.config)
    except (IOError, OSError, ValueError) as exc:
        print("usage error: %s" % exc, file=sys.stderr)
        return 2
    if not steps_for(config):
        print("usage error: config %s has no pipeline roles" % config["name"],
              file=sys.stderr)
        return 2
    if args.parallel:
        block = (config.get("pipeline") or {}).get("executors")
        if isinstance(block, dict):
            block["parallel"] = args.parallel

    with io.open(args.cases, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    cases = [c for c in (doc.get("evals") or [])
             if not args.case or c.get("id") == args.case]
    if not cases:
        print("usage error: no case %r in %s" % (args.case, args.cases), file=sys.stderr)
        return 2

    worst = 0
    for case in cases:
        args.case_row = case
        code, _row = run_pipeline(args, case, config)
        worst = max(worst, code)
        if code and not args.dry_run:
            return worst
    return worst


if __name__ == "__main__":
    sys.exit(main())
