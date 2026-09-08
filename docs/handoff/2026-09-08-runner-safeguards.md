# Persona runner recovery safeguards — 2026-09-08

No live model calls were made for this change. Claude-dependent sessions remain paused.

`bench/personas.py` now makes **one subprocess attempt per actor launch** by default.
Provider refusal, quota/rate limits, authentication failures, explicit connection
failures, and a missing CLI stop the invocation after saving its session. A Claude
`is_error` envelope also counts as failure when the CLI exits 0. The shared launcher's
nonzero/empty-output classification remains conservative. Successful replies which
merely mention rates or provider errors are not discarded or replayed.

Failures by the persona, target agent, satisfaction helper, and judge all stop the
batch. A failed satisfaction/judge call keeps the conversation's observed outcome;
its `provider_failures` explains why evaluation is incomplete. A model regrade stops
at its first provider failure, keeps the old judgment and its model attribution,
records the failure, and retains untouched cards in the scorecard. Refused or empty
conversations are not sent to a model judge.

## Resume only after the provider recovers

First inspect a bounded retry plan. The usage audit recovered **`claude-opus-5`** as
the actual target in all 64 original/fixed sessions and the successful fix2 target
turn, although the old cards stored `model: null`. Pin it explicitly for this retry:

```sh
python3 bench/personas.py --retry-failed bench/results/personas-2026-09-07-fix2 \
  --model claude-opus-5 --max-sessions 1 --dry-run
```

After recovery, the same command without `--dry-run` runs one full-session canary.
Inspect its result before increasing `--max-sessions`. Retry preserves the recorded
persona, variant, seed, agent, persona family, and model names unless the operator
explicitly supplies model overrides. The prior failed card is archived only after
the replacement session returns, so interruption during the canary leaves it intact.
Unattempted failed cards remain available for the next retry invocation.

To continue a matrix whose cards consistently record explicit model names, use its
**original** matrix, model flags, result root, and date label, plus
`--skip-existing --max-sessions 1`. Old `model: null` cards intentionally do not match
an explicitly pinned model: use the dedicated paused-session plan for these
historical batches rather than weakening the configuration check.

`--skip-existing` compares the saved agent/harness/model choices, persona family,
settings, probe, and seed. It refuses a configuration mismatch rather than silently
overwriting that card. It skips every matching saved outcome: failed conversations
use `--retry-failed`; already completed conversations with a failed judge can be
regraded without buying another conversation. It checks the current persona file's
configuration, not a historical checksum of every fixture; use the same committed
experiment inputs when resuming. The budget counts sessions started after skips.

Do not wrap these commands in a shell loop that ignores nonzero exit status (such as
the old `fix2.sh` loop). That would start a fresh invocation after the circuit breaker
stops. Use one bounded `--retry-failed` invocation and inspect its result. Exit 1 can
also mean a completed low-scoring/abandoned session, so use the saved failure details
to distinguish infrastructure failure from an experimental outcome.

`--max-sessions` applies to runs and retries, not regrades. It limits full sessions,
not tokens, dollars, internal CLI retries/tool calls, or wall time within a session.
No token/USD cap is claimed: Codex's existing plain output may not report usage, and
Claude API-equivalent USD is not the subscription's remaining allowance. A normal
persona run still invokes live models with `--rules-only`: that flag skips only its
model judge. `--regrade FOLDER --rules-only` is the offline calibration path.
Every default agent choice has a Claude dependency: Claude/chat targets use Codex
helpers, while Codex targets use Claude persona and judge helpers. Changing the
target to Codex therefore does not avoid the Claude pause and changes the experiment.

## New usage evidence

Historical `cost.usage` is retained unchanged: it sums the recorded target-agent
turns. New `usage_scope` labels that subtotal. New `cost.launches` records every actor
launch, including the persona's final `[END]` message, satisfaction, judge, and failed
calls, with family, usage, time, attempts, and provider status.

`cost.all_actor_usage_reported` sums the numeric fields actually reported by those
launches. `usage_missing_for` lists absent usage envelopes; missing is unknown, never
zero. `all_launches_reported_usage` means every launch returned a nonempty usage
object; it does **not** establish that every field (particularly USD, cache tokens,
or internal retries) was reported consistently or that the total is billable usage.
Per-call records are the source of truth for comparing like fields and providers.

`--regrade --dry-run` only prints the inspection plan; neither model-judge nor
rules-only dry runs call models or modify saved files.

Model regrades append separate `cost.regrade_launches` and
`cost.regrade_usage_reported`, including usage reported on failed calls.
`all_regrade_launches_reported_usage` has the same envelope-coverage meaning. These
are additional regrade costs, not included in the original session's actor subtotal.
Older runs cannot be backfilled from absent telemetry.

## Offline verification

The final full offline suite passed, including all **105 persona tests**. Run this
subset with `python3 -m unittest discover -s tests -p test_personas.py`.
New regressions cover a one-attempt failed subprocess, zero-exit Claude error
envelopes, failure at every actor, canary/matrix stopping, configuration-safe skips,
retry archival after replacement, interruption preservation, incomplete usage,
and regrade failure preserving old judgments and untouched scorecard rows.
