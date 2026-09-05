Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Budget modes: the same checks at three depths

People on a £20-a-month plan share usage caps and smaller sandboxes; people with no tools at all paste pages by hand. The skill must still give them the basic functions: hard filters, a verdict, and the two killer questions. `profile.yaml: budget_mode` selects the depth. Default `standard`. The agent states the mode on the first line of the report and lists what was skipped. Depth also moves on its own during a run: see "The escalation ladder" below.

| | `lite` | `standard` | `deep` |
|---|---|---|---|
| Who | £20 plans, chat-only users, a first quick screen | most users | £100+ plans, final shortlists, area sweeps |
| Fetches per flat (shell mode, approx.) | ≤ 8 | ≈ 15–25 | 40+ |
| Identity and area | `epc.py search --postcode "<postcode>"` to list the flats, then `epc.py cert <certificate id>` for the matching flat (never pass an address to `cert`) | + `epc.py search` for the building's flats | + whole-building profile (`epc.py building`) and certificate history |
| Crime | `geo.py lookup "<postcode>"` for coordinates, then `crime.py box --lat <lat> --lng <lng> --months 3 --no-sensitivity` (4 calls) | 6 months, no sensitivity (6 calls) | 6 months + ±20 m sensitivity (30 calls) + route corridor |
| Commute | `commute.py journey --from "<postcode>" --to "<destination postcode>"` (postcodes work directly) | + rail and bus plans, `redundancy` | + `stations` detail and alternative arrival times |
| Company and compliance | `company.py profile` of the named entity | + `search` for same-name shells, `redress.py cmp`, `heat-trust` | + `filings`, `address-search` (RMC/RTM), `rogue`, `landregistry.py price-paid` |
| Planning | skip (state it) | `planning.py near --radius 250 --limit 20` | + `stages` on tall schemes, `roads.py near` |
| Reviews | ask the user for the lowest reviews only | full paste, incentivised and burst filters | + Trustpilot/press, cross-building matrix |
| Report | verdict card, hard filters, 2 questions, 12 axes with U where skipped | full | full + comparison |
| Area sweep | not offered; suggest `standard` | `sweep.py --radius 600 --max-buildings 6` | run several `--radius 1000` sweeps on different anchors (one per neighbourhood) with `--max-buildings 8` each; a single 3,200 m sweep trips the map service's rate limit and needs the filter caps raised |

## The escalation ladder (automatic)

Depth is not chosen up front. Every candidate starts at tier 1, and moves up only when a stated
trigger fires. Record where you ended up in the report: `generated_by.tier` and
`generated_by.escalation_reason`. Both renderers print them as the first line under the title, so the
reader can see how much machine was behind the words before reading a single finding.

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

**Fan-out rule.** Whenever four or more subagents run at once, they use the cheap tier, whatever the
budget says. Fan-out, not depth, is what empties a subscription window: four parallel readers on the
strongest model burn more in a minute than a whole `standard` run.

**What the tier implies.** Tiers 1, 2 and `lite` run cheap workers with a strong judge; `manual` runs
no workers at all. The renderers print `Configuration: <tier> — <reason or "default">; workers:
<cheap|strong>; judge: <model_name>` under the title and again in "About this report". A report with no
`tier` prints "not stated", which is itself a finding about the report.

## What never gets cut
Hard filters from the profile · evidence grades · the "not found" table · the attribution footer · "never sign on the viewing day" · asking the user once, in one list, for what cannot be fetched.

## Chat-only users on any plan
The prompt pack (`INSTRUCTIONS.md` + references) plus `viewer.html` is the lite path: the user pastes the certificate page and the listing, the agent applies the filters and writes the report JSON, the viewer renders it. No fetch budget is consumed.

## Measuring it
`bench/run.py` records wall time and tokens when the CLI reports them; run the same case in `lite` and `standard` and keep the numbers in `bench/results/`. Target for `lite` on a single flat: under ten tool calls and one report.

## How much a £20 plan actually buys (checked 2026-09-03; these change often)
- **ChatGPT Plus → Codex** is the only £20 plan that publishes numbers: 10–100 messages per 5-hour window on the largest model, 250–2,000 on the smallest, plus a credit rate card. A `lite` run is one message, so tens of flats per window on the large model and hundreds on the small one; an undisclosed weekly cap sits behind that.
- **Claude Pro → Claude Code / Cowork** publishes no number ("at least 5× free"); one pool is shared with chat; the default model is the mid-size one and the largest is credits-only. Use `lite`, and split sweeps into ≤ 600 m runs.
- **Google AI Pro → Antigravity** publishes no number ("generous, refreshed every five hours until the weekly limit"). Gemini CLI needs an API key.
- **xAI** has no £20 tier; SuperGrok shows usage as a percentage of an unpublished allowance.
- **Pay-as-you-go is cheap per flat**: at list API prices a `lite` run costs a few pence and a sweep well under £1 on any vendor's mid-size model. If a plan's windows get in the way, an API key on a cheap model is the predictable route for batch sweeps.

## Which models
Two jobs, two different answers. Vendor names below are examples, not requirements: pick by role.

- **Extraction workers** — pull one stated number or fact out of one document (a saved reviews page, a planning officer's report, a tariff page, a certificate, a raw journey JSON). Use **the cheapest model that passes the worker eval** (`bench/ab/worker_eval.py`: fifteen tasks, exact match, no tools). A mid-tier model scored 15/15 on that eval at 42% of the cost of the top-tier model, which scored 14/15. Paying more here buys nothing.
- **Judgment** — the main loop: deciding what the numbers mean, applying the hard filters, weighing evidence grades, writing the verdict and the two killer questions. Use **the strongest model you have**. Across the measured arms this is the one substitution that moved the result: strongest main model 0.71 landmine recall, mid 0.57, cheapest 0.46.
- **If you only have one model**, put it on the judgment and cut axes instead.

### On a £20 plan
Keep `standard` mode and run **fewer axes**. Do not switch to `lite` with all twelve. Measured: `lite` on the strongest model found fewer landmines (0.38) than `standard` on the weakest (0.46), and `lite` runs invented numbers far more often (2.0–2.3 fabricated numbers per run against 0.3 in `standard`). Depth is what stops the model guessing; breadth is the part you can safely trade away. When you drop axes, say which ones and mark them `U`.

Full tables, method, caveats and the cost/recall chart: `docs/EXPERIMENTS.md` — https://github.com/jacky18008/pea-princess/blob/main/docs/EXPERIMENTS.md

## What an upgrade buys (from `docs/EXPERIMENTS.md`, 5 flats, small sample)
Going from a £20 setup (mid model, `lite`) to the default (strong judge, `standard`) found about 3.8× as many known landmines (0.15 → 0.57) and cut invented numbers by about 87% (2.3 → 0.3 per report) at roughly 10× the cost per run. `lite` → `standard` alone: +50% landmines, −85% invented numbers. A stronger judge adds a further +0.1–0.15 recall (within noise). Breadth (one reader per axis) adds +0.3 recall at about 5× cost. Worker models make no measurable difference. **Order of upgrades: mode first, then the judge, then breadth; never the workers.**

