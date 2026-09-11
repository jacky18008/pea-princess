Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The report contract

`report.json` follows `report-schema.json`; this page says what a good report contains and how it reads. Both renderers (`scripts/render.py`, `viewer/viewer.html`) lay it out the same way and regenerate the attribution footer themselves.

## Lead with the decision
Start with what the user should do and the main reason. Keep execution settings in `generated_by` for traceability; do not copy them into conversation headings or prose. Explain meaningful scope in ordinary words, such as “I checked the supplied listing; the journey time still needs checking.” Technical settings belong in an optional technical view, not the opening answer.

## What every report contains
1. **Verdict card** per candidate: PASS · EDGE (with the break-even rent) · CONDITIONAL (conditions listed) · KILL (the fatal axis named), a one-line headline, and the landmine codes as plain labels.
2. **Your must-haves versus this flat**: every hard filter from the profile with requirement, observed value, pass / fail / unknown and its evidence grade.
3. **The questions we always answer**: the fixed questions of `fixed-questions.yaml` that this run owes an answer to, in order, with a state each: found (the sentence quoted and the source named), asked (you asked the user, source `user`), unknown (no quote, no number, and the reader is told what it costs not to know). Gate F1-F8 for every flat; listing F9-F14 and extended F15-F18 whenever a page, an email or a contract was pasted; how many by budget mode (lite 8, standard 14, deep 18), and the `tiers` block of that file is the only place that mapping lives. Answering more than the tier asks for is welcome. Written as `fixed_answers` on the candidate, drawn in its three groups.
4. **Your questions, answered**: each entry of the profile's `my_questions`, placed at its stage — filter questions with the hard filters, vet questions under the verdict, compare questions as extra rows of the comparison table, viewing and sign questions in the checklists — with an answer, an evidence grade and whether the trigger fired. Written as `question_answers` on the candidate.
5. **Side by side** when there is more than one candidate: £ per sq ft on EPC area, crime six-month count, commute minutes and redundancy grade, management organic score and incentivised share, nearest works, landlord type, total monthly cost; every number carries what it means and what it is compared with.
6. **Worst resident reviews**: building, source, date, score, organic or not, a short excerpt, why it matters.
7. **Landmines** L1–L16 with a plain label and whether they are reversible.
8. **The 12 checks in detail** with an evidence chip on each finding and an unknowns list.
9. **Questions and the viewing day**: at most two killer questions drawn from `questions.md`, then the checks only the site can answer.
10. **What only you can tell**: the axes marked unknown and the things the tool cannot sense (smell, noise at night, light on the day, how the street feels), phrased as a request, not a gap; the report's own asks go in `only_you_can_tell`, and leaving it out asks the four standard ones.
11. **What we could not find**, with the search strings and the blocked sources; **sources** with retrieval times; the arithmetic check; **About this report** with the scope of checks in plain words and the footer `Generated with pea-princess <version> — <source URL>`.

## The fixed form
found = quote+source · asked = user said it · unknown = no quote, no number. How many: lite 8 · standard 14 · deep 18; `advanced.fixed_form` overrides. Gate (ask if missing): F1 deposit cap 5/6 weeks · F2 holding (1 wk) · F3 advance (see scope) · F4 tenancy/licence · F5 landlord · F6 deposit scheme · F7 redress+CMP · F8 council licence. Listing (if pasted): F9 area+source · F10 EPC letter · F11 bills · F12 min term · F13 break clause · F14 move-in. Extended: F15 tax band · F16 guarantor · F17 referencing · F18 furnished/inventory.

## Plain-language rules (every text field)
- Short sentences. Say “total monthly cost” / “每月總花費（房租加帳單）”. Do not expose mode names, field names, file paths or execution banners unless the user asks about implementation.
- Every number is followed by what it means and what it is compared with.
- Evidence grades appear as plain labels: official record / self-reported / third-party / inferred / unknown.
- Keep the source and its uncertainty beside each finding, including short table cells and checkmarks. “Landlord estimate: 20 min; not checked” cannot become “Commute 20 min ✓”. A number below a limit permits a qualified comparison, not a confirmed pass when the evidence is only an unverified estimate. Official journey-planner output is still a prediction for its stated route and time, not a guarantee.
- Numbers come with a source id or a `computed_by` note; a number with neither is flagged "no source" and fails `--strict`.
- Write in the user's language; keep source labels bilingual where the glossary has them.
- Roast the listing, never the person: describe defects and evidence, not motives.

## Never
Sign on the viewing day. Treat listing area as fact. Scale crime figures for missing months. Turn a missing item into a pass. Hide a red flag. Use ethnicity or nationality as a factor.

## When four roles wrote it
A report can be produced by one agent or by the role pipeline in `pipeline.md`. The same contract applies. The integrator may use verified items only: an item the verifier did not pass is **unknown** in the report, with the consequence of that gap stated. A verifier pass permits use of the checked claim; it does not upgrade its source class, remove “estimated”, or prove factual truth or a hard-filter pass. Checking that a quote appears in a source validates attribution, not the source's accuracy. Numbers cite the evidence item ids in `sources` and `computed_by`. Keep role and tier details in metadata.
