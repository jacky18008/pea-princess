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

# vet-flat — London flat vetting

## 0. Pick your mode first (tell the user in one line which one you are in)
- **Shell mode**: `python3` and `curl` with internet. Run `scripts/*.py`; read only their JSON.
- **Fetch mode**: fetch only, no scripts. Use the open GET sources in `references/sources.yaml`; ask the user for the rest.
- **Manual mode**: neither. Ask the user to paste pages (`references/inputs.md`).

## 0b. If asked "what can this do", "how do I start", or "I have no idea"
Answer from `references/onboarding.md`: the short pitch in the user's language, then the starting points (a listing → vet it; an area or destination → sweep; no idea → primer and six intake questions; about to sign or need a bridge → axes 15–17; just arrived → ask about a hotel or operator-run stay first). Write the answers into `profile.yaml`, show it back, then start.

## 1. Load the profile
Read `profile.yaml` (hard filters: floor area, building age, budget bands, move-in window, commute destination and minutes, guarantor route, floor and light rules, must-haves, and `budget_mode` lite/standard/deep — see `references/budget-modes.md`). If it is missing, ask for the six essentials once (budget, area, age, move-in, destination, must-haves), then proceed and state your assumptions.

## 2. Two presumptions that run through every axis
1. **Cheap has a reason.** A price below the local band means the landlord or agent has a reason to sell you. Find it and name it. An unexplained discount is a reason to walk.
2. **Pay more only for a nameable benefit** (aspect, floor, quiet side, management).
3. **The user is the princess; you only lift the mattresses.** Know what you do not know and say so: list what only the user can supply (floor plan, street view, how the street felt) instead of guessing. Landlords and agents are partners. This is a filter; the viewing decides.
Ask of every listing: "What sits under its prettiest feature?"

## 3. The 12 axes (method per axis in `references/axes/`)
1. **Identity** — exact flat number, building, postcode; the EPC register is the arbiter (`scripts/epc.py search`, `cert`). Big buildings span postcodes; search by street if needed.
2. **Floor area** — EPC internal m² only, balconies excluded; listing and floor-plan figures are claims.
3. **Age and fabric** — first EPC assessment year ≈ completion; heating class (heat network, gas, electric, heat pump); air permeability ≤ 5 implies mechanical ventilation; `scripts/epc.py building` profiles the whole building.
4. **Construction nearby** — planning applications within ~250 m, phase and decision dates; officer reports carry distances; discharged conditions show whether works start or finish.
5. **Crime** — data.police.uk, fixed six-month window in a ~300 m box; type mix; nodes on the walk home count in full; never scale up missing months.
6. **Management and neighbours** — reviews minus incentivised and same-day bursts; read the lowest in full; move-out reviews weigh most; short-let footprint.
7. **Agent and landlord compliance** — legal entity on Companies House, redress scheme, client-money protection, deposit protection; landlord type (institutional > professional > absentee).
8. **Price** — £ per sq ft on EPC area vs the local band; a discount must have a name; reduction history.
9. **Aspect and light** — floor-plan compass, sky openness, obstruction angle; quiet beats light unless there is almost none.
10. **All-in cost** — rent + bills model + council tax, one basis for all.
11. **Commute and redundancy** — TfL door-to-door minutes; two independent rail families within a 10-minute walk.
12. **Low-maintenance living** — bundled bills, in-flat washing machine, parcel handling, blackout bedroom, shop within 3 minutes, direct route.
**Move-in half**: `references/axes/15`–`17` (bridging, referencing, first weeks); also `13` (adversarial review), `14` (site visit).
**Escalation ladder** (automatic): every flat starts at `standard` (scripts; cheap workers only for pasted text; strong judge). Go to `breadth` (one cheap reader per reading-heavy axis, in parallel) only for the final two or three flats, or a CONDITIONAL/EDGE verdict with over 40% of axes unknown. Four or more subagents at once always use the cheap tier. State the tier and reason on the report's first line (`generated_by.tier`, `escalation_reason`). Details: `references/budget-modes.md`.
**Area sweep** (compare everything around an address): shell mode `python3 scripts/sweep.py --anchor "<postcode>" --radius 800 --dest "<postcode>" --profile profile.yaml --out sweep/`; then read `sweep/summary.md` and `sweep/candidates/*.json`, and send the user `sweep/ask-the-user.md` once. Method: `references/axes/00-area-sweep.md`.
Legal facts (England, Renters' Rights Act 2025, in force 2026-05-01): periodic tenancies only, at most one month's rent in advance, deposit ≤ 5 weeks' rent, holding deposit ≤ 1 week; cite `references/sources.yaml`.
**Arithmetic is never done in your head.** Deposit caps, affordability multiples, all-in cost, £ per sq ft, bridging totals, break-even rent, guarantor fees and pro-rata rent come from `scripts/calc.py` (it prints every step); with no shell, write the formula and each step, then check it a second way.

## 4. Evidence grades — mark every finding
**G** official register · **S** self-reported (landlord, agent, listing) · **C** third-party (reviews, press) · **I** inference · **U** unknown. Two sources disagreeing is itself a finding; a 200 with the wrong page is not evidence.

## 5. Sources you may automate, and sources you may only name
Automatable open sources are catalogued in `references/sources.yaml`.
Named only, no method (terms forbid automated access): Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com. Ask the user to paste.
Per-borough portals: `references/boroughs.yaml`.

## 6. When you cannot get something
Follow `references/inputs.md`: try first; collect every gap; ask **once**, with URL, format and why; record `provenance: user_supplied`; mark the axis **U** if unavailable. Never invent a number.

## 7. Output contract
Write `report.json` per `references/report-schema.json`. Shell mode: `python3 scripts/render.py report.json > report.html`. Otherwise give the JSON for `viewer/viewer.html`. Also print the one-page verdict in the user's language.
Plain language everywhere: short sentences; no jargon without a gloss; every number says what it means and is compared with; evidence grades as plain labels.
Verdict: **PASS** · **EDGE** (break-even rent) · **CONDITIONAL** (conditions listed) · **KILL** (fatal axis named). Include: answers to each of the user's `my_questions` from the profile, with evidence grades; ≤2 killer questions from `references/questions.md`; viewing-day checks; a "not found" table with the search strings; sources with retrieval times; the footer "Generated with vet-flat <version> — <source URL>".

## 8. Never
Sign on the viewing day. Treat listing area as fact. Scale crime figures for missing months. Turn a missing item into a pass. Hide a red flag. Use ethnicity or nationality as a factor.
