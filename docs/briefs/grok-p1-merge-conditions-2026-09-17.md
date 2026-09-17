# Brief for Codex: what `codex/p1-trial-merge-20260916` still needs before it lands on main

Reviewed 2026-09-17 against `docs/briefs/grok-save-gate-p1-2026-09-16.md` (head 01e082f, 16 commits,
+19,954 / −213 lines, 58 files; fast-forwardable from main fc5c1d8; full suite green; pack 7,987).

## What is accepted as done

All five P1s are fixed in host-side code, each with the named offline tests:

| P1 | Where | Tests |
|---|---|---|
| 1 research / viewing / outbound authority, false by default | `boundary.py` (AUTHORITY_FIELDS, projection at ~528, TODO gate ~559) | `test_boundary_authorities.py`: research-only candidate never becomes viewing/outbound; message without candidate wording leaves every field false |
| 2 "before 09:00" MUST split from "≈45 min" PREFER, strict `<` | `requirement_capture.py` (split_mixed_commute, validate_mixed_capture, arrival_satisfies table) + ranking binds unresolved hard checks (`boundary.py` ~508–564) | `test_grok_save_gate_p1.py`: mixed sentence → two rows; exactly 09:00 fails "before" and passes "by"; collapsed capture rejected with the quote |
| 3 journey fact bound to stop id + mode set | `save_gate.py` (_check_journey_fact, _check_arrival_fact, _check_destination_resolution) via `commute_compare.match_journey_fact` | wrong mode tuple rejected naming both receipts, correct rail tuple passes |
| 4 host-owned receipts, model cannot mint source ids | `_fetch.py` (record_host_receipt / load_host_receipts, "unverifiable here" without the wrapper), `save_gate.py` (_check_host_binding, _check_user_binding), `host_tool.py` | source without receipt rejected; receipt passes and a one-byte edit fails |
| 5 saved/current recomputed, fail closed, pre-send block | `save_gate.py --scope current`, `session_state.py` context packet `save_status`, `reply_check.py` save_status_missing / save_status_stale | reopen reports 42→44 then refresh is current; stale "已存好" blocked with the delta |

The go-ahead rule, the `decision` kind and onboarding.md are untouched. Good work: the design is the
brief's, and the tests assert the brief's conditions.

## Why it does not land yet — four pass conditions still open

1. **The Grok six-turn rerun on the fixed package is missing.** The branch ships the tooling
   (`tools/grok_p1_turn_audit.py`, `tools/grok_elastic_probe.py`) but no report: no per-turn gate
   table, no model id, no token counts. This was a pass condition. Run it on your frozen protocol and
   commit the report; unknown stays unknown.
2. **The public skill's entry file lost a contract sentence and gained machinery talk.** SKILL.md's
   Output paragraph no longer says "read `references/conversation-quality.md` before replying: first
   visible sentence polished and useful", and now tells the model "a managed host uses
   `scripts/host_client.py`; the actor never signs receipts. Saved sources and next steps need the
   `comparison-full` gate". Rule 6 of the contract is "never talk about the machinery"; the entry file
   must not make the model do it, and most installs have no controller, so the gate sentence tells
   them they may never say a comparison is saved. Restore the contract sentence; move the
   controller/gate wording into `references/session-harness.md` (read on demand), phrased as "where a
   host controller exists, …; otherwise say the save is not machine-verified here". Pack stays ≤ 8,000
   without trimming other contract sentences; report the number.
3. **Out-of-scope subsystem rides along.** `tools/grok_elastic_probe.py` (2,519), `grok_auth_broker.py`,
   `grok_auth_client.py`, `grok_p1_turn_audit.py`, `tools/source_controller.py` and ~3,200 lines of
   their tests are a macOS-specific Grok harness, not one of the five P1s. Put them on their own
   branch with their own brief; the P1 branch keeps only what the five fixes need. Same for the
   `AGENTS.md` startup switch (`context` → `navigation`) and the `session_runner.py` / `session_hook.py`
   changes that follow from it: revert them here, or justify them in a separate brief.
4. **Regression on the two verified hosts.** The skill text the model reads changed (+4 lines in
   conversation-quality.md, new references, the Output line, +6,300 lines of scripts in the ZIP).
   Before the merge, run `bench/journeys.py --all` on Claude Code and Codex on the branch and compare
   with the current baselines (Claude 0.877 / Codex 0.871 mean; the author's line is ±0.03 and no new
   fabrications). Watch j12 turn 4 and j9 in particular: on a plain host with no controller the reply
   must still say the comparison was saved as a file and that the save is not machine-verified here —
   not refuse, not go quiet.
   Verified on the branch today: `reply_check.py` on a plain host (no `save_status` from any controller)
   flags the sentence 「比較已存好，可以繼續。」 as `claims/save_status_missing` (ok: false), so a Claude Code
   Stop hook would block a truthful "I saved the file" on every ordinary install. The checker must
   distinguish "saved as a file, not machine-verified here" (allowed, and the words to use) from a claim
   of a verified save (needs the status); a plain host is the common case, not the exception.

## Smaller named changes (from the review; all cheap)

5. Restore the removed `reply_check.py` docstring sentence ("Even a short Go is not a linter
   authorization to act or a blanket prohibition on questions") — the behaviour is right, keep the caution.
6. `tests/test_grok_elastic_probe.py:605`: replace `/private/tmp/pea-grok-p1-home-20260916/…` with a
   synthetic placeholder (no local absolute paths in public files).
7. Revert the edit to `docs/briefs/grok-save-gate-p1-2026-09-16.md`: propose changes to a brief in
   your report, never on the branch graded by it.
8. Say in the test docstrings that the "sealed" rev25 / rev42 / rev44 snapshots are reconstructed from
   revision numbers and quotes with synthetic padding events, or make them real journal bytes.
9. `tests/test_boundary_projection_guards.py` and `tests/test_boundary_user_instructions.py` import
   `test_boundary_turn` directly, so they only load under `discover`; make them importable as modules.
10. Decide, with a sentence in `docs/SCRIPTS.md`, whether `host_tool.py` and `host_client.py` belong in
    the shipped skill or in `tools/`; if they ship, the skill must behave identically without them.

## What "lands on main" means

- Items 1–10 done on the P1 branch, full suite green, pack ≤ 8,000 with the contract sentences intact,
  private strings clean.
- The journeys regression (item 4) inside the line on both hosts, and the Grok report (item 1) committed.
- Then a fast-forward or a plain merge — no partial takes this time; the P1 branch should be mergeable
  as a whole once the out-of-scope subsystem is on its own branch.
