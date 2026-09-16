# Article review and instruction redundancy audit

2026-09-09. Read-only implementation audit at source commit `5886d26`; file sizes below describe the checkout inspected, including its built prompt pack. No model calls or core code changes were made for this audit. Proposed treatments are hypotheses, not measured improvements.

## Article access and coverage

Requested source: Eric Provencher, [Rethinking skills and prompts for GPT-6 Astra](https://x.com/pvncher/status/2095991462416490862).

- The integrating agent read the original X article in the Codex browser without logging in: introduction, Skills, AGENTS.md, decision boundaries, persistence and closing. It also visually reviewed the decorative cover, both teaching figures and the article ending.
- This independent reviewer could not fetch the original through the web text tool (403) or public oEmbed. An [English mirror](https://en.rattibha.com/thread/2095991462416490862) exposed the same apparent section sequence and linked the two original X-hosted figures. That mirror is a retrieval aid, not proof of original completeness; original coverage is established by the integrating agent's browser review.
- Figure links: [skill-description comparison](https://pbs.twimg.com/media/HRZ0MiYaIAAeAdI.jpg), [conditional document-loading comparison](https://pbs.twimg.com/media/HRZ0VrCbwAAtwtk.jpg). This reviewer located the URLs; the integrating agent supplied visual verification. The cover is decorative rather than a third teaching diagram.

The article argues that instructions accumulated to compensate for older models can become unnecessary work or restrictive rules. Keep skill descriptions narrowly triggered, load detail when relevant, reconsider fixed recipes, make confirmation boundaries proportional, and define completion. It explicitly notes that instructions useful to Sol or Luna may overconstrain Astra. The figures compare a broad database trigger with a migration-only trigger, and mandatory document reading with reading tied to the actual task. This is practitioner guidance, not a controlled ablation or proof that shorter prompts preserve quality. No underlying research paper was identified in the reviewed article.

## Independent official support

OpenAI's [current model guidance](https://developers.openai.com/api/docs/guides/latest-model) independently describes sensitivity to conflicting skill instructions, unnecessary clarification stops, verbosity and excessive testing. Its recommendations support auditing instruction scope and making completion explicit; they do not establish a universally optimal prompt length.

The locally installed [skill-creator](<(private evidence folder)) was also read as an upstream reference. It recommends precise discovery, progressive disclosure, retaining non-obvious operational invariants, and deterministic scripts when they improve reliability. This local path identifies the inspected copy, not a portable repository dependency. See also the [conversation-design source review](conversation-design-sources.md) for actual Codex/Claude clarification capabilities.

## What is currently loaded

`bench/personas.py:system_prompt` delegates to `bench/journeys.py:system_prompt`. The latter always inserts the following three files, even when `refs="none"`; that option controls only additional references.

| File | Characters | UTF-8 bytes | Loading behavior |
| --- | ---: | ---: | --- |
| `dist/prompt-pack/INSTRUCTIONS.md` | 7,927 | 8,050 | Always inserted |
| `skills/vet-flat/references/inputs.md` | 6,069 | 6,094 | Always inserted |
| `skills/vet-flat/references/onboarding.md` | 24,981 | 25,443 | Always inserted |
| **Subtotal** | **38,977** | **39,587** | Before needed references, transcript and execution notes |
| `playground/conversation-policy.md` | 4,843 | 4,847 | Also inserted by the local lab |
| `skills/vet-flat/SKILL.md` | 7,119 | 7,231 | Native skill entry; distinct from the prompt-pack path |
| `AGENTS.md` | 1,651 | 1,651 | Repository entry instructions |
| `CLAUDE.md` | 326 | 326 | Repository continuity pointer |
| `skills/vet-flat/references/session-harness.md` | 5,778 | 5,790 | Resume/change protocol |

These are exact text sizes, not token counts, billing measurements or additive totals for every host. The native skill path and the lab prompt-pack path differ. A saved prompt manifest must establish which bytes a particular call received.

## Concrete findings and candidate treatments

| Layer / location | Finding | Candidate change and retained invariant |
| --- | --- | --- |
| `bench/journeys.py:627–642` | The compact prompt pack, missing-input guidance and entire onboarding are injected together. Their clarification, evidence and fallback rules overlap. The approximately 25k-character onboarding also contains optional life-history elicitation, worked examples, a primer and FAQs. | Give each concept one canonical owner. Route onboarding sections only for onboarding, history only when the user asks to use it, and source-specific fallback instructions only when blocked. Chat-only callers must receive the needed text; unavailable file pointers are not a treatment. |
| `bench/personas.py:1207–1210` | Both chat and non-chat paths inherit the three unconditional documents; `refs="none"` does not mean a small base prompt. | Make the context policy explicit in manifests and tests. Compare native skill loading and text-only simulation separately rather than treating them as the same product. |
| `tools/persona_playground.py:configured_system`, `_prepare`; `bench/journeys.py:RUN_NOTE`; `tools/session_runner.py:run_step` | The lab repeats plain language, limited questions, internal-metadata suppression, useful progress and tool restrictions across the prompt pack, policy, run note, execution settings, final instruction and runner wrapper. | Keep one conversation policy plus a small host-capability/output-schema adapter. Do not remove host restrictions or schema validation merely because their prose is repeated. |
| `tools/persona_playground.py:_prepare` | The latest input appears in the full transcript and again as CURRENT INPUT. Explicit amendments can appear in history, the amendments block and durable state. | Test one canonical current-input placement plus structured active amendments. Preserve exact raw messages privately and current scoped changes in the decision context; distinguish intentional salience from accidental duplication. |
| `AGENTS.md:5–7`, `references/session-harness.md` | A short repository entry can trigger substantial universal reading and a full state packet during narrow maintenance. Full packets include historical evidence references and task receipts that may not affect a label edit. | Route coding conventions/security details by action; keep a minimal global privacy/authority rule. Design scoped task views only with complete active requirements and dependency closure, explicit coverage checks and access to exact source spans. Never silently truncate the authoritative packet. |
| `skills/vet-flat/SKILL.md:17–32,39–61` | The entry has a useful router, but also twelve axis summaries and detailed legal/arithmetic/fixed-form policies. Several numeric defaults repeat reference data. | Retain purpose, routing, evidence qualifiers and genuine invariants at entry; put axis procedures and maintained constants in canonical references/tool outputs. Test whether small models still load the correct material. |
| `references/inputs.md:53–66` | A copyable missing-input template asks for three documents and ends by claiming multiple checks are running. In a text-only host that closing statement is false; its fixed itinerary can dominate a much smaller user request. | Replace copied action claims with capability-conditioned examples. Never claim a tool call occurred unless the execution record supports it. |
| `references/onboarding.md`, `playground/conversation-policy.md` | Numeric question/length guidance and concrete examples help target the observed failure, but can become another mandatory itinerary. | Treat three questions as a ceiling, zero as valid, and examples as optional. Evaluate varied openings, contract-first requests and already-complete input to detect overfitting. |
| `references/budget-modes.md`, entry escalation rules | Automatic tier/worker heuristics are policy choices inherited from earlier experiments, not universal model facts. | Separate user resource limits from an experimentally selected research strategy. Preserve pauses and budget accounting while testing different effort/context strategies. |
| `session_state.py`, `session_runner.py`, durable controller, schemas | Repeated checks at different trust boundaries may look redundant in prose but prevent stale acceptance, duplicate calls, source corruption or unknown-spend retries. | Keep deterministic checks fixed across prompt ablations. Consider removing duplicate explanatory prose only after mapping which code enforces each invariant. |

The installed skill's description is longer than a minimal trigger, but it is already London-rental-specific. It is a lower-priority target than unconditional onboarding injection. Removing detail solely to minimize characters would repeat the earlier compact-quality failure.

## Current versioned ablation

The authorized native-agent study uses two instruction factors: existing versus outcome-oriented skill entry, and bulk versus routed reference loading. All four combinations are crossed with Astra/Luna, low/high effort and lite/standard/deep research depth: **48 sessions**, within the user's overall ceiling of **192 controlled native CLI invocations and a stop-before-next-call threshold of 6,000,000 direct processed tokens**. The complete factorial identifies these two entry/loading effects and their interaction within the tested model/effort/depth settings. Entry shortening bundles removal of repeated guidance with reduced procedural detail; it cannot isolate those two mechanisms. No measured result is asserted here. The candidate and component/assumption audit live in `evals/conversation-quality/skill-outcome.md` and `evals/conversation-quality/skill-component-audit.json`.

The following eight-arm design is an optional future decomposition, not the current dispatch plan. It would require an explicit allocation within the remaining budget before execution.

## Optional future decomposition

Freeze the repaired UX baseline before applying these treatments. Preserve historical prompts and raw outputs; each treatment gets an explicit ID, source commit, exact assembled-prompt hashes, fixture hashes, model, effort, host mode and tool manifest.

Use three separable instruction factors for a tractable full factorial design:

1. **Reference loading:** current full base versus intent-selected sections with deterministic coverage.
2. **Repeated policy:** current layered prose versus one canonical policy and a minimal host adapter.
3. **Procedural detail:** current detailed recipes versus concise goals/decision criteria, with the same available tools and mandatory evidence/requirement checks.

All eight combinations test both main effects and interactions. Cross them with the requested available models and supported effort levels, using the same case/repetition schedule. This establishes a full factorial for these named factors, not every possible harness feature. Test native tool mode versus chat-only mode as an explicitly named factor or a separate matched study; do not silently change capabilities while attributing differences to prompt length. Claude remains paused until the user changes that instruction.

Required cases include a vague beginner request, a complete listing, changed/conditional budgets, partial answers, postponed topics, ambiguous evidence, missing tools, a document containing hostile instructions, and resume after a long conversation. Include unfamiliar held-out cases and paired repeats; keep dynamic persona variability controlled or use fixed recorded user turns for the causal comparison.

Measure complete provider usage including input, cached input, output/reasoning where available, retrieval/controller/judge calls and failed attempts; also record latency, physical calls, document reads, question count, first useful progress and completion. Score factual requirement coverage, estimate/source qualifiers, changed-intent retention, unauthorized-action failures and conversational usefulness separately. Unknown usage stays unknown and pauses further dispatch. Deterministic interface tests and small AI-rated samples cannot prove quality equivalence.

Before dispatch, calculate the exact calls from configurations × cases × repeats, add any separately authorized judge budget, and enforce the invocation ceiling and stop-before-next-call token threshold through the durable controller (the last invocation can overshoot). Never automatically retry a failed physical call or merge results from changed prompts into the frozen baseline.
