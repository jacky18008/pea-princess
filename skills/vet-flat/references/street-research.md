Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Street research and the next conversation

Use the exact installed script path. A street comparison does not require the
building-sweep reference or every flat-assessment axis. Identify the street and
its representative postcode first; a brochure's agent-office address is not the flat.

Run `python3 <skill>/scripts/area_scan.py --postcode "<full postcode or outward code>" --street "<street name>"`.
With only an outward code, the script resolves the district through public data and
uses a representative midpoint on the mapped street. For a connected branched street,
it uses the longest joined chain and reports branches excluded from the sample route. Report that location and its limits; distances
are not from the unknown flat and can differ elsewhere on the street. Do not invent
coordinates or copy example coordinates. Supplied coordinates require
`--location-source` identifying the user input or retained geocoder evidence;
that text is not verification by itself. A missing or ambiguous street stops the scan.
The script uses the configured baseline depth, or standard when none is configured.
For an explicitly expanded scope, pass `--depth deep --escalation-reason "<why>"`.
Keep that reason factual; writing it does not grant authority to exceed a user's limit.

Use the host's `VETFLAT_SCAN_RESULT_DIR`, or choose a private project result directory
with `--result-dir`. Identical calls share one saved result. If a run is pending,
wait for that same run or inspect its saved status; do not start parallel copies.
Use returned partial evidence when a register fails. Retained failed/interrupted
results are not permission to retry indefinitely.

Write from the returned result, including its coverage: successful sample points
out of those attempted, missing layers, planning rows read and the area actually
covered. Lden is a day/evening/night weighted measure; Lnight is the night measure.
These are outdoor area estimates, not measurements inside a particular bedroom.
An exact unit address can refine the outdoor sample point, but the map still
cannot measure floor effects, window exposure or bedroom sound.
Window direction affects exposure; facing away does not establish absence of noise.
Planning approval does not establish that work has started. Distances are relative
to the reported scan point until the exact home location is established.
An OSM zero means no matching element was mapped by that successful query and
its actual radius (pubs, bars and clubs: 100 m; roads: usually 300 m), not that
none exists. Police-box totals count records, not personal safety; different
Defra outdoor layers and points cannot prove which bedroom is quieter. Preserve
source failures and missing coverage.

Explain the useful comparison, then ask only about a preference or missing fact
that changes the next decision. A user approving the proposed research means run
it, not ask for approval again. Answer interruptions before returning to unfinished
work. A new preference or rent ceiling changes the recommendation; it usually
does not require fetching the same geographic evidence again. Reuse the saved
result and its original retrieval date, and distinguish changed preferences from
changed source facts. If the person asks to stop research or use existing data,
continue the discussion without another lookup.
