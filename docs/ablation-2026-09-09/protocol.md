# Preregistered ablation study · 2026-09-09

The user authorized all three next steps and a full ablation study. This protocol,
runner, adapter, new cases, rubrics and tests are committed before live calls. No
Claude invocation is allowed; the original seven Claude confirmations stay paused.
All historical results are retained unchanged. No deployment or outside contact.

## Questions and interpretation

1. Can the tested deterministic reducer govern a real runner boundary with durable,
   correctly deduplicated progress and known/unknown usage?
2. Does a revised visibility-aware evaluator avoid previously observed access
   confusion and catch genuine source errors? Calibration is a regression check,
   not independent validation on unseen judge errors.
3. What changes when answerers consume automatic prose versus structured memory,
   with source metadata and explicit replacement metadata separately removed?
4. Which part of retrieval changes quality/cost: summary, lexical selection, model
   selection and extra invocation, known essential documents, or document length?

"Full ablation" means every cell of the declared component matrix, including the
2×2 memory metadata interaction and comparison controls, is executed and reported.
It does not mean all possible model/tool/architecture combinations or a powered
population study. All examples are new authored synthetic cases, not real customers.
The new outcomes cannot establish statistical equivalence, safety reliability, legal
accuracy, satisfaction, or a universally optimal context policy.

## A. Runner integration: offline before live

`bench/call_control.py` wraps the frozen `bench/report_control.py` reducer. Each
physical CLI call is its own reducer session; logical job, role and phase are saved
separately, so adaptive phases and batched judges are not forced into a one-agent /
one-judge quality model. The adapter persists dispatch before invoking a callback,
blocks subsequent dispatch on failure, and supports atomic checkpoint restoration.
Existing `context_quality.invoke()` guards remain in effect; old experiment source
files are not edited. The new `ablation_study.py` runner actually uses this adapter.

Offline acceptance: replay all 38 saved calls, match 669,726 tokens and phases;
duplicate delivery and restored successful calls cannot change usage or rerun a
callback. Missing direct usage remains unknown, including failed work. A stub failure
must prevent a subsequent subprocess callback. Nonfatal model-catalog stderr warnings
must not become provider failures. Optional follow-up calls can be explicitly skipped
without fabricating zero-token model calls; skipped calls remain in the plan audit.

The integration checks call boundaries after subprocess completion. This does not
measure streaming failure detection, live notification delivery or detection latency.
Serial control and a local lock are exercised, not all distributed concurrency races.

## B. Grader calibration: four old cases × two variants = 8 calls

Use the unchanged final answers/source packets for A1, A2, R3 and R5 from the
2026-09-08 run, retaining the same anonymous candidate labels. One fresh `legacy`
judge and one fresh `visible` judge per case; alternate which variant runs first.
Legacy uses the old judge rules and full reference case, without per-answer visibility.
Visible adds actual available evidence per candidate and explicit distinctions among
source access, finding omission, factual error, exact quotation and profile recital.

This is a **bundled grading-rule + visibility change**, not a visibility-only causal
estimate. Candidate identities/costs are hidden, but evidence visibility necessarily
reveals information about the input treatment. The four cases were selected because
we already know their error types: false missing-source contradictions (A1/A2),
supported translations in quote fields (A2), 40→42 threshold errors (R3), an assumed
balcony and a composite criterion dispute (R5). Assess against retained source reviews;
these are AI-reviewed development anchors, not human ground truth.

Freeze both graders now. Use the visible grader for all new cases regardless of
calibration scores. Do not tune prompts after seeing calibration, rerun until a
preferred verdict, erase old labels, or claim this proves general judge accuracy.
Retain both variants and any remaining disagreements.

## C. Rental memory: 3 cases × 2 turns × 2 repeats × 6 arms

Six arms at every case/turn/repeat:

| Arm | Representation | Source ID + exact quote | Status + supersedes links |
|---|---|---|---|
| full | Full supplied history | Source history retained | Source history retained |
| prose | Automatically produced narrative | Whatever the narrative retains | Whatever the narrative retains |
| state | Structured facts | Yes | Yes |
| state_no_sources | Same structured fact rows | Removed | Yes |
| state_no_updates | Same structured fact rows | Yes | Removed |
| state_neither | Same structured fact rows | Removed | Removed |

All four state views come from the **same generated fact rows**, with deterministic
field removal and no extra model invocation. IDs, keys, values, qualification, order
and all other fields remain fixed. No filler is added to equalize length. Thus removal
changes metadata and its token footprint; it is not an equal-token information test.
Narrative versus state is a representation/content bundle because the model can omit
different information in its two outputs; it is not a pure syntax-only comparison.

One shared live memory-generation call per case/repeat/turn produces BOTH narrative
and facts, at most 48 facts and a target of 200 English narrative words. For T1 it sees
only initial user-source messages. For T2 it sees the **full prior generated memory**
and T1's user message, never the forthcoming T2 question or gold. Existing IDs and
source quotes must be retained, updated facts get explicit replacement links, and
old values remain marked as superseded. Assistant claims are not source evidence.
Model-produced omissions and wrong citations are saved as failures, not repaired by
injecting reference facts or generating again.

This tests **metadata consumption under a common rich updater**. The updater is not
ablated: it still has the full prior prose/facts/metadata. It is not a measurement of
source-free or replacement-free end-to-end compressors. `state_no_updates` removes
explicit metadata, not the actual update operation. Row order and scalar content may
still allow an answerer to infer recency; this is a legitimate compensating pathway.

Each arm answers T1, then retains its own immediately previous answer separately for
T2. It is labelled as prior assistant output, not source truth. Full sees initial
history + T1 user update + its own prior answer; compressed arms see updated memory
+ their own prior answer. Everyone gets the identical T2 user message. This measures
two-turn behavior and some self-answer carryover, not arbitrary history compaction.
S1 T2 refers back to T1 requirements without restating numeric thresholds.

All answers see identical fixed manual entry guidance, English response rules, no
tools/external facts, and the same requested scalar keys. Expected scalar values and
rubrics never reach answerers/generators. A scalar field can be correct while prose
is wrong; the judge must check consistency. Source, memory and scalar checks are
reported separately from semantic quality.

Exactly five always-applicable criteria per turn, with critical criteria defined
before outputs. New positive controls require supported progression when access or
verification gaps are genuinely resolved. Always holding cannot pass every case.
The three cases are not independent population samples; the two stochastic repeats
share fixtures and are reported as repeats, not six independent real users.

Calls: **72 answers + 12 shared memory generations/updates + 12 judges = 96**.
Within each turn, arm order and anonymous judge order are independently seeded and
saved. The same model/effort is used across arms. No replicate is selected or discarded.

## D. Retrieval: 3 case types × 2 lengths × 6 arms

Cases: a supported narrow approval, a concrete rejection, and insufficient evidence.
Each has four source documents in nested short/long variants, the same decisive
evidence, question, five required findings and reference scalar checks. Long versions
add distinct operational context, not repeated padding or new decision-changing facts.
Essential evidence fits within two documents. Document IDs/titles/order remain fixed;
this length treatment does not independently randomize needle position or distractors.
Two lengths and one sample per cell do not estimate a general crossover curve.

| Arm | Documents supplied | Extra model steps |
|---|---|---|
| raw_full | All four, no generated summary | None |
| full | All four + shared automatic summary | Summary generation |
| summary | Shared summary + catalog only | Summary generation |
| lexical | Shared summary + lexical ranker's top two | Summary generation; ranker is Python |
| adaptive | Summary/catalog, then at most two chosen docs | Summary generation; optional one follow-up CLI call |
| oracle | Summary + preregistered essential document IDs | Summary generation; oracle IDs are not discovered |

One summary-generation call per case/length sees full documents but no question or
gold; target <=180 English words, neutral factual overview. The output is frozen for
all consumer arms, even if it accidentally loses or invents a fact. `raw_full` has an
empty summary slot and does not consume or get charged for this generator. Comparing
raw_full/full exposes the effect and cost of adding a redundant generated summary.

Lexical retrieval uses the frozen question/text/title TF-IDF-style score, two results,
deterministic document-ID tie breaks, no embeddings/model/gold. Save every score and
selection. Adaptive can answer immediately, or request one/two IDs followed by exactly
one new CLI invocation with the selected documents and first response. Both invocations
are counted; no invalid ID can open a file or earn another retrieval round. Oracle is
a diagnostic selection control with privileged document IDs; never recommend it as
a deployable system or evidence that the actual retriever already finds those sources.

Gold/expected values are absent from summary and answer prompts. All answer arms use
the same JSON/fact-key contract and Traditional Chinese answer rules. Exact quotations
are checked only against actually supplied documents/summary. Judge sees full reference
truth plus each candidate's actual evidence, with group/cost labels omitted.
Short/long order alternates by case; arm/judge order is seeded within case/length.

Maximum calls: **36 final answers + 6 summaries + 6 optional retrieval follow-ups
+ 6 judges = 54**. Zero model retrieval is a real outcome, not grounds to force a call.

## Measurements, causal contrasts and decision gates

Primary descriptive outcomes: required-finding coverage, critical omissions, false
approval/refusal, unsupported material claims, scalar correctness, exact-quote
membership, useful next step and actual processed tokens. Preserve per-case/per-turn/
per-repeat outcomes; do not let a mean hide a new critical failure.

Memory factorial contrasts are paired on the same case/turn/repeat:

- Source effect: average of state−state_no_sources and state_no_updates−state_neither.
- Replacement-metadata effect: average of state−state_no_updates and
  state_no_sources−state_neither.
- Interaction: state−state_no_sources−state_no_updates+state_neither.

Compute these for finding coverage and answer tokens; display critical errors
separately. Report repeat disagreement and T1→T2 patterns. Do not treat the repeated
turns as independent observations to manufacture narrow confidence intervals.

Retrieval contrasts: raw_full/full (summary addition), full/summary (document removal),
summary/lexical (fixed retrieval), lexical/oracle (selection headroom), adaptive/oracle
(chosen sources plus extra-call cost), and short/long within each arm. These mechanisms
are coupled where the protocol states so; an adaptive/oracle difference is not solely
the number of calls. Report actual requested/selected IDs and failures to retrieve.

Pilot adoption gate, declared before outputs: an implementable candidate should save
at least **10% standalone pipeline processed tokens** against full rental history or
raw_full retrieval, have no new paired critical omission, no worse overall scalar
correctness, and no increase in source-reviewed unsupported consequential claims.
Passing this small gate is a reason for further limited validation, not certification.
Oracle cannot be adopted. If all candidates fail the gate, that is the result.
No quality failure triggers extra generations or excluded cases.

## Accounting and operating bounds

Maximum **158 CLI calls** = 8 calibration + 96 rental + 54 retrieval; stop before
starting another call after **4,200,000 reported processed tokens**. The token threshold
is checked between calls and may be exceeded by the final in-flight call; not a hard
financial spend cap. Timeout240 seconds per call. Sequential execution, no automatic
retry, no quota-reset consumption, no model substitution, no Claude calls.

All model roles use explicit `gpt-5.6-terra` for answers/generation and
`gpt-5.6-sol` for judges/calibration, effort `low`, through the existing Codex CLI.
These are recorded requested model IDs, not independently attested internal revisions.
Each fresh CLI invocation retains command, prompt, schema, raw JSONL, stderr, output,
direct terminal usage and hashes. First provider failure, missing usage, malformed
events, timeout or unexpected native tool blocks subsequent dispatch and preserves
the result. Interrupted/orphan invocations stay unknown, not silently absent or zero.
An interrupted in-flight checkpoint cannot automatically start the same call again.

Processed = direct terminal input + output. Cache is an input subset, reasoning is
an output subset, neither is counted again. Actual study usage counts each shared
generation exactly once, including calibration/judges. Standalone arm pipeline cost
charges that arm every required generation/update once per case/replicate; T2 does
not count the initial generation twice. Arm totals share dependencies and **must not
be summed into actual study usage**. The joint prose+facts generator is charged in
full to either standalone arm; this is conservative for a specialized pure-prose
compressor and does not measure its separately optimized production cost.

The parent conversation, fixture authors, code review and post-hoc agent source review
are outside measured CLI totals. Offline compute is separate. Report this explicitly;
no claim about invoices or subscription quota can be made from processed counts.

## Validation and preservation

Offline tests cover real dispatch guard, known failed work, unknown/orphan usage,
optional skips, fixture/source IDs, future/gold isolation, exact scalar checks,
deterministic field ablation, selection scope and shared-dependency accounting.
Run the appropriate full offline suite before the live freeze, with logs preserved.
Freeze source and copied packets by SHA-256 and commit. Once live outputs exist,
do not modify generators, answer/grader prompts, cases, rubric or ranker for this run.

Preserve all cells, raw primary judgments and separately named source reviews. Prepare
results tables, ablation contrasts, per-case failure analysis, source/memory artifacts,
reproduction scripts, original-file integrity checks, commits and a verified local
Git bundle/raw-artifact archive. Calibration-known cases remain separate from new cases.

This design follows the task-specific criteria, mixed automated/semantic checks,
edge-case coverage and evaluator-bias cautions in
[OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
Human validation remains absent; source-grounded agent review is labelled accordingly.

```sh
python3 bench/ablation_study.py prepare --output bench/results/ablation-2026-09-09/live-v1
python3 -u bench/ablation_study.py run --output bench/results/ablation-2026-09-09/live-v1
```

`prepare` and `summarize` are offline; `run` invokes the models within the frozen bounds.
