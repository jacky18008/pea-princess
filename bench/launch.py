#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared benchmark launcher: owned processes, attempt evidence, provider status.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

WHY THIS EXISTS
===============
Two pilots lost rows to the provider, not to the model, and the harnesses recorded the
loss as if the model had answered nothing:

  bench/results/docs-ablation/docs-2026-09-07  ten of twenty-six rows carry
        "the agent exited 1: ; no answers array in the reply" and were graded 0 facts.
        They are consecutive in time and the same arm succeeded before and after them.
  bench/results/personas-2026-09-06            P3-baseline-s1 carries
        "turn 2 agent: exited 1: " after 365 s and was written down as a timeout.

Neither runner kept the process's stdout or stderr, so nothing in the results says
whether that was a usage limit, an outage, or a bad flag. A zero from a provider failure
poisons every mean it lands in, and it cannot be told from a zero the model earned.

WHAT THIS DOES
==============
``run()`` is the common launcher used by the multi-actor runners. It

  * closes stdin (``stdin=subprocess.DEVNULL``) for every launch, always. ``claude -p``
    reads anything piped on stdin as part of the prompt, and a runner started from a
    shell heredoc hands that heredoc to every child it spawns (2026-09-05: four journey
    runs and ten sweep rows went out that way);
  * captures stdout and stderr and keeps the last ``TAIL_CHARS`` of each;
  * makes one attempt by default; an explicit retry budget retains all attempt usage,
    including failures, and leaves the aggregate unknown when telemetry is missing;
  * after the last attempt returns ``provider_error=True`` with the tails and the exit
    code, so the row can be diagnosed months later instead of being read as a zero;
  * parses token usage for both CLIs: ``claude --output-format json`` and the ``codex
    exec --json`` event stream. Both parsers live here and nowhere else.

WHAT IS NOT A PROVIDER ERROR
============================
A hard timeout is the caller's ceiling, not the provider refusing: it ends the loop with
``provider_error=False`` and the note it always had. A command that cannot be started at
all (no such binary) is a configuration error, also not a provider error. Both are kept
apart because a runner shows them to the reader differently.

USAGE
  import launch
  res = launch.run(cmd, workdir, timeout, "claude")
  if res.provider_error:
      row["outcome"] = "provider_error"      # no grade, out of every mean
  else:
      grade(res.text)
"""
from __future__ import unicode_literals

import collections
import atexit
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid

# Growing pauses for callers that explicitly opt into retries.
MAX_ATTEMPTS = 1  # A new physical attempt must be an explicit caller decision.
RETRY_WAITS = (60, 180, 600)
TAIL_CHARS = 600          # of each stream, kept on the result
SCAN_CHARS = 2000         # of stdout, scanned for provider language when a run failed

# The narrow pattern: what a provider says when it is refusing to serve right now.
TRANSIENT = re.compile(r"at capacity|rate.?limit|too many requests|\b429\b|overloaded|"
                       r"temporarily unavailable|try again later|server error|\b5\d\d\b|"
                       r"ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|can'?t reach the API|"
                       r"API Error", re.I)
# The wider one: what a CLI says on stderr when the account, not the service, is out.
# "rate" carries word boundaries on purpose - "generate" and "accurate" are not outages.
# Provider language. "rate" alone is not in it: a persona discussing a nightly rate had
# every turn's stderr read as a refusal and retried twice (2026-09-07).
PROVIDER = re.compile(r"usage limit|limit reached|try again later|quota|rate[ -]?limit|"
                      r"ratelimit|overloaded|too many requests|\b429\b|at capacity", re.I)

# claude --output-format json
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
              "cache_creation_input_tokens")
# codex exec --json, across the versions that have named these differently
TOKEN_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens",
              "cache_write_input_tokens", "reasoning_output_tokens", "total_tokens", "prompt_tokens",
              "completion_tokens", "cache_read_input_tokens")

_FIELDS = ("text usage note seconds attempts provider_error stdout_tail stderr_tail "
           "exit_code session_id attempt_records")


class LaunchResult(collections.namedtuple("LaunchResult", _FIELDS)):
    """What one launch produced. ``text`` is the model's answer (claude: the ``.result``
    field; codex: the raw stdout, which the caller may replace with its last-message
    file). ``provider_error`` says the CLI did not complete successfully; it does not
    prove that the provider performed no work or charged no tokens."""

    __slots__ = ()

    def __new__(cls, text="", usage=None, note=None, seconds=0.0, attempts=1,
                provider_error=False, stdout_tail="", stderr_tail="", exit_code=None,
                session_id=None, attempt_records=None):
        return super(LaunchResult, cls).__new__(
            cls, text, usage, note, seconds, attempts, bool(provider_error),
            stdout_tail, stderr_tail, exit_code, session_id, attempt_records)

    def tail_note(self, prefix=""):
        """The note with the captured tails appended, for a row someone has to diagnose.

        Empty tails are said so out loud: "stderr tail: (empty)" is the finding in the
        docs pilot - the CLI exited 1 and said nothing at all."""
        note = (prefix + (self.note or "")) if prefix else (self.note or "")
        if not self.provider_error:
            return note or None
        parts = [note or "the provider refused the launch"]
        parts.append("attempts %d" % self.attempts)
        if self.exit_code is not None:
            parts.append("exit %s" % self.exit_code)
        parts.append("stdout tail: %s" % (self.stdout_tail.strip() or "(empty)"))
        parts.append("stderr tail: %s" % (self.stderr_tail.strip() or "(empty)"))
        return "; ".join(parts)


_ACTIVE_PROCESSES = set()
_PROCESS_LOCK = threading.RLock()
_SIGNAL_HANDLERS = {}


class ProcessCleanupError(RuntimeError):
    """Cancellation could not establish that the owned processes were stopped."""


def _signal_group(group, sig):
    try:
        os.killpg(group, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        return "permission denied for process group %s" % group


def _owned_groups(processes):
    """Snapshot descendant groups before a nested wrapper can exit/reparent them.

    ps reads PID/PPID/PGID only, never command arguments or environment values.
    An unavailable process table leaves the owned initial groups as a fallback.
    """
    roots = {process.pid for process in processes}
    groups = set(roots)
    try:
        table = subprocess.run(["ps", "-ax", "-o", "pid=", "-o", "ppid=", "-o", "pgid="],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, timeout=2, check=True)
        rows = [tuple(map(int, line.split())) for line in table.stdout.splitlines() if line.strip()]
        descendants = set(roots)
        while True:
            extra = {pid for pid, parent, _group in rows if parent in descendants} - descendants
            if not extra:
                break
            descendants.update(extra)
        groups.update(group for pid, _parent, group in rows if pid in descendants)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass  # The initial sessions still have their process-group cleanup.
    return {group for group in groups if group > 1 and group != os.getpgrp()}


def _stop_processes(processes, grace):
    groups = _owned_groups(processes)
    errors = []
    for group in groups:
        error = _signal_group(group, signal.SIGTERM)
        if error:
            errors.append(error)
    deadline = time.monotonic() + grace
    for process in processes:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    # Kill captured nested sessions even if their wrapper already exited.
    for group in groups:
        error = _signal_group(group, signal.SIGKILL)
        if error:
            errors.append(error)
    for process in processes:
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            errors.append("process %s still running after cancellation" % process.pid)
    with _PROCESS_LOCK:
        _ACTIVE_PROCESSES.difference_update(processes)
    if errors:
        raise ProcessCleanupError("Process cleanup incomplete: " + "; ".join(sorted(set(errors))))


def stop_process(process, grace=0.5):
    """Stop owned descendants, including nested runners and output-pipe holders.

    This is lifecycle cleanup, not an OS sandbox against code deliberately
    daemonizing/reparenting before cancellation. The process snapshot is bounded.
    """
    _stop_processes([process], grace)


def _cleanup_signal(signum, frame):
    with _PROCESS_LOCK:
        active = list(_ACTIVE_PROCESSES)
    if active:
        _stop_processes(active, grace=0.1)
    previous = _SIGNAL_HANDLERS.get(signum)
    if callable(previous):
        previous(signum, frame)
    raise SystemExit(128 + signum)


def start_process(command, **kwargs):
    """Start an owned session; nested benchmark runners forward cancellation.

    The first launch in a runner's main thread installs signal cleanup. Executor
    threads share that registry, so the outer sweep can stop their CLI sessions.
    """
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            if signal.getsignal(sig) is not _cleanup_signal:
                _SIGNAL_HANDLERS[sig] = signal.getsignal(sig)
                signal.signal(sig, _cleanup_signal)
    kwargs["start_new_session"] = True
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    with _PROCESS_LOCK:
        process = subprocess.Popen(command, **kwargs)
        _ACTIVE_PROCESSES.add(process)
    return process


def finish_process(process):
    """Reap a finished CLI and remove any remaining processes in its session."""
    with _PROCESS_LOCK:
        active = process in _ACTIVE_PROCESSES
    if active:
        stop_process(process, grace=0)


def _cleanup_exit():
    # A normally exiting nested wrapper must not reparent registered child sessions.
    with _PROCESS_LOCK:
        active = list(_ACTIVE_PROCESSES)
    if active:
        try:
            _stop_processes(active, grace=0.1)
        except ProcessCleanupError as error:
            print(str(error), file=sys.stderr)


atexit.register(_cleanup_exit)


def attempt_usage(records):
    """All-attempt numeric totals, or unknown when any attempt lacks telemetry.

    Raw per-attempt usage stays in LaunchResult.attempt_records even when a total
    cannot be established. An omitted field is never filled with zero.
    """
    usages = [r["usage"] for r in records]
    if not usages or any(not isinstance(u, dict) or u.get("usage_invalid_reason") or any(
            type(u.get(k)) not in (int, float) or not math.isfinite(u[k]) or u[k] < 0
            for k in ("input_tokens", "output_tokens")) for u in usages):
        return None
    for usage in usages:
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
               for key, value in usage.items() if key in TOKEN_KEYS + USAGE_KEYS):
            return None
        if usage.get("cached_input_tokens", 0) > usage["input_tokens"]:
            return None
    if len(records) == 1:
        return usages[0]
    keys = set.intersection(*(set(u) for u in usages))
    return {key: sum(u[key] for u in usages) for key in sorted(keys)
            if all(type(u[key]) in (int, float) and math.isfinite(u[key]) for u in usages)}


def claude_tool_flags(rules):
    """Separate available built-ins from their auto-approval permission rules.

    --allowedTools alone does not remove other tools. An empty rule list therefore
    needs --tools "" as well. No benchmark actor inherits connectors or hooks.
    These flags require the documented Claude Code 2.1 CLI interface.
    """
    if isinstance(rules, str):
        rules = [rule.strip() for rule in rules.split(",") if rule.strip()]
    rules = list(rules)
    names = sorted({rule.split("(", 1)[0] for rule in rules})
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in names):
        raise ValueError("benchmark tool rules must name built-in tools")
    flags = ["--tools", ",".join(names), "--allowedTools", ",".join(rules),
             "--setting-sources", "", "--settings", '{"disableAllHooks":true}',
             "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    if not rules:
        flags += ["--disable-slash-commands"]
    return flags


def transient_error(text):
    """True when the failure text names a passing provider condition."""
    return bool(TRANSIENT.search(text or ""))


def provider_language(text):
    """True when the text is a provider saying no: busy, out of quota, over the limit."""
    return bool(TRANSIENT.search(text or "") or PROVIDER.search(text or ""))


def claude_envelope(stdout):
    """The --output-format json envelope as a dict, or None."""
    try:
        start = stdout.index("{")
    except (ValueError, AttributeError):
        return None
    depth, in_string, escape = 0, False, False
    for i in range(start, len(stdout)):
        ch = stdout[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(stdout[start:i + 1])
                except ValueError:
                    return None
                return obj if isinstance(obj, dict) else None
    return None


def claude_error(stdout):
    """The message Claude Code put in .result when it flagged is_error, else None.
    "API Error: Can't reach the API server (ENOTFOUND)" arrived this way on 2026-09-07,
    exit 1, with nothing on stderr - and the note showed the tail of the envelope."""
    obj = claude_envelope(stdout or "")
    if isinstance(obj, dict) and obj.get("is_error"):
        return str(obj.get("result") or obj.get("error") or "an error the CLI did not name")[:300]
    return None


def looks_like_provider_failure(exit_code, stdout, stderr):
    """(retry, why). The three shapes a provider failure took in the two pilots.

    stdout is only scanned when the run already failed: a successful reply that happens
    to discuss a rent "rate" must never be thrown away and paid for twice."""
    flagged = claude_error(stdout)
    failed = exit_code != 0 or not (stdout or "").strip() or flagged is not None
    if flagged:
        return True, "the CLI reported: %s" % flagged[:120]
    # stderr too is only read once the run has failed: codex writes its banner and its
    # progress there, and a successful reply about a "rate limit" clause in a tenancy is
    # still a successful reply.
    if failed and provider_language(stderr):
        return True, "the provider answered on stderr"
    if failed and provider_language((stdout or "")[-SCAN_CHARS:]):
        return True, "the provider answered on stdout"
    if exit_code != 0:
        return True, "the CLI exited %s" % exit_code
    if not (stdout or "").strip():
        return True, "the CLI exited 0 with no output"
    return False, None


def vetflat_cache_dir():
    """Where the skill's fetchers keep bodies: $VETFLAT_CACHE, else ~/.cache/vet-flat."""
    return os.environ.get("VETFLAT_CACHE") or os.path.join(os.path.expanduser("~"), ".cache",
                                                           "vet-flat")


def codex_cache_flags():
    """Extra `codex exec` flags that open the fetch cache to a workspace-write sandbox.

    Codex's workspace-write sandbox denies writes under the home directory, and every
    fetcher in the skill writes the body it downloads straight into ~/.cache/vet-flat, so
    a Codex run inside the sandbox failed every cache miss with "curl error 56" and only
    cache hits survived (found 2026-09-07; it confounded every Codex row before it: a
    warm cache made a run look able to fetch). The skill now falls back to a writable
    cache on its own, but a bench run should share the one cache with the Claude runs,
    so the sandbox gets that directory as an extra writable root.
    """
    cache = vetflat_cache_dir()
    try:
        os.makedirs(cache, exist_ok=True)
    except OSError:
        pass
    return ["-c", "sandbox_workspace_write.writable_roots=[%s]" % json.dumps(cache)]



def session_id_in(cmd):
    """The value after --session-id in a command list, or None."""
    try:
        return cmd[cmd.index("--session-id") + 1]
    except (ValueError, IndexError):
        return None

def run(cmd, cwd, timeout, family, attempts=MAX_ATTEMPTS, waits=RETRY_WAITS,
        label=None, sleep=None, echo=None):
    """Run one agent command and return a LaunchResult.

    ``family`` is "claude" or "codex" and decides how the tokens are read. ``attempts``
    and ``waits`` are the retry budget; ``waits[i]`` is the pause before attempt i+2 and
    the last wait is reused if the budget is longer than the list. ``label``, ``sleep``
    and ``echo`` exist for the callers and the tests: the runner passes a row label so
    the retry line names it, and a test passes its own clock so it does not wait.
    """
    sleep = sleep or time.sleep
    echo = echo if echo is not None else print
    started = time.time()
    attempt, stdout, stderr, exit_code, note = 0, "", "", None, None
    cmd = list(cmd)
    session_used = session_id_in(cmd)
    records = []
    while True:
        attempt += 1
        if attempt > 1 and session_used:
            # A retry must not reuse a Claude session id: the first attempt registered it
            # even when it failed, and the second dies with "Session ID ... is already in
            # use" (seven persona sessions, 2026-09-07). The caller reads the id it must
            # resume from the result.
            session_used = str(uuid.uuid4())
            cmd[cmd.index("--session-id") + 1] = session_used
        proc = None
        try:
            # stdin is closed on purpose, for every actor. `claude -p` treats anything
            # piped on stdin as part of the prompt, and a runner started from a shell
            # heredoc hands that heredoc to every child (it happened on 2026-09-05).
            proc = start_process(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if proc is not None:
                stop_process(proc)
                out, err = proc.communicate()
            else:
                out, err = b"", b""
            stdout = (out or b"").decode("utf-8", "replace")
            stderr = (err or b"").decode("utf-8", "replace")
            records.append({"attempt": attempt, "usage": answer(stdout, family)[1],
                            "exit_code": proc.returncode if proc else None, "timeout": True,
                            "stdout_tail": stdout[-TAIL_CHARS:], "stderr_tail": stderr[-TAIL_CHARS:]})
            # The caller's ceiling, not the provider refusing. Not retried, not a
            # provider error: a runner shows a timeout to its reader as a timeout.
            return LaunchResult(text="", usage=attempt_usage(records),
                                note="timed out after %d s" % timeout,
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=False, stdout_tail=stdout[-TAIL_CHARS:], stderr_tail=stderr[-TAIL_CHARS:],
                                exit_code=None, session_id=session_used, attempt_records=records)
        except OSError as exc:
            records.append({"attempt": attempt, "usage": None, "exit_code": None,
                            "start_error": str(exc), "timeout": False})
            return LaunchResult(text="", usage=None,
                                note="could not start %r: %s" % (cmd[0], exc),
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=False, stdout_tail="", stderr_tail="",
                                exit_code=None, session_id=session_used, attempt_records=records)
        except BaseException:
            if proc is not None:
                stop_process(proc)
            raise
        finally:
            if proc is not None and proc.poll() is not None:
                finish_process(proc)
        stdout = (out or b"").decode("utf-8", "replace")
        stderr = (err or b"").decode("utf-8", "replace")
        exit_code = proc.returncode
        records.append({"attempt": attempt, "usage": answer(stdout, family)[1],
                        "exit_code": exit_code, "timeout": False, "session_id": session_used,
                        "stdout_tail": stdout[-TAIL_CHARS:], "stderr_tail": stderr[-TAIL_CHARS:]})
        retry, why = looks_like_provider_failure(exit_code, stdout, stderr)
        failed = exit_code != 0 or not stdout.strip() or claude_error(stdout) is not None
        if not retry:
            # A run that answered is kept as it is, whatever stderr grumbled: paying twice
            # for a run that worked is the worse mistake. The grumble goes in the note.
            note = ("the provider warned on stderr: %s" % stderr.strip()[-300:]
                    if provider_language(stderr) else None)
            break
        if attempt >= max(1, attempts):
            if not failed:
                # The provider grumbled on stderr but the reply arrived. Keep the answer:
                # paying twice for a run that worked is the worse mistake.
                note = "the provider warned on stderr: %s" % stderr.strip()[-300:]
                break
            flagged = claude_error(stdout) if family == "claude" else None
            note = ("exited %d: %s" % (exit_code, flagged or stderr.strip()[-300:])) if exit_code \
                else "exited 0 with no output"
            # Whatever did come back is kept beside the tails. It is not graded - the
            # run never completed - but a reader looking at this row months later
            # should not have to guess what the CLI managed to say.
            text, usage = answer(stdout, family)
            return LaunchResult(text=text, usage=attempt_usage(records), note=note,
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=True, stdout_tail=stdout[-TAIL_CHARS:],
                                stderr_tail=stderr[-TAIL_CHARS:], exit_code=exit_code, session_id=session_used,
                                attempt_records=records)
        pause = waits[min(attempt - 1, len(waits) - 1)] if waits else 0
        echo("  %s%s; retry %d of %d in %d s"
             % (("%s: " % label) if label else "", why, attempt, max(1, attempts) - 1,
                pause))
        sleep(pause)

    text, usage = answer(stdout, family)
    if len(records) > 1 and attempt_usage(records) is None:
        note = (note + "; " if note else "") + "all-attempt usage unknown; inspect attempt_records"
    return LaunchResult(text=text, usage=attempt_usage(records), note=note,
                        seconds=round(time.time() - started, 2), attempts=attempt,
                        provider_error=False, stdout_tail=stdout[-TAIL_CHARS:],
                        stderr_tail=stderr[-TAIL_CHARS:], exit_code=exit_code, session_id=session_used,
                        attempt_records=records)


# ------------------------------------------------------------ reading the reply --
def answer(stdout, family):
    """(text, usage) for either CLI. Unknown families are handed back their raw stdout."""
    if family == "claude":
        return claude_answer(stdout)
    if family == "codex":
        return stdout, usage_from_events(stdout)
    return stdout, None


def claude_usage(obj):
    """Tokens and cost from a --output-format json envelope; None when absent."""
    if not isinstance(obj, dict):
        return None
    usage = obj.get("usage") or {}
    out = collections.OrderedDict()
    for key in USAGE_KEYS:
        if key in usage:
            out[key] = usage[key]
    for key in ("total_cost_usd", "duration_ms", "num_turns"):
        if key in obj:
            out[key] = obj[key]
    total = sum(v for v in (out.get(k) for k in USAGE_KEYS) if isinstance(v, (int, float)))
    if total:
        out["total_tokens"] = total
    return out or None


def claude_answer(stdout):
    """(final message, usage). Claude Code wraps the message in .result with
    --output-format json and puts the token counts beside it."""
    try:
        start = stdout.index("{")
    except (ValueError, AttributeError):
        return stdout or "", None
    depth, in_string, escape = 0, False, False
    for i in range(start, len(stdout)):
        ch = stdout[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(stdout[start:i + 1])
                except ValueError:
                    return stdout, None
                if isinstance(obj, dict) and isinstance(obj.get("result"), str):
                    return obj["result"], claude_usage(obj)
                return stdout, claude_usage(obj)
    return stdout, None


def usage_from_events(stdout):
    """Read the last terminal usage snapshot from a codex --json event stream.

    Codex emits cumulative thread totals in ``turn.completed.usage``. Prefer that
    complete snapshot over nested records; older streams without it retain the
    recursive, last-holder fallback without merging partial snapshots. Cached input and reasoning output are breakdowns
    of input and output respectively, never additional tokens.
    """
    totals = collections.OrderedDict()
    completed = None
    shapes = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for holder in walk_usage(event):
            keys = tuple(sorted(k for k in holder if type(holder[k]) is int))
            if keys and keys not in shapes:
                shapes.append(keys)
            totals = collections.OrderedDict((key, holder[key]) for key in TOKEN_KEYS if key in holder)
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict):
                snapshot = collections.OrderedDict(
                    (key, usage[key]) for key in TOKEN_KEYS if key in usage)
                if snapshot:
                    completed = snapshot
    if completed is not None:
        totals = completed
    if not totals:
        return None
    for canonical, alias in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
        if canonical not in totals and alias in totals:
            totals[canonical] = totals[alias]
        elif canonical in totals and alias in totals and totals[canonical] != totals[alias]:
            totals["usage_invalid_reason"] = "conflicting token aliases"
    input_tokens, output_tokens = totals.get("input_tokens"), totals.get("output_tokens")
    if type(input_tokens) is int and type(output_tokens) is int:
        expected = input_tokens + output_tokens
        if "total_tokens" in totals and totals["total_tokens"] != expected:
            totals["usage_invalid_reason"] = "total differs from input plus output"
        else:
            totals["total_tokens"] = expected
    totals["usage_shapes_seen"] = ["+".join(s) for s in shapes]
    return totals


def walk_usage(node):
    """Every dict carrying token counters, once per occurrence in the JSON tree."""
    out = []
    if isinstance(node, dict):
        if any(k in node for k in TOKEN_KEYS):
            out.append(node)
        for value in node.values():
            if isinstance(value, (dict, list)):
                out.extend(walk_usage(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(walk_usage(item))
    return out
