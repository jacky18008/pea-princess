#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One launcher for every bench runner: retries, captured tails, a provider_error result.

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
``run()`` is the only place in bench/ that starts an agent. It

  * closes stdin (``stdin=subprocess.DEVNULL``) for every launch, always. ``claude -p``
    reads anything piped on stdin as part of the prompt, and a runner started from a
    shell heredoc hands that heredoc to every child it spawns (2026-09-05: four journey
    runs and ten sweep rows went out that way);
  * captures stdout and stderr and keeps the last ``TAIL_CHARS`` of each;
  * retries a launch that failed the way a busy provider fails - a non-zero exit, an
    empty stdout, or provider language on stderr - with a growing pause;
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
import json
import os
import re
import subprocess
import time
import uuid

# Growing pauses, in seconds, before attempt 2 and attempt 3. A usage window that has
# just closed does not reopen in ten seconds; ten minutes is the last try worth making
# inside one batch.
MAX_ATTEMPTS = 3
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
           "exit_code session_id")


class LaunchResult(collections.namedtuple("LaunchResult", _FIELDS)):
    """What one launch produced. ``text`` is the model's answer (claude: the ``.result``
    field; codex: the raw stdout, which the caller may replace with its last-message
    file). ``provider_error`` says the run never reached the model."""

    __slots__ = ()

    def __new__(cls, text="", usage=None, note=None, seconds=0.0, attempts=1,
                provider_error=False, stdout_tail="", stderr_tail="", exit_code=None,
                session_id=None):
        return super(LaunchResult, cls).__new__(
            cls, text, usage, note, seconds, attempts, bool(provider_error),
            stdout_tail, stderr_tail, exit_code, session_id)

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
    failed = exit_code != 0 or not (stdout or "").strip()
    flagged = claude_error(stdout) if failed else None
    if flagged and provider_language(flagged):
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
            proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if proc is not None:
                proc.kill()
                proc.communicate()
            # The caller's ceiling, not the provider refusing. Not retried, not a
            # provider error: a runner shows a timeout to its reader as a timeout.
            return LaunchResult(text="", usage=None,
                                note="timed out after %d s" % timeout,
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=False, stdout_tail="", stderr_tail="",
                                exit_code=None, session_id=session_used)
        except OSError as exc:
            return LaunchResult(text="", usage=None,
                                note="could not start %r: %s" % (cmd[0], exc),
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=False, stdout_tail="", stderr_tail="",
                                exit_code=None, session_id=session_used)
        stdout = (out or b"").decode("utf-8", "replace")
        stderr = (err or b"").decode("utf-8", "replace")
        exit_code = proc.returncode
        retry, why = looks_like_provider_failure(exit_code, stdout, stderr)
        failed = exit_code != 0 or not stdout.strip()
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
            return LaunchResult(text=text, usage=usage, note=note,
                                seconds=round(time.time() - started, 2), attempts=attempt,
                                provider_error=True, stdout_tail=stdout[-TAIL_CHARS:],
                                stderr_tail=stderr[-TAIL_CHARS:], exit_code=exit_code, session_id=session_used)
        pause = waits[min(attempt - 1, len(waits) - 1)] if waits else 0
        echo("  %s%s; retry %d of %d in %d s"
             % (("%s: " % label) if label else "", why, attempt, max(1, attempts) - 1,
                pause))
        sleep(pause)

    text, usage = answer(stdout, family)
    return LaunchResult(text=text, usage=usage, note=note,
                        seconds=round(time.time() - started, 2), attempts=attempt,
                        provider_error=False, stdout_tail=stdout[-TAIL_CHARS:],
                        stderr_tail=stderr[-TAIL_CHARS:], exit_code=exit_code, session_id=session_used)


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
    recursive, last-count fallback. Cached input and reasoning output are breakdowns
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
            for key in TOKEN_KEYS:
                if type(holder.get(key)) is int:
                    totals[key] = holder[key]
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict):
                snapshot = collections.OrderedDict(
                    (key, usage[key]) for key in TOKEN_KEYS if type(usage.get(key)) is int)
                if snapshot:
                    completed = snapshot
    if completed is not None:
        totals = completed
    if not totals:
        return None
    if "total_tokens" not in totals:
        input_tokens = totals.get("input_tokens", totals.get("prompt_tokens"))
        output_tokens = totals.get("output_tokens", totals.get("completion_tokens"))
        if input_tokens is not None or output_tokens is not None:
            totals["total_tokens"] = (input_tokens or 0) + (output_tokens or 0)
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
