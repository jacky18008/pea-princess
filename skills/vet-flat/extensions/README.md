Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Personal add-ons: your own little secretary

The public skill checks what every renter needs and stops there. Anything personal,
local or contestable — a number you want that the skill does not offer, a source you
trust, a rule that is yours — goes here, in your copy, and stays out of the shared skill.

## How it works

1. Copy `_template.md` to a new file in this folder, e.g. `gym-distance.md` or `school-run.md`.
2. Fill in the five headings. Keep the source open or your own; say what the number means.
3. The skill reads every `*.md` in this folder except `README.md` and `_template.md`, at the
   start of a session, after `SKILL.md`. Each add-on becomes one extra check on every
   candidate, reported under **Personal add-ons** with its source and date.

## The rules an add-on keeps

- **It never changes a verdict code.** An add-on can add a line, a number and a question
  for the viewing day; the verdict (PASS / CONDITIONAL / EDGE / FAIL) comes from the
  shared axes only, unless you write `verdict: mine` in the add-on and accept that the
  report says so.
- **It is labelled.** Every finding from an add-on carries `(personal add-on: <file>)`.
- **It reads only what its own source allows.** No listing sites, no review sites; the
  open-register rule of the main skill applies to add-ons too.
- **It does not sort people by protected characteristics.** An add-on that ranks areas by
  ethnicity, nationality, faith, disability or the like is not one the skill will run.
  Everything else that the shared skill deliberately leaves out — an income or benefits
  statistic, a reputation you have heard, a rule of thumb of your own — is exactly what
  this folder is for: your call, in your copy, labelled as yours, never in the verdict.
- **It is yours.** Nothing in this folder is shared, uploaded or stored anywhere but your copy.

## Things people add

- Walking distance to a specific gym, pool, climbing wall, allotment, place of worship.
- A school's catchment or a nursery's waiting-list rule.
- A noise source they know: a venue's event nights, a flight path, a night bus stand.
- A personal threshold: "no flat above the fourth floor without a lift I have ridden".
- A data set the skill does not ship: a council's own noise-complaint map, a river-level gauge.

## What an add-on looks like

See `_template.md`. Five headings, plain sentences, one source, one way to read the number.
An add-on with a script follows the same shape as the skill's scripts: standard library,
one JSON object out, `source_url` / `retrieved_at` / `ok` / `evidence_class` in the envelope.
