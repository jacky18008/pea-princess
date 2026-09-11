Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 5 — Crime and the walk home

## Purpose
Grade the immediate area with open police data, on one fixed geometry for every candidate, and separately assess the route from the station to the door.
The output is a tier and a texture, not a precise ranking of streets.

## What counts as evidence
- **G** — street-level crime records published by the police open-data service, with the months they cover.
- **S** — the agent's or operator's characterisation of the area.
- **C** — local press, resident reports, a neighbourhood policing page.
- **I** — anything you scaled, extrapolated or inferred from a partial window.
- **U** — the address is too new to appear in the street gazetteer, so it is unmeasured (which is not the same as clean).

## Method in shell mode
0. If the question is the street rather than one flat, `python3 scripts/area_scan.py --postcode "<pc>" --street "<name>"` answers crime, roads, noise in dB, works and the living environment in one compact JSON; come here only for the finer window or route analysis.
1. `python3 scripts/crime.py latest` — the newest month the dataset actually holds. Choose months from this, never from today's date.
2. `python3 scripts/geo.py box --lat <lat> --lng <lng> --half-width 150` — the polygon. Same spec for every candidate.
3. `python3 scripts/crime.py box --lat <lat> --lng <lng> --half-width 150 --months 6 --sensitivity 20` — counts by month and category, the top street anchors, and the four shifted boxes.
4. Classify each top anchor as on or off the station-to-door route, using the walking leg from `commute.py journey`.

## Method in fetch mode
The police open-data API is open, has an empty robots file, and answers plain GET requests. Use the polygon form, not a single point — a point query returns a one-mile circle, which is a different question.

## Method in manual mode
Open data, so this axis rarely needs the user. If it does, ask for: the postcode's official coordinates, and the exact route they walk home from the station.

## How to read the numbers
- `crime_box_half_width_m`, `crime_box_lat_delta_deg`, `crime_box_lng_delta_deg` — the standard box (about 300 m by 305 m at London latitude). Never resize it per candidate.
- `crime_window_months` — a fixed window, always the same length.
- `police_data_lag_months` — publication runs behind by this much; the newest month available is not last month.
- `crime_sensitivity_shift_m` — shift the box this far in each of four directions and report the range.
- `crime_point_source_share_flag` — a single anchor carrying at least this share of the counts is a point source; say so.
- `crime_top_anchor_count` — how many street anchors to list.
- `night_route_node_share_flag` — the share of counts sitting on the walk home; above this is a red flag on its own.

## Traps and lessons
- **Never scale up for missing months.** Publication delay is not a reduction in exposure, and multiplying a short window to a six-month equivalent is unsupported. Use a fixed window, mark missing months as missing, never fill them with zeros, and if you must extrapolate, state the observed period and the assumption in the same sentence.
- **Get the sign of the longitude from the geocoder.** A flipped sign puts the box a kilometre away over empty ground and returns a fake quiet reading. Do not infer the sign from the postcode area — a rule of that kind was tested and found wrong for a street on the "obvious" side of the meridian. After the query, check that the top street names are actually near the target.
- **Report the sensitivity range, not a point.** Shifting the box 20 m has moved a count by 37%. One box centre is an opinion; five boxes are a range.
- **Box size and centre change the conclusion.** Over one area the six-month count moved between 66 and 139 with the centre; shrinking the box from 150 m to 120 m removed exactly the two anchors carrying all the violence. Use the standard spec for every candidate, and say so in the method note.
- **"On or near <street>" is a snap point**, not the place the offence happened. Anchors are for pattern reading, never for street-level precision.
- **Anchor spread is character.** Counts spread across the top five street names is neighbourhood-wide antisocial behaviour and cannot be discounted. One street dominating is usually a retail or transport point source that can be discounted for the area grade.
- **The point-source discount grades the area; it never erases the walk home.** A node sitting on the line from the station to the door counts in full, at full weight — one candidate had 89% of its counts on two nodes directly on the route home. Report `crime.night_route_node_share` separately from the area tier.
- **Adjacent boxes share anchors.** Two overlapping candidate boxes can contain the same 21 records; never add them.
- **Texture beats the total.** A predatory subset — antisocial behaviour, violence, theft from the person, robbery — separates a busy place from a dangerous one far better than the headline count. A transport interchange produces a large count of a specific, predatory kind.
- **Unmeasured is not clean.** A building too new for the street gazetteer can return almost nothing at its own address while the surrounding streets are busy.
- **Reading the street in person.** Chain convenience shops across London have had guards since retail theft rose in 2023, so a guard is background, not a signal. The signal is posture and fitting-out: two or more guards, one standing at the door, security tags on alcohol, meat and coffee, gates at the self-checkout exit. Then read the 20 m outside the shop. Compare a store fitted out defensively with one that is relaxed a mile away.
- **Personal discomfort can be a valid personal reason to walk away, and must never be written up as police evidence that an area is dangerous.** Keep the two sentences apart in the report.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 5`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.crime_6mo_count` — the fixed-window count, with the box specification and the months actually retrieved in `meaning`.
- `candidates[].landmines[]` with code **L3** when the counts sit on the route between the station and the front door.
- `candidates[].viewing_day_checks[]` — walk the station-to-door route after dark.
- `candidates[].axes[].unknowns[]` — any month the dataset did not have. Never fill a missing month with a zero, and never scale a short window up.
Numbers to record: window count, the four shifted counts as a range, the predatory subset, the top anchors with their shares, the share sitting on the walk home, the publication lag.
