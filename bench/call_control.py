#!/usr/bin/env python3
"""Persistent serial CLI-call adapter around the offline reporting reducer.

Each physical invocation is a reducer session; logical jobs, roles and phases are
metadata. The adapter never starts a process or model itself. Python 3.9 stdlib.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

import report_control


VERSION = 1
FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")


class CallControlError(RuntimeError):
    pass


class CallControlPaused(CallControlError):
    def __init__(self, message, call_id=None, failure_kind=None, record=None):
        super().__init__(message)
        self.call_id = call_id
        self.failure_kind = failure_kind
        self.record = copy.deepcopy(record)


class PendingCallError(CallControlError):
    pass


class ConflictingCallError(CallControlError):
    pass


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _atomic_json(path, value):
    """Commit a whole JSON file; a crash cannot expose a partial checkpoint."""
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent),
                                         prefix="." + path.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
        descriptor = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def failure_kind(record):
    """A complete wrapper status cannot override failed events or bad telemetry."""
    if record.get("errors"):
        return "provider_error"
    if record.get("timeout"):
        return "timeout"
    if record.get("tool_events"):
        return "unexpected_tool_use"
    if record.get("malformed_event_lines"):
        return "malformed_events"
    if record.get("exit_code", 0) != 0:
        return "process_error"
    if record.get("status") != "complete":
        return "call_failure"
    direct = record.get("direct_terminal_usage")
    if type(record.get("terminal_usage_events")) is not int or record["terminal_usage_events"] != 1 \
            or not isinstance(direct, dict):
        return "invalid_direct_usage"
    if any(type(direct.get(field)) is not int or direct[field] < 0 for field in FIELDS):
        return "invalid_direct_usage"
    if direct["cached_input_tokens"] > direct["input_tokens"]:
        return "invalid_direct_usage"
    return None


class CallControl:
    """Guard callbacks using an atomic checkpoint and a fixed progress report.

    Successful saved calls are idempotent. Failures stay paused, and a restored
    in-flight call is never dispatched again automatically. There is no automatic
    retry or resume API. All methods reread the checkpoint under a POSIX file lock;
    at most one unresolved physical invocation is permitted.
    """

    def __init__(self, output_dir, planned_call_ids):
        self.output_dir = Path(output_dir)
        if isinstance(planned_call_ids, (str, bytes)):
            raise ValueError("planned call IDs must be a sequence, not a string")
        self.planned_call_ids = list(planned_call_ids)
        # Use the reducer's independently tested plan validation.
        report_control.initial_state(self.planned_call_ids)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.output_dir / "checkpoint.json"
        self.progress_path = self.output_dir / "progress.json"
        self.reducer_sha256 = hashlib.sha256(Path(report_control.__file__).read_bytes()).hexdigest()
        with self._locked() as state:
            if not self.checkpoint_path.exists():
                self._save(state)
            else:
                # Repair a stale derived report after an interrupted two-file save.
                _atomic_json(self.progress_path, self._report(state))

    def _initial(self):
        return {"version": VERSION, "planned_call_ids": self.planned_call_ids,
                "reducer_sha256": self.reducer_sha256, "revision": 0, "calls": {}, "skipped": {},
                "reducer_state": report_control.initial_state(self.planned_call_ids)}

    @contextmanager
    def _locked(self):
        with (self.output_dir / "controller.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if self.checkpoint_path.exists():
                    envelope = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
                    state = envelope["state"]
                    if envelope["state_sha256"] != _digest(state):
                        raise CallControlError("checkpoint checksum differs")
                    if state["version"] != VERSION or state["reducer_sha256"] != self.reducer_sha256:
                        raise CallControlError("checkpoint controller/reducer version differs")
                    if state["planned_call_ids"] != self.planned_call_ids:
                        raise CallControlError("checkpoint planned call IDs differ")
                    if set(state["calls"]) != set(state["reducer_state"]["requests"]):
                        raise CallControlError("checkpoint request ledger differs")
                    if set(state["skipped"]) & set(state["calls"]) \
                            or not set(state["skipped"]).issubset(self.planned_call_ids):
                        raise CallControlError("checkpoint skipped-call ledger differs")
                    for row in state["calls"].values():
                        if row["record"] is not None and _digest(row["record"]) != row["record_sha256"]:
                            raise CallControlError("checkpoint original record checksum differs")
                else:
                    state = self._initial()
                yield state
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _save(self, state):
        _atomic_json(self.checkpoint_path, {"state": state, "state_sha256": _digest(state)})
        _atomic_json(self.progress_path, self._report(state))

    @staticmethod
    def _report(state):
        reduced = report_control.report(state["reducer_state"])
        calls = []
        for call_id, row in state["calls"].items():
            status = "pending" if row["record"] is None else ("failed" if row["failure_kind"] else "complete")
            calls.append({"call_id": call_id, "job_id": row["job_id"], "role": row["role"],
                          "phase": row["phase"], "status": status, "failure_kind": row["failure_kind"]})
        completed = sum(c["status"] == "complete" for c in calls)
        failed = sum(c["status"] == "failed" for c in calls)
        covered = completed + len(state["skipped"])
        plan_complete = covered == len(state["planned_call_ids"])
        return {"version": VERSION, "revision": state["revision"],
                "planned_calls": len(state["planned_call_ids"]), "dispatched_calls": len(calls),
                "completed_calls": completed, "failed_calls": failed,
                "skipped_calls": len(state["skipped"]), "skipped_call_ids": list(state["skipped"]),
                "skip_reasons": copy.deepcopy(state["skipped"]),
                "completed_or_skipped_calls": covered, "resolved_planned_calls": covered + failed,
                "plan_complete": plan_complete,
                "pending_call_ids": [c["call_id"] for c in calls if c["status"] == "pending"],
                "paused": reduced["paused"], "decision": "pause_calls" if reduced["paused"] else
                    ("report_results" if plan_complete else "wait"),
                "usage": reduced["usage"], "calls": calls,
                "scope": "Physical CLI calls and direct token usage only; logical job quality is reported separately."}

    def report(self):
        with self._locked() as state:
            return copy.deepcopy(self._report(state))

    def snapshot(self):
        with self._locked() as state:
            return copy.deepcopy(state)

    def record(self, call_id):
        with self._locked() as state:
            row = state["calls"].get(call_id)
            return copy.deepcopy(row["record"]) if row is not None else None

    @staticmethod
    def _raise_paused(state):
        failed = next((r for r in state["calls"].values() if r["failure_kind"]), None)
        raise CallControlPaused("call controller is paused; no new callback may start",
                                call_id=failed["call_id"] if failed else None,
                                failure_kind=failed["failure_kind"] if failed else None,
                                record=failed["record"] if failed else None)

    def dispatch(self, call_id, job_id, role, phase):
        metadata = {"call_id": call_id, "job_id": job_id, "role": role, "phase": phase}
        if any(not isinstance(value, str) or not value for value in metadata.values()):
            raise ValueError("call, logical job, role and phase IDs must be nonempty strings")
        if call_id not in self.planned_call_ids:
            raise ValueError("call ID is not in the frozen controller plan: " + call_id)
        with self._locked() as state:
            if call_id in state["skipped"]:
                raise ConflictingCallError("cannot dispatch a skipped call: " + call_id)
            previous = state["calls"].get(call_id)
            if previous is not None:
                if any(previous[key] != value for key, value in metadata.items()):
                    raise ConflictingCallError("call ID reused with different job/role/phase: " + call_id)
                if previous["record"] is not None and previous["failure_kind"] is None:
                    return False
            if state["reducer_state"]["paused"]:
                self._raise_paused(state)
            pending = [key for key, row in state["calls"].items() if row["record"] is None]
            if pending:
                raise PendingCallError("unresolved call blocks dispatch; inspect its saved artifacts: " + pending[0])
            reduced = report_control.reduce_event(state["reducer_state"], {
                "id": "dispatch/" + call_id, "type": "dispatch", "request_id": call_id,
                "session": call_id, "stage": "agent"})
            if call_id not in reduced["requests"]:
                raise CallControlError("underlying reducer rejected dispatch")
            state["reducer_state"] = reduced
            state["calls"][call_id] = dict(metadata, record=None, record_sha256=None, failure_kind=None)
            state["revision"] += 1
            self._save(state)
            return True

    def skip(self, call_id, reason):
        """Resolve an optional planned call without inventing a dispatch or usage."""
        if call_id not in self.planned_call_ids:
            raise ValueError("call ID is not in the frozen controller plan: " + call_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("a nonempty skip reason is required")
        with self._locked() as state:
            if call_id in state["calls"]:
                raise ConflictingCallError("cannot skip a dispatched call: " + call_id)
            if call_id in state["skipped"]:
                if state["skipped"][call_id] != reason:
                    raise ConflictingCallError("skip reason differs for existing call: " + call_id)
                return False
            state["skipped"][call_id] = reason
            state["revision"] += 1
            self._save(state)
            return True

    def complete(self, call_id, record):
        if not isinstance(record, dict) or record.get("id", call_id) != call_id:
            raise ValueError("result must be a dict for the dispatched call ID")
        original = copy.deepcopy(record)
        original_digest = _digest(original)  # Reject non-JSON records before changing state.
        with self._locked() as state:
            if call_id not in state["calls"]:
                raise CallControlError("cannot complete an undispatched call")
            row = state["calls"][call_id]
            if row["record"] is not None:
                if row["record_sha256"] != original_digest:
                    raise ConflictingCallError("different terminal record for existing call: " + call_id)
                return copy.deepcopy(row["record"])
            kind = failure_kind(original)
            direct = original.get("direct_terminal_usage")
            usage = {key: direct[key] for key in FIELDS if key in direct} if isinstance(direct, dict) else {}
            # The frozen reducer has one stop event. The adapter maps all guarded
            # call failures to it, while exposing the actual category separately;
            # its provider retry/quality fields are never our public call report.
            event = {"id": "terminal/" + call_id,
                     "type": "provider_error" if kind else "result", "request_id": call_id,
                     "usage": usage, "failure_kind": kind}
            if kind is None:
                event.update(outcome="completed", grade=None)
            state["reducer_state"] = report_control.reduce_event(state["reducer_state"], event)
            row.update(record=original, record_sha256=original_digest, failure_kind=kind)
            state["revision"] += 1
            self._save(state)
            return copy.deepcopy(original)

    def run(self, call_id, job_id, role, phase, invoke_callback):
        """Persist dispatch before invoking a zero-argument callback exactly once.

        Return successful saved records unchanged. A stopped/invalid result is
        persisted then raises CallControlPaused with that record attached. A
        callback exception is persisted as a failed attempt and reraised.
        """
        if not self.dispatch(call_id, job_id, role, phase):
            return self.record(call_id)
        try:
            result = invoke_callback()
        except BaseException as error:
            stopped = getattr(error, "record", None)
            if not isinstance(stopped, dict):
                stopped = {"id": call_id, "status": "stopped", "terminal_usage_events": 0,
                           "direct_terminal_usage": None,
                           "callback_exception": {"type": type(error).__name__, "message": str(error)}}
            elif failure_kind(stopped) is None:
                stopped = dict(stopped, status="stopped",
                               callback_exception={"type": type(error).__name__, "message": str(error)})
            self.complete(call_id, stopped)
            raise
        self.complete(call_id, result)
        if failure_kind(result):
            with self._locked() as state:
                self._raise_paused(state)
        return copy.deepcopy(result)
