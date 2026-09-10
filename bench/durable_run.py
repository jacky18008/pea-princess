#!/usr/bin/env python3
"""Durable, serial physical-call boundary for legacy benchmark runners.

The frozen plan is a ceiling, not permission to retry. A failed or unresolved call
stops every later invocation; successful replays restore their recorded artifacts.
The token budget is checked between calls, so the final call can exceed it.
No model is called by constructing, inspecting, or replaying this controller.
"""
import base64
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess

from call_control import (CallControl, CallControlError, CallControlPaused,
                          ConflictingCallError, _atomic_json, _digest, failure_kind)
import launch
import report_control

VERSION = 1
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_SNAPSHOT_FILES = 2000
EXCLUDED = ((".git",), (".cache",), ("__pycache__",))
_SKIP_DISCOVERY_WARNING = re.compile(
    r"Under-development features enabled: skip_host_skill_discovery\. "
    r"Under-development features are incomplete and may behave unpredictably\. "
    r"To suppress this warning, set `suppress_unstable_features_warning = true` "
    r"in /[^\x00-\x1f\x7f]+/config\.toml\."
)


def source_fingerprint(root=None):
    """Hash tracked executable/prompt inputs plus this newly added infrastructure."""
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=str(root)).decode().split("\0")
    paths = {p for p in tracked if p and not p.startswith(("bench/results/", "docs/"))
             and (p.startswith(("bench/", "scripts/", "references/", "assets/", "skills/", "tools/"))
                  or p in ("SKILL.md", "AGENTS.md", "CLAUDE.md"))}
    paths.update(str(Path(module.__file__).resolve().relative_to(root))
                 for module in (launch, report_control))
    paths.update(("bench/call_control.py", "bench/durable_run.py"))
    paths.update(str(p.relative_to(root)) for p in (root / "bench").glob("*.py"))
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sorted(paths)
            if (root / p).is_file()}


def _canonical_usage(usage, family):
    """Map direct provider counters without inventing missing zeroes."""
    if not isinstance(usage, dict):
        return None
    if family == "claude":
        result = {}
        parts = [usage.get(k) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
        if all(type(v) is int and v >= 0 for v in parts):
            result["input_tokens"] = sum(parts)
        if "cache_read_input_tokens" in usage:
            result["cached_input_tokens"] = usage["cache_read_input_tokens"]
        if "output_tokens" in usage:
            result["output_tokens"] = usage["output_tokens"]
        return result
    result = {key: usage[key] for key in ("input_tokens", "cached_input_tokens", "output_tokens") if key in usage}
    for target, alias in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
        if alias in usage and target not in result:
            result[target] = usage[alias]
        elif alias in usage and target in result and result[target] != usage[alias]:
            result[target] = None
    for key in ("prompt_tokens_details", "input_tokens_details"):
        details = usage.get(key)
        if "cached_input_tokens" not in result and isinstance(details, dict) and "cached_tokens" in details:
            result["cached_input_tokens"] = details["cached_tokens"]
    for key in ("prompt_tokens_details", "input_tokens_details"):
        details = usage.get(key)
        if isinstance(details, dict) and "cached_tokens" in details and details["cached_tokens"] != result.get("cached_input_tokens"):
            result["cached_input_tokens"] = None
    if "cache_read_input_tokens" in usage:
        if "cached_input_tokens" not in result:
            result["cached_input_tokens"] = usage["cache_read_input_tokens"]
        elif result["cached_input_tokens"] != usage["cache_read_input_tokens"]:
            result["cached_input_tokens"] = None
    direct_input, direct_output = result.get("input_tokens"), result.get("output_tokens")
    bad_total = ("total_tokens" in usage and type(direct_input) is int and type(direct_output) is int
                 and (type(usage["total_tokens"]) is not int or usage["total_tokens"] != direct_input + direct_output))
    if usage.get("usage_invalid_reason") or bad_total:
        result["input_tokens"] = None
    return result


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _startup_feature_warning(event):
    """Recognize one observed CLI diagnostic, not arbitrary item/error messages."""
    if set(event) != {"type", "item"} or event["type"] != "item.completed":
        return False
    item = event["item"]
    return (isinstance(item, dict) and set(item) == {"id", "type", "message"}
            and item["type"] == "error" and isinstance(item["id"], str)
            and re.fullmatch(r"item_[0-9]+", item["id"]) is not None
            and isinstance(item["message"], str)
            and _SKIP_DISCOVERY_WARNING.fullmatch(item["message"]) is not None)


def cli_record(call_id, result, family):
    """Audit the complete physical CLI stream, never recursive/last-holder totals."""
    raw = result.stdout or (result.text if family == "codex" else "")
    errors, tool_events, diagnostic_events, malformed, terminals = [], [], [], 0, []
    if family == "codex":
        thread_started, turn_started = False, False
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if not isinstance(event, dict):
                malformed += 1
                continue
            if event.get("type") == "thread.started":
                thread_started = True
            if event.get("type") in ("turn.started", "turn.completed", "turn.failed"):
                turn_started = True
            if thread_started and not turn_started and _startup_feature_warning(event):
                diagnostic_events.append(event)
                continue
            if event.get("type") == "turn.completed":
                terminals.append(event.get("usage"))
            if event.get("type") in ("error", "turn.failed"):
                errors.append(event)
            item = event.get("item") or {}
            if isinstance(event.get("type"), str) and event["type"].startswith("item.") and (
                    not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning")):
                tool_events.append(event)
        usage = _canonical_usage(_json_safe(terminals[0]), family) if len(terminals) == 1 else None
    elif family == "claude":
        envelope = launch.claude_envelope(raw)
        if isinstance(envelope, dict):
            terminals = [envelope.get("usage")]
            if envelope.get("is_error"):
                errors.append({"type": "provider_error", "message": envelope.get("result")})
        else:
            malformed += 1
        usage = _canonical_usage(_json_safe(terminals[0]), family) if len(terminals) == 1 else None
    else:
        raise ValueError("CLI family must be codex or claude")
    attempts = result.attempt_records or []
    timeout = any(r.get("timeout") for r in attempts)
    stopped = result.provider_error or result.exit_code != 0 or timeout or result.attempts != 1
    if result.provider_error and not errors:
        errors.append({"type": "provider_error", "message": result.note})
    return _json_safe({"id": call_id, "status": "stopped" if stopped else "complete",
            "exit_code": result.exit_code, "timeout": timeout, "errors": errors,
            "tool_events": tool_events, "diagnostic_events": diagnostic_events,
            "malformed_event_lines": malformed,
            "terminal_usage_events": len(terminals), "direct_terminal_usage": usage,
            "family": family, "launch_result": dict(result._asdict())})


def _excluded(relative):
    return any(relative.parts[:len(prefix)] == prefix for prefix in EXCLUDED)


def _snapshot(folder):
    rows, size = {}, 0
    for parent, dirs, files in os.walk(str(folder), followlinks=False):
        parent = Path(parent)
        dirs[:] = [name for name in dirs if not _excluded((parent / name).relative_to(folder))]
        for name in dirs + files:
            path = parent / name
            rel = path.relative_to(folder)
            if _excluded(rel):
                continue
            if path.is_symlink():
                raise CallControlError("mutable workdir contains a symlink: " + str(rel))
            if not path.is_file():
                continue
            length = path.stat().st_size
            size += length
            if size > MAX_SNAPSHOT_BYTES or len(rows) >= MAX_SNAPSHOT_FILES:
                raise CallControlError("mutable workdir exceeds the frozen artifact snapshot ceiling")
            rows[str(rel)] = {"data": base64.b64encode(path.read_bytes()).decode("ascii"),
                              "mode": path.stat().st_mode & 0o777}
    return rows


def _restore(folder, rows):
    current = _snapshot(folder)  # Reject symlinks and oversize trees before any write.
    for rel in current:
        if rel not in rows:
            (folder / rel).unlink()
    for parent, dirs, _files in os.walk(str(folder), topdown=False):
        for name in dirs:
            path = Path(parent) / name
            if not _excluded(path.relative_to(folder)):
                try:
                    path.rmdir()
                except OSError:
                    pass
    for rel, row in rows.items():
        path = folder / rel
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise CallControlError("invalid saved artifact path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(row["data"], validate=True))
        path.chmod(row["mode"])


def _artifact_path(folder, value):
    path = Path(value)
    path = path if path.is_absolute() else folder / path
    resolved = path.resolve()
    if folder not in resolved.parents:
        raise CallControlError("last-message artifacts must remain inside the owned workdir")
    for ancestor in (path,) + tuple(path.parents):
        if ancestor.is_symlink():
            raise CallControlError("last-message output path contains a symlink")
        if ancestor.resolve() == folder:
            break
    return path


class DurableRun:
    def __init__(self, output_dir, planned_call_ids, config, allow_tools=False,
                 allow_claude=False, max_total_tokens=None):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.output_dir.chmod(0o700)
        manifest_exists = (self.output_dir / "run.json").exists()
        checkpoint_exists = (self.output_dir / "control" / "checkpoint.json").exists()
        if manifest_exists != checkpoint_exists:
            raise CallControlError("incomplete durable state: run manifest and physical-call checkpoint must both exist; do not redispatch")
        if type(allow_claude) is not bool:
            raise ValueError("allow_claude must be boolean")
        if max_total_tokens is not None and (type(max_total_tokens) is not int or max_total_tokens <= 0):
            raise ValueError("max_total_tokens must be a positive integer")
        self.allow_claude, self.allow_tools = allow_claude, allow_tools
        self.max_total_tokens = max_total_tokens
        manifest = {"version": VERSION, "planned_call_ids": list(planned_call_ids),
                    "config": copy.deepcopy(config), "allow_tools": allow_tools,
                    "allow_claude": allow_claude, "max_total_tokens": max_total_tokens,
                    "source_sha256": source_fingerprint()}
        self.manifest = copy.deepcopy(manifest)
        self._freeze(self.output_dir / "run.json", manifest, "frozen run configuration/source differs")
        self.control = CallControl(self.output_dir / "control", manifest["planned_call_ids"], allow_tools=allow_tools)

    @contextmanager
    def _locked(self):
        with (self.output_dir / "run.lock").open("a+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _freeze(self, path, value, message):
        with self._locked():
            if path.exists():
                saved = json.loads(path.read_text(encoding="utf-8"))
                if saved.get("sha256") != _digest(saved.get("value")):
                    raise CallControlError("frozen manifest checksum differs")
                if saved["value"] != value:
                    raise ConflictingCallError(message)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_json(path, {"value": value, "sha256": _digest(value)})

    def _before(self, call_id, request, family):
        if source_fingerprint() != self.manifest["source_sha256"]:
            raise ConflictingCallError("frozen implementation/prompt source changed during the run")
        # Legacy entrypoints bind every selected external fixture without storing
        # its contents. Revalidate inside a long-running process, not just restart.
        config = self.manifest.get("config")
        inputs = config.get("input_sha256", {}) if isinstance(config, dict) else {}
        for name, expected in inputs.items():
            path = Path(name)
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ConflictingCallError("frozen input changed during the run: " + str(path))
        if family == "claude" and not self.allow_claude:
            raise CallControlError("Claude calls remain paused; explicit --allow-claude is required")
        if call_id not in self.control.planned_call_ids:
            raise ValueError("call ID is outside the frozen plan")
        filename = hashlib.sha256(call_id.encode("utf-8")).hexdigest() + ".json"
        request_path = self.output_dir / "requests" / filename
        if call_id in self.control.snapshot()["calls"] and not request_path.exists():
            raise CallControlError("dispatched call lost its immutable request manifest; do not redispatch")
        self._freeze(request_path,
                     {"call_id": call_id, "family": family, "request": request},
                     "call request differs from its frozen physical-call identity: " + call_id)
        # Earlier successful calls may replay even after the ceiling is reached.
        if self.control.record(call_id) is None and self.max_total_tokens is not None:
            report = self.control.report()
            total = report["usage"]["total_tokens"]
            if total is not None and total >= self.max_total_tokens:
                _atomic_json(self.output_dir / "budget-stop.json", {
                    "next_call_id": call_id, "max_total_tokens": self.max_total_tokens,
                    "processed_tokens": total, "scope": "between physical calls; one-call overshoot is possible"})
                raise CallControlPaused("processed-token budget reached before next physical call",
                                        call_id=call_id, failure_kind="token_budget")

    def run_cli(self, call_id, job_id, role, phase, cmd, cwd, timeout, family, **kwargs):
        if kwargs.get("attempts", 1) != 1:
            raise ValueError("durable calls permit one physical attempt; register a new plan to retry")
        kwargs["attempts"] = 1
        folder = Path(cwd).resolve()
        if self.allow_tools and (folder == self.output_dir or self.output_dir not in folder.parents):
            raise CallControlError("tool-enabled workdir must be strictly inside the durable run directory")
        command = [str(part) for part in cmd]
        if family not in ("codex", "claude") or not command or Path(command[0]).name != family:
            raise ValueError("durable CLI executable must match its declared codex/claude family")
        models = []
        for index, part in enumerate(command):
            if part in ("--model", "-m") and index + 1 < len(command):
                models.append(command[index + 1])
            elif part.startswith("--model="):
                models.append(part.split("=", 1)[1])
        if len(models) != 1 or not models[0].strip() or models[0].startswith("-"):
            raise ValueError("every durable CLI call must specify exactly one explicit model")
        for flag in ("--session-id", "--output-last-message", "-o"):
            if command.count(flag) > 1:
                raise ValueError("runtime CLI flags cannot be duplicated")
        if "--output-last-message" in command and "-o" in command:
            raise ValueError("last-message output must be specified once")
        for flag in ("--output-last-message", "-o"):
            if flag in command:
                index = command.index(flag) + 1
                if index >= len(command):
                    raise ValueError("missing last-message output path")
                _artifact_path(folder, command[index])
        normalized = [part.replace(str(folder), "<WORKDIR>") for part in command]
        for flag in ("--session-id", "--output-last-message", "-o"):
            if flag in normalized:
                position = normalized.index(flag) + 1
                if position < len(normalized):
                    normalized[position] = "<RUNTIME:" + flag + ">"
        self._before(call_id, {"command": normalized, "timeout": timeout}, family)
        snapshot = self.allow_tools
        if snapshot:
            _snapshot(folder)  # Check bounded ownership before an irreversible call.

        def invoke():
            result = launch.run(command, str(folder), timeout, family, **kwargs)
            record = cli_record(call_id, result, family)
            try:
                if snapshot:
                    record["workdir_artifacts"] = _snapshot(folder)
                outputs = {}
                for flag in ("--output-last-message", "-o"):
                    if flag in command:
                        index = command.index(flag) + 1
                        if index < len(command):
                            path = _artifact_path(folder, command[index])
                            if path.is_file() and not path.is_symlink():
                                if path.stat().st_size > MAX_SNAPSHOT_BYTES:
                                    raise CallControlError("last-message artifact exceeds snapshot ceiling")
                                outputs[flag] = base64.b64encode(path.read_bytes()).decode("ascii")
                record["output_artifacts"] = outputs
            except Exception as error:
                record["status"] = "stopped"
                record["artifact_error"] = str(error)
            return record

        record = self.control.run(call_id, job_id, role, phase, invoke)
        if snapshot:
            _restore(folder, record["workdir_artifacts"])
        for flag, data in record.get("output_artifacts", {}).items():
            path = _artifact_path(folder, command[command.index(flag) + 1])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(data, validate=True))
        return launch.LaunchResult(**record["launch_result"])

    run = run_cli

    def run_callable(self, call_id, job_id, role, phase, callback, request, family="api"):
        """Callback returns an existing canonical terminal-record dict, exactly once."""
        self._before(call_id, request, family)
        return self.control.run(call_id, job_id, role, phase, callback)

    def run_api(self, call_id, job_id, role, phase, callback, model, request_identity=None):
        """Persist legacy (text, direct_usage, error_note) API callback results.

        API request retrying must be disabled by its caller/SDK. Missing cached
        counters remain unknown and pause the run rather than being filled with 0.
        """
        if not isinstance(model, str) or not model.strip():
            raise ValueError("every durable API call must specify its model")
        if "claude" in model.lower() and not self.allow_claude:
            raise CallControlError("Claude calls remain paused, including API models")
        self._before(call_id, {"model": model, "request": request_identity}, "api")

        def invoke():
            result = callback()
            if not isinstance(result, (tuple, list)) or len(result) != 3:
                raise ValueError("API callback must return (text, usage, note)")
            text, usage, note = result
            return {"id": call_id, "status": "stopped" if note else "complete",
                    "errors": [{"type": "api_error", "message": str(note)}] if note else [],
                    "exit_code": 0, "terminal_usage_events": 1 if isinstance(usage, dict) else 0,
                    "direct_terminal_usage": _canonical_usage(_json_safe(usage), "api"),
                    "api_result": _json_safe(list(result))}
        record = self.control.run(call_id, job_id, role, phase, invoke)
        return tuple(record["api_result"])

    def skip(self, call_id, reason):
        return self.control.skip(call_id, reason)

    def report(self):
        result = self.control.report()
        if (self.output_dir / "budget-stop.json").exists() and not result["plan_complete"]:
            result.update(paused=True, decision="pause_calls", failure_kind="token_budget",
                          budget=json.loads((self.output_dir / "budget-stop.json").read_text()))
        return result


def add_arguments(parser):
    parser.add_argument("--durable-dir", "--control-dir", dest="durable_dir")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-processed-tokens", "--max-total-tokens", dest="max_processed_tokens", type=int)
    parser.add_argument("--allow-claude", action="store_true")


def require_session(args, identity, planned_call_ids, config=None, allow_tools=False):
    if not getattr(args, "durable_dir", None):
        raise ValueError("live calls require --durable-dir")
    planned = list(planned_call_ids)
    if getattr(args, "max_calls", None) is not None and len(planned) > args.max_calls:
        raise ValueError("planned calls exceed --max-calls")
    return DurableRun(args.durable_dir, planned, {"identity": identity, "config": config},
                      allow_tools=allow_tools, allow_claude=getattr(args, "allow_claude", False),
                      max_total_tokens=getattr(args, "max_processed_tokens", None))
