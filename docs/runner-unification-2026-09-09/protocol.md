# Durable runner migration and bounded quality rerun

Status: protocol fixed before new model responses. Date: 2026-09-09.

## Question and scope

The security review at `95f7695` left older runners with inconsistent batch persistence, replay, failure stopping and model pinning. Migrate the live entrypoints to the same durable call controller and verify that a newly prepared quality A/B can finish under the hardened runtime. Preserve historical experiments; never resume their frozen plans against modified source.

This is an execution migration and a new exploratory quality regression. It is not another complete 156-call mechanism ablation, a causal estimate of the security patch's effect, or a claim of statistical quality equivalence.

## Execution contract

- Persist dispatch before each physical model invocation; retain raw output and direct usage.
- Use one attempt. Failed, unknown-usage and unresolved calls stop later dispatch. No automatic recovery or paid retry.
- Replaying an identical successful request must start zero new model calls; changed source, configuration, model, prompt or schema must reject reuse.
- Require explicit model choices and a bounded call/token plan. Check the reported-token threshold between calls; one call can cross it. This is not an invoice or subscription quota cap.
- Keep Claude paused. New live quality calls use the same requested models as the historical pilot: `gpt-5.6-terra` answers and `gpt-5.6-sol` judges, effort `low`. Requested aliases do not establish an unchanged backend revision.
- Maintain owner-only new operational artifacts. Do not publish, send messages, fetch real private documents, or touch historical raw files.

## Quality matrix

Use the existing `bench/context_quality.py` fixtures and prompts unchanged by the migration:

| Tasks | Treatments | Initial answers | Optional followups | Judges |
|---|---|---:|---:|---:|
| Four document-analysis cases | Full / summary / adaptive retrieval | 12 | At most 4 | 4 |
| Six rental next-response cases | Full history / compact handoff | 12 | 0 | 6 |
| Total | | 24 | At most 4 | 10 |

Maximum: **38 physical calls**, **900,000 reported processed tokens**, **180 seconds per call**. The first scheduled call is the canary and remains part of the matrix, not an extra test. Failure stops the run and is reported as incomplete. Do not silently change provider, model, thresholds or output directory to get around a stop.

The previous completed pilot under `bench/results/context-quality-2026-09-08/live-v1` is a historical reference. Compare matching tasks and treatments, preserving both raw judgments. Generation is stochastic and runtime/instructions may differ from the old captured snapshot; report any difference. Historical comparisons cannot identify the controller as the cause of a quality change.

## Quality interpretation

Report answer/followup cost separately from judge cost, input/output/cache subsets separately, and all physical calls once. Report required findings, critical misses, unsupported claims, contradictions, citation defects, formatting and protocol violations; do not reduce quality to a single average.

The old judge has known limitations: it may confuse evidence visible to the judge with evidence supplied to an answer, and fail to account for common skill guidance. Retain that judge for measurement continuity. Before generation, select **all 24 new answers** for a separate AI source review, split between document-analysis and rental reviewers. Supply actual available evidence, full reference truth and common instructions, but hide treatment names, costs and primary judgment labels. Evidence format may reveal a treatment; this is not guaranteed blinding or human ground truth. Keep source-review findings beside primary labels. Any additional targeted review after results are seen is explicitly post hoc. Do not overwrite primary labels with preferred judgments.

## Verification and delivery

1. Focused offline tests exercise dispatch-before-callback, restored success deduplication, pending/failed stop, unknown telemetry, request/config conflict, explicit model/budget bounds, and process cleanup.
2. Commit the tested quality runner and its shared dependencies, then freeze a new manifest including source and prepared input hashes. Legacy adapters may continue independent development while these quality-run sources remain frozen.
3. Run the matrix serially, then verify raw-event accounting, artifact hashes, controller coverage and a zero-new-call replay.
4. Run the complete offline suite once the integrated source is stable, before final delivery.
5. Commit concise results plus detailed migration/feedback design documents. Keep raw operational files private, with a verified local backup and restoration instructions.
