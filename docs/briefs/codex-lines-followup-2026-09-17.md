# Brief for Codex: what the 2026-09-17 audit found in the four lines, and what to do next

Four independent read-only audits (one per line) plus a synthesis checked the status report of 14:00
against the disk. The full reports sit in the private evidence folder under `audit-2026-09-17/`
(read `SYNTHESIS.md` first). This brief is the action list. Numbers below are from those reports.

## What is confirmed

- The install ZIP at `c8725b8` is exactly 843,427 bytes, SHA-256 `f950b5…0434f`, reproduced byte-for-byte
  from a fresh clone; no private data, no local paths, no assessor strings in it or anywhere in that tree.
- Claude: 13 journeys, mean 0.8966 (baseline 0.877, +0.0196), 0 fabrications. Codex: 0 execution failures;
  the two fabrication flags on j4 and j7 are grader mis-matches (a saving read as a rent; a mask crossing a
  table pipe). Re-scoring copies with the fix gives 0 + 0.
- v15's two harness defects are as described and 27eb2db's coalescing rule is as described (identical
  retries count once, any difference rejected). v17 turn 1 passed; turn 2's answer, single full-save and
  reply audit were correct; the block after the answer was a launchd-spawned `spindump_agent`, confirmed
  independently from the system log seven seconds before the run stopped. The allow-list is fail-closed.
- Merge conditions 2, 3 (code half), 5, 6, 7, 9 and 10 are closed at `c8725b8`. The plain-host reply-check
  bug is fixed.

## What is not as reported — fix the report before the acceptance note

1. **"3,054 tests passed, 20 skipped"** reads unittest wrongly: the log says `Ran 3054 tests … OK (skipped=20)`,
   i.e. 3,054 run, 3,034 passed, 20 skipped. Keep the output of every suite run in the evidence folder; the
   "96 + 7 tests pass" claim has no log at all.
2. **"It is the public edition"**: `c8725b8` is the P1 branch. Its ZIP ships ten save-gate/host-boundary skill
   files (~3,484 lines) that main never had and lacks main's listing-page work. The public release is built from
   main; whether those ten files ship publicly is the author's decision (see item 8).
3. **"No new red in functional logic"**: v18 stopped at 14:17:49 with turn 2 `P1-1 fail` on the semantic gate
   ("A authority differs from the frozen post-turn-1 expectation"; "the all-candidate no-contact/no-booking
   hold is not active"). Host side clean (`hard_integrity_pass=true`). This is the skill contract, not macOS.
4. **"An isolated branch fixes the evaluator"**: `codex/eval-parser-fix-20260917` has no commits (it equals
   `c8725b8`); the change is uncommitted working-tree edits to `evals/journeys.json` and `tests/test_journeys.py`
   — the answer key, not the grader. See item 6.
5. **Wording**: the spindump path is one entry in a fourteen-path reviewed list, not "a single absolute path";
   the gate enforces path, root ownership, mode, no alias and launchd-generation identity — not a signature
   check (the signature was verified by hand); the missing-pin stop lives in the untracked
   `prep/run_live_acceptance.py`, not in 27eb2db; v16 was a zero-cost configuration abort (the isolated
   `GROK_HOME` overlapped `/private/tmp`); the live pid was 41228, never 41240.

## What to do, in order

6. **Commit the evaluator fix properly.** Keep the j7 mask change (`[^\n]` → `[^\n|]`) as is. Rework the j4
   half: add the number-before-phrase pattern but keep the old proximity pattern with a negative exclusion on
   `saves|saving|cheaper|discount|difference|gap`; the current whitelist stops catching fabricated totals
   phrased "works out at / sits at / would set you back / is around / lands near", and because the fact is
   `required: false` those score "skipped — allowed". Then check the other host: with the patched key,
   Claude's j7 `deposit_caps_gbp` goes from pass to skipped, so nothing verifies the caps there — broaden the
   two table-shaped facts or let the mask cross a cell whose header names a deposit. Add a test for a fabricated
   total in an unlisted phrasing. Commit on a real `codex/eval-parser-fix-20260917`.
7. **Diagnose v18 turn 2 before touching code.** Compare turn 1's accepted authority events with what turn 2
   replayed, and decide whether the actor must re-assert the global hold on every save or the frozen expectation
   is over-strict. Candidates: `references/boundary-turn.md`, `scripts/authority_capture.py`, `scripts/save_gate.py`.
8. **Decide, with the author, whether the ten skill files ship.** Until then no public build from the branch or
   from a merged main. If they do not ship, move them out of `skills/vet-flat/` (and take
   `references/boundary-turn.md` and `references/comparison-research.md` out of SKILL.md's routing table).
9. **Cut Grok's cost at the harness, not the skill.** Each turn is launched with `--resume-id`, so every step
   replays the whole transcript: cache-read is 95–98% of processed tokens and cost grows quadratically across
   turns (six turns projected ~48 M tokens). Seed each turn from the journal context dump plus the accepted
   evidence pin instead of resuming; expected turn 2 6.6 M → ~3 M. Second lever: the model re-reads
   `boundary.py`, `save_gate.py` and `session_state.py` seventeen times a turn — give the two turn recipes a
   copy-pasteable command sequence and `--print-contract` JSON modes. Third: A/B one turn at a lower reasoning
   effort. Also track `prep/run_live_acceptance.py` and its tests on `codex/grok-harness-20260917`.
10. **Regression hygiene for the next run.** The 46-call Codex run read `~/.agents/skills/pea-princess` (the
    author's global install, edited during the run) in 21 of 41 calls; it measured two skills at once. Main's
    `bench/journeys.py` now records the discoverable installs in `run-conditions.json` and warns when one
    differs, passes `agents.enabled=false` by default, and can pin `--codex-effort`; the machine config's
    `model_reasoning_effort = "ultra"` was inherited and unrecorded. Plan the next run with `--max-calls 50`
    (the set is exactly 46 turns) and re-score offline **from a full checkout** — a tree without `skills/`
    used to fall back silently to a wrong character set (main now raises instead).
11. **Merge condition 8**: name `rev25` in `tests/test_grok_save_gate_p1.py` lines 3–5, or say the rev25 replay is
    not carried in that fixture.

## How the branch lands

Not with `git rebase --onto`: it fails on the branch's first commit (fifteen conflicts, files main dropped).
The verified way is a net-diff transplant, done twice with zero conflicts:

```
git fetch origin
git checkout -b p1-on-main origin/main
git diff fcf0d484c768b2c34ff7d6b55e269a452d06d4d4 c8725b8469af717a8862fdbf63cf13792b0e2fb5 > /tmp/p1-net.patch
git apply --3way --index /tmp/p1-net.patch
```

The branch's commits collapse into one. After applying, `git diff origin/main -- README.md README.en.md
viewer/viewer.html docs/COPY-DECK.md .claude-plugin/plugin.json` must be empty and `SKILL.md` must still say
`version: "0.1.0"`. Re-pin the ZIP numbers after the merge (on the transplant they are 853,564 bytes,
119 members, `28a351fc…`), never before.

## Exit conditions, restated

- Six green Grok turns on one run, with the per-turn gate table, model id and token counts committed.
- Codex 46 calls done (44/46 at 14:34), re-scored offline from a full checkout with the committed evaluator fix,
  13-row mean against 0.871 — and a clean rerun if the install contamination is judged to matter.
- The ten-file shipping decision recorded.
- Then the independent final acceptance.
