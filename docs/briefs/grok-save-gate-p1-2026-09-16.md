# Brief for Codex: the five P1s in the boundary / save-gate machinery — what to fix, how, and what counts as a pass

Scope: branch `codex/grok-postbaseline-integration-20260916` (and its v4 ancestors). Main took the
honest-data fixes from it on 2026-09-16 (area-scan radius, noise, doctor, commute, the council-tax
null-total set, reply_check refinements, reproducible ZIP) and left `scripts/boundary.py`,
`scripts/save_gate.py`, the `eligibility.py` bounded exceptions, the `session_state.py` batches and
their four references (`boundary-turn.md`, `boundary-api.md`, `comparison-fidelity.md`,
`comparison-research.md`) on the branch. They come to main when the five P1s below pass their own
acceptance tests, on the branch, with the tests committed. The P1s are the ones your own report
names (`docs/grok-round2-2026-09-15/patched-full-journey-results-2026-09-16.md`, severity table);
this brief turns each into a design, a smallest fix and a pass condition. Two rules for all five:
the fix lives in the host-side code (`boundary.py`, `save_gate.py`, `session_state.py`), never in a
sentence the model is asked to obey; and every pass condition below is an offline unittest that
replays a sealed snapshot — no Grok, no Codex, no Claude call is part of the acceptance.

## P1-1 — research authority became viewing authority

**What broke.** With no explicit hold on B, the review projected B `viewing_allowed:true` and a TODO
`viewing_permitted` during a research-only turn; the person had authorised research on B and had
said "do not contact or book".

**Design.** Three separate authorities per candidate, each false until an exact positive quote from
the person grants it: `research` (look things up), `viewing_consideration` (may be treated as a
candidate for a viewing), `outbound` (contact an agent, book, pay). A global "do not contact or
book" is a negative authority that overrides any candidate-level `outbound` until the person
withdraws it in their own words. Absence of a hold never means permission: the default for all
three is false, and the review must derive `viewing_allowed` from `viewing_consideration`, never
from "no hold recorded".

**Smallest fix.** In `boundary.py`, replace the single consent flag with the three-field authority
record on each candidate event; make the projection compute `viewing_allowed = authority.viewing_consideration` and `outbound_allowed = authority.outbound and not global_no_outbound`; make the TODO
generator emit `research` tasks for a research grant and never a `viewing_permitted` action unless
`viewing_consideration` is true. Every grant event carries the exact quote and the user-message
revision it came from.

**Pass.** A test replays the sealed rev25 journal (turn 2: "A only consider viewing; continue B
research; save; no contact") and asserts: A `viewing_consideration=true`, B `research=true`,
B `viewing_consideration=false`, both `outbound=false`, `global_no_outbound=true`; the TODO list has
a B research item and no viewing invitation; rev42 (turn 5) still shows the same holds. A second
test feeds a message with no candidate wording at all and asserts every authority stays false.

## P1-2 — a mandatory "before 09:00" was folded into a negotiable 45-minute preference

**What broke.** The person wrote "平日要在 9:00 前到 London Bridge Station，通勤希望在 45 分鐘左右，但可以再談".
The journal has one `commute-london-bridge` row with `strength:prefer` and `commute_minutes <= 45`;
there is no separate strict-before-arrival MUST row, and `save_gate.py` (line ~185) tests
`<= 09:00`, which lets an arrival at exactly 09:00 pass a "before 09:00" rule.

**Design.** One sentence from the person can carry two requirements of different strength. The
capture step must split them: `arrives_before: 09:00` with `strength: must` and predicate
`arrival < 09:00` (strict), and `commute_minutes <= 45` with `strength: prefer` and the
"negotiable" flag. A capture that produces a single row from a sentence that contains both a hard
word (要, 必須, must, before) and a soft word (希望, 可以再談, prefer, negotiable) is rejected at save
time with the sentence quoted back. The ranking binds to the full set of hard checks; an unresolved
hard check (arrival unknown) is a research TODO, not a pass.

**Smallest fix.** In the capture parser: a strength classifier per clause, not per sentence; in
`save_gate.py`: the predicate for "before" is strict `<`, "by" is `<=`, and both forms are covered
by a table, not an ad-hoc comparison; in the review: a candidate with any unresolved hard check
cannot be ranked above one with all hard checks resolved.

**Pass.** Three tests: (a) the sentence above yields two rows with the strengths and predicates
stated; (b) a plan arriving at exactly 09:00 fails the `before 09:00` row and passes a `by 09:00`
row; (c) capturing the sentence into one `prefer` row raises with the quote in the message.

## P1-3 — a 28-minute Underground plan was saved under the Rail scope

**What broke.** The saved evidence carries B `commute_minutes:28` with
`scope.destination_id: london-bridge-rail-station`, while the actual Rail plan to that station was
30 minutes arriving 08:36; the 28 was the all-mode plan to the Underground station. The
structural gate (`comparison-full`) passed because the hashes matched.

**Design.** A journey fact is a five-tuple (origin, resolved destination stop id, mode set,
duration, arrival), and the scope key of the requirement it answers must match the destination
stop id and the mode set of the raw plan it came from. The gate checks semantics, not only bytes:
for every journey fact, find the raw TfL receipt it cites and compare the tuple; a mismatch is a
gate failure with both tuples printed.

**Smallest fix.** `commute_compare.py` already audits receipts by mode and endpoint; call it from
`save_gate.py` for every journey fact and refuse the save when the cited receipt's destination stop
id or mode set differs from the fact's scope. Store the resolved stop id (the `1000139`-style id)
on the fact, never the free-text place name.

**Pass.** A test replays the sealed rev42 evidence and asserts the gate rejects B's 28-minute fact
with a message naming the Rail receipt (30 min, 08:36) and the Underground receipt (28 min); after
the fact is rewritten to cite the Rail receipt, the gate passes.

## P1-4 — the model can write its own evidence file and satisfy the hashes

**What broke.** `evidence.json` and the `actor` source label are model-written; a plausible
projection with consistent hashes passes the structural gate although no host observation backs
it.

**Design.** Provenance is host-owned. The host (the runner, the hook, or the script wrapper the
skill ships) records every tool response as an immutable receipt — URL, status, time, byte length,
SHA-256 of the body — and allocates the source id. The model may cite a source id; it cannot create
one. A user-facing fact or unknown without a host receipt behind it cannot be part of a full save;
partial fetches are disclosed as partial.

**Smallest fix.** Route every register call the skill makes through one thin wrapper in
`_fetch.py` that appends the receipt to `.pea-state/receipts.jsonl` (append-only, host-side);
`save_gate.py --scope comparison-full` requires each cited source id to resolve to a receipt line
and each fact's value to be derivable from that receipt's body hash + a recorded extraction (the
JSON path or the script name and arguments). Reject an `evidence.json` that names a source id with
no receipt.

**Pass.** Two tests: (a) an evidence file citing a source id that has no receipt is rejected;
(b) the same file with the receipt present passes, and editing one byte of the receipt body hash
makes it fail. On hosts that cannot run the wrapper (no shell), the gate returns
"unverifiable here" and the reply says so; it never returns pass.

## P1-5 — the reopened session claimed a current comparison while its checkpoint was stale

**What broke.** After the clean reopen (turn 6), the journal was at rev44 but the saved review and
checkpoint stayed at rev42; the terminal answer continued the comparison while the current
`comparison-full` gate rejected it.

**Design.** "Saved" and "current" are computed, not remembered. Before the reply may say the
comparison is saved or continued, the host recomputes review, pending TODO and checkpoint for the
current revision; if any receipt is older than the journal head, the gate fails closed and the reply
must say "the last saved state is rev N; since then: …" with the delta listed. The restart path runs
the same recomputation before its first reply.

**Smallest fix.** `save_gate.py --scope current` that compares journal head revision, checkpoint
revision and review revision and returns the delta; `session_state.py context` includes that delta
at the top so the reply cannot miss it; a stale delta blocks the words "saved" and "continued" in
the pre-send check (a `claims` finding with the delta quoted).

**Pass.** A test replays the sealed post-turn-6 snapshot and asserts `current=false` with the
rev42→rev44 delta listed; after regenerating review and checkpoint at rev44 the same call returns
`current=true`. A second test asserts that a reply containing "已存好" while `current=false`
trips the pre-send check.

## What "pass" means for the whole set

- All ten tests above committed on the branch, offline, run by `python3 -m unittest discover`,
  green together with the existing 3,000.
- The full suite on a trial merge into main stays green and the manual pack stays ≤ 8,000 (the two
  route rows the branch adds do not fit today: fit them by merging into existing rows, not by
  trimming contract sentences).
- One more Grok Bot six-turn run on the fixed package, on your own frozen protocol, with the five
  gates reported per turn — and the honesty rule of your own reports kept: unknown stays unknown.
- Nothing private in public files: no real address below postcode district, no live listing URL, no
  local absolute path (main scrubbed these on 2026-09-16; keep it that way).
