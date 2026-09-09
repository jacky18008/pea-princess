# Persistent call controller integration — 2026-09-09

**Implemented and validated offline: 22 tests pass.** The adapter replayed all 38 saved CLI results and reproduced **639,639 input + 30,087 output = 669,726 processed tokens**, including **132,352 cached input tokens** within input. Reopening the checkpoint and replaying the same calls invoked **zero additional callbacks**. No new benchmark model calls or callback subprocesses were started.

The smallest integration is the new [call adapter](../../bench/call_control.py) around the new runner’s invocation callback. Existing runner stop guards, raw event capture and saved-file verification remain intact. The frozen `context_quality.py`, `report_control.py` and `launch.py` files were not edited by this work.

## API

```python
from call_control import CallControl

control = CallControl(output / "control", planned_call_ids)
record = control.run(
    call_id, logical_job_id, role, phase,
    lambda: invoke_and_return_saved_result(),
)
# Only when an optional retrieval was not requested:
control.skip(optional_call_id, "initial answer requested no documents")
progress = control.report()
```

Each physical invocation is its own reducer session. A selection call and its retrieved-document answer share a logical job but have different call IDs/phases. A batch judge also receives a separate call ID and role. The public report describes calls and usage; it does not reinterpret the reducer’s agent/judge quality fields as benchmark quality.

- `dispatch(call_id, job_id, role, phase)` commits a new dispatch before execution and returns `True`. An identical already successful call returns `False`. Paused, unresolved, unplanned, skipped or conflicting calls cannot start.
- `complete(call_id, record)` preserves the result and direct usage. Duplicate identical completion is idempotent; conflicting terminal records reject. Failed or incomplete telemetry pauses scheduling.
- `run(..., invoke_callback)` combines these operations around a zero-argument callback and returns a successful result dictionary. A stopped/invalid result is persisted, then raises `CallControlPaused`; the exception exposes `.call_id`, `.failure_kind` and `.record`. A callback exception is persisted and reraised.
- `skip(call_id, reason)` applies only to an undispatched planned call. It stores the reason separately, adds no request or usage, and is idempotent for the same reason. Dispatched calls cannot be erased through skipping.
- `report()`, `snapshot()` and `record(call_id)` return defensive copies. Public decisions are `pause_calls`, `wait` and `report_results`. The report exposes `skipped_calls`, `skipped_call_ids`, `skip_reasons`, `completed_or_skipped_calls` and `plan_complete`.

The callback should return its saved result even when `status == "stopped"`. If an invocation raises after writing `result.json`, its wrapper should return that saved record, or attach it as `exception.record`, so known failed-attempt usage reaches the ledger. A generic exception without a saved result has unknown usage and pauses. No fallback token values fill missing direct usage.

Use a dedicated controller directory and preserve the ordered plan on restore. Success requires a complete result plus exactly one valid direct terminal usage record. Known usage from failed attempts counts once; missing input/output leaves total usage null. Cache-subset contradictions, malformed events, unexpected tools, failed exits and timeouts cannot be treated as successful calls. A nonfatal catalog-refresh stderr message does not change an otherwise valid complete result.

## Persistence and validation

`checkpoint.json` is the authoritative checksum-verified state. It is atomically replaced and fsynced before callback execution; `progress.json` is derived and repaired on restore. A local POSIX lock serializes ledger changes, and only one unresolved invocation is permitted. A crash after dispatch leaves an unresolved call that fails closed. The adapter provides no automatic retry or resume API.

The [22 focused tests](../../tests/test_call_control.py) cover the real saved run and the actual callback boundary: duplicate delivery, checkpoint restoration, original-record immutability, metadata/plan conflicts, a failed stub that prevents the next callback, missing/partial/invalid direct usage, exception-attached failed usage, warning-only stderr, stale progress repair and optional skips. One synthetic success plus one optional skip completes a two-slot plan with **one physical call and 13 tokens**, rather than inventing a second call.

The preserved offline validation is under `bench/results/ablation-2026-09-09/controller/`. It includes the 38-call replay checkpoint/report and separate failure, missing-usage, optional-skip, warning and unresolved-restore checkpoints. All **114 original result/event/stderr input files** were rehashed afterward and remained unchanged.

The test command was:

```sh
python3 -m unittest discover -s tests -p 'test_call_control.py' -v
```

The [machine-readable integration record](controller-integration.json) records the API, exact totals, source hashes and artifact hashes. The validation manifest SHA-256 is `390fede6d35b78cad42f838cd48cec2bdd04ba7b81bf5102c67fff58d5d863d4`.

This is a serial local runner integration boundary, not a deployment of production notifications or a measurement of streaming provider-error detection latency. Logical-job quality and model-judge labels remain the runner’s separate reporting responsibility. The next live ablation is owned and recorded by the main task; these offline checks make no live-run claims.
