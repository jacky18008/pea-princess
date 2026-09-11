Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The requirements contract: the form, the file, the page

Two fixed frames, so that no assistant ever writes HTML and every assistant produces the same pages:

| | The data (what the model writes) | The page (what the person sees) |
|---|---|---|
| Requirements | `profile.yaml` — the keys below | `viewer/requirements.html`: `scripts/panel.py --profile profile.yaml > requirements.html`, or the person pastes the YAML into the page |
| Report | `report.json` — `references/report-schema.json` | `viewer/viewer.html`: `scripts/render.py report.json > report.html`, or the person pastes the JSON into the page |

Both pages are one file each, work from disk in any browser, load nothing from the network and store nothing. In a chat box without a shell the assistant writes the YAML or JSON in a code block and tells the person which page to paste it into; with a shell it writes the page itself and names the file.

## The form's fields and where they live in `profile.yaml`

| Question (typed = the person types it; choice = a fixed set) | Type | Key |
|---|---|---|
| Where do you go most days? | typed place | `commute.destination` |
| How exact is that place? | choice: unknown · district · station · address | `commute.destination_precision` |
| Arrive by | time | `commute.arrive_by` |
| Longest door-to-door | number, minutes | `commute.max_door_to_door_min` |
| Monthly ceiling, and whether it includes bills | number + choice | `budget.all_in_pcm_ceiling` (rent + bills) or `budget.rent_pcm_target` (rent only) |
| Home type | choice: room_in_shared_flat · studio · one_bed · two_bed · three_bed_plus · any | `flat_type` |
| People living there | number | `occupants` |
| A real bedroom (door and window) | yes/no | `separate_bedroom_required` |
| Earliest / latest move-in | dates | `move_in_window.earliest`, `move_in_window.latest` |
| What matters most, in order | choices | `priorities` (list: quiet, commute, price, light, space) |
| Deal-breakers | choices | `floors.reject_ground_floor`, `light.reject_no_sky`, `quiet_over_light`, `avoid` (the exact strings of the deal-breaker menu in `onboarding.md`), `must_haves` |
| How deep | choice: lite · standard · deep | `budget_mode` |
| Reply language | choice | `language` |
| Your own questions for every flat | typed lines | `my_questions[].question` |

Rules that make the frame safe to fill:
- **Blank means unknown.** The page writes nothing for an empty field; the profile keeps the key empty; the report shows U. Nobody guesses a destination or a budget.
- **Precision travels with the destination.** A district-level destination gives an estimated commute, never a verified one; the page and the report both say so.
- **A form entry is `provenance: user_supplied`**, like an answer in chat. The assistant merges the pasted YAML into `profile.yaml`, says in one line what changed, and records the revision (`.pea-state` when the session harness is on).
- **The page shows only its own keys.** `panel.py` inlines the subset above; story summaries, seeds and anything else in the profile never go into an HTML file.
- **Nothing on the page is a research result.** The "what the assistant will do" box is filled by the assistant (`--summary`, `--next`) and says what it will check and what is missing; it never states a finding the checks have not produced.

## Which tool asks which

The same three essentials can be asked in chat. A host's choice tool is for the fixed sets (home type, deal-breakers, depth); the typed answers — a place, a figure, a date — go in plain text or the tool's free-text field; never as invented options. When the person prefers a form, or the host has no question tool, the assistant says: open `requirements.html`, fill what you know, copy the YAML back.
