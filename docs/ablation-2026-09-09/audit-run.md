# Independent offline run audit

After the frozen run finishes, run from the repository root:

    python3 docs/ablation-2026-09-09/audit-run.py --output docs/ablation-2026-09-09/independent-run-audit.json

The default input is bench/results/ablation-2026-09-09/live-v1. Override it with --run PATH. The auditor reads saved artifacts and uses only read-only Git commands; it does not import the runner or call a model.

The output file must not already exist. Exit 0 means the audit passed, possibly with stderr diagnostics; exit 1 means inconsistent evidence or an audit error; exit 2 means the run is incomplete and no output file was written. Without --output, a completed audit prints its full JSON to stdout.

Validate the accounting helpers without reading the live run:

    python3 docs/ablation-2026-09-09/audit-run.py --self-test

The audit checks direct terminal usage, attempts and orphan artifacts, requested models, immutable hashes, controller accounting and optional skips, dependency accounting, judge mappings, calibration copies, and stderr diagnostics. It distinguishes whole-run cost from overlapping standalone arm costs. It does not independently assess answer quality, provider billing, provider-resolved model identity, or live notification latency.
