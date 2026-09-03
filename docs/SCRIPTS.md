# Scripts — usage

One section per script in `skills/vet-flat/scripts/`. Append your own section at
the end; do not rewrite anyone else's. Every script prints one JSON object to
stdout, takes `--verbose` to echo the curl commands to stderr, and exits 0 on
success, 2 on a usage error, 1 on a fetch failure.

## `geo.py` — postcodes.io (open, no key)

```
geo.py lookup "SE1 9SG"
geo.py reverse --lat 51.504963 --lng -0.087625 [--radius 200] [--limit 10]
geo.py nearby  --lat 51.504963 --lng -0.087625 --radius 2000
geo.py cover   --lat 51.504963 --lng -0.087625 --radius 3200 [--step 1500]
geo.py box     --lat 51.504963 --lng -0.087625 --half-m 150
```

`lookup` gives the coordinates and the admin geography the other axes key off.
`reverse` and `nearby` go the other way. `cover` is the 2-mile sweep enumerator:
it tiles a bigger circle with several `nearby` calls on a hex grid and dedupes.
`box` is the rectangle `crime.py` queries with; `haversine_m()` and `bbox()` are
importable by other scripts, no network.

Two hard API caps, both silent: **radius is capped at 2000 m** (a bigger value
returns HTTP 200 and the 2000 m answer anyway, so `nearby` refuses it outright)
and **limit is capped at 100 rows**. In central London the row cap bites long
before the radius — a 2000 m call around London Bridge stops at about 330 m — so
`nearby` reports `saturated` and `cover` reports `tiles_saturated`, `complete`
and `saturation_reach_m`. A saturated result is a floor, not a census; lower
`--step`.

```console
$ geo.py lookup "SE1 9SG"
{ "ok": true, "http_status": 200, "evidence_class": "G",
  "postcode": "SE1 9SG", "lat": 51.504963, "lng": -0.087625,
  "admin_district": "Southwark", "admin_ward": "London Bridge & West Bermondsey",
  "lsoa": "Southwark 006F", "msoa": "Southwark 006",
  "outcode": "SE1", "region": "London", ... }

$ geo.py box --lat 51.504963 --lng -0.087625 --half-m 150
{ "poly": "51.503616,-0.089790:51.506310,-0.089790:51.506310,-0.085460:51.503616,-0.085460",
  "width_m_actual": 299.7, "height_m_actual": 299.7,
  "half_m_actual_ns": 149.8, "half_m_actual_ew": 149.8, ... }
```

## `crime.py` — data.police.uk (open, no key, empty robots.txt)

```
crime.py latest
crime.py box --lat 51.504963 --lng -0.087625 [--half-m 150] [--months 6] [--end 2026-06]
crime.py box --lat 51.504963 --lng -0.087625 --route "51.505019,-0.086092;51.504963,-0.087625"
             [--corridor-m 30]
```

`latest` is the newest **data** month, not today and not an event date;
publication runs 2-3 months behind. `box` fetches all-crime for a fixed window
of the last N available months over the `geo.bbox` rectangle. A month that fails
is listed in `months_missing` and is **never scaled or extrapolated**; totals
cover `months_fetched` only.

Output carries: `total`, `per_month`, `by_category` (all 14 police categories,
zero-filled), `predatory_subset` (anti-social behaviour + violent crime + theft
from the person + robbery — the split that separates "busy" from "dangerous"),
`top_anchors` with the top anchor's share, `anchor_dispersion` (a high single
anchor share means a point source such as a station or a retail node), and
`sensitivity` — the same box re-fetched with the centre moved 20 m N/S/E/W, so
you can see whether the number is an artefact of where the pin went.

Request budget: months x 5 positions (default 30), plus `months` more with
`--route`. Past months never change, so a re-run is served from cache.

```console
$ crime.py box --lat 51.504963 --lng -0.087625 --half-m 150 --months 6
{ "ok": true, "months_fetched": ["2026-01", ..., "2026-06"], "months_missing": [],
  "total": 583,
  "per_month": {"2026-01": 92, "2026-02": 75, "2026-03": 119, "2026-04": 100,
                "2026-05": 86, "2026-06": 111},
  "by_category": {"theft-from-the-person": 209, "other-theft": 117,
                  "violent-crime": 93, "anti-social-behaviour": 42, "robbery": 31, ...},
  "predatory_subset": {"count": 375, "share_of_total": 0.643, ...},
  "top_anchors": [{"anchor": "On or near Hospital", "count": 142, "share_of_total": 0.244}, ...],
  "anchor_dispersion": {"top5_share_of_total": 0.892, "distinct_anchors": 10, ...},
  "sensitivity": {"counts": {"centre": 583, "north_20m": 623, "south_20m": 581,
                             "east_20m": 583, "west_20m": 622}, "spread": 42, ...} }
```

`--route` counts incidents within `--corridor-m` (default 30 m) of the
station-to-door polyline, fetched over its own rectangle. The rule is that
**incidents on the walk home count in full and must not be discounted as point
sources**. Watch the resolution: police.uk snaps every crime to a sparse set of
anonymised map points, and around London Bridge the nearest one sits about 61 m
off a 106 m walk line, so a 30 m corridor can return zero from a busy street.
The output therefore also carries `nearest_anchor_m`, a `corridor_ladder`
(counts at 30 / 60 / 100 / 150 / 250 m) and a `resolution_warning` that says
plainly when a zero is a resolution artefact rather than a clean bill.

## `commute.py` — TfL Unified API (no key needed at low volume)

```
commute.py journey --from "SE1 9SG" --to "WC2R 2LS" [--arrive 09:00]
                   [--date next-weekday|YYYYMMDD] [--door-buffer-min 0] [--plans all,rail,bus]
commute.py journey --from "51.5049,-0.0876" --to "51.5119,-0.1166"
commute.py stations   --lat 51.504963 --lng -0.087625 [--radius 800]
commute.py redundancy --lat 51.504963 --lng -0.087625 [--radius 2000]
```

`--to` is required; no destination is hard-coded anywhere. An optional free
`app_key` can go in a plain `.env` next to the scripts as `TFL_APP_KEY=...`
(parsed by hand, no package; an environment variable of the same name wins, and
the key is redacted from every URL the script reports).

`journey` runs three plans — `all` (TfL picks any mode), `rail` (tube, DLR,
Overground, Elizabeth line, national rail, walking) and `bus` (bus, walking) —
and reports the fastest of each with legs, `changes`, `walking_min`,
`first_leg_walk_min` and `alternatives_min`. TfL chains legs back to back, so
`wait_sample_note` flags a plan whose connections depart at the exact minute the
previous leg arrives: a zero-wait sample that has budgeted nothing for waiting.
`--door-buffer-min` is 0 by default and applied only when asked.

```console
$ commute.py journey --from "SE1 9SG" --to "WC2R 2LS" --arrive 09:00 --date 20260907
{ "fastest_plan": "all", "fastest_min": 24, "rail_only_min": 32, "bus_only_min": 24,
  "plans": { "rail": { "duration_min": 32, "changes": 0, "walking_min": 28,
                       "first_leg_walk_min": 17, "alternatives_min": [32, 32, 32],
                       "legs": [ {"mode": "walking", "line": null, "duration_min": 17,
                                  "from": "SE1 9SG", "to": "Cannon Street Underground Station"},
                                 {"mode": "tube", "line": "District", "duration_min": 4,
                                  "from": "Cannon Street Underground Station",
                                  "to": "Temple Underground Station"}, ... ],
                       "wait_sample_note": "2 of the 2 connections ... depart at the exact minute
                                            the previous leg arrives ..." } } }
```

`stations` lists nearby tube, DLR, Overground, Elizabeth line, national rail and
river-bus stations with their lines and a walking estimate (straight line x 1.3,
at 80 m per minute — an **estimate** of street distance, not a routed walk).
`redundancy` sorts them into strike families — A = tube + DLR, B = national rail
+ Overground + Elizabeth line, C = river bus — and grades: **A** both A and B
within an 800 m walk, **B** both but the second 800-1600 m, **B-** one within
800 m plus another beyond 1600 m or bus only, **C** one family only. Two lines
of the same family do not count as redundancy; they tend to strike together.

```console
$ commute.py redundancy --lat 51.504963 --lng -0.087625
{ "grade": "A", "nearest_family": "family_B",
  "nearest_family_walk_m": 169, "second_family_walk_m": 301,
  "families": { "family_A": {"nearest": "London Bridge Underground Station",
                             "lines": ["Jubilee", "Northern"], "walk_m_estimate": 301},
                "family_B": {"nearest": "London Bridge Rail Station",
                             "lines": ["Southeastern", "Southern", "Thameslink"],
                             "walk_m_estimate": 169},
                "family_C": {"nearest": "London Bridge City Pier", "walk_m_estimate": 427} },
  "reason": "Both families are within an 800 m walk ... so a strike on one leaves the other standing.",
  "explanation": "Two lines of the same family do not count as redundancy; they tend to strike together ..." }
```
