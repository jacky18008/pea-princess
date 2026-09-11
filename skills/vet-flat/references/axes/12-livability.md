Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 12 — Low-maintenance living

## Purpose
Ask whether the flat still works on a week when the tenant has no energy for it: whether the bills pay themselves, the laundry happens, the parcels arrive and the bedroom is sleepable.
This axis catches what the other eleven miss, because none of them are about daily friction.

## What counts as evidence
- **G** — the tenancy or the inventory listing the appliances; a bundled-bill contract; the building's own parcel policy in writing.
- **G** — the area's living-environment deciles from the English Indices of Deprivation 2025 (`scripts/living_env.py`): housing quality indoors; air quality and road traffic accidents outdoors. About 1,500 people around the postcode, not the building.
- **S** — the listing's amenity list and the operator's description.
- **C** — residents describing what actually happens with parcels, lifts, laundry and the concierge.
- **I** — an appliance inferred from a photograph or a plan symbol.
- **U** — nobody has confirmed it and the viewing has not happened.

## Method in shell mode
1. `python3 scripts/geo.py nearby "<postcode>" --radius 400` and `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 400` — the nearest food shop, launderette, pharmacy and the walking distance to each.
2. `python3 scripts/commute.py journey` — whether the daily route is direct or needs changes (a direct route beats a route that saves five minutes with a change).
3. Reviews (paste mode, axis 6) — search for lifts, parcels, laundry and heating complaints.
4. `python3 scripts/living_env.py lookup --postcode "<postcode>"` — the neighbourhood's living-environment deciles (official, open). Context for the comparison, never a filter.

## Method in fetch mode
Mapping and journey data only. Everything about the inside of the flat comes from the listing or the viewing.

## Method in manual mode
Ask the user for:
1. The amenity list from the listing and the appliance list from the inventory, if there is one.
2. Whether bills are one bundled payment or separate accounts, and which utilities are in the bundle.
3. A photograph of the kitchen and utility cupboard, and of the bedroom window and any blind.
4. Whether the building's parcel room accepts couriers other than the national postal service.

## How to read the numbers
- `living_environment.decile`, `indoors.decile`, `outdoors.decile` — 1 is the most deprived tenth of small areas in England, 10 the least. Read the two halves separately: a low outdoors decile is air quality and road accidents (most of inner London), a low indoors decile is housing in poor condition or without central heating in the area, which the EPC and the viewing settle for this flat. Compare candidates with each other; say the number is an area figure; never let it change a verdict on its own, and never describe the area by who lives there.
- `supermarket_walk_min` — a food shop within this walk.
- `redundancy_walk_min` — reused here for the launderette and pharmacy walk.
- `washing_machine_required` — profile. For most users a machine inside the flat is close to a hard requirement; a missing one is usually only found in older conversions, where the age filter has already bitten.
- `launderette_trip_cost` and `launderette_trip_minutes` — profile placeholders for costing the alternative on axis 10.

## The checklist
1. **Bills structure.** One bundled bill is the gold standard; five separate accounts set up by the tenant is a deduction, because a missed direct debit is exactly what a bad week produces.
2. **Washing machine inside the flat.** Grade the alternatives rather than treating them as equal: in-flat machine; shared laundry in the building; launderette within a short walk; launderette far away; none. Cost the trips into axis 10.
3. **Dishwasher** is a bonus, not a requirement.
4. **Parcels.** A concierge or parcel room, and whether it takes couriers other than the national post. This is the single most common quiet failure in a tall building.
5. **A food shop within `supermarket_walk_min`.**
6. **A bedroom that closes and blacks out**, so daytime sleep is possible when the routine slips.
7. **One named reason to leave the house nearby.** If you cannot finish the sentence "the thing that would get me out of the flat here is …", the location is a deduction, not a saving. A discount earned by an empty neighbourhood is a discount taken out of this axis.
8. **A direct route beats saving five minutes with a change** (see axis 11).
9. **Move-in week routine:** set up the direct debits, the council tax account and any exemption, and the broadband payment in one sitting, while there is energy to do it.
10. **Kitchen grading** — for a temporary or serviced let: a private kitchen with a hob, a fridge and either an oven or a microwave is a full kitchen. The word "kitchenette" does not disqualify anything; read the equipment list instead.

## Traps and lessons
- **A listing that contradicts itself is a quality signal about the operator**: "high-speed wi-fi" in the description with "unavailable: wi-fi" in the amenity list; "studio, 0 bathrooms"; a one-month minimum stay that will nevertheless accept a seven-night request. Record it here and cross-reference axis 7.
- **Split levels and spiral staircases** are a daily tax and a moving-in problem; deduct.
- **A windowless second room is storage**, whatever it is called. If the user actually wants a dark room, that is a private benefit — it does not raise the price you offer.
- **"Bills included" tied to one compulsory supplier** is only a benefit once that supplier has been checked (axis 6).
- **Nothing on this axis can be confirmed remotely.** Almost every item here belongs on the viewing-day list; see `14-site-visit.md`.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 12`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row per must-have from the profile, each with what was observed and whether it passes.
- `candidates[].viewing_day_checks[]` — most of this axis is a viewing-day list; write each item as a question the visit can answer.
- `candidates[].landmines[]` with code **L11** where the flat has no cooling or shares its ventilation.
- `candidates[].photos_vs_reality_notes` — where the listing contradicts itself, say which version the report used.
Numbers to record: walking minutes to a food shop, to a launderette and to a pharmacy; the number of separate utility accounts; the cost and time of a laundry trip where there is no machine.
