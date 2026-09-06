# Document reading — test bed

Part of Pea Princess (vet-flat) — https://github.com/jacky18008/pea-princess — CC BY 4.0

The ablation behind `scripts/find.py` — full read vs grep-only vs a BM25 "thick view" tool vs fixed
regexes, on cheap and strong models — is graded against a **private** corpus, not in this repository
and never published. Every case is a real page saved during the maintainer's own London flat search,
de-identified: invented building, street, company and reviewer names, X-prefixed postcodes, rewritten
references, emails and URLs. Rents, dates, unit counts and distances stay verbatim because the answers
depend on them, leaving the corpus re-identifiable — so it stays out of git.

**Case types.** `reviews` (incentivised reviews, same-month bursts, organic averages) · `terms` (minimum
stay, cancellation, fees, licence-vs-tenancy) · `planning` (what is approved, distances, construction
period, conditions) · `listing` (deposit/term/bills in 100 KB+ of boilerplate) · `agreement` (clauses) ·
`shortlet` (a platform listing against what arrival really looked like).

**Gold schema** — one `gold.json` per case, so the grader stays deterministic:
```
{"id", "type", "file", "chars", "lines", "questions": [
  {"qid", "kind": "fixed|free", "fixed_id": "F1..F18"|null, "question", "question_zh",
   "answer": {"value","unit"} | {"text"} | {"list", "min_hits"?} | {"absent": true},
   "spans": [{"line_start","line_end","quote"}], "confidence": "high|medium", "note",
   "forbidden": ["regex a WRONG answer would match"]}]}
```

Every quote is verbatim at its stated lines, verified by script, and each case carries at least two
`absent` questions — pages often do not state a council tax band or a cancellation window, and inventing
one is the failure this bed catches. `fixed_id` follows `references/fixed-questions.yaml`.

**Public fixtures** for the finder live in `tests/fixtures/find/` — a listing, a planning officer's
report, a review page and a tenancy agreement. Those are synthetic and safe.
