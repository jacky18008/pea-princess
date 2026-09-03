Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Budget modes: the same checks at three depths

People on a £20-a-month plan share usage caps and smaller sandboxes; people with no tools at all paste pages by hand. The skill must still give them the basic functions: hard filters, a verdict, and the two killer questions. `profile.yaml: budget_mode` selects the depth. Default `standard`. The agent states the mode on the first line of the report and lists what was skipped.

| | `lite` | `standard` | `deep` |
|---|---|---|---|
| Who | £20 plans, chat-only users, a first quick screen | most users | £100+ plans, final shortlists, area sweeps |
| Fetches per flat (shell mode, approx.) | ≤ 8 | ≈ 15–25 | 40+ |
| Identity and area | one certificate (`epc.py cert`) | + `epc.py search` for the building's flats | + whole-building profile (`epc.py building`) and certificate history |
| Crime | `crime.py box --months 3 --no-sensitivity` (3 calls) | 6 months, no sensitivity (6 calls) | 6 months + ±20 m sensitivity (30 calls) + route corridor |
| Commute | `commute.py journey` all-modes only | + rail and bus plans, `redundancy` | + `stations` detail and alternative arrival times |
| Company and compliance | `company.py profile` of the named entity | + `search` for same-name shells, `redress.py cmp`, `heat-trust` | + `filings`, `address-search` (RMC/RTM), `rogue`, `landregistry.py price-paid` |
| Planning | skip (state it) | `planning.py near --radius 250 --limit 20` | + `stages` on tall schemes, `roads.py near` |
| Reviews | ask the user for the lowest reviews only | full paste, incentivised and burst filters | + Trustpilot/press, cross-building matrix |
| Report | verdict card, hard filters, 2 questions, 12 axes with U where skipped | full | full + comparison |
| Area sweep | not offered; suggest `standard` | `sweep.py --radius 600 --max-buildings 6` | run several `--radius 1000` sweeps on different anchors (one per neighbourhood) with `--max-buildings 8` each; a single 3,200 m sweep trips the map service's rate limit and needs the filter caps raised |

## What never gets cut
Hard filters from the profile · evidence grades · the "not found" table · the attribution footer · "never sign on the viewing day" · asking the user once, in one list, for what cannot be fetched.

## Chat-only users on any plan
The prompt pack (`INSTRUCTIONS.md` + references) plus `viewer.html` is the lite path: the user pastes the certificate page and the listing, the agent applies the filters and writes the report JSON, the viewer renders it. No fetch budget is consumed.

## Measuring it
`bench/run.py` records wall time and tokens when the CLI reports them; run the same case in `lite` and `standard` and keep the numbers in `bench/results/`. Target for `lite` on a single flat: under ten tool calls and one report.
