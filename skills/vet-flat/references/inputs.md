# When the agent cannot get something: ask the user (the "you fetch, I read" protocol)

Part of Pea Princess (vet-flat). CC BY 4.0.

Many sources are open but not reachable from every runtime: some sandboxes have no
network, some fetchers honour robots.txt (the EPC register and council planning
portals disallow everything), some sites block bots, some need a login or a fee,
and some things (floor plans, the flat itself) are not on any API. **This is
normal. Do not guess, do not fabricate, do not silently skip the axis.** Ask.

## Rules for asking
1. First try what you can: run the scripts in `scripts/` if you have a shell and
   network; fetch open URLs if you only have a fetch tool.
2. Collect every missing item, then **ask once**, in one message, as a numbered
   list. For each item give: what you need, the exact URL or place to get it, the
   format you want back (paste text / upload file / a number), and why it matters
   (one short sentence). Never send one question per axis.
3. While waiting, continue with everything that does not depend on the answer.
4. Record what the user supplied with `provenance: user_supplied` and the date.
   Official documents supplied by the user (an EPC page, a Land Registry title,
   a planning decision) keep evidence class **G (official)**; what the user
   *tells* you (the agent said, the landlord said) is class **S (self-reported)**.
5. If the user cannot supply an item, mark the axis **U (unknown)** in the report
   with the reason. An unknown is never a pass.

## What to ask for, per axis

| Axis | Try first | If blocked, ask the user for | Where they get it | Format |
|---|---|---|---|---|
| Identity, floor area, age, heating | `scripts/epc.py search --postcode` then `cert` | The certificate page for the exact flat (or the search page listing all flats) | find-energy-certificate.service.gov.uk → "Find an energy certificate" → postcode | Paste the whole page text, or the certificate number |
| Whole-building EPC profile | `scripts/epc.py building --postcode` | Nothing; skip or ask for the search-page text | same | Paste |
| Floor plan and orientation | (no API) | The floor plan image and any developer plan with a compass | Listing page, developer brochure | Image upload (jpg/png/pdf) |
| Listing text, price history | (portal terms forbid automated access) | The listing page saved as HTML or its full text, plus the URL | Rightmove / Zoopla / OnTheMarket / OpenRent | "Save page as… (complete)" or select-all-copy |
| Owner / landlord entity | `scripts/company.py` (Companies House, open) | The Land Registry title register PDF | search-property-information.service.gov.uk (£7, needs GOV.UK sign-in) | PDF upload |
| Resident reviews | (site terms forbid automated access) | The full reviews page text for the named development | HomeViews, Google Maps, Trustpilot | Paste text (all pages, oldest first) |
| Planning near the site | GLA Planning Datahub (open) | Application numbers and the officer report PDF | The borough planning portal (see `boroughs.yaml`) | Paste numbers / upload PDF |
| Crime | `scripts/crime.py` (data.police.uk, open) | Nothing; open data | — | — |
| Commute | `scripts/commute.py` (TfL, open) | Confirm the exact destination address and arrival time | — | Text |
| Heat network supplier & tariff | Heat Trust members page (open) | The Welcome Pack tariff page | Landlord / agent | PDF or photo |
| Redress and client-money protection | Client Money Protect search (open) | Agent's CMP certificate and redress-scheme membership number | Ask the agent in writing | Photo / PDF |
| Anything on site (smell, noise, light, lift log, phone signal) | (never available remotely) | The viewing-day checklist answers | The viewing | Text / photos |

## Optional keys and logins (never required)
If the user has them, they go in `.env` next to the scripts and the scripts use
them automatically; otherwise the free HTML routes are used.

| Variable | Service | How to get | Benefit |
|---|---|---|---|
| `COMPANIES_HOUSE_KEY` | Companies House REST API | developer.company-information.service.gov.uk (free) | JSON instead of HTML, higher rate limit |
| `TFL_APP_KEY` | TfL Unified API | api-portal.tfl.gov.uk (free) | Higher quota |
| (download) | EPC open data CSV | get-energy-performance-data.communities.gov.uk (free GOV.UK One Login) | Bulk building data without page fetches |

## Template for the ask (copy, fill, send once)
```
I can finish X of 12 axes myself. To complete the rest I need 3 things:
1. EPC page for Flat 12, 4 London Bridge Street — go to
   https://find-energy-certificate.service.gov.uk, search postcode SE1 9SG, open
   the row for Flat 12, and paste the whole page here. (Sets the floor area, age
   and heating type; everything else keys off it.)
2. The floor plan image from the listing. (Orientation and windowless rooms.)
3. The HomeViews page text for "<development>", all review pages, oldest first.
   (Management score after removing incentivised reviews.)
Meanwhile I am running crime, commute, planning and company checks.
```
