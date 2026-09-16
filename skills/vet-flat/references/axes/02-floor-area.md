Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 2 — Floor area

## Purpose
Establish how big the flat actually is, in internal square metres, from the energy certificate.
Everything advertised — square feet on a listing, a figure on a floor plan, a developer's brochure — is a claim until the certificate agrees with it.

## What counts as evidence
- **G** — "Total floor area: 51 square metres" on the flat's own EPC; the whole-building area distribution from the register.
- **S** — the listing's square footage; the agent's floor plan; the landlord's own description.
- **C** — a developer brochure or a press unit schedule.
- **I** — an area scaled off a plan by hand; the area of "a similar unit in the building".
- **U** — no certificate for this flat and no plan.

## Method in shell mode
1. `python3 scripts/epc.py cert <certificate id>` — `total_floor_area_m2` and `total_floor_area_sqft`.
2. `python3 scripts/epc.py building --postcode "<postcode>" --match "<building>"` — `summary.floor_area_m2` gives min, median, max and a histogram, plus `property_types` and `ground_or_basement_flats`.
3. Compare: advertised area, plan area, EPC area. Record all three and the variance.

## Method in fetch mode
Fetch the certificate page and read the "Total floor area" row. Nothing else on the page is an area.

## Method in manual mode
Ask the user for:
1. The certificate page text for this exact flat (the area is one row on it).
2. The floor plan image from the listing, at full size, including the small print under it.
3. If the plan states an area: the exact wording ("approximate gross internal area", "including balcony", or a separately dimensioned balcony).

## How to read the numbers
- `min_floor_area_sqft` — the user's floor, from `profile.yaml`. There is no generic default; if the profile is silent, report the area and do not fail the flat on size.
- `floor_area_exception_band_sqft` — profile: some users allow a slightly smaller flat in a specific area or with specific compensations. State the exception's scope; never apply a city-wide exception.
- `area_variance_investigate_pct` — an advertised-vs-certificate gap above this needs a named explanation before anything else on the listing is trusted.
- `studio_living_area_share` — if the living area is at or above this share of the total, the flat is a studio however it is advertised.

## Traps and lessons
- **The advertised area often includes the balcony; the certificate never does.** A 2019 riverside tower advertised at 885 sq ft had 570 sq ft on its energy certificate. Always convert and compare in the same unit.
- **"Approximate gross internal area" does not automatically include a balcony.** If the balcony is dimensioned separately on the same plan, the stated internal area excludes it. Do not assert either way without reading the plan; withdraw any earlier inference that assumed it.
- **Mezzanines and galleries** may or may not be counted. If the plan shows a second level, ask which areas the certificate measured.
- **The whole-building distribution is worth more than one certificate.** It tells you whether this flat is a mainstream type or an edge type, whether an apparent £ per square foot gap is just the size curve, and whether the building contains ground-floor flats at all. In one sweep it cancelled a false "dark side discount" alarm outright.
- **A self-described "studio suite" is not evidence.** Use the building's area bands plus the living-area share to decide whether it is a real one-bedroom.
- **Borrowed areas are not this flat's area.** If the only certificate is for a neighbouring unit, say in the axis text that the certificate is a neighbouring unit's and grade the axis S at best.
- **Sources disagreeing is itself a finding.** A plan saying 459 sq ft against a certificate saying 549 sq ft is a document-quality problem; record it separately from any management or landlord judgement, and use it as a question, not an accusation.
- **A listing that contradicts itself** (an accessibility field saying ground floor while the text says 16th) tells you how carefully the listing was assembled. Note it here and again in axis 7.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 2`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the profile's minimum area: `requirement`, `observed`, `pass`, `evidence_class`.
- `candidates[].metrics.price_per_sqft_epc` — this axis supplies the denominator; axis 8 supplies the rent.
- `candidates[].landmines[]` with code **L1** when the advertised size exceeds the certified indoor area, or a balcony or gallery is being counted as room.
- `candidates[].photos_vs_reality_notes` — a wide lens, a shot from the one corner with sky, furniture at doll scale.
Numbers to record: certified area in square metres and square feet, advertised area, the gap as a percentage, the building's median and range.
