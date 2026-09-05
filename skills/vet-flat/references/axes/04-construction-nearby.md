Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 4 — Construction and works nearby

## Purpose
Find out what will be built, demolished or dug up near the flat during the tenancy, and which facade takes the hit.
For any development begun after about 2010, the first question is: is the scheme finished, and which phase am I facing?

## What counts as evidence
- **G** — planning applications, decision notices, officer and committee reports, discharge-of-condition records, licensing and highways notices.
- **S** — the developer's or agent's account of the programme; a marketing site plan.
- **C** — local press, residents' objections, a neighbourhood forum thread.
- **I** — a phase inferred from which conditions are being discharged; distance measured off a map.
- **U** — the borough portal is unreadable and the user cannot search it.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` for coordinates.
2. `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250` — applications within the standard radius from the London-wide index.
3. `python3 scripts/planning.py search --site-name "<building or neighbour site>"` — by name, and by street when the name fails.
4. `python3 scripts/planning.py stages --ref "<application reference>"` — decision date, conditions, and which conditions have been discharged.
5. `python3 scripts/planning.py planit --postcode "<pc>" --radius-km 0.3` — a second index, queried by postcode and radius (a free-text site-name search there matches only the description field and will return nothing).
6. `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 200` — distance to the nearest major road, railway, tunnel mouth and late-night food or market use.
7. Before the visit: street imagery, see `18-street-view.md`. `python3 scripts/streetview.py check --lat <lat> --lng <lng>`, then `fetch` if the user has a key. Hoarding, scaffolding, a crane, a site cabin or a wheel wash in the frame is a lead — and site hoarding usually carries the developer's name and often the planning reference, which goes straight into step 4. Read the capture date first: imagery years old may show a hoarding where a finished building now stands, or an empty site where a tower now stands. Class C, dated, and a lead to confirm, never a finding on its own.

## Method in fetch mode
The London-wide planning index answers over plain GET. Borough portals are all robots-disallowed, so treat them as manual. Council committee pages are fetchable, but only if you assert on the page title containing "Agenda for" — a stale meeting id returns a plausible-looking page with HTTP 200.

## Method in manual mode
Ask the user for:
1. A search of the borough's planning portal for the building name and each adjacent street, pasted as the list of application references with dates and decisions.
2. The officer report or committee report PDF for any large neighbouring scheme — these state distances between buildings and often name affected properties and windows.
3. Anything the agent says in writing about works, and when they are due to finish.

## How to read the numbers
- `planning_radius_m` — the standard search radius around the flat.
- `road_facade_distance_m` — inside this distance from a major road, the building must be split by facade before any noise judgement.
- `construction_decision_within_tenancy` — an undecided application whose decision is expected during the tenancy is a live risk, not a non-event.
- `hospital_helipad_distance_m` — inside this distance from an accident-and-emergency entrance, an ambulance route or a helipad, treat it as a deduction. Being near a hospital is never scored as a benefit on this axis; one rooftop helipad 230 m away averaged five movements a day.

## Traps and lessons
- **Read the officer report before doing your own geometry.** Committee and officer reports for a neighbouring scheme frequently name the affected building and give the numbers window by window — including findings such as "moderate adverse" daylight effects and materially harmful winter sunlight to named windows. Search for the report first.
- **Condition discharge tells you the phase.** Pre-commencement conditions (archaeology, piling method, construction management plan) mean works are about to start. Pre-occupation conditions (accessible parking bays, cycle stores, remediation verification, ecology compensation) mean a scheme is finishing.
- **Status fields lie in both directions.** A London-wide index can mark an implemented permission as lapsed, creating a false three-year clock; an aggregator can be years stale and still show a withdrawn scheme as registered; a borough portal can hide a withdrawn application behind "details not available". Take form data and decision dates from the index, and take the real state from recent condition activity in the borough register.
- **Zero hits is a coverage gap, not an absence.** A regional index carries the larger and referable schemes; a small named site may simply not be in it. Never write "no planning activity" off a nil result — record the exact query in the `not_found[]` table.
- **Coordinate precedence for distances:** grid coordinates printed on a phasing or site plan > the portal's own site point > an address point. An address point has been observed 190 m from the real site boundary. A portal map pin and a police snap point are never geometry.
- **Only registry documents date a start.** Piling method statements, construction environmental management plans and build programmes naming a contractor and week numbers are official-grade. A company announcement is self-reported. An agent's assurance is not evidence.
- **Include trunk roads in any road query.** Major A-roads are frequently classified as trunk rather than primary, and a filter that omits the class has missed a five-lane road 42 m away and written the building up as quiet.
- **Split the building by facade.** Within `road_facade_distance_m` of a major road, the road side and the courtyard side are two different products at the same rent. Ask the agent, in these words: does the window face the main road or the courtyard?
- **A tunnel mouth, a cutting or a bridge deck acts as a megaphone**; so does a bin or delivery yard at night. Check what sits under the prettiest feature: a river view can be a river-facing main road.
- **Two flats in the same building share this axis.** Merge them; they are not independent options.
- **A bank-holiday visit proves nothing.** No site activity on a holiday does not tell you why the site is quiet and says nothing about a Tuesday. See `14-site-visit.md`.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 4`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.nearest_works_m` — distance to the nearest active site or approved scheme, with what it is and when it runs in `meaning`.
- `candidates[].landmines[]` with code **L5** (a site next door, or a tall scheme still undecided whose decision lands during the tenancy) and code **L4** (the flat faces a main road, a railway or a tunnel mouth).
- `candidates[].killer_questions[]` — "does this window face the main road or the courtyard" earns its place here.
- `not_found[]` — every planning query that returned nothing, with the exact search terms, because a nil result on a regional index is a coverage gap.
Numbers to record: distance to each scheme, storeys, decision date, works window, distance to the nearest trunk road and railway.
