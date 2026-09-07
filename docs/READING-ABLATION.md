# The reading ablation: four ways to find the sentence that answers the question

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

A user pastes a tenancy agreement, an operator's terms, a planning officer's report or a
saved review page. Somewhere in fifteen to two hundred kilobytes there are three sentences
that answer the question, and the rest is boilerplate. **Which reading discipline finds
them, and for which model tier?**

That question is why `skills/vet-flat/scripts/find.py` exists, and `references/find.md`
says in as many words that its thick view is *"a hypothesis under test in this repo, not a
proven gain"*. This is the test. Nothing here is a result; it is the harness and the
rules, written down before the runs so the rules cannot be chosen after seeing the numbers.

```bash
python3 bench/docs_bench.py --cases bench/private/docs --arm R2 --agent claude \
        --model sonnet --case R1 --dry-run
python3 bench/docs_bench.py --cases bench/private/docs --matrix --dry-run
python3 bench/docs_bench.py --menu-probe --cases bench/private/docs
python3 bench/docs_bench.py --check --cases bench/private/docs
python3 bench/docs_bench.py --regrade bench/results/docs-2026-09-06 --cases bench/private/docs
```

---

## 1. The four arms

| arm | name | what the agent may do | asks |
|---|---|---|---|
| **R0** | full read | `Read` the document, ranges allowed. No shell at all. | every question |
| **R1** | grep only | `grep`/`rg`, then `Read` a range around each hit. | every question |
| **R2** | find.py | `find.py --ask` and, on a review page, `reviews.py`; then `Read` a range. `grep` stays as a fallback. | every question |
| **R3** | fixed regexes | `scan.py`, then `Read` a range. No grep, no other script. | fixed-form questions only |

R3 asks only the fixed-form questions (`F1`–`F18`, `references/fixed-questions.yaml`)
because fixed regexes are the whole of what that arm has; asking it a free question would
be scoring a tool for not being a different tool. That is a property of the arm, in
`ARMS["R3"]["fixed_only"]`, not a config switch.

R2 and R3 get a copy of the skill in the working directory. `$VETFLAT_SKILL_DIR` pins
which copy, so an arm can be run against an older checkout or a skill variant without
touching the harness.

### The three hypotheses, which are being re-tested and not assumed

These come from another project, on another corpus. They are patterns to check here, and
the honest outcome of this bench includes "none of them reproduced".

- **H1** — a thick view (the whole paragraph plus its neighbours, ~1,000 characters) helps
  cheap models most. Expect R2 − R1 to be larger at the cheap tier than the strong tier.
- **H2** — a rule-heavy interface hurts weak models and leaves strong ones unchanged.
  R3 is the rule-heavy end. Expect R3 to be worst at the cheap tier and roughly level with
  R1 at the strong tier, on the fixed questions only.
- **H3** — grep is enough. If R2 ≈ R1 everywhere, `find.py` is buying ranking that models
  do not need, and `find.md`'s honesty line should be strengthened rather than its ranker.

## 2. The models

`bench/ab/configs/docs/docs-matrix.yaml`: five models × four arms = 20 rows per case per run.

| vendor | cheap | middle | strong |
|---|---|---|---|
| Claude | `sonnet` | — | `opus` |
| Codex | `gpt-5.6-luna` | `gpt-5.6-terra` | `gpt-5.6-sol` |

Claude has no third public tier in this harness, so the middle cell stays empty rather than
carrying a guess. `bench/ab/configs/docs/docs-pilot.yaml` is the cheap first pass: R1 vs R2
on sonnet, two rows per case, which is the whole of H3 in one comparison.

The configs sit in a subfolder of `bench/ab/configs/` on purpose. `bench/run.py`
`list_configs()` claims every `*.yaml` directly in that directory as an A/B arm, and these
are not A/B arms; a subfolder is invisible to that sweep.

## 3. The session contract

One model call per case × arm × model × run. The working directory holds:

- `doc.txt` — the document, copied in;
- `.claude/skills/vet-flat/` or `.agents/skills/vet-flat/` for R2 and R3;
- `AGENTS.md` for codex, which is the only channel `codex exec` has for an appendix.

The prompt carries the questions (fixed ones by id, with the reader-facing wording from
`references/glossary.yaml`), the discipline for the arm in one paragraph, and the required
output — the `answers.json` shape, one object per question:

```json
[{"qid": "R1-q1", "status": "found", "value": 5, "unit": "weeks",
  "text": null, "list": null,
  "quote": "The deposit is £2,128.85, being five weeks' rent.",
  "line_start": 55, "line_end": 55, "how": "find"}]
```

`status` is `found`, `absent` (you looked; the document does not answer it) or `unknown`
(you could not tell). The array comes back **in the reply**, in a fenced block, not as a
file: R0, R1 and R3 have no Write tool and codex runs `--sandbox read-only`, so nothing in
this bench can write to its own workdir. Every launch closes stdin
(`stdin=subprocess.DEVNULL`) and the per-reply timeout is 900 s.

Questions can be asked in Chinese with `--lang zh`; the gold carries `question_zh` for
every question. The default is English, and the menu probe follows the same flag, so the
ranker is always asked what the model was asked.

## 4. How the discipline is held — and where it is only watched

**Claude: enforced.** `--allowedTools` is the whole of it, verbatim per arm:

| arm | `--allowedTools` |
|---|---|
| R0 | `Read` |
| R1 | `Read,Bash(grep:*),Bash(rg:*)` |
| R2 | `Read,Bash(python3 .claude/skills/vet-flat/scripts/find.py:*),Bash(python3 .claude/skills/vet-flat/scripts/reviews.py:*),Bash(grep:*),Bash(rg:*)` |
| R3 | `Read,Bash(python3 .claude/skills/vet-flat/scripts/scan.py:*)` |

No permission-bypass flag is passed anywhere, ever. A test greps the source for
`--dangerously-skip-permissions`, `bypassPermissions`, `acceptEdits`,
`--dangerously-bypass-approvals-and-sandbox` and `danger-full-access` and fails if any of
them appears.

**Codex: not enforced, only audited.** `codex exec` takes no tool allow-list. So:

- the discipline is written into `AGENTS.md`, plus a line telling the model that a
  read-only shell is what it has instead of a `Read` tool (`sed -n '70,90p' doc.txt`) —
  without that, R0 would tell a shell agent it has no shell and every codex row would be
  graded against a discipline nobody could follow;
- the sandbox is `--sandbox read-only`;
- the row records **`discipline_enforced: false`**;
- the `--json` event stream is parsed afterwards and every shell command is counted by
  kind: `find`, `scan`, `grep`, `read_range` (`sed -n`, `head`, `tail`), `read_full`
  (`cat`, `less`), `inspect` (`ls`, `wc`), `python`, `other`. Anything the arm does not
  allow lands in `discipline_violations`.

`read_range` and `inspect` are allowed in every arm — a read-only shell is all codex has
in place of `Read`. `read_full` is allowed only in R0, because reading the document end to
end is exactly what R1, R2 and R3 are measured against; a `read_full` violation says the
arm collapsed into R0, which is a different failure from reaching for an extra tool.

**Read a codex row as evidence of what the model did, never as evidence that a discipline
was held.** A claude R1 row and a codex R1 row are not the same experiment, and the
scorecard's `enforced` column says so on every line.

## 5. The grading rules

`bench/docs_grade.py`. Deterministic, no model, frozen. Every rule has a test both ways —
the shape that passes and the shape that fails — in `tests/test_docs_bench.py`.

| rule | passes | fails | tests |
|---|---|---|---|
| **value match** | the gold number, with tolerance for money (a penny, or 0.5%) and area (2%). Word numbers count: "five" is 5. | any other number. Weeks, months, percents and counts are exact — "five weeks" and "six weeks" are different facts. | `TestValueMatching` (5) |
| **text / list match** | every KEY of the gold is in the answer, however it is phrased | a missing key; a wrong number in place of a key number | `TestTextAndListMatching` (8) |
| **absent honesty** | `status: absent`; or `found` with a sentence that says the page is silent ("no price is shown", "does not state the window", "names no landlord") — the honest answer under the wrong label, counted apart as `absent_said_as_found` | a value → **fabrication**. `unknown` is honest but not a pass, and is counted separately | `TestAbsentHonesty` (3), `TestAbsentSaidAsFound` (3) |
| **span hit** | quote within ±3 lines of a gold span → **1.0**; verbatim with whitespace collapsed, or its words in order within twelve lines when the text came out of a two-column PDF ("reassembled"), or short but rare ("£485 pw", at most three places) | elsewhere in the document → **0.5** "misplaced but real"; nowhere → **0.0** and an **invented quote**; a short quote found all over the page → 0.0 but not invented | `TestSpanScoring` (7), `TestQuoteLocating` (5) |
| **gold span verification** | every gold quote is findable in the document at the lines the gold claims | a stale line number or an unfindable quote → the case is refused before a token is spent | `TestSpanVerification` (6) |
| **forbidden** | the correct answer matches no rule | a wrong answer matches → **fabrication** | `TestForbiddenRules` (3) + a sweep over every rule in the bed |
| **unknown honesty** | — | `unknown` on a question the document answers is a miss, counted apart from a wrong answer | `TestTheSessionScorecard` (3) |

### What the first pilot taught the grader

The 26-row pilot (R1 and R2, Sonnet, thirteen cases) reported 11 invented quotes and 9
fabrications. Reading them one by one, none of the quotes and seven of the nine
fabrications were the grader's, not the model's:

- **Seven "invented" quotes were sentences read correctly across two PDF columns.** Text
  extracted from a two-column leaflet (cases O3, O4) interleaves the columns line by line,
  so one sentence from the left column is cut by half-lines of the right one. A model that
  reads it the way a person would cannot quote it verbatim against that text. The finder
  now also accepts a quote of six or more words whose words appear in order within twelve
  lines, found at 90% or better and making up at least a quarter of the words in that
  stretch (two interleaved columns give about a half; the same words scattered by chance
  over twelve lines of a long document give a few percent).
- **Four were short quotes** — "£485 pw", "1 Beds", "£531" — under the eight-character floor.
  A short quote is now evidence when it sits in the document at most three times; it is
  rare exactly because it is specific.
- **Five fabrications were honest answers filed under `found`**: "no price is shown; the
  pricing widget errored", "no cancellation window is stated", "the agreement names no
  landlord". The rule now reads the sentence, not only the label.
- **Two were negation-blind forbidden regexes in the bed**: a rule meant to catch "a UK
  guarantor is required" also fired on "No UK guarantor is required", and "refundable"
  fired on "Not refundable". Seven rules across six questions gained a negation guard.

After the fixes, the same 26 rows read R1 0.713 facts / 0.636 spans / 0 fabrications and
R2 0.752 / 0.616 / 1 fabrication (a licence's "Provider" given as the landlord), with no
invented quotes on either arm. Every fix has a test both ways.

### Keys, not sentences

A `text` or `list` answer is right when every **key** of the gold is present after
normalisation — not when the gold's sentence is inside the answer. Whole-sentence
containment scored a correct paraphrase as wrong: a gold reading *"A licence. Clause 1.1
says the Agreement is a licence to occupy and does not create a tenancy…"* against an
answer reading *"This Agreement is a licence, not a tenancy."* On the first pilot that rule
gave one case 2/14 when twelve answers were substantively right.

Keys come from `keys: [...]` on the gold question when the bed's author has named them, and
then **every one is required**. Otherwise they are derived, and split by how much the
harness actually knows:

| derived from | required |
|---|---|
| every number the gold states, clause citations excluded | all of them |
| every value in the gold's `list`, citation keys (`clauses`, `source`, `lines`…) excluded | all of them |
| up to three distinctive terms — words ≥ 5 letters, not stop words, first three in the gold text | **at least one**, and only when there is no number or list value to check instead |

Numbers compare as numbers with the money/area tolerance, so `10319.0`, `£10,319.00` and
`10319` are one key. The keys an answer was actually judged on are written into every
graded item's notes, so `--regrade` plus a look at the notes is how the maintainer finds
the questions that need an explicit `keys` list.

The split exists because a number is a fact the gold *states* and a distinctive term is
this module's *guess* at which words a right answer would use. Requiring all three guesses
is what marked the paraphrase wrong.

### A failed launch is not a zero

A row whose reply carried no answers array gets `valid: false`, **no summary at all**, and
is counted under "not run" in the scorecard's per-arm table. Grading it as a row of zeros
poisons every mean it lands in: on the first pilot, ten failed R2 launches beside three
real ones read as an arm scoring 0.16 when the arm scored 0.70. `--regrade` applies the
same rule to rows that were already stored. `bench/launch.py` classifies the cause
(`provider_error`) and re-runs them; `is_valid()` honours that outcome too.

Three more details worth stating, because they decide close calls:

- **Whitespace, not characters.** A quote is compared with runs of whitespace collapsed and
  NFKC applied, so a sentence quoted across a wrapped line still counts as verbatim. A
  quote under 8 characters is never evidence, whatever it matches.
- **Forbidden rules run over the assertion, never the quote.** A model that quotes the trap
  sentence and then answers correctly is reading well. Only what it asserted is judged.
- **An `absent` question may carry a span, and the good ones do.** The span is then the
  sentence that proves the "no" — a review page's "Viewing 1-4 out of 4", a pet clause with
  no money in it. A model that answers `absent` and quotes that has shown its work and
  scores the span like any other. An `absent` question with no such sentence is left out
  of `span_recall` entirely: there was nothing to quote, so quoting nothing is not a miss.
- **An extra list item is reported, not marked wrong.** Naming a fourth incentivised
  reviewer is an invention, and inventions belong to that question's `forbidden` regexes.
  The list rule names the extra in the note and leaves the verdict there.
- **Every forbidden rule owes a two-way test.** `test_the_correct_answer_never_trips_a_forbidden_rule`
  builds the correct answer from the gold for *every question in every fixture* and asserts
  no rule fires. A rule that fires on the right answer would quietly turn a good run into a
  fabrication count, and that is the one grading bug that would be invisible in the numbers.

Per session the scorecard records: `fact_recall`, `span_recall`, `fabrications`,
`invented_quotes`, `unknowns`, `absent_honesty`, `menu_recall@5`, `how_counts`, tokens,
wall time and the command counts.

`--regrade <folder>` re-scores every stored row with today's rules and rebuilds the
scorecard. The replies stay what they were; only the grader runs again, so a frozen rule
that turns out to be wrong reaches runs that were already paid for.

## 6. The zero-token menu probe

For R2 rows the runner also runs `find.py` **itself**, once per question, with the same
wording the model got, and records whether a gold span is inside the top five hits:
`menu_recall@5`. It costs no tokens.

It separates two failures that look identical in `fact_recall`:

- `menu_recall@5` high, `fact_recall` low → the tool surfaced the answer and the **model**
  did not use it.
- `menu_recall@5` low → the **ranker** never put the answer on the menu, and no amount of
  model quality would have helped.

On the public fixtures the probe already earns its place: `V1-q3` asks *in English* for a
review written in Chinese, and the ranker misses it at top-5. Without the probe that would
have been filed as a model failure.

Questions whose gold answer is `absent` have no span to hit and are excluded, so a case
full of absent probes does not read as a perfect menu.

## 7. The test bed

**Private**, described in [`evals/docs/README.md`](../evals/docs/README.md), living at
`bench/private/docs/` and never committed (`.gitignore`: `bench/private/`). Real pages
saved during a London flat search, de-identified at name level — invented buildings,
streets, companies, reviewers, X-prefixed postcodes — with rents, dates, unit counts and
distances kept verbatim, because the answers depend on them. That leaves the corpus
re-identifiable, which is exactly why it stays out of git.

```
bench/private/docs/cases/<id>/doc.txt
bench/private/docs/cases/<id>/gold.json
```

```json
{"id": "R1", "type": "reviews|terms|planning|listing|agreement",
 "file": "cases/R1/doc.txt", "chars": 6989, "lines": 121,
 "questions": [
   {"qid": "R1-q1", "kind": "fixed|free", "fixed_id": "F1", "question": "…",
    "question_zh": "…",
    "answer": {"value": 5, "unit": "weeks"},
    "spans": [{"line_start": 55, "line_end": 55, "quote": "verbatim"}],
    "forbidden": ["a regex a wrong answer matches"],
    "confidence": "high|medium", "note": "…"}]}
```

`check_gold()` refuses a gold file that breaks the contract *before a single token is
spent*: a repeated `qid`, a present answer with no span, a `fixed` question with no
`fixed_id`, an uncompilable forbidden regex.

`verify_spans()` catches the two faults only the document can reveal, and `load_case()`
refuses the case rather than grading it wrongly:

- a gold quote that is **not findable** in the document — no answer can ever score that
  span, so the case quietly loses a point per question in every arm equally, which reads
  as a hard case rather than a broken gold;
- a gold quote that **is** in the document but not within ±3 lines of the lines the gold
  claims, usually a gold built against an earlier copy — every correct quote then scores
  0.5 "misplaced but real" and the case reads as if every model half-missed it.

`--check` reports the whole bed at once, for whoever is building it:

```bash
python3 bench/docs_bench.py --cases bench/private/docs --check
```

**Public fixtures** — `tests/fixtures/docs_bench/cases/{A1,V1}/`, built from the finder
fixtures, same shape, safe to commit, and what the tests read.

| case | type | document | questions |
|---|---|---|---|
| `A1` | agreement | the invented tenancy agreement, 249 lines | 3 fixed (F1, F4, F10), 3 free, 2 of them `absent` |
| `V1` | reviews | the invented review page, 150 lines, English and Chinese | 6 free, 2 of them `absent` |

In each case one `absent` probe carries the span that proves the "no" and one does not, so
both paths through the grader are exercised by the public bed.

Both carry traps that are in the documents on purpose: `A1` is headed ASSURED SHORTHOLD
TENANCY AGREEMENT and clause 2.3 says it is a licence; the holding deposit is one week's
rent and the deposit is five; the EPC is C now and B potentially. `V1` has a 78% hygrometer
reading a model can mistake for the 12% rent rise, and three of six five-star reviews
disclose an incentive while the other three do not. The `absent` probes have near misses
that grep will surface — a parking bay "allotted to another flat", a pet clause with no
money in it — so `absent` is a real decision, not an empty search.

Every gold span quote is asserted verbatim within its own line range **and** unique in its
document, so a span hit can never be an accident of a repeated phrase.

## 8. Results

**The full matrix ran on 2026-09-07: four arms, five models, thirteen private documents,
one run per cell, 230 rows planned (R3 asks only the seven cases that carry fixed-form
questions), all 230 graded.** Seven rows needed a second attempt: six of the strong OpenAI
model's R3 rows hit the 900-second ceiling with no reply and one cheap-model R2 row returned
no answers array; re-run with an 1,800-second ceiling they finished in two to nine minutes
(transient slowness, not a property of the arm) and the tables use one row per cell, the
first valid one. Single runs: a difference of three points in a cell is noise, six is a
hint, and the same sign across five models is a finding.

### Per arm, all models

| arm | rows | facts right | quote in place | said "not there" when it was not | fabrications (rows) | tokens per row |
|---|---|---|---|---|---|---|
| R0 read the whole document | 65 | 0.731 | 0.644 | 0.940 | 12 | 320 k |
| R1 grep only | 65 | 0.720 | 0.642 | 0.905 | 19 | 299 k |
| R2 find.py + reviews.py (keyword search with synonyms, thick view) | 64 | 0.725 | 0.638 | 0.906 | 17 | 461 k |
| R3 scan.py only (fixed-form regexes; 7 cases) | 35 | 0.395 | 0.276 | 0.634 | 2 | 331 k |

### Facts right, per model and arm

| model (tier) | R0 read | R1 grep | R2 find.py | R3 scan.py |
|---|---|---|---|---|
| Claude Sonnet (cheap) | 0.727 | 0.706 | **0.768** | 0.424 |
| Claude Opus (strong) | **0.839** | 0.803 | 0.782 | 0.441 |
| gpt-5.6-luna (cheap) | **0.722** | 0.711 | 0.684 | 0.361 |
| gpt-5.6-terra (middle) | 0.680 | 0.669 | **0.699** | 0.355 |
| gpt-5.6-sol (strong) | 0.688 | **0.711** | 0.690 | 0.392 |

Fabrications per model over the three reading arms (39 rows each): Sonnet 7, Opus 5, luna
15, terra 9, sol 12. Wall time per row: Claude 1.2–1.9 minutes, OpenAI 4–8 minutes. The
find.py menu probe — the tool's own top-five ranking, zero tokens — put the answering
paragraph in the top five 0.51 of the time on every model's question set.

### What it says

1. **The reading discipline moves facts by three to six points inside a model; the model
   moves them by eleven.** Opus reading the whole document (0.839) beats every other cell by
   a margin no discipline closes. The three hypotheses of section 1 were re-tested, not
   assumed: none of them held as a general claim.
2. **find.py does not beat grep or the whole document.** It helps Sonnet (+0.04 over reading)
   and terra (+0.02), hurts luna (−0.04) and Opus (−0.06), and costs 44% more tokens than
   reading and 54% more than grep, because its thick view is verbose. The honest reading of
   the hypothesis "BM25 + a harness beats a bare shell" is: not on documents of this size
   (4,000–65,000 characters). Its case would have to be made on documents too long to read,
   and none of these was.
3. **Tools cost honesty.** With grep or find.py the models said "not there" less often when
   it was not there (0.905 against 0.940) and fabricated more (19 and 17 rows against 12).
   A tool that returns nothing reads as "no answer" to a careful model and as "look harder,
   then guess" to a less careful one.
4. **The regex scan is a starting point, not a reader.** R3 answers fewer than half the
   fixed-form questions; that is the floor a model must beat, and every model did by a wide
   margin.
5. **OpenAI's Codex ran commands in the arm that forbids them** (R0: 280–400 command
   executions per thirteen rows). Read those rows as "what the model chose to do", not as
   the discipline held; the Claude rows held it by construction.

### Files

```
bench/results/docs-ablation/docs-matrix-2026-09-07/
  raw/<row>.json              the whole record: command, usage, answers, per-question cards
  answers/<row>.answers.json  just the model's array, for reading by eye
  scorecard.json
  scorecard.md
```

A row is `docs-<arm>-<agent>-<model>-<case>-<run>`.

## 9. The run matrix and what it costs

Per case: 4 arms × 5 models = 20 calls. The private bed has 13 cases, so a full single-run
matrix is **260 calls**; at `--run 3`, 780.

The cost is dominated by R0, which puts the whole document in the context every time. A
15 KB document is roughly 4–5 K tokens; the largest cases in the bed are 100 KB+, so an R0
row there is 30 K+ input tokens before the model has said anything, while an R1 or R2 row
on the same case reads a few hundred lines. **Order of magnitude only, and the point of
recording `total_tokens` per row is that this document should not be the source of that
number once the runs exist.**

Run the pilot first:

```bash
python3 bench/docs_bench.py --cases bench/private/docs --matrix \
        --matrix-config bench/ab/configs/docs/docs-pilot.yaml --case R1
```

## 10. What the results can and cannot say

**Can:**

- Whether an arm changes `fact_recall`, `span_recall` or fabrication counts on *these
  twelve documents*, for *these five models*, on *these questions*.
- Whether a gap between arms is bigger at one tier than another — H1 and H2 are stated as
  gaps between arms within a tier, which is the comparison this design supports.
- Whether a failure is the ranker's or the model's, on R2 rows, because of the menu probe.
- Whether an arm makes a model *invent*: `absent_honesty` and `invented_quotes` are
  separate columns from `fact_recall`, so an arm that raises recall by guessing does not
  look like an arm that raises recall by reading.

**Cannot:**

- Say anything about the Claude middle tier. There is no row for it.
- Compare a claude row with a codex row as an equal test of a discipline. One is enforced
  and one is asked for. The `enforced` column is on every line of the scorecard for this
  reason, and `discipline_violations` says how far a codex row drifted.
- Generalise past this corpus. Twelve documents of five types, from one person's flat
  search, in two languages. A finding here is a reason to look again, not a law.
- Settle a difference smaller than the run-to-run noise. `--run 3` and a look at the spread
  come before any claim that one arm beat another; with one run per cell, a one-question
  difference on a six-question case is 0.17 of `fact_recall` and means nothing.
- Say whether the thick view is the right *size*. The 1,000-character view is one setting,
  not a swept parameter. If a run shows a model quoting confidently from a paragraph that
  did not contain the answer, `find.md` asks for that to go in the notes rather than for
  the view to be quietly shrunk.

## 11. Files

| file | what it is |
|---|---|
| `bench/docs_bench.py` | the runner: arms, prompts, commands, codex audit, menu probe, results, `--regrade` |
| `bench/docs_grade.py` | the frozen grader; importable and runnable on one answers file |
| `bench/ab/configs/docs/docs-matrix.yaml` | 4 arms × 5 models |
| `bench/ab/configs/docs/docs-pilot.yaml` | R1 vs R2 on sonnet |
| `tests/test_docs_bench.py` | 94 tests: fixtures, span verification, every grading rule both ways, menu probe, dry-run tool strings, codex audit, matrix, regrade |
| `tests/fixtures/docs_bench/` | the two public cases |
| `evals/docs/README.md` | what the private bed is and why it is private |
| `skills/vet-flat/references/find.md` | the tool under test, and its own honesty line |
