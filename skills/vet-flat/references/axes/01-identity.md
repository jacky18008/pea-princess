Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 1 — Identity

## Purpose
Pin the exact flat: unit number, building, street, postcode, and the certificate that proves it exists.
Every other axis keys off this. If identity is unresolved, no axis above it can be graded better than U.

## What counts as evidence
- **G (official register)** — the EPC register row for the exact flat ("FLAT 16, 4 Example Street"); a Land Registry title register naming the same unit; a planning or licensing register entry for the address.
- **S (self-reported)** — the listing address, the agent's email, the operator's own unit schedule, a brochure unit number.
- **C (third party)** — a resident review or news article that names the building; an aggregator's copy of a listing.
- **I (inference)** — a floor read off a unit number; a stack position read off a four-digit number; "same building, so probably the same address series".
- **U** — no certificate matches and the user cannot supply one.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` — official coordinates, borough, ward. Use these, never a map pin.
2. `python3 scripts/epc.py search --postcode "<postcode>"` — every certificate registered at that postcode, with full flat-level addresses.
3. If the flat is missing: `python3 scripts/epc.py search --street "<street>" --town "<town>"`.
4. `python3 scripts/geo.py cover --lat <lat> --lng <lng> --radius 250` — the other postcodes that cover the same building footprint; repeat step 2 for each.
5. `python3 scripts/epc.py building --postcode "<postcode>" --match "<building name>"` — the whole-building profile (how many flats, which address series, whether ground-floor flats exist).
6. `python3 scripts/epc.py cert <certificate id>` — the certificate for the exact flat.

## Method in fetch mode
Fetch the EPC postcode-search page and then the certificate page (see `sources.yaml`, `epc_find_by_postcode`, `epc_certificate_page`).
The register's robots.txt disallows these paths for crawlers, so a robots-honouring fetcher will not get them. That is expected: fall through to manual mode.

## Method in manual mode
Ask the user for, in one message:
1. The EPC search page for the postcode — "open the Find an energy certificate service, search the postcode, paste the whole results page".
2. The certificate page for the exact flat (or its 20-digit certificate number).
3. The full address exactly as it will appear on the tenancy agreement, including the flat number and any building name.
4. If the flat is not in the results: the street and town, so you can search by street instead.

## How to read the numbers
- `epc_validity_years` — a certificate older than this is expired; the flat may have been re-assessed under another certificate.
- `fetch_host_spacing_seconds` — the minimum gap between requests to one host; do not bulk-harvest a register for an address you are not vetting.
- No pass/fail number lives on this axis. The output is a boolean: `identity.epc_exact_match`.

## Traps and lessons
- **One building, several postcodes.** Large blocks are commonly split across postcodes by floor band, so a high-floor flat is simply absent from the postcode you searched. Search by street, and check every covering postcode before concluding the flat has no certificate.
- **Unit-number decoding is a hypothesis, not evidence.** A four-digit number often encodes floor plus stack (1701 = floor 17, stack 01), and the same stack usually repeats its geometry up the building. Useful for generating questions; never quotable as a fact.
- **"Mid-floor" is not a floor number.** The register records only Ground, Basement, Mid-floor and Top-floor. It cannot yield "first" or "second", and a flat numbered 180 is not evidence of the 18th floor. Conversely, a flat advertised as "Flat 201" has appeared on its certificate as a ground-floor flat.
- **One complex can carry two independent address series** (for example Flats 1–8 on the street number and a separate 61–180 series under an older building name). Matching the wrong series produces the wrong area, age and floor.
- **Same complex is not the same building.** Shared branding does not prove shared floors, corridors, lifts or services; a separate entrance does not prove structural independence either. Say which you verified.
- **Name collision.** Two developments in different postcodes can share a name. Never move reviews, crime counts or planning history between them; check the postcode on every borrowed fact.
- **A search that misses a listing does not prove it was never advertised.** Trace aggregator → source platform → detail id; the same id across several sites is one feed and counts once.
- **HTTP status has meaning.** 410 means archived, not blocked. 403 with a challenge page means you were stopped, not that the listing was withdrawn. "Document unavailable" is not 404. Record what actually happened; never dress a failed fetch as "checked, nothing found".
- **A 200 with the wrong page is the worst failure mode** — some council systems return a plausible page for a stale id. Assert on the expected content, not the status code.
- **Out-of-range pagination can return a repeat of the previous page.** Sanity-check the flat-number range before treating a list as complete.
- **Two flats in the same building are not two independent candidates.** They share the works risk and the same crime box; merge them in any comparison.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 1`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].identity` — `display_name`, `address`, `postcode`, `flat`, `floor`, `building`, `listing_url`.
- `candidates[].provenance_notes` — whether the certificate is this flat's own or a neighbour's, which postcodes were searched, and who supplied the page.
- `candidates[].landmines[]` with code **L10** when the flat number implies a floor the official record does not confirm, or the flat is at street level.
- `not_found[]` — one entry per failed search, with `queries_used` (the exact strings), `where_looked` and `next_step`.
- `blocked_sources[]` — anything that returned a challenge, a redirect or a 200 with the wrong page, with `http_status`, `reason` and `workaround`.
Numbers to record: number of certificates at the postcode, number of covering postcodes, certificate age in years.
