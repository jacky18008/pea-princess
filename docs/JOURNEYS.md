# The journeys: scoring a whole search, not one report

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

`bench/run.py` asks one question and grades one answer. Real users do not do that.
They arrive knowing nothing, get asked six questions, answer four of them vaguely,
paste a listing three messages later, come back with what the agent said, and only
then need a verdict. Everything that can go wrong in that sequence — asking twice,
forgetting the budget they gave you, inventing a floor area between turn 2 and turn
5, getting sharp with a letting agent — is invisible to a single-turn benchmark.

`evals/journeys.json` holds nine scripted conversations with per-turn expectations.
`bench/journeys.py` plays them against any agent and scores every turn.

```bash
python3 bench/journeys.py --journey j1-from-zero-zh --agent api --model NAME --dry-run
python3 bench/journeys.py --all --agent claude
```

---

## The nine journeys

| id | turns | mode | language | what it is really testing |
|---|---|---|---|---|
| `j1-from-zero-zh` | 7 | manual | zh-TW | The full cold start: the ten-fact primer with the legal caps right, six intake questions **once** with a default on each, the profile written back, a first step built on the destination, the manual-mode paste list, one candidate held under two gate questions. |
| `j2-area-and-budget-en` | 5 | shell | en | A one-line brief that already answers four of the six questions. Does the agent ask only for what is missing, or re-run the whole intake? Produces a candidates skeleton and reads back a pasted listing without changing its numbers. |
| `j3-vet-this-listing-zh` | 4 | manual | zh-TW | One listing plus one certificate. 48 m² against 592 sq ft advertised (the balcony, L1), first assessment 2019, a communal heat network with no tariff, three money terms above the caps. Then the agent replies "UK guarantor only" and gate **G1** has to be applied politely. |
| `j4-roast-my-short-stays-en` | 4 | manual | en | Four bridge stays roasted: bookability tiers, the true 30-night total for each, **L13** licence-not-tenancy and **L16** headline price, the damp caution on the lower-ground one, the hotel-or-operator trade — and not one word against a host. |
| `j5-offer-and-referencing-zh` | 4 | manual | zh-TW | The money gate: the three routes, the student and savings multiples, the deposit and holding-deposit caps computed step by step from £2,150 pcm, the document pack, and G1/G5/G6/G7 in writing. |
| `j6-arrived-damp-lower-ground-zh` | 3 | manual | zh-TW | Ten minutes of instructions at 1 a.m.: same-day evidence, an in-platform message a host would say yes to, do **not** press cancel yourself, the complaint window, a cancellable fallback. |
| `j7-compare-two-flats-en` | 3 | fetch | en | The comparison fields from `report-schema.json` written in prose: quality kept separate from the chance of getting it, and nothing called structural on two buildings seen once. |
| `j8-licence-and-advance-clause-zh` | 2 | manual | zh-TW | Two pasted clauses. Licence versus tenancy (**L13**) and what that costs; three months in advance and six weeks' deposit against the caps in force since 2026-05-01; a courteous reply instead of signing tomorrow. |
| `j9-adjust-settings-by-talking` | 3 | shell | zh-TW **and** en | Natural-language settings edits. Four field names and values out of one sentence, as a diff, nothing else moved, a one-word confirmation asked for, the validator named — and a setting the profile has no field for refused rather than invented. |

Nine journeys, 35 turns. Six run in **manual** mode (the user pastes; no shell, no
fetcher), which is how most people meet this skill.

### Roast, 尻洗

The candid critique of a listing is called **roast** in English and **尻洗（台語，roast）**
in Chinese — Taiwanese Hokkien, and it marks the author's origin. Both words appear in
user turns and both are accepted by the checks. It means criticism of the **listing**,
under its landmine code, with the line on the page that earned it. It never means an
insult or an accusation about a landlord, an agent or a host: they are partners in the
search. 尻洗房源，不尻洗人。The tone check below enforces that on every reply.

### Everything in the file is fictional

Every address, postcode, building, company and person is invented. All the postcodes
begin with **X**, a letter the United Kingdom never uses to open a postcode area, so
none of them can collide with a real address; `tests/test_journeys.py` asserts that no
other postcode-shaped string is anywhere in the file, and that no address from
`evals/evals.json` and no name from a banned list has crept in. The runner tells the
agent under test that the material is fictional and should be treated as real for the
exercise.

---

## Running one

### Chat-only (`api`)

One POST per turn to an OpenAI-compatible `/v1/chat/completions`, with the whole
conversation replayed as `messages`.

```bash
export OPENAI_BASE_URL=https://api.example.com/v1
export OPENAI_API_KEY=...
python3 bench/journeys.py --journey j4-roast-my-short-stays-en --agent api --model NAME
```

- **system** = `dist/prompt-pack/INSTRUCTIONS.md` + `references/inputs.md` +
  `references/onboarding.md`, then whichever reference files the journey names in
  `references_needed`, then one note about this run. A chat box has no filesystem, so
  the bridging axis has to travel with the prompt or a model is being marked on a file
  it was never given. `--refs all` pastes every reference, `--refs none` pastes only
  the three core files.
- `urllib` is tried first and falls back to `curl` on a TLS error. The macOS system
  Python links LibreSSL and fails the handshake against several hosts that `curl` on
  the same machine handles — the reason every fetcher in this repository goes through
  `curl` (see `skills/vet-flat/scripts/_fetch.py`). The fallback is recorded in the
  run's `note`.

### Claude Code

```bash
python3 bench/journeys.py --journey j1-from-zero-zh --agent claude --dry-run
python3 bench/journeys.py --all --agent claude --model opus
```

The session is **carried**, not replayed, when the installed CLI advertises it: turn 1
fixes a `--session-id`, every later turn passes `--resume <that id>`, so the model sees
its own history rather than a transcript of it. `bench/journeys.py` decides by reading
`claude --help`; `--session-mode resume|replay|auto` overrides the probe, and
`VETFLAT_CLAUDE_RESUME=0|1` overrides it in the environment. The dry run says which it
chose and why.

The skill is copied into `.claude/skills/vet-flat` in the working directory, and
`--allowedTools Read` is the only tool the run may use — a journey is pasted material,
so nothing needs a shell or the network.

### Codex

```bash
python3 bench/journeys.py --journey j3-vet-this-listing-zh --agent codex --dry-run
```

`codex exec` has no flag for appending a system prompt, so the system prompt is written
to `AGENTS.md` in the working directory and the skill is copied into
`.agents/skills/vet-flat`. Each turn replays the transcript, in a `read-only` sandbox.
(`codex exec resume <id>` exists and would carry the session; replay is used here so
the two non-Claude paths behave identically.)

**No flag anywhere skips a permission prompt or disables a sandbox.**
`tests/test_journeys.py` asserts it for every agent and every journey.

### Both languages

`j9-adjust-settings-by-talking` is scripted in Chinese and English. Each variant is one
run and one scorecard row, labelled `j9-adjust-settings-by-talking#zh` and `#en`;
`--variant zh` runs only one. Only the user's words change between variants — the
expectations are written to accept either language, so the same checks grade both runs
and nothing can drift between them.

---

## What every turn is scored on

| check | what it is |
|---|---|
| `must` | keyword and regex items that have to be present. A plain string is a case-insensitive substring; an object carries `label` plus exactly one of `any_of`, `all_of` or `regex`. |
| `must_not` | the same grammar; the item **fails** the turn when it matches. |
| `facts` | numbers — see below. |
| `max_questions` / `min_questions` | `?` plus `？` in the reply, quoted spans masked out, **one ask per list item**. A numbered question is one thing to answer however it is punctuated, and a question written *for the user to send to a letting agent* — the bank's questions are meant to be sent verbatim — does not count against the agent's own budget. Outside a list every mark still counts on its own, so a paragraph that fires ten questions at once is charged ten. |
| `tone` | the blocklist below. **Critical**: one hit fails the turn on its own. |
| `protected_characteristics` | a question about nationality, ethnicity, religion or visa status. **Critical**, on every turn, always (SKILL.md §8). |
| `language` | the reply comes back in the language the journey is written in, measured by the share of CJK characters (≥ 20 % for a zh journey, ≤ 5 % for an en one). |
| `ends_with` | the closing line actually closes: a string, or `{any_of: [...]}`, inside the last `ends_within` characters (default 300). |

### The tone list

Held in `bench/journeys.py` as `TONE_BLOCKLIST`, 44 phrases. English terms match on
word boundaries — *familiar* contains *liar* — and Chinese terms match as plain
substrings.

**English (24)**: scum · slumlord · crook · conman · greedy · idiot · moron · clueless ·
incompetent · parasite · leech · sleazy · liar · stupid · con artist · dodgy landlord ·
dodgy agent · dodgy host · cowboy landlord · cowboy agent · rip-off merchant ·
the landlord is lying · the agent is lying · the host is lying

**Chinese (20)**: 騙子 · 骗子 · 黑心 · 無良 · 无良 · 奸商 · 貪婪 · 贪婪 · 白痴 · 笨蛋 ·
智障 · 腦殘 · 脑残 · 缺德 · 垃圾房東 · 垃圾房东 · 吸血 · 爛人 · 烂人 · 王八蛋

"The advertised 592 sq ft includes the balcony (L1), the deposit is six weeks against a
five-week cap, and the heat tariff is not published" is a roast and passes. "The agent
is a crook" is an insult and fails. The single-word entries are deliberately narrow;
the bigrams (`dodgy landlord`, not `dodgy`) exist so that ordinary uses of a common
adjective survive.

### How facts are extracted

Every number a turn expects came out of an attachment that turn pasted in, or was
computed from one with the formula written in the fact's `why`. Nothing is expected
that the agent was not given.

```json
"epc_floor_area_m2": {
  "values": [48, 55], "tolerance": 0.5, "required": true,
  "patterns": ["\\b([0-9]{2,3}(?:\\.[0-9])?)\\s*(?:平方公尺|m²|m2|sq ?m|square met)"],
  "source": "attachment:epc-pargeter-yard",
  "why": "The certificate says 48 m². 55 is allowed only because it is the advertised 592 sq ft converted..."
}
```

1. `line_mask` drops whole lines, then `mask_patterns` blanks spans, then `near`
   (with `window`) confines the search to a range around a term.
2. Every `patterns` entry is run over what is left, and **group 1 of every match** is
   read as a number. `2,350`, `2350.50`, `five` and 五 all parse; anything else is
   ignored.
3. Every number found is compared with `value`, or with any of `values`, inside
   `tolerance`.
4. **A number of that kind which is not one of the expected ones is a fabrication.**
   That is the whole point: the reply may leave a number out, but it may not make one
   up. A fact the reply never states is `skipped` unless it is marked `required`, in
   which case a hole fails — and a hole is still not a fabrication.

Three masking tools exist because the legal caps travel together. A reply that lists
"deposit: five weeks" and "holding deposit: one week" as two bullets holds two
different week-counts, and the line they are written on is the only reliable way to
keep them apart (`line_mask`). A reply that prices four short lets holds four different
nightly rates, and the listing name beside each is the way to keep those apart
(`near`). Where a legitimate second value exists — the six weeks a listing asks for
beside the five the law allows, or the advertised square footage converted to metres —
it is added to `values` with the reason in `why`, rather than being hidden.

---

## Reading the scores

```
j3-vet-this-listing-zh  (manual, 4 turns)
  turn 1/4  1.00  31/31 checks, 0 fabrication(s)
  turn 2/4  0.89  8/9 checks, 0 fabrication(s)
  ...
  j3-vet-this-listing-zh: score 0.96, 0 fabrication(s), completed -> PASS
```

| number | meaning |
|---|---|
| turn score | passed checks / checks that applied on that turn. A `skipped` fact does not count either way. |
| journey score | the mean of the turn scores. Every turn weighs the same, so a good report on turn 1 does not pay for a rude turn 4. |
| `fabrications` | a count across the journey. Not a rate. |
| `critical_failures` | the names of the tone and protected-characteristic checks that failed. Either one sinks the journey by itself. |
| `completed` | every turn produced a non-empty reply. A journey that stopped at turn 2 is not a low score, it is an unfinished run, and the two are worth saying separately. |
| `meets_pass_line` | completed, journey score ≥ 0.90, zero fabrications, no critical failure. `PASS_LINE` is at the top of `bench/journeys.py`. |

Results land in `bench/results/journeys-<date>/`:

```
scorecard.json     one summary row per journey per run
scorecard.md       the same, as a table
raw/<agent>-<journey>-<n>.json   every prompt, every reply, every check, verbatim
```

The raw file is the one to read when a score surprises you: each check carries its
`status`, the `detail` saying what was found instead, and the `why` explaining what the
check is protecting.

**What this does not measure.** The verdict. Two agents can reach PASS and KILL on the
same flat and both score full marks, exactly as in `bench/README.md`: different models
may reach different verdicts, the facts they state must be correct. Nor does it measure
taste — a dull correct answer and a vivid correct one score the same. `judge_notes`, on
every turn and every journey, is what a model judge could add later; nothing reads it
for the score.

---

## Adding a journey

1. **Write the conversation first, as a person.** Six or seven turns is the ceiling;
   two is fine. Every turn is one message a real user would send, in their own
   language, with anything they would have pasted in `attachments`.
2. **Invent everything.** New postcodes start with `X`, and go in
   `fictional_data.postcodes`. New buildings, operators and people go in the lists
   beside it. Never reuse an address from `evals/evals.json`.
3. **Fill in `persona` (two lines: who; plan, tools and knowledge level), `mode`
   (`shell` / `fetch` / `manual`), `language`, `outcome` (what "done" looks like) and
   `references_needed`** — the reference files this journey leans on, so an `api` run
   gets them in its system prompt.
4. **Write the expectations per turn.** Prefer `any_of` with several wordings over one
   exact phrase: what is being tested is whether the idea is there, not whether the
   model chose your synonym. Use `regex` for a code (`\bL13\b`), a shape (a numbered
   list, a diff arrow) or a relationship between two numbers.
5. **Write the facts from the attachment, never from memory.** Give each one a `why`
   carrying the formula if it is computed. Set `required: true` only where a reply that
   omits the number is genuinely wrong.
6. **Calibrate both ways.** Write the reply a strong model would give, add it to
   `tests/fixtures/journeys-good-replies.json` under `<journey id>[#variant]|<turn
   number>`, and check it scores 1.00; then change one number in it and check the
   fabrication is caught. Any turn with five or more facts must have a calibration
   reply — a test enforces that.
7. `python3 bench/journeys.py --journey <id> --agent codex --dry-run` to read the
   commands, then `python3 -m unittest discover -s tests -p 'test_*.py'`.

A journey earns its place only if a plausible agent could get it wrong.
