Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The A/B harness: does a lean harness cost quality?

The public benchmark (`bench/README.md`) asks whether a model gets the facts right.
This one asks a different question: **if you change how the agent works — scripts
instead of raw pages, a small model for the reading, a big model only for the
judgment — does the answer get worse?**

Facts are cheap to grade and they are already graded. What the lean settings could
quietly destroy is the part nobody grades: the landmines the report finds, the verdict
it reaches, and the questions it tells you to ask. So the A/B grades those, against a
private gold set built from one person's real, human-reviewed London shortlist.

---

## The arms

| config | phase | agent | main model | budget | what it isolates |
|---|---|---|---|---|---|
| `A-legacy` | core | claude | CLI default | standard | the baseline: Opus subagents per axis, raw web pages, whole files read in |
| `B-lean` | core | claude | CLI default | standard | the candidate: scripts only, Sonnet workers, no file over 40 KB, one big output |
| `C-twenty` | core | claude | `sonnet` | lite | the cheapest realistic setup, no subagents, no web tools |
| `codex-B-lean-sol` | core | codex | `gpt-5.6-sol` | standard | the lean arm on the OpenAI side |
| `codex-C-terra-lite` | core | codex | `gpt-5.6-terra` | lite | cheap setup, OpenAI side |
| `codex-C-luna-lite` | core | codex | `gpt-5.6-luna` | lite | cheap setup, smallest model |
| `B-raw` | ablation | claude | `fable` | standard | **data path**: raw pages instead of the scripts |
| `B-opus-workers` | ablation | claude | CLI default | standard | **worker model**: Opus instead of Sonnet on the subagents |
| `B-lite` | ablation | claude | CLI default | lite | **budget mode**, main model held at the default |
| `B-main-opus` | ablation | claude | `opus` | standard | **main model** pinned to Opus |
| `B-main-sonnet` | ablation | claude | `sonnet` | standard | **main model** pinned to Sonnet |
| `codex-A-raw-sol` | ablation | codex | `gpt-5.6-sol` | standard | **data path** on the OpenAI side |
| `codex-C-sol-lite` | ablation | codex | `gpt-5.6-sol` | lite | **budget mode** on the default Codex model |
| `codex-D-luna-standard` | ablation | codex | `gpt-5.6-luna` | standard | **budget mode** on the smallest Codex model |

`A-legacy` and `B-lean` both leave `main_model` null, so both run on whatever the CLI
default is. That is deliberate: the two core arms differ in *how they work*, not in
which model they are. `B-main-opus` and `B-main-sonnet` are what pin the model down.

`C-twenty` never votes on adoption. It answers one question — do the basic functions
survive on the cheapest setup — and has its own pass line.

Claude Code model aliases (`claude --help`): `opus`, `sonnet`, `fable` name the latest
model in each family; a full name such as `claude-fable-5` also works. Codex model ids
were read off the installed CLI (codex 0.151): `gpt-5.6-sol` (the default in
`~/.codex/config.toml`), `gpt-5.6-terra`, `gpt-5.6-luna`.

Nothing anywhere passes a permission-bypass flag. The Claude side is scoped by
`--allowedTools`; the Codex side by `-s workspace-write` with the documented
`sandbox_workspace_write.network_access=true`. A test asserts it
(`test_no_config_asks_for_a_permission_bypass`).

---

## The protocol

1. **Build the gold** (private, once):

   ```
   bench/private/build_gold.py
   ```

   Writes `gold.json`, `cases_private.json`, `gold_rules.md` and `profile.yaml` into
   `bench/private/`, which is gitignored. The rules are in `gold_rules.md` and are
   generated from the same table the builder uses, so they cannot drift.

2. **Run the sweep**:

   ```
   bench/ab/run_ab.py --phase core \
       --cases bench/private/cases_private.json \
       --case-ids v2-buck,s09,e01,s02,nw03 --runs 3
   ```

   The loop is **run → case → config**, so the arms interleave: A, B, C, A, B, C …
   Time of day, a register that updates at noon, a model that gets busier at 5 pm —
   all of it lands on every arm equally. No arm ever runs twice in a row.

   It is **resumable**: a run is identified by its raw output file,
   `bench/results/<date>/raw/<config>-<case>-<run>.json`. If that file exists the run
   is skipped. Kill the sweep and restart it and it picks up where it stopped.
   `--no-resume` runs everything again.

   `--dry-run` prints the exact command list and stops. `--parallel N` launches N runs
   at a time, taken in order off the interleaved list, and waits for all of them before
   starting the next batch. At `--parallel 2` that means A and B go out together on the
   same case, which is the tightest possible pairing. Above about 3 you start giving
   back the time-of-day control you interleaved for, and you are also rate-limiting
   yourself, so keep it small.

   The smallest thing worth looking at first — two cases, three configs, one run:

   ```
   bench/ab/run_ab.py --configs A-legacy,B-lean,C-twenty \
       --cases bench/private/cases_private.json \
       --case-ids v2-buck,s09 --runs 1 --agent claude --dry-run
   ```

   which prints six commands in this order, and nothing else happens:

   ```
     1. r1  A-legacy   v2-buck  claude
     2. r1  B-lean     v2-buck  claude
     3. r1  C-twenty   v2-buck  claude
     4. r1  A-legacy   s09      claude
     5. r1  B-lean     s09      claude
     6. r1  C-twenty   s09      claude
   ```

   Each line is followed by the full `bench/run.py --agent claude --config … --cases …
   --case … --run-index …` command it would run. Drop `--dry-run` to run them.

3. **Grade**:

   ```
   bench/ab/grade_ab.py --results bench/results/<date> --gold bench/private/gold.json
   ```

   `run_ab.py` calls it after every batch, so you can watch the tables fill in. It
   writes `summary.md` and `summary.json` next to the scorecard.

4. **Worker eval**, separately, when the A/B says the worker model matters:

   ```
   bench/ab/worker_eval.py --dry-run
   bench/ab/worker_eval.py --models sonnet,opus
   ```

   Fifteen extraction tasks, three of each kind — a saved reviews dump, a planning
   officer's committee report, a tariff page, an energy certificate, a raw TfL journey
   JSON — each with one answer a person checked. No tools, no shell: the model gets the
   instruction and at most 60 KB of UTF-8 from the file, and must answer with the value
   and nothing else. A task on a file bigger than that names `window_start_bytes`;
   every task is answerable from its own window alone.

   This is the one measurement the eleven-axis A/B cannot make cleanly. If Sonnet is
   worse at pulling one number out of one document, the whole lean arm is worse, and the
   A/B would only show it as noise spread thin. Here it shows up as a count.

---

## What is measured

Per run, on top of the public fact scores from `bench/grade.py`:

| metric | what it means | good is |
|---|---|---|
| `landmine_recall` | of the gold's **high-confidence** codes, the share the report raised | high |
| `landmine_recall_low_confidence` | the same for low-confidence gold codes, reported separately and **never** counted in the decision | context only |
| `landmine_precision` | of the codes the report raised, the share in the gold (high or low) | high |
| `verdict_agreement` | exact PASS/EDGE/CONDITIONAL/KILL match | high |
| `verdict_agreement_kill_split` | the 2-level match, KILL vs not-KILL | high |
| `killer_question_overlap` | share of the report's questions sharing ≥50% of their content words with a gold question | high |
| `killer_questions_from_bank` | the public check, carried through | high |
| `unknown_share` | share of the twelve axes graded `U` | low, but honest beats confident |
| `total_tokens`, `total_cost_usd`, `wall_time_s` | the bill | low |

`total_tokens` is input + output + cache-read + cache-creation, summed across the main
loop and every subagent (Claude Code reports the split in `usage` and `modelUsage`, and
both are kept in the scorecard row). It is not the API bill — `total_cost_usd` is that,
and it is reported next to it — it is "how much text did this arm have to move", which
is the thing the lean settings are supposed to change.

Two honest limits, so nobody over-reads the tables:

* **The gold verdicts are 10 CONDITIONAL and 10 EDGE — no PASS, no KILL.** That is
  what a real shortlist looks like when every candidate still has open questions. So
  `verdict_agreement_kill_split` is satisfied by any arm that never says KILL, and it
  is a floor check, not a discriminator. The exact-match number is the one to read.
* **Question overlap does not cross languages.** The gold questions are bilingual: the
  reviewer's own are Chinese, the letters actually sent are English. Every candidate
  carries English letter questions, so an English report has English gold to match
  against; a Chinese report matches the Chinese gold through CJK bigrams. A Chinese
  gold question will never match an English report question, and should not.

---

## The decision rule

Printed at the end of `summary.md`, for B against A:

```
ADOPT B    if  fact recall B  >= fact recall A - 0.02
           and fabrications B <= fabrications A
           and the mean landmine recall drop <= one code per case
               (that is, <= 1 / mean gold high-confidence codes per case)
           and tokens B <= 0.5 x tokens A

UNDECIDED  if the B - A differences are smaller than the within-config
           run-to-run spread. Nothing was measured; add runs.

KEEP A     otherwise, with the failing clause named.
```

On the current gold the mean is **5.80 high-confidence codes per case**, so "one code
per case" is a recall drop of about **0.17**. That number moves when the gold moves;
the grader recomputes it and prints it in `inputs.landmine_recall_drop_allowed`.

`C-twenty` and the two cheap Codex arms are judged separately, by the
**basic-functions** line — all of it, or FAIL:

* stable fact recall ≥ 0.90
* fabrications = 0
* hard filter consistency = 1.0
* at least one killer question from the bank
* a verdict is present
* the report is schema-valid

### The factor table

Each ablation config is paired against `B-lean`, one factor at a time, and gets one
line: **effect within noise**, **helps** or **hurts**. "Within noise" means the mean
paired difference on fact recall, landmine recall and verdict agreement is no bigger
than the largest run-to-run spread either arm showed against itself on one case. That
is the whole point of running each case more than once.

---

## How to read the tables

`summary.md` has four:

1. **Per config** — mean over runs, with min–max in brackets for landmine recall and
   tokens. Read the brackets first. If they overlap between two arms, the means are
   telling you very little.
2. **Paired differences** — B minus A, *per case*, plus how many cases B was at least
   as good on. A mean difference of −0.1 made of five −0.02s is a different animal
   from one made of one −0.5, and the per-case table is where you see which.
3. **Ablation** — one factor at a time against B-lean, with the effect word.
4. **Basic functions** — the cheap arms, pass or fail, check by check.

Then the decision block, with every input it used and the noise floor it compared
against.

---

## The run plan, and what it costs

The core sweep, six configs, five cases, three runs:

| phase | configs | cases | runs | agent runs | rough tokens |
|---|---:|---:|---:|---:|---:|
| core | 6 | 5 | 3 | 90 | ~7.2 M |
| ablation | 8 | 5 | 2 | 80 | ~6.4 M |

The rough number is 90 runs × ~80 k tokens for a lean run. **Read it as a floor, not
an estimate.** The raw-page arms — `A-legacy`, `B-raw`, `codex-A-raw-sol` — pull whole
rendered pages into context, which is one to two orders of magnitude more than the JSON
a fetcher returns, so budget several times that for them. In the core sweep two of the
six arms (`A-legacy`, and any run that falls back to the web) are the expensive ones;
in the ablation set it is `B-raw` and `codex-A-raw-sol`.

A practical way to find out what it really costs before committing: run one case, one
run, all core configs, and read `total_tokens` per config off the first `summary.md`.

```
bench/ab/run_ab.py --phase core --cases bench/private/cases_private.json \
    --case-ids v2-buck --runs 1
```

Five cases is the smallest set that gives the paired tables anything to say. Twenty
are available; `--case-ids` picks any subset.

---

## Adding a gold case

The gold is generated, never hand-edited. To add a case:

1. Add the candidate to the campaign review file that `bench/private/build_gold.py`
   reads.
2. Re-run `bench/private/build_gold.py` and read the coverage table it prints.
3. If a landmine code came out wrong, fix the keyword table **in the builder**, not in
   `gold.json`: the file is regenerated and your edit would be lost. `gold_rules.md`
   is regenerated from the same table, so the documentation follows automatically.
4. If a case genuinely needs a KILL verdict, no rule produces one automatically — say
   so by hand and write why in `notes`.
5. Re-run the tests: `python3 -m unittest discover -s tests -p 'test_*.py'`.

The gold-rule tests in `tests/test_ab.py` skip when `bench/private/` is absent, which
is the normal state of a fresh clone. Everything else in that file runs on synthetic
data and is always green.

---

## Files

```
bench/ab/configs/*.yaml     the arms
bench/ab/run_ab.py          the sweep: runs x cases x configs, interleaved, resumable
bench/ab/run_codex.py       one config x case against the Codex CLI
bench/ab/grade_ab.py        the metrics, the tables, the decision
bench/ab/worker_eval.py     Sonnet vs Opus on the extraction tasks
bench/ab/CODEX_BRIEF.md     paste this into Codex to run the same thing on the OpenAI side
bench/private/              PRIVATE, gitignored: the gold, the cases, the worker tasks
bench/results/<date>/       scorecard.json, summary.md, summary.json, raw/
tests/test_ab.py            offline tests for all of the above
```
