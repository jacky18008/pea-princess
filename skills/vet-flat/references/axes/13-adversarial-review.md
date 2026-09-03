Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 13 — Adversarial review

## Purpose
Have a second agent attack the verdict before the user acts on it, in a format that forces every objection to be answerable.
The purpose is not to find fault; it is to make the report's weak points visible and to say exactly what would settle each one.

## The five-column objection format
Every objection is one row. A row missing any column is not an objection.

| Column | What it must contain |
|---|---|
| **Claim to challenge** | The exact sentence from the report being disputed, quoted, with the axis it sits on. |
| **Counter-evidence** | What contradicts it, with a source and an evidence class (G / S / C / I). "It feels wrong" is not counter-evidence. |
| **Severity** | CRITICAL, HIGH or MEDIUM, defined below. |
| **Recommended action** | What the main report should do: change the verdict, add a condition, add a question, re-run a query, mark U. |
| **Release evidence** | The specific evidence that would retire this objection. **An objection with no release condition is not a valid objection.** |

Add a `sources[]` list to every row.

### Severity
- **CRITICAL** — new, direct counter-evidence that removes the candidate's eligibility (for example a registered sale that contradicts the claimed building age).
- **HIGH** — a hard condition is not met and the candidate is nevertheless ranked highly.
- **MEDIUM** — a presentation or maturity problem: an unsupported adjective, a missing denominator, an unlabelled inference.

## The "not proven defects" section
Every reviewer must also file the list of things they went looking for and **did not** find wrong, with the queries used.
Without this section, a reviewer under pressure to produce findings will manufacture them. With it, the silence is evidence.

## Disposition vocabulary (the deciding agent's reply to each row)
accepted · partly accepted · accepted in full and withdrawn from the ranking · partly released · accepted with a document to follow · accepted with a limit · accepted and tracked · rejected.
Use these words and no others, so dispositions can be counted and compared between rounds.

## Time classification of corrections (E / R / N / U / J)
When correcting an earlier judgement, classify why it was wrong. This stops new rules being used to retro-score old decisions.
- **E** — an error identifiable with what was known at the time.
- **R** — the standard changed afterwards; the old judgement was right under the old rule.
- **N** — new data arrived afterwards.
- **U** — still not enough data; the finding stays unknown.
- **J** — a defensible judgement call that could have gone either way.

## Explaining a change of rank
Decompose every movement into four causes and name which applied:
candidate pool changed · rule changed · evidence corrected · weights changed.
**A number going down does not mean the flat got worse.** Say which of the four moved it.

## Freeze, then compare
1. Produce the independent version first, without reading the earlier material.
2. Record a timestamp and a content hash for every output file.
3. Only then read the earlier reports and compare.
4. Re-check the hashes after the comparison to prove nothing was edited during it.
5. Issue corrections as a **separate errata document**. **Never rewrite a frozen output.** Version files side by side; do not overwrite.

## The retrieval manifest
Log every fetch that failed, with its status: 403, 406, 410, 429, 500, an empty body, or a 200 carrying the wrong page. Record whether the raw response was kept.
- Never work around a block and describe it as a successful check.
- Never claim to have kept a raw response you did not keep.
- **A failed fetch is recorded as a failed fetch**, never as "checked, nothing found".

## Limits on the adversary
- Models from the same family share blind spots; several agents agreeing is not verification.
- A reviewer may not turn caution into permanent inaction: "more evidence would be nice" is not an objection unless it names the evidence and the decision it would change.
- A reviewer may not introduce a personal preference as a fact. Preferences belong in `profile.yaml` and are labelled as preferences.
- Objections must attach to the report's claims, not to the user's choices.

## Delivery QA gate
Before handing anything over, check mechanically for: broken internal anchors; duplicate element ids; dead local links; replacement characters from a bad encoding; the axis count per candidate (all twelve present, or an explicit U); and any candidate still flagged not-ready while appearing in a ranking.

## Fixed closing three paragraphs
Every adversarial round ends with exactly these three, in this order:
1. **What this round did** — the checks run and the sources reached.
2. **What is unfinished is not a hidden pass** — every U listed item by item, with why it is unknown and what would resolve it.
3. **What this round did not attempt** — the checks deliberately skipped, so the next round knows where to start.

## What goes into the report
The adversarial round's own artefacts do not live in `report.json`. Keep them in a separate, versioned file beside it: the five-column objection table, the not-proven list, the disposition table, the correction classes, the rank-change decomposition, the freeze hashes and the retrieval manifest.
What enters `report.json` (per `references/report-schema.json`) is only what was **adopted**:
- `candidates[].verdict` — a changed `status`, added `conditions[]`, a changed `fatal_axis` or `reason_codes[]`.
- `candidates[].landmines[]` — a new problem found by the reviewer, under its code, with `evidence_class` and `sources`.
- `candidates[].axes[].unknowns[]` — anything the reviewer showed was never actually established.
- `candidates[].axes[].finding` — corrected wording where a claim overreached its evidence.
- `not_found[]` and `blocked_sources[]` — the reviewer's failed and blocked retrievals, recorded honestly rather than as "checked, nothing found".
- `candidates[].provenance_notes` — that an adversarial round ran, on what date, and where its full record sits.
Never overwrite the frozen version to make the two agree. Publish the errata alongside it.
