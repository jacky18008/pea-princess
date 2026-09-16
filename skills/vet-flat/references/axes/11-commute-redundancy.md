Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 11 — Commute and route redundancy

## Purpose
Measure the door-to-door journey to a destination the user names, on one consistent basis, and check that the route survives a strike or a weekend closure.
A journey time is only half the axis; the other half is what happens on the day the line is shut.

## What counts as evidence
- **G** — the transport authority's journey planner output, with its legs and times; station locations from the same source.
- **S** — "ten minutes to the station" in a listing.
- **C** — a resident correcting the advertised walk ("more like 17 minutes").
- **I** — any time you assembled from more than one query.
- **U** — no journey could be planned.

Keep both provenance and uncertainty when shortening an answer. A landlord's “estimated
20 minutes” is a self-reported estimate, even when its quote has been checked against the
message. Write “Landlord estimate: 20 min; journey not checked”, not “Commute: 20 min ✓”.
An estimate below the user's limit can support a provisional comparison; it does not confirm
that the door-to-door requirement is met. Keep that hard filter unknown until adequate route
evidence exists. Official planner times remain predictions for the stated route, date and
arrival time; do not promote them to guaranteed real-world travel times.

## Method in shell mode
1. `python3 scripts/commute.py journey --from "<postcode or lat,lng>" --to "<destination address>" --arrive 09:00` — the destination is always an argument. Never build a destination into a script.
2. `python3 scripts/commute.py stations --lat <lat> --lng <lng> --radius 800` — every rail, underground and light-rail station within the redundancy walk.
3. `python3 scripts/commute.py redundancy --lat <lat> --lng <lng> --radius 800` — which strike families are reachable on foot and what grade that gives.
4. Run the journey three ways and keep them separate: average walking speed (the headline), fast walking speed (a sensitivity run only), and an entrance buffer added at the destination.

## Method in fetch mode
The journey planner answers plain GET requests with postcodes or coordinates and needs no key at this volume.

## Method in manual mode
Use supplied details first. Ask only the next essential missing detail, following the overall
three-question limit; these are not three mandatory onboarding questions:
1. The exact destination address and the time they need to arrive.
2. Which door of the destination they actually use, so the entrance buffer is right.
3. Whether they would rather sit still on one line for longer or change twice for a shorter total.

## How to read the numbers
- `commute_max_minutes` — profile. The headline is the door-to-door average-walking-speed number.
- `commute_entrance_buffer_min` — added at the destination, reported separately, never folded silently into the headline.
- `redundancy_walk_min` and `redundancy_walk_m` — the walk within which a second ticket counts.
- `station_to_door_walk_max_min` — profile, if the user sets one.
- `redundancy_min_grade` — profile. Grades are reported in `metrics.commute_redundancy_grade` and must carry the meanings the report schema fixes: **A** — two independent rail families within `redundancy_walk_min`. **B** — one rail family plus a bus route that genuinely serves this journey. **C** — one line only, no plan B.
- Say the finer reading in the finding rather than inventing a new letter: inside an A, whether the second family is at the same station or needs a 12 to 20 minute walk; inside a B, whether a second-family station sits just beyond the walk.

## The two strike families
- **Family one:** the underground and the light-rail network — the same union constituency, and they usually stop together.
- **Family two:** national rail, the overground and the cross-London line — a different constituency.
- **River services** are a third, uncorrelated ticket. Buses are not a family: they are what is left when both families fail.
- **Two lines of the same family are not redundancy.** The classic false A is a station with two underground-family lines: it is not an A, unless a second-family station is one stop or a short walk away.
- The two failure modes the grade exists for are periodic underground strikes and chronic weekend engineering work on national rail.

## Traps and lessons
- **Never splice.** Nearest station, total time and number of changes must all come from the same single journey. Assembling the best leg from three different routes produces a journey nobody can take.
- **Zero-wait samples.** Check the leg times: if arrival at the platform equals the departure time, the sample assumes a perfect connection. Report a five-minute and a ten-minute wait scenario alongside it.
- **Walking legs can contain zero-time in-station segments.** A 709 m walk shown as five minutes included a moving-link segment counted at zero, so it is not evidence of a short station-to-door walk. Read the legs, not the total.
- **The three speeds are not interchangeable.** The average-speed run is the value that goes in the table; the fast run is sensitivity; the entrance buffer is a third number. Never let one stand in for another.
- **Advertised walk times are claims.** Record a resident's correction alongside the listing,
  with its source and route scope; disagreement is a finding, not automatic proof either is true.
- **A postcode centroid is not the door.** Record the coordinate provenance with the result, and say it is not a verified doorway.
- **Say what you optimised.** Sitting still on one direct line for 55 minutes can be better than changing twice for 35, especially on a low-energy day. If the user's preference is a direct route, say that the ranking reflects it.
- **Off-peak, night and weekend journeys are different journeys.** A grade earned at 09:00 on a weekday says nothing about getting home at midnight; check the last services on both families.
- **The walk home is an axis-5 question as much as an axis-11 one.** Cross-reference the route against the crime anchors before grading either.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 11`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.commute_min` and `metrics.commute_redundancy_grade`.
- `candidates[].hard_filters[]` — one row for the profile's maximum door-to-door time and one for its minimum redundancy grade.
- `candidates[].axes[].unknowns[]` — anything the journey planner could not resolve, such as an ambiguous destination.
Numbers to record: door-to-door minutes at average walking speed, the fast-walk sensitivity, the entrance buffer, the number of changes, the station walk in minutes and metres, and the stations reachable on foot with their strike family.
