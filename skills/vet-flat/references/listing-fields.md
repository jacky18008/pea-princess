Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Reading a listing page the person saved or pasted

`scripts/listing_fields.py` turns a listing page **the person already has** — a file saved from their own browser, or the page text copied and pasted — into the facts the page states: rent and its period, bedrooms, bathrooms, floor, floor area, postcode and postcode district, address, availability, furnishing, deposit, let type, minimum term, property type, EPC band, council tax band. Every value carries the sentence it was read in, so it can be checked against the page.

```
python3 scripts/listing_fields.py saved-page.html
python3 scripts/listing_fields.py --text pasted.txt
pbpaste | python3 scripts/listing_fields.py -
```

It reads standard markup first (schema.org JSON-LD, microdata, Open Graph, any embedded JSON carrying the same standard keys), then the visible text with plain-language patterns. What the page does not state is listed under `unknown`; nothing is guessed. The values are what the page *states* — the certified floor area, the landlord's identity and the rest are still checked against the registers (axes 1–12).

A page saved from the browser usually carries the page's own data block, with more than the screen shows: the full postcode where the screen shows only the district, the coordinates, the nearest stations with distances, every photo and floor-plan link, the EPC image, the listing date, the agent's company name. The tool opens that block in place (including the index-referenced form some page frameworks write) and lists what it says under `page`. The links under `page` are for the person to open in their own browser: never fetch them, never suggest fetching them. An office or contact postcode is never the property's, and a postcode from another district than the address states is excluded as well; conflicting candidates leave the postcode unknown.

## Why this tool never fetches, and the rules that keep it that way

The listing portals allow people to browse; their terms do not allow programs to read for them. This skill therefore does not read listing sites at all: the person finds the homes they like on the sites themselves, and hands the page to the skill. The skill does the checking. These rules are the design, not a preference:

1. **No network capability in this tool.** No fetch, no browser automation, no shelling out to a downloader. It is a pure function from bytes the person supplies to fields. The tests assert that no network module is imported.
2. **A web address is refused, never resolved.** Given a link, the tool answers: "This tool does not open web pages. Open the listing in your browser, save the page (or copy the text), and pass the file." Refusing is an affirmative step, and it is documented.
3. **Generic extraction, never site-specific.** Standard markup and plain-language patterns only; no selector tables, no site names in the code or in this file's examples. A parser keyed to a named site is the artefact a court would read as "designed for" that site.
4. **No fetch-shaped features, even unused.** No pagination, no rate limiting, no user-agent switching, no proxies, no challenge solving.
5. **The documentation says "paste or save", and names no site as a target.** The registers this skill does read for itself are the open ones listed in `sources.yaml` under their open licences; listing pages are never among them.

The reasoning behind these rules — the cases that draw the line between a tool with lawful uses and one built to induce a breach — is in `docs/research/scraping-blocker-2026-09-11.md` in the repository.

## What to tell the person

One sentence, in their language, when they give a link or ask the skill to look a listing up. The skill does not open the link and does not suggest that anything else should; it says so once, without a lecture, and asks for the page in the form that carries the most. A link carries no photos and no floor plan, and those are what the checks need most:

> This skill does not read listing sites itself — their terms allow people to browse, not programs to read for them. Find the homes you like on the sites, then hand me the page: save it from your browser (File → Save Page As, "Webpage, Complete") and give me the .html — that carries the most; print to PDF or take screenshots for the photos and the floor plan; or copy the text. I will do the checking.

## How the person hands a page over

- **Desktop, most browsers**: on the listing page, File → Save Page As → "Webpage, Complete". The `.html` file alone carries the data block; the folder beside it holds only the photos that were on screen when saving. In a browser whose formats are "Web Archive" and "Page Source", choose "Page Source" (the archive is a container the tool does not read).
- **Photos, floor plan, EPC chart**: these are images, so the data block holds their links, not the pictures. The person opens them in the browser and saves them, or prints the page to PDF. Only hosts that read images can look at them; on the others, ask the person what the floor plan shows.
- **Phone (iPhone, iPad)**: two ways carry the data block. (1) A one-tap Shortcut built from `scripts/capture_page.js` (the build steps are at the top of that file): on the listing page, share → the shortcut → a `.txt` lands in Files or goes straight to the chat app; it runs in the person's own browser on the page in front of them and makes no request. (2) Share → Options → "Web Archive" → Save to Files: the tool reads the main document out of the `.webarchive`; note that chat apps may not accept that file type. The share sheet's "PDF" gives what is on screen (photos included, hidden fields not) and "copy the text" works everywhere; neither carries the data block, so the full postcode and the coordinates then stay unknown unless the page shows them — say so, and ask for the full postcode if a check needs it.
- **Never**: open the link, run a downloader, or suggest either. `capture_page.js` is not a downloader: it serialises the page the person already opened, the way "Save Page As" does.

If they ask where to look, name the places people use — the big portals (Rightmove, Zoopla, OnTheMarket), direct-from-landlord sites (OpenRent), rooms (SpareRoom), build-to-rent operators' own sites, the university accommodation office, agents' sites, resident-review sites for a building — as places to browse under their own terms, without any instruction to automate them, and suggest the sites' own saved-search alerts as the way to keep a watch — the alert email's text is a page they can paste. The skill does not open the links inside it either; the person opens the few homes they like and hands over those pages.

---

# Real examples and listing evidence

Read when finding homes or using examples to explore a renter's preferences.

## Discover, then compare

Listing pages come from the person; the skill never opens them (`references/listing-fields.md` owns the exact rule).

Begin with a small, relevant set. Read an original page before claiming its listing details; a search snippet is a discovery lead. A general development page and its “from” rent describe a building or price band, not an identified available flat. Do not copy the benefits or specifications of a neighbouring unit. Exclude unrelated locations and property types. Once concrete differences are available, compare them and learn priorities from the user's reaction instead of gathering an exhaustive intake first.

## Keep the identity and time attached

For each candidate, retain the source URL, retrieval time in UTC, source type, unit identity (or unknown), relevant source spans and these separate observations:

- What the page advertised: rent and period, bedrooms, size and its measurement source, floor, terms and advertised start date when actually present. Missing values stay unknown; promotional claims remain attributed.
- What was retrieved: original listing, search snippet, building page, user-supplied extract, or dated snapshot. A successful HTTP response, cached search hit or page view is not confirmation from the landlord.
- Availability: advertised, withdrawn, conflicting, or unknown; any direct confirmation needs its own source and date. An advert still online does not establish that the unit can be secured on the user's date.
- Decision limits: rent alone does not establish total monthly cost; station proximity does not establish the user's commute; a listing's area does not become certified EPC area. Carry these limits into the ranking and next checks.

Store compact facts with supporting spans in the host's private source record. Preserve failed reads and conflicting versions. Reopening a saved file does not refresh its date. Refresh time-sensitive claims when the user needs a current recommendation; never silently reuse an old offer as current. Use the eligibility checks for known hard conditions; this source record does not itself prove fit or a PASS.

## When access or evidence is missing

Describe the specific affected claim as unconfirmed, continue independent checks, or request the source extract that would unlock the next decision. Do not fill a missing shortlist with invented addresses, rents, links or availability. Research that finds no suitable units can still explain the trade-off and next search adjustment; report that result accurately.

An explicit request for an invented teaching or arithmetic example permits one, clearly labelled. “Show me some examples” during a real rental search is not that permission. No synthetic candidate belongs in a production shortlist.

## Test data stays distinguishable

Synthetic cases test controlled edge conditions. Frozen real snapshots test claims against reproducible evidence as of the capture date. Live acceptance tests actual permitted retrieval. Report their results separately. A passing synthetic test does not establish live discovery, and one live success does not prove reliability across sources or models.

Keep the data origin in each test record and at the first visible presentation or mode change. Do not repeat a blanket fiction disclaimer in every progress message and answer. Independently opened reports need their own source/date context; material uncertainty belongs beside the affected claim. Never improve tone by disguising a test case as real.
