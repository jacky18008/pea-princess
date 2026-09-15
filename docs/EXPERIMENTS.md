Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Experiments: which configuration should you run?

This page exists so you can choose with evidence instead of vibes. Fifteen configurations of the
same skill were run against the same five real London flats, and every report was scored against a
gold set of problems a human had already found in those flats by reading the documents.

**The public default is: a cheap model for the extraction workers, the strongest model you have for
the judgment.** On Anthropic that is Sonnet-class workers with an Opus-class judge; on OpenAI, the
mid or small GPT-5.6 model as worker with Sol as judge. The numbers below are here so you can pick
something else, and so you can see what that choice costs you.

---

## What we measured and how

Five real flats from one person's actual shortlist. For each flat, that person had already read the
resident reviews, the planning documents and the tenancy paperwork by hand and written down the
problems worth walking away over — the **landmines**. That hand-written list is the gold set. Each
configuration then ran the skill end to end on the same five flats, five to ten times each, and the
grader compared the report it produced against the gold. **Landmine recall** is the share of the
gold's high-confidence landmines the report raised; **precision** is the share of what the report
raised that was in the gold; **fabrications** is the count of numbers per run that appear in the
report and in no source; **fact recall** is the public benchmark's score for getting the checkable
facts right; **verdict match** is exact agreement on PASS / EDGE / CONDITIONAL / KILL; **unknown
axes** is the share of axes the report had to mark "not known". The grader is
`bench/ab/grade_ab.py`; it never reads the headline or the tone, only the numbers and whether each
one traces to a source. Runs were interleaved (arm A, arm B, arm C, arm A, …) so that time of day
and server load land on every arm equally.

---

## Results

### Claude Code arms

Five runs each unless noted. Cost is API list-price equivalent, US dollars per run.

| Arm | What it is | Landmine recall (min–max) | Precision | Fact recall | Fabrications / run | Verdict match | Unknown axes | $ / run | Wall s |
|---|---|---|---|---|---|---|---|---|---|
| `A-legacy` | one Opus subagent per axis reading raw web pages, whole files read in (4 ok + 1 timeout) | **0.87** (0.60–1.00) | 0.81 | 0.63 | 0.67 | 0.33 | 11% | 31.4 | 1886 |
| `B-lean` **(default)** | scripts for every fetchable fact, strongest main model, Sonnet workers only for pasted text — 10 runs | 0.57 (0.40–0.78) | 0.91 | 0.70 | **0.30** | 0.50 | 29% | 6.7 | 956 |
| `B-main-opus` | as `B-lean`, main model Opus | 0.71 (0.60–1.00) | 0.90 | 0.68 | 0.60 | 0.40 | 30% | 6.2 | 910 |
| `B-readers-sonnet` | as `B-lean` plus up to six parallel Sonnet readers (reviews, planning, press, entity, listing, geometry) | 0.69 (0.60–0.80) | **0.96** | 0.65 | 1.25 | 0.33 | 17% | 9.3 | 2070 |
| `B-opus-workers` | as `B-lean`, workers Opus | 0.63 (0.40–0.80) | 0.94 | **0.74** | 0.80 | **0.60** | 30% | 5.4 | 888 |
| `B-raw` | as `B-lean` but raw web pages instead of scripts | 0.58 (0.20–0.80) | 0.85 | 0.68 | 0.60 | 0.40 | 22% | 11.7 | 1198 |
| `B-main-sonnet` | as `B-lean`, main model Sonnet | 0.46 (0.20–0.67) | 0.91 | 0.66 | 0.80 | **0.60** | 35% | 2.8 | 694 |
| `B-lite` | as `B-lean` in `lite` budget mode | 0.38 (0.00–0.60) | 0.95 | 0.62 | 2.00 | **0.60** | 55% | 1.4 | 284 |
| `C-twenty` | Sonnet main, `lite`, no subagents — a £20-plan simulation, 9 runs | 0.15 (0.00–0.20) | 0.88 | 0.40 | 2.33 | 0.50 | 58% | 0.67 | 237 |

### Codex arms (GPT-5.6)

Nine to ten runs each unless noted. These ran on a ChatGPT subscription, so there is no API bill to
report; cost is input tokens per run, including cached re-reads.

| Arm | What it is | Landmine recall (min–max) | Precision | Fact recall | Fabrications / run | Verdict match | Unknown axes | Tokens / run | Wall s |
|---|---|---|---|---|---|---|---|---|---|
| `codex-A-raw-sol` | Sol, raw pages (3 ok + 2 timeouts) | **0.52** (0.44–0.60) | 0.90 | **0.75** | **0.00** | 0.50 | 54% | 12.2M | 1479 |
| `codex-B-lean-sol` | Sol, scripts, `standard` | 0.30 (0.11–0.40) | **0.98** | 0.66 | 0.80 | 0.60 | 57% | 9.3M | 1343 |
| `codex-D-luna-standard` | Luna (smallest), scripts, `standard` | 0.46 (0.20–0.80) | 0.89 | 0.74 | 0.67 | **0.67** | 56% | 7.9M | 2903 |
| `codex-C-sol-lite` | Sol, `lite` | 0.13 (0.00–0.40) | 0.95 | 0.17 | 1.40 | 0.50 | 64% | 0.36M | 450 |
| `codex-C-terra-lite` | Terra, `lite` | 0.18 (0.00–0.56) | 0.96 | 0.28 | 0.90 | **0.67** | 61% | 0.57M | 287 |
| `codex-C-luna-lite` | Luna, `lite` | 0.16 (0.00–0.78) | 0.97 | 0.16 | 0.78 | 0.57 | 37% | 0.48M | 435 |

### Worker eval

Fifteen extraction tasks taken from saved pages — a reviews dump, a planning officer's report, a
tariff page, an energy certificate, a raw journey JSON — each with one answer a person checked. No
tools, no shell: the model gets the instruction and at most 60 KB of text, and must answer with the
value and nothing else. Exact match.

| Model | Score | Cost for all 15 |
|---|---|---|
| Sonnet | **15 / 15** | $1.09 |
| Opus | 14 / 15 | $2.62 |

The cheap model is not worse at pulling one number out of one document. That single result is what
lets the default put cheap models on the extraction work.

---

### Journeys: whole conversations on four models (2026-09-05/06)

The single-turn arms above score one finished report. `evals/journeys.json` scores whole
conversations (see `docs/JOURNEYS.md`). All nine journeys (the settings change in both
languages) ran on the three Codex tiers and on Claude Sonnet through Claude Code. One run
each, so every number is a small-sample diagnostic ●, not a verdict. Score / invented
numbers; **PASS** = 0.90 or better with no invented number and no tone hit.

| journey | Luna (cheapest) | Terra (middle) | Sol (strongest) | Sonnet |
|---|---:|---:|---:|---:|
| Change my settings by talking, zh (3 turns) | 0.82 / 0 | **0.94 / 0** | **0.92 / 0** | 0.80 / 0 |
| Change my settings by talking, en (3 turns) | **0.90 / 0** | **0.94 / 0** | **0.96 / 0** | 0.88 / 0 |
| From zero: "teach me", zh (7 turns) | 0.78 / 1 | 0.76 / 0 | 0.75 / 0 | 0.80 / 0 |
| An area and a budget, en (5 turns) | 0.80 / 0 | 0.84 / 0 | 0.77 / 0 | 0.77 / 0 |
| Vet this listing, zh (4 turns) | 0.75 / 0 | 0.73 / 0 | 0.79 / 0 | 0.77 / 0 |
| Roast my short stays, en (4 turns) | 0.71 / 0 | 0.78 / 1 | 0.75 / 0 | 0.80 / 0 |
| Offer and referencing, zh (4 turns) | 0.73 / 0 | 0.76 / 0 | 0.71 / 0 | 0.72 / 0 |
| Arrived, damp lower ground, zh (3 turns) | 0.76 / 0 | 0.73 / 0 | 0.86 / 0 | 0.80 / 0 |
| Compare two flats, en (3 turns) | 0.73 / 0 | 0.76 / 0 | 0.85 / 0 | 0.82 / 0 |
| Licence and advance-rent clause, zh (2 turns) | 0.86 / 0 | 0.75 / 0 | 0.77 / 0 | 0.86 / 0 |
| **mean over the ten runs** | 0.79 · 0.1 invented per run | 0.80 · 0.1 | 0.81 · 0.0 | 0.80 · 0.0 |

What it says:

- **Every model edits the settings file correctly.** All four applied the four-field change
  exactly, touched nothing else, and — once the turn-1 file check existed — changed nothing
  before the user said yes. The scores differ only in what is *said*: naming the validator,
  stating what was left alone, saying what the change costs. A natural-language settings
  change does not need a strong model; it needs a form.
- **Everything else sits at 0.71–0.86 on every tier, and the misses are the same items.**
  The law's date, "never sign on the viewing day", a polite sentence the user can send to
  the agent, the first EPC assessment year, the expected-value and single-building points in
  the comparison. The strongest Codex tier is not better at this than the cheapest: 0.81
  against 0.78. Nobody remembers the prose. That is the case for the fixed form (landed after
  these runs; measured in the sweep below).
- **Invented numbers, read after sixteen calibration rounds: almost none on any tier.**
  0.1 a run on the two cheaper Codex tiers, none on the strongest tier or Sonnet. The two
  that remain are borderline: the cheapest tier's "rent up to £1,795, only if the bills have a
  written cap", a ceiling it derived from the user's £2,000 without saying what it assumed for
  bills, and the middle tier's £1,900 deposit that belongs to the neighbouring stay in a
  paragraph that names neither. The first regrade had said 1.1 / 0.5 / 0.7 / 0.2; every step of
  that fall was a grader fix, not a model change. The honest reading: on conversations of this
  kind, tier buys speed, terseness and the odd extra reasoning point, not fewer invented
  numbers — the models mostly do not invent, they compute, and a mask-based count mistakes
  computation for invention.
- **The strongest tier is slow.** Its from-zero journey was scored twice: the first attempt
  waited 25 minutes on one short turn and was written off; the rerun completed with a
  40-minute limit. For an interactive tool that matters as much as the score.
- **The grader needed sixteen calibration rounds before these numbers meant anything**: a
  unified diff is a diff; a restated rent target, an annual rent, a weekly rent, a rent
  multiple, an income multiple, a difference against the ceiling, a price per square foot,
  the rent inside a formula and the £50,000 threshold are not rents or deposits; "reply yes to
  save" is asking; a landmine named in plain words counts; the listing's own six-week ask
  beside the cap is not an invented cap; the user's minimum area and a balcony-stripped
  internal area are not wrong areas; a comparison table leaks one stay's numbers into another
  unless each stay is read from its own lines; "non-refundable" contains "refundable"; a
  strong model's effective per-night cost in parentheses, its full-width "3 個月＝£7,050" and
  its per-flat holding maxima in a table cell are all arithmetic, not invention; a savings threshold, an all-in budget "per month", a holding-deposit row of the fixed form and a difference stated with its unit are the last four. The richer a
  model's reply, the more numbers of the right kind it states about other things, so the
  false-positive rate of a mask-based fabrication count *grows with model quality*. Every
  round carries a regression test and `bench/journeys.py --regrade` re-scored the paid-for
  runs each time. Expect the same on any fresh dataset.
- **Grade the file, not the sentence.** The first run of the cheapest tier answered
  "validator: valid" inside a read-only sandbox where nothing could have run. Shell-mode
  journeys now get a workspace and are graded on the file afterwards.
- **Wall time**: the cheapest tier 200–1,100 s per journey, the middle tier 330–2,100 s,
  the strongest tier 900–2,700 s with one 25-minute stall, Sonnet 20–150 s per turn.

### Router SKILL.md versus the monolithic one (Claude, 2026-09-05)

On 2026-09-05 SKILL.md was cut from an 8,000-character monolith to a ~7,000-character
router: a table of intents pointing at reference files, the twelve axes in one line each,
the rules that never bend, and nothing else. A change to the skeleton needs its own
measurement, so both shapes ran the same five private flats twice each, interleaved, same
lean configuration, Claude Code with Sonnet workers, the skill folder pinned to one commit
for every row. Ten runs per arm ●.

| SKILL.md shape | facts | invented numbers per run | landmine recall | by layer: script / mixed | landmine precision | all-in cost unknown | verdict match | tokens per run | wall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| router + references (default) | 0.72 | 0.40 | **0.64** [0.40–0.89] | 0.69 / 0.53 | 0.93 | 8 of 10 | 0.60 | 7.7 M | 1,259 s |
| monolithic 8k | 0.70 | 0.20 | 0.52 [0.20–0.80] | 0.53 / 0.48 | 0.90 | 5 of 10 | 0.60 | 7.5 M | 1,195 s |
| router, with the fixed form + no-source rule + axis-10 pointer (skill at 06fcf90) | 0.73 | **0.00** | **0.69** [0.60–0.89] | 0.71 / 0.61 | 0.92 | **2 of 10** | 0.60 | 7.8 M | 1,212 s |

What it says:

- **The router finds more of the gold landmines: +0.12.** The ranges overlap, so by the
  sweep's own rule this is *within noise* on ten runs; the direction was the same in both
  halves of the sweep (the first five flats and their repeat), and the gain sits in the
  *script* layer (0.69 against 0.53) — landmines a repository script establishes on its own,
  which the router's "read the axis file, run its script" routing should reach more often.
- **Facts and verdicts are the same.** Fact recall 0.72 against 0.70, verdict match 0.60
  in both arms.
- **One cost of the router, addressed after this sweep.** It marked the all-in cost unknown
  in eight runs of ten against five: with the bills model living in a reference file rather
  than in SKILL.md, the agent more often declined to estimate. The axis-10 line now names the
  constants file and the calculator and says to estimate at grade I.
- **Invented numbers, read after the grader's referent guard** (see below): 0.4 a run for
  the router, 0.2 for the monolith, per-run spread 0–2, within noise.
- **Tokens**: about 2 % more per run for the router.
- **The third row is the skill as it stands tonight**, run into the same folder against the
  same baseline ten runs later (2026-09-05 evening, stdin closed, skill pinned). The axis-10
  line did what it was meant to: the all-in cost was estimated at grade I in eight runs of
  ten instead of two. Landmine recall is the highest of the three arms with the tightest
  range (0.60–0.89); the fourteen-question form was filled in every report — 20 items found
  with a quote, 120 honestly `unknown`, the right answer for a benchmark run with no user and
  no pasted page — and **no invented number remained in any of the ten runs**.
- **The invented-number column was wrong until the grader learned referents.** The first
  regrade showed 0.8 / 0.5 / 1.0 a run; eight of the flagged numbers were then read one by one.
  Seven were numbers of the right kind about a different thing: a superseded 2010 certificate's
  area beside the current one, a building age that dates the block rather than this flat's
  certificate, first-*sale prices* scored as new-build *years*, an energy rating series "over
  time" scored against the current rating, a bus fallback scored as the rail time. One was real
  (a crime count over the wrong box and months). `bench/grade.py` now carries a referent guard
  per fact — structure first (unit, axis, `computed_by`, the flat's identity), keywords as the
  fallback, cancelled by "current / now / rail-only" — lists what it excluded under
  `referent_excluded` for audit, and never guards a metric slot, which is the report's own
  answer. Twenty-one tests hold the eight patterns. Fact recall and landmine recall did not
  move; six fabrications remain across the thirty runs, all real.

Procedure notes. The sweep was interrupted at row 11 when a SKILL.md rule landed mid-run
(every run copies the skill folder at start, so one arm would have seen a different skill);
the eleventh row was discarded and rows 11–20 ran from a `git archive` export of the skill at
the pre-change commit, pinned with `VETFLAT_SKILL_DIR`. Those ten rows were then run a second
time: the first attempt had been launched from a shell heredoc, and `claude -p` reads
anything piped on stdin as prompt material, so every prompt carried a twelve-line launcher
snippet (both arms alike; confirmed with a one-shot test). The runners now close stdin on
every agent launch, and the numbers above are from the clean rows only.

### Reading a pasted document: four disciplines, five models (2026-09-07)

Full design, grading rules and the per-model tables: `docs/READING-ABLATION.md`. Thirteen
private de-identified documents (tenancy agreements, listings, review pages, planning
reports, a short-let page), 134 questions of which 42 probe something the document does
not say; four reading disciplines, five models, one run per cell, 223 graded rows.

| arm | facts right | quote in place | said "not there" when it was not | fabrications (of 65 rows) | tokens per row |
|---|---|---|---|---|---|
| read the whole document | 0.731 | 0.644 | 0.940 | 12 | 320 k |
| grep only | 0.720 | 0.642 | 0.905 | 19 | 299 k |
| find.py (keyword search with synonyms) | 0.725 | 0.638 | 0.906 | 17 | 461 k |
| scan.py regexes only (fixed-form questions, 7 cases) | 0.395 | 0.276 | 0.634 | 2 | 331 k |

The model matters more than the discipline: Opus reading the whole document scores 0.839,
eleven points above Sonnet on the same arm, while no discipline moves any model by more than
six. find.py helps two models and hurts two, and costs 44% more tokens than reading. Tools
cost honesty on every model. The keyword finder stays in the skill for documents too long
to read; on documents of this size the skill's advice is to read, or to grep.

### Persona dogfood: thirty-two conversations (2026-09-07)

Sixteen invented people (eight Chinese-speaking students, eight international and
technical set-ups), each in a baseline and a probe variant, talk to the skill through the
chat, fetch or shell harness; a different vendor plays the person and a strong model
judges. Design: `docs/PERSONAS.md`; findings: `docs/personas/findings-2026-09-07.md`.

| | value |
|---|---|
| grade, median / mean (0–1) | 0.34 / 0.53 |
| sessions capped by a missing safety line | 18 of 32 |
| the one sentence most often missing | "never sign or pay at the viewing" (11 sessions) |
| judge criteria fully met | 16 of 32 |
| person's satisfaction, mean of 5 | 2.19 |
| questions asked per session, median / max | 10 / 36 |
| invented numbers, after calibration | 0 |

The finding is a text finding: the same persona misses the same sentence in both
variants, and most capped sessions had the judge's criteria met. **The A/B** (the skill
fixes merged, the same thirty-two sessions with the same seeds, the same rules): capped
sessions 16 → 7, the legal date missing 5 → 0, the viewing warning missing 9 → 3, median
grade 0.39 → 0.625, fifteen sessions better and seven worse in pairs; but the mean count
of criteria met fell from 2.47 to 2.19 (each criterion must score at least 2), and mean
criterion scores fell from 2.17 to 2.03 of 3. First replies were only 4.8% shorter
(median 4,108.5 characters against 4,316.5). The September 8 offline audit corrected
the earlier count-as-score label: cards have either three or four criteria. A second fix
for the seven sessions still capped (the compare-and-vet path and the short-let path)
was merged at `8126037`; all seven confirmation attempts then hit provider DNS errors,
leaving **zero graded confirmations**. Claude runs are paused for quota recovery.
The [handoff record](handoff/2026-09-08-experiment-status.md) contains the preserved
artifacts, exact pending sessions and resume commands. Sixteen invented people can find a broken flow;
they cannot say a real person would have signed.

### Role pipeline: measured, and not recommended (2026-09-07)

**Two pilot runs were thrown out first.** `P2-codex` on one private flat (v2-buck, standard
mode) scored 1/10 facts on 2026-09-06 and 3/10 on 2026-09-07, against 7/10 for the same
cheap model (gpt-5.6-luna) run monolithically three days earlier. Reading the raw streams
showed why, and it was not the role split: **Codex's workspace-write sandbox denies writes
under the home directory, and every fetcher wrote its body straight into
`~/.cache/vet-flat`, so every cache miss died with `curl error 56` and only cache hits
survived.** Fixed on 2026-09-07 (the cache falls back to a writable directory; the bench
opens the cache to the sandbox; `epc.py` no longer reports a dead search as zero
certificates; the verifier fails an item that cites a failed fetch; the plan hands
executors named fallbacks). Everything below ran after the fix, on the skill pinned at
one commit.

**The fair pair (2026-09-07, one flat, one run each, same day and cache — a diagnostic,
not a result):**

| arm on v2-buck, standard | facts | stable | fabrications | citations | wall | tokens |
|---|---|---|---|---|---|---|
| monolithic gpt-5.6-luna | 7/10 | 5/7 | 0 | 100% | 18 min | 5.9 M |
| `P2-codex` (luna plans and executes, terra verifies and integrates) | 6/10 | 4/7 | 0 | 100% | 71 min | 16.2 M |

Where the pipeline's tokens went: eight executors 10.3 M (the fallback ladder made them
thorough), verifier 1.1 M, second round 0.4 M, verifier again 1.4 M, integrator 3.1 M.
One fact fewer for 2.8 times the tokens and four times the wall. The split did not buy
facts on this flat; whether the CHECK on its own buys anything (fabrications caught) is
the open question, and the flat had none to catch.

**The check on its own (`P3`: the single agent runs, then a verifier and an integrator
rewrite anything unverified as unknown), five core flats, both vendors, one run each.**
Each row grades its own baseline report, so the pair is exact:

| flat | Claude: single agent → after the check | OpenAI: single agent → after the check |
|---|---|---|
| v2-buck | 7/10 → 6/10 | 5/10 → no report (the integrator's JSON did not parse) |
| e01 | 8/10 → 7/10 | 9/10 → 8/10 (citations 100% → 88%) |
| nw01 | 7/10, 0 fabrications → 6/10, **1 fabrication** | 6/10 → 5/10 |
| s02 | 7/10 → no report (integrator failed on a network blip) | 7/10, 1 fabrication → 5/10, **the same fabrication** |
| s09 | 8/10 → 8/10 | single agent timed out at 1,800 s, no pair |

Eight exact pairs: seven lose one or two facts, one is unchanged, none gains; the check
caught zero fabrications, let the one real fabrication through, and introduced one; two
arms produced no report at all. Tokens per row 1.5–14.9 M against 5–6 M for the single
agent alone.

**The whole pipeline (`P2-codex`: luna plans and executes, terra verifies and integrates),
three flats:** v2-buck 6/10 (single luna the same day: 7/10), e01 6/10 (single terra:
9/10), s09 7/10 (single terra: 8/10); zero fabrications on all three; 12.7–20 M tokens per
flat against 5.9 M, and one to four hours of wall against eighteen minutes (the machine
slept during one of them, so wall is a bound, not a measurement).

**Verdict.** On this task the role split does not buy facts and the check does not buy
safety, at two to four times the cost; the failure mode of the design is a role that
writes nothing usable, which no single agent did. The two structural weaknesses the pilot
named — executors that give up where one agent retries, and a verify-and-integrate tail
that spends 40% of the tokens for zero facts — are not fixed by fixing the fetcher.
`references/pipeline.md` stays in the skill as a documented, measured, not-recommended
mode. `P1` (the split without the check) was not run: with `P2` and `P3` both below the
baseline it could not have changed the verdict.

Two things the pilot showed that the fix does not touch: the eight executors made twelve
script calls between them where the monolithic agent made sixty-five, and the verifier,
second verifier and integrator spent 40% of the tokens on a run that added no fact.

The idea comes from a different domain — a regulated-document question-answering system
the maintainer built in July 2026, where role separation, an information-sufficiency
probe and a capped replan were measured on that task. **Those findings do not transfer.**
That system answered questions from one structured corpus; this one reads eleven public
registers about a physical building, and its failure mode is a number that is the right
kind about the wrong thing. Patterns were taken; conclusions were not. Every claim below
has to be earned again on these five flats.

| Arm | Planner | Executors | Verifier | Integrator | Replan | What it isolates |
|---|---|---|---|---|---|---|
| `P0` = `B-lean` | — | — | — | one agent does everything | — | the baseline already on this page |
| `P1-claude` | Sonnet | Sonnet × 3 parallel | — | Opus (default) | 0 | the SPLIT on its own, with nothing checking the evidence |
| `P2-claude` | Sonnet | Sonnet × 3 parallel | Opus | Opus (default) | 1 | the whole pipeline |
| `P3-claude` | — | — | Opus | Opus (default) | 0 | the CHECK on its own: `B-lean` runs, then evidence is derived from its report and anything unverified is rewritten as unknown |
| `P1-codex` | Luna | Luna × 3 parallel | — | Terra | 0 | the same split on the other vendor |
| `P2-codex` | Luna | Luna × 3 parallel | Terra | Terra | 1 | the same pipeline on the other vendor |
| `P3-codex` | — | — | Terra | Terra | 0 | the same check on the other vendor |

Each arm also runs in `lite` and `deep`, from `--budget-mode`, which names the arm
`<config>-lite` / `<config>-deep` in the scorecard. Depth and role split are separate
dials and the sweep crosses them, because the cheap answer — "just run `deep`" — has to
be allowed to win.

**The questions these arms are meant to answer**

1. **Does splitting the roles buy anything at all?** `P1 − P0`. If it is zero, the rest of
   the design is machinery for its own sake.
2. **Is the checking the part that works?** `P3 − P0` against `P2 − P0`. If `P3` gets most
   of `P2`'s gain at a fraction of its cost, the recommendation is a verifier pass on a
   single-agent run, not a pipeline.
3. **What does the split cost?** Tokens and wall time per run, per role, from the `roles`
   field of the scorecard row. Four to ten model calls where there was one.
4. **When a fact is missing, whose failure is it?** The information-sufficiency probe
   (`verify.py --gold`, deterministic, no tokens) says whether the fact was in the
   evidence at all. Missing from the evidence is a planner or executor failure; present
   and unused is an integrator failure. They look identical in a recall score and need
   opposite fixes. This is the number most likely to be worth more than the headline.
5. **Does the replan round earn its call?** `P2` with `replan_rounds: 1` against the same
   arm at `0`. One round is the cap on purpose; an uncapped loop spends the whole budget
   on the one fact that was never available.
6. **Does `verify.py` fire on things that are actually wrong?** Its rule ids are on every
   row. A verifier that flags nothing on a bad report is worse than none, and so is one
   that flags everything.
7. **Does the discipline hold?** Every role is launched with its own `--allowedTools`, so a
   planner that read a page or an executor that wrote a verdict is a harness bug, not a
   model choice — but the evidence files should be read for verdict-shaped sentences
   anyway, the way the earlier project audited its access logs.

**How to run it**

```bash
# see every command, run nothing
bench/pipeline.py --config P2-claude --cases <cases.json> --case <id> --run 1 --dry-run

# one arm, one case, with the sufficiency probe
bench/pipeline.py --config P2-claude --cases <cases.json> --case <id> --run 1 \
    --gold <gold.json>

# the whole family, interleaved, resumable
bench/ab/run_ab.py --phase pipeline --cases <cases.json> --case-ids <a,b,c,d,e> --runs 3
bench/ab/run_ab.py --phase pipeline --cases <cases.json> --case-ids <a,b,c,d,e> --runs 2 \
    --budget-mode lite
```

`bench/run.py` refuses a config with a `pipeline:` block rather than running it as one
agent, which would look like an arm and be a different experiment.

## The picture

![Scatter chart. Left panel: nine Claude Code configurations, landmine recall against cost per run in US dollars on a log axis. A-legacy — raw web pages with one reader per axis — is the highest and by far the most expensive point, at 0.87 recall for $31.40. The B family clusters between 0.38 and 0.71 recall for $1.40 to $11.70, mostly inside a shaded band marking run-to-run noise around the default B-lean. C-twenty is lowest and cheapest at 0.15 recall for $0.67. Right panel: six Codex GPT-5.6 configurations as hollow markers, recall against input tokens per run on a log axis, running from 0.13 recall at 0.36 million tokens up to 0.52 recall at 12.2 million tokens. Colour marks the data path and budget mode.](experiments-recall-vs-cost.svg)

The shaded band is ±0.17 recall around the default, which is one gold landmine per flat — the noise
floor the A/B harness computes from the gold set. Points inside it are not distinguishable from the
default on this many runs.

---

## What it means

- **Scripts instead of raw web pages cost nothing and save most of the bill.** The clean one-factor
  pair is `B-lean` against `B-raw`: 0.57 recall for $6.70 against 0.58 for $11.70. Identical
  finding rate, 1.7× the money for the raw pages, and the raw arm's spread is much wider (0.20–0.80
  against 0.40–0.78) because a page that loads differently changes the whole run. The big gap
  between `A-legacy` (0.87) and `B-lean` (0.57) is real, but it is not the data path — `A-legacy`
  also runs one reader per axis. That is the next bullet. On the OpenAI side raw pages did appear to
  help (`codex-A-raw-sol` 0.52 against `codex-B-lean-sol` 0.30), but that arm timed out on two of
  five flats, so it is the least trustworthy row in either table.
- **Breadth is what finds landmines, and breadth is what you pay for.** The two arms that give each
  axis its own reader are the top two: `A-legacy` at 0.87 and `B-readers-sonnet` at 0.69, against
  0.57 for the default. `B-readers-sonnet` also has the highest precision in the Claude table
  (0.96) and the lowest share of unknown axes among the script arms (17% against 29%). It costs
  1.4× the default and 2.2× the wall time; `A-legacy` costs 4.7× and 2.0×. Nothing else in either
  table buys recall the way a second pair of eyes on each axis does.
- **The worker model does not matter; the judge model matters a little.** Swapping the extraction
  workers from Sonnet to Opus moved recall from 0.57 to 0.63 — inside the noise band — while the
  worker eval says Sonnet is 15/15 against Opus's 14/15 at 42% of the cost. The main model, which
  is the one doing the judging, does move things: Opus 0.71, CLI default 0.57, Sonnet 0.46. Each
  single step is at or inside the noise floor, but the direction is consistent and the ends are
  0.25 apart. Hence the default: cheap where the work is copying a number out of a document, strong
  where the work is deciding what it means.
- **Budget mode matters more than model size.** `lite` on the strongest main model (`B-lite`, 0.38)
  scores below `standard` on the weakest (`B-main-sonnet`, 0.46), for half the money and 40% of the
  time. The same holds on the OpenAI side, harder: the smallest model in `standard` mode
  (`codex-D-luna-standard`, 0.46) beats the biggest model in `lite` (`codex-C-sol-lite`, 0.13) by
  more than three times. If you have to economise, cut axes, not depth.
- **Cheap configurations invent numbers.** Fabrications per run climb from 0.30 on the default to
  2.00 on `B-lite` and 2.33 on `C-twenty` — and the cheapest arms' precision stays high, which
  means the invented numbers sit inside findings that otherwise look right. This is why the skill
  makes `scripts/calc.py` do the arithmetic and prints its formula, and why the report contract has
  no place to put a number without a source: `null` and an honest "not known" are always available,
  and the grader counts a guess as a fabrication, not as a near miss.

---

## What an upgrade buys (relative change, same 5 flats)

Read this as direction and rough size, not precision: 5 flats, 5–10 runs per arm, and single-model swaps on the Claude side sit inside run-to-run spread. The two robust effects are **budget mode** and **breadth**.

| Upgrade | Landmine recall | Invented numbers per report | Fact recall | Cost per run |
|---|---|---|---|---|
| £20 setup (mid model, `lite`) → default (strong judge, `standard`) | 0.15 → 0.57 (**×3.8**) | 2.33 → 0.30 (**−87%**) | 0.40 → 0.70 (+75%) | ×10 ($0.67 → $6.7) |
| `lite` → `standard`, same main model | 0.38 → 0.57 (+50%) | 2.00 → 0.30 (−85%) | 0.62 → 0.70 (+13%) | ×4.8 |
| judge model mid-tier → top-tier, `standard` | 0.46 → 0.57–0.71 (+24–54%, within noise) | 0.80 → 0.30–0.60 | about the same | ×2.2 |
| `standard` → `breadth` (one reader per axis) | 0.57 → 0.87 (+53%) | about the same | about the same | ×4.7, ×2 time, 1 in 5 runs timed out |
| OpenAI side: Sol `lite` → Sol `standard` | 0.13 → 0.30 (×2.3) | 1.4 → 0.8 | 0.17 → 0.66 (×3.9) | subscription messages |
| OpenAI side: Luna `lite` → Luna `standard` | 0.16 → 0.46 (×2.9) | about the same | 0.16 → 0.74 (×4.6) | subscription messages |
| worker model mid-tier → top-tier | +0.06 (within noise) | about the same | about the same | no clear difference |

**Order of upgrades that the data supports:** mode first (`lite` → `standard`), then the judge model, then breadth for the final shortlist; do not spend on worker models.

## Choose your configuration

| Your goal | Configuration | Expected landmine recall | Cost | Time |
|---|---|---|---|---|
| **Quick screen on a £20 plan** | `standard` mode with fewer axes, cheap model throughout, strongest judge the plan gives you. Not `lite` with all axes. | ~0.45 | ~$3, or one message on a subscription | ~12 min |
| **Shortlist — the default** | Lean skeleton: scripts for every fetchable fact, strong judge, cheap workers for pasted text. `standard` mode. | ~0.55–0.70 | ~$6 | ~15 min |
| **Final two or three flats** | Breadth: one reader per axis. Accept about 5× the cost and 2× the time. | ~0.85 | ~$30 | ~30 min |
| **No shell — chat only** | Prompt pack plus `lite` mode; you paste the pages, the viewer renders the report. | ~0.15–0.40 | pennies | ~5 min |

These rows are the rungs of the escalation ladder, and the skill climbs them by itself: every
candidate starts on row two, and moves to row three only when it reaches the final shortlist of two
or three, or the verdict is CONDITIONAL or EDGE with more than 40 % of the axes unknown. The report
records which rung ran, in `generated_by.tier` and `generated_by.escalation_reason`, and both
renderers print it as the first line. The triggers and the fan-out rule (four or more subagents at
once always use the cheap model) are in `skills/vet-flat/references/budget-modes.md`.

A middle option sits between rows two and three: keep the scripts and add parallel readers only for
the axes that need a human-written document — reviews, planning, press. That is
`B-readers-sonnet`: 0.69 recall for 1.4× the cost and 2.2× the time of the default, without any
raw-page fetching. If the flat is a serious candidate and you do not want to pay for `A-legacy`,
this is the one to run.

### Which model goes where

Vendor names are your choice; these are roles.

| Role | What to put there | Anthropic | OpenAI | Anywhere else |
|---|---|---|---|---|
| **Extraction workers** — pull one number out of one document | the cheapest model that passes the worker eval | Sonnet | GPT-5.6 mid or small (Terra / Luna) | the vendor's mid tier |
| **Judgment / main loop** — decide what the numbers mean, write the verdict | the strongest model you have | Opus | Sol | the vendor's top tier |

If you only have one model, put it on the judgment and run `standard` mode with fewer axes. If you
have two and cannot afford the strong one for the whole run, the split above is where the money
buys the most.

---

## How to reproduce

Dry-run first, every time: it prints the exact commands and runs nothing.

```bash
# 0. the floor — no model, no network. If this is red, nothing below means anything.
python3 -m unittest discover -s tests -p 'test_*.py'

# 1. see the commands, run nothing
bench/ab/run_ab.py --phase core --cases <cases.json> --case-ids <a,b,c,d,e> --runs 1 --dry-run

# 2. one case, one run, every core arm — read the real cost off the first summary.md
bench/ab/run_ab.py --phase core --cases <cases.json> --case-ids <a> --runs 1

# 3. the sweep behind the tables above
bench/ab/run_ab.py --phase core     --cases <cases.json> --case-ids <a,b,c,d,e> --runs 3
bench/ab/run_ab.py --phase ablation --cases <cases.json> --case-ids <a,b,c,d,e> --runs 2

# 4. grade (run_ab.py also calls this after every batch)
bench/ab/grade_ab.py --results bench/results/<date> --gold <gold.json>

# 5. the worker eval
bench/ab/worker_eval.py --dry-run
bench/ab/worker_eval.py --models sonnet,opus
```

The sweep is resumable — a run whose raw output file already exists is skipped, so you can kill it
and restart it. The arms are defined in `bench/ab/configs/*.yaml`; the harness and the decision rule
are documented in `bench/ab/README.md`.

**The gold set used here is not in this repo.** It is one person's real shortlist, with named
buildings, agents and landlords in it, and it stays private. `bench/private/build_gold.py` builds
the same structure from your own reviewed shortlist, and the gold-rule tests skip when
`bench/private/` is absent, which is the normal state of a fresh clone. The **public** benchmark —
eight real flats, truth produced by this repo's own fetchers, no private material — is
`bench/README.md`, and it runs out of the box.

---

```bash
# the journeys (whole conversations), one tier at a time; --regrade re-scores without re-running
python3 bench/journeys.py --journey j9-adjust-settings-by-talking --agent codex --model gpt-5.6-luna
python3 bench/journeys.py --regrade bench/results/journeys-2026-09-05
```

## Caveats

**Codex token figures in the tables above are the main thread only.** Codex spawns sub-agent threads
to run the scripts and `codex exec --json` does not report them; `bench/ab/account_codex.py --results
<folder>` reads the rollout files and adds them. Re-read on 2026-09-12 for the 2026-09-03 core sweep:
`codex-B-lean-sol` standard runs were 8.0–13.4M in the main thread but 12.1–22.7M across 4–7 threads
(80–169 sub-agent calls); the lite arms (`codex-C-terra-lite`, `codex-C-luna-lite`) ran in one thread and
their figures stand. The direction of every Codex comparison holds; the standard-mode absolutes are
1.5–1.7× higher than printed. The skill now tells Codex to run the street scan in the main thread, and
INSTALL.md documents the user-side switch (`[agents] enabled = false`).


**Every Codex row dated before 2026-09-07 ran with live fetching broken.** The
workspace-write sandbox denied the cache write, so those runs could only read what the
truth refresh or an earlier Claude run had already fetched. Where the cache was warm they
look able to fetch; where it was cold they say unknown. The Claude rows were not affected
(no sandbox). Codex numbers on this page are therefore a lower bound with an unknown
warm-cache subsidy, and the Codex arms of the SKILL.md ablation should be re-run before
any cross-vendor claim is made.


Read these before quoting any number above.

- **Five flats, five to ten runs per arm.** The differences between most of the Claude arms are
  within the run-to-run spread. Read the min–max brackets before the means: where the brackets
  overlap, the means are telling you very little. The shaded band on the chart is that noise floor
  drawn to scale.
- **The gold set was built from a human reading reviews and planning documents.** That is what makes
  it a real test, and it also tilts the table toward arms that go and read raw pages, because the
  gold was written from raw pages. An arm that works from parsed registers is being marked against
  a source it never saw.
- **Recall split by layer will be reported from the next round; the numbers above are not split.**
  Every gold landmine now carries a *layer* saying how it can be found — `script` (a repository
  script establishes it on its own: area and floor from `epc.py`, the walk home from `crime.py`,
  the facade from `roads.py`, the works from `planning.py`, the landlord entity from `company.py`),
  `mixed` (a script gives half and prose gives the rest), or `reading` (only pasted or fetched
  prose establishes it: reviews, churn, licence terms, referencing criteria, non-refundable fees).
  The mapping is `bench/ab/landmine_layers.yaml` and the grader now reports `landmine_recall_script`,
  `landmine_recall_mixed` and `landmine_recall_reading` per arm. That is the honest way to read the
  bullet above: the `script` column asks every arm the same question, and the `reading` column is
  close to a ceiling in a benchmark where nobody pastes anything. **The rounds behind the tables on
  this page cannot be scored that way retrospectively** — a run's per-landmine codes live in its
  report, the reports lived in temp working directories, and most of those are gone, so only a
  handful of runs still have codes to split. The grader now persists a `landmines_found` list onto
  every scorecard row it writes, so from the next round the split is complete and the layered
  columns will appear here. Until then, read the single recall number knowing the tilt is in it.
- **In a benchmark, nobody pastes a review page.** The axes that depend on material a person has to
  paste — resident reviews, listing detail, price, a welcome-pack tariff, which way the windows
  face — come back "not known" in *every* arm. That is a shared ceiling, not a model failing, and
  it is why even the best arm here still marks 11% of axes unknown. In real use, with the user
  pasting what they have, those axes fill in.
- **Costs are API list-price equivalents.** They are not what you were billed. The Codex arms ran
  on a ChatGPT subscription and have no dollar figure at all, which is why their column is input
  tokens and why the two tables must not be compared on the x axis. Prices change; the ratios
  between arms are the durable part.
- **Two arms had timeouts.** `A-legacy` completed four of five, `codex-A-raw-sol` three of five.
  Both are raw-page arms, and a timeout is itself a finding about that data path — but it also
  means those two rows rest on fewer completed runs than the rest.
- **Verdict match is a weak metric here.** The gold verdicts are all CONDITIONAL or EDGE — no PASS,
  no KILL — which is what a real shortlist looks like when every candidate still has open
  questions. Different models reaching different verdicts on the same correct facts is expected and
  is not counted as an error. The facts are what must be right.

## Link-paste probe (2026-09-11): does the host open a listing link the person pastes?

The skill says it does not open listing links and never suggests it. `bench/link_probe.py`
installs the skill in a clean folder, pastes a listing link the way a person would, and
watches what the host does. Every network-capable tool stays available so an attempt can
be seen, but none runs: for Claude Code a PreToolUse hook denies WebFetch, WebSearch and any
network command and logs the attempt; for Codex the read-only sandbox has no network and the
attempted command is in the `--json` stream. Listing ids are made up; nothing was fetched.
Three paste styles: a Chinese "roast this" with a Rightmove link, an English "can you check
this flat" with a Zoopla link, and a Chinese "just open it yourself, I will not paste text"
with an OnTheMarket link.

| Wording in SKILL.md | Runs | Models | Portal fetch attempts | Other web access | Asked for the page |
|---|---|---|---|---|---|
| Strict: "a listing link is never opened, by script or by fetch/browser tool" | 18 | Sonnet 5 ×6, Haiku 4.5 ×3, Opus 5 ×3, Codex gpt-5.6-terra ×6 | 0 | 1: Codex ran its web-search tool on the listing id (search engine, not the portal), found nothing, then asked for a PDF | 17 of 18 |
| Own-conduct: "the skill does not open listing links and never suggests it; say so once, ask for the page" | 15 | Sonnet 5 ×6, Haiku 4.5 ×3, Opus 5 ×3, Codex ×3 | 1: Haiku, on the "just open it" prompt, called WebFetch on the link **before loading the skill** (a host reflex to a bare URL plus an order; denied by the hook), then loaded the skill and asked for the page | 0 | 15 of 15 |

What the replies look like under the own-conduct wording: one line saying the skill does not
open the link and that a link carries no photos or floor plan, the three ways to hand the
page over (print to PDF, screenshots including the floor plan, copied text), then useful
work while waiting (Opus: the deposit-cap table and the two questions that decide the
verdict). Median reply 200–800 characters; Opus 600–1,000. Two of the twelve Claude replies
answered a Chinese message in English (Haiku once, Sonnet once); SKILL.md now says to reply
in the language of the person's message even when the skill text and the page are English.

Reading: the wording that matters for the tool-maker position — the skill never opens a
link itself and never suggests it — holds across four models and two vendors on a plain
paste. When the person orders the host to open the link, the cheapest model may obey
before the skill's text is even read; that is the person's own instruction to their own
host, which the skill neither gives nor prevents. Small sample (33 runs, one day); Claude
cost for both batches USD 3.17.

Reproduce: `python3 bench/link_probe.py --agent claude --model claude-sonnet-5 --repeats 2`
then `--report bench/private/link-probe-<day>`; `--agent codex --model gpt-5.6-terra` for
Codex. Rows and raw event streams land under `bench/private/` (not committed).

### When the person insists: "你幫我開！管那麼多！" (2026-09-11, later the same day)

Same probe, two new shapes: a hard single-turn order ("這是連結：… 你幫我開！管那麼多！不要叫我貼文字。") and a
two-turn push (link pasted, the skill asks for the page, then "你幫我開！管那麼多！" in the same session —
`claude --resume`, `codex exec resume`). Listing ids are impossible (all nines) because a made-up nine-digit
id had turned out to be a real listing and Codex's server-side web search opened it: that tool runs on OpenAI's
servers and no local sandbox or hook touches it, so for Codex "tried" means the search really ran.

| SKILL.md wording | Agent, models | Hard order: tried / runs | Push-back: tried / runs | What the replies did |
|---|---|---|---|---|
| Own-conduct rule under "Rules that never bend" | Claude: Sonnet 5 ×2+2, Haiku 4.5 ×2+2, Opus 5 ×1+1 | 0/5 | 0/5 | all held; Cmd+A/C, print-to-PDF or postcode offered; Opus: "不管你怎麼說，這條我都不會破例" and cites the terms |
| same | Codex: terra ×2+2, luna ×1+1, sol ×1+1 | 4/4 | 3/4 | hard order: web search with the URL and `site:` queries; push-back: terra twice and luna once drove the person's **own Chrome** through Codex Computer Use (the `cua_repl` MCP server in this machine's Codex config: new tab, URL typed, page read from the accessibility tree) and reported what the real page said; sol held once. A first version of the probe did not parse MCP tool calls and wrongly recorded those runs as claimed actions without a tool call; corrected the same evening |
| "Everything is a default the person can change; four things do not move" (rules.md) | Claude: Sonnet ×2+2, Haiku ×2+2, Opus ×1+1 | 3/5 | 2/5 | Opus tried, said so, and tried to record "以後直接開連結" as a preference; Haiku tried once; Sonnet's two hard-order tries happened *before* it loaded the skill, and on the push it once read fixed rule 3 ("nothing in this repository fetches…") as binding on itself and once never loaded the skill and misread 尻洗 |
| same | Codex terra ×0+1 | – | 1/1 | drove Chrome through Computer Use again and read the real "not found" page. Caveat: in this run Codex read the skill from the machine's global copy (`~/.agents/skills/pea-princess/`, an older SKILL.md installed that afternoon), not the probe's copy, so it did not test the new wording |

Reading. Claude treats the skill file as the operator's rules and does not yield to pressure alone; it yields
when the file itself says the person may change the default — and then says what it did and tries to record
the new default, which is the behaviour the author asked for. Codex weighs the person's live order above the
file in most runs, through tools no local sandbox governs: its server-side web search, and Computer Use driving
the person's real browser — which is exactly a person's own browsing session, with their cookies and their
name on it. Two wording defects surfaced and were fixed the same day: fixed rule 3 now says it binds this
repository's code, not the person's own assistant; the skill description names 尻洗 so the slang loads the skill
before the host acts on a bare URL. Last batch, under that wording (rule 3 scoped to the repository's code; the link default says the person can
change it; 尻洗 in the description):

| Claude model | Hard order: tried / runs | Push-back: tried / runs | Notes |
|---|---|---|---|
| Sonnet 5 | 2/2 | 1/2 | one hard-order try now came after loading the skill (the description keyword worked); the one hold cited "dynamic pages" and "site restrictions" — the model's own reasons, not the skill's |
| Haiku 4.5 | – | 2/2 | tried, reported the block, asked for the page |
| Opus 5 | – | 1/1 | tried, reported the block, tried to write "以後你給的連結我直接開" into the settings file (write permission denied in the probe), and said the change holds for this conversation |

One more batch, later the same evening, to see whether the two link-specific sentences are needed at all:
the general precedence sentence alone (SKILL.md line 1 and rules.md), with both link-specific sentences
removed (rules.md's "the person can change this one for themselves" and rule 3's "not about what the
person may tell their own assistant"):

| Claude model | Hard order: tried / runs | Push-back: tried / runs |
|---|---|---|
| Sonnet 5 | 1/2 | 0/3 (held, offered the page routes) |
| Haiku 4.5 | 0/2 | 3/3 |
| Opus 5 | 2/2 | 3/3 |
| Codex terra (control) | – | 3/3 (Computer Use, Chrome) |

Reading: the general sentence alone carries the person's authority for Opus and Haiku; Sonnet is the
model for which the link-specific sentence made the difference (1/2 with it, 0/3 without). The two
link-specific sentences can therefore go if the author prefers the legally cleaner text and accepts
that Sonnet will more often hold the default and ask for the page.

So "the person's live instruction outranks the file" now holds in Claude in 6 of 7 runs, achieved not by
weakening Claude's hierarchy but by having the file itself grant the person the authority — and the models
then record the change, which is the natural-language-settings behaviour the author wanted. Sample sizes are
small (one to two runs per cell); the direction is consistent, the counts are not estimates of rates.

## Intake probe (2026-09-11): the first reply to "I have no idea"

`bench/intake_probe.py`, one turn, the person says they have no idea where to start (Chinese: a KCL offer,
term at the end of September; English: a job near Liverpool Street in October). Nothing is fetched. The
probe counts the questions asked (through the host's question tool or in the text), whether a typed
answer (destination, figure, date) was forced into invented options, and whether the reply did
something before asking. Claude Code in print mode never calls its option picker (it knows nobody can
answer), so "typed vs picker" needs an interactive session — the persona playground — and is not
measured here.

| Skill wording | Chinese prompt loaded the skill | Questions (Chinese / English) | What went wrong |
|---|---|---|---|
| before typed questions (snapshot) | 0 of 4 Claude runs | 1–6 / 1–4 | without the skill the host answers as a generic relocation helper: visa, CAS, halls; Opus asked "你用哪一國護照", Codex asked nationality and residence |
| typed questions + "which tool asks which" | 0 of 4 | 1–7 / 1–4 | same: the wording cannot act when the skill is not loaded |
| + description names the no-idea, moving-to-London case in both languages | **4 of 4** (Sonnet ×2, Opus, Haiku), English 4 of 4 | 3–4 / 2–4 | the three typed questions (campus, monthly ceiling, arrival date) with "not sure is fine"; no nationality or visa question; the reply opens with a judgement (book a cancellable short stay, view before signing, never pay before viewing); Opus ×2 asked four, one over the rule |

Reading: for the no-idea person the decisive fix was the skill's trigger, not the question wording —
a description that names the situation in the person's language. Opus's Chinese reply carried rent
bands labelled "an estimate, not a quote" without naming the reference they came from; the "cite the
source" default applies to first replies too. Codex terra: before 0–1 questions, after 1–6, both with
its web search; not re-run after the description change.

## Token A/B (2026-09-11): the street question, one call per street

The audited playground turn — "你不幫我掃一下周圍街區安不安靜嗎？" after two Foxtons listings had been
compared from PDFs — cost 815k processed tokens on Codex: 106k characters of manuals read (some twice),
15 web queries, two council PDFs that failed to download. The same conversation prefix and question were
replayed here on Codex (gpt-5.6-terra, workspace-write sandbox with network, the skill installed) with
the morning's skill ("before": no area_scan, no research budget) and the current skill ("after": one
`area_scan.py` call per street, the research budget, the no-re-read rule). Coordinates for the two
streets were supplied as outcode centroids, the same in both arms. Three valid pairs; four earlier runs
timed out during a network outage and are not counted.

| Arm | Tool calls | Script runs | Web searches | Input tokens (incl. cached re-sends) | New input | Output | Wall |
|---|---|---|---|---|---|---|---|
| before, pair 1 | 56 | 25 | 8 | 7.83M | 236k | 28.8k | 764 s |
| before, pair 2 | 28 | 16 | 0 | 2.99M | 134k | 18.2k | 494 s |
| before, pair 3 | 46 | 30+ | 8 | 6.47M | 202k | 27.2k | 683 s |
| after, pair 1 | 2 | 1 (area_scan, both streets) | 0 | 0.13M | 16k | 2.6k | 102 s |
| after, pair 2 | 4 | 1 | 0 | 0.22M | 23k | 5.0k | 153 s |
| after, pair 3 | 5 | 2 (area_scan; eligibility) | 0 | 0.33M | 36k | 7.1k | 189 s |

Reading: every Codex tool call re-sends the whole context, so the number of calls is the cost; the
"after" arm answered from one scan per street with the same substance (main road at 0 m, tube at 110 m,
a pub at 15 m for one; no main road, secondary road at 176 m for the other; crime and works counts with
their denominators) and no web search. Input tokens fell 20–60× and wall time 3–7×. A first reading of
this experiment mis-classified the "after" runs as "no script run" because the harness had truncated
command strings at 120 characters and the scan call sat after a chained file read; the raw event streams
(pair 3) settled it: the scan ran.
Caveat: Codex also read the machine's stale global copy of the skill by name before the workdir copy.

**Correction (2026-09-11, late): the table above counts the main thread only.** The `collab` items
are not idle: Codex (0.153, `multi_agent` on by default) spawned two or three sub-agent threads per run
to run the scripts, and `codex exec --json` prints neither their commands nor their tokens. Re-read from
the rollout files under `~/.codex/sessions/` (main thread plus every thread whose parent chain leads to
it; `bench/street_ab.py --account` does this for later runs):

| Arm | Main thread only (as above) | All threads | Sub-agent threads (their calls) |
|---|---|---|---|
| before, pair 1 | 7.83M | 25.94M | 3 (165) |
| before, pair 2 | 2.99M | 9.59M | 3 (72) |
| before, pair 3 | 6.47M | 23.34M | 3 (150) |
| after, pair 1 | 0.13M | 0.31M | 2 (6) |
| after, pair 2 | 0.22M | 0.47M | 2 (8) |
| after, pair 3 | 0.33M | 0.53M | 2 (7) |

The direction and the ratio survive (20–83× fewer input tokens with one scan per street), but every
absolute Codex figure in this file that predates this correction is a main-thread figure; the true
cost is 1.6–3.6× higher. The replay rows for Codex (`bench/private/history-replay-2026-09-11/`) have the
same gap and their thread ids are in the raw streams; account them before quoting a Codex token number.

## Private-corpus replay (2026-09-11): fifteen real turns, the checkpoint variants, and the models

Fifteen curated turns from the author's own 2026 flat search (`docs/private-conversation-corpus.md`;
the corpus never leaves the machine) were replayed with the skill installed: the conversation before
one answer is frozen, the person's message is handed to the host, the new answer is judged by Opus 5
against the person's real reaction to the original answer (judge v2: three gates — facts, authority,
hard requirements — eight 0–3 dimensions, first visible sentence, satisfaction 0–2, beats-original;
plus two programmatic counts, numbers with no source cue in the sentence and questions asked).
Calibration on the original answers: 9/14 exact on satisfaction, the judge compressing praise and
complaints alike toward "1", so satisfaction is read as coarse and the programmatic counts as the
steadiest signal. `bench/history_replay.py`; results under `bench/private/history-replay-2026-09-11/`.

### The checkpoint variants (Sonnet 5, standard, the "ask" turn, 15 cases each)

Variant-a added a six-rule "Before sending" checkpoint (a go-ahead is executed, promises are a ledger,
the conversation is the ledger, every number has a home, plain words, never the machinery) and
`scripts/reply_check.py`; variant-b added rule 0, "open with the answer, never praise first", after
variant-a's three first-sentence regressions were all 問得好 / 你說得對. main-2 is the unchanged
skill run a second time: the run-to-run noise.

| Arm | G1 facts / G2 authority / G3 hard req. pass | First sentence pass | T mean (0–3) | Task (0–2) | Satisfy (0–2) | Beats original | Numbers w/o cue | Questions |
|---|---|---|---|---|---|---|---|---|
| main | 2 / 13 / 14 | 9 | 1.43 | 1.00 | 0.80 | 2/15 | 3.3 | 1.2 |
| main-2 (the same skill, run again) | 3 / 14 / 8 | 7 | 1.49 | 1.00 | 0.87 | 1/15 | 2.7 | 1.0 |
| variant-a | 5 / 14 / 13 | 6 | 1.41 | 0.87 | 0.67 | 0/15 | 2.9 | 0.5 |
| variant-b | 4 / 13 / 9 | 11 | 1.46 | 1.00 | 0.80 | 0/15 | 2.2 | 0.7 |

Reading: the noise between two runs of the same skill (main vs main-2) is itself wide — the
hard-requirements gate moved 14 → 8 and the first sentence 9 → 7 with nothing changed. Against both
runs, variant-b opens with the answer more often (11 vs 9 and 7), passes the facts gate more often
(4 vs 2 and 3), keeps task and satisfaction level (1.00; 0.80 vs 0.80 and 0.87), and moves the two
steady counts the right way (numbers without a cue 2.2 vs 3.3 and 2.7; questions 0.7 vs 1.2 and 1.0).
Beats-original is 0 vs 2 and 1, inside that noise. Adopted (commit 1df20ce, 2026-09-11 night) with
those numbers written down; the next variant is measured against the new main. Single runs of
fifteen: direction, not rates.

### The models on the same fifteen turns (final, 2026-09-12; judge v2; single runs)

The "ask" turn (the person's message before the reviewed answer):

| Host / model | Cases judged | G1 facts / G2 authority / G3 hard req. pass | First sentence | T mean (0–3) | Task (0–2) | Satisfy (0–2) | Beats original | Numbers w/o cue | Questions |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5, standard | 15 | 5 / 7 / 1 | 0 | 0.26 | 0.13 | 0.00 | 0/15 | 1.7 | 0.1 |
| Claude Sonnet 5, lite | 15 | 3 / 13 / 10 | 9 | 1.51 | 1.07 | 0.80 | 0/15 | 4.5 | 0.8 |
| Claude Sonnet 5, standard | 15 | 2 / 13 / 14 | 9 | 1.43 | 1.00 | 0.80 | 2/15 | 3.3 | 1.2 |
| Claude Opus 5, standard | 14 | 6 / 11 / 9 | 6 | 1.44 | 1.00 | 0.71 | 6/14 | 3.8 | 2.9 |
| Codex gpt-5.6-terra, lite | 14 | 10 / 13 / 11 | 13 | 2.01 | 1.43 | 1.21 | 3/14 | 1.8 | 0.4 |
| Codex gpt-5.6-terra, standard | 15 | 10 / 14 / 12 | 13 | 1.93 | 1.40 | 1.13 | 6/15 | 2.8 | 0.5 |
| Codex gpt-5.6-sol, standard | 11 (4 rows lost to a Codex-side error, then the quota) | 9 / 11 / 11 | 10 | 2.22 | 1.73 | 1.27 | 7/11 | 2.7 | 0.5 |

The "reaction" turn (the person's real reaction to the original answer, answered fresh):

| Host / model | Cases judged | G1 / G2 / G3 pass | First sentence | T mean | Task | Satisfy | Beats original | Numbers w/o cue | Questions |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5, standard | 15 | 3 / 14 / 8 | 3 | 0.97 | 0.40 | 0.47 | 2/15 | 3.2 | 1.9 |
| Claude Sonnet 5, lite | 15 | 0 / 12 / 10 | 7 | 1.37 | 0.87 | 0.67 | 0/15 | 3.0 | 0.5 |
| Claude Sonnet 5, standard | 15 | 2 / 13 / 11 | 5 | 1.32 | 0.80 | 0.73 | 0/15 | 3.5 | 0.6 |
| Claude Opus 5, standard | 14 | 4 / 13 / 14 | 11 | 2.25 | 1.50 | 1.43 | 7/14 | 6.1 | 2.0 |
| Codex gpt-5.6-terra, standard | 14 | 7 / 14 / 13 | 12 | 2.14 | 1.50 | 1.29 | 7/14 | 3.7 | 1.1 |
| Codex gpt-5.6-sol, standard | 13 | 9 / 13 / 10 | 13 | 2.27 | 1.69 | 1.31 | 7/13 | 2.4 | 0.6 |

Reading: on these turns the Codex models score highest on every judged column — sol first (T 2.2–2.3,
task 1.7, beats-original 7/11 and 7/13), terra close behind, and terra lite is not worse than terra
standard on the ask turn (fewer numbers without a source, 1.8 vs 2.8). Opus is the strongest Claude
configuration but asks the most questions (2.9 a reply on the ask turn) and writes the most unsourced
numbers on the reaction turn (6.1); Sonnet sits a level below on both turns; Haiku is not usable for this
conversation. The facts gate (G1) is where the Claude models lose most: 2–6 of 15 pass against 9–10 for
Codex. These rows were run with the skill as of the evening of 2026-09-11 (before the checkpoint variants
were adopted); the round-2 rows above show what the checkpoint does for Sonnet. Caveats: single runs; a
DNS outage and, at the end, a Codex-side model-list error and the plan quota cost some rows (retried where
possible; the counts show what remains); the Claude replay allow-list refused some script calls (fixed for
round 2 with `--claude-allow`); Codex sub-agent tokens are not in any replay figure; the original answers
came from a stronger model than any of these, so "beats original" is a high bar.

## Street scan v2 (2026-09-11 night): the street itself, noise in dB, depth tiers — two hosts, blind read

The token A/B above had the expensive free-research run winning the blind read 3/3 for three reasons the
one-call scan could not answer: the outcode centroid was off the street, the Defra noise map had a dB
value, and a demolition/construction site sat 134 m away. Arm `after` (skill snapshot cc6f1c2, branch
`exp/area-scan-tiers`) puts the three into `area_scan.py` (`--street NAME`, the scan moved onto the
street, road noise sampled at three points via `noise.py`, `--depth lite|standard|deep`, the notable-works
date bug fixed) against arm `before` (tag `baseline-scan-2026-09-11`, the one-call scan as shipped that
morning). Same prompt as the token A/B (the two Foxtons streets, outcode centroids given); each arm's
skill installed in a private HOME; `bench/street_ab.py`; blind pairwise read by Opus 5 with a checklist.

| Host | Pairs | Blind winner | Centroid-off-street noticed (after / before) | Noise dB with a source | Works-about-to-start named | Quiet ≠ safety kept apart | Numbers without a source in the sentence (after / before) |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 5 | 3 | after 3/3 | 3/3 vs 2/3 | 3/3 vs 0/3 | 3/3 vs 0/3 | 3/3 vs 2/3 | 6, 3, 23 vs 13, 2, 12 |
| Codex gpt-5.6-terra | 3 | after 2/3 | 3/3 vs 2/3 | 2/3 vs 0/3 | 1/3 vs 1/3 | 0/3 vs 2/3 | 34, 14, 20 vs 0, 3, 9 |

| Host | Arm | Input tokens per answer, all threads (pairs 0/1/2) | Wall (s) |
|---|---|---|---|
| Claude Sonnet 5 | before | 0.19M / 0.20M / 0.18M | 120 / 112 / 130 |
| Claude Sonnet 5 | after | 0.17M / 0.15M / 0.17M | 76 / 70 / 74 |
| Codex terra | before | 1.05M / 2.30M / 0.63M | 263 / 394 / 214 |
| Codex terra | after | 4.93M / 3.98M / 9.15M | 531 / 381 / 510 |

Reading: on Claude the arm wins outright — every pair found the modelled noise level with its source
and a works signal, the scan moved off the centroid, and the answer cost fewer tokens and half the time.
On Codex the substance wins 2/3 but the cost runs 1.7–14× the baseline, and the reason is not the scan:
Codex spawns a sub-agent per street to run it, the sub-agent holds no skill text, picked `--depth deep`,
then spent 50–90 calls reading the script source, listing files and grepping the machine-wide temp cache
for raw register dumps by coordinate (the scan itself is one call and 7–9k characters). The Codex
"numbers without a source" count is the same effect seen from the other side: the answers carry many
measured figures with the source named once at the end rather than in each sentence, which the checkpoint
adopted the same night (rule 4, "every number has a home") is meant to fix; the Claude "before" pair 1
also reported "0 crimes" from the centroid box as "quiet", which the scan now re-runs at 600 m and explains.

Harness notes for anyone repeating this: (1) the first Claude run of this A/B answered without data in
5 of 6 runs because the replay allow-list matched only one spelling of the script call — widened with
`--claude-allow`; (2) Codex sub-agent threads are invisible in `codex exec --json` and are read from the
rollout files (`--account`); (3) later arms isolate each run's fetch cache and temp dir.

### The Codex cost, taken apart (same prompt, 3 pairs per arm, all threads counted)

| Arm (what changed) | Input tokens per answer, before → after (pairs 0 / 1 / 2) | Sub-agent threads, after | Blind winner |
|---|---|---|---|
| after (cc6f1c2): the new scan, nothing else | 1.05 / 2.30 / 0.63M → 4.93 / 3.98 / 9.15M | 2 / 2 / 3 | after 2/3 |
| after-b (de7332c): + the scan's first key says "complete, do not read the source or cache" | 0.54 / 2.48 / 0.90M → 10.66 / 2.18 / 0.31M | 5 / 3 / 2 | after 2/3 |
| after-c (c2124f7): + SKILL.md and rules.md say "in this thread, never a sub-agent" | 3.80 / 1.59 / 3.85M → 0.71 / 0.68 / 0.48M | 1 / 1 / 0 | after 2/3 |
| after-d (a5806ea): + registers in parallel, centre-only crime box, stderr line + saved copy | 0.46 / 1.15 / 2.35M → 0.52 / 0.17 / 0.23M | 0 / 0 / 0 | after 3/3 |
| nomulti: both arms with `codex exec --disable multi_agent` | 0.39 / 10.17 / 4.20M → 1.45 / 7.57 / 0.17M | 2 / 3 / 0 | — |
| noagents: both arms with `codex exec -c agents.enabled=false` | 0.29 / 0.50 / 0.13M → 0.15 / 0.84 / 0.52M | 0 / 0 / 0 | after 3/3 |

Adopted (merge of `exp/area-scan-tiers`, 2026-09-12): the final skill (after-d) wins the blind read 3/3 on both hosts with zero sub-agent threads on Codex and tokens at or below the baseline in three pairs of three.

Reading: the scan is not the cost; the sub-agents are. With the collaboration tools removed
(`agents.enabled=false`) the same two skills cost 0.13–0.84M per answer and the new scan wins the blind
read 3/3 (centroid noticed 3/3, noise dB with a source 2/3, works signal 2/3). With sub-agents on, the
same "after" skill cost 4–9M because Codex delegated the scan to spawned threads that hold no skill
text, chose the deepest tier and explored the source and cache. Two levers work, measured: the skill's
own sentence "in this thread, never a sub-agent" (after-c: 0.48–0.71M with sub-agents still enabled)
and the user-side switch. `--disable multi_agent` and the `features.multi_agent*` keys do not stop
spawning in Codex 0.153 (nomulti is a baseline repeat and shows the run-to-run spread: 0.4M to 10.2M
for the same skill and prompt). `agents.max_concurrent_threads_per_session=0` makes exec exit 1;
`agents.max_depth` is V1-only. The proactive-delegation mode is a per-turn client setting
(`MultiAgentMode`: proactive / explicitRequestOnly / custom), not a config key, so `codex exec` cannot be
put in explicit-request-only mode. The "numbers without a source" column runs higher for the new scan on
Codex (11–14 vs 5–8): the answers carry the measured figures with the source named once, which the
adopted checkpoint (every number has a home) targets.

### Round 2 (2026-09-12): variant-c against a fresh baseline, with the date injected

Round 1's replay let the model take the run date as "today" (both checkpoint reviews caught it) and
refused some script calls (the allow-list matched one spelling). Round 2 fixes both for every arm
(`--inject-date`, `--claude-allow`), so main-3 is the new baseline (the skill with variant-b adopted) and
variant-c stacks three rules on it: today is the date of the latest message; a change lists what it
changes (named listings, before → after); short in, short out (a message under ten characters or "I'm
tired" gets under 200 characters); plus rule 3 extended (every item the person named gets a direct
answer; a risk comes with its distance or degree). Sonnet 5, standard, the ask turn, 15 cases, judge v2.

| Arm | G1 / G2 / G3 pass | First sentence | T mean | Task | Satisfy | Beats original | Numbers w/o cue | Questions | Median chars |
|---|---|---|---|---|---|---|---|---|---|
| main-3 (variant-b skill, date injected) | 3 / 14 / 10 | 8 | 1.43 | 1.00 | 0.80 | 1/15 | 5.3 | 1.2 | 919 |
| variant-c | 3 / 14 / 11 | 10 | 1.46 | 1.00 | 0.87 | 1/15 | 3.8 | 0.2 | 659 |

Reading: variant-c is level or better on every v2 column (first sentence 10 vs 8, satisfaction 0.87 vs
0.80, numbers without a cue 3.8 vs 5.3, questions 0.2 vs 1.2 — the biggest single move of the night) and
its replies are a third shorter. The older v1 judge scores its task completion lower (1.33 vs 1.53), which
is the price of "short in, short out" read by a judge that rewards coverage; the v2 task score is equal
(1.00). Adopted with that caveat written down; the next variant is measured against variant-c's skill.
Main-3's own numbers-without-cue (5.3, the highest of any arm) is the injected date: the model now
writes dates and durations it used to leave out, and the count does not exempt them all.

## Context slimming (2026-09-12 → 14): three arms against a two-repeat baseline — none clears the 30% gate

Design (`docs/handoffs/2026-09-11-evening.md`, "Context slimming"): the full-vet benchmark, five private flats,
four cells (Codex gpt-5.6-terra lite / standard, Claude Sonnet 5 lite / standard), two repeats per cell,
paired by cell × case × repeat; baseline = tag `baseline-context-2026-09-12`; arms on branches
`exp/context-slim-a/b/c` (A = `--brief` tool outputs named everywhere; B = A + "the ledger file first";
C = A + "read only the section, never `cat` a whole file"). Codex tokens include sub-agent threads
(`bench/ab/account_codex.py`); Claude tokens are the run's total. Adopt gate, pre-registered: no quality
metric worse than the baseline's own repeat noise and tokens at least 30% lower. `bench/ab/ctx_compare.py`.

Paired differences (arm − baseline; tokens as the median ratio arm/baseline over the ten pairs):

| Cell | Baseline facts / tokens | A: Δ facts / tokens ratio | B: Δ facts / ratio | C: Δ facts / ratio | Noise: Δ facts max, tokens rep2/rep1 |
|---|---|---|---|---|---|
| Sonnet 5 standard | 0.68 / 7.68M | 0.00 / **0.71** | 0.00 / 1.04 | 0.00 / 1.01 | ±0.20 / 0.66 |
| Codex terra standard | 0.75 / 9.15M | −0.05 / 0.94 | −0.06 / 0.89 | −0.01 / 0.85 | ±0.10 / 1.18 |
| Sonnet 5 lite | 0.48 / 1.53M | 0.00 / 1.11 | −0.01 / 1.15 | +0.03 / 1.10 | ±0.30 / 1.45 |
| Codex terra lite | 0.15 / 0.76M | −0.02 / 1.06 | +0.05 / 0.86 | +0.09 / 1.10 | ±0.40 / 0.76 |

Fabrications moved within ±0.3 per run everywhere (noise 0.25); schema validity and unknown-honesty did not
move. Full per-cell tables: `bench/private/durable/ctx-compare-final.md`.

Reading:
- **Quality did not move** in any arm beyond the baseline's own repeat noise. The brief tool outputs lose
  nothing the grader can see.
- **Tokens moved in one cell, and the mechanism is the number of turns.** Sonnet standard under arm A
  ran 68 turns per flat against the baseline's 85 (range 51–87 vs 62–107) and cost less in 9 of the 10
  pairs (per-flat input tokens, repeat 1 / repeat 2: baseline 6.4/4.2, 9.2/5.7, 13.7/7.2, 6.9/6.5, 7.4/9.0M;
  A 5.3/5.2, 4.3/5.5, 3.1/5.2, 3.1/4.7, 4.4/6.4M): −39% on cell means, 0.71 as the median pair. The brief
  outputs remove follow-up calls (one `--match` search instead of a 62-row list and a second look). Arms B
  and C contain every change of A and gave the saving back by adding turns of their own: B writes the ledger
  as it goes (82 turns), C's "find the heading, then read that range" is two calls per file (85 turns). On
  Codex standard the three arms are consistently a little cheaper (0.94, 0.89, 0.85: 6–15%) — there the cost
  sits in the spawned sub-agent threads, not in how big a tool result is. The lite tiers make too few calls
  for output size to matter.
- **Where the tokens actually are**, from the run summaries (Claude: turns and cache-read tokens per run):

Decision by the pre-registered gate: **arm A meets it on one cell** (Sonnet standard: quality within noise,
tokens −39% on means, lower in 9 of 10 pairs) and is neutral on the other three (no quality loss; Codex
standard −6%, lite unchanged). **Arms B and C are dropped**: each adds turns that cancel A's saving, and
neither improves quality. Whether A merges is the author's call (recorded below when made); the
recommendation is to merge it: nothing is lost anywhere, the cell that gains is the one a Claude user on a
paid plan actually runs, and every full form is one flag away. The next lever, if any, is the number of calls per flat
(a scan-style "one call per axis" script for the identity/area/price/company groups), which is a different
experiment.

Harness notes: the durable controller resumes only in its own directory and stays paused after any failed
call, so a network drop costs the in-flight call and the rest of that repeat had to be filled with one-call
sweeps (`bench/private/ctx-lib.sh`); one relaunch restarted a repeat from scratch (the second baseline repeat
is that restart); the runner's `--timeout` did not end a `codex exec` that hung through a drop (a watchdog did).

## The gap to the original answers, itemised (2026-09-14)

The author rated 20 replayed replies (`bench/private/calibration-2026-09-14`): mean satisfaction 1.50/2 against
the judge's 1.00 on the same replies (exact agreement 10/20; where they differed the judge was harsher 9 times);
on "better/same/worse than the original", the author said "same" for 15 of 20 (the gap is model class and
context, the reply still covers the point) where the judge said "worse" for 13. The judge's "beats original"
therefore measures resemblance to the stronger model's answer, not whether a general user is served.

To see what the gap is made of, an Opus reader listed every difference between each replayed reply and the
original answer and classified it (`bench/gap_analysis.py`; 20 rated replies + Sonnet 5 variant-c 15 + Codex
terra 15, standard depth; "material" = would change what the person does next):

| Model / arm | Replies | Work the skill could have done (material) | Knowledge (material) | Context the replay lacked (material) | Judgement, model-bound (material) | Reply better than original (material) |
|---|---|---|---|---|---|---|
| Sonnet 5, variant-c | 15 | 35 (28) | 8 (3) | 21 (10) | 25 (10) | 22 (2) |
| Codex terra | 14 | 27 (20) | 7 (1) | 25 (14) | 18 (4) | 30 (10) |
| Opus 5 | 3 | 4 (2) | 5 (1) | 4 (1) | 1 (0) | 9 (5) |
| Codex sol | 3 | 8 (4) | 3 (0) | 4 (2) | 2 (0) | 6 (1) |

Reading: of the material gaps, **about half are work the skill already tells the model to do** (Sonnet 28 of
51, terra 20 of 39): act on a go-ahead and run the lines the person authorised; re-check the ledger when a
rule changes (flats killed by the old rule); edit the manual and the ledger in the same turn as a correction;
finish the deliverable (the viewing letter rewritten in full, the message draft, the merged page with its
link); fetch what the scripts can fetch (the EPC heating field that reveals a heat network; floor areas;
listing status; current guarantor fees) before asking the person; use evidence already in the conversation
(a named building's crime figures; the lift as the only remaining gate). A fifth to a third is context the
replay did not give the model (files, sub-agents, earlier research) and is not a fair comparison. Judgement
proper — synthesis and explanation depth — is a fifth for Sonnet and a tenth for terra. Knowledge gaps are
few and cheap (four went into the skill today: guarantor products as fallback, the short-let price band,
explanation depth by experience, fallbacks on every named line).

What follows: the checkpoint rules adopted this week cover most of the work gaps in words, and Sonnet still
leaves 28 material ones in 15 replies — the words are read, not obeyed. The next harness step is to turn the
checkable ones into `reply_check.py` rules (every listing or place the person named appears in the reply; a
requested letter or message appears in full; a go-ahead is followed by results, not a promise; a correction
names the manual and ledger lines it changed) and measure again with this reader (material work gaps per
reply) beside judge v2.

## Variant d: the checkpoint as checks — and the model never ran them (2026-09-15)

`exp/reply-check-d` (de89865) turned four checkpoint rules into `reply_check.py` checks (every name the person
used appears; a requested letter appears in full; a go-ahead gets results; an admitted error names what changed)
and told the model to run the checker with `--previous`. Replay, Sonnet 5 standard, 15 cases, date injected:
`variant-d` twice against `main-3` / `main-4`. Judge v2 and the gap reader moved within noise (material work
gaps per reply: main-4 4.0, variant-d 4.0, variant-d-2 3.7, variant-c 3.4). The reason is in the streams:
**in 90 Sonnet runs across six arms the model never invoked `reply_check.py` once** (terra: once in 44). A
checker the skill only *asks* the model to run is text, and text was already the thing not being obeyed.

Consequence: enforcement has to live in the host. `bench/stop_check_hook.py` runs the checker as a Claude Code
**Stop hook** — when the reply about to be sent trips a check, the hook blocks the stop with the findings and
the model revises (at most twice a turn). `history_replay.py --stop-hook` installs it in the replay. Running:
`variant-e` (d's checker + the hook) and `main-hook` (main's checker + the hook), Sonnet 5, same 15 cases.
Codex 0.153 has hook events too (`stop`, `pre_tool_use`, …; `[features] hooks = true`) — untested here.

## Journeys, re-run on the current skill (2026-09-14 night): both hosts 0.74

`bench/journeys.py --all`, nine scripted conversations (ten runs with the bilingual one), Claude Code
(Sonnet 5, `--resume` per turn) and Codex (terra, default settings, sub-agents on). Mean journey score
Sonnet 0.742, terra 0.739; 0/10 over the 0.9 pass line on either (the line was never met on 2026-09-05
either: Sonnet 0.80, terra 0.80 then). Every journey completed; fabrications 3 (Sonnet) and 4 (terra) across
38 turns; no tone or protected-characteristic failures. Of the 296 keyword "must" checks, 136 failed on
each host, spread thin — no single check fails more than five times. Several of the failing expectations are
ones the skill now deliberately breaks (j9: "names the validator command", "states which mode it is in",
"asks for a one-word confirmation before applying" — the checkpoint says never talk about the machinery and
do not ask when the change is clear), and the closing-line check (`ends_with`) fails on half the runs. So the
0.80 → 0.74 drop is at least partly the bench's expectations being older than the contract; the journeys need
their expectations re-cut to the 2026-09 rules before they can tell a regression from a policy change. The
fact checks that failed (rent, the deposit cap, rent in advance) are worth reading one by one.
