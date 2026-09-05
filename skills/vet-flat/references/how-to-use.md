Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# How to use this skill, and how to change any setting by talking

Read this when the user asks how something works, how to change a setting, how deep to go, or what a field means. Teach by doing: show the current value, propose the change as a diff, apply only after a yes.

## The one rule for every setting change
1. Turn the user's words into a **diff of `profile.yaml`**: `field: old → new`, one line per field, nothing else touched.
2. Show the diff and ask for a one-word confirmation. Never apply silently, never invent a field, never change a field the user did not mention.
3. After applying, run `python3 scripts/profile_check.py profile.yaml` (shell mode) and show its verdict; without a shell, re-read the changed lines back to the user.
4. If a phrase is ambiguous ("dig deeper" with no axis named), ask which axis, offering the list.

## Phrases → fields
| The user says | Field | Notes |
|---|---|---|
| "my max is 2,300 all in" / 「上限 2300 含帳單」 | `budget.all_in_pcm_ceiling: 2300` | all-in includes bills and council tax; rent target stays unless mentioned |
| "rent around 1,700" | `budget.rent_pcm_target: 1700` | warn if the gap to the ceiling cannot hold bills |
| "dig deeper on crime and management, keep the rest light" / 「治安跟管理挖深，其他輕量」 | `axis_depth.crime: deep`, `axis_depth.management: deep`, `budget_mode: lite` | unset axes follow `budget_mode` |
| "go deep on everything for these two flats" | `budget_mode: deep` for those candidates only (say so in the report's first line) | the escalation ladder does this automatically for a final shortlist |
| "keep it cheap / I'm on a £20 plan" | `budget_mode: standard` with fewer axes (not `lite` with all axes) | see `budget-modes.md`: lite triples invented numbers |
| "no more than 20 fetches per flat" | `limits.max_fetches_per_flat: 20` | hard cap, whatever the depth |
| "I hate noise" / 「我怕吵」 | `quiet_over_light: true`, add "main windows facing a main road or a railway" to `avoid` | L4 |
| "I need to see sky" | `light.reject_no_sky: true` | L2 |
| "ground floor is fine if it's dry" | `floors.reject_ground_floor: false` | the damp check stays on the viewing list |
| "must have a washing machine" | add `washing_machine_in_flat` to `must_haves` | a must-have that fails is a hard fail |
| "I always ask X" | append to `my_questions` with `when`/`kind` (classify: compare / filter / viewing / sign) | see `onboarding.md` |
| "stop asking me about Y" | remove Y from `must_haves` or `avoid` | show the diff |
| "start over" | offer `profiles/` examples or the six intake questions | never delete the old profile without a yes |

## Depth in plain words
- **lite**: the scripts for the fetchable facts and nothing else; fast; more invented numbers if the model is weak, so every number must show a source.
- **standard** (default): every axis, cheap workers only for pasted text, strong judge.
- **deep / breadth**: one reader per reading-heavy axis; for the final two or three flats.
Per-axis depth overrides the mode for that axis only. Hard caps in `limits` win over everything.

## Teaching a new user (two minutes)
1. Say what you can and cannot do in three sentences (the pitch in `onboarding.md`).
2. Show the profile they are using, in plain words, six lines.
3. Offer the three most common changes as examples (budget, deal-breakers, depth) and how to say them.
4. Tell them the report's first line always states the configuration used, so they can check.

## If the model is small or the plan is limited
Prefer explicit fields over prose; echo every change as a diff; run the validator; keep `limits` conservative; when unsure, ask one question rather than guessing.
