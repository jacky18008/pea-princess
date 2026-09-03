#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run one vet-flat eval case against one agent, grade the report, record the score.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHAT THIS DOES
==============
1. Builds a clean working directory: the case's ``profile.yaml`` and the skill
   itself, linked into the folder that agent looks in
   (``.claude/skills/vet-flat`` for Claude Code, ``.agents/skills/vet-flat`` for
   the others, which is the convention ``npx skills add`` installs into).
2. Builds the non-interactive command for that agent out of DOCUMENTED flags that
   SCOPE tool access. It never passes a flag whose job is to skip a permission
   prompt or disable a sandbox, and it never runs an agent as a different user.
   With ``--dry-run`` it prints the plan and the command and stops.
3. Runs the command with a timeout, then looks for ``report.json`` in the working
   directory. If the agent printed the report instead of writing it, the first
   JSON object in stdout is used.
4. Grades the report with ``bench/grade.py`` and appends one row to
   ``bench/results/<date>/scorecard.json`` and ``scorecard.md``.
5. Writes the run's stdout verbatim to
   ``bench/results/<date>/raw/<config>-<case>-<run>.json`` so a later grader, or a
   later argument, can go back to what the agent actually said.

THE A/B CONFIGS
===============
``--config <yaml>`` reads one file from ``bench/ab/configs`` and applies it:
``append_system_prompt`` is appended to the agent's system prompt, ``allowed_tools``
becomes ``--allowedTools``, ``main_model`` becomes ``--model`` when ``--model`` is not
given, and ``budget_mode`` is written into the run's own copy of ``profile.yaml`` so
the skill's budget logic and the prompt appendix agree. The config's name, phase and
factor go into the scorecard row, next to the wall time, ``total_cost_usd`` and the
token counts (``usage`` and ``modelUsage`` when Claude Code reports them).

``--cases <file>`` swaps the case file. The default is ``evals/evals.json``; the A/B
suite uses ``bench/private/cases_private.json``.

Two cases in the suite are conversations, not flats: the user asks what the skill
does, or says they have no idea where to start. For those there is no profile and
no report - the skill is still linked in so the agent can read its own pitch, and
what gets graded is the plain text that comes back, by the checks in the case's
expected_facts. A case with ``prompt_variants`` is run once per variant (the
capability question is asked in Chinese and in English) and produces one scorecard
row each, labelled ``<case>#<variant>``; ``--variant zh`` runs just one.

THE AGENTS
==========
claude    TESTED (dry run). ``claude -p <prompt> --allowedTools "Bash(python3:*)"
          Read Write --output-format json [--model NAME]``. ``--allowedTools``
          names the tools this run may use; everything else stays unavailable, so
          nothing is bypassed. ``--output-format json`` is what carries the cost
          and token counts back.
codex     TESTED (dry run). ``codex exec --cd <workdir> --sandbox workspace-write
          -c sandbox_workspace_write.network_access=true --skip-git-repo-check
          [--model NAME] <prompt>``. Codex's sandbox blocks network by default,
          which stops every fetcher in this skill; the documented config key turns
          network on INSIDE the sandbox and leaves the sandbox in place.
gemini    UNTESTED. ``gemini --prompt <prompt> [--model NAME]``.
opencode  UNTESTED. ``opencode run <prompt> [--model NAME]``.
api       A chat-only layer, no shell and no tools: one POST to an
          OpenAI-compatible ``/v1/chat/completions``. The system message is the
          prompt pack plus the "you fetch, I read" protocol; the user message is
          the case prompt plus the pasted truth fixtures, exactly as a person in a
          chat box would paste them. This measures whether a model can write a
          correct report from material handed to it - the manual mode the skill
          describes - separately from whether it can run tools.
          Needs OPENAI_BASE_URL and OPENAI_API_KEY; it says so and stops if not.

Standard library only. Python 3.9. The one network call (api mode) goes through
``skills/vet-flat/scripts/_fetch.py``, which shells out to curl, so this file
opens no sockets of its own.

Usage:
  bench/run.py --agent claude --case e14-marsh-wall-301 --dry-run
  bench/run.py --agent codex  --case e14-marsh-wall-301 --dry-run
  bench/run.py --agent claude --case e14-marsh-wall-301 --model opus --timeout 900
  bench/run.py --agent api --case e14-marsh-wall-301 --model gpt-4.1-mini
  bench/run.py --agent claude --case explain-capabilities --dry-run
  bench/run.py --agent api --case no-idea-intake --model <name>
  bench/run.py --agent claude --all-cases --dry-run
  bench/run.py --agent claude --config B-lean --cases bench/private/cases_private.json \
               --case v2-buck --run-index 1 --dry-run

Exit codes: 0 the case ran and was graded, 1 it did not produce a gradeable
report, 2 usage error.
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
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SKILL_DIR = os.path.join(ROOT, "skills", "vet-flat")
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")
RESULTS = os.path.join(HERE, "results")
PROMPT_PACK = os.path.join(ROOT, "dist", "prompt-pack", "INSTRUCTIONS.md")
INPUTS_MD = os.path.join(SKILL_DIR, "references", "inputs.md")
ONBOARDING_MD = os.path.join(SKILL_DIR, "references", "onboarding.md")

sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import grade as grader  # noqa: E402

AGENTS = ("claude", "codex", "gemini", "opencode", "api")
SHELL_AGENTS = ("claude", "codex", "gemini", "opencode")
SKILL_HOME = {"claude": os.path.join(".claude", "skills"),
              "codex": os.path.join(".agents", "skills"),
              "gemini": os.path.join(".agents", "skills"),
              "opencode": os.path.join(".agents", "skills")}
UNTESTED = ("gemini", "opencode")
CONFIG_DIR = os.path.join(HERE, "ab", "configs")


# -------------------------------------------------------------- A/B configs --
CONFIG_KEYS = ("name", "agent", "phase", "factor", "description", "main_model", "worker_model",
               "budget_mode", "allowed_tools", "append_system_prompt", "notes")


def load_config(path):
    """A deliberately small YAML reader for bench/ab/configs/*.yaml.

    It understands exactly what those files use: `key: scalar`, `key: null`,
    `key: |` literal blocks, and `key:` followed by `  - item` lists. Anything
    else raises, so a config that needs real YAML fails loudly instead of being
    silently half-read. Standard library only, per docs/CONVENTIONS.md.
    """
    if not os.path.isabs(path) and not os.path.exists(path):
        for guess in (os.path.join(CONFIG_DIR, path),
                      os.path.join(CONFIG_DIR, path + ".yaml")):
            if os.path.exists(guess):
                path = guess
                break
    with io.open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    cfg = collections.OrderedDict()
    key, block, block_indent, listing = None, None, None, None
    for raw in lines + [""]:
        line = raw.rstrip("\n")
        stripped = line.strip()
        indented = line[:1] in (" ", "\t")

        if block is not None:
            if not stripped or indented:
                block.append(line[block_indent:] if len(line) > block_indent else "")
                continue
            cfg[key] = " ".join(" ".join(block).split())
            block, key = None, None

        if listing is not None:
            if stripped.startswith("- "):
                listing.append(scalar(stripped[2:].strip()))
                continue
            cfg[key] = listing
            listing, key = None, None

        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("bench config line is not key: value: %r" % line)
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value in ("|", ">", ">-", "|-"):
            block, block_indent = [], 2
        elif value == "":
            listing = []
        else:
            cfg[key] = scalar(value)
            key = None
    if block is not None:
        cfg[key] = " ".join(" ".join(block).split())
    if listing is not None:
        cfg[key] = listing

    cfg.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    cfg.setdefault("agent", "claude")
    cfg.setdefault("phase", "core")
    cfg.setdefault("budget_mode", "standard")
    cfg.setdefault("main_model", None)
    cfg.setdefault("allowed_tools", None)
    cfg.setdefault("append_system_prompt", None)
    cfg["path"] = path
    return cfg


def scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text in ("null", "~", ""):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if re.match(r"^-?\d+$", text):
        return int(text)
    return text


def list_configs(directory=None):
    directory = directory or CONFIG_DIR
    if not os.path.isdir(directory):
        return []
    return [load_config(os.path.join(directory, n))
            for n in sorted(os.listdir(directory)) if n.endswith(".yaml")]


BUDGET_RE = re.compile(r"^(\s*budget_mode\s*:\s*)(\S+)", re.M)


def apply_budget_mode(workdir, mode):
    """Write the config's budget_mode into the run's own profile.yaml copy."""
    if not mode:
        return None
    path = os.path.join(workdir, "profile.yaml")
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    if BUDGET_RE.search(text):
        text = BUDGET_RE.sub(lambda m: m.group(1) + str(mode), text, count=1)
    else:
        text = text.rstrip("\n") + "\n\nbudget_mode: %s\n" % mode
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return mode


def quote(part):
    if part and all(c.isalnum() or c in "-_./:=" for c in part):
        return part
    return "'" + part.replace("'", "'\\''") + "'"


def shell(cmd):
    return " ".join(quote(str(p)) for p in cmd)


def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# ------------------------------------------------------------------ workdir --
def prepare_workdir(case, agent, evals_path, workdir=None, link=True):
    """profile.yaml plus the skill, in the folder this agent reads skills from."""
    if workdir:
        path = os.path.abspath(workdir)
        if not os.path.isdir(path):
            os.makedirs(path)
    else:
        path = tempfile.mkdtemp(prefix="vetflat-%s-%s-" % (agent, case["id"]))
    plan = []
    base = os.path.dirname(os.path.abspath(evals_path))
    for rel in case.get("files") or []:
        src = os.path.join(base, rel)
        dst = os.path.join(path, os.path.basename(rel))
        shutil.copyfile(src, dst)
        plan.append("copy %s -> %s" % (os.path.relpath(src, ROOT), os.path.basename(rel)))
    if agent in SKILL_HOME:
        home = os.path.join(path, SKILL_HOME[agent])
        if not os.path.isdir(home):
            os.makedirs(home)
        dst = os.path.join(home, "vet-flat")
        if os.path.lexists(dst):
            (shutil.rmtree if os.path.isdir(dst) and not os.path.islink(dst) else os.unlink)(dst)
        if link:
            os.symlink(SKILL_DIR, dst)
            plan.append("symlink skills/vet-flat -> %s/vet-flat" % SKILL_HOME[agent])
        else:
            shutil.copytree(SKILL_DIR, dst)
            plan.append("copy skills/vet-flat -> %s/vet-flat" % SKILL_HOME[agent])
    return path, plan


# ------------------------------------------------------------------ commands --
def build_command(agent, case, model, workdir, prompt=None, config=None):
    prompt = prompt or case["prompt"]
    config = config or {}
    if config.get("main_model") and not model:
        model = config["main_model"]
    if agent == "claude":
        tools = config.get("allowed_tools") or ["Bash(python3:*)", "Read", "Write"]
        cmd = ["claude", "-p", prompt]
        if config.get("append_system_prompt"):
            cmd += ["--append-system-prompt", config["append_system_prompt"]]
        cmd += ["--allowedTools"] + list(tools) + ["--output-format", "json"]
        if model:
            cmd += ["--model", model]
        return cmd
    if agent == "codex":
        cmd = ["codex", "exec",
               "--cd", workdir,
               "--sandbox", "workspace-write",
               "-c", "sandbox_workspace_write.network_access=true",
               "--skip-git-repo-check"]
        if model:
            cmd += ["--model", model]
        return cmd + [prompt]
    if agent == "gemini":
        cmd = ["gemini", "--prompt", prompt]
        if model:
            cmd += ["--model", model]
        return cmd
    if agent == "opencode":
        cmd = ["opencode", "run", prompt]
        if model:
            cmd += ["--model", model]
        return cmd
    return None


# ----------------------------------------------------------------- api mode --
def condense(payload, keep):
    return collections.OrderedDict((k, payload[k]) for k in keep if k in payload)


def fixture_text(case):
    """The pasted material a person would hand a chat box, from evals/truth/."""
    facts = case.get("expected_facts") or {}
    blocks = []

    epc_raw = (facts.get("epc") or {}).get("raw")
    if epc_raw and os.path.exists(os.path.join(ROOT, epc_raw)):
        with io.open(os.path.join(ROOT, epc_raw), encoding="utf-8") as fh:
            cert = json.load(fh)
        lines = ["ENERGY CERTIFICATE PAGE (pasted from find-energy-certificate.service.gov.uk)",
                 "Address: %s" % cert.get("address"),
                 "Certificate number: %s" % cert.get("certificate_number"),
                 "Property type: %s" % cert.get("property_type"),
                 "Total floor area: %s square metres" % cert.get("total_floor_area_m2"),
                 "Date of assessment: %s" % cert.get("date_of_assessment"),
                 "Date of certificate: %s" % cert.get("date_of_certificate"),
                 "Valid until: %s" % cert.get("valid_until"),
                 "Energy rating: %s with a score of %s" % (cert.get("energy_rating"),
                                                           cert.get("energy_score")),
                 "Type of assessment: %s" % cert.get("assessment_type"),
                 "Main heating: %s" % cert.get("main_heating"),
                 "Hot water: %s" % cert.get("hot_water"),
                 "Air permeability: %s" % cert.get("air_permeability"),
                 "Other certificates for this property: %s"
                 % (", ".join(cert.get("other_certificates") or []) or "none"),
                 "Source: %s" % cert.get("source_url")]
        for name, feat in (cert.get("features") or {}).items():
            lines.append("Feature - %s: %s" % (name, (feat or {}).get("description")))
        for h in cert.get("history") or []:
            lines.append("Earlier certificate %s: assessed %s, rating %s, %s square metres"
                         % (h.get("certificate_id"), h.get("date_of_assessment"),
                            h.get("energy_rating"), h.get("total_floor_area_m2")))
        blocks.append("\n".join(lines))

    crime_raw = (facts.get("crime") or {}).get("raw")
    if crime_raw and os.path.exists(os.path.join(ROOT, crime_raw)):
        with io.open(os.path.join(ROOT, crime_raw), encoding="utf-8") as fh:
            crime = json.load(fh)
        small = condense(crime, ["source_url", "retrieved_at", "months_fetched", "months_missing",
                                 "total", "per_month", "by_category", "predatory_subset",
                                 "top_anchors", "anchor_dispersion", "box", "method"])
        blocks.append("POLICE RECORDED CRIME, JSON from data.police.uk\n"
                      + json.dumps(small, ensure_ascii=False, indent=1))

    commute_raw = (facts.get("commute") or {}).get("raw")
    if commute_raw and os.path.exists(os.path.join(ROOT, commute_raw)):
        with io.open(os.path.join(ROOT, commute_raw), encoding="utf-8") as fh:
            journey = json.load(fh)
        small = condense(journey, ["source_url", "retrieved_at", "query", "fastest_plan",
                                   "fastest_min", "rail_only_min", "bus_only_min", "plans"])
        blocks.append("TfL JOURNEY PLANNER, JSON\n" + json.dumps(small, ensure_ascii=False)[:12000])

    red_raw = (facts.get("commute") or {}).get("redundancy_raw")
    if red_raw and os.path.exists(os.path.join(ROOT, red_raw)):
        with io.open(os.path.join(ROOT, red_raw), encoding="utf-8") as fh:
            red = json.load(fh)
        small = condense(red, ["source_url", "retrieved_at", "grade", "nearest_family",
                               "nearest_family_walk_m", "second_family_walk_m", "families",
                               "reason", "explanation"])
        blocks.append("TfL LINE REDUNDANCY, JSON\n" + json.dumps(small, ensure_ascii=False)[:8000])

    company_raw = (facts.get("company") or {}).get("raw")
    if company_raw and os.path.exists(os.path.join(ROOT, company_raw)):
        with io.open(os.path.join(ROOT, company_raw), encoding="utf-8") as fh:
            comp = json.load(fh)
        small = condense(comp, ["source_url", "retrieved_at", "total_reported_by_site", "count",
                                "dissolved_count", "results", "same_name_warning"])
        blocks.append("COMPANIES HOUSE SEARCH, JSON\n"
                      + json.dumps(small, ensure_ascii=False)[:8000])

    lr_raw = (facts.get("landregistry") or {}).get("raw")
    if lr_raw and os.path.exists(os.path.join(ROOT, lr_raw)):
        with io.open(os.path.join(ROOT, lr_raw), encoding="utf-8") as fh:
            lr = json.load(fh)
        small = condense(lr, ["source_url", "retrieved_at", "count", "new_build_count",
                              "earliest_new_build_year", "earliest_new_build_transaction",
                              "earliest_transaction", "not_found"])
        blocks.append("HM LAND REGISTRY PRICE PAID, JSON\n"
                      + json.dumps(small, ensure_ascii=False)[:6000])
    return "\n\n---\n\n".join(blocks)


def system_prompt():
    system = []
    for path, title in ((PROMPT_PACK, "SKILL INSTRUCTIONS"),
                        (INPUTS_MD, "WHEN YOU CANNOT GET SOMETHING"),
                        (ONBOARDING_MD, "ONBOARDING")):
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as fh:
                system.append("# %s\n\n%s" % (title, fh.read()))
    return system


def api_messages_conversation(case, prompt):
    """A conversation case: no report, no fixtures. Just the skill and the question."""
    system = system_prompt()
    system.append("You have no shell and no internet in this run. Answer the user directly, in "
                  "the language they used. Do not write a report and do not write JSON.")
    return "\n\n".join(system), prompt


def api_messages(case, profile_text, schema_text):
    system = system_prompt()
    system.append("You have no shell and no internet in this run. Everything you can have has "
                  "been pasted below. Write the report from it. Leave anything that is not there "
                  "null and list it in not_found. Answer with ONE JSON object and nothing else: "
                  "no prose before it, no code fence around it.")
    user = [case["prompt"],
            "",
            "profile.yaml:",
            profile_text,
            "",
            "The report must match this JSON Schema:",
            schema_text,
            "",
            "Material collected for you:",
            "",
            fixture_text(case)]
    return "\n\n".join(system), "\n".join(user)


def run_api(case, model, profile_path, timeout, prompt=None, conversation=False):
    import _fetch
    base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or not base:
        print("api mode needs OPENAI_BASE_URL and OPENAI_API_KEY in the environment. "
              "Set them and run again, or use --agent claude / codex for the shell agents.",
              file=sys.stderr)
        return None, None, "no OPENAI_API_KEY / OPENAI_BASE_URL"
    if not model:
        return None, None, "api mode needs --model"
    if conversation:
        system, user = api_messages_conversation(case, prompt or case["prompt"])
    else:
        with io.open(profile_path, encoding="utf-8") as fh:
            profile_text = fh.read()
        with io.open(grader.SCHEMA_PATH, encoding="utf-8") as fh:
            schema_text = fh.read()
        system, user = api_messages(case, profile_text, schema_text)
    payload = {"model": model, "temperature": 0,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    url = base + ("" if base.endswith("/chat/completions") else "/chat/completions")
    res = _fetch.post_json(url, payload, headers={"Authorization": "Bearer " + key},
                           cache_ttl=0, timeout=timeout, min_gap=0,
                           expect=lambda b: "choices" in b or "error" in b)
    if not res["ok"]:
        return None, None, "http %s: %s" % (res["status"], (res["body"] or "")[:300])
    try:
        body = json.loads(res["body"])
    except ValueError:
        return None, None, "the endpoint did not return JSON"
    if "error" in body and "choices" not in body:
        return None, None, "api error: %s" % json.dumps(body["error"])[:300]
    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return text, body.get("usage"), None


# ---------------------------------------------------------- report recovery --
def first_json_object(text):
    """The first balanced {...} in a blob, ignoring braces inside strings."""
    if not text:
        return None
    fence = text.find("```json")
    if fence >= 0:
        text = text[fence + 7:]
    start = text.find("{")
    while start >= 0:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    chunk = text[start:i + 1]
                    try:
                        return json.loads(chunk)
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def find_report(workdir, stdout):
    direct = os.path.join(workdir, "report.json")
    if os.path.exists(direct):
        try:
            with io.open(direct, encoding="utf-8") as fh:
                return json.load(fh), direct
        except ValueError:
            pass
    for base, _dirs, files in os.walk(workdir):
        if ".claude" in base or ".agents" in base:
            continue
        for name in files:
            if name == "report.json":
                path = os.path.join(base, name)
                try:
                    with io.open(path, encoding="utf-8") as fh:
                        return json.load(fh), path
                except ValueError:
                    continue
    obj = first_json_object(stdout)
    if obj is not None and "candidates" in obj:
        path = os.path.join(workdir, "report.from-stdout.json")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False, indent=1))
        return obj, path
    # Claude Code's --output-format json wraps the answer in .result
    wrapper = first_json_object(stdout)
    if isinstance(wrapper, dict) and isinstance(wrapper.get("result"), str):
        inner = first_json_object(wrapper["result"])
        if inner is not None and "candidates" in inner:
            path = os.path.join(workdir, "report.from-stdout.json")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(inner, ensure_ascii=False, indent=1))
            return inner, path
    return None, None


def answer_text(agent, stdout):
    """The agent's final message. Claude Code wraps it in .result; the rest print it."""
    if agent == "claude":
        obj = first_json_object(stdout)
        if isinstance(obj, dict) and isinstance(obj.get("result"), str):
            return obj["result"]
    return stdout or ""


USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
              "cache_creation_input_tokens")


def total_tokens(usage):
    """One comparable number per run: everything the run had to pay attention to."""
    if not usage:
        return None
    total = 0
    seen = False
    for key in USAGE_KEYS:
        value = usage.get(key)
        if isinstance(value, (int, float)):
            total += value
            seen = True
    return total if seen else None


def usage_from_stdout(agent, stdout):
    """Tokens and cost when the agent reports them; None when it does not."""
    obj = first_json_object(stdout) if agent == "claude" else None
    if isinstance(obj, dict):
        usage = obj.get("usage") or {}
        out = collections.OrderedDict()
        for key in USAGE_KEYS:
            if key in usage:
                out[key] = usage[key]
        for key in ("total_cost_usd", "duration_ms", "num_turns"):
            if key in obj:
                out[key] = obj[key]
        # modelUsage is per-model and is what tells A from B when subagents ran on a
        # different model from the main loop. Kept whole; it is small.
        for key in ("modelUsage", "model_usage"):
            if isinstance(obj.get(key), dict):
                out["modelUsage"] = obj[key]
                for per_model in obj[key].values():
                    if isinstance(per_model, dict):
                        for k in USAGE_KEYS:
                            if k in per_model:
                                out.setdefault(k, 0)
                                if k not in usage:
                                    out[k] += per_model[k]
                break
        total = total_tokens(out)
        if total is not None:
            out["total_tokens"] = total
        return out or None
    return None


def write_raw(stdout, config_name, case_label, run_index, when=None, results_root=None):
    """bench/results/<date>/raw/<config>-<case>-<run>.json, verbatim."""
    day = (when or datetime.datetime.utcnow()).strftime("%Y-%m-%d")
    folder = os.path.join(results_root or RESULTS, day, "raw")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, raw_name(config_name, case_label, run_index))
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(stdout or "")
    return path


def raw_name(config_name, case_label, run_index):
    def safe(text):
        return re.sub(r"[^A-Za-z0-9._#-]+", "-", str(text or "none"))
    return "%s-%s-%s.json" % (safe(config_name), safe(case_label), int(run_index))


def raw_exists(config_name, case_label, run_index, day=None, results_root=None):
    day = day or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    return os.path.exists(os.path.join(results_root or RESULTS, day, "raw",
                                       raw_name(config_name, case_label, run_index)))


# ------------------------------------------------------------- scorecard IO --
MD_HEADER = ("| run (UTC) | agent | model | case | facts | stable | fabrications | citations | "
             "unknown honesty | hard filters | questions | gates | schema | wall s | "
             "tokens / cost |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")


def append_scorecard(row, when=None):
    day = (when or datetime.datetime.utcnow()).strftime("%Y-%m-%d")
    folder = os.path.join(RESULTS, day)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    jpath = os.path.join(folder, "scorecard.json")
    rows = []
    if os.path.exists(jpath):
        try:
            with io.open(jpath, encoding="utf-8") as fh:
                rows = json.load(fh)
        except ValueError:
            rows = []
    rows.append(row)
    with io.open(jpath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")

    mpath = os.path.join(folder, "scorecard.md")
    new = not os.path.exists(mpath)
    with io.open(mpath, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# vet-flat benchmark, %s\n\n"
                     "Facts are graded, verdicts are not. The pass line is stable facts at or "
                     "above 95 percent, zero fabrications, citations at 100 percent.\n\n"
                     % day)
            fh.write(MD_HEADER)
        fh.write("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                 "\n" % (
                     row["run_at"], row["agent"], row.get("model") or "-", row["case"],
                     row.get("facts") or "-", row.get("stable_facts") or "-",
                     row.get("fabrications", "-"), row.get("citations") or "-",
                     row.get("unknown_honesty") or "-", row.get("hard_filters") or "-",
                     row.get("questions") or "-", row.get("gates") or "-",
                     "ok" if row.get("schema_valid") else "FAIL",
                     row.get("wall_time_s", "-"), row.get("cost_note") or "-"))
    return jpath, mpath


def make_row(agent, model, case, card, wall, usage, workdir, command, note=None, variant=None,
             config=None, run_index=None, raw_path=None):
    scores = (card or {}).get("scores") or {}
    counts = (card or {}).get("counts") or {}
    cost = None
    if usage:
        bits = []
        if usage.get("input_tokens") is not None:
            bits.append("in %s" % usage["input_tokens"])
        if usage.get("prompt_tokens") is not None:
            bits.append("in %s" % usage["prompt_tokens"])
        if usage.get("output_tokens") is not None:
            bits.append("out %s" % usage["output_tokens"])
        if usage.get("completion_tokens") is not None:
            bits.append("out %s" % usage["completion_tokens"])
        if usage.get("total_cost_usd") is not None:
            bits.append("$%.4f" % usage["total_cost_usd"])
        cost = ", ".join(bits) or None
    config = config or {}
    return collections.OrderedDict([
        ("run_at", now()), ("agent", agent), ("model", model),
        ("config", config.get("name")),
        ("config_phase", config.get("phase")),
        ("config_factor", config.get("factor")),
        ("budget_mode", config.get("budget_mode")),
        ("worker_model", config.get("worker_model")),
        ("run_index", run_index),
        ("case", case["id"] + ("#" + variant if variant else "")),
        ("gold_id", case.get("gold_id")),
        ("kind", case.get("kind", "report")),
        ("address", case.get("address")), ("borough", case.get("borough")),
        ("facts", "%s/%s" % (counts.get("correct"), counts.get("gradeable")) if counts else None),
        ("stable_facts", ("%.0f%%" % (scores["stable_fact_recall"] * 100))
         if scores.get("stable_fact_recall") is not None else None),
        ("fact_recall", scores.get("fact_recall")),
        ("stable_fact_recall", scores.get("stable_fact_recall")),
        ("fabrications", scores.get("fabrications")),
        ("citations", ("%.0f%%" % (scores["citations"] * 100))
         if scores.get("citations") is not None else None),
        ("unknown_honesty", ("%.0f%%" % (scores["unknown_honesty"] * 100))
         if scores.get("unknown_honesty") is not None else None),
        ("hard_filters", "%s/%s" % (counts.get("hard_filters_consistent"),
                                    counts.get("hard_filters_checked")) if counts else None),
        ("hard_filter_consistency", scores.get("hard_filter_consistency")),
        ("questions", "%s/%s" % (counts.get("killer_questions_grounded"),
                                 counts.get("killer_questions"))
         if counts and counts.get("killer_questions") is not None else None),
        ("killer_questions_from_bank", scores.get("killer_questions_from_bank")),
        ("gates", "%s/%s" % (counts.get("gates_covered"), counts.get("gates_expected"))
         if counts and counts.get("gates_expected") else None),
        ("gate_questions_present", scores.get("gate_questions_present")),
        ("schema_valid", (card or {}).get("schema", {}).get("valid")),
        ("meets_pass_line", (card or {}).get("meets_pass_line")),
        ("wall_time_s", round(wall, 1) if wall is not None else None),
        ("tokens", usage),
        ("total_tokens", total_tokens(usage)),
        ("total_cost_usd", (usage or {}).get("total_cost_usd")),
        ("cost_note", cost),
        ("raw", raw_path),
        ("workdir", workdir), ("command", command), ("note", note),
        ("summary", (card or {}).get("summary")),
        ("report_path", (card or {}).get("report")),
    ])


# --------------------------------------------------------------------- main --
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", required=True, choices=AGENTS)
    ap.add_argument("--case", help="an eval case id from evals/evals.json")
    ap.add_argument("--all-cases", action="store_true", help="every case, one after another")
    ap.add_argument("--model", help="the model name to pass to the agent")
    ap.add_argument("--variant", help="for a conversation case asked in more than one language, "
                                      "run only this variant (for example zh)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds, default 900")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the working-directory plan and the command; run nothing")
    ap.add_argument("--config", help="an A/B config from bench/ab/configs (a path, or the "
                                     "bare name). Applies append_system_prompt, allowed_tools, "
                                     "main_model and budget_mode, and labels the scorecard row")
    ap.add_argument("--cases", help="a cases file in the evals/evals.json shape; defaults to "
                                    "evals/evals.json. Use bench/private/cases_private.json "
                                    "for the A/B suite")
    ap.add_argument("--run-index", type=int, default=1,
                    help="which repeat of this config x case this is; names the raw file")
    ap.add_argument("--results", help="results root; default bench/results. The date folder "
                                      "is created inside it")
    ap.add_argument("--evals", default=EVALS_JSON)
    ap.add_argument("--workdir", help="use this directory instead of a fresh temp one")
    ap.add_argument("--copy-skill", action="store_true",
                    help="copy the skill into the workdir instead of symlinking it")
    ap.add_argument("--keep", action="store_true", help="do not delete the temp workdir")
    return ap


def load_cases(path, case_id, all_cases):
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    cases = doc.get("evals") or []
    if all_cases:
        return cases
    for case in cases:
        if case.get("id") == case_id:
            return [case]
    return []


def variants_of(case):
    """[(variant id or None, prompt)] - a conversation case may be asked twice."""
    vs = case.get("prompt_variants") or []
    if not vs:
        return [(None, case["prompt"])]
    return [(v.get("id"), v.get("prompt") or case["prompt"]) for v in vs]


def run_one(args, case, variant=None, prompt=None):
    agent = args.agent
    config = getattr(args, "config_data", None) or {}
    conversation = case.get("kind") == "conversation"
    prompt = prompt or case["prompt"]
    label = case["id"] + ("#" + variant if variant else "")
    workdir, plan = prepare_workdir(case, agent, args.evals, args.workdir,
                                    link=not args.copy_skill)
    mode = apply_budget_mode(workdir, config.get("budget_mode"))
    if mode:
        plan.append("set budget_mode: %s in the run's profile.yaml" % mode)
    command = build_command(agent, case, args.model, workdir, prompt, config)

    if args.dry_run:
        print("case:     %s  (%s)" % (label, case.get("address")
                                      or ("a conversation, no flat" if conversation
                                          else "no address")))
        print("agent:    %s%s" % (agent, "   [UNTESTED - flags not verified against the vendor "
                                          "documentation]" if agent in UNTESTED else ""))
        if config:
            print("config:   %s   [%s]  factor: %s"
                  % (config.get("name"), config.get("phase"), config.get("factor")))
            print("raw file: %s" % os.path.join(
                "bench", "results", datetime.datetime.utcnow().strftime("%Y-%m-%d"), "raw",
                raw_name(config.get("name"), label, args.run_index)))
        print("model:    %s" % (args.model or config.get("main_model")
                                or "(the agent's default)"))
        print("workdir:  %s" % workdir)
        for line in plan or ["(no case files: this case is a question, not a flat)"]:
            print("          %s" % line)
        print("prompt:   %s" % prompt)
        print("graded:   %s" % ("the plain-text answer, by the checks in expected_facts"
                                if conversation else "report.json, against expected_facts"))
        if agent == "api":
            print("command:  (no shell command) POST $OPENAI_BASE_URL/chat/completions")
            print("          system = dist/prompt-pack/INSTRUCTIONS.md + references/inputs.md"
                  + (" + references/onboarding.md" if os.path.exists(ONBOARDING_MD) else ""))
            if conversation:
                print("          user   = the case prompt, nothing else")
            else:
                print("          user   = the case prompt + profile.yaml + report-schema.json + "
                      "the pasted truth fixtures")
                print("          fixtures pasted: %d characters" % len(fixture_text(case)))
        else:
            print("command:  cd %s && %s" % (workdir, shell(command)))
        if not args.keep and not args.workdir:
            shutil.rmtree(workdir, ignore_errors=True)
        return 0, None

    started = time.time()
    stdout, stderr, usage, note = "", "", None, None
    if agent == "api":
        profile_path = os.path.join(workdir, "profile.yaml")
        stdout, usage, note = run_api(case, args.model, profile_path, args.timeout,
                                      prompt=prompt, conversation=conversation)
        if stdout is None:
            print("api run did not happen: %s" % note, file=sys.stderr)
            return 1, make_row(agent, args.model, case, None, time.time() - started, None,
                               workdir, "api", note, variant, config, args.run_index)
    else:
        try:
            proc = subprocess.Popen(command, cwd=workdir, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate(timeout=args.timeout)
            stdout = (out or b"").decode("utf-8", "replace")
            stderr = (err or b"").decode("utf-8", "replace")
            if proc.returncode != 0:
                note = "the agent exited %d: %s" % (proc.returncode, stderr.strip()[-300:])
        except subprocess.TimeoutExpired:
            proc.kill()
            note = "timed out after %d s" % args.timeout
        except OSError as exc:
            note = "could not start %r: %s" % (command[0], exc)
            print(note, file=sys.stderr)
            return 1, make_row(agent, args.model, case, None, time.time() - started, None,
                               workdir, shell(command), note, variant, config, args.run_index)
        usage = usage_from_stdout(agent, stdout)
    wall = time.time() - started
    command_text = "api" if agent == "api" else shell(command)
    raw_path = write_raw(stdout, config.get("name") or agent, label, args.run_index)

    if conversation:
        text = stdout if agent == "api" else answer_text(agent, stdout)
        path = os.path.join(workdir, "answer.txt")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text or "")
        if not (text or "").strip():
            note = (note + "; " if note else "") + "the agent produced no answer"
            row = make_row(agent, args.model, case, None, wall, usage, workdir,
                           command_text, note, variant, config, args.run_index, raw_path)
            append_scorecard(row)
            print(note, file=sys.stderr)
            return 1, row
        card = grader.grade_conversation(text, case, variant)
        card["report"] = path
    else:
        report, path = find_report(workdir, stdout)
        if report is None:
            note = (note + "; " if note else "") + ("no report.json and no JSON object in the "
                                                    "output")
            row = make_row(agent, args.model, case, None, wall, usage, workdir,
                           command_text, note, variant, config, args.run_index, raw_path)
            append_scorecard(row)
            print(note, file=sys.stderr)
            return 1, row
        profile_path = grader.case_profile_path(args.evals, case)
        card = grader.grade(report, case, profile_path)
        card["report"] = path

    with io.open(os.path.join(workdir, "scorecard.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(card, ensure_ascii=False, indent=1) + "\n")
    row = make_row(agent, args.model, case, card, wall, usage, workdir, command_text, note,
                   variant, config, args.run_index, raw_path)
    append_scorecard(row)
    print(card["summary"])
    return 0, row


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "results", None):
        global RESULTS
        RESULTS = os.path.abspath(args.results)
    if getattr(args, "cases", None):
        args.evals = args.cases
    args.config_data = load_config(args.config) if getattr(args, "config", None) else None
    if args.config_data and args.agent != "claude":
        if args.config_data.get("append_system_prompt"):
            print("usage error: only the claude agent takes --append-system-prompt, so this "
                  "config's appendix would be silently dropped. For a codex config use "
                  "bench/ab/run_codex.py, which delivers the appendix as AGENTS.md.",
                  file=sys.stderr)
            return 2
    if not args.case and not args.all_cases:
        print("usage error: give --case <id> or --all-cases", file=sys.stderr)
        return 2
    cases = load_cases(args.evals, args.case, args.all_cases)
    if not cases:
        print("usage error: no case %r in %s" % (args.case, args.evals), file=sys.stderr)
        return 2
    worst = 0
    first = True
    for case in cases:
        for variant, prompt in variants_of(case):
            if args.variant and variant and variant != args.variant:
                continue
            if not first and args.dry_run:
                print()
            first = False
            code, _row = run_one(args, case, variant, prompt)
            worst = max(worst, code)
    return worst


if __name__ == "__main__":
    sys.exit(main())
