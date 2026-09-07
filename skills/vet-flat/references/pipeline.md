Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The role pipeline: planner → executors → verifier → integrator

One agent doing all four jobs is fast and usually fine. It also fails in one particular way: it fetches something, forms an opinion, and then reads everything afterwards as support for the opinion. The number that was about the building becomes the number about the flat. The rating on the replaced certificate becomes the rating. Nobody lied; the same head did the getting and the deciding.

This page splits the work into four roles that cannot do each other's job, and puts a deterministic check between the getting and the deciding. It is written so any agent can follow it — with subagents or without, on any vendor.

## When to use it

Run the pipeline when **any** of these is true:

- the model doing the judging is not the strongest one you have;
- the flat is on the final shortlist of two or three;
- the budget mode is `deep`;
- the report will be shown to somebody who is going to sign something.

Otherwise the single pass in `SKILL.md` is enough. The pipeline costs more calls and more wall time; it buys separation, and separation is only worth paying for when a wrong number would actually cost something.

## The four roles in one line each

| Role | Decides | Never | Tier |
|---|---|---|---|
| **Planner** | what to fetch, what to ask the user | reads a page; decides which fields survive | cheap |
| **Executors** | nothing — they collect | writes a verdict, a score, or a sum of its own | cheap, in parallel |
| **Verifier** | which evidence stands up | fetches anything new | the strongest you have |
| **Integrator** | what the report says | uses anything the verifier did not pass | the strongest you have |

The one rule that holds the whole thing up: **the planner decides WHAT TO GET, never what survives.** A planner that also picks the fields is a planner that quietly throws away the field the answer needed, and no downstream role can get it back. If you must give the planner an opinion about fields, give it as a hint the executors may ignore, and keep everything.

## With subagents, and without

**With subagents** (Claude Code, Codex with collaborators, anything that can spawn a worker): each role is a subagent with its own tool list. The executors run in parallel, one per axis group. Four or more at once always use the cheap tier — that is the fan-out rule in `budget-modes.md`, and it applies here too.

**Without subagents** (one chat window, one context): run the roles as phases, in order, **and write each phase's output to a file before the next phase starts.** Then start the next phase by reading that file and nothing else. Say out loud which phase you are in. The file is what makes the separation real: without it you are one agent again, remembering what you hoped to find.

If you have no file system either, put each phase's output in its own fenced block, in order, and begin the next phase with "Reading plan.json:" and quote it back. It is weaker, and it is still better than nothing.

## Tool discipline per role

The tools are the discipline. Not the instructions — the tools.

| Role | May use | Writes |
|---|---|---|
| Planner | Read | prints `plan.json` |
| Executors | Read, Bash (`python3 scripts/*.py`) | print `evidence.json` items |
| Verifier | Read, Bash (`scripts/verify.py`, `scripts/calc.py`) | prints `verified.json` |
| Integrator | Read, Write | writes `report.json` |

Only the integrator writes a file. Everybody else prints one JSON object and the harness — or you, in one context — saves it. A role that can write files can leave itself notes, and notes are how an opinion gets from the planner to the integrator without passing the verifier.

---

## 1. Planner

**Input:** `profile.yaml`, the user's request, the budget mode, the fixed-form tier.
**Output:** `plan.json` — `references/plan-schema.json`.
**Start from:** `python3 scripts/plan.py --mode <lite|standard|deep> --postcode "<postcode>"`, which prints the scaffold deterministically.

Write, per axis: the scripts to run with their arguments, the sources allowed, and what only the user can supply. Then the fixed-question ids this tier owes an answer to, and every question for the user **in one list, asked once**.

You may **add** to the scaffold — a second postcode because the building spans two, a heat-supplier lookup because the request mentions a communal network. You may not **shrink** it. Check yourself:

```
python3 scripts/plan.py --check plan.json --mode standard
```

Exit 1 means you dropped something required. Put it back.

Do not read a page. Do not run a fetcher. Do not decide that floor position "will not matter for this flat" — you have not seen the flat. The planner's whole value is that it is cheap and has no opinions yet; both go away the moment it starts reading.

A cheap model is right for this job and there is evidence for it: on a comparable planner task a small model produced a usable plan every time where a large one managed under two in five, at a twenty-eighth of the cost. Plan quality is about coverage, not cleverness.

## 2. Executors

**Input:** `plan.json`, and only the axes in your group.
**Output:** `evidence.json` items — `references/evidence-schema.json`.

Two rules the pilot taught (2026-09-07). **A call marked `fallback` in the plan runs when
the axis's primary call returned nothing or failed** — before an item is written unknown —
and every attempt, primary or fallback, goes under `tried` with its error. **A script whose
JSON says `ok: false`, carries a `curl error`, or shows `http_status: 0` is a failed fetch,
never an answer**: do not copy a count or a null out of it as a value (a `certificates_found:
0` after a dead search is not zero certificates). Record it as unknown with the error under
`tried`, and try the fallback. The verifier fails a found item whose note or quote carries
such an error (`dead_fetch`).

One executor per axis group, in parallel. Each writes items and nothing else:

```json
{"id": "e-area", "axis": 2, "claim": "certified internal floor area of this flat",
 "status": "ok", "value": 54.0, "unit": "m2", "source": "pasted:epc-cert",
 "quote": "Total floor area: 54 square metres.", "fetched_at": "2026-09-06T09:00:00Z",
 "script": "scripts/epc.py cert 0000-0000-0000-0000-0000"}
```

- **`claim` names the thing, not the source.** "certified internal floor area of *this flat*", not "the EPC number". The referent check reads this field: a claim that says which thing it is about is a claim that can be checked.
- **`quote` is verbatim.** Copy it; do not retype it, do not tidy it, do not join two sentences. For a script result, quote the line of its JSON: `"total": 199`.
- **Save what you quoted.** Write each script's JSON output to `sources/<name>.json` before you quote it, and cite it as `pasted:<name>`. A quote nobody can open is a quote nobody can check, and the verifier will not take your word for it. Where the fact came from a register page rather than a script, the source id from `sources.yaml` is also accepted.
- **The scripts are inside the skill folder**, not beside your working directory: run `<skill>/scripts/epc.py`, never a bare `scripts/epc.py`. The plan the harness hands you already has the full path in it.
- **`unit` always.** 54 is not an area.
- **No verdicts. No scores. No comparisons with the profile.** "54 m² is below the 45 m² floor" is two jobs at once and one of them is not yours.
- **No arithmetic in your head.** The only sum you may report is a `scripts/calc.py` call, written into `computed_by` with its output. Anything you worked out yourself belongs to nobody.
- **When you cannot get something, say so as an item:**

```json
{"id": "e-reviews", "axis": 6, "claim": "organic management review score",
 "status": "unknown",
 "tried": ["asked the user once for the lowest reviews with their dates; nothing pasted",
           "review sites forbid automated access, so no script can get this"]}
```

A gap somebody tried to fill is a different thing from a gap nobody looked at, and the verifier treats them differently. An `unknown` with an empty `tried` fails under `verify.py --strict`.

## 3. Verifier

**Input:** `evidence.json`, the pasted sources, and — if there is one yet — `report.json`.
**Output:** `verified.json` — `references/verified-schema.json`.

**Run the deterministic check first. Always.**

```
python3 scripts/verify.py evidence.json --sources sources/ --tier standard --table
```

It checks, with one answer each: the quote really is in the source (whitespace ignored, case ignored); the source id resolves; every number carries a unit; the number is about the thing it claims to be; every legal cap recomputed from the rent the evidence itself carries; items that claim the same thing and disagree; and whether the tier's fixed questions are all answered. It exits 1 if anything failed.

**Then read only what it flagged.** That is the point. A verifier that re-reads everything costs as much as the run it is checking and goes blind in the same places. Your job is the handful of items a rule could not settle.

**Write the whole file, not just your part.** Start from what `verify.py` wrote and change
only the entries you actually looked at. An item you leave out is **unknown in the
report**, so dropping the ones a rule already settled would empty a perfectly good run.
And you may re-judge evidence, never create it: an item id that is not in `evidence.json`
does not belong in `verified.json`.

On each flagged item, decide one of three things and say why in one sentence:

- **pass** — you looked, and it stands.
- **fail** — and the reason a reader could act on. When you are agreeing with a `verify.py` failure, **quote its reason back** in your own `reason` and name its rule id in `rules`. A fail with no reason reads as an opinion and gets dropped.
- **unknown** — the executor could not get it, or you looked and still cannot tell.

**Unknown is not the default.** An item `verify.py` passed stays passed unless you have a reason to say otherwise. Marking a whole file unknown is not caution; it is an empty report, and the integrator will faithfully print it as one.

Check these by hand, because they are where reports go wrong:

1. **Quote in source.** Not "close enough". The words, in that order.
2. **Referent.** A building-level number is not a flat-level number. A historical rating is not the current one. A sale price is never a year. The strike-day journey is not the commute. Another flat's area is another flat's area.
3. **Rule adoption.** Every legal cap applied *with the right branch*: deposit five weeks where the annual rent is under £50,000 and six at or above it; holding deposit one week; rent in advance at most one month. The branch is the part people get wrong, because it turns on an annual figure nobody computes. Recompute it from the rent in the evidence: `scripts/calc.py deposit --rent-pcm <rent>`. The caps live in `references/thresholds.yaml`.
4. **Contradictions.** The advert's area against the certificate's; the advert's energy letter against the register's. Two sources disagreeing is a finding, not a tie to break quietly.
5. **The fixed form.** Every id the tier owes, in one of its three states.

Then write a `replan` list: what is worth one more round of executor work, concretely — the command with the right argument, the page to ask for. **One round only.** If the second round still cannot get it, it is unknown, and the report says so and says what it costs not to know it. A replan loop with no cap is how a run spends a whole budget on the one fact that was never available.

## 4. Integrator

**Input:** `verified.json` and `evidence.json`. Nothing else.
**Output:** `report.json` — `references/report-schema.json` and `references/report-contract.md`.

- **Verified items only.** An item that is not in `verified.json`, or is there as `fail` or `unknown`, is **unknown in the report**. Not "probably". Not quietly dropped. Unknown, with the line telling the reader what it costs not to know it.
- **Cite the item ids** in `sources` and `computed_by`, so a reader can walk any number back to the sentence it came from.
- **The first line names the tier and the pipeline**: `Configuration: <tier> — <reason>; pipeline: planner/executor/verifier`. A reader deserves to know how much machine was behind the words.
- Everything else is the ordinary report contract: the verdict card, the hard filters, the fixed form, the landmines, the twelve checks, what only the user can tell, what could not be found.

The integrator does not go back for anything. If it finds itself wanting a fact, that is a note for `not_found`, not a fetch.

---

## What this is expected to buy, and what it is not

Nothing on this page is a measured result for flat vetting. The design comes from a different domain (a regulated-document question-answering system, 2026-07) where the same shape was measured, and **its findings do not transfer** — they were re-tested here from scratch. The arms are in `docs/EXPERIMENTS.md` under "Role pipeline (to be measured)" and the harness is `bench/pipeline.py`. Until those tables have numbers in them, treat this page as a design, not a recommendation, and say so if you quote it.

Two things are worth knowing while the numbers are being collected:

- **The split and the check are different factors.** A pipeline that fetches in four roles and never checks anything may buy nothing at all. That is why there is an arm with the verifier and no split (`P3`) and an arm with the split and no verifier (`P1`).
- **Information sufficiency is the diagnostic.** When a fact is missing from the report, `verify.py --gold` says whether it was in the evidence at all. Missing from the evidence is a planner or executor failure; present in the evidence and missing from the report is an integrator failure. They look identical in a score and they need opposite fixes.
