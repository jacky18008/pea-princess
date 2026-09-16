Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Budget modes: the same checks at three depths

The available tools and usage allowance determine how much can be checked. Always preserve the user's requirements, the recommendation and the important unknowns. `profile.yaml: budget_mode` selects the internal depth, default `standard`; `advanced.fixed_form.questions` can override coverage using the `tiers` block of `references/fixed-questions.yaml`. Explain scope through useful consequences: “I can compare these documents now; the journey and bills still need checking.” Do not announce mode names, model roles, configuration banners or question-count codes in ordinary replies. These settings govern work, not an intake form the user must complete.

When explaining depth, say “quick initial check”, “usual checks”, or “closer review of the shortlist”. Ask about extra cost or scope only when the choice matters and is not already authorized. Use a native choice tool only when the host provides it; otherwise plain text. Prefer zero to two clarifications, with three as the upper bound, and make progress from current evidence while learning preferences.

| | `lite` | `standard` | `deep` |
|---|---|---|---|
| Who | £20 plans, chat-only users, a first quick screen | most users | £100+ plans, final shortlists, area sweeps |
| Fetches per flat (shell mode, approx.) | ≤ 8 | ≈ 15–25 | 40+ |
| Identity and area | `epc.py search --postcode "<postcode>" --brief --match "<flat or building>"` to find the flat, then `epc.py cert <certificate id>` for the matching flat (never pass an address to `cert`) | + `epc.py search` for the building's flats | + whole-building profile (`epc.py building`) and certificate history |
| Crime | `geo.py lookup "<postcode>"` for coordinates, then `crime.py box --lat <lat> --lng <lng> --months 3 --no-sensitivity` (4 calls) | 6 months, no sensitivity (6 calls) | 6 months + ±20 m sensitivity (30 calls) + route corridor |
| Commute | `commute.py journey --from "<postcode>" --to "<destination postcode>"` (postcodes work directly) | + rail and bus plans, `redundancy` | + `stations` detail and alternative arrival times |
| Company and compliance | `company.py profile` of the named entity | + `search` for same-name shells, `redress.py cmp`, `heat-trust` | + `filings`, `address-search` (RMC/RTM), `rogue`, `landregistry.py price-paid` |
| Planning | skip (state it) | `planning.py near --radius 250 --brief` | + `stages` on tall schemes, `roads.py near --brief` |
| Reviews | ask the user for the lowest reviews only | full paste, incentivised and burst filters | + Trustpilot/press, cross-building matrix |
| Report | verdict card, hard filters, 2 questions, 12 axes with U where skipped | full | full + comparison |
| The fixed form (`fixed-questions.yaml`) | the 8 gate questions, F1–F8 | + the 6 listing questions, F9–F14 | + the extended 4, F15–F18: council tax band, guarantor, referencing, furnishing and inventory |
| Area sweep | not offered; suggest `standard` | `sweep.py --radius 600 --max-buildings 6` | run several `--radius 1000` sweeps on different anchors (one per neighbourhood) with `--max-buildings 8` each; a single 3,200 m sweep trips the map service's rate limit and needs the filter caps raised |

## The escalation ladder (automatic)

Start with the ordinary checks and add effort only when a stated trigger fires, within the user's
limits and explicit configuration. Record `generated_by.tier` and `generated_by.escalation_reason`
internally. Lead the answer with the recommendation; explain extra checks in the user's language.

| Tier | Name | What runs | When |
|---|---|---|---|
| 1 | `standard` | Scripts for every fetchable fact; cheap workers only for text the user pasted; the strongest model you have doing the judging. | The default for every candidate. Always start here. |
| 2 | `breadth` | One bounded reader per reading-heavy axis — reviews, planning, press, the landlord entity, the listing, the geometry — up to six, in parallel, on the cheap model. One document in, one small JSON object out. | Only on a trigger, below. |
| 3 | `manual` / `lite` | No shell: the user pastes, the model writes, the viewer renders. `lite` is the same shape with a fetch budget of about eight calls. | Chat-only runs, and £20 plans that have to stretch one window over many flats. |

**Escalate to `breadth` when either of these is true:**
- the candidate is in the final shortlist of two or three; or
- the verdict is CONDITIONAL or EDGE **and** more than 40 % of the axes are unknown (5 or more of the 12).

**Never start at breadth.** Run tier 1 first, escalate on a trigger, and say so in
`escalation_reason` ("final shortlist of three", "CONDITIONAL with 6 of 12 axes unknown"). Breadth
buys roughly 0.55–0.70 landmine recall up to about 0.85, and costs about five times the tokens and
twice the wall time (`docs/EXPERIMENTS.md`). That is worth paying on the last two or three flats and
wasted on a flat a hard filter kills in one line.

**Splitting the roles.** Depth is one dial; who does the work is another. `references/pipeline.md` runs the same checks as four separate roles — a cheap planner that decides what to fetch and never reads a page, cheap executors that collect evidence and write no verdicts, a strong verifier that runs `scripts/verify.py` and reads only what it flagged, and an integrator that may use verified items only. Use it when the judging model is not the strongest you have, when the flat is on the final shortlist, or when the mode is `deep`. It costs more calls and more wall time; what it buys on this task is still being measured (`docs/EXPERIMENTS.md`, "Role pipeline (to be measured)"), so do not quote a number for it yet.

**Fan-out rule.** Whenever four or more subagents run at once, they use the cheap tier, whatever the
budget says. Fan-out, not depth, is what empties a subscription window: four parallel readers on the
strongest model burn more in a minute than a whole `standard` run.

**What the tier implies internally.** Tiers 1, 2 and `lite` use workers with a stronger judge;
`manual` has no workers. Preserve these details in metadata for technical review. They are not
headings or explanations to copy into the user's housing conversation.

## What never gets cut
Current requirements and their conditions · source and estimate qualifiers · important unknowns · attribution · advice against signing at the viewing when relevant · at most three essential clarifications while other work continues.

## Chat-only users on any plan
The prompt pack (`INSTRUCTIONS.md` + references) plus `viewer.html` is the lite path: the user pastes the certificate page and the listing, the agent applies the filters and writes the report JSON, the viewer renders it. No fetch budget is consumed.

## Measuring it
`bench/run.py` records wall time and tokens when the CLI reports them; run the same case in `lite` and `standard` and keep the numbers in `bench/results/`. Target for `lite` on a single flat: under ten tool calls and one report.

## How much a £20 plan actually buys (checked 2026-09-03; these change often)
## Which models
Two jobs, two different answers. Vendor names below are examples, not requirements: pick by role.

### On a £20 plan

Full tables, method, caveats and the cost/recall chart: `docs/EXPERIMENTS.md` — https://github.com/jacky18008/pea-princess/blob/main/docs/EXPERIMENTS.md

