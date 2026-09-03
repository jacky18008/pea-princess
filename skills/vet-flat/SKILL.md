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
- **Shell mode**: you can run `python3` and `curl` with internet access. Run `scripts/*.py`; read only their JSON output, never raw pages.
- **Fetch mode**: you can fetch URLs but not run scripts. Use the open GET sources in `references/sources.yaml`; ask the user for the rest.
- **Manual mode**: neither. Ask the user to open pages and paste text, following `references/inputs.md`.
Codex: sandbox network is off by default; enable it or use manual mode. Fetchers that honour robots.txt cannot read the EPC register or council planning portals; that is expected — ask the user.

## 0b. If asked "what can this do", "how do I start", or "I have no idea"
Answer from `references/onboarding.md`: the short pitch in the user's language, then the three starting points (a listing → vet it; an area or destination → sweep; no idea → the ten-fact primer, then six intake questions in one message with a suggested default each). Write the answers into `profile.yaml`, show it back plainly, then start.

## 1. Load the profile
Read `profile.yaml` (hard filters: minimum floor area, maximum building age, budget bands, move-in window, commute destination and minutes, guarantor route, floor and light rules, must-haves, and `budget_mode` lite/standard/deep — depths in `references/budget-modes.md`). If it is missing, ask for the six essentials once (budget, area, age, move-in, destination, must-haves), then proceed and state your assumptions.

## 2. Two presumptions that run through every axis
1. **Cheap has a reason.** A price below the local band means the landlord or agent has a reason to sell you. Find it and name it (location, age, construction, timing, management, commute, aspect). An unexplained discount is a reason to walk.
2. **Pay more only for a nameable benefit** (aspect, floor, quiet side, management). If you cannot say what the premium buys, do not pay it.
Ask of every listing: "What sits under its prettiest feature?" and check what that feature costs on the other axes.

## 3. The 12 axes (method per axis in `references/axes/`)
1. **Identity** — exact flat number, building, postcode. The EPC register is the arbiter (`scripts/epc.py search`, `cert`). Large buildings span several postcodes; search by street if a flat is missing.
2. **Floor area** — EPC internal m² only; balconies excluded; listing and floor-plan figures are claims, not evidence.
3. **Age and fabric** — first EPC assessment year approximates completion; heating class (heat network, gas, electric, heat pump); air permeability ≤ 5 implies mechanical ventilation; `scripts/epc.py building` gives the whole-building profile.
4. **Construction nearby** — planning applications within about 250 m, their phase and decision dates; officer reports carry distance numbers; conditions being discharged tell you whether works are starting or finishing.
5. **Crime** — data.police.uk, a fixed six-month window in a ~300 m box; type mix; nodes on the walk home count in full; never scale up missing months.
6. **Management and neighbours** — resident reviews with incentivised and same-day-burst reviews removed; read the lowest reviews in full; move-out reviews weigh most; short-let footprint in the building.
7. **Agent and landlord compliance** — legal entity on Companies House, redress scheme, client-money protection, deposit protection; landlord type (institutional > professional > absentee).
8. **Price** — £ per sq ft on EPC area against the local band; a discount must have a name; price-reduction history.
9. **Aspect and light** — floor-plan compass, sky openness, obstruction angle; quiet beats light unless there is almost no light.
10. **All-in cost** — rent + bills model + council tax on one basis for every candidate.
11. **Commute and redundancy** — TfL door-to-door minutes; two independent rail "families" within a 10-minute walk.
12. **Low-maintenance living** — bundled bills, washing machine in the flat, parcel handling, blackout bedroom, shop within 3 minutes, a direct route.
**Area sweep** (compare everything around an address): shell mode `python3 scripts/sweep.py --anchor "<postcode>" --radius 800 --dest "<postcode>" --profile profile.yaml --out sweep/`; then read `sweep/summary.md` and `sweep/candidates/*.json`, and send the user `sweep/ask-the-user.md` once. Method: `references/axes/00-area-sweep.md`.
Legal facts (England): Renters' Rights Act 2025, in force 2026-05-01 — periodic tenancies only, no fixed terms, at most one month's rent in advance, deposit ≤ 5 weeks' rent, holding deposit ≤ 1 week. Cite from `references/sources.yaml`.

## 4. Evidence grades — mark every finding
**G** official register · **S** self-reported (landlord, agent, listing) · **C** third-party (reviews, press) · **I** inference · **U** unknown. Two sources disagreeing is itself a finding. An HTTP 200 with the wrong page is not evidence: check the content.

## 5. Sources you may automate, and sources you may only name
Automatable (official or open): EPC register (HTML only; single addresses, built-in spacing), data.police.uk, Companies House, GLA Planning Datahub, TfL, postcodes.io, Land Registry price-paid, Heat Trust, Client Money Protect, GLA rogue landlord checker.
Named only, no method given (their terms forbid automated access): Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com. Ask the user to paste the page.
Catalogue with tested status: `references/sources.yaml`; per-borough portals: `references/boroughs.yaml`.

## 6. When you cannot get something
Follow `references/inputs.md`: try first; collect every gap; ask **once**, in one numbered list, with the URL, the format and one sentence on why; keep working on everything else meanwhile; record `provenance: user_supplied`; mark the axis **U** if it stays unavailable. Never invent a number.

## 7. Output contract
Write `report.json` conforming to `references/report-schema.json`. Shell mode: `python3 scripts/render.py report.json > report.html`. Otherwise hand over the JSON and tell the user to paste it into `viewer/viewer.html`. Always also print the one-page verdict in the user's language.
Plain language in every text field: short sentences; no jargon without a gloss; every number says what it means and what it is compared with; evidence grades as plain labels.
Verdict: **PASS** · **EDGE** (with the break-even rent) · **CONDITIONAL** (conditions listed) · **KILL** (fatal axis named). Include: at most two killer questions for the agent, drawn from `references/questions.md`; viewing-day checks that only the site can answer; a "not found" table listing the search strings you used; sources with retrieval times; and the footer "Generated with vet-flat <version> — <source URL>".

## 8. Never
Sign on the viewing day. Treat listing area as fact. Scale crime figures for missing months. Turn a missing item into a pass. Drop a red flag to make the report tidy. Use ethnicity or nationality as a risk factor.
