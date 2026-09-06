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

## `company.py` — Companies House (official, free, no key, no robots.txt)

```
company.py search         --name "Get Living" [--limit 40]
company.py profile        08854998 [--skip-filings] [--api]
company.py filings        08854998 [--limit 40] [--page 1]
company.py address-search --query "SE1 9SG" [--limit 100] [--pages 1]
company.py heat-supplier  --name "Loka Energy"
```

Reads the public HTML site
`find-and-update.company-information.service.gov.uk`. That host serves **no
robots.txt at all** (404), so nothing is disallowed; the 1.2 s per-host spacing
still applies. The REST API is optional: put `COMPANIES_HOUSE_KEY=<key>` in a
plain `.env` next to the scripts (KEY=VALUE lines, parsed by hand — no package)
or in the environment, then `profile --api` adds the JSON record. Without a key
the API path returns `access: manual` instead of failing.

`search` uses **`/advanced-search/get-results?companyNameIncludes=`**, not
`/search/companies`, because the plain search page carries no company status —
a dissolved shell looks exactly like a trading company there. Every row comes
back with `status`, `dissolved`, `dissolved_on`, `company_type`, `sic_codes` and
the registered office, plus `dissolved_count` and a `same_name_warning`: match
on the company **number** printed on the tenancy agreement, never on the name.
Overseas entities say `registration_event: "Registered"` rather than
`"Incorporated"`; the date lands in the same field.

`profile` makes four requests (overview, `/charges`, `/officers`,
`/filing-history`; `--skip-filings` drops to three) and returns status,
incorporation and dissolution dates, company type, SIC codes, registered office,
previous names, accounts (last made up to / next due / `overdue`), confirmation
statement dates, `charges_count` (total, outstanding, satisfied, part
satisfied), `officers` (name, role, appointed, resigned, `active_officer_count`)
and `insolvency_flag`. Officer records carry **names, roles and dates only** —
dates of birth, nationality and country of residence are on the page and are
deliberately not extracted.

`landlord_type_hint` is an **inference (class I)** from the SIC code:
`68209` → `owner_or_investor` (letting and operating of own or leased real
estate — likely owns the property), `68310` → `agent_not_owner` (real estate
agency), `68320` → `managing_agent` (management on a fee basis), `68100` →
`buying_selling`, anything else → `other`. Owner beats agent when both are
present. Every hint repeats the note: *brand != landlord; the legal entity named
on the tenancy agreement is what matters.*

`filings` flags the three filing types that show a change of hands:
`registered_office_changes` (AD01), `name_changes` (CERTNM) and
`accounts_filings` with their made-up-to dates. The site paginates at ~25 rows;
`pages_available` tells you what else is there and `--page` fetches it.

`address-search` probes `/advanced-search/get-results?registeredOfficeAddress=`.
The site's own count is a loose token match — "SE1 9SG" reported 3,259 results —
so the script re-filters rows on the normalised address and reports both
`total_reported_by_site` and `count`. Its purpose is to find the building's
Resident Management Company or Right to Manage company; names matching RMC/RTM
markers land in `rmc_rtm_candidates`. **Zero RMC/RTM entries at an address means
residents may have no route to replace the managing agent** — an inference
(class I), not a register fact: an RMC can be registered at its accountant's
address, and an RTM company can be formed later. Confirm from the lease.

`heat-supplier` is `search` + `profile` + the latest accounts PDF link, for
checking who runs a communal heat network.

```console
$ company.py search --name "Get Living" --limit 3
{ "source_url": ".../advanced-search/get-results?companyNameIncludes=Get+Living",
  "http_status": 200, "ok": true, "evidence_class": "G",
  "total_reported_by_site": 66, "count": 3, "dissolved_count": 1,
  "results": [ { "company_number": "07883003", "name": "GET LIVING IT LTD",
                 "status": "Dissolved", "incorporated": "15 December 2011",
                 "dissolved_on": "20 April 2021", "sic_codes": ["62090", "86900"],
                 "address": "Rosedale Wellbrookside, Peterchurch, Hereford ... HR2 0SP" },
               { "company_number": "15778219", "name": "GET LIVING (BIRMINGHAM) D LIMITED",
                 "status": "Active", "incorporated": "14 June 2024",
                 "sic_codes": ["68209"], "address": "1 East Park Walk, London, England E20 1JL" }, ... ],
  "same_name_warning": "Several companies can share almost the same name, and a dissolved shell
                        keeps its name on the register forever. Match on the company NUMBER ..." }
```

## `redress.py` — compliance registers (CMP, Heat Trust, GLA rogue checker)

```
redress.py cmp        --agent "Home-Made"
redress.py heat-trust --site "Greenwich Peninsula"
redress.py heat-trust --supplier "Loka"
redress.py rogue      --name "Smith" [--address "Ilford"]
redress.py prs
redress.py tpo
```

**`cmp`** — Client Money Protect. The `/agent-search/` page is a shell, but the
search is server-side: the form posts
`action=member_search_third_party&keyword=<text>&auto=0` to
`/wp-admin/admin-ajax.php` and gets JSON back, and that exact path is the one
line `robots.txt` explicitly **allows** inside an otherwise disallowed
`/wp-admin/`. Matches carry name, membership number (`CMP015515`), address and
membership status. `valid_until` is always `null` — the API returns a status,
not an expiry date; ask the agent for the certificate. The API also returns each
member's email and phone; the script drops both. A miss returns
`evidence_class: "U"` and lists the five other approved schemes (Propertymark,
Money Shield, RICS, Safeagent, UKALA) — CMP is one of six, so absence here is
not proof an agent is uninsured.

**`heat-trust`** — plain HTML at `heattrust.org/our-members`, evidence class
`C` (a voluntary industry scheme's own register, not a government one). Returns
`total_members`, `total_sites`, `consumers_protected` and the page's `as_at`
date, and matches against both the participant list and the site list. London
sites are listed as `<li>` items under an underlined borough heading; everywhere
else they are `<br>`-separated text under a local-authority heading — the parser
handles both, and the parsed counts are asserted against the page's own
headline numbers. Registration is voluntary and a supplier may register some
networks and not others, so a miss says nothing about whether the building has a
heat network.

**`rogue`** — the GLA Rogue Landlord and Agent Checker, a server-rendered Drupal
exposed form: `?name=` and `?address=` filter the result cards with no
JavaScript. Each card yields name, enforcement action type, enforcement
authority (borough), rental property address, offence, offence description,
fine, enforcement date and record expiry. Hits are evidence class **G**; a miss
is **U** and says so in words: *no entry found for query X in the checker (which
lists only enforcement actions boroughs chose to publish)*.

**`prs` / `tpo`** — `access: manual`, no fetch, with the URL and the questions
to put to the agent. The Property Redress Scheme's public feed ignores every
filter parameter and returns the same ten recent members whatever you ask, so it
cannot answer a membership question; `tpos.co.uk/robots.txt` carries an explicit
`User-agent: ClaudeBot / Disallow: /`.

```console
$ redress.py rogue --name "Reptons"
{ "source_url": ".../rogue-landlord-and-agent-checker?name=Reptons",
  "http_status": 200, "ok": true, "evidence_class": "G", "count": 1,
  "results": [ { "name": "Reptons Global Property LTD (07523446)",
                 "enforcement_action_type": "Civil Penalty (Housing and Planning Act 2016)",
                 "enforcement_authority": "Redbridge",
                 "address": "United Kingdom: IG1 3BW - FLAT 1, 80, WESTBURY ROAD null, ILFORD",
                 "offence": "Duty of manager to maintain living accommodation ... SI_REGULATION 8 p.1",
                 "fine": "5000", "enforcement_date": "Wednesday 11 April 2029",
                 "record_expires": "Thursday 11 April 2030" } ],
  "caveat": "The checker holds only what London boroughs sent the GLA ... Absence is not a clean record." }
```

## `landregistry.py` — HM Land Registry open data (official, keyless SPARQL)

```
landregistry.py price-paid --postcode "SE1 2BE" [--since 2015] [--paon "ST. SAVIOURS WHARF"]
                           [--limit 500] [--method post|get]
landregistry.py title --help-only
```

`price-paid` queries the public SPARQL endpoint
`https://landregistry.data.gov.uk/landregistry/query` with
`Accept: application/sparql-results+json`. No key, no login, no fee. Both forms
work — POST with a `query=` form field (the default, because long queries
overflow a URL) and GET with `?query=`; `--method get` switches. The exact
SPARQL is in the script's docstring and is echoed back in the output's `sparql`
field. Postcodes must be upper case and spaced as the register holds them; the
script normalises `se12be` to `SE1 2BE` for you.

Each transaction is `{date, price, paon, saon, street, town, property_type,
new_build, estate_type, category}`, sorted by date. On top: `count`,
`earliest_transaction`, `latest_transaction`, `new_build_count` and
`earliest_new_build_transaction`. **A `new_build: true` row is the Land Registry
recording the first sale of a newly built dwelling, so the earliest one in a
postcode is a hard lower bound on the completion year** — independent of the
brochure. The reverse does not hold: build-to-rent blocks that were never sold
flat by flat, and flats sold under a different postcode, leave no new-build row
at all. `--paon` adds `same_building_matches` and a price range for one building
or one flat number.

`title --help-only` fetches nothing. The title register is the only source that
names the registered proprietor and the lease terms, and it stacks three
barriers: a Cloudflare interactive challenge on
`search-property-information.service.gov.uk` (its robots.txt is challenged too),
a GOV.UK One Login sign-in, and **£7 per title register / £11 per filed
document**. The command prints the route and the fields to paste back:
proprietor name(s), title number, tenure, date of registration, lease term and
start date, and any restrictions or charges.

```console
$ landregistry.py price-paid --postcode "SE1 2BE" --paon "ST. SAVIOURS WHARF"
{ "query": {"postcode": "SE1 2BE", "paon": "ST. SAVIOURS WHARF"},
  "source_url": "https://landregistry.data.gov.uk/landregistry/query",
  "http_method": "POST", "http_status": 200, "ok": true, "evidence_class": "G",
  "count": 101, "new_build_count": 3, "earliest_new_build_year": 1998,
  "earliest_transaction": { "date": "1995-02-17", "price": 175000,
                            "paon": "ST. SAVIOURS WHARF", "saon": "FLAT 38",
                            "street": "MILL STREET", "town": "LONDON",
                            "property_type": "flat-maisonette", "new_build": false,
                            "estate_type": "leasehold",
                            "category": "standardPricePaidTransaction" },
  "earliest_new_build_transaction": { "date": "1998-02-26", "price": 325000,
                                      "saon": "FLAT 46", "new_build": true, ... },
  "same_building_matches": {"count": 101, ...},
  "same_building_price_range": {"min": 101000, "max": 2000000,
                                "first_date": "1995-02-17", "last_date": "2026-05-26"} }
```

## `planning.py` — GLA Planning London Datahub (open guest Elasticsearch, no key)

```
planning.py near   --lat 51.5045 --lng -0.0865 [--radius 250] [--since 2018] [--limit 200] [--bbox]
planning.py search --text "Emery Wharf" [--lpa "Tower Hamlets"] [--since 2015] [--limit 50]
planning.py stages --reference "26/AP/0812" --lpa Southwark
planning.py planit --postcode "SE1 9SG" [--km 0.3] [--limit 20]
```

One index covering all 33 London planning authorities plus the two Mayoral
Development Corporations (LLDC, OPDC) — 1,280,679 applications. `near` is the
construction-risk question ("what is going up next door?"), `search` finds a
named site or street, `stages` turns one case's status into plain English for
someone about to sign a tenancy, and `planit` is the fallback.

**Geo fields.** `_mapping` is 403 for the guest role, so the shape was read off
`_search`. `centroid` is a real **geo_point on 100 % of documents**, so `near`
uses a `geo_distance` filter and a `_geo_distance` sort — no conversion needed.
`centroid_easting`/`centroid_northing` (OSGB36 metres) exist on 94 % and never
where `centroid` is missing, so they add no coverage; `--bbox` uses them anyway
through `wgs84_to_osgb36()`, a pure-Python Helmert + Transverse Mercator that
lands ~5 m from OSTN15 (the projection half is exact against the OS worked
example; the datum shift is the lossy part). The two paths agree: at London
Bridge, `geo_distance` returns 268 applications and the square bbox returns 348,
which trims to the same 268 on the true distance.

**Field types that bite.** `lpa_name`, `status`, `decision`, `application_type`,
`postcode` and `borough` are `text` with **no `.keyword` sub-field** — aggregate
on them and Elasticsearch throws; filter with `match_phrase`. `development_type`,
`ward` and `id` are keywords. Date fields are `dd/MM/yyyy`, so a `range` query
**must** pass `"format": "dd/MM/yyyy"` or an ISO bound raises `parse_exception`.
`hits.total` caps at 10000 unless you send `"track_total_hits": true`.
`application_details.building_details` is **nested**: a plain `exists` on
`...building_details.no_storeys` returns 0; it needs a `nested` query.

`tall_building_hint` is a screen, not a survey: it fires on stated storeys ≥ 8
(including the London phrasing "part 26 and part 16 storeys" and word numbers
like "eight storey"), on ≥ 100 proposed residential units, or on the words "tall
building"/"tower" — with Tower Hamlets, Tower Bridge, Tower Hill and cooling
towers subtracted. `tall_building_reasons` says which rule fired.

`portal_url` comes from `references/boroughs.yaml`, so the model can send the
user to the borough's own case file. 23 of the 33 portals disallow crawling,
which is why the Datahub is the route in and the portal is a link, not a fetch.
LLDC and OPDC are not boroughs and get `portal_url: null` plus a note.

Caveats printed on every result: the Datahub carries applications **as boroughs
report them**, small householder cases may be absent, and **zero hits is not
proof of no activity**. `search` matches `site_name`, `street_name` and
`description` only — a marketing name never filed with the application will miss
(this is why "Emery Wharf" returns 0). `planit` is a third-party mirror whose
`/api/applics/` path is **robots-disallowed**: single lookups only, and only
after the Datahub comes back empty. Its `search=` parameter matches the
description text alone, so this tool uses `pcode` + `krad`.

```console
$ planning.py near --lat 51.5045 --lng -0.0865 --radius 250 --limit 12
{ "ok": true, "http_status": 200, "evidence_class": "G",
  "geo_filter": "geo_distance on centroid (geo_point)",
  "count": 12, "total_matching": 268,
  "results": [
    { "reference": "26/AP/0812", "lpa_name": "Southwark", "distance_m": 6,
      "address": "The Shard, 32 London Bridge Street, London", "postcode": "SE1 9SG",
      "description": "The View from the Shard", "status": "Approved", "decision": "Approved",
      "decision_date": "29/04/2026", "tall_building_hint": false, "storeys": null,
      "portal_url": "https://planning.southwark.gov.uk/online-applications/" },
    { "reference": "19/AP/2089", "distance_m": 61, "tall_building_hint": true,
      "tall_building_reasons": ["26 storeys"],
      "description": "Details of Condition 25 (Flue/Extraction - CHP) of plann…" }, ... ],
  "caveat": "the Datahub carries applications reported by boroughs; …" }

$ planning.py stages --reference "26/AP/0812" --lpa Southwark
{ "record": {...},
  "what_this_means": [
    "Status Approved = permission granted.",
    "Granted 2026 with no commencement recorded = works could start at any time. The
     permission expires 29/04/2029, so works must start before then." ],
  "conditions": { "in_api": false, "portal_url": "https://planning.southwark.gov.uk/…",
                  "how_to_read_the_rest": "… never the discharge status of each one …" } }
```

## `roads.py` — OpenStreetMap via Overpass (open, ODbL, no key)

```
roads.py near        --lat 51.5045 --lng -0.0865 [--radius 300]
roads.py facade-note --lat 51.5045 --lng -0.0865 [--radius 300]
```

What is physically around the flat, in **one** Overpass query per call:
`trunk_or_primary_road` and `secondary_road` (within `--radius`),
`railway_surface`, `railway_tunnel_portal`, `tube_surface`,
`helipad_or_aerodrome` (1000 m), `night_economy` (100 m),
`food_smell_sources` (60 m), `waste_or_recycling` (150 m), `supermarket`
(400 m, with a walking estimate), `park_or_green` (400 m) and
`obstruction_candidates` (buildings within 60 m carrying `building:levels` or
`height`). The fixed radii are the nuisance distance for that thing, so
`--radius` widens only the linear features.

**Overpass refuses browser User-Agents with 406** — the inverse of every other
host in this repo — so this script sends `_fetch.TOOL_UA`. It also rate-limits by
dropping the connection rather than returning 429, so `_retryable()` treats any
transport failure as a backoff (2 / 4 / 8 s) and then falls to
`overpass.kumi.systems`. `attempts` in the output records every try, and
`overpass_instance` says which one answered. `overpass-api.de/robots.txt`
disallows `/api/` for everyone; this is a single user-directed query per flat,
so keep it that way — do not loop it over a list of addresses.

Distances are **point-to-segment against the real `out geom` geometry**, so a
road that runs past the flat is measured where it actually passes, and a point
inside a polygon (a park, an industrial estate) scores 0 m. Every distance is an
integer in metres; `null` means nothing of that kind is *mapped* inside that
radius — OSM is crowd-sourced, so that is a gap in the map, not proof of quiet.
`count` counts OSM elements (one road is split into many ways), so read `names`
instead. A tunnel way's end node is only reported as a portal when it is shared
with a surface railway way; otherwise it is listed under
`unconfirmed_way_ends` as what it usually is, a mapper's way split.

`obstruction_candidates` gives distance, bearing and levels/height per
neighbouring building so the model can judge daylight:
**angle ≈ atan(height / distance)**, and over 45° on a low floor means very
little sky. Height comes from the `height` tag where OSM has one and otherwise
`building:levels × 3.0 m`. The facade rule is generic and fires whenever a
trunk or primary road is within 60 m.

```console
$ roads.py near --lat 51.5045 --lng -0.0865 --radius 300
{ "ok": true, "evidence_class": "C", "overpass_instance": "https://overpass-api.de/api/interpreter",
  "attribution": "© OpenStreetMap contributors, ODbL 1.0",
  "trunk_or_primary_road": { "count": 64, "names": ["Tooley Street", "Borough High Street", …],
      "nearest": {"distance_m": 142, "name": "Tooley Street", "ref": "A200",
                  "highway": "primary", "maxspeed": "20 mph", "direction": "NNE"} },
  "railway_surface":  {"nearest": {"distance_m": 62, "name": "South Eastern Main Line"}},
  "tube_surface":     {"count": 0, "nearest": null},
  "railway_tunnel_portal": {"count": 0, "count_unconfirmed_way_ends": 5},
  "night_economy":    {"count": 2,  "nearest": {"distance_m": 11, "name": "Bar 31"}},
  "food_smell_sources": {"count": 3, "nearest": {"distance_m": 19, "name": "Aqua Shard"}},
  "supermarket":      {"nearest": {"distance_m": 32, "name": "M&S Food",
                                   "walk_minutes_street_estimate": 1}},
  "park_or_green":    {"count": 3, "names": ["Guy Street Park", "Leathermarket Gardens"]},
  "waste_or_recycling": {"count": 0}, "helipad_or_aerodrome": {"count": 0},
  "obstruction_candidates": { "count": 3, "worst_first": [
      {"name": "The Shard", "distance_m": 0, "contains_point": true,
       "building_levels": 95.0, "height_m": 310.0, "obstruction_angle_deg": 90},
      {"name": "Shard Place", "distance_m": 41, "direction": "WNW",
       "building_levels": 26.0, "height_m_estimate": 96.2, "obstruction_angle_deg": 66.9}] },
  "facade_note": null, "facade_note_trigger_m": 60,
  "not_found": {"what": ["secondary_road", "tube_surface", "helipad_or_aerodrome",
                         "waste_or_recycling"], "meaning": "… a gap in the map …"} }

$ roads.py facade-note --lat 51.505375 --lng -0.085706     # 30 m off the A200
{ "trunk_or_primary_road": {"distance_m": 30, "name": "Tooley Street", "ref": "A200"},
  "facade_note": "the building has a road-facing and a quiet side; ask which side the
                  flat's windows face" }
```

## `sweep.py` — area sweep orchestrator (calls the other nine)

```
sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/
sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
         --profile profile.yaml --candidates candidates.txt \
         --max-buildings 4 --out sweep/
sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/ --dry-run
```

One address in, one compact JSON file per candidate building out. This is
`references/axes/00-area-sweep.md` turned into a program, and the whole point is
the cost gate: **the model reads JSON, never a page.** It imports the other
scripts as modules (no subprocesses), so every fetch still goes through
`_fetch.fetch` with its 1.2 s per-host spacing and its on-disk cache.

**Options.** `--anchor` takes a postcode or `lat,lng`. `--radius` is metres,
default 800, refused above 3300 (about two miles) and warned about above 1200.
`--dest` is the commute destination and is required unless `--profile` sets
`commute.destination`; `--arrive` overrides the profile's arrival time.
`--profile profile.yaml` supplies the hard filters — with no profile the run says
so and filters nothing. `--candidates file.txt` takes addresses or postcodes, one
per line, and those buildings are **always** kept: an exclusion or a failed filter
is recorded against them but never drops them. Caps, all with sensible defaults:
`--max-streets` (0 = no cap), `--max-postcode-lookups` 120, `--postcode-fallback` 40,
`--max-filter-buildings` 25, `--certs-per-building` 8, `--max-buildings` 8,
`--crime-months` 6, `--crime-half-m` 150, `--planning-radius` 250,
`--roads-radius` 300. `--resume` reuses the stage files already in `--out`.
`--dry-run` locates the anchor, counts the streets and prints the plan.

**The register refuses busy streets.** A street search that would return too many
rows gets the register's own page instead — *"Too many results for this address.
Search by postcode instead."* — and it hits exactly the streets with the most homes
on them (6 of 64 streets in a 400 m circle at London Bridge, including Tooley
Street, Borough High Street and Union Street). `epc.search` now recognises that
page, keeps `ok: true` and sets `too_many_results`, and the sweep does what the page
says: it re-searches by postcode, nearest first, using the postcodes already primed
from one `geo.nearby` call, capped by `--postcode-fallback` (default 40, 0 = off).
What the cap left out is listed in `not_found` with the exact commands. Without this
the sweep silently loses its best streets.

Two more of the register's answers used to read as fetch failures, which is the one
thing the `not_found` table exists to prevent: a postcode with nothing on it serves
*"No results for SE1 9BS"*, and a street with nothing on it serves *"A certificate
was not found at this address"*. Neither carries the results table the old content
assertion looked for. `epc.search` now accepts both, keeps `ok: true`, sets
`no_results` and fills `not_found` — so a nil result and a broken request no longer
look the same. In the demo run that moved 55 rows out of the failure column.

**Enumeration is Overpass then the energy register, not postcodes.io.**
postcodes.io returns at most 100 rows per call, so around London Bridge a 2000 m
request stops at about 330 m: it can locate a point but it can never census a
circle. So stage 1 asks OpenStreetMap for the **named** ways in the circle with
`highway` in residential, living_street, tertiary, unclassified, pedestrian or
service (the `["name"]` filter is what keeps unnamed service roads out), then runs
one `epc.search --street --town` per street name — a street search returns 190+
certificates in one page. postcodes.io is then used only to turn each
certificate's postcode into coordinates, primed with a single `geo.nearby` call
and topped up one lookup at a time up to the cap.

**Grouping.** Certificates become buildings on `building name or number + street +
outcode`, which is also the candidate's file name (`4--london-bridge-street--se1`).
The flat number is never in the key, so two flats in one building are one
candidate. A number range collapses to its first number ("4-6" and "4" are one
building) and street abbreviations expand ("Weston Rd" and "Weston Road" are one
street) — but only on the **last** word, because "St. Thomas Street" is Saint
Thomas, not Street Thomas. A letter suffix stays: 4A and 4 are different
addresses. The street on the certificate beats the street that was searched, so a
building found twice — once by the census, once by a user-supplied postcode — lands
on one key.

The register also spells the same street two ways: "4 London Bridge Street" and
"4 London Bridge" are one block and arrive as two candidates. A merge pass runs
after grouping — same building token, same outcode, one street name a word-prefix
of the other — and folds the shorter spelling into the longer, keeping every
certificate and the nearer distance reading. What was folded is listed in the
building's `merged_from` and in `buildings.json` under
`merged_abbreviated_streets`, so a reader can undo the judgement.

**Stage 1b exclusions** are name patterns, and they mark rather than delete:
`student_accommodation` (student, hall of residence, dormitory),
`serviced_apartments` (serviced apartments/suites, aparthotel, short stay or
short let, holiday lets), `hotel_or_hostel` (hotel, hostel, motel, guest house)
and `care_or_retirement` (care/nursing/residential/rest home, hospice, retirement
home or village, sheltered housing, extra care, almshouse). Every excluded
building keeps an `excluded_reason` naming the words that matched, and appears in
`summary.md`, because a pattern list is a guess about a name and the reader may
disagree with it.

**Stage 2** samples up to `--certs-per-building` certificates *spread across* the
building's list — never the first eight, because a big block's first certificates
are all one floor and one layout — and computes median area, earliest assessment
year, heating classes, ground-floor share, assessment types and air permeability.
The filters follow the profile: building age against `max_building_age_years`,
`min_floor_area_sqft` where **any** flat that clears it keeps the building, and
the ground-floor rule (`floors.reject_ground_floor`, or the words "ground floor"
in the profile's `avoid:` list) recorded per building but applied per flat (it fails a
building only when every sampled flat is ground or basement). Rows use the
report-schema `hard_filter` shape, so an unknown is the string `"unknown"` and
never a pass — and an unknown keeps the building rather than dropping it silently.

**Stage 3** runs, for survivors only and capped by `--max-buildings`:
`crime.box`, `commute.journey` (plans `all` and `rail`) plus `commute.redundancy`,
`planning.near`, `roads.near`, `landregistry.price_paid`,
`company.address_search`, and `redress.heat_trust` **only** when a sampled
certificate says the heating is a community network. Each call is wrapped, so one
dead source does not stop the run; what failed lands in the record's `failures`
and in the manifest.

The crime window is fixed once for the whole sweep: stage 3 reads the latest
published month with one `crime.latest` call and passes it to every `crime.box` as
`end`, so the buildings cannot end up on different six-month windows if the police
publish mid-run. The method's rule is one geometry and one window for every
candidate, or the table compares methods rather than flats.

`roads.py` says in its own docstring: *do not loop this query over a list of
addresses.* So the sweep does not. It sends **one** Overpass query for the whole
circle — `roads.build_query` with every `around:` radius widened by the sweep
radius, taken from roads.py by regex so the tag list cannot drift — and then hands
those elements to `roads.near(..., elements=, meta=)` per building, which
re-filters at each category's proper distance from that building's coordinates.
Above `SHARED_OVERPASS_MAX_M` (1200 m) the widened query would pull megabytes, so
the sweep falls back to one query per building and says so on stderr. This matters:
in testing, four back-to-back per-building Overpass calls tripped the public
instance's rate limit, and each refusal costs up to 90 s x 8 attempts before
roads.py gives up.

**The 4 KB rule.** Every `candidates/<key>.json` is at most 4096 bytes
pretty-printed. Provenance sits at the block level: each of `epc`, `crime`,
`commute`, `planning`, `roads`, `land_registry` and `companies` carries its own
`source_url`, `retrieved_at` (minute precision) and `evidence_class`, and those
three are never trimmed — a number with no provenance is worse than no number.
A block that failed keeps `ok: false`, its status and its note; a block that
succeeded drops those three, because a plain 200, an empty note and `ok: true` cost
bytes and say nothing. When the record is still too big, `fit_to_budget()` walks a
documented list of trim steps:
metadata that summary.json repeats goes first, then detail the summary table does
not use, and the three lists the method actually asks for — the top crime anchors,
the nearest planning cases and the nearest of each road category — are cut down
last. `trimmed` says how many fields went and names the first few; the full list
is in `summary.json` under each candidate.

**`metrics`** uses the exact `report-schema.json` keys and holds only what a sweep
can measure: `crime_6mo_count`, `commute_min`, `commute_redundancy_grade` and
`nearest_works_m`. `compared_to` is filled mechanically with the sweep median (it
is only knowable after every candidate is in, so stage 5 rewrites the files);
`meaning` is left as the literal string `TO BE WRITTEN BY THE MODEL`. The four
metrics a sweep cannot reach — `price_per_sqft_epc`, `management_organic_score`,
`management_incentivised_share`, `landlord_type` — are named in
`metrics_not_measured` with the reason, rather than emitted as empty measures that
would cost 700 bytes and teach nothing.

**Stage 4** writes `ask-the-user.md`, which follows `references/inputs.md`: one
message, one numbered list, the review sites and listing portals **by name only**
with no URLs at all, and per building the specific thing to ask about (the heat
tariff when the block is on a network, the stage of the nearest tall scheme, who
appoints the managing agent). The repo never fetches a review site or a portal.

**Stage 5** writes `summary.json`, `summary.md` and `report-skeleton.json`. The
table is one row per building — distance, certificates, median square feet,
earliest year, heating, ground-floor share, crimes and predatory share, commute
all/rail, redundancy grade, nearest tall scheme, nearest trunk road, RMC/RTM count
and earliest new-build sale — with a MEDIAN row under it. `coverage` counts
streets found, searched and refused as "too many results", postcode-fallback
searches, certificates seen, buildings, streets merged, excluded, assessed, passed,
failed, **not assessed** (past `--max-filter-buildings`, which is neither a pass nor
a fail), fetched, failures and wall seconds; `not_found` carries the exact query for
every empty search, and a fetch that a retry or the mirror later fixed is not listed
as a gap. `report-skeleton.json` is a partly-filled report — identity,
metrics, hard filters, sources, not_found, blocked_sources — that the model
completes; it is deliberately **not** yet schema-valid, because every candidate
still needs its verdict, twelve axes, costs and landmines, and its
`_skeleton_notes` say so.

**`manifest.json`** records every fetch the run made — stage, url, method, status,
ok, note, retrieved_at, from_cache — by wrapping `_fetch.fetch` and rebinding it
inside each imported module. Failures are recorded, never hidden, and the wrapper
is removed in a `finally`, so the manifest is written even when the run dies.

**Cost.** Stage 3 costs about `crime_months x 5 + 7` fetches per building (the
police box re-fetches the same window at four shifted centres for its sensitivity
check, which is 5x on its own), so 37 at the defaults, plus one shared
OpenStreetMap query for the whole run. Enumeration is 1 Overpass call + 1
energy-register search per street + up to `--max-postcode-lookups` geocodes, and
stage 2 is `certs_per_building x` the buildings assessed. `--dry-run` prints all of
that before you spend it. Past police months and certificate pages are cached, so a
re-run inside the cache window is nearly free. On a cold cache the energy register
is the slow part — the pages take about 3.5 s each, well over the 1.2 s spacing — so
stage 2 dominates the clock; `--certs-per-building 4 --max-filter-buildings 12` cuts
it about fourfold when you only want a shortlist.

```console
$ sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
           --max-buildings 4 --out sweep/ --dry-run
{ "dry_run": true, "streets_found": 64, "streets_that_would_be_searched": 64,
  "estimated_fetches": { "street_query": 1, "shared_openstreetmap_query": 1,
                         "epc_street_searches": 64, "epc_certificates": 200,
                         "per_building_facts": 37, "facts_total": 148,
                         "grand_total_excluding_postcodes": 414 } }

$ sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
           --max-buildings 4 --out sweep/
stage 1: 64 streets searched, 1202 certificates, 207 buildings (1 excluded)
stage 2: 25 assessed, 25 passed, 0 failed, 181 not assessed (over the cap)
stage 3 plan: 4 building(s) x about 37 fetches = about 148 fetches
{ "ok": true, "out": "/…/sweep", "candidates": 4,
  "coverage": {...}, "sweep_medians": {...},
  "files": ["anchor.json", "buildings.json", "filtered.json", "candidates/*.json",
            "ask-the-user.md", "summary.json", "summary.md",
            "report-skeleton.json", "manifest.json"] }
```

Measured on a cold cache, that run took **6 min 15 s** for **373 fetches** (296 over
the network, 77 served from the cache inside the same run because three of the four
buildings share one postcode centroid and therefore one crime box). The same run
against a warm cache takes about 54 s. Each of the four candidate files came out at
4011-4079 bytes.

Volume note: the energy register's robots.txt disallows crawling. This tool keeps
the built-in spacing, caps the census, and is meant for an area someone is
actually house-hunting in — not for harvesting a borough.

## calc.py — deterministic arithmetic (no model maths)
Every computed number in a report comes from here or shows its formula. Subcommands: `deposit`, `affordability`, `all-in`, `price-per-sqft`, `bridge`, `break-even`, `guarantor-product`, `pro-rata`, `pct-diff`. Each prints `inputs`, `formula`, `steps`, `result`.
```
python3 skills/vet-flat/scripts/calc.py deposit --rent-pcm 2400
python3 skills/vet-flat/scripts/calc.py affordability --rent-pcm 2400 --multiple 2.5 --income 65000 --guarantor-multiple 4
python3 skills/vet-flat/scripts/calc.py guarantor-product --rent-pcm 2400 --model annual --weeks 3 --setup 59.99
```

### Arithmetic check (render.py recomputes what calc.py computes)
`scripts/render.py` carries a `recompute(report)` that redoes, from the raw inputs in the JSON, every number that follows from a formula above: weekly rent, the deposit and holding-deposit caps, the three all-in totals, rent per square foot from the energy-certificate area, break-even rent against the profile ceiling, and the twelve-month bridging total when bridging inputs are present. Each one is compared with the figure the model wrote — `costs`, `metrics`, `axes[].numbers[]` and the `observed` text of a hard filter are searched by key and by label keywords — inside a tolerance of 1 per cent or £1, whichever is larger (a penny rather than £1 on a £/sqft figure). Deposits are checked as caps: less is fine, more is unlawful. `verdict.break_even_rent_pcm` is not compared; that field is a judgement about what the flat is worth, not this formula.

The result is written to each candidate as `arithmetic_check` (`arithmetic_ok` plus one row per figure), printed as one `WARNING  arithmetic:` line per mismatch on stderr, turned into an error by `--strict`, and shown in section 6 of the HTML and Markdown as an **Arithmetic check** table that states each formula in words, with a *check the maths* chip on every number that does not follow from it. `viewer/viewer.html` does the same in the browser with the same formulas and the same tolerance. Put `computed_by: "scripts/calc.py deposit"` (or `"shown formula"`) on any derived number so a reader can see where it came from; the check runs either way.

```
python3 skills/vet-flat/scripts/render.py report.json --validate-only   # WARNING per mismatch
python3 skills/vet-flat/scripts/render.py report.json --strict          # mismatches are errors
```

### No source, no number (render.py enforces what the schema states)
Every number a report states — each `axes[].numbers[]` entry and each `metrics` measure — has to carry at least one id in `sources` (resolving to the top-level `sources` list) or a `computed_by` note saying how it was worked out. The rule is written into `references/report-schema.json` as an `anyOf` on the `labelled_number` and `measure` definitions, so the `required` list is unchanged and a report written against schema 1.0 still validates. `render.py` reads those keys back out of the schema rather than hard-coding them, and prints one `WARNING  no source:` line per offending number; `--strict` turns each into an error and exits 1. Both renderers put a *no source* chip on the number itself (`**[no source]**` in Markdown), and `viewer/viewer.html` runs the same check in the browser. A `null` value is never flagged: there is no number in it to source.

```
python3 skills/vet-flat/scripts/render.py report.json                   # WARNING per unsourced number, page still written
python3 skills/vet-flat/scripts/render.py report.json --strict --validate-only   # each one is an error, exit 1
python3 bench/release_gate.py bench/results/<date>                      # the pre-release gate: 0 fabrications, schema ok
```

### Your questions, and what only you can tell (two report sections)
`candidates[].question_answers` holds the user's own `my_questions` from `profile.yaml`, answered. Each entry carries the question, the stage it belongs to (`when`: filter, vet, compare, viewing, sign), the answer, an evidence grade and whether the trigger fired, and both renderers put it where the user reads it: filter answers as extra rows of the hard-filter table, vet answers under the verdict card, compare answers as one row per question with a cell per candidate, viewing answers with the viewing-day checks and sign answers under *Before you sign*. An answer that states a number obeys the same no-source-no-number rule as every other number. Section 8, *What only you can tell*, then asks for what the tool cannot sense: every axis graded unknown, followed by `candidates[].only_you_can_tell` or, when that is empty, the four standard requests in `glossary.yaml` (`only_you.smell`, `only_you.noise_night`, `only_you.light_today`, `only_you.street_feel`).

### The configuration line (which rung of the escalation ladder ran)
`generated_by.tier` (`lite` | `standard` | `breadth` | `manual`) and `generated_by.escalation_reason` are optional fields that say how much machine was behind the report. Both renderers print `Configuration: <tier> — <reason or "default">; workers: <cheap|strong>; judge: <model_name>` as the first line under the title and again in *About this report*; a report with no tier prints `not stated`. The workers half follows from the tier — `standard`, `breadth` and `lite` run cheap workers with a strong judge, `manual` runs none — and the ladder itself, including the triggers and the fan-out rule, is in `references/budget-modes.md`.

## `streetview.py` — street-level imagery (your own key; free routes too)

```
streetview.py check     --lat 51.5045 --lng -0.0865 [--radius 50] [--outdoor]
streetview.py fetch     --lat <road lat> --lng <road lng> --out sv/ \
                        [--toward-lat <building lat> --toward-lng <building lng>] \
                        [--headings 0,90,180,270] [--fov 90] [--pitch 0] \
                        [--size 640x640] [--used-this-month 0]
streetview.py mapillary --lat 51.5045 --lng -0.0865 [--radius 60] [--limit 10]
streetview.py brief
```

The closest thing to a viewing before the viewing: which elevation the flat is
on, what trades at ground level under the windows, how exposed a ground-floor
window is, whether the street is mid-build, and how many storeys the building
opposite has. Method and the full read-the-picture checklist:
`references/axes/18-street-view.md`. Everything this script returns is
**evidence class C** and carries a **capture date that is usually years old** —
quote the date in every finding.

**Three routes, in order.** (1) Google Street View Static API with the *user's
own* `GOOGLE_MAPS_KEY`; (2) Mapillary with the user's own free
`MAPILLARY_TOKEN`; (3) no key at all — `brief` prints the checklist and the four
screenshots to ask the user for. Keys are read from a plain `KEY=VALUE` `.env`
next to the script or from the environment, same as `commute.py` and
`company.py`. Nothing here ever uses a shared key.

**`check` is free and always runs first.** It calls the metadata endpoint, which
Google prices at nothing: *"Street View Static API metadata requests are
available at no charge. No quota is consumed when you request metadata."* It
returns `status`, `pano_id`, `date` (the capture date) and `location` (where the
camera actually stands), plus the distance and bearing from your point to the
camera and the heading that would point the camera back at your building. With
no key it exits **0** with `access: manual` and prints how to make a key and how
to take the screenshots by hand — a missing key is not an error.

**`fetch` needs a key and refuses without one (exit 2, and it does not even
create the output directory).** It calls `check` first, pins every image to the
returned `pano_id` so all four views come from one standing position, downloads
up to four JPEGs into `--out`, and writes `manifest.json` beside them. Give it
the **road** point in `--lat/--lng` and the **building** in `--toward-lat/-lng`:
the heading is computed from the first toward the second and the other three
views sit 90° apart, so one run gives you the building, the street both ways,
and whatever faces the flat across the road. `--headings` overrides that.
`size` is capped at the documented 640×640, `fov` at 120, `pitch` at ±90.
A `ZERO_RESULTS` panorama downloads nothing and bills nothing.

**Every URL in the manifest is key-redacted** (`key=REDACTED`, likewise
`access_token` and `signature`) because a manifest is exactly the kind of file
that gets pasted into a chat. Images are downloaded through the new
`_fetch.fetch_binary()`, which streams to disk without UTF-8 decoding and
**never caches** — Google's terms forbid caching Google Maps Content, with one
exception: the panorama ID, which may be stored indefinitely. Keep `pano_id`,
the capture date and your written finding; delete the JPEGs when the run ends
unless the user chose to keep them.

**Cost, verified 2026-09-05** on
<https://developers.google.com/maps/billing-and-pricing/pricing>. Since
2025-03-01 the old $200 credit is gone and each SKU carries its own free monthly
allowance. `Static Street View` (SKU 9BD0-A2EE-44C3): **10,000 free calls a
month**, then **$7.00 / 1,000** (0–100k), $5.60 / 1,000 (100k–500k), $4.20 /
1,000 (500k+). `Street View Metadata` (SKU 3168-48A9-5C8C): free, unlimited.
Four views per flat is four calls — free until the 2,500th flat of the month,
about **$0.028** after that. `cost_estimate` in the manifest shows the split;
pass `--used-this-month` with your real month-to-date count to make it truthful.
The key still needs a Google Cloud project with a billing account attached, even
inside the free allowance, so `sources.yaml` marks the image SKU `paid`.

**`mapillary` is the free fallback** (CC BY-SA 4.0, token from
mapillary.com/dashboard/developers). The token rides in an
`Authorization: OAuth` header so it never enters a URL. Mapillary's `/images`
endpoint wants a bbox smaller than 0.01 degrees square and its radius search
caps at 50 m, so the script builds a bbox and caps `--radius` at 300 m. Results
come back nearest-first with `captured_at`, `compass_angle_deg`, the contributor
and a thumbnail URL (signed, and it expires — open it now). No token exits 0
with `access: manual`.

**Never scrape.** Do not lift Street View images off maps.google.com with a
fetch tool: Maps Platform ToS 3.2.3(a) *No Scraping* names bulk-downloading
Street View images, and the API exists so you do not have to. Attribution when
an image appears in a report: Google's wordmark stays on the image and the
[Street View policies](https://developers.google.com/maps/documentation/streetview/policies)
apply; a Mapillary image needs the contributor credit, the Mapillary logo and a
link back.

```console
$ streetview.py check --lat 51.5045 --lng -0.0865
{ "ok": true, "evidence_class": "C", "status": "OK", "pano_id": "…",
  "date": "2023-07", "location": {"lat": 51.50448, "lng": -0.08661},
  "camera_distance_m": 8, "camera_direction": "WSW",
  "heading_from_camera_to_point_deg": 73.7,
  "billing": {"free": true, "sku": "Street View Metadata (SKU 3168-48A9-5C8C)"} }

$ streetview.py fetch --lat 51.5045 --lng -0.0865 --toward-lat 51.5047 \
                      --toward-lng -0.0862 --out sv/
{ "ok": true, "evidence_class": "C", "pano_id": "…", "capture_date": "2023-07",
  "toward_heading_deg": 43.0, "toward_direction": "NE",
  "headings_deg": [43.0, 133.0, 223.0, 313.0],
  "images": [{"file": "streetview-h043.jpg", "heading_deg": 43.0, "direction": "NE",
              "url": "https://maps.googleapis.com/maps/api/streetview?size=640x640&pano=…&key=REDACTED",
              "shows": "the target (the building), from the camera point"}, …],
  "cost_estimate": {"image_calls": 4, "billable_image_calls": 0, "estimated_usd": 0.0} }
```

Tests: `tests/test_streetview.py` (no network — headings, URL building, key
redaction in the manifest, no-key behaviour, the cost arithmetic against the
verified constants, and the brief).

## `seed.py` — the shareable seed (no network, no key)

```
seed.py export --profile profile.yaml [--name "quiet, high, morning sun"]
               [--journey journey.json] [--exact] [--commute-area "Zone 1"]
               [--hide-commute] [--reveal-address] [--max-code 400] [--json]
seed.py import "PP1.eyJ2Ijox…" [--out profile.yaml] [--force] [--json]
seed.py import seed-card.txt --out profile.yaml
```

Turns the user's own `profile.yaml` into something postable: a **card** (three
sentences drafted from the profile, then a compact YAML block) and a **code**
(`PP1.` plus base64url of a minimal JSON), and reads a code back into a fresh
profile. Not a data source; it fetches nothing.

The scrub is an **allow-list**, so a field the profile grows later cannot leak:
seed name, `flat_type`, budget as a **band**, `budget_mode`, the commute
destination reduced to a **postcode district**, the move-in window as a
**month**, `must_haves`, `avoid`, `priorities`, `my_questions` (text, stage and
kind — never the `trigger`), floor rules, light rules, `quiet_over_light`,
`bridging.first_weeks`, `story_summary`. Never: an address, a name, income,
savings, `guarantor_route`, `self_intro_template`, exact dates, exact money
(unless `--exact`), `tenancy`, `occupants`, or anything under `bridging` beyond
`first_weeks`. Free text is swept for UK postcodes on the way out.

The band rule: round the all-in ceiling up to the nearest 100 for the top, take
200 off below £1,500 and 400 otherwise for the bottom. A bare profile makes a
code of about 250 characters; a full one with a summary and questions runs 600
to 1,000, and `--max-code` (default 400, `0` = no limit) drops exactly one key
to get closer — `s`, the summary, which stays on the card.

`--journey journey.json` adds the "what I found" lines: how many flats were
vetted, how the verdicts fell, and what was chosen — never the address, unless
`--reveal-address`. The format is in `references/seed-schema.json`
(`definitions.journey`) and `references/sharing.md`.

`import` writes a profile with the seed's preferences and `# FILL IN` on
everything that is not inheritable: floor area, budget numbers, dates, the
destination, the income-check route, the self-introduction. Somebody else's
ceiling is a comment, never a value. It refuses to overwrite an existing file
without `--force`, and it reads a code out of a saved card as happily as off the
command line.

```console
$ seed.py export --profile profile.yaml --name "quiet, high, morning sun"
Pea Princess seed — quiet, high, morning sun
what I am looking for, and nothing about where I live, what I earn or who I am.

I want a one-bedroom flat, on floors 2-8, with windows facing E or SE, within reach of
WC2R, from October 2026, at £2,000–2,400 all-in; it must have washing machine in the
flat; and I rank quiet, light and price in that order.
I will not take: ground floor; heating with no written tariff; windows that cannot see sky.
Price sits last of my three priorities: I will pay towards the top of the band for a
benefit I can name, and quiet wins when quiet and light conflict.

seed:
  name: quiet, high, morning sun
  flat_type: one_bed
  budget_band: "£2,000–2,400 all-in"
  # My questions — every report has to answer each of these by name, at the stage in brackets
  my_questions:
    - "[compare] If this is unusually cheap next to its neighbours, what is the hidden problem?"
  …
seed code (paste it into any AI agent that has the Pea Princess skill, …):
PP1.eyJhdiI6WyJncm91bmQgZmxvb3IiXSwicHIiOlsicXVpZXQiLCJsaWdodCIsInByaWNlIl0sInEiOnRydWUs…
```

The agent-facing rules are `references/sharing.md`; the exact code format, for a
runtime with no shell, is `references/seed-format.md`. `viewer/viewer.html`
draws the same three sentences from a report's `profile_snapshot` under **Share
card**, with a copy button (no code: the snapshot holds less than a profile).

Tests: `tests/test_seed.py` (no network — the allow-list, the scrub against a
profile stuffed with secrets, the code's prefix, alphabet and length formula, the
worked example in `seed-format.md`, the export/import round trip, the questions'
stages, the journey lines, and the blanks an imported profile leaves).

## `scan.py` — the fixed-form pre-scanner (no network, no key)

```
scan.py listing.txt
cat listing.txt | scan.py -
scan.py listing.txt --table
scan.py listing.txt --tier gate
scan.py listing.txt --questions path/to/fixed-questions.yaml
```

Reads pasted text — a listing, an agent's email, a draft contract — and hands back
the **candidate sentences** for each of the eighteen fixed questions in
`references/fixed-questions.yaml`, with line numbers. It is the answer to models
skipping things in 40 KB of paste: the script does the reading, the model fills the
form from quotes it can point at.

A candidate is a sentence worth reading, never an answer. The patterns are
deliberately loose and bilingual (English and Chinese, case-insensitive, so there is
no `--lang`), and two of them can hit the same sentence. At most five candidates are
kept per question, deduped, each cut to the 300-character quote limit of
`report-schema.json`.

The ids with **no** candidate are the point: they are printed to stderr as one plain
line, because that is the list the model turns into questions for the user — gate
questions F1–F8 always, listing questions F9–F14 and the extended F15–F18 whenever a
page was pasted.

`--tier` narrows both the looking and that list: `gate` the eight, `standard` the
fourteen, `full` all eighteen. It defaults to `full` because reading is cheap; the
tier only decides how many the *report* must answer, and that is `render.py`'s job.
Any name in the file's `tiers` block works, and an unknown one exits 2 rather than
quietly scanning for nothing.

```console
$ scan.py listing.txt --table
no sentence found for F3, F6, F8 — ask the user these, once, in one message
id   group    line  candidate sentence
---  -------  ----  --------------------
F1   gate     16    - Deposit: five weeks' rent (£2,711).
                16    Holding deposit of one week's rent (£542)
F2   gate     16    Holding deposit of one week's rent (£542)
F3   gate     -     (nothing found - ask the user)
...

$ scan.py listing.txt
{ "ok": true, "source": "listing.txt", "lines": 38, "tier": "full",
  "items": [{"id": "F1", "group": "gate", "ask_if_missing": "always",
             "candidates": [{"line_no": 16, "text": "Deposit: five weeks' rent (£2,711)."}]}, ...],
  "summary": {"found_candidates": 30, "silent": ["F3", "F6", "F8"]} }
```

The question file is also the machine side of the report's fixed form: `group`
(`gate`, `listing` or `extended`), `axis`, `answer_type`, `ask_if_missing`, a `cap`
pointing into `thresholds.yaml` where the law caps the answer, an optional
`source_hint` naming where a human would go and look, and the `why` line both
renderers print when an answer is unknown. Its `tiers` block is the one place the
mapping from depth to how many questions lives — lite eight, standard fourteen, deep
eighteen — and `scan.py`, `render.py` and the viewer all read it from there. The
reader-facing wording lives in `glossary.yaml` as `fixed.F1` … `fixed.F18`, in three
languages.

Tests: `tests/test_scan.py` (no network — the parser, the bilingual patterns against
`tests/fixtures/pasted-listing.txt`, the five-candidate cap, the silent-id line on
stderr, and the JSON shape).
