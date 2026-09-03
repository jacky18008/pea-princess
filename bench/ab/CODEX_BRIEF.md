Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Brief for Codex: run the vet-flat A/B on the OpenAI side

Paste this whole file into Codex. It is self-contained: it tells you what every file
is, the exact commands, where to write results, what you must not do, and what to
report back.

---

## 0. What this is, in three sentences

`vet-flat` is a skill that vets a London rental flat across twelve axes and writes a
standardised report (`report.json`) with a verdict — PASS / EDGE / CONDITIONAL / KILL —
plus "landmines" coded L1–L12 and two killer questions. We are testing whether a
**lean** way of running it (the repository's own fetch scripts, compact JSON inputs, no
whole-file reads) reaches the same quality as a **legacy** way (raw web pages read in
full). Your job is to run the same comparison with GPT models so we can see whether the
answer is about the harness or about the model family.

---

## 1. Where everything is

Absolute paths on the owner's machine. If you are working from the tarball
`dist/ab-package-for-codex.tar.gz`, everything below is relative to where you unpacked
it, and `README-CODEX.md` at the top of the tarball repeats this section.

| path | what it is |
|---|---|
| `/Users/chenhsienhao/Documents/pea-princess` | the repository root. **`REPO` below means this.** |
| `REPO/skills/vet-flat/` | the skill itself: `SKILL.md`, `references/`, `scripts/` |
| `REPO/skills/vet-flat/SKILL.md` | the instructions the agent follows |
| `REPO/skills/vet-flat/references/report-schema.json` | the report contract. The single source of truth for the output shape, the four verdict statuses and the L1–L12 landmine codes |
| `REPO/skills/vet-flat/references/questions.md` | the question bank. Killer questions must come from here |
| `REPO/skills/vet-flat/references/budget-modes.md` | what `lite` / `standard` / `deep` each allow |
| `REPO/skills/vet-flat/scripts/*.py` | the fetchers: `epc.py`, `crime.py`, `commute.py`, `company.py`, `planning.py`, `geo.py`, `roads.py`, `redress.py`, `render.py`. Standard library only, each prints one JSON object |
| `REPO/bench/run.py` | runs one case against one agent and grades it |
| `REPO/bench/grade.py` | the public grader: facts, citations, hard filters, question bank |
| `REPO/bench/ab/configs/*.yaml` | the arms. The Codex ones are the five `codex-*.yaml` |
| `REPO/bench/ab/run_codex.py` | **the runner you should use.** It does everything in section 3 for you |
| `REPO/bench/ab/run_ab.py` | the sweep driver; `--agent codex` dispatches to `run_codex.py` |
| `REPO/bench/ab/grade_ab.py` | the A/B grader: landmine recall/precision, verdict agreement, question overlap, tokens, the decision rule |
| `REPO/bench/ab/worker_eval.py` | the extraction-task comparison |
| `REPO/bench/private/cases_private.json` | the 20 private cases, in the `evals/evals.json` shape |
| `REPO/bench/private/gold.json` | the private gold: verdict, landmine codes, killer questions per case |
| `REPO/bench/private/profile.yaml` | the profile every private case uses |
| `REPO/bench/private/worker_tasks.json` | the extraction tasks with human-checked answers |
| `REPO/evals/evals.json` | the public eight-flat suite, if you want a sanity run first |
| `REPO/tests/fixtures/` | offline fixtures the parser tests read |

**`bench/private/` is private.** It is gitignored. Do not publish it, do not paste its
contents anywhere, and **do not modify `gold.json`, `cases_private.json` or
`worker_tasks.json`.** Read them; that is all.

---

## 2. The arms you are running

Five configs, in `REPO/bench/ab/configs/`:

| config | model | budget | phase | what it isolates |
|---|---|---|---|---|
| `codex-B-lean-sol.yaml` | `gpt-5.6-sol` | standard | core | the lean baseline on the OpenAI side |
| `codex-C-terra-lite.yaml` | `gpt-5.6-terra` | lite | core | a cheap-plan user, mid model |
| `codex-C-luna-lite.yaml` | `gpt-5.6-luna` | lite | core | a cheap-plan user, smallest model |
| `codex-A-raw-sol.yaml` | `gpt-5.6-sol` | standard | ablation | **data path**: raw pages instead of the scripts |
| `codex-C-sol-lite.yaml` | `gpt-5.6-sol` | lite | ablation | **budget mode** with the model held fixed |
| `codex-D-luna-standard.yaml` | `gpt-5.6-luna` | standard | ablation | **budget mode** on the smallest model |

Those model ids were read off the installed CLI (codex 0.151) and `~/.codex/config.toml`,
where `gpt-5.6-sol` is the default. **Before you run, confirm them yourself**:

```
codex --help
codex exec --help
```

If any id is not offered by your build, list what is and use the largest and the
smallest available, and say in your report which ids you actually used. Do not guess an
id from memory.

Each config file carries:

* `main_model` — the model id
* `budget_mode` — `standard` or `lite`; written into the run's own `profile.yaml`
* `append_system_prompt` — the arm's instruction appendix
* `factor`, `phase` — what it isolates, and whether it is core or ablation

---

## 3. How one run works

`REPO/bench/ab/run_codex.py` already does all of this. Use it. This section is here so
you can check it, and so you can rebuild it if you are working somewhere else.

1. Make a temp working directory.
2. Copy the case's `profile.yaml` (`REPO/bench/private/profile.yaml`) into it, and set
   `budget_mode:` in that copy to the config's value.
3. **Copy** `REPO/skills/vet-flat` to `<workdir>/.agents/skills/vet-flat`. A copy, not
   a symlink: the `workspace-write` sandbox will not follow a link out of the workspace.
4. Write `<workdir>/AGENTS.md`. `codex exec` has no `--append-system-prompt`, and
   Codex reads `AGENTS.md` in the working root on start, so that is where the arm's
   appendix goes. The file is the config's `append_system_prompt`, then:

   > Write report.json in this directory following
   > `.agents/skills/vet-flat/references/report-schema.json`. The skill is installed at
   > `.agents/skills/vet-flat`; read its `SKILL.md` first. Write exactly one
   > `report.json` and nothing else large.

   (If your build of Codex offers a documented flag for extra instructions — check
   `codex exec --help` — you may use that instead. Say in your report which you used.)
5. Run:

```
codex exec -m <model> -C <workdir> --skip-git-repo-check \
  -s workspace-write \
  -c 'sandbox_workspace_write.network_access=true' \
  -o <workdir>/last.txt --json "<case prompt>"
```

   * `-s workspace-write` keeps the sandbox on. The network key turns the network on
     **inside** it, which every fetcher needs.
   * `--json` prints the event stream as JSONL on stdout. Keep the whole stream; the
     token counts are in it. Check `codex exec --help` for what your build's `--json`
     emits, and say so if the shape differs.
   * `-o <workdir>/last.txt` writes the final message, which is where the report lands
     if the run printed it instead of writing it.
   * **Never** `--dangerously-bypass-approvals-and-sandbox`. Not once, not "just to see".
6. Read `<workdir>/report.json`, grade it, append one row to the scorecard.

The ready-made command:

```
python3 REPO/bench/ab/run_codex.py \
    --config codex-B-lean-sol \
    --cases REPO/bench/private/cases_private.json \
    --case v2-buck --run 1 --dry-run
```

Drop `--dry-run` to run it for real.

---

## 4. The sweep

Five cases is the smallest useful set. Use these five, which spread across the gold's
verdicts and landmine mixes:

```
v2-buck, s09, e01, s02, nw03
```

Core, three runs each:

```
python3 REPO/bench/ab/run_ab.py --agent codex \
    --configs codex-B-lean-sol,codex-C-terra-lite,codex-C-luna-lite \
    --cases REPO/bench/private/cases_private.json \
    --case-ids v2-buck,s09,e01,s02,nw03 \
    --runs 3 \
    --results REPO/bench/results/ab-codex-<date>
```

Ablation, two runs each:

```
python3 REPO/bench/ab/run_ab.py --agent codex \
    --configs codex-A-raw-sol,codex-C-sol-lite,codex-D-luna-standard \
    --cases REPO/bench/private/cases_private.json \
    --case-ids v2-buck,s09,e01,s02,nw03 \
    --runs 2 \
    --results REPO/bench/results/ab-codex-<date>
```

Replace `<date>` with today's date as `YYYY-MM-DD`.

`--results` is a **root**; the runner creates a dated folder inside it. So with
`--results bench/results/ab-codex-2026-09-05` the scorecard lands at
`bench/results/ab-codex-2026-09-05/2026-09-05/scorecard.json` and the raw event streams
at `.../2026-09-05/raw/<config>-<case>-<run>.json`. That doubled date is what the
grader path in the next section points at.

The loop interleaves the configs (config A, config B, config C, config A …) so drift
lands on every arm equally. It is resumable: a run whose raw output already exists at
`<results>/<date>/raw/<config>-<case>-<run>.json` is skipped, so you can stop and
restart. Add `--dry-run` first and read the command list before you spend anything.

---

## 5. Grading

```
python3 REPO/bench/ab/grade_ab.py \
    --results REPO/bench/results/ab-codex-<date>/<date> \
    --gold REPO/bench/private/gold.json \
    --baseline codex-A-raw-sol \
    --candidate codex-B-lean-sol \
    --basic codex-C-terra-lite,codex-C-luna-lite
```

It writes `summary.md` and `summary.json` and prints the tables.

* `--baseline` / `--candidate` are what the ADOPT / UNDECIDED / KEEP rule compares. On
  the Codex side the honest pairing is raw-pages against scripts on the same model:
  `codex-A-raw-sol` vs `codex-B-lean-sol`.
* `--basic` names the arms judged by the basic-functions line instead: stable fact
  recall ≥ 0.90, zero fabrications, hard filter consistency 1.0, at least one killer
  question from the bank, a verdict present, schema valid.

The decision rule, in full:

```
ADOPT the candidate  if  fact recall >= baseline - 0.02
                     and fabrications <= baseline
                     and the mean landmine recall drop <= one code per case
                     and tokens <= 0.5 x baseline
UNDECIDED            if every difference is inside the within-config run-to-run spread
KEEP the baseline    otherwise
```

---

## 6. The worker eval, with two GPT models

`REPO/bench/ab/worker_eval.py` is written for Claude Code. The equivalent on your side:
take each task in `REPO/bench/private/worker_tasks.json`, build a **no-tools** prompt —
the task's `instruction`, then the text of `input_path` truncated to 60 KB — and ask
two models: **the largest available GPT-5.6 model and the smallest**. List them first
(`codex --help`, or whatever your build offers); do not name a version from memory.

Score each answer:

* `exact` — the normalised answer equals `expected` (ignore case, whitespace, thousands
  separators, a leading currency symbol, a trailing full stop; for a list, the same set
  in any order)
* `within` — numeric and inside `tolerance`
* `miss` — neither

Write `REPO/bench/results/ab-codex-<date>/worker-<model>.json` per model, with one row
per task: `task`, `kind`, `model`, `status`, `answer`, `expected`, `wall_time_s`, and
the token count if your CLI reports one. Then a comparison table, one row per model:
exact / within / miss counts, total tokens, total cost, total wall time.

The point of this eval is narrow: **is a small model good enough at pulling one number
out of one saved document?** If it is, the lean harness can keep handing that work to a
small model. If it is not, that is the single change that would break it.

---

## 7. Constraints

* **No portal scraping.** Rightmove, Zoopla, OnTheMarket, PrimeLocation, OpenRent,
  HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com: do not fetch them, do not
  write a fetcher for them, do not add selectors or endpoints for them anywhere. The
  repository has a standing rule about this (`docs/CONVENTIONS.md`) and it is not
  negotiable. Official registers and public APIs only: the energy certificate register,
  data.police.uk, TfL, Companies House, HM Land Registry, borough planning portals.
* **No git push.** No commits either unless the owner asks. Do not create branches.
* **Do not modify the gold.** `bench/private/gold.json`, `cases_private.json` and
  `worker_tasks.json` are read-only inputs. If you think a gold answer is wrong, say so
  in your report with the evidence; do not edit it.
* **Do not publish anything from `bench/private/`.** It is one person's real shortlist:
  real addresses, real landlords, real money.
* **No permission-bypass flags**, anywhere, for any reason.
* Scripts are **standard library only**, Python 3.9. Do not `pip install` anything.
* Write results only under `REPO/bench/results/ab-codex-<date>/`.

---

## 8. What to report back

The same tables `grade_ab.py` prints, plus what only you can tell us:

1. **Per config** — runs, fact recall, stable fact recall, fabrications, landmine
   recall (mean, min, max), landmine precision, verdict agreement (exact and the
   KILL/not-KILL split), killer question overlap, unknown share, tokens, cost, wall
   time.
2. **Paired differences**, candidate minus baseline, **per case**, plus the count of
   cases where the candidate was at least as good, and the run-to-run spread beside it.
3. **The factor table** — each ablation config against `codex-B-lean-sol`, one line
   each: *effect within noise* / *helps* / *hurts*.
4. **Basic functions** — `codex-C-terra-lite` and `codex-C-luna-lite`, pass or fail,
   check by check.
5. **The decision** — ADOPT / UNDECIDED / KEEP, with the inputs it used.
6. **The worker eval table** — two models, exact/within/miss, tokens, cost, time.
7. **Notes only you have**: the exact model ids you used, how you passed the extra
   instructions (AGENTS.md or a flag), what `--json` actually emitted and where the
   token counts were, anything that failed, and any case where the sandbox or the
   network key got in the way.

Attach `summary.md` and `summary.json`. Do not paste the contents of `bench/private/`.
