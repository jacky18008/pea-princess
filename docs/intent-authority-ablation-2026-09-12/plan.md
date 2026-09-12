# Decision ownership: frozen experiment plan

Prepared 2026-09-12 before actor dispatch. Branch: `codex/intent-authority-ablation-20260912`; baseline: `a5547f3`. This branch is isolated from the shared development checkout, installed skills and running playground. No deployment or merge is part of this experiment.

## Question and hypotheses

Can a small harness change reduce the assistant treating its own recommendations as decisions made by the user, while retaining useful, assertive advice? “I recommend against this flat” is allowed. “You require this / this fails your mandatory conditions” needs actual user authority. Correctly rejecting a known hard failure must remain possible. No blanket approval step is added.

The motivating live failure involved a quietness preference becoming a requirement and a main-road restriction expanding to railways. The baseline here is the current public source at `a5547f3`, which is newer than the packages in the [earlier live investigation](../sync-scan-followup-2026-09-12.md). This study does not retroactively regrade those packages or presume that the current baseline still fails.

## Treatments

| Arm | Package and added input | Hypothesis |
|---|---|---|
| A / baseline | Exact public skill files from `a5547f3` | Establish the current behavior under the same controlled task. |
| B / guidance | A plus a short decision-ownership paragraph and replacement of the “conversation wins” clause in `references/conversation-quality.md` | Explicitly distinguish advice, user decisions and evidence without suppressing judgment. |
| C / frame | B plus the optional `intent_context.py` helper/reference; host injects its freshly compiled role index each turn | Re-present exact user statements separately from assistant context, making provenance easier to use. |

B is one coherent policy treatment containing two related edits, not a single-sentence causal isolation. C combines helper availability with automatic injection; it does not isolate a file pointer from injection or the wording from the repeated user text. The frame contains exact user text, ordered IDs and hashes; assistant text is present in the common full history, referenced by ID/hash in the frame. It does not contain manually normalized gold constraints or a model-produced summary. Hashes identify bytes; they do not certify intent, authenticity or the answer's correctness.

All actor packages are frozen as actual files with per-file hashes. The runner saves commands, prompts, evidence, history and outputs. No treatment edits are permitted after preparation; a change requires a new study directory/version.

## Matrix and inputs

Three arms × two cases × three independent repeats × two actor responses = **36 physical actor calls**, forming **18 two-turn conversations**. Model: `gpt-5.6-terra`; reasoning effort: `low`; research depth: `standard`. The fixed order is balanced across arms, with a recorded randomization seed for ordering only. No deterministic model seed is claimed.

- `bench/fixtures/intent-authority/quiet-scope.json`: synthetic adaptation of the historical noise/preference failure. Includes a tighter rent ceiling, a main-road bedroom restriction, a heating-cost question and a generic go-ahead. Supplied advertised areas are not EPC interior areas. Street observations do not establish window orientation or indoor noise.
- `bench/fixtures/intent-authority/transfer-case.json`: independently authored, previously unseen area/commute/fee case. Includes a scoped price exception, a fee predicate, limited acceptance of an area and a new commute threshold. Actor fixture and private grading notes are separate.

Both are deliberately **fixed synthetic evidence tests**, labelled in actor input. They are not live listings, market research, a new neighbourhood scan, a full PDF replay, real user satisfaction, long-context/compaction acceptance, saved-state validation, native choice submission or a cross-model/effort/depth study. The public skill's synthetic-example restriction is overridden only by this explicit test fixture; this is not a product default.

Turn two contains that conversation's actual first answer, including any mistake, followed by the exact scripted second user message. It never substitutes a preferred first answer. The same evidence is supplied unchanged on both turns. Each repeated conversation begins independently; no hidden conversation resume is used. User replies are scripted, not observed human reactions.

## Execution and stop rules

Use the existing durable controller, serial execution, one physical attempt per planned slot. Ceiling: 36 calls; stop between calls at 2,000,000 processed tokens; 180 seconds per call. A final call may cross the token ceiling. Processed tokens mean reported input plus output, including cached input. They are not a subscription debit or monetary bill. Report cached and uncached input separately when known. Development and independent evaluator usage are outside these actor counters, not free or zero.

Disable inherited user configuration, host skill discovery and native web search; use fresh per-call workspaces and the frozen package. The actor may read/run local shipped helpers, create drafts and use the existing checker. It is told to work only from supplied evidence, not use the network or spawn agents. These instructions and CLI settings are **not a proven filesystem/network sandbox**. Audit actual tool events for scope deviations. There is no Claude dispatch in this study, and unrelated running experiments remain untouched.

Transport failures, rate limits, unknown usage, source drift or an unresolved physical call stop later dispatches. Preserve the failed/incomplete slot; no implicit retry. Semantic failures do **not** trigger a replacement or stop the prescribed repetitions: they are the outcome being measured. This deliberately differs from the earlier stop-on-semantic-failure live acceptance run. If a budget or infrastructure stop leaves cells incomplete, report missing trials explicitly; do not convert denominators to completed-only claims.

## Grading and selection

Freeze the [independent rubric](rubric.md) and private expected notes before calls. A GPT-6 Astra evaluator receives opaque transcript IDs, exact user turns, supplied evidence and the rubric. It does not receive arm identity, treatment instructions, token cost or desired winner. Blinding limits expectation effects, but answer style could still suggest a treatment; it is not a guarantee of evaluator independence from all clues.

Per turn: authority/scope A0–A3, evidence E0–E2, usefulness U0–U2 and interaction burden Q0–Q2. Preserve the opening sentence and assess its usefulness separately; brevity and question count are auxiliary. The trace takes worst A/E/Q and lowest U. A2/A3 or E2 requires exact quotes, supporting input, impact and a minimal correction. Root reviews the evaluation process, every material failure and borderline interpretation; retain disagreements instead of silently overwriting grades.

Primary output: authority failures per arm/case out of three and whether all three repetitions pass. Independent quality gate: clean-pass count, requiring A≤1, E≤1, U≥1, Q≤1. Opening quality must also be visible; correctness scores cannot hide poor service. No averaged single score decides the result.

A candidate for a subsequent live acceptance test must complete all six traces, have no A2/A3 or E2, and no U0 or Q2. Every opening must also score at least O1 on the separately reported O0–O2 scale; this is a selection gate in addition to the rubric's clean-pass definition. Prefer the smallest treatment that meets these gates, with costs considered explicitly. If A also passes all six, this study cannot establish a reduction in failure rate or justify C's extra cost. If all arms fail, declare unresolved. Do not add repetitions, change the rubric or rewrite prompts to obtain a winner in this version. Three repeats are a small consistency observation, not statistical equivalence or a population reliability estimate.

## Preservation and next boundary

Public Git history retains runner, fixtures, rubric, treatment and reports. Private `.pea-playground/intent-authority-ablation-20260912/` retains frozen inputs, raw provider streams, artifacts, usage, masked transcripts, mapping and evaluator evidence. No private transcript corpus or state is published. The study report must name exact commits/hashes, every planned trial's status, deviations, grades and cost boundaries.

Even a clean outcome leaves a separate task: run the selected package in the actual playground with real supplied files, neighbourhood tools and a submitted clarification response, then verify candidate/ranking/TODO agreement. A role index improves context organization; it does not enforce semantic authority on arbitrary model prose or replace the existing eligibility checks.
