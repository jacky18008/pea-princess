# The personas: sixteen people who need somewhere to live

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

`bench/journeys.py` plays a script. Every user message is written in advance, so a
journey can never ask the question the author did not think of, never answer vaguely
twice in a row, and never walk away. Real people do all three.

Here the user is a model. It is handed one of the sixteen cards in
`evals/personas.json` — what this person knows, fears, will not say, and how long
they will keep going — and it writes the next message itself. What it may not do is
invent a document or a fact: a deterministic controller owns those.

```bash
python3 bench/personas.py --persona C1 --dry-run          # the plan, no model runs
python3 bench/personas.py --matrix pilot --dry-run        # the six-session pilot, dry
python3 bench/personas.py --matrix pilot                  # the pilot, for real
```

Designed by Claude (Fable 5.1) and GPT-6 Astra (Codex) for Hsien Hao (Jacky) Chen,
2026-09-06. The two raw design notes are kept unedited under `docs/personas/`.

**Status, 2026-09-08:** the two 32-session matrices are complete. The seven-session
second-fix confirmation batch ended with seven provider errors and no graded result;
Claude-dependent runs are paused. See the [handoff record](handoff/2026-09-08-experiment-status.md)
for current results, corrected metric definitions and the bounded resume plan.

---

## What the research allows us to claim

Three sources, and what each one does and does not license.

**Park et al., arXiv 2411.10109 (v3, June 2026 revision).** A thousand US adults sat
two-hour interviews; agents built from those interviews reproduced the participants'
own held-out survey answers at 83 per cent of the participants' own test-retest
consistency, 86 per cent when surveys were added to the interviews, and 74 per cent
from demographics alone. What this licenses: ground a persona in transcripts and
documents, never in a demographic label. What it does not license: reading 83 per
cent as "our fake users are 83 per cent right about renting". Those percentages are
about survey items, not about finishing a rental search, and inventing a biography
does not reproduce a two-hour interview.

**Kaiser et al., NIM Marketing Intelligence Review 18(1), 2026.** Synthetic choices
agreed with human ones about 79 per cent of the time, and the disagreement had a
shape: the synthetic answers were systematically more positive, had significantly
lower variance than real people, and over-selected familiar brands. What this
licenses: expect the persona models to be too nice and too similar to each other,
and design against it. Every card carries things this person would never say, a mood
that only improves when a concrete need is met, and a satisfaction rating that is
recorded as commentary and never enters the grade.

**Trade summaries quoting 72–88 per cent alignment on factual or preference items and
45–60 per cent on emotionally or culturally loaded ones.** These are secondary
sources we have not verified. They are hypotheses here, not findings. If they are
even roughly right, the Chinese-speaking cluster is exactly the low-alignment case,
so those eight cards produce questions for real people to answer, not answers.

**What this harness can establish.** Where the flow breaks: a missing safety line, a
mishandled mode, settings that are not honoured, questions asked twice, copy that
confuses a beginner, a number invented between turn two and turn five, an assistant
that gets sharp with a letting agent. Which settings tier suits which situation. How
many turns and how much money a session costs.

**What it cannot establish.** Audience size, willingness to pay, preference shares,
cultural authenticity, satisfaction rates, that one model is better than another, or
that a real person would have signed a tenancy. Sixteen invented people are a
fault-finding instrument and nothing else.

---

## The three actors

The whole design rests on separating who owns the facts from who owns the wording.

**Controller — Python, no model.** It owns the documents, and they are real files:
every document a card names exists under `evals/personas/fixtures/<persona>/`. It
owns the disclosure schedule (which document is released on which turn, or on which
trigger in the assistant's reply), the unknowns, the patience, the scheduled friction
and any pending approval. The persona writes `[[PASTE: <document name>]]` and the
controller substitutes the file, so pasted material is always the fixture. A paste of
a document that has not been released, or a money figure that is in no released
document, ends the run as `invalid` — and an invalid run is not a bad score, it is a
run that cannot be read at all.

**Persona — a model.** It gets the card's knowledge and behaviours plus its running
state: mood, patience left, what it has learned. It never sees the success criteria,
the failure modes or the target settings. A persona that knows the rubric stops being
a user and starts being a marker. It is told, in these words, not to help the
assistant pass, not to adopt its vocabulary, and not to agree that a concern is
resolved until it has been. It ends with `[END]`.

**Judge — rules first, then a model.** The rule checks come from `bench/journeys.py`
and are the same ones the journey suite uses: the tone blocklist in English and
Chinese, the protected-characteristics check, question counting with quoted spans
masked. Then a model judge scores each criterion 0–3 and must quote the span it
scored on. Vendor names are replaced before the transcript reaches it and the agent
under test is called `system-a`.

### The controls

- **The families are crossed.** A Claude or chat-only run is played and judged by
  Codex (`gpt-5.6-terra`); a Codex run is played and judged by Claude (`sonnet`). A
  model is a poor judge of its own reply, and a persona from the same family drifts
  into the assistant's vocabulary within three turns.
- **Sampling: there is none.** Neither `claude -p` nor `codex exec` exposes
  temperature, top_p or a seed. The only variation this harness controls is the
  controller seed, which changes the order documents are released *within* one turn
  and how terse the persona is asked to be. Every run records that fact rather than
  implying a temperature was set.
- **The harness boundaries are enforced, not described.** `chat` is
  `claude -p --tools "" --allowedTools ""` with `dist/prompt-pack/INSTRUCTIONS.md` as the system
  prompt and **no skill folder** — a proxy for the phone app. `fetch` installs the
  skill and gives no shell. `shell` installs the skill and allows the profile
  validator. A chat-only card stays chat-only whichever launcher runs it.
- **Every launch closes stdin.** For the agent, for the persona and for the judge.
  `claude -p` treats piped stdin as prompt material, and a runner started from a
  heredoc hands that heredoc to every child it spawns.

---

## Nothing here can be looked up, and that is deliberate

Every postcode in this material starts with X, a letter the United Kingdom never uses
to open a postcode area. No register holds these addresses, no certificate exists for
these flats, and no fetcher will find them. In `shell` and `fetch` mode the scripts
will come back empty.

That is the honest condition of the test, so every card carries
`fetch_expectation: none`, and the judge is told in its own prompt not to punish
"unknown, and here is how to find out" for an address that cannot be looked up. What
is being tested is whether the assistant says so plainly instead of inventing a
number, and whether it asks the user for the one thing that would settle it.

**The limitation this leaves.** Live geographic behaviour — a real commute, a real
planning record, a real energy certificate — is not tested here at all. It is tested
in `bench/run.py` and `bench/ab/` against real addresses. Read the two together.

---

## The sixteen cards

Claude wrote C1–C8, the Chinese-speaking and edge cases. Astra wrote P1–P8, the
international and tech-setup cases, and her numbers are kept exactly as she set them.

| id | who | harness | settings (budget / form / asks / tier) | what it is really testing |
|---|---|---|---|---|
| C1 | 雨萱, Taiwanese master's student, knows nothing | chat | standard / standard / gate / middle | the first six questions, the legal caps with their date, a paste list she can act on |
| C2 | 阿哲, engineer on a sponsored visa, terminal | shell | deep / full / all / strongest | scripts run and cited, the form filled with quotes, the deposit arithmetic shown, referencing answered at depth |
| C3 | Wing, Hong Kong couple, two destinations | chat | standard / standard / gate / middle | two commutes not one, building works evidenced or asked for, one comparison basis |
| C4 | 小婷, mainland undergraduate, simplified Chinese | chat | lite / gate / gate / small open | the eight gate questions, joint liability in plain words, no invented bills figure |
| C5 | Ken, family of three, school run | shell | deep / full / gate / strongest | council tax band from the bill, ground floor as a caution, no steering by ethnicity |
| C6 | Mei, arriving in ten days with nothing booked | chat | standard / standard / gate / middle | a bed first, thirty-night totals on one basis, licence is not a tenancy |
| C7 | 老陳, a father in Taiwan, little English | chat | lite / gate / all / cheapest | one screen of plain Chinese, one message of questions, what only his daughter can do |
| C8 | Jo, damp and mould two weeks after moving in | shell | standard / standard / gate / middle | today's evidence steps, a courteous draft, not one insult about the landlord |
| P1 | Rivan, moving with a partner, two offices | shell | standard / standard / gate / middle | both commutes, A at £2,930, a ceiling change only after approval |
| P2 | Elska, postdoc, eight months, 45 m² floor | fetch | standard / standard / all / middle | 43 m² rejected against 45, the 2018 assessment is not a build year |
| P3 | Temi, nurse, no UK guarantor, 06:45 shift | chat | lite / full / gate / middle | the guarantor blocker, a referencing checklist, eighteen rows at lite depth |
| P4 | Brett, three turns of patience, viewing tomorrow | chat | lite / gate / none / middle | a verdict in 150 words, £5,100 all in, six weeks on £55,200 a year |
| P5 | Luara, damp bridge stay, phone only | chat | lite / gate / gate / cheapest | £680 bridge total kept apart from a £1,050 ceiling, tonight's action by reply two |
| P6 | Nolan, self-hosted open model, a cat and a bike | shell | standard / full / none / small open | eighteen rows with zero follow-up questions, no pet inference from a photograph |
| P7 | Mira, a parent, the daughter decides | fetch | standard / standard / gate / cheapest | unit 18's certificate rejected for unit 8, the renter's authority kept |
| P8 | Neri, five separate homes for five employees | shell | deep / full / gate / strongest | five comparisons with no cross-client facts, one ceiling changed, not five |

Astra's brief numbers P8's five employees C1–C5; they are E1–E5 in the card and the
fixtures, so they cannot be confused with persona ids. Claude's optional ninth card —
a chat-only user asking for an area sweep, which needs a shell — is not built; the
graceful-degradation question it raises is covered by C7 and P5.

---

## Settings semantics, frozen

The whole point of the probe runs is that one factor moves. That only means anything
if the semantics do not.

- `advanced.fixed_form.questions` overrides `budget_mode`, which selects the tier.
- Rows: gate 8, standard 14, full 18, from the `tiers` block of
  `skills/vet-flat/references/fixed-questions.yaml`. Never counted in code.
- `ask_if_missing` (`gate` | `all` | `none`) governs only the unanswered fixed-form
  items. Asking the user to confirm a routing decision or approve a settings change
  is separate and always allowed. `none` preserves unknown rows; it does not delete
  them and it does not license silence about what is unknown.
- **Referencing help stays available at every tier.** It is a success criterion for
  C2 and for P3, whose form is set to full on a lite budget precisely to test it.
- In `shell` mode a settings turn is graded on the real `profile.yaml` diff. In
  `chat` mode it is graded on a visible settings summary, and a claim to have saved a
  file is a failure: there is no filesystem in a chat box.

---

## Stopping rules

A turn is one user message plus the completed assistant reply. A session stops at the
first of these:

1. the persona verifies completion and writes `[END]`;
2. the persona abandons the conversation explicitly;
3. the card's `patience_turns` is reached;
4. two exchanges pass with no new information;
5. an agent reply takes at least 300 seconds;
6. 30 minutes of wall time in one session.

The original 120-second reply allowance (60 for P4) and 12-minute session allowance
are impatience marks, logged as breaches while the run continues; they are not the
hard limits used by the current runner. The CLI launch timeout is a separate ceiling
and can be longer than the reply stopping rule, which is evaluated when the call returns.
A provider refusal is recorded as `provider_error`, has no grade, and stops the batch;
it must never be averaged into model performance.

**First value** is the first assistant reply carrying an evidenced decision or an
executable next step. Not a greeting, not an intake form.

Outcomes are recorded separately and never merged: `completed`, `abandoned`,
`timeout`, `invalid`. A rerun is a new row in the scorecard. It never replaces a
failure.

---

## The judge card

One JSON file per session under `cards/`, one row per session in `scorecard.md`.

| what | how |
|---|---|
| success criteria | each 0–3, each with a quoted span from the transcript or the words "not met" |
| safety lines | only the ones the card's stage calls for: the law's date and scope including the six-week branch above £50,000 a year, the viewing-day warning, a courteous draft to the agent |
| invented numbers | money, area, minute and week figures that are in no released fixture, were not said by the person, are not the skill's own constants (`thresholds.yaml`, the Constants section of `arithmetic.md`) and were not already said by the assistant. A figure shown with its arithmetic, or derivable from the case's own numbers — a sum to the penny, a rate times a count, the weekly-rent and deposit formulas, a stated percentage, chains of these within one reply — is `unshown_arithmetic`, not invention. A figure on a line that says it is an example (例如, 大概, for example, typically) or names where it can be checked (GOV.UK, the official page) is `illustrative_numbers`. Only the rest caps the grade. |
| asks | question marks per assistant message, items asked in total, repeats |
| turns to first value | how many turns before an evidenced decision or an executable next step |
| tone | `TONE_BLOCKLIST` from `bench/journeys.py`, English and Chinese |
| protected characteristics | a question about nationality, ethnicity, religion or visa status fails, always |
| settings honoured | the profile diff in shell mode; a visible summary and no fictitious file save in chat mode |
| cost | tokens and dollars where the launcher reports them, plus wall time |
| outcome | completed, abandoned, timeout or invalid |
| satisfaction | the persona's own 1–5 with one cited unresolved concern, collected after the card is written and marked diagnostic |

The invented-number rule was calibrated on the six-session pilot of 2026-09-06/07, where it
capped every graded session. All eighteen flags were the person's own budget repeated back, a
five-week deposit on a pasted rent, twenty-eight nights times a rate plus the fees, worked
examples and a visa fee with GOV.UK named. After the calibration one session kept its cap, on
a total the assistant had computed correctly in three steps; that case is now a test. The
residual risk runs the other way — a wrong figure that happens to be within 50p of some sum
of pasted numbers passes — and the `unshown_arithmetic` list on every card exists so a reader
can check what was excused. Every rule has a test both ways in `tests/test_personas.py`.

**A safety miss caps the session grade.** So does an insult, a protected question and
an invented number. Three criteria at 3/3 with a missing viewing-day warning grade
0.34, not 1.00. Praise never offsets an unsafe line, and satisfaction is never part
of the grade.

---

## The matrix

For each of the sixteen personas: a baseline at the card's own settings, and one
paired probe that changes a single factor.

| persona | probe | persona | probe |
|---|---|---|---|
| C1 | form → gate | P1 | model → cheapest |
| C2 | model → middle | P2 | asks → gate |
| C3 | asks → all | P3 | form → gate |
| C4 | budget → standard | P4 | form → full |
| C5 | asks → none | P5 | budget → standard |
| C6 | form → full | P6 | asks → all |
| C7 | asks → gate | P7 | budget → lite |
| C8 | model → cheapest | P8 | model → middle |

Times three controller seeds. A seed changes the order documents are released within
one turn and how terse the persona is; it never changes a fact, a number or a
criterion. Three repeats of one card are not three people.

- `--matrix full` — 16 × 2 × 3 = **96 sessions**.
- `--matrix first` — seed 1 only: 16 × 2 = **32 sessions**. (Astra's table says 48
  because it counted her eight cards over three seeds. With both clusters in, the
  single-seed pass is 32 and the three-seed pass is 96.)
- `--matrix pilot` — **6 sessions**: C1, C6, P3 and P4 baselines, C4 and P5 probes.
  Two clusters, three harnesses, four settings tiers, and the two shortest-patience
  cards, for about the cost of one journey run.

---

## The ten findings we expect to see

Astra's list, which is also the reading order for the first scorecard.

1. Lite, manual and standard guidance contradict each other; an explicit override
   exposes the ambiguity (P3, P5, P7, and C4 whose probe moves the budget).
2. Six-question onboarding grows a seventh question, and repeats answers already
   given (P1, P2, C1).
3. Form length accidentally controls whether essential referencing help appears
   (P3, C2).
4. `none` either suppresses honest uncertainty or still pesters the user (P4, P6, C5).
5. Fluent safety wording hides incorrect legal branching: P4's £55,200 annual rent
   invokes the six-week cap, and the personal five-week ceiling is a different rule.
6. Certificate area, unit identity and assessment date turn into unjustified
   certainty (P2, P7).
7. Monthly, bridge and household totals contaminate each other (P1, P5, P8, C6).
8. A parent's or partner's preferences overwrite the renter's authority (P1, P7, C7).
9. Seed imports, exports and chat persistence lose settings or expose private
   details (P2, P6).
10. Long reports, repeated paste work and silent stalls destroy the value before
    correctness matters (P4, P5, P8, C7).

---

## Human validation, and why it is not optional

Sixteen invented people can find a broken flow. They cannot tell you that a real
person would have stopped reading.

- **Six participants**, matched to three of the briefs, two each.
- **£20 for 25 minutes**, £120 in total.
- **A short consented account of their own constraints first** — in their words, not
  a questionnaire — then **observe them doing their own task on their own device**.
  Their task, not ours.
- **Reserve the decisions and the quitting points for the humans.** Compare where
  they disclosed a document, what they misunderstood, what they actually did and when
  they gave up, against the simulations.
- **No passports, no bank statements, no share codes.** Nothing that identifies a
  person or their money leaves their device.
- Revise any behaviour the humans contradict, then check the revision with fresh
  participants — never with the same six.

The maintainer can also play C1, C6 and C8 himself: he lived all three in August and
September 2026, and the divergence between his own session and the synthetic one is
the cheapest calibration available.

---

## How to run it

```bash
# See exactly what would happen. No model is called.
python3 bench/personas.py --persona P4 --dry-run
python3 bench/personas.py --matrix pilot --dry-run

# The pilot, for real. Six sessions.
python3 bench/personas.py --matrix pilot

# One card, its probe, a different seed, on a specific launcher.
python3 bench/personas.py --persona P1 --probe --seed 2 --agent codex

# Every persona, both variants, one seed.
python3 bench/personas.py --matrix first --agent claude

# Re-apply the checks to sessions already paid for. Nothing is re-played.
python3 bench/personas.py --regrade bench/results/personas-2026-09-06
python3 bench/personas.py --regrade bench/results/personas-2026-09-06 --rules-only
```

Useful flags: `--agent claude|codex|chat` (default: whatever the card's own tech block
says), `--persona-agent auto|claude|codex` (default `auto`, which crosses the
families), `--model`, `--persona-model`, `--judge-model`, `--day`, `--results`,
`--workdir`, `--keep`, `--rules-only`.

### What lands where

```
bench/results/personas-<date>/
  transcripts/<persona>-<variant>-s<seed>.md     the whole dialogue, with the controller's events
  cards/<persona>-<variant>-s<seed>.json         the judge card
  scorecard.json                                 one row per session
  scorecard.md                                   the same rows, readable
```

The transcript is the record of what was said. The card is the record of what it was
worth. `--regrade` reads the transcripts back and rebuilds the cards, so a
calibration fix reaches sessions that have already been paid for.

---

## Adding a persona

1. Write the card in `evals/personas.json`: the situation, the documents with a
   release turn or trigger, the unknowns, the fears, patience, tech, settings, one
   probe, three success criteria as full sentences, three failure modes, at least two
   frictions with turns, things this person would never say, at least one cooperative
   moment, the opening message, and which safety lines apply.
2. Write every document it names as a text file under
   `evals/personas/fixtures/<id>/`. Fictional, dated, postcodes starting with X,
   invented company names.
3. Run `python3 -m unittest tests.test_personas -q`. The dataset guards will tell you
   what is missing before any model is called.
4. Dry-run it: `python3 bench/personas.py --persona <id> --dry-run`.

Roast the listing, never the person — 尻洗房源，不尻洗人。That rule holds for the
persona cards too: nothing in this material insults a landlord, an agent or a host,
and no card is a caricature of the people it stands for.
