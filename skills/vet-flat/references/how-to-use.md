Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# How to use this skill, and how to change any setting by talking

Read this when the user asks how something works or changes their needs or the scope of checks. Explain changes in their language, not configuration syntax. A clear user instruction authorizes its stated change; do not ask for a redundant yes. Clarify only material ambiguity, while continuing independent work.

## Optional voice input

If the person prefers speaking, suggest dictation into their existing chat box. Built-in device dictation or their usual app is enough; [Typeless](https://www.typeless.com/pricing) and [Wispr Flow](https://wisprflow.ai/pricing) are optional examples with usage-limited free plans (checked 2026-09-11; current limits are on those pages). They can describe needs, housing experiences or changes without preparing a form. Suggest checking names, postcodes, amounts, dates, negations and conditions before sending. Offer this when useful, not in every opening; neither a new app nor a live voice-call feature is required.

## The one rule for every setting change
1. Capture the user's exact words and update the versioned requirements per `session-harness.md`. Produce a **diff of `profile.yaml`** for fields it can represent: `field: old → new`, one line per field. The latest durable requirements take precedence; the profile is a compatibility projection, not a second authority.
2. Show the effect in plain words, for example “The monthly limit is now £2,300 including bills; the quiet-bedroom requirement still applies.” Keep the technical diff in the local record unless requested. Apply explicit changes; confirm your own suggested changes or clarify ambiguity. Preserve conditions, scope and exceptions even when the legacy profile has no matching field.
3. If execution is available, run `python3 scripts/profile_check.py profile.yaml`. Never claim a file was saved or validated without observing it. Without file tools, keep the updated requirements in the conversation and state that limitation only when saving matters; do not hand a new renter a command to run.
4. If “check more carefully” has no scope, use the current decision to propose the next useful check. Ask only if different interpretations materially change the work or cost. Use native choices if actually available, otherwise text; at most three clarifications, usually fewer.

## Phrases → fields
| The user says | Field | Notes |
|---|---|---|
| "my monthly limit is £2,300 including bills" / 「每月總花費上限 2300，含帳單」 | `budget.all_in_pcm_ceiling: 2300` | total monthly cost includes bills and council tax; rent target stays unless mentioned |
| "rent around 1,700" | `budget.rent_pcm_target: 1700` | warn if the gap to the ceiling cannot hold bills |
| "dig deeper on crime and management, keep the rest light" / 「治安跟管理挖深，其他輕量」 | `axis_depth.crime: deep`, `axis_depth.management: deep`, `budget_mode: lite` | unset axes follow `budget_mode` |
| "check everything thoroughly for these two flats" | `budget_mode: deep` for those candidates only | explain the extra checks in plain words; respect user limits |
| "keep it cheap / I'm on a £20 plan" | `budget_mode: standard` with fewer axes (not `lite` with all axes) | see `budget-modes.md`: lite triples invented numbers |
| "no more than 20 fetches per flat" | `limits.max_fetches_per_flat: 20` | hard cap, whatever the depth |
| "I hate noise" / 「我怕吵」 | `quiet_over_light: true`, add "main windows facing a main road or a railway" to `avoid` | L4 |
| "I need to see sky" | `light.reject_no_sky: true` | L2 |
| "ground floor is fine if it's dry" | conditional requirement in `.pea-state`; `floors.reject_ground_floor: false` only as a projection | preserve “dry” as a required condition with evidence; unknown dryness cannot become an unconditional pass |
| "must have a washing machine" | add `washing_machine_in_flat` to `must_haves` | a must-have that fails is a hard fail |
| "I always ask X" | append to `my_questions` with `when`/`kind` (classify: compare / filter / viewing / sign) | see `onboarding.md` |
| "stop asking me about Y" | change the follow-up question policy | this does not itself waive the requirement; ask once if the user also wants Y retired |
| "start over" | begin with useful examples and learn preferences gradually | do not silently delete the saved history |
| 「只問把關的八題」 / "just the eight that matter" | `advanced.fixed_form.questions: gate` | the fixed form drops to the money-and-paperwork eight |
| "all 18 questions, always" / 「全部 18 題都要」 | `advanced.fixed_form.questions: full` | adds council tax band, guarantor, their tenant checks, furniture and inventory |
| "ask me about everything" / 「不知道的都問我」 | `advanced.fixed_form.ask_if_missing: all` | prioritize at most three essential questions now; continue work and defer the rest unless a full questionnaire is explicitly requested |
| "don't ask, just mark unknown" / 「別問我，不知道就寫不知道」 | `advanced.fixed_form.ask_if_missing: none` | say out loud that an unknown is a risk, never a pass |

The last four live under `advanced:` at the bottom of `profile.yaml`, and the defaults there are
right for almost everyone: the number of questions follows `budget_mode` on its own (lite eight,
standard fourteen, deep eighteen). Never raise them in onboarding — offer them only when the user
asks to be asked less, or asks for more.

## Which questions get answered
Every flat answers the same form (`references/fixed-questions.yaml`). How many depends on the depth:
**lite** the eight gate questions (deposit, money up front, the contract, the landlord, the schemes,
the licence) · **standard** those plus six the listing answers (size, energy letter, bills, minimum
term, break clause, move-in) · **deep** all eighteen, adding the council tax band, whether a UK
guarantor is needed, what their tenant checks want from you, and what furniture and inventory come
with it. `advanced.fixed_form` overrides that, and the mapping itself lives in one place: the
`tiers` block of `references/fixed-questions.yaml`.

## Explain the scope in plain words
- **Quick initial check** (`lite` internally): available facts first; label what remains unchecked.
- **Usual checks** (`standard`): cover the relevant issues and inspect supporting evidence.
- **Closer review of a shortlist** (`deep` / `breadth`): spend more effort on the few remaining candidates and explain what extra information may change the decision.
Per-axis depth overrides the mode for that axis only. Hard caps in `limits` win over everything.

## Teaching a new user (two minutes)
1. Begin with a useful answer or comparison; follow `onboarding.md` for examples and source limits.
2. Learn priorities from their reaction instead of requiring a completed profile first.
3. Explain that they can change budget, deal-breakers or the amount of checking at any time.
4. Summarize only changes that matter to the current recommendation. Keep internal fields and execution labels out of ordinary replies.

## If the model is small or the plan is limited
Keep explicit fields in the internal record and inject current requirements through the supported host. Explain their effect to the user in plain words. Use conservative limits and validate when possible; do not make the user manage implementation details because the model is small.
