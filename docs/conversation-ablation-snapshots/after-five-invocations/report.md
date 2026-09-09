# Conversation ablation aggregate

**Incomplete** snapshot; 5 of 192 CLI invocation slots dispatched. Underlying provider requests: unknown.

Observed processed tokens: **unknown**; known input/output subtotal: 1,073,081. Input includes cached input; cached tokens are not added again.

| Input | Cached input (subset) | Noncached input | Output | Started command events | Completed command events |
| ---: | ---: | ---: | ---: | ---: | ---: |
| unknown | unknown | unknown | unknown | 59 | 59 |

Missing input/output counters: 1 / 1 dispatched invocations. Successful receipts awaiting local settlement: 0.

## Costs by condition

Prefix = T1–3; extension = T4–9 only; long-session total = T1–9. Long-session totals overlap the other rows. Judge costs are separate.

| Segment | Model | Effort | Depth | Arm | Dispatched / planned | Processed | Known subtotal | Command completions |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| extension_turns_4_9 | gpt-5.6-luna | low | standard | existing-bulk | 0 / 6 | 0 | 0 | 0 |
| extension_turns_4_9 | gpt-5.6-luna | low | standard | outcome-routed | 0 / 6 | 0 | 0 | 0 |
| extension_turns_4_9 | gpt-6-astra | low | standard | existing-bulk | 0 / 6 | 0 | 0 | 0 |
| extension_turns_4_9 | gpt-6-astra | low | standard | outcome-routed | 0 / 6 | 0 | 0 | 0 |
| long_session_turns_1_9 | gpt-5.6-luna | low | standard | existing-bulk | 0 / 9 | 0 | 0 | 0 |
| long_session_turns_1_9 | gpt-5.6-luna | low | standard | outcome-routed | 0 / 9 | 0 | 0 | 0 |
| long_session_turns_1_9 | gpt-6-astra | low | standard | existing-bulk | 0 / 9 | 0 | 0 | 0 |
| long_session_turns_1_9 | gpt-6-astra | low | standard | outcome-routed | 0 / 9 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | deep | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | deep | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | deep | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | deep | outcome-routed | 1 / 3 | unknown | 0 | 10 |
| prefix_turns_1_3 | gpt-5.6-luna | high | lite | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | lite | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | lite | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | lite | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | standard | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | standard | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | standard | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | high | standard | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | deep | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | deep | existing-routed | 1 / 3 | 164,221 | 164,221 | 11 |
| prefix_turns_1_3 | gpt-5.6-luna | low | deep | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | deep | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | lite | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | lite | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | lite | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | lite | outcome-routed | 1 / 3 | 196,350 | 196,350 | 7 |
| prefix_turns_1_3 | gpt-5.6-luna | low | standard | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | standard | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | standard | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-5.6-luna | low | standard | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | deep | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | deep | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | deep | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | deep | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | lite | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | lite | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | lite | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | lite | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | standard | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | standard | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | standard | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | high | standard | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | deep | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | deep | existing-routed | 1 / 3 | 345,612 | 345,612 | 11 |
| prefix_turns_1_3 | gpt-6-astra | low | deep | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | deep | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | lite | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | lite | existing-routed | 1 / 3 | 366,898 | 366,898 | 20 |
| prefix_turns_1_3 | gpt-6-astra | low | lite | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | lite | outcome-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | standard | existing-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | standard | existing-routed | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | standard | outcome-bulk | 0 / 3 | 0 | 0 | 0 |
| prefix_turns_1_3 | gpt-6-astra | low | standard | outcome-routed | 0 / 3 | 0 | 0 | 0 |

Judge processed tokens: 0 (0 dispatched invocations).

## Existing judge scores

0 / 24 planned pairs graded. Scores come only from conversation_grading.summarize; this report does not evaluate text.

| Segment | Graded sessions | Quality index mean | Safe success / failure / unknown | First useful turn |
| --- | ---: | ---: | --- | --- |
| common_prefix | 0 | unknown | 0 / 0 / 0 | unknown (not collected) |
| continuation | 0 | unknown | 0 / 0 / 0 | unknown (not collected) |

Condition-level scores and available descriptive matched contrasts are in report.json. Missing judgments and null scores are not zeros.

## Limits

- Incomplete or unpaired observations cannot establish treatment effects; available contrasts are descriptive.
- One authored scenario per condition (n=1); no population equivalence, confidence intervals or real human-satisfaction claim.
- Entry changes bundle deduplication with procedural changes. Diagonal judge pairing can affect cross-pair score comparisons.
- Native tools ran in fresh ephemeral invocations with message replay and a T6 file-resume challenge; native persistent continuation/compaction was not tested.
- Input includes cached input. Processed tokens are input plus output, not a monetary bill or a subscription rate-limit calculation.
- CLI dispatches and launcher attempts are separate from underlying provider requests, whose count is unknown.
- Extension cost is T4–9 only; nine-turn totals also include T1–3 and must not be added to the other cost segments.
- First useful turn is not collected by the current rubric and remains unknown; no semantic scoring is performed here.
- Structural/hash validation does not establish source truth or judge correctness. No private quotations or rationale are included.

Frozen plan hash: `1e17aef4191a439ef6e227058371b0bd29cdd6800de552b18784c163ad9803ad`. Controller snapshot hash: `34f9f8868fb0a9ad9d3bb313b617b0f294e175720e20b4437745360b5db70d12`.
