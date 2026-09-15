#!/usr/bin/env python3
"""One-shot Grok Build CLI probe; local inspect, no source fetching or retry.

`audit` reads an existing streaming-json trace without starting a model.
`run` starts exactly one Grok CLI process in an isolated project/home supplied
by the caller. Raw model output and the frozen prompt stay owner-only locally.
The inspect/configuration report identifies the active installed skill, but
cannot prove source truth, sandbox isolation, or answer quality.

Examples:
  python3 tools/grok_elastic_probe.py audit --stream private/actor.ndjson
  python3 tools/grok_elastic_probe.py run --project /private/tmp/new-project \
      --grok-home /private/tmp/new-grok-home --prompt-file actor.txt \
      --skill-file /private/tmp/new-project/.grok/skills/pea-princess/SKILL.md \
      --out /private/tmp/new-probe-receipt --always-approve
"""

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid


FIELDS = ("input_tokens", "cache_read_input_tokens",
          "cache_creation_input_tokens", "output_tokens", "reasoning_tokens")
STOP_GRACE_SECONDS = 20


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as target:
        json.dump(value, target, ensure_ascii=False, indent=2, sort_keys=True)
        target.write("\n")


def positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class StreamLedger:
    """Incremental observer of ACP-derived streaming-json lines."""

    def __init__(self, soft_turns=14):
        self.soft_turns = soft_turns
        self.event_counts = collections.Counter()
        self.tool_counts = collections.Counter()
        self.usage_totals = {field: 0 for field in FIELDS}
        self.usage_missing = set()
        self.usage_events = 0
        self.soft_snapshot = None
        self.end = None
        self.malformed_lines = 0
        self.current_text = []
        self.last_response_text = ""

    def feed(self, line):
        try:
            event = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            self.malformed_lines += 1
            return
        if not isinstance(event, dict):
            self.malformed_lines += 1
            return
        kind = event.get("type")
        self.event_counts[str(kind)] += 1
        if kind == "text" and isinstance(event.get("data"), str):
            self.current_text.append(event["data"])
        elif kind == "tool_call":
            self.tool_counts[str(event.get("toolName") or "unknown")] += 1
        elif kind == "usage":
            self.usage_events += 1
            item = event.get("usage")
            item = item if isinstance(item, dict) else {}
            for field in FIELDS:
                value = item.get(field)
                if positive_int(value):
                    self.usage_totals[field] += value
                else:
                    self.usage_missing.add(field)
            self.last_response_text = "".join(self.current_text)
            self.current_text = []
            if self.usage_events == self.soft_turns:
                self.soft_snapshot = self.snapshot()
        elif kind == "end":
            self.end = event

    def snapshot(self):
        totals = {field: (None if field in self.usage_missing
                          else self.usage_totals[field]) for field in FIELDS}
        processed = None
        if all(totals[field] is not None for field in FIELDS[:4]):
            processed = sum(totals[field] for field in FIELDS[:4])
        return {"usage_events": self.usage_events,
                "usage_sum": totals,
                "processed_tokens": processed,
                "missing_usage_fields": sorted(self.usage_missing),
                "tool_calls": dict(sorted(self.tool_counts.items())),
                "event_counts": dict(sorted(self.event_counts.items()))}

    def report(self, exit_code=None, interrupted=False):
        result = self.snapshot()
        end = self.end or {}
        terminal_text = self.last_response_text if self.usage_events else "".join(self.current_text)
        terminal_text = terminal_text.strip()
        complete = end.get("stopReason") == "end_turn" and bool(terminal_text)
        end_usage = end.get("usage") if isinstance(end.get("usage"), dict) else None
        cost_ticks = end.get("total_cost_usd_ticks")
        if not positive_int(cost_ticks):
            cost_ticks = None
        result.update({"complete_answer": complete,
                       "terminal_answer_chars": len(terminal_text) if complete else 0,
                       "terminal_answer_sha256": (hashlib.sha256(terminal_text.encode("utf-8")).hexdigest()
                                                  if complete else None),
                       "stop_reason": end.get("stopReason"),
                       "session_id": end.get("sessionId"),
                       "request_id": end.get("requestId"),
                       "end_num_turns": end.get("num_turns"),
                       "end_usage": end_usage,
                       "total_cost_usd_ticks": cost_ticks,
                       "cost_is_partial": end.get("cost_is_partial"),
                       "usage_is_incomplete": end.get("usage_is_incomplete"),
                       "soft_turns": self.soft_turns,
                       "soft_reached": self.soft_snapshot is not None,
                       "soft_snapshot": self.soft_snapshot,
                       "malformed_lines": self.malformed_lines,
                       "exit_code": exit_code,
                       "interrupted": interrupted})
        return result

    def accepted_answer(self):
        if not self.report()["complete_answer"]:
            return None
        return self.last_response_text.strip() if self.usage_events else "".join(self.current_text).strip()


def audit(path, soft_turns=14):
    ledger = StreamLedger(soft_turns)
    with Path(path).open("r", encoding="utf-8") as stream:
        for line in stream:
            ledger.feed(line)
    return ledger.report()


def inspect_skill(report, name, expected_file):
    skills = report.get("skills") if isinstance(report, dict) else None
    if not isinstance(skills, list):
        raise ValueError("inspect JSON has no skills array")
    matches = [item for item in skills if isinstance(item, dict) and item.get("name") == name]
    if len(matches) != 1:
        raise ValueError("inspect must show exactly one active skill named " + name)
    source = matches[0].get("source")
    selected = source.get("path") if isinstance(source, dict) else None
    if not isinstance(selected, str) or Path(selected).resolve() != Path(expected_file).resolve():
        raise ValueError("inspect active skill path differs from --skill-file")
    return selected


def run(args):
    if args.hard_turns <= args.soft_turns:
        raise ValueError("hard turns must exceed soft turns")
    if args.session_id and args.resume_id:
        raise ValueError("--session-id creates a new conversation; use --resume-id alone to continue")
    if args.resume_id:
        try:
            uuid.UUID(args.resume_id)
        except ValueError as exc:
            raise ValueError("--resume-id must be an existing session UUID") from exc
    project = args.project.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project must be a directory")
    prompt = args.prompt_file.resolve(strict=True)
    skill = args.skill_file.resolve(strict=True)
    if not prompt.is_file() or not skill.is_file():
        raise ValueError("prompt and SKILL must be regular files")
    prompt_hash, skill_hash = sha256(prompt), sha256(skill)
    for label, actual, expected in (("prompt", prompt_hash, args.expected_prompt_sha256),
                                    ("skill", skill_hash, args.expected_skill_sha256)):
        if expected and actual != expected.lower():
            raise ValueError(label + " SHA-256 differs from expected frozen bytes")
    rules_text = None
    rules_hash = None
    if args.rules_file:
        rules_text = args.rules_file.read_text(encoding="utf-8").strip()
        rules_hash = sha256(args.rules_file)
    out = args.out.resolve()
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(out, 0o700)
    env = os.environ.copy()
    env["GROK_HOME"] = str(args.grok_home.resolve())
    env["GROK_DISABLE_AUTOUPDATER"] = "1"
    frozen_prompt = out / "prompt.txt"
    shutil.copyfile(prompt, frozen_prompt)
    os.chmod(frozen_prompt, 0o600)
    if sha256(frozen_prompt) != prompt_hash:
        raise ValueError("frozen prompt copy differs before dispatch")
    cli = str(args.cli)
    inspect_proc = subprocess.run([cli, "inspect", "--json"], cwd=project, env=env,
                                  capture_output=True, text=True, timeout=30, check=False)
    if inspect_proc.returncode != 0:
        raise ValueError("grok inspect failed before dispatch: " + inspect_proc.stderr.strip())
    inspect_report = json.loads(inspect_proc.stdout)
    selected_skill = inspect_skill(inspect_report, args.skill_name, skill)
    write_json(out / "inspect.json", inspect_report)
    version_proc = subprocess.run([cli, "--version"], cwd=project, env=env,
                                  capture_output=True, text=True, timeout=10, check=False)
    if version_proc.returncode != 0:
        raise ValueError("grok --version failed before dispatch")
    cmd = [cli, "-m", args.model, "--sandbox", args.sandbox,
           "--no-subagents", "--max-turns", str(args.hard_turns),
           "--output-format", "streaming-json", "--prompt-file", str(frozen_prompt)]
    if args.always_approve:
        cmd.append("--always-approve")
    if args.session_id:
        cmd.extend(["--session-id", args.session_id])
    if args.resume_id:
        cmd.extend(["--resume", args.resume_id])
    if args.reasoning_effort:
        cmd.extend(["--effort", args.reasoning_effort])
    if rules_text:
        cmd.extend(["--rules", rules_text])
    manifest = {"cli_version": version_proc.stdout.strip(), "project": str(project),
                "grok_home": env["GROK_HOME"], "prompt_original": str(prompt),
                "prompt_sha256": prompt_hash, "frozen_prompt": str(frozen_prompt),
                "skill_name": args.skill_name, "skill_file": str(skill),
                "skill_sha256": skill_hash, "inspect_active_skill_path": selected_skill,
                "model": args.model, "reasoning_effort": args.reasoning_effort,
                "rules_sha256": rules_hash, "sandbox": args.sandbox,
                "always_approve": args.always_approve, "session_id_requested": args.session_id,
                "resume_id_requested": args.resume_id,
                "soft_turns": args.soft_turns, "hard_turns": args.hard_turns,
                "max_seconds": args.max_seconds,
                "automatic_retry": False}
    write_json(out / "manifest.json", manifest)
    ledger = StreamLedger(args.soft_turns)
    interrupted = False
    deadline_reached = threading.Event()
    started = time.monotonic()
    with (out / "stderr.txt").open("x", encoding="utf-8") as error_file, \
            (out / "stream.ndjson").open("x", encoding="utf-8") as stream_file:
        proc = subprocess.Popen(cmd, cwd=project, env=env, stdout=subprocess.PIPE,
                                stderr=error_file, text=True, bufsize=1,
                                start_new_session=True)

        def signal_group(signum):
            try:
                os.killpg(proc.pid, signum)
            except ProcessLookupError:
                pass

        force_timer = threading.Timer(STOP_GRACE_SECONDS, signal_group,
                                      args=(signal.SIGKILL,))
        force_timer.daemon = True

        def stop_on_deadline():
            deadline_reached.set()
            print("wallclock deadline reached; stopping Grok process group", file=sys.stderr)
            signal_group(signal.SIGTERM)
            force_timer.start()

        deadline_timer = threading.Timer(args.max_seconds, stop_on_deadline)
        deadline_timer.daemon = True
        deadline_timer.start()
        try:
            for line in proc.stdout:
                stream_file.write(line)
                stream_file.flush()
                before = ledger.usage_events
                ledger.feed(line)
                if before < args.soft_turns == ledger.usage_events:
                    print("soft observation reached; Grok continues", file=sys.stderr)
            exit_code = proc.wait()
        except KeyboardInterrupt:
            interrupted = True
            signal_group(signal.SIGINT)
            try:
                exit_code = proc.wait(timeout=STOP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                signal_group(signal.SIGKILL)
                exit_code = proc.wait()
        finally:
            deadline_timer.cancel()
            force_timer.cancel()
            if deadline_reached.is_set() or interrupted or proc.poll() is None:
                signal_group(signal.SIGKILL)
            if proc.poll() is None:
                proc.wait()
    receipt = ledger.report(exit_code=exit_code, interrupted=interrupted)
    receipt["deadline_reached"] = deadline_reached.is_set()
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    receipt["frozen_identity_ok_after"] = (sha256(prompt) == prompt_hash and
                                           sha256(skill) == skill_hash and
                                           sha256(frozen_prompt) == prompt_hash)
    answer = ledger.accepted_answer()
    if answer:
        with (out / "terminal-answer.txt").open("x", encoding="utf-8") as target:
            target.write(answer + "\n")
    write_json(out / "summary.json", receipt)
    print(json.dumps({"out": str(out), "complete_answer": receipt["complete_answer"],
                      "stop_reason": receipt["stop_reason"],
                      "usage_events": receipt["usage_events"],
                      "processed_tokens": receipt["processed_tokens"],
                      "total_cost_usd_ticks": receipt["total_cost_usd_ticks"]},
                     ensure_ascii=False))
    return 0 if receipt["complete_answer"] and receipt["frozen_identity_ok_after"] and exit_code == 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    offline = commands.add_parser("audit", help="parse an existing NDJSON trace; no model")
    offline.add_argument("--stream", type=Path, required=True)
    offline.add_argument("--soft-turns", type=int, default=14)
    live = commands.add_parser("run", help="dispatch exactly one Grok CLI session")
    live.add_argument("--project", type=Path, required=True)
    live.add_argument("--grok-home", type=Path, required=True)
    live.add_argument("--prompt-file", type=Path, required=True)
    live.add_argument("--skill-file", type=Path, required=True)
    live.add_argument("--out", type=Path, required=True)
    live.add_argument("--cli", type=Path, default=Path("grok"))
    live.add_argument("--skill-name", default="pea-princess")
    live.add_argument("--model", default="grok-4.6")
    live.add_argument("--sandbox", default="workspace")
    live.add_argument("--reasoning-effort")
    live.add_argument("--rules-file", type=Path)
    live.add_argument("--session-id")
    live.add_argument("--resume-id", help="continue this project's existing Grok session; never creates a new ID")
    live.add_argument("--always-approve", action="store_true")
    live.add_argument("--expected-prompt-sha256")
    live.add_argument("--expected-skill-sha256")
    live.add_argument("--soft-turns", type=int, default=14)
    live.add_argument("--hard-turns", type=int, default=32)
    live.add_argument("--max-seconds", type=float, default=3600)
    args = parser.parse_args(argv)
    if args.soft_turns < 1:
        parser.error("soft turns must be positive")
    if args.command == "run" and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        parser.error("max seconds must be positive and finite")
    try:
        if args.command == "audit":
            print(json.dumps(audit(args.stream, args.soft_turns), ensure_ascii=False))
            return 0
        old_umask = os.umask(0o077)
        try:
            return run(args)
        finally:
            os.umask(old_umask)
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
