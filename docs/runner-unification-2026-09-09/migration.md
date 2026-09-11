# Runner migration guide

This document accompanies the 2026-09-09 migration. Final verification and new quality measurements are recorded in `results.md` when available. Historical raw evidence and the original frozen experiment sources remain separate.

## Shared execution boundary

The common `CallControl` ledger records dispatch before invoking a physical model call, terminal direct usage afterward, and an explicit skipped state for unused planned capacity. Restored successful calls do not invoke a model again. A failed or unresolved call blocks new dispatch; missing token counters are unknown, never zero-filled to make a batch look complete.

Two adapters use that same ledger:

- `bench/durable_run.py` and `bench/legacy_control.py` serve legacy CLI/API runners and dynamic role/turn loops. They bind a run configuration, request identities, source/input fingerprints and a finite call ceiling.
- The newer context/cost/ablation runners keep their frozen fixture plans and raw JSONL format, but route physical execution through `CallControl` and the shared process lifecycle functions in `bench/launch.py`.

This is shared persistence and accounting, not a promise that tool-enabled rental investigations have the same permissions as no-tools document experiments. The tool policy is explicit and frozen. Tool-enabled jobs require an owned work directory; no-tools experiments reject observed tool events. Runtime sandboxing and filesystem/network permissions are still required for hostile documents.

## Entry points

| Entry point | Workload |
|---|---|
| `bench/run.py` | Whole-skill shell/API cases and onboarding responses |
| `bench/journeys.py` | Scripted multi-turn conversations |
| `bench/personas.py` | Persona, target and judge roles |
| `bench/docs_bench.py` | Document testbed matrix |
| `bench/pipeline.py` | Planner, executor, verifier and integration roles |
| `bench/ab/run_ab.py` | Interleaved A/B configurations |
| `bench/ab/run_codex.py` | Codex A/B target |
| `bench/ab/worker_eval.py` | Document workers |
| `bench/cost_probe.py` | Reporting-cost pilot |
| `bench/context_quality.py` | Context/quality A/B pilot |
| `bench/ablation_study.py` | Full mechanism ablation |

Offline graders, fixture refreshers and report reducers are not model runners. They do not need synthetic paid-call ledger entries.

## Starting a new legacy run

Live legacy entrypoints require explicit model choices plus:

```
--durable-dir <new-owned-run-directory>
--max-calls <positive-physical-call-ceiling>
--max-processed-tokens <positive-reported-token-ceiling>
```

For example, first inspect a dry run:

```sh
python3 bench/run.py --agent codex --case explain-capabilities \
  --model gpt-5.6-terra \
  --durable-dir bench/results/onboarding-durable-example \
  --max-calls 2 --max-processed-tokens 100000 --dry-run
```

Removing `--dry-run` makes model calls. The models above are explicit benchmark requests, not a recommendation to migrate every application to that model. Multi-role configurations must pin each actual actor too.

Persona sessions need explicit target/persona models and a judge model unless rules-only. A model-based persona `--regrade` requires `--judge-model` and the live bounds; rules-only regrading remains offline. Live `--skip-existing` cannot bypass the ledger. Recovery copies are capped at 2,000 files / 32 MiB, and the source must neither contain nor be contained by the new durable directory.

Claude stays disabled by default. `--allow-claude` is an explicit opt-in for a new authorized experiment, not a rate-limit polling or automatic recovery mechanism. The seven earlier paused Claude confirmations are not resumed by this migration.

Physical calls are serial so that the next call cannot race a failure in another one. Budget checks occur between calls; one call may exceed the token ceiling. A complete result with warning-only stderr is retained instead of bought again. Conversely, a failed result with partial usage remains a failure even if some useful text was produced.

## Restore and recovery

Repeat the exact original command against the same directory to validate and reuse successful work. Changed model/settings, request content or pinned inputs should reject reuse. Raw-file presence alone is not permission to skip a job.

Workdir snapshots restore file contents, not an exact directory tree. Empty runtime directories are preserved; the caller must create its owned working directory before dispatch or replay. A missing/non-directory cwd is rejected before a call is registered. See the [nested-persona directory incident and recovery](../controller-recovery-2026-09-11.md).

If a call is pending after interruption, do not delete its checkpoint or manually mark it successful. Inspect the retained process/output state. If it failed or the outcome remains unknown, preserve that directory. A deliberate recovery requires a new documented attempt with its own identity and budget; totals must include any known earlier usage. This migration does not auto-resolve uncertain provider billing or implement exactly-once delivery across provider servers.

## Evidence and permissions

Run metadata, stdout/stderr, request snapshots and generated workdir files are private operational artifacts. Hashes provide integrity checks, not anonymization or access control. New run directories use owner-only permissions; do not publish raw traces as part of a public skill release.

The lifecycle code supervises owned local processes and ordinary descendants. It is not a container boundary against deliberate daemon escape or forced supervisor termination. An allowed Python interpreter remains broad code execution; these runners are not a hosted multi-user service.

The call ceiling covers invocations issued by these runners. It does not independently meter a tool-enabled target that launches another provider from inside an allowed shell/Python tool, or repair external side effects and remote Claude session state. Keep provider credentials and unrelated tools out of hostile-document workloads. The quality rerun uses authored fictional sources and rejects observed tool events; it does not establish preventive filesystem isolation for every legacy agent.

Direct API providers that omit required cache counters stop with unknown telemetry instead of an invented zero. Named Claude models are blocked unless explicitly enabled; an arbitrary proxy model alias cannot prove the actual backend provider.
