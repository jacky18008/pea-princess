# Conventions (read before adding a script or reference)

## Scripts (`skills/vet-flat/scripts/`)
- Python 3.9 compatible, **standard library only**. No pip packages. Network I/O only through `_fetch.fetch()` (curl under the hood; per-host throttle ≥1.2 s; on-disk cache; `expect=` content assertion). Never call urllib for network.
- Every script: `argparse` CLI, subcommands where natural, prints **one JSON object** to stdout, human-readable errors to stderr, exit code 0 on success, 2 on usage error, 1 on fetch failure. `--verbose` prints the curl commands to stderr.
- Output envelope for every fetched record: `source_url`, `http_status`, `ok`, `note`, `retrieved_at` (UTC ISO), `evidence_class` (`G` official register / `S` self-reported / `C` third-party / `I` inference / `U` unknown), plus the parsed fields. Missing = `null`, never a guess. Counts of things you looked for but did not find go in `not_found` with the exact query used.
- A 200 with the wrong page is a failure: always pass an `expect` lambda. Record the assertion that failed in `note`.
- Use the browser UA (`_fetch.BROWSER_UA`) except where a host wants a tool UA (Overpass: `_fetch.TOOL_UA`).
- **No personal parameters.** Destinations, budgets, thresholds come from arguments or `profile.yaml`. Defaults must be generic (e.g. destination is a required argument, not a hard-coded campus).
- **Commercial portals and review sites** (Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com): no fetch code, no selectors, no endpoints, anywhere in this repo. Scripts may *parse a local file the user saved* only if the file format is documented publicly; if in doubt, leave it out.
- Docstring at the top: what the source is, whether it is official, whether a key/login/fee is needed, robots/ToS note, usage examples.

## Tests (`tests/`)
- `unittest` only (pytest is not assumed). Offline parser tests read `tests/fixtures/<script>-<case>.{html,json}` captured from the live site (keep each fixture ≤ 400 KB; strip nothing that the parser needs). One live smoke test per script under `tests/live_smoke.py`, skipped unless `VETFLAT_LIVE=1`.
- Run: `python3 -m unittest discover -s tests -p 'test_*.py'`.

## References (`skills/vet-flat/references/`)
- English, model-facing, plain sentences, checklists over prose. Numbers live in `thresholds.yaml` and are referenced by id; endpoints live in `sources.yaml`.
- First line of every reference file: `Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0`.
- No codenames, no personal circumstances, no named real buildings, no ethnicity/nationality rules.

## Report contract
- `references/report-schema.json` is the single source of truth for the report. Text fields follow the plain-language rules in SKILL.md §7. `render.py` (shell) and `viewer/viewer.html` (browser) must produce the same layout from the same JSON, and both print the footer `Generated with vet-flat <version> — https://github.com/jacky18008/pea-princess`.
- Twelve sections in this order: verdict, hard filters, the questions we always answer, side by side, worst reviews, landmines, the 12 checks, questions and the viewing day, what only you can tell, what we could not find, sources, about. Adding one means `SECTIONS` in `render.py`, `SECTIONS` in `viewer/viewer.html`, a `section.*` entry in `glossary.yaml` in three languages, and a line in `report-contract.md`.
- The fixed form has three states and no fourth: `found` (the sentence quoted, a source id that is not `user`), `asked` (the user answered it, source `user`), `unknown` (no quote, no number, and the reader is shown the `why` line from `references/fixed-questions.yaml`). A missing id warns and fails `--strict`; a repeated id is an error.

## Git
- Small commits per script or reference, with tests. Commit messages end with the Co-Authored-By trailer used in this repo.
