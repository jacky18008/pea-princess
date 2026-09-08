# Synthetic rental fixtures · 2026-09-08

`evals/context-quality/rental-cases.json` contains six newly authored fictional
conversation prefixes. They support the paired next-turn experiment described in
`protocol-2026-09-08.md`; they are not real rental advice or verified property data.

The setup subagent wrote each complete history, compact handoff, final user turn
and evidence-linked gold before target-model outputs existed. The histories are
not sampled production conversations, and the handoffs are not outputs of a
separately evaluated compressor. Neither these prefixes nor their invented
addresses were copied from the earlier sixteen persona cards. This jointly
authored synthetic set can test consumption of a carefully preserved state, but
cannot establish production compression accuracy or real-user satisfaction.

The authorship/review computation belongs to experiment setup, outside the live
CLI answer/judge token totals. It must not be presented as free compression or
zero-cost fixture preparation. No target calls, Claude calls, source lookups,
external messages, payments, signatures or bookings were used to create the set.

| Case | Coverage | History messages | History characters | Handoff characters |
| --- | --- | ---: | ---: | ---: |
| R1 | Exact-flat certificate mismatch, payment recipient and deadline | 10 | 4,810 | 992 |
| R2 | Conflicting repair accounts, observational limits and viewing payment | 10 | 4,917 | 1,033 |
| R3 | Completed profile, one viewing, hard desk requirement and budget margin | 10 | 4,794 | 1,037 |
| R4 | Finish a usable three-check viewing message under time/effort limits | 10 | 5,021 | 1,059 |
| R5 | Replaced budget, layout requirement, destination and quote | 10 | 4,991 | 1,015 |
| R6 | Changed access requirement, unresolved lift outage, corrected handover | 10 | 4,986 | 1,035 |

Character counts exclude JSON formatting, role labels, message IDs and the final
question. They are character counts, not model-token measurements. The final user
turn appears only in `question`, so both arms receive precisely the same next
request without a duplicated turn. Histories contain actual source excerpts,
observations, corrections and task constraints rather than unrelated background
added to inflate full-context cost.

Every history message has a stable local `U1`/`A1`-style ID. Gold references the
original history through these IDs and must be judged with the original history
and final question. The compact handoff is never the grading reference. Gold
requires useful actions and preservation of task constraints as well as
verification boundaries; safe but unhelpful refusal is not full completion.

The handoffs keep current user requirements, relevant withdrawn requirements,
document identity, source conflicts, outstanding checks and practical limits.
They also keep supplied numerical estimates and arithmetic that appeared in the
history. They do not supply a fresh PASS/KILL recommendation, an answer to the
final user question, or instructions to the judge. On-site observations, agent
claims and documents presented as official extracts are distinguished. The word
"official" is a source label within the fiction, never evidence of an actual
register check by fixture authors or the target model.

`dist/prompt-pack/INSTRUCTIONS.md` is the appropriate fixed prompt: it is the
repository's real manual distribution entry point and includes the manual digest.
`skills/vet-flat/SKILL.md` was also read during setup to check intent. Neither was
modified. The entry prompt references additional files and contains legal and
full-report instructions. The shared runner should explicitly scope this pilot
to fictional supplied evidence, unavailable references/tools, and a natural-language
next reply. It should not claim to run the entire tool-enabled skill or evaluate
current law. The gold relies on verification, stated preferences and source
consistency; none requires fresh legal research. All fixture conversation text is
English; R4's word limit is intended for an English message.

Pre-run structural validation passed for all six cases: unique case and message
IDs; ten alternating user/assistant messages per history; valid roles and severity
values; nonempty final questions outside the history; all 35 finding evidence
references resolve; histories within 4,000–9,000 characters; handoffs within
500–1,100 characters. Read-through review checked current constraints against the
handoffs, including R1's wrong-flat correction, R3's non-negotiable desk, R5's
withdrawn budget/destination/quote and R6's access and date updates. This is setup
agent review, not independent human validation.

Interpretation limits: the set is small, English-only, and intentionally uses
clear user requirements and explicit source conflicts. Helpful earlier assistant
messages are part of the authored histories. Both histories and summaries were
prepared with knowledge of the task design, so this is not a blinded real-user
holdout. Good compact-arm performance would support this controlled pilot only;
it would not establish safety of arbitrary automatic handoffs.
