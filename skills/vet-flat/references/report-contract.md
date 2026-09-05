Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The report contract

`report.json` follows `report-schema.json`; this page says what a good report contains and how it reads. Both renderers (`scripts/render.py`, `viewer/viewer.html`) lay it out the same way and regenerate the attribution footer themselves.

## First line
`Configuration: <tier> — <reason or default>; workers: <cheap|strong>; judge: <model>` from `generated_by.tier` and `escalation_reason` (see `budget-modes.md`). If you did not escalate, say `standard — default`.

## What every report contains
1. **Verdict card** per candidate: PASS · EDGE (with the break-even rent) · CONDITIONAL (conditions listed) · KILL (the fatal axis named), a one-line headline, and the landmine codes as plain labels.
2. **Your must-haves versus this flat**: every hard filter from the profile with requirement, observed value, pass / fail / unknown and its evidence grade.
3. **Your questions, answered**: each entry of the profile's `my_questions`, placed at its stage — filter questions with the hard filters, vet questions under the verdict, compare questions as extra rows of the comparison table, viewing and sign questions in the checklists — with an answer, an evidence grade and whether the trigger fired. Written as `question_answers` on the candidate.
4. **Side by side** when there is more than one candidate: £ per sq ft on EPC area, crime six-month count, commute minutes and redundancy grade, management organic score and incentivised share, nearest works, landlord type, all-in monthly cost; every number carries what it means and what it is compared with.
5. **Worst resident reviews**: building, source, date, score, organic or not, a short excerpt, why it matters.
6. **Landmines** L1–L16 with a plain label and whether they are reversible.
7. **The 12 checks in detail** with an evidence chip on each finding and an unknowns list.
8. **Questions and the viewing day**: at most two killer questions drawn from `questions.md`, then the checks only the site can answer.
9. **What only you can tell**: the axes marked unknown and the things the tool cannot sense (smell, noise at night, light on the day, how the street feels), phrased as a request, not a gap; the report's own asks go in `only_you_can_tell`, and leaving it out asks the four standard ones.
10. **What we could not find**, with the search strings and the blocked sources; **sources** with retrieval times; the arithmetic check; **About this report** with the configuration line again and the footer `Generated with vet-flat <version> — <source URL>`.

## Plain-language rules (every text field)
- Short sentences. No jargon or abbreviation without a gloss the first time.
- Every number is followed by what it means and what it is compared with.
- Evidence grades appear as plain labels: official record / self-reported / third-party / inferred / unknown.
- Numbers come with a source id or a `computed_by` note; a number with neither is flagged "no source" and fails `--strict`.
- Write in the user's language; keep source labels bilingual where the glossary has them.
- Roast the listing, never the person: describe defects and evidence, not motives.

## Never
Sign on the viewing day. Treat listing area as fact. Scale crime figures for missing months. Turn a missing item into a pass. Hide a red flag. Use ethnicity or nationality as a factor.
