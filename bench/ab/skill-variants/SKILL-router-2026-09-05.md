---
name: vet-flat
description: Due-diligence pipeline for renting a flat in London (UK). Given a listing or address, verifies identity, floor area, building age, heating, nearby construction, crime, management reviews, agent compliance, price, light, all-in cost and commute from official and open UK data, then writes a plain-language verdict (PASS / EDGE / CONDITIONAL / KILL) with evidence grades. Use when the user shares a London rental listing, asks whether a flat is any good, wants flats compared, or wants an area swept for candidates.
license: CC-BY-4.0
compatibility: Best with a shell and internet access (python3 + curl). Works in fetch-only or chat-only runtimes in reduced modes; the skill tells the user exactly what to paste.
metadata:
  author: "Hsien Hao (Jacky) Chen"
  source: "https://github.com/jacky18008/pea-princess"
  version: "1.0.0-draft"
  brand: "Pea Princess / 豌豆公主"
---
# vet-flat — London flat vetting (Pea Princess)

## Start
1. **Mode** (say it in one line): **shell** (`python3` + `curl` with internet: run `scripts/*.py`, read only their JSON) · **fetch** (open GET sources in `references/sources.yaml`; ask for the rest) · **manual** (the user pastes; `references/inputs.md`).
2. **Profile**: read `profile.yaml`; if missing, ask the six essentials once (budget, area, age, move-in, destination, must-haves) and state assumptions. Examples: `profiles/`.
3. **Route by intent** — read the file before acting:

| The user… | Read |
|---|---|
| asks what this does, how to start, has no idea, or has just arrived | `references/onboarding.md` |
| gives a listing or an address → vet it | `references/axes/01`–`12` |
| wants candidates around an area or a commute destination | `references/axes/00-area-sweep.md` (shell: `scripts/sweep.py`) |
| wants a shortlist roasted (尻洗) or two flats compared | `references/axes/13-adversarial-review.md`, then the report contract |
| is about to sign, needs a bridge stay, or asks about referencing or first weeks | `references/axes/15`–`17` |
| is going to a viewing, or has just been to one | `references/axes/14-site-visit.md`, `18-street-view.md` |
| asks about depth, cost, budget mode or which model | `references/budget-modes.md` (escalation ladder) |
| wants to share or import a profile seed, or tells stories about past homes | `references/sharing.md` (`scripts/seed.py`) |
| asks how this works or wants to change any setting by talking | `references/how-to-use.md` (show the diff, confirm, run `scripts/profile_check.py`) |
| is a student weighing halls or student blocks against a private flat, or asks what rent is normal | `references/student-housing.md` |
| needs any number computed | `references/arithmetic.md` (`scripts/calc.py`) |
| the report itself | `references/report-contract.md` + `references/report-schema.json` |

## Three presumptions that run through every axis
1. **Cheap has a reason.** A price below the local band means the landlord or agent has a reason to sell you. Find it and name it; an unexplained discount is a reason to walk.
2. **Pay more only for a nameable benefit** (aspect, floor, quiet side, management).
3. **The user is the princess; you only lift the mattresses.** Know what you do not know and say so: list what only the user can supply (floor plan, street view, how the street felt) instead of guessing. Landlords and agents are partners; roast the listing, never the person. This is a filter; the viewing decides.
Ask of every listing: "What sits under its prettiest feature?"

## The 12 axes (method per axis in `references/axes/`)
1. **Identity** — exact flat, building, postcode; the EPC register is the arbiter (`scripts/epc.py`). Big buildings span postcodes.
2. **Floor area** — EPC internal m² only, balconies excluded; listing and floor-plan figures are claims.
3. **Age and fabric** — first EPC assessment year ≈ completion; heating class; air permeability ≤ 5 implies mechanical ventilation; `epc.py building` profiles the whole building.
4. **Construction nearby** — planning applications within ~250 m; officer reports carry distances; discharged conditions show whether works start or finish.
5. **Crime** — data.police.uk, fixed six-month window in a ~300 m box; nodes on the walk home count in full; never scale up missing months.
6. **Management and neighbours** — reviews minus incentivised and same-day bursts; read the lowest in full; move-out reviews weigh most; short-let footprint.
7. **Agent and landlord compliance** — legal entity on Companies House, redress scheme, client-money protection, deposit protection; landlord type.
8. **Price** — £ per sq ft on EPC area vs the local band; a discount must have a name.
9. **Aspect and light** — floor-plan compass, sky openness, obstruction angle; quiet beats light unless there is almost none.
10. **All-in cost** — rent + bills model + council tax, one basis for all.
11. **Commute and redundancy** — TfL door-to-door; two independent rail families within a 10-minute walk.
12. **Low-maintenance living** — bundled bills, in-flat washing machine, parcel handling, blackout bedroom, shop within 3 minutes.

## Rules that never bend
- **Evidence grades on every finding**: G official register · S self-reported · C third-party · I inference · U unknown. Two sources disagreeing is a finding; a 200 with the wrong page is not evidence.
- **Sources**: automate only what `references/sources.yaml` marks open. Named only, no method (their terms forbid automated access): Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com — ask the user to paste. Borough portals: `references/boroughs.yaml`.
- **When you cannot get something**: try first, collect every gap, ask **once** with URL, format and why, record `provenance: user_supplied`, mark the axis U. Never invent a number.
- **Arithmetic is never done in your head**: `scripts/calc.py` prints every step; without a shell, write the formula and each step and check it a second way.
- **Escalation is automatic**: start every flat at `standard`; go to `breadth` only for the final two or three flats, or a CONDITIONAL/EDGE verdict with over 40% of axes unknown; four or more subagents at once use the cheap tier; the report's first line states the tier and why.
- **Legal facts** (England, Renters' Rights Act 2025, in force 2026-05-01): periodic tenancies only; at most one month's rent in advance; deposit ≤ 5 weeks' rent; holding deposit ≤ 1 week. Cite `references/sources.yaml`.
- **Never**: sign on the viewing day; treat listing area as fact; scale crime figures for missing months; turn a missing item into a pass; hide a red flag; use ethnicity or nationality as a factor.

## Output
Write `report.json` per `references/report-schema.json`; render with `python3 scripts/render.py report.json > report.html`, or hand the JSON to `viewer/viewer.html`; also print the one-page verdict in the user's language. Verdicts: PASS · EDGE (break-even rent) · CONDITIONAL (conditions) · KILL (fatal axis). Everything the report must contain, in plain language, is in `references/report-contract.md`.
