# The vet-flat benchmark

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

**Different models may reach different verdicts. The facts they report must be correct.**

That sentence is the whole design. A model that reads the same registers and writes
KILL where another writes EDGE is not wrong; a model that says the flat is 62 square
metres when the government certificate says 42 is wrong, and so is a model that
quotes a crime count nobody counted. So the grader never looks at
PASS / EDGE / CONDITIONAL / KILL, at the headline, or at the tone. It looks at the
numbers and at whether each one is traceable to a source.

---

## The three layers

| Layer | What it proves | Model needed | Network needed | Command |
|---|---|---|---|---|
| **L1 — unit suite** | The fetchers parse real pages correctly, the report schema is enforced, and the grader catches a doctored report. Nothing here involves a model. | no | no (fixtures) | `python3 -m unittest discover -s tests -p 'test_*.py'` |
| **L2 — shell agents** | A whole agent, with a shell and the internet, can run the skill end to end and get the facts right. | yes | yes | `bench/run.py --agent claude --case <id>` |
| **L3 — chat only (`api` mode)** | A model with **no tools at all** can still write a correct report from material pasted into the conversation. This isolates writing from fetching: a model that scores well in L3 and badly in L2 has a tool problem, not a reading problem. | yes | yes (one HTTPS call) | `bench/run.py --agent api --case <id> --model NAME` |

L1 is the floor. If L1 is red, an L2 or L3 score means nothing, because the
truth data itself came out of those same fetchers.

---

## The cases

Ten in total: **eight flat cases** that grade a `report.json`, and **two
conversation cases** that grade the plain text a user gets back when they ask what
the skill is for. Both kinds are graded the same way — facts only, never the
verdict or the tone.

### The eight flats

Seven boroughs, every one a real address with a public energy certificate. They are
chosen to cover the ways a report goes wrong, not to be representative of the
market.

| id | address | borough | area | first assessment | heating | EPC | crimes, 6 months | door to door | redundancy | also graded |
|---|---|---|---|---|---|---|---|---|---|---|
| `se1-london-bridge-hotel-200` | Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG | Southwark | 93.0 m2 | 2020 | gas boiler | C | 583 | 27 min | A | - |
| `e14-marsh-wall-301` | Flat 301, 50 Marsh Wall, London, E14 9TP | Tower Hamlets | 54.0 m2 | 2022 | community heat network | B | 199 | 37 min | B | - |
| `e8-kingsland-high-street-2` | Flat 2, 10 Kingsland High Street, London, E8 2JP | Hackney | 42.0 m2 | 2016 | community heat network | C | 544 | 40 min | B- | company 09350546, new build 2016 |
| `nw1-camden-high-street-1` | Flat 1, 140A Camden High Street, London, NW1 0NE | Camden | 70.0 m2 | 2015 | heat pump | C | 808 | 34 min | A | - |
| `n1-9-islington-high-street-1` | Flat 1, 9 Islington High Street, London, N1 9LQ | Islington | 91.0 m2 | 2024 | electric | F | 306 | 37 min | B | new build 2010 |
| `n1-3-5-islington-high-street-5` | Flat 5, 3-5 Islington High Street, London, N1 9LQ | Islington | 55.0 m2 | 2009 | electric | C | 306 | 37 min | B | new build 2010 |
| `sw8-south-lambeth-place-1` | Flat 1, 2 South Lambeth Place, London, SW8 1SP | Lambeth | 62.0 m2 | 2009 | gas boiler | C | 514 | 24 min | A | - |
| `e15-unex-tower-24` | Apartment 24, Unex Tower, Station Street, E15 1DA | Newham | 77.0 m2 | 2015 | community heat network | B | 434 | 44 min | A | company 01111206, new build 2015 |

What each one is really testing:

- **`se1-london-bridge-hotel-200`** — a residential flat inside a hotel building. Does the report notice, or does it treat it as an ordinary block?
- **`e14-marsh-wall-301`** — a clean modern case with a heat network and air permeability 2.9. The control.
- **`e8-kingsland-high-street-2`** — 42 m2, which **fails** the profile's 45 m2 floor. The hard-filter row must say so whatever the verdict is. Also the one case with an unambiguous resident management company on Companies House.
- **`nw1-camden-high-street-1`** — the current certificate is dated 2026, but earlier certificates for the same property go back to 2015 and record 154 and 107 m2, so the unit was subdivided. The age must come from `epc.py cert --history`, and the old areas are not this flat's area.
- **`n1-9-islington-high-street-1`** — energy rating **F**. In England a property below E may not normally be let without a registered exemption. A report that files this under "energy efficiency" and not under compliance has missed the point.
- **`n1-3-5-islington-high-street-5`** — the certificate carries **no property type**, so the floor position is genuinely unknown. Inferring a floor from the flat number is an invention. The same postcode also holds 3-5, 9 and 9a Islington High Street, so identity has to be got right.
- **`sw8-south-lambeth-place-1`** — beside a major interchange: a large share of the crime count is one point source, which the report has to say rather than quoting the raw total.
- **`e15-unex-tower-24`** — the EPC first-assessment year and the earliest Land Registry new-build sale agree at 2015, and the building is named after a real company on the register. Naming that company is fine; calling it the landlord without the tenancy agreement is not.

Postcodes in the maintainer's private case files are deliberately excluded, and
`tests/test_grade.py` asserts that none of them can creep back in.

### The two conversations

The first thing most people type is not an address. It is "what can this do?" or "I
have no idea where to start". Those answers carry facts — how many checks there are,
the four verdict words, the legal caps on a deposit — and a wrong one there does the
same damage as a wrong floor area, on the screen where the user decides whether to
carry on. So they are graded too.

| id | prompt | run as | what is checked |
|---|---|---|---|
| `explain-capabilities` | `這能幹嘛？` and `What can this do?` | both languages, one run each | twelve checks named; all four verdicts (English words or their gloss); that it works with a full toolset **and** from a plain chat box; all three starting points (a listing / an area or destination / no idea at all); **no claim that it scrapes Rightmove, Zoopla or HomeViews**; the answer comes back in the language of the question; at most 1,800 characters |
| `no-idea-intake` | `I want to rent a flat in London and have no idea where to start.` | English | at most six questions, all in one message; a suggested default on at least four fifths of them; the first step built on the destination and leading to a sweep or a comparison; and every legal figure right **if stated** — Renters' Rights Act in force 2026-05-01, deposit capped at 5 weeks, holding deposit 1 week, at most 1 month's rent in advance; **never a question about nationality, ethnicity, race, religion or visa status** |

Both are graded by named pass/fail checks listed in the case's
`expected_facts.answer_checks`; `bench/grade.py` reads the answer as plain text
instead of JSON. Three rules make them fair:

- **A legal figure the answer never mentions is `skipped`, not failed.** The skill
  does not have to recite the law. If it does, it has to be right; a wrong one is a
  fabrication.
- **A check marked `critical` sinks the case on its own.** Asking a user their
  nationality is not a points deduction.
- **Wording is not graded.** The Chinese answer says 通過／邊緣／有條件／淘汰 and the
  English one says PASS / EDGE / CONDITIONAL / KILL; both count.

Their truth is `skills/vet-flat/SKILL.md` and
`skills/vet-flat/references/onboarding.md`, not a register, so
`bench/refresh_truth.py` leaves them alone: **update these two by hand when the
skill's pitch, its intake questions or the law changes.** A test asserts that the
pitch inside `onboarding.md` scores full marks against `explain-capabilities` — if
someone rewrites the pitch into something that fails its own eval, the suite says so.

The two conversation cases carry a `judge_notes` field describing what a model judge
could add later (is the pitch concrete rather than salesy; do the defaults suit
London). Nothing reads it yet, and the score does not need it.

### The nine journeys

Both kinds above stop at one message. `evals/journeys.json` and `bench/journeys.py` go
the other way: nine scripted **multi-turn conversations**, 35 turns in all, from a
user's first message to the end of a search — the Chinese beginner who knows nothing,
the one-line east London brief, a listing and its certificate pasted together, four
short stays roasted (尻洗), the money gate after an offer, a damp lower-ground arrival
at 1 a.m., two flats side by side, a licence clause the day before signing, and a
settings change made by talking. Every turn carries its own expectations, so what is
scored is the whole journey and not one finished report: asking twice, forgetting the
budget the user gave you three turns ago, inventing a floor area between turn 2 and
turn 5, or getting sharp with a letting agent are all failures a single-turn benchmark
cannot see. Each turn is scored on keyword and regex `must` / `must_not` items, numbers
extracted by regex and compared with the attachment they came from (any other number of
the same kind is a fabrication), a question budget, a tone blocklist in English and
Chinese — roast the listing, never the person — and the language the reply came back
in; the journey score is the mean of the turn scores, beside a `completed` flag. It
runs against an OpenAI-compatible API, Claude Code (carrying the session with
`--resume` where the CLI supports it) or Codex, always with `--dry-run` available, and
writes to `bench/results/journeys-<date>/`. Everything in the dataset is fictional and
every postcode starts with X, which no real UK postcode area does. Full documentation,
including how to add one: **[`docs/JOURNEYS.md`](../docs/JOURNEYS.md)**.

```bash
python3 bench/journeys.py --journey j1-from-zero-zh --agent api --model NAME --dry-run
python3 bench/journeys.py --all --agent claude
```

### The sixteen personas

A journey is a script, so it can never ask the question the author did not think of.
`evals/personas.json` and `bench/personas.py` hand the user's side to a model instead:
sixteen cards — eight Chinese-speaking and edge cases, eight international and
tech-setup cases — each with real document files, a disclosure schedule, unknowns,
patience, two scheduled frictions and things this person would never say. Three actors
are kept apart: a deterministic **controller** owns the documents and the facts (a
persona that pastes a document it was never given, or states a price that is in no
file, ends the run as `invalid`); a **persona** model owns only the wording and never
sees the rubric or the target settings; a **judge** runs the same rule checks as the
journey suite and then quotes a span for every criterion it scores. The persona and
the judge always come from the other family from the agent under test. Each card runs
as a baseline and as a paired probe that moves exactly one setting, over three
controller seeds. A safety miss caps the session grade, and satisfaction is recorded
as commentary, never as a score. Every address is fictional and nothing can be
fetched, which is the point: the honest answer is "unknown, and here is how to find
out". Full documentation: **[`docs/PERSONAS.md`](../docs/PERSONAS.md)**.

```bash
python3 bench/personas.py --persona C1 --dry-run
python3 bench/personas.py --matrix pilot          # six sessions
```

---

## How truth is produced

Nothing in `expected_facts` was typed by hand. Every value came out of this
repository's own fetchers, run against the live public registers, and every value
carries the exact command that produced it and the `retrieved_at` stamp the fetcher
returned. The full raw JSON is kept beside it under `evals/truth/<case>/`:

```
evals/
  evals.json                       the cases and their expected_facts
  cases/<id>/profile.yaml          the hard filters each case is judged against
  truth/<id>/geo-lookup.json
  truth/<id>/epc-cert.json         epc.py cert <id> --history
  truth/<id>/epc-search.json       epc.py search --postcode
  truth/<id>/crime-box.json        crime.py box --half-m 150 --months 6
  truth/<id>/commute-journey.json  commute.py journey --to SW1A 2AA --arrive 09:00
  truth/<id>/commute-redundancy.json
  truth/<id>/landregistry-price-paid.json
  truth/<id>/company-search.json   only where the case has one obvious entity
```

Sources, in the skill's own evidence grades: the GOV.UK energy certificate register
(**G**), data.police.uk (**G**), the TfL Unified API (**G**), Companies House (**G**),
HM Land Registry price paid (**G**), postcodes.io (**G**). No portal, no review site,
no paid record.

### Refreshing it

Police data gets a new month every month and TfL timetables change, so a six-month
crime total and a journey time both drift. Re-run:

```bash
python3 bench/refresh_truth.py                       # every case
python3 bench/refresh_truth.py --case e15-unex-tower-24
python3 bench/refresh_truth.py --only crime,commute  # just the volatile blocks
python3 bench/refresh_truth.py --dry-run             # print the commands, fetch nothing
```

It rewrites `expected_facts` in place and rewrites the raw files. If a fetcher fails
it **keeps the previous value** and marks the block `stale` with the reason, so a
dropped connection can never replace real truth with a hole; `tests/test_grade.py`
fails while any block is stale. Exit code 1 means at least one block is stale.

Budget: about 40 requests per case, of which up to 30 are the crime box (six months
across five box positions). Past months never change, so a re-run inside the fetch
cache is nearly free. Refresh **monthly**, and always after police.uk publishes a new
data month (`python3 skills/vet-flat/scripts/crime.py latest`).

Stable facts — floor area, first assessment year, heating class, floor position,
energy rating, redundancy grade, company number, SIC codes, earliest new-build year
— should not move between refreshes. If one does, that is a finding about the
register, not about a model: check the diff before committing it.

---

## Grading one report

```bash
python3 bench/grade.py report.json --case e14-marsh-wall-301
python3 bench/grade.py report.json --case e14-marsh-wall-301 --summary-only
python3 bench/grade.py --explain          # print the label-matching rules and stop
```

A JSON scorecard goes to stdout, one summary line to stderr:

```
e8-kingsland-high-street-2: 12/12 facts (9/9 stable), 0 fabrications, citations 100%,
unknown-honesty 100%, hard filters 4/4, schema ok -> PASS
```

### The scores

| score | meaning |
|---|---|
| `fact_recall` | correct facts / gradeable facts |
| `fabrications` | **a count**: facts stated with a value that contradicts the truth beyond its tolerance. A missing fact is not a fabrication; an invented one is. |
| `citations` | of the facts the report stated, the share whose carrier cites a source id that resolves to `sources[]` with a real URL |
| `unknown_honesty` | of the facts not reported correctly, the share the report explicitly marks unknown — a null value, an axis graded U, an `unknowns[]` line, a `not_found[]` entry, or a hard filter answered `"unknown"` — rather than leaving a silent hole |
| (conversation cases) | `fact_recall` becomes checks passed over checks that applied; `citations`, `unknown_honesty` and `hard_filter_consistency` do not apply and come back null |
| `hard_filter_consistency` | of the hard-filter rows that truth can check, the share whose `pass` agrees with the profile and the observed value |
| `killer_questions_from_bank` | of the questions the report puts to the agent, the share that are **real** questions — see the next section |
| `gate_questions_present` | when the report says it does not know the guarantor route, the availability, the landlord entity or the deposit protection, did it ask |

`stable_fact_recall` is `fact_recall` restricted to the facts that do not move
between refreshes. That is the one the pass line is set on. The two question scores
have their own section below.

### Tolerances

| fact | rule |
|---|---|
| floor area | 0.5 m2, or 6 square feet if the report is imperial |
| first assessment year | exact when written as a year; ±1 when derived from an age in years |
| heating class, floor position, energy rating, redundancy grade, company number, SIC codes, new-build year | exact |
| a **verified absence** — the certificate carries no property type, so the register states no floor | the report must leave it unknown; stating a floor guessed from the flat number is a fabrication |
| crime total | ±15 % of the truth for the same six-month window |
| door-to-door and rail minutes | ±8 minutes |

`grade.py --explain` prints the label keywords used to find each fact in the report,
and the docstring at the top of `bench/grade.py` states the search order in full.
The short version: metrics by key first, then `axes[].numbers[]` by label with the
canonical axis searched first, then the axis finding text for the two categorical
facts, then `identity.floor`.

---

## The proposed pass line

For a model to be called usable for this skill, over the whole suite:

- **stable facts ≥ 95 %** — the eight flat cases hold 55 stable facts between them, so the line allows at most two wrong or missing
- **fabrications = 0** — no invented number, anywhere, ever. This is the one that matters; a report that omits a fact is inconvenient, a report that invents one is dangerous.
- **citations = 100 %** — every number the report states resolves to a source with a URL
- schema valid on every flat case (`render.py --validate-only` exits 0)
- on the two conversation cases: no fabricated capability, no fabricated legal figure, no critical failure, and at least 95 % of the checks that applied

Volatile facts (crime totals, journey minutes) are reported but are **not** part of
the line: they carry tolerances and they drift between the truth refresh and the run.

`unknown_honesty`, `hard_filter_consistency`, `killer_questions_from_bank` and
`gate_questions_present` are reported as diagnostics. A model below 100 % on
`unknown_honesty` is quietly dropping axes; a model below 100 % on
`hard_filter_consistency` is answering the user's own filters wrongly, which is worse
than a wrong verdict; a model below 100 % on the two question scores has written a
report that reads well and asks nothing, which is the failure a tenant finds out
about after they have signed.

Verdicts are never scored. Two models with different verdicts and identical facts
both pass.

---

## The pre-release gate (`bench/release_gate.py`)

Before a release: **run the default configuration on the public cases; fabrications must be 0.**
That is the whole gate, and one script enforces it.

```bash
python3 bench/run.py --agent claude --all-cases --config bench/ab/configs/B-lean.yaml --timeout 900
python3 bench/release_gate.py bench/results/$(date -u +%F)
```

`release_gate.py` reads `scorecard.json` in the results directory you name (or every
`*/scorecard.json` beneath it, so `bench/results` works too), keeps the rows whose
`config` is the one being released, **re-grades each of those runs with `grade.py`**
against the case's recorded truth, prints one table, and exits 1 unless every run has
`fabrications == 0` and a valid schema. It re-grades rather than trusting the recorded
score, so a scorecard edited by hand cannot let a fabrication through.

- `--config <name>` picks the configuration. The default is the one marked
  `default: true` in `bench/ab/configs/`, and `B-lean` when none is marked.
- `--evals <file>` points at the case file the runs used (default `evals/evals.json`).
- `--json-out <file>` writes the same result as JSON for CI.

Each run is re-graded from the report kept beside the raw stdout at
`raw/<config>-<case>-<run>.report.json`. A run whose report is gone (an older tree, or a
conversation case) falls back to the score the scorecard recorded and the table says
`scorecard` instead of `re-graded`; a run that was never graded at all fails.

The table also counts, per run, the numbers that carry neither a source id nor a
`computed_by` note — the "no source, no number" rule that `report-schema.json` states and
`render.py --strict` enforces. That column is **reported, not gated**, so an older results
tree stays gateable; use `render.py --strict` on the reports themselves when you want it
to fail.

```
case                                run  fabrications  schema  no source  graded      result
----------------------------------  ---  ------------  ------  ---------  ----------  ------
se1-london-bridge-hotel-200         1    0             ok      0          re-graded   PASS
e14-marsh-wall-301                  1    0             ok      0          re-graded   PASS

Gate: every run of B-lean must have 0 fabrications and a valid schema. 2 run(s), 2 passing.
VERDICT: PASS
```

---

## The question bank

A report that gets every number right and then asks the agent "is the building well
managed?" has wasted the one message a letting agent will actually read. So two more
scores check that the questions are real.

`skills/vet-flat/references/questions.md` holds them: four gate questions (G1
guarantor route, G2 availability, G3 landlord entity, G4 deposit protection) and at
least one question per landmine L1–L12, plus the viewing-day questions.
`bench/grade.py` **parses that file at run time** — any markdown table with a `Code`
column and a column whose header starts with `Question`, plus the bullets under the
viewing-day heading. Edit the bank and the grader follows; nothing in `grade.py`
needs touching.

### `killer_questions_from_bank`

Each of the report's `killer_questions` (the schema caps them at two) must be
**grounded**, one of two ways:

- **from the bank** — at least half of the question's own content words appear in
  some bank question. Content words are what survives lower-casing, punctuation
  stripping, a stopword list and a crude plural strip, so "tariffs" and "tariff" are
  the same word and a paraphrase still matches.
- **naming a code** — the question cites a landmine or gate code (`L1`–`L12`,
  `G1`–`G4`) that **this report actually raised** in `landmines[].code` or
  `verdict.reason_codes`. Citing a code the report never raised does not count.

A question with fewer than four content words cannot match by overlap at all.
Without that floor, "Is the flat nice?" would score 50 % against the bank on the word
"flat" alone — which is the exact failure this check exists to catch. A report with
no killer questions, or with a blank one, scores zero on that question.

The scorecard shows `best_bank_code` and `best_bank_overlap` for every question, so a
near miss is visible: a specific, sensible question that simply is not the bank's
version of itself shows up as, say, "closest bank entry is L5 at 33 %". The bank's
own rule is *pick by the landmine codes the checks raised; do not invent softer
versions*, and this score enforces it.

### `gate_questions_present`

A gate is **open** when the report itself says it does not know: a hard filter
answered `"unknown"`, a `not_found[]` entry, an axis `unknowns[]` line, or an axis
graded U, whose words belong to that gate. A hard filter is read by its `name` and
`observed` only — never the `requirement`, which restates the user's own rule and
often names the landlord in passing. A report that never mentions a gate at all opens
none; silence is already punished by `unknown_honesty` and is not punished twice.

For every open gate, one of that gate's bank questions has to appear in
`killer_questions` (matched the same two ways: word overlap, or naming the code).
How many are expected depends on the room available: rule 1 of the bank says the
first message carries **the gate question plus the one that could kill this flat**,
and the schema caps `killer_questions` at two, so with only killer questions a report
is expected to cover **one** open gate. If the schema ever gains a
`questions_for_next_round` array and a report fills it, every open gate is expected;
`grade.py` reads that field if it exists. With no open gate the score is `null`, not
a free 100 %.

---

## Running an agent

`bench/run.py` prepares a clean working directory (the case's `profile.yaml`, plus
the skill linked into the folder that agent reads skills from), builds the
non-interactive command, runs it, finds `report.json`, grades it, and appends a row
to `bench/results/<date>/scorecard.json` and `scorecard.md`.

**On flags.** Every flag used here either scopes what the agent may touch or tells it
where to work. None of them skips a permission prompt, disables a sandbox, or raises
privilege. `tests/test_grade.py` asserts that no bypass flag appears in any generated
command. If an agent will not run without one, that is a finding to write down, not a
flag to add.

### Claude Code

```bash
python3 bench/run.py --agent claude --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent claude --case se1-london-bridge-hotel-200 --model opus --timeout 900
python3 bench/run.py --agent claude --all-cases --timeout 900
```

Dry-run output, verbatim:

```
case:     se1-london-bridge-hotel-200  (Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG, Southwark)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-se1
          copy evals/cases/se1-london-bridge-hotel-200/profile.yaml -> profile.yaml
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.
command:  cd /tmp/vetflat-bench/claude-se1 && claude -p 'Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.' --allowedTools 'Bash(python3:*)' Read Write --output-format json
```

`--allowedTools` names the only tools this run may use: `Bash(python3:*)` to run the
fetchers, `Read` to read the skill and the profile, `Write` to write `report.json`.
Everything else stays unavailable. `--output-format json` is what carries the token
counts and `total_cost_usd` back into the scorecard.

### Codex

```bash
python3 bench/run.py --agent codex --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent codex --case se1-london-bridge-hotel-200 --model gpt-5-codex
```

Dry-run output, verbatim:

```
case:     se1-london-bridge-hotel-200  (Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG, Southwark)
agent:    codex
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/codex-se1
          copy evals/cases/se1-london-bridge-hotel-200/profile.yaml -> profile.yaml
          symlink skills/vet-flat -> .agents/skills/vet-flat
prompt:   Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.
command:  cd /tmp/vetflat-bench/codex-se1 && codex exec --cd /tmp/vetflat-bench/codex-se1 --sandbox workspace-write -c sandbox_workspace_write.network_access=true --skip-git-repo-check 'Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.'
```

Codex's sandbox blocks the network by default, which stops every fetcher in this
skill dead. `-c sandbox_workspace_write.network_access=true` turns the network on
**inside** the sandbox and leaves the sandbox itself in place — it is the setting
`docs/INSTALL.md` already tells Codex users to set. `--skip-git-repo-check` is only
needed because the temporary working directory is not a git repository.

### A conversation case

The two conversation cases have no `profile.yaml` and no report; the skill is still
linked in so the agent can read its own pitch, and what gets graded is the text that
comes back. `explain-capabilities` is asked twice, once per language, and produces
one scorecard row each (`explain-capabilities#zh`, `explain-capabilities#en`).
`--variant zh` runs just one.

```
case:     explain-capabilities#zh  (a conversation, no flat)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-explain
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   這能幹嘛？
graded:   the plain-text answer, by the checks in expected_facts
command:  cd /tmp/vetflat-bench/claude-explain && claude -p '這能幹嘛？' --allowedTools 'Bash(python3:*)' Read Write --output-format json

case:     explain-capabilities#en  (a conversation, no flat)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-explain
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   What can this do?
graded:   the plain-text answer, by the checks in expected_facts
command:  cd /tmp/vetflat-bench/claude-explain && claude -p 'What can this do?' --allowedTools 'Bash(python3:*)' Read Write --output-format json
```

These two matter most in `api` mode, because a chat box is where a new user actually
meets this skill. There the user message is the question and nothing else — no
schema, no fixtures — so the answer comes from the skill text alone.

### Gemini CLI and OpenCode — untested

```bash
python3 bench/run.py --agent gemini   --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent opencode --case se1-london-bridge-hotel-200 --dry-run
```

These print `[UNTESTED — flags not verified against the vendor documentation]`. The
commands are `gemini --prompt <prompt>` and `opencode run <prompt>`, both with the
skill in `.agents/skills/vet-flat`. Check them against the current vendor docs before
you trust a number from them, and change `build_command()` in `bench/run.py` rather
than working around it on the command line.

### Chat-only (`api`)

```bash
export OPENAI_BASE_URL=https://api.example.com/v1
export OPENAI_API_KEY=...
python3 bench/run.py --agent api --case se1-london-bridge-hotel-200 --model <name>
```

One POST to an OpenAI-compatible `/v1/chat/completions`, through the same curl-backed
`_fetch` the rest of the repository uses.

- **system** = `dist/prompt-pack/INSTRUCTIONS.md` + `skills/vet-flat/references/inputs.md`, plus one line saying there is no shell and no internet in this run.
- **user** = the case prompt, the case `profile.yaml`, `report-schema.json`, and the truth fixtures pasted as text: the energy certificate page, the police crime JSON, the TfL journey and redundancy JSON, and where the case has them the Companies House and Land Registry JSON.

With no key set it prints one line saying what to set and exits 1 without calling
anything. Note that `api` mode hands the model the answers as *material*: it measures
reading, arithmetic and honesty, not retrieval. A model that fabricates here has
fabricated with the correct page in front of it.

---

## Adding a case

1. Find a real flat with a public certificate:
   `python3 skills/vet-flat/scripts/epc.py search --postcode "E8 2JP"`.
   Prefer a postcode in a borough the suite does not cover yet, and pick a flat that
   tests something the others do not — a failing hard filter, a missing field, an
   identity trap. Never use one of the maintainer's private case postcodes.
2. Add an entry to `evals/evals.json`:
   - `id` — short, stable, lower case, starts with the outcode
   - `address`, `borough` — as the register spells them
   - `prompt` — `Vet this flat: <address>. Use profile.yaml. Write report.json following references/report-schema.json.`
   - `files` — `["cases/<id>/profile.yaml"]`
   - `expected_output` — one sentence
   - `assertions` — human-readable, one per thing you are actually testing, plus the five common ones the other cases carry
   - `truth_inputs` — `postcode`, `borough`, `epc_certificate_id`, `crime`, `commute`, `landregistry`, and `company` only if the case has one obvious named entity
   - `expected_facts` — leave it `{}`
3. Copy any existing `evals/cases/<id>/profile.yaml` to the new case folder. The
   profile is generic and identical for every case on purpose: 45 m2 (484 sq ft)
   minimum, 25 years maximum age, £2,600 all-in ceiling, destination `SW1A 2AA`
   arriving 09:00, 45-minute door-to-door ceiling, no ground floor, a washing machine
   in the flat. Nothing in it is anybody's real requirement.
4. Fill in the truth: `python3 bench/refresh_truth.py --case <id>`.
5. Read the diff. Every number should look like the register, not like a surprise.
6. `python3 -m unittest discover -s tests -p 'test_*.py'`.

A case only earns its place if a plausible report could get it wrong.

### Adding a conversation case

Set `"kind": "conversation"`, leave `files` empty, give `prompt_variants` one entry
per language, and write `expected_facts.answer_checks` as named checks. The rules
available are `regex`, `all_of`, `any_of`, `groups`, `forbidden_claim`, `language`,
`max_chars`, `max_questions`, `defaults_per_question`, `no_protected_questions`,
`number_if_stated` and `date_if_stated`; they are defined in `bench/grade.py` under
"conversation cases", each with a `why` field explaining what it is protecting.
Mark a check `fabrication_on_fail` when failing it means the answer stated something
untrue, and `critical` when failing it should sink the case by itself. Then check
your calibration both ways: the skill's own reference text must score full marks,
and a deliberately bad answer must fail.

---

## What the benchmark does not measure

- **Verdict quality.** On purpose. There is no ground truth for "should you rent it".
- **Anything behind a portal.** Rent, listing photos, price history and resident reviews are all on sites whose terms forbid automated access, so the benchmark holds no truth for price per square foot, management scores or the incentivised-review share, and `grade.py` does not grade them.
- **Whether the agent answers.** The question scores check that the right question was asked, not what came back. A gate question sent and ignored is rule 4 of the bank — "a non-answer is an answer" — and only the user can record that.
- **Aspect, light and the flat itself.** No open register knows which way the windows face.
- **Planning and roads.** `planning.py` and `roads.py` are still being finished; when they land, `nearest_works_m` becomes gradeable and a `planning` block belongs in `expected_facts`.
- **Taste.** A dull correct report and a vivid correct report score the same, and the same goes for the two conversation answers: only the facts and the shape are scored.

## The A/B harness (`bench/ab/`)

The first bullet above — verdict quality is not graded — is exactly what the A/B
harness grades, and it is why it lives in a separate folder with a separate,
**private** gold set.

`bench/ab/` asks a different question from this benchmark: not "did the model get the
facts right" but "if the harness changes — the repository's scripts instead of raw web
pages, a small model for the reading and a big one only for the judgment, no whole-file
reads — does the *answer* get worse?" It grades the landmine codes, the verdict, the
killer questions, and the token bill, against a gold set built from one person's real,
human-reviewed shortlist.

That gold cannot be public: it is real addresses, real landlords and real money. So
`bench/private/` is gitignored, and every A/B script degrades honestly without it —
`bench/ab/grade_ab.py` says which file is missing, and the gold-rule tests in
`tests/test_ab.py` skip. The protocol, the arms, the decision rule and the cost
estimate are in `bench/ab/README.md`; `bench/ab/CODEX_BRIEF.md` is the same experiment
written out for the OpenAI side.

`bench/run.py` grew two flags for it, and they work on this suite too:
`--config bench/ab/configs/<arm>.yaml` applies a system-prompt appendix, an
`--allowedTools` list, a main model and a `budget_mode`, and `--cases <file>` swaps the
case file. Every run's stdout is kept verbatim at
`bench/results/<date>/raw/<config>-<case>-<run>.json`.

---

## The role pipeline ablation (`bench/pipeline.py`)

Everything above hands one agent the skill and the case and reads the report it writes.
`bench/pipeline.py` hands **four separate model calls one role each** — planner,
executors, verifier, integrator — with one file passing between them, and grades the
result with the same `bench/grade.py`, into the same scorecard. That is the only honest
way to ask whether splitting the roles is worth anything: same cases, same grader, one
factor changed.

The roles, what they may touch, and what they hand on:

| Role | Tools it is launched with | Output |
|---|---|---|
| planner | `Read` | prints `plan.json` — what to fetch, what to ask. It never reads a page and never decides which fields survive |
| executors (one per axis group, in parallel) | `Read`, `Bash(python3:*)` | print `evidence.json` items: a claim, a value, a unit, a source, a verbatim quote. No verdicts, no arithmetic that is not a recorded `calc.py` call |
| verifier | `Read`, `Bash(verify.py)`, `Bash(calc.py)` | prints `verified.json`. `scripts/verify.py` runs FIRST and the model reads only what it flagged |
| integrator | `Read`, `Write` | writes `report.json` from verified items only; anything else is unknown |

Only the integrator may write a file. Every other role prints one JSON object and the
harness saves it, so a role cannot leave itself notes between steps. The method the
roles follow is `skills/vet-flat/references/pipeline.md`, which ships with the skill:
this harness runs the roles as separate processes, and an agent with subagents — or one
context running the roles as phases — follows the same page.

Two deterministic steps hold it honest. `scripts/plan.py` writes the scaffold the
planner starts from, and `plan.py --check` replaces a plan that dropped something
required (recorded in the row, never hidden). `scripts/verify.py` does every check that
has one answer before the verifier model sees anything, and with `--gold` it also runs
the **information-sufficiency probe**: deterministically, at no token cost, was each
known-good fact even derivable from the evidence the executors collected? A fact missing
from the evidence is a planner or executor failure; a fact in the evidence and missing
from the report is an integrator failure. They look identical in a recall score.

```bash
# every command and the first line of every role prompt; runs nothing
python3 bench/pipeline.py --config P2-claude --cases bench/private/cases_private.json \
    --case v2-buck --run 1 --dry-run

# one arm, one case, with the sufficiency probe
python3 bench/pipeline.py --config P2-claude --cases bench/private/cases_private.json \
    --case v2-buck --run 1 --gold bench/private/gold.json

# the whole family, interleaved and resumable, like every other sweep here
python3 bench/ab/run_ab.py --phase pipeline --cases bench/private/cases_private.json \
    --case-ids v2-buck,s09,c01,e01,s10 --runs 3
python3 bench/ab/run_ab.py --phase pipeline --cases bench/private/cases_private.json \
    --case-ids v2-buck,s09,c01,e01,s10 --runs 2 --budget-mode lite
```

The arms are `P1`, `P2` and `P3` on each vendor, plus the existing `B-lean` as `P0`;
`--budget-mode lite|deep` renames an arm `<config>-<mode>` and reruns it at another
depth, so depth and role split are crossed rather than confounded. The table and the
questions each arm is meant to answer are in `docs/EXPERIMENTS.md` under **"Role
pipeline (to be measured)"**, and it has no numbers in it yet on purpose.

Everything that passes between the roles is kept next to the event streams under
`raw/`: `plan-scaffold`, `plan`, one `evidence-<group>` per executor, the merged
`evidence` (and `evidence-round2` after a replan), `verify-table` and
`verify-deterministic` for each verifier pass, `verified` for each pass, and the two
files the integrator was handed. The working directory is a temp folder that does not
survive the run, so anything not copied there is gone, and the first pilot could only be
diagnosed by re-deriving the evidence out of Codex event streams.

The scorecard row is the ordinary one plus a `roles` field — per role the model, the
wall time, the tokens and the tool list it was launched with, plus what that role
produced (items, of which got, unknown, with a quote, with a source, and never tried
for) or verified (pass / fail / unknown and which rule did the failing) — a `pipeline`
block with the same summaries for the run as a whole, the artefacts kept, and
`information_sufficiency` when a gold file was given.

`bench/run.py` refuses a config with a `pipeline:` block instead of running it as one
agent: doing that would produce a row that looks like an arm and is a different
experiment.
