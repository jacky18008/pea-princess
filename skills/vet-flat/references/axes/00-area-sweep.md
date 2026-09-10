Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 0 — Area sweep

## Purpose
Sweep a whole area for candidates instead of vetting one flat: enumerate every building that could qualify, filter cheaply, then vet only the survivors.
The twelve axes are the per-building method; this file is the order in which they are run over many buildings without exhausting the budget.

## The cost gate (read this before starting)
Enumerate cheaply, read expensively, and only at the end.
1. Cheap and mechanical: geocoding, postcode coverage, the energy register, the crime and journey APIs, the company register, the planning index. All of it goes through scripts.
2. Free: filtering that list by distance, age, area, floor and price band.
3. Moderate: asking the user to paste review pages for the survivors only.
4. Expensive, and last: the agent reading review text and officer reports.
**For scripted register sweeps, use compact JSON and retrieve the original source spans when a critical fact needs checking.** Host listing research may read permitted public pages; retain relevant evidence once and avoid repeatedly loading whole pages.
Deep review reading is done only inside `sweep_deep_read_radius_m`, even when the enumeration radius is `sweep_radius_m`.

## Stage 0 — Anchor
- Anchor on a **real street address or postcode**, never an area name: "two kilometres around this address", not "around this district".
- `python3 scripts/geo.py lookup "<postcode>"` for the official coordinates, borough, ward and statistical areas.
- A map pin on a listing portal is never geometry. Neither is a police snap point.
- Record the radius, the anchor and the date at the top of the report; every later number is relative to them.

## Stage 1 — Enumerate

Read [listing-evidence.md](../listing-evidence.md) for real candidate discovery using permitted host tools. This register sweep finds buildings; it does not establish advertised units or current availability. Merge public operator listings where accessible, preserving unit identities and source dates. A failed lookup is not permission to create example flats.
1. **Energy-register postcode census.** `python3 scripts/geo.py cover --lat <lat> --lng <lng> --radius <m>` gives the postcodes inside the circle (the underlying radius search caps at `nearest_postcode_max_radius_m` and silently ignores a larger value, so page the circle rather than asking for one big one); then `python3 scripts/epc.py search --postcode "<pc>"` for each, and `python3 scripts/epc.py building --postcode "<pc>" --match "<name>"` for each building worth expanding. Where high floors are missing, search by street instead.
2. **A user-supplied list.** Listing portals and resident-review sites cannot be enumerated automatically; ask the user to paste the search results or the names of the developments they already know, and merge that list in. See `inputs.md`.
Deduplicate by building, not by listing: one building split across postcodes is one candidate, and two flats in the same building are one entry with two units.

## Stage 1b — Exclude
Drop, with a reason recorded for each:
- purpose-built student accommodation and halls;
- serviced apartments and aparthotels;
- blocks that are entirely social or affordable housing, and waiting-list stock;
- anything whose coordinates land outside the circle (a name collision with a development elsewhere);
- buildings with no residential certificates at all.

## Stage 2 — Hard filter (mechanical, from register data only)
- First assessment year and building age against `max_building_age_years`.
- Certified internal area against `min_floor_area_sqft`.
- Floor position from the certificate's property type against `floor_position_exclusions`.
- Advertised price band against `rent_ceiling_pcm`.
Anything that fails here never reaches a script that costs money. Record the count in and the count out.

## Stage 3 — Per-building facts (scripts only, capped)
Cap the deep lines at `sweep_max_deep_lines` buildings. For each, run and store **one compact JSON record**, every field carrying `source_url`, `retrieved_at` and `evidence_class`:
`epc.py building` · `crime.py latest` then `crime.py box` · `commute.py journey`, `stations`, `redundancy` · `planning.py near` and `stages` · `roads.py near` · `company.py search`, `profile`, `address-search` · `redress.py cmp|prs|tpo|rogue|heat-trust` · `landregistry.py price-paid`.
Keep compact records for later stages and retain the source spans needed to verify critical claims.

## Stage 4 — Worst-review surgery (paste mode)
For the survivors only, ask the user once for the review pages, then run the full review hygiene in `06-management-neighbours.md`:
remove incentivised reviews, remove same-day bursts of `review_burst_same_day_min` or more, read the lowest reviews in full, weight move-out reviews highest, treat a building with no natural sample in `review_staleness_years` as unmeasured, and never read a zero denominator as clean.
Attach every score to a **building**, not to a development or a brand.
Cross-check the same building against other sources — hyperlocal news, planning objections, tribunal and company records — because for a small block with no reviews those are the better evidence.

## Stage 5 — Adversarial pass (two lenses)
Give every surviving candidate a fresh reviewing agent that has not seen the first pass, working two lenses:
- **Lens A — landlord, management, bills:** who owns it, who manages it, what the money gate looks like, what the bills really are.
- **Lens B — noise, works, commute, street:** what is being built, what the facade faces, whether the journey survives a strike, what the walk home is like.
Every objection must be written in the five-column format in `13-adversarial-review.md` and must name a **release condition** — the evidence that would retire it. An objection with no release condition is not a valid objection.
Every reviewer must also file a **"checked but not proven"** list: the defects they looked for and did not find. Without it, a reviewer under pressure invents findings.

## Stage 6 — Integration
Produce, in this order:
1. **Coverage and denominator table** — how many buildings were enumerated, excluded, filtered, vetted; and for each source, what was searched and what came back empty.
2. **Comparison table**, one row per building: original verdict, verdict after the adversarial pass, organic management score and invited share, harshest review theme, commute and redundancy grade, residual crime reading, distance to works, best evidenced unit and its estimated total monthly cost, landlord type.
3. **Worst-review matrix**: building, distance, source, date, score, organic or not, and a short verbatim excerpt.
4. **Structural versus single-building findings.** A theme found across at least `structural_finding_min_developments` buildings and at least `structural_finding_min_years` years is structural and may be generalised to the area. Anything narrower is a single-building defect and may not.
5. **Red flags and green lights**, each with a grade, a source class, and whether it is reversible; plus the "not found" table carrying the exact search strings used.
6. **Ranking by quality × probability of closing.** Score quality on the twelve axes and multiply by the chance the deal actually completes. Enquiries change the probability, not the quality — that is what the letters are for.
7. **At most `sweep_max_decision_questions` decision questions** put back to the user, and a per-candidate list of at most two questions for the agent.
8. A viewing-day plan: what must be in writing before leaving the house, at most three flats in one area in a day, and the on-site-only list from `14-site-visit.md`.

## Traps and lessons
- **Name collisions.** Two developments can share a name in different postcodes; check the postcode before moving any review, crime figure or planning record between them.
- **Two flats in one building are not two options.** They share the works risk and the crime box.
- **Nil results are queries, not facts.** Record every search string that returned nothing, so a later reader can tell "there is nothing" from "we did not find it".
- **One fixed geometry for every candidate.** Same box, same window, same journey basis, same bills model — otherwise the table compares methods rather than flats.
- **The enumeration is the cheap part and the reading is the expensive part.** If the budget is running out, cut the number of deep lines, never the hygiene steps.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract. A sweep produces one `candidates[]` entry per building that reached stage 3, each with its twelve `axes[]`, and then fills the sweep-level containers:
- `comparison.ranking[]` — `candidate_id`, `quality_score`, `closing_probability`, `expected_value`, `reason`. Quality is the twelve-axis score; the enquiry letters move the probability, not the quality.
- `comparison.structural_findings[]` — `theme`, `detail`, `buildings_count`, `years`, `generalisable`, `sources`. Set `generalisable` true only when both structural thresholds are met.
- `comparison.single_building_findings[]` — `building`, `theme`, `detail`, `generalisable: false`, `sources`.
- `not_found[]` — `what`, `queries_used` (the exact strings), `where_looked`, `next_step`. This is the coverage table; a sweep without it cannot be audited.
- `blocked_sources[]` — `source`, `http_status`, `reason`, `workaround`, for everything that refused, challenged or returned the wrong page.
- `sources[]` — every source used, with `id` matching `sources.yaml`, `retrieved_at`, `evidence_class` and `provenance`.
- `profile_snapshot` — the ruler used, so a reader can see which filters produced this shortlist.
Keep the excluded buildings and the reason for each in the run's working notes, and summarise the counts in the sweep's opening section.
