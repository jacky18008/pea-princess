# Complete street scan and clarification regression

This follows the intent-authority ablation. It tests the actual pinned public
package through the local lab, including public-source tools, retained research,
and real clarification forms. It does not resume the earlier incomplete tool
matrix or change localhost:8765.

## Case and comparison

Use the existing private rental-history corpus, current `corpus-v2/cases-v3`.
Case 05 contains a user's evolving daylight requirement after requesting area
research. Retain its original role, source line, record UUID and raw source hash.
The new four-turn case is an **adapted development regression**, not an exact
historical replay, new holdout, or measurement of the user's present satisfaction.

1. Research one real, explicitly identified street with the standard public
   toolkit. The operator supplies an explicit initial direct-morning-sun rule,
   a quietness preference, and an official address excerpt as a local attachment.
   The initial hard daylight rule is an added test condition, not attributed to
   an unseen historical human statement. Finish useful research and show one
   optional question with choices and a free-text field.
2. Submit the retained historical daylight relaxation through the actual form's
   free-text field. Use only existing research afterward. Keep the exact question
   prefix sent by the UI; inspect whether that assistant-authored text incorrectly
   becomes new user authority.
3. Ask the historical winter-light question and whether daylight should instead
   be a preference. Explicitly request advice before deciding and two or three
   choices. Do not activate the proposal yet.
4. Select an actually offered option that makes daylight preference-only, with
   no new search/contact or unrelated constraint change. If no such option is
   offered, use the frozen free-text fallback and record fixed-choice coverage as
   missing. Never rewrite an option to manufacture a pass.

The two conditions are main `a5547f3` and its single short
`references/conversation-quality.md` change from `fdaf401`. Neither condition
contains the experimental original-message index helper. Source, ZIP and loaded
actor inventories are checked byte-for-byte; the only public member difference
must be that reference. The host implementation is identical and frozen.

Run three fresh lab sessions per condition, each with its own attachments,
conversation and research directory: at most 24 actor calls. Within a session,
each answer receives its own actual earlier answers and saved evidence. The lab
starts a fresh provider CLI per turn; this is same-lab-session continuity, not a
claim to test provider-native thread resumption.

## Limits and admission

Freeze Terra / low / standard, 300 seconds per physical call, 700,000 processed
tokens per four-turn session, and 4,000,000 across this study. These are operator
stopping bounds for the newly authorized task, not a spend target or an automatic
transfer of the earlier study's remaining budget. Cached input is already part
of input: processed = input + output. Development and evaluator usage are not
included in that actor ledger.

Dispatch serially. The coordinator permits one step, message or UI reservation
at a time. Stop after the first paid call and retain it in the matrix. Release
more work only after a cost receipt estimates six initial calls plus a 200,000
token allowance per session for its three follow-ups within the global ceiling.
If that projection does not fit, preserve the pilot and amend the scope before
another dispatch. Do not consult semantic grades to decide whether to keep a
pilot. A call may exceed a remaining inter-call budget; this is not a provider
billing cap.

Semantic failures stay in the planned repetitions; they are not replaced by
retries. Rate limits, unknown usage, physical failures and unmatched dispatches
pause the study. Reconnecting, refreshing, restarting the server or running
`report` cannot authorize another paid answer. The existing lab owns physical
call supervision and durable receipts; the new coordinator owns cross-session
admission, recorded intentions and combined accounting.

## Evidence and grading

Freeze an independent Astra rubric before dispatch. Mask condition identities
for primary grading. Keep first visible progress text separate from the final
opening, and score authority, source correctness, usefulness and interaction
burden independently. Then review the evaluator's exact quotes and judgments.

Report actual coverage of roads, railways, night venues, modelled noise, planning
and living environment, including failed/partial sources, geography and dates.
Area observations cannot establish bedroom orientation, indoor noise or daylight.
Compare raw tool paths and each scan's source identity to the pinned public
package. Later no-search turns must reuse retained observations, not re-fetch
them merely to rebuild context.

Retain the real DOM questions, exact submitted option/free text, source call,
outgoing message, subsequent call, all replies, state and research hashes.
The agent lane stores raw user instructions; it does not independently certify
normalized conditions, ranking or TODO correctness. Record absent capabilities
separately from conversational success. Full-loop results do not establish a
complete product release or performance across other models/efforts/depths.

Personal text, case adaptations, raw sources and receipts stay in ignored
`.pea-playground/full-scan-followup-acceptance-20260913/`. Reusable runner and
aggregate reports belong to this experimental branch. Preserve every planned
session in the denominator, including missing or blocked sessions.
