Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 3 — Age, fabric, heating and ventilation

## Purpose
Date the building, work out whether it was built as housing or converted into it, and identify how it is heated, ventilated and billed.
This axis decides most of the running-cost and comfort risk, and it is where refurbishment claims are tested.

## What counts as evidence
- **G** — first EPC assessment year; the earliest registered sale with a new-build flag; the original use class in the planning register; the heat supplier's filed accounts; a scheme's entry on the heat-network consumer-protection register.
- **S** — "built 2019" in the listing; "recently refurbished"; the operator's tariff page.
- **C** — resident reports of summer heat, smells through vents, or a tariff rise; local press.
- **I** — completion year inferred from the first certificate; ventilation type inferred from air permeability.
- **U** — no certificate history and no planning record.

## Method in shell mode
1. `python3 scripts/epc.py cert <id> --history` — every certificate for the flat, oldest first; `first_assessment_year`, ratings over time.
2. `python3 scripts/epc.py building --postcode "<pc>" --match "<building>"` — `earliest_assessment_year`, `assessment_year_counts`, `assessment_types`, `heating_classes`, `air_permeability_values`.
3. `python3 scripts/landregistry.py price-paid --postcode "<pc>" --brief` — the earliest and latest sales, the new-build count and a price summary (drop `--brief` for every transaction); the earliest sales and their new-build flag. This is the hardest available counter-evidence to an age claim.
4. `python3 scripts/planning.py search --site-name "<building>"` and `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250 --brief` — the original permission and use class.
5. Heat networks: `python3 scripts/redress.py heat-trust --site "<building>"`, then `python3 scripts/company.py search "<supplier>"` → `profile` → `filings` for the accounts and the registered office.

## Method in fetch mode
Certificate pages, the planning datahub, the heat-network register and the regulator's heat-networks page are all fetchable. Company filings are fetchable on the free HTML service.

## Method in manual mode
Ask the user for:
1. The certificate page for this flat and, if offered, the older certificates linked from it.
2. The heating and hot-water rows, verbatim, if they only paste part of the page.
3. The welcome pack or tariff page for the heat network — standing charge and unit rate, in writing, from the landlord or agent.
4. One sentence from the agent: "when was the flat last refurbished, and are the photographs of this exact flat as it stands today?"

## How to read the numbers
- `max_building_age_years` — profile. Compute age from the first assessment year, and say it is an approximation.
- `epc_validity_years` — a whole building re-assessed on one day is usually this clock expiring, not a refurbishment.
- `air_permeability_mech_vent_threshold` — an air permeability at or below this value implies the flat must have mechanical ventilation to meet the ventilation building regulation. It implies mechanical ventilation; it does not identify which kind.
- `heat_network_supplier_margin_flag` — cost of sales above revenue in the supplier's accounts.

## Traps and lessons
- **First assessment year approximates completion, it does not prove it.** The earliest registered sale carrying a new-build flag is stronger, and has overturned an age claim outright.
- **New build versus conversion.** No "new dwelling" certificates in the register while the first certificate year is well after 2008 points to a conversion, not a new build.
- **Conversions skipped the daylight and space standards.** Office-to-residential permitted development, live/work units turned residential, and warehouse conversions were never assessed against residential daylight or internal space standards. The certificate and the listing will not reveal this; the planning register's original use class will. An unusually cheap split-level flat deserves the question "what was this before?" — one such unit was a live/work commercial shell converted years later, with a 2.44 m ceiling and a bedroom wall of street-facing glazing.
- **Two-generation certificate comparison is a refurbishment test.** Line up each flat's old and new rating: ratings rising is evidence of refurbishment; flat or falling across the whole building is a strong indicator that nothing was refurbished. It is an indicator, not proof — assessment-method revisions can lower ratings on their own, so state the caveat.
- **Photographs are recycled.** Completion photography can run for a decade, and "brand new" copy with it. The consequence is that condition can only be verified at the viewing, and any gap between photograph and reality is negotiating leverage.
- **Heat networks have no price cap.** The regulator took on heat networks with pricing benchmarks and standards of performance following later, so a tenancy signed in the gap has no price protection. There is a statutory ombudsman route; a scheme outside the consumer-protection register should be marked as having no independent complaints route beyond that.
- **Read the heat supplier's accounts.** A retail heat supplier whose cost of sales exceeds its revenue is selling below cost and will raise the tariff — the accounts show it about a year before residents notice. A registered office that has moved away from the developer's address signals a change of ownership, after which the retailer becomes a pass-through and pricing control sits elsewhere. This is harder evidence than any press release.
- **Ventilation ladder:** cooling > heat-recovery ventilation > mechanical extract > openable windows only. Heat recovery is not cooling; on a hot day its bypass simply brings outdoor air in at outdoor temperature. Its real value is air change with the windows shut (which serves quiet), night purge, and continuous air quality.
- **"The EPC does not list air conditioning" does not mean there is no cooling.** Air permeability alone does not prove a heat-recovery system, and an extract-only system is not automatically inadequate. Ask; do not infer a whole-area rejection from a silent field.
- **Shared ducts carry neighbours' smells.** Extract systems and shared risers move smoke and cooking smells between flats, and a new building is not immune. Search resident reviews for smell-through-vent reports; treat a hit as a real defect on this axis.
- **Warehouse and loft conversions** raise three separate questions: industrial glazing (noise and heat), the heating cost of a double-height space, and non-standard layouts.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 3`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the profile's maximum building age.
- `candidates[].landmines[]` with code **L6** (heat bought from a building-wide system at a rate the tenant cannot switch away from, plus whoever bills it) and code **L11** (no cooling, or mechanical ventilation carrying cooking and smoke between flats).
- `candidates[].viewing_day_checks[]` — open the utility cupboard, find the ventilation unit and the heat interface unit.
- `candidates[].provenance_notes` — if the age rests on the first assessment year rather than a registered sale, say so.
Numbers to record: first assessment year, age in years, earliest registered sale year, air permeability, heating kWh a year, supplier revenue against cost of sales.
