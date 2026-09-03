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
