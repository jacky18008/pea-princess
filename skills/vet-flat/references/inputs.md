Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# When the agent cannot get something: ask the user

Many sources are open but not reachable from every runtime: some sandboxes have no
network, some fetchers honour robots.txt (the EPC register and council planning
portals disallow everything), some sites block bots, some need a login or a fee,
and some things (floor plans, the flat itself) are not on any API. **This is
normal. Do not guess, do not fabricate, do not silently skip the axis.** Ask.

## If listing research is blocked

The rule on listing links lives in `references/listing-fields.md`: paste or save, never fetch.

## Rules for asking
1. Try available scripts or open sources first; use only tools actually available.
2. Collect gaps; ask at most **three essential clarifications** once, with where to
   get each item, its format and why it matters. Never hide more questions in subparts.
   Use a native question/choice tool when available; otherwise plain text, no fake buttons.
3. Continue independent work now. Defer other gaps to the report; a checklist is not
   an intake form the user must complete. Respect requests for no follow-up questions.
4. Record `provenance: user_supplied` and date. Supplied official records keep **G**;
   relayed agent claims stay **S**. Keep estimate qualifiers; quoting a claim does not prove it.
5. Unresolved checks remain **U**, with a reason; unknown never means pass.
6. Do not offer to read unrelated mailboxes, files, calendars or accounts; ask for the relevant extract.

## What to ask for, per axis

| Axis | Try first | If blocked, ask the user for | Where they get it | Format |
|---|---|---|---|---|
| Identity, floor area, age, heating | `scripts/epc.py search --postcode` then `cert` | The certificate page for the exact flat (or the search page listing all flats) | find-energy-certificate.service.gov.uk → "Find an energy certificate" → postcode | Paste the whole page text, or the certificate number |
| Whole-building EPC profile | `scripts/epc.py building --postcode` | Nothing; skip or ask for the search-page text | same | Paste |
| Floor plan and orientation | (no API) | The floor plan image and any developer plan with a compass | Listing page, developer brochure | Image upload (jpg/png/pdf) |
| Listing text, price history | (portal terms forbid automated access) | The listing page as a PDF, screenshots, saved HTML or its full text, plus the URL as the citation (the skill does not open it) | Rightmove / Zoopla / OnTheMarket / OpenRent | "Print → Save as PDF", "Save page as… (complete)", screenshots (floor plan too), or select-all-copy |
| Owner / landlord entity | `scripts/company.py` (Companies House, open) | The Land Registry title register PDF | search-property-information.service.gov.uk (£7, needs GOV.UK sign-in) | PDF upload |
| Resident reviews | (site terms forbid automated access) | The full reviews page text for the named development | HomeViews, Google Maps, Trustpilot | Paste text (all pages, oldest first) |
| Planning near the site | GLA Planning Datahub (open) | Application numbers and the officer report PDF | The borough planning portal (see `boroughs.yaml`) | Paste numbers / upload PDF |
| Crime | `scripts/crime.py` (data.police.uk, open) | Nothing; open data | — | — |
| Commute | `scripts/commute.py` (TfL, open) | Confirm the exact destination address and arrival time | — | Text |
| Heat network supplier & tariff | Heat Trust members page (open) | The Welcome Pack tariff page | Landlord / agent | PDF or photo |
| Redress and client-money protection | Client Money Protect search (open) | Agent's CMP certificate and redress-scheme membership number | Ask the agent in writing | Photo / PDF |
| Street-level imagery (before the visit) | `scripts/streetview.py check` (free, needs `GOOGLE_MAPS_KEY`), then `fetch` for up to four views; `scripts/streetview.py mapillary` if there is no Google key | Screenshots of the street outside, and the capture date printed in the corner. Say which headings you want: **at the building**, **along the street each way**, and **across the road from the flat** | google.com/maps → drop the pegman on the street outside; or mapillary.com/app | Image upload (jpg/png) plus the date. Method: `axes/18-street-view.md` |
| Anything on site (smell, noise, light, lift log, phone signal) | (never available remotely) | The viewing-day checklist answers | The viewing | Text / photos |

## Optional keys and logins (never required)
If the user has them, they go in `.env` next to the scripts and the scripts use
them automatically; otherwise the free HTML routes are used.

| Variable | Service | How to get | Benefit |
|---|---|---|---|
| `COMPANIES_HOUSE_KEY` | Companies House REST API | developer.company-information.service.gov.uk (free) | JSON instead of HTML, higher rate limit |
| `TFL_APP_KEY` | TfL Unified API | api-portal.tfl.gov.uk (free) | Higher quota |
| `GOOGLE_MAPS_KEY` | Google Street View Static API | console.cloud.google.com → enable Street View Static API → API key, then restrict it (needs a billing account; 10,000 free image calls a month, the coverage/date check is always free) | Street imagery and its capture date without asking the user to screenshot anything |
| `MAPILLARY_TOKEN` | Mapillary Graph API v4 | mapillary.com/dashboard/developers (free) | Free CC BY-SA street imagery, sometimes newer than Street View, no billing account |
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
