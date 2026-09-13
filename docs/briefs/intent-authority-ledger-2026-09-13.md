# Brief for Codex — a condition is the person's only when we can quote them (2026-09-13)

Read this whole file, then `docs/handoffs/2026-09-11-evening.md` ("Context slimming" and the 09-13 sections)
and `docs/scan-intent-reliability-2026-09-13/results.md`. Work on a new branch; do not merge.

## The problem, as diagnosed

Terra (and sometimes the others) turns a preference into a requirement: "偏好安靜" became
"只有在臥室背向主幹道及鐵路、晚間實聽仍可接受時才值得". Three layers stack:

1. Tool text seeded the conditions (roads.py facade note; the area-scan "listen at the window at night"
   line; noise.py "which side the bedroom faces"). Fixed on main on 2026-09-13: tool JSON now carries facts
   only. Do not re-add advice sentences to any script output.
2. The skill's vocabulary frames judgement as gating: verdicts KILL / EDGE / CONDITIONAL "(conditions
   listed)", "hard filters", `must_haves`, and the profile has no place for "a check I propose". A model
   told to list conditions, with nowhere to put its own, writes them as the person's.
3. Run-to-run randomness: 2/6 vs 4/6 drift on three runs per cell cannot separate 30% from 60%.

Host-side gates (tools/playground_intent.py) catch some of it at publish time; they exist only in the
playground. This brief is the portable, skill-level fix plus the measurement that decides whether it ships.

## What to build (one branch: `codex/condition-ledger-2026-09-13`, from `main` at or after the commit
"reply_check: condition-authority check…" — check `git log --oneline -3` for it)

### 1. The condition ledger with provenance (profile + eligibility + panel)

- `skills/vet-flat/profile.template.yaml`: keep `must_haves`, `avoid`, `nice_to_haves` as they are for
  backward compatibility, and add two things:
  - `condition_sources:` a map from a condition line (exact text as it appears in `must_haves` / `avoid` /
    `limits`) to `{source: user, quote: "<the person's words>", turn: <n or timestamp>}`. Rule: a
    mandatory condition without a `user` source is not mandatory; `scripts/eligibility.py` treats it as a
    preference (non-mandatory) and says so in its output (`downgraded: [..]` with the reason
    "no user quote").
  - `proposed_checks:` a list of `{text, why, status: pending | accepted | declined, proposed_at, decided_at,
    quote}`; written by the assistant when it wants a condition; `status` changes only on the person's
    words (quote required). Accepted items are then copied into `must_haves`/`avoid` with a `user` source.
- `scripts/profile_check.py`: validate the new blocks; a mandatory line without a `user` source is a
  warning with the exact fix ("quote the person or move it to proposed_checks").
- `scripts/eligibility.py`: only `user`-sourced rows can set `mandatory: true`; the report of blocked
  candidates names the quote that blocked them.
- `scripts/panel.py` (the requirements page): two sections, "你的條件（有原話）" and "我建議先確認（待你決定）",
  never mixed. `scripts/session_state.py` (if it stores conditions): same two buckets.
- `references/requirements-contract.md`, `references/onboarding.md` (section 2b if it exists),
  `references/report-contract.md`: CONDITIONAL verdicts list *the person's* conditions by quote and
  *the assistant's proposed checks* separately, labelled; the verdict card wording says which is which.

### 2. The one text rule (small, in `references/conversation-quality.md`, checkpoint list)

Add one numbered rule: "**A condition is the person's only when you can quote them.** Write it with their
words (你說…). Everything else is your suggestion and is written as one (我建議先確認…); it goes to
`proposed_checks`, never into `must_haves`, and never as 必須／只有…才／排除／底線." Mirror one clause in
`references/rules.md` "Before sending" (the pack must stay ≤ 8,000 characters: `python3 tools/build_dist.py`).
Do not add a general reminder elsewhere; the earlier ablation showed a short rule beats a long one.

### 3. Measurement (before any merge)

The checker already counts the failure: `scripts/reply_check.py` kind `authority` (a sentence with
必須／只有…才／排除／底線／must／only if that quotes neither the person nor a proposal marker). Use it as the
programmatic metric, plus judge v2's G3 gate and the reviewers' "condition ownership" reading.

- Private replay (`bench/history_replay.py`, judge v2 pinned to Opus 5, `--inject-date`, `--claude-allow
  "Bash(python3 *),Bash(cd *)"`): 15 cases × ask turn × {Sonnet 5 standard, Codex terra standard} × 2
  repeats, arms `main` (current main) vs `ledger` (this branch, via `--skill-dir` on a `git archive` snapshot
  under `bench/ab/skill-variants/skill-<commit>`). Add `authority` to the report's programmatic columns
  (mean per reply) if it is not already there.
- Codex's two fixtures (`bench/fixtures/intent-authority/*.json`, quiet/window and area/commute/fees) × 3
  fresh conversations × 2 turns on terra low, same harness as the 2026-09-12 ablation, arm `ledger` vs
  `main`; report substantive condition errors and wording drift separately, as before.
- Cost: tokens per reply (Codex rows: account sub-agent threads with `bench/ab/account_codex.py` before
  quoting).
- Adopt gate: `authority` findings per reply down by at least half against `main` on both models; G3 pass,
  first sentence, task, satisfy not worse than the main-vs-main noise (use the 2026-09-12 round-2 numbers in
  `docs/EXPERIMENTS.md` as the noise reference); tokens within +5%; no fabricated cross-listing facts
  (the E2 class from the ablation). Otherwise: record and do not merge.

### 4. Version control and boundaries

- One commit per part (ledger schema + scripts; text rule; measurement), numbers in the commit message and in
  `docs/EXPERIMENTS.md` (a new section "Condition ledger (2026-09-13)").
- Do not touch: `../pea-princess-ctx-a`, `../pea-princess-ctx-c` (worktrees), `bench/private/durable/`
  (sweeps running), `tools/persona_playground.py` and `tools/playground_*.py` (the host gates stay as they
  are; this brief is the portable layer), the judge prompt or model.
- Never push. No listing-site fetching anywhere. Private corpus text stays out of the repo.
- Tests: extend `tests/test_profile_check.py`, `tests/test_eligibility.py`, `tests/test_panel.py`; the full
  suite (`python3 -m unittest discover -s tests -p 'test_*.py'`) must pass; the pack ≤ 8,000.

### 5. Report back (one file, `docs/condition-ledger-2026-09-13/results.md`)

The two arms' tables (replay and fixtures), the noise reference, the adopt decision with the gate numbers,
what was left out and why, and the exact commands to re-run. Plain language; every number with what it is
compared to.
