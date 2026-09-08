# Offline zero-model reporting controller — 2026-09-08

**Result: 20/20 independently expected traces passed across 81 events.** The run saved 101 report snapshots (including each initial state). All 14 focused tests passed under Python 3.9.6, including 120 late-usage orderings and checkpoint restoration at all 101 trace boundaries.

This is an offline pure reducer prototype. It made **0 benchmark model calls, 0 network calls, and 0 deployments**. It does not establish live notification latency, production monitor behavior, provider billing savings, or end-user quality. The token values in the traces are synthetic accounting fixtures.

## Contract and oracle

The [implementation](../../bench/report_control.py) is independent of `cost_probe.facts()` and imports no existing benchmark aggregation code. The [fixture](../../evals/context-quality/controller-cases.json) contains 20 complete hand-authored expected reports plus 10 selected prefix checkpoints. Expected outcomes, usage quantities, retry lists, pauses, grades and safety counts were specified independently; the reducer did not generate its own answer key. Every final report is compared with its entire expected JSON object, with strict field/type checks. No judge or reporting model supplied the oracle.

The state machine is deliberately small: **running** or **paused**, with accepted requests and a preserved event history. Its event types are `dispatch`, `result`, `provider_error`, `judge_error`, `usage`, and `resume`. A dispatch event proposes work; accepting it records an intent in this simulation and does not start any real process.

- An accepted provider error immediately sets `paused`, including errors during judging. Every later dispatch proposal is blocked until `resume` acknowledges the current pause event ID. A second outage needs a new acknowledgment.
- Results from previously accepted in-flight requests can arrive while paused. The first terminal event for a request wins. Duplicate event IDs and request IDs cannot add outcomes or usage; conflicting identities are reported.
- Usage is a final per-request quantity, not a delta. Input includes cached input. Each known input, cached input, and output value counts once, including failed agent and judge attempts. A newly supplied field that would make cached input exceed input is rejected and remains unknown, with an explicit conflict reason; both arrival orders are tested. Late usage fills absent fields. Missing input/output makes `total_tokens` null, while the known subtotals remain visible. Zero counts only as known zero when explicitly supplied. Cached tokens are never added again to the input-plus-output total.
- Provider failures contribute no quality grade. A null grade remains null, and a failed judge leaves the completed agent ungraded. A successful replacement judge can supply the grade. Low grades, abandonment, timeout, and invalid outcomes do not enter provider retry lists.
- Each named safety failure counts at most once per graded session, and multiple caps count as one capped session. Ungraded sessions do not acquire safety zeroes.
- Agent retries require the latest attempt to have a provider error and use a new request ID. Earlier attempt cost remains in the ledger; the latest attempt determines the current session outcome. Judge requests bind to the agent result they grade.
- Original events, including rejected and duplicate callbacks, remain in the audit history. Reducing an event does not mutate its input or the previous state. A serialized checkpoint preserves the pause, history and cost ledger.

A fully observed batch with no pending requests reports results. A nonempty unfinished plan waits. An empty plan reports results with null quality. A pause takes precedence over both decisions. “Report results” means the observations can be reported, not that all sessions succeeded or all results were graded.

## Evidence

| Trace | Result | Events |
| --- | --- | ---: |
| 01-empty-plan | PASS | 0 |
| 02-empty-observations | PASS | 0 |
| 03-normal-completion | PASS | 4 |
| 04-partial-batch | PASS | 2 |
| 05-in-flight | PASS | 1 |
| 06-explicit-zero | PASS | 2 |
| 07-null-grade-missing-usage | PASS | 2 |
| 08-partial-usage | PASS | 2 |
| 09-duplicate-event | PASS | 3 |
| 10-duplicate-request | PASS | 4 |
| 11-conflicting-identities | PASS | 4 |
| 12-first-provider-error-halts | PASS | 3 |
| 13-failed-attempt-partial-usage | PASS | 3 |
| 14-late-in-flight-result | PASS | 5 |
| 15-explicit-resume-and-retry | PASS | 10 |
| 16-second-outage-stale-resume | PASS | 7 |
| 17-no-quality-outcome-provider-retry | PASS | 10 |
| 18-judge-error-is-ungraded | PASS | 4 |
| 19-judge-provider-error-halts | PASS | 5 |
| 20-judge-recovery-late-usage-safety | PASS | 10 |

The [focused tests](../../tests/test_report_control.py) also deliberately disable the pause guard: both the authored oracle and event-boundary invariant checks detect the bad controller. Tests separately reject unknown usage converted to zero, boolean counts, and null quality converted to zero. Usage permutations check order independence for partial fields; checkpoint restoration checks persistence without implicitly acknowledging an outage. Artifact tests disallow subprocess/network calls and verify every saved trace hash, original event list and snapshot count.

The actual commands were:

```sh
python3 -m unittest discover -s tests -p 'test_report_control.py' -v
python3 bench/report_control.py --output bench/results/context-quality-2026-09-08/controller/final
```

Both exited successfully. The CLI refuses to overwrite an existing experiment; use a fresh output directory for a new run. The full repository suite is handled by the root task after parallel edits settle and is not claimed in this record.

## Existing report compatibility replay

A separate independent script recomputed the reporting schema directly from the three saved handoff scorecards, without importing `facts()`, the controller, or any existing aggregation code. It used a one-pass outcome/safety count, a grade sum and sorted median, then compared all 20 logical fields against each previous `trial-v1` compact `answer.txt`. Mean and median were normalized to four decimals.

**3/3 existing reports matched, covering 60/60 logical fields, with 0 new model calls.** The batches contain 32, 32, and 7 observed sessions respectively. This establishes that those specific existing reports can be reproduced deterministically from their saved scorecards. Agreement with prior model answers is a compatibility result; it does not independently prove that the source scorecards or prior answers are correct. The 20 hand-authored event traces above provide the independent controller oracle.

The replay and its standalone reproduction script are preserved at `bench/results/context-quality-2026-09-08/controller/legacy-report-replay.json` and `legacy-report-replay.py`. The JSON records computed reports, prior compact answers, per-field differences (none), and source hashes. Its SHA-256 is `f731dcf111bf1f9d6601bffe8e688415a1f5625f4957de8ec49fbf550f4cd076`. It also refuses to overwrite its saved output.

## Preserved record

The [machine-readable summary](controller-results-2026-09-08.json) records all trace paths and SHA-256 hashes, source hashes, test counts, commands, and limitations. The final ignored raw artifacts are under `bench/results/context-quality-2026-09-08/controller/final/`: `contract.json`, a copied `cases.json`, `manifest.json`, and 20 trace JSON files. Each trace retains every original event, its complete expected and actual final report, all prefix snapshots, and assertion failures (none in this run).

- Source commit before these additions: `24daf4ea2d85ed6a845aa5e5c176569216ff40c5`.
- Manifest SHA-256: `0608605868404525c429d978eb9e86b47619e756872564c97ecccb4182a5efee`.
- Reducer SHA-256: `c89635e22eba04e9fc6dfd3a0a38bbcf760b044840b1d1db54b2428a9a4d5f5a`.
- Fixture SHA-256: `80bfefb02d491c3c1602eae435f9dcbe08502a1c52d54060c10294b63f2b6388`.
- Test SHA-256: `a76425ff71a22fc5bb8239409a3f7ddfcc203b792d5ee9589814555a1bcefb9f`.

The initial 20/20 run remains preserved one directory above `final/`; the final run includes the later cache-subset validation and current source/test hashes.

The result supports this finite serial-event contract. Production use still needs an adapter for real event formats and provider-error classification, plus tests of scheduling concurrency and actual notification delivery. None of those were deployed or measured here.
