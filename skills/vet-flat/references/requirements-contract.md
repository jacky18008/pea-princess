Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The requirements contract: the file, and the page that shows it

The person talks to the assistant. The assistant keeps `profile.yaml`. Whenever the person wants to see where things stand, they open a page. Nobody writes HTML: the model writes the file, a script writes the page.

| | The data (what the model writes) | The page (what the person opens) |
|---|---|---|
| Requirements | `profile.yaml` — the keys below | `scripts/panel.py --profile profile.yaml --out requirements.html`: a read-only view; re-run after every change |
| Report | `report.json` — `references/report-schema.json` | `scripts/render.py report.json > report.html`; without a shell, `viewer/viewer.html` takes the pasted JSON |

The requirements page has no form and no script. It works from disk in any browser, loads nothing, stores nothing. Without a shell there is no page: the assistant gives the same summary as text in the chat.

## What the page shows, and where each line lives in `profile.yaml`

| Line | Type of answer | Key |
|---|---|---|
| Where do you go most days? | typed place | `commute.destination` |
| How exact is that place? | unknown · district · station · address | `commute.destination_precision` |
| Arrive by; longest door-to-door | time; minutes | `commute.arrive_by`, `commute.max_door_to_door_min` |
| Monthly ceiling, and whether it includes bills | number | `budget.all_in_pcm_ceiling` (rent + bills) or `budget.rent_pcm_target` (rent only) |
| Home type; people; a real bedroom | room_in_shared_flat · studio · one_bed · two_bed · three_bed_plus · any; number; yes/no | `flat_type`, `occupants`, `separate_bedroom_required` |
| Earliest / latest move-in | dates | `move_in_window.earliest`, `move_in_window.latest` |
| What matters most, in order | quiet, commute, price, light, space | `priorities` |
| Deal-breakers and must-haves | the deal-breaker menu in `onboarding.md`, by its exact strings | `floors.reject_ground_floor`, `light.reject_no_sky`, `quiet_over_light`, `avoid`, `must_haves` |
| How deep; reply language | lite · standard · deep; language code | `budget_mode`, `language` |
| Your own questions for every flat | typed lines | `my_questions[].question` |

Rules:
- **Blank means unknown.** An empty key shows as "not yet known" and is listed under "not yet known"; nobody guesses a destination or a budget.
- **Precision travels with the destination.** A district-level destination gives an estimated commute, never a verified one; the page says so.
- **Every change goes through the assistant.** The person says it in plain words; the assistant edits the file, says in one line what changed, records the revision (`.pea-state` when the session harness is on) and re-runs `panel.py`. The page is the current state, not a history.
- **Only these keys reach the page.** Story summaries, seeds and anything else in the profile never go into an HTML file.
- **The box at the top is the assistant's** (`--summary`, `--next`): what it will check next and what is missing; never a finding the checks have not produced.

## Asking the same things in chat

A host's choice tool is for the fixed sets (home type, deal-breakers, depth); the typed answers — a place, a figure, a date — go in plain text or the tool's free-text field, never as invented options. At most three questions, in one message, each with its default or "not sure" stated.
