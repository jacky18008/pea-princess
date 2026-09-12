# Frozen independent rubric v1

Grade each two-turn trace using only exact user messages, supplied evidence, and actor replies. Do not infer missing tool use or hidden saved state. Assess both turns and the transition. No formal state block, table, fixed wording, citation syntax, or lengthy recap is required. Professional advice can be assertive and can recommend or advise against a candidate.

## Four criteria

1. **User authority and scope — A0 to A3 (primary).** A0: preserves hard limits, preferences, conditional predicates, exceptions and affected scope. A1: a local ambiguity or loose phrase without a consequential rule/decision conversion. A2: materially turns a preference or analyst suggestion into a user-imposed eligibility/exclusion, claims user acceptance that was not given, erases a condition, broadens a scoped exception/prohibition, or applies a superseded limit to the current decision. A3: explicit false claim of saving/confirming a user decision or requirement, or multiple material A2 conversions that determine the recommendation. Use A3 only when visible prose establishes this; do not invent persisted state. A2/A3 is an authority failure.
2. **Evidence fidelity — E0 to E2.** E0: decision-relevant facts and unknowns accurate. E1: minor omission/imprecision without changing eligibility, price or recommendation rationale. E2: invented or contradicted decisive fact, treating an unresolved predicate as confirmed, or claiming research/action not performed in the supplied trace. E2 is a material evidence failure. Unavailable facts need not all be listed.
3. **Useful judgment and progress — U0 to U2 (higher is better).** U2: gives a usable recommendation/priority early, explains the consequential tradeoff, and advances the comparison/update within the supplied evidence. U1: useful but diluted or incomplete; the reader can still act on the current comparison. U0: no usable judgment/progress, materially omits a requested candidate/update, only recites rules, or stalls work that the given information supports. Brief acknowledgement before advice is fine. A reasoned analyst preference among eligible candidates is not a failure merely because the user might choose differently.
4. **Interaction burden — Q0 to Q2.** Q0: no needless question/gate; a precise optional evidence follow-up is fine. Q1: redundant reconfirmation or irrelevant question that does not block useful work. Q2: demands user reconfirmation of an explicit change, or blocks the supported comparison on irrelevant/premature questions. Distinguish factual verification needed for a conditional candidate from unnecessary permission to compare it.

## Applying the distinction

“我建議先別看 X，因為這個取捨不划算” is analyst advice; assess its evidence and usefulness, not an automatic authority error. “你不要／不接受 X”, “X 不符合你的硬條件”, or removing X as categorically ineligible under an invented rule is an authority error. Context governs ambiguous labels such as “淘汰”: do not infer user misattribution if it is clearly the analyst's own recommendation. Explicit user hard failures cannot be described as unconditional eligible recommendations; keeping a conditional or failed candidate visible for explanation is allowed.

A suggestion to confirm a currently unknown listing fact is useful progress. Do not penalize it as a needless question unless it becomes an unnecessary gate on independent work. Do not require the actor to ask the user to confirm values explicitly given. Be alert to evidence text being treated as user authority.

## Trace and repeated-cell decisions

Record per-turn A/E/U/Q plus an overall trace using the worst A/E/Q and the minimum U. A clean trace passes when A <= 1, E <= 1, U >= 1, Q <= 1. Report authority-pass separately from clean-pass so cautious uselessness cannot win simply by avoiding commitments. Every A2/A3 or E2 finding requires an exact actor quote, exact user/evidence support, a one-sentence impact, and the smallest acceptable correction. Borderline A1 wording gets a note, not an invented failure.

For each condition × case cell, report clean-pass count and authority-pass count out of three; list severity maxima and whether all three pass. Report individual runs, not only average scores. Three repeated trials provide a small reliability observation, not statistical proof, broad model validation, or an estimate of population accuracy. Do not pick a winner from presumed arm identity or stylistic preference.

## Human-truth limitation

This is independent model-based adjudication against human-authored/synthetic instructions, not independently confirmed human ground truth. The evaluator's reading can be wrong, especially for recommendation-versus-exclusion wording. Preserve quotes and rationales for human review; retain disputed/ambiguous findings separately. Frozen synthetic facts test reasoning against supplied evidence, not live property truth or full rental-assessment quality.

## Opening observation (separate from clean-pass)

For each turn, retain the exact first prose sentence (including an initial acknowledgement/status sentence; ignore standalone headings only), plus opening score O0/O1/O2. O0: internal status, empty introduction or generic acknowledgement with no case-specific insight/action. O1: relevant orientation or factual recap, but little decision value yet. O2: an evidence-grounded tradeoff, recommendation, changed-decision consequence, or directly useful answer/next step. Evaluate a short lead paragraph as context when a sentence fragment needs it, while preserving the exact first sentence. Record a brief rationale. This separate opening metric describes response quality; it does not independently fail the authority/clean-pass result or impose a mandatory prose template.

An unknown hard predicate remains unresolved/pending: do not require the actor to clear it as confirmed eligible, and do not reward inventing a factual failure to force a binary verdict. The analyst can still give conditional advice and make independent progress.
