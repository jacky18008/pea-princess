# Scanner lifecycle and user-intent reliability

This is a new remediation version on `codex/scan-intent-reliability-20260913`, based on `6ad0250`. The earlier full-scan study, including its timeout and unknown usage, stays unchanged. It is not resumed or replaced by these checks.

## Questions and implementation

1. Can a slow or interrupted source leave an apparently running scan forever? Add whole-scan and per-source deadlines, source checkpoints, cancellation of owned fetches and lock-based recovery. Preserve completed evidence; an incomplete scan must never call itself complete. Loss of the observer, source failure and producer death are distinct events.
2. Can model advice become a user-authorized hard condition? Keep model question prefixes separate from actual selected/free-text answers. Derive a bounded condition frame from host-owned user messages, bind it to the full conversation revision, require matching response metadata and reject recognized contradictions before publication. The development grammar covers quietness and daylight; it does not certify arbitrary natural language, source truth, rankings or TODOs.
3. Can input changes or replay corrupt that authority? Reject answers superseded by new input; preserve discarded output and usage without automatic repair. Validate historical clicks against their original saved controls, including when replaying a replay whose new model asked different questions.

The downloaded public package contains the reusable checker and integration contract. Enforcement in this test is implemented by the lab host. A skill file alone does not install enforced hooks in Codex, Claude Code or Grok.

## Offline acceptance

Inject stalled sources, missing producer leases, interrupted fetches and slow checkpoint writes. Check partial preservation, terminal status, no hidden retry, and no late overwrite. Test positive and negative condition changes, advice without adoption, actual form inputs, forged/stale receipts, stale model responses, replay and restart. Use the real controller with mock model receipts. Passing these tests is not a new model-quality result.

Run the full Python suite and the browser functional suites. Independently review the implementation; retain and repair reproduced defects. Freeze the final code, public ZIP and runtime before actor dispatch.

## Small Terra verification

Use Terra (`gpt-5.6-terra`), low reasoning effort, standard research depth, and agent output. Three independently created four-turn conversations are planned:

| Case | Evidence acquisition | What it can establish |
|---|---|---|
| Live 1 | One new standard sweep of a deliberately selected real street | Actual source execution, saved progress and subsequent conversation |
| Cached 1 | Explicitly supplied, frozen prior real scan result | Repeated dialogue/intent behavior with unchanged source evidence |
| Cached 2 | The same frozen prior real scan result | Another independent dialogue/intent sample |

Each conversation starts with quietness as a preference and morning direct sunlight as mandatory, then relaxes sunlight through the real free-text form, asks for advice without adopting a change, and selects an actually offered self-contained daylight-as-bonus option. Do not manufacture an option if the model did not offer one. The cached cases must not be described as new scans or current-source confirmations; inspect traces for unexpected network work.

The source case, exact turn text, selected attachment bytes, source/runtime hashes and per-case limits are retained in the private frozen plan. This is a development regression, not an unseen holdout or statistical proof of reliability. The first live scan and the cached repetitions answer different questions.

The operator-selected stop boundary is **12 physical actor calls and 1,200,000 known processed tokens**, with a separate new ledger. The live case allowance is 650,000; cached cases 275,000 each. These are task execution bounds, not numbers quoted from the user. They are checked between calls, so one call can exceed the remaining allowance. Unknown usage, rate limits or a timeout stop new dispatch; missing counts never become zero. Preserve failed or rejected output and do not silently retry, repair with another model call or replace a failed cell. Claude remains paused. Evaluator/development usage is separate from actor receipts.

After execution, review the complete dialogue, actual selected answers, source results and tool receipts. Check both useful conversational progress and faithful condition strength; matching metadata alone is insufficient. GPT-6 Astra provides an independent evaluation and root reviews its process and findings. Report completed, rejected, failed and unrun cells separately.

No claim about the historical timeout's network cause follows from new successful tests. Do not promote to the main test service merely because the source compiles; retain an explicit version/deployment record.
