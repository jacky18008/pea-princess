Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Reading a listing page the person saved or pasted

`scripts/listing_fields.py` turns a listing page **the person already has** — a file saved from their own browser, or the page text copied and pasted — into the facts the page states: rent and its period, bedrooms, bathrooms, floor, floor area, postcode, address, availability, furnishing, deposit, EPC band, council tax band. Every value carries the sentence it was read in, so it can be checked against the page.

```
python3 scripts/listing_fields.py saved-page.html
python3 scripts/listing_fields.py --text pasted.txt
pbpaste | python3 scripts/listing_fields.py -
```

It reads standard markup first (schema.org JSON-LD, microdata, Open Graph, any embedded JSON carrying the same standard keys), then the visible text with plain-language patterns. What the page does not state is listed under `unknown`; nothing is guessed. The values are what the page *states* — the certified floor area, the landlord's identity and the rest are still checked against the registers (axes 1–12).

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

> This skill does not read listing sites itself — their terms allow people to browse, not programs to read for them. Find the homes you like on the sites, then hand me the page: print it to PDF, take screenshots (the floor plan too), or copy the text. I will do the checking.

If they ask where to look, name the places people use — the big portals (Rightmove, Zoopla, OnTheMarket), direct-from-landlord sites (OpenRent), rooms (SpareRoom), build-to-rent operators' own sites, the university accommodation office, agents' sites, resident-review sites for a building — as places to browse under their own terms, without any instruction to automate them, and suggest the sites' own saved-search alerts as the way to keep a watch — the alert email's text is a page they can paste. The skill does not open the links inside it either; the person opens the few homes they like and hands over those pages.
