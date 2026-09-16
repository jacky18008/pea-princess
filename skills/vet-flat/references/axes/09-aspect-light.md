Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 9 — Aspect, light and the floor plan

## Purpose
Judge how much daylight the flat will actually get, and read the plan for windowless rooms, blind walls and awkward geometry.
In a London winter, indoor brightness comes from sky openness, floor level and window area far more than from the compass.

## What counts as evidence
- **G** — a developer's or architect's plan with a north point; a daylight assessment in a planning document.
- **S** — "south facing" in the listing text; an agent-drawn plan with no compass.
- **C** — resident comments about darkness, overheating or facing a wall.
- **I** — an orientation read off a window photograph, a shadow, or the stack position.
- **U** — no plan, no compass, no photograph.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` and `python3 scripts/geo.py nearby --lat <lat> --lng <lng> --radius 100` (the lookup prints lat and lng) — what stands around the building.
2. `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 150 --brief` — the buildings, roads and railways the windows face.
3. `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250 --brief` — any consented scheme that will take the sky away, and any daylight assessment naming this building.
4. Compute the obstruction angle: the height of the facing obstruction over the distance to it, as an angle from the window.
5. Before the visit: street imagery, see `18-street-view.md`. `python3 scripts/streetview.py check --lat <lat> --lng <lng>` is free and says whether there is a panorama and how old it is; `fetch --toward-lat/--toward-lng` points the camera at the building. Count the storeys of the facing building in the picture and check them against the `building:levels` or `height` tag — OSM heights are often missing or wrong, and a photograph is the cheapest correction available. Class C, dated: quote the capture date with the angle.

## Method in fetch mode
Planning documents and mapping data are fetchable. Floor plans and marketing photographs are not — they sit on listing portals.

## Method in manual mode
Ask the user for:
1. The floor plan image at full size, plus any developer plan or site plan that carries a north point.
2. Photographs taken from the windows, and the time of day and season if known.
3. The floor number and which way the living room faces, in the agent's own words, so it can be tested against the plan.

## How to read the numbers
- `obstruction_angle_kill_deg` — an obstruction subtending more than this angle from the window, on a low floor, is the "almost no light" case.
- `sky_openness_good_obstruction_angle_deg` — below this, the sky in front of the window is effectively open.
- `min_sky_openness_note` — sky openness is the winter criterion; orientation is a summer and shoulder-season criterion.
- `floor_position_exclusions` — profile (some users exclude ground and basement outright).
- `reject_no_sky` — profile. When true, the almost-no-light case below is a hard fail rather than a deduction.
- `quiet_over_light` — profile. When true, the quiet elevation wins any conflict with the brighter one, short of almost no light.

## The floor plan, read three ways
1. **Window convention.** Within one consistent set of plans, external openings are always drawn. A room whose external wall carries no opening mark has no window, and that is plan-grade evidence, not a guess.
2. **Service-wing stacking.** Overlay the same projection on the other floors' plans. If every floor puts bathrooms, WCs, laundry and storage in that wing — rooms that need no window — the wing's external wall is a blind wall by design. A blind wall facing a railway or a main road suggests the living side was deliberately turned to the quiet side. That is a good hypothesis to take to the viewing with a compass, not a conclusion.
3. **Odd layouts.** If the main rooms are square and the projection is an add-on, the flat is still a complete standard unit without it, and the projection is a bonus. If the main rooms themselves are chopped into awkward leftovers by the projection, walk. Price a windowless second room as storage, and do not tell the agent what you value it at.

## Traps and lessons
- **Sky openness beats orientation in winter.** Through December to February the sun is above the horizon for only a couple of hours of usable light a day on average and most daytime hours are overcast, so what matters is the obstruction angle from the window, the floor level relative to the building opposite, and the glazed area. A high floor with open sky can beat a lower floor facing the "right" way.
- **The only light-related walk-away is "almost no light".** Low floor plus close obstruction (the facing building taller than the gap between them, obstruction angle above `obstruction_angle_kill_deg`), a deep light well, or a single elevation facing a wall. Anything else is scored, not fatal.
- **Quiet beats light unless there is almost no light.** Light serves the morning; quiet serves sleep, and sleep sits upstream of everything else. Half-decent light on the quiet side beats full light on the noisy side. In the same building at the same price, take the quiet elevation first and then look at the light.
- **Summer is the other half of this axis.** A west-facing living room with no cooling overheats through the late afternoon; a recessed balcony shades in summer and still admits low winter sun. Note both.
- **Agent plans usually have no compass**, so "south facing" in the text is copy, not data. Only a developer or architect plan settles it. Where the plan has none, the compass at the window on the viewing day does.
- **Marketing photography for a rental building is shot per unit type, not per flat** ("example furniture only"), so at best it fixes the orientation of the stack, not of this flat.
- **Date a window photograph** from landmarks on the skyline, the direction of shadows, leaf cover and any scaffolding — then say what the photograph can and cannot establish.
- **A split level with a spiral staircase** is a daily tax; note it here and again on axis 12.
- **Lower ground, garden and basement flats** are where the advert and the room differ most. The listing may say "garden flat" or "ground floor" where the floor plan, the EPC or the photographs say lower ground; photographs are shot upward toward the window. Check: window head height and any light well (sky openness is close to zero below pavement level), damp marks low on the walls and the smell on the viewing day, flood risk for the postcode (`ea_long_term_flood_risk` in `sources.yaml`, open), pavement noise and footfall at the window, security grilles, and where the bins live. A lower ground flat is not a rejection; an undisclosed one is an identity landmine on axis 1 and an almost-no-light question here.
- **A rejection made on orientation alone should be revisited** once sky openness is measured: several units rejected for "no direct sun" turned out to be acceptable on openness, while their other defects stood unchanged.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 9`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].landmines[]` with code **L2** when another building, a wall or a deep recess takes the sky away from the main windows.
- `candidates[].hard_filters[]` — the profile's no-sky rule and any floor-position exclusion.
- `candidates[].viewing_day_checks[]` — a compass reading at each window and a photograph of any works visible from it.
- `candidates[].photos_vs_reality_notes` — marketing photography for a rental building is shot per unit type, not per flat.
Numbers to record: floor level, obstruction angle in degrees and what it was measured against, distance to the facing building and its height, orientation in degrees, number of windowless rooms.
