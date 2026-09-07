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

### Reading a pasted document: the pilot (Sonnet, 2026-09-07)

Design, arms and grading rules: `docs/READING-ABLATION.md`. Thirteen private de-identified
documents (tenancy agreements, listings, review pages, planning reports, a short-let page),
134 questions of which 42 probe something the document does not say. Two arms so far, one
model, one run each — a small-sample diagnostic, not a result.

| arm | rows | facts right | quote in the right place | said "not there" when it was not | fabrications | invented quotes |
|---|---|---|---|---|---|---|
| R1 grep only | 13 | 0.713 | 0.636 | 1.000 | 0 | 0 |
| R2 find.py (keyword search with synonyms, thick view) | 13 | 0.752 | 0.616 | 0.962 | 1 | 0 |

The first grading of these rows reported 11 invented quotes and 9 fabrications; all of the
quotes and seven of the fabrications were the grader's (two-column PDF text, short quotes,
honest "the page does not say" filed under `found`, negation-blind forbidden rules), and
every fix has a test both ways. The full matrix — four arms, five models, thirteen cases,
260 rows — is running.

### Role pipeline (pilot only; the ablation is still to run)

**Two pilot runs exist, and neither counts.** `P2-codex` on one private flat (v2-buck,
standard mode) scored 1/10 facts on 2026-09-06 and 3/10 on 2026-09-07, zero fabrications,
against 7/10 for the same cheap model (gpt-5.6-luna) run monolithically on the same flat
three days earlier. Reading the raw streams showed why, and it was not the role split:
**Codex's workspace-write sandbox denies writes under the home directory, and every fetcher
wrote its body straight into `~/.cache/vet-flat`, so every cache miss died with
`curl error 56` and only cache hits survived.** The 15 facts the pipeline did find were
exactly the long-lived cache entries warmed by a truth refresh three days before; the
monolithic run had worked one day after that refresh, on a warm cache. Fixed on
2026-09-07 (the cache falls back to a writable directory; the bench opens the cache to the
sandbox; `epc.py` no longer reports a dead search as zero certificates; the verifier fails
an item that cites a failed fetch; the plan hands executors named fallbacks). A fair pair
— monolithic luna and `P2-codex`, same day, same cache — is running; until it is in, do
not quote this design as a recommendation anywhere, including in `references/pipeline.md`.

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
