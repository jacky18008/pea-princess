# Experiment handoff, 2026-09-08

The two persona matrices are finished. The second-fix confirmation is **pending: 0
graded sessions, 7 provider failures**. This handoff completed deterministic regrading
and source preservation without launching a model. Claude-dependent work remains
paused; the user's pasted Claude message reports a weekly reset on September 11 at
05:00 Europe/London (04:00 UTC). That message is historical evidence, not a new quota
check or a guarantee that connectivity and capacity will be available then.

## Preserved state and offline reproduction

The second skill fix was merged at `8126037`; the earlier A/B write-up is `b1728ae`.
Original results, including failed and superseded attempts, remain in `bench/results/`.
The root handoff also archived all 2,060 original artifact files before testing, under
`/Users/chenhsienhao/Documents/pea-princess-handoff-20260908T113914Z`. The original shell
plans and relevant logs were preserved by the root handoff as supplemental evidence.

The independent regrade lives locally at
`bench/results/handoff-2026-09-08-verified/`: copied cards and transcripts, three
rules-only logs, `summary.json`, and `provenance.json`. The latter records every source
file's SHA-256, grading input hashes, and successful before/after source-integrity
verification. It does not rewrite the historical transcript header grades; copied
JSON cards are authoritative for the regrade. The committed, transcript-free output is
[`2026-09-08-persona-summary.json`](2026-09-08-persona-summary.json).

Reproduce from a fresh output path (existing output is rejected):

```bash
cd /Users/chenhsienhao/Documents/pea-princess
python3 bench/handoff_personas.py --output bench/results/handoff-personas-reproduce
```

The script copies the three batches, guards against accidental model launches, applies
only deterministic rules, retains each existing model judgment, and verifies originals
are unchanged. Its `provenance.json` captures actual file hashes even when the checkout
has uncommitted changes; its Git HEAD field alone must not be read as the entire source
identity. The verified summary SHA-256 is
`00aecd8af558e0e81119ac9cf66414d98139d6dd1aa573b08fc6f0a2f191a622`.

## Complete and pending experiments

| Batch | Verified state | Next action |
|---|---|---|
| Persona pilot, `personas-2026-09-06` | 6 current cards; superseded attempts retained | Complete, diagnostic baseline only |
| First persona matrix, `personas-2026-09-07` | All C1–C8 and P1–P8, baseline/probe, seed 1: 32 graded | Complete |
| First-fix matrix, `personas-2026-09-07-fixed` | Same 32 sessions; all five provider-error replacements finished | Complete |
| Second-fix batch, `personas-2026-09-07-fix2` | 7 attempted, all provider errors | Resume exactly the seven below after Claude is available |
| Document reading matrix | All 230 planned arm/model/case cells have a valid result | Complete; no outstanding provider retry |
| Pipeline ablation | All 12 cells in `pipeline-ablation.sh` present; chain ended September 7, 18:03:30 UTC | Complete, including documented missing-report failures |
| Pipeline pilot recovery | Monolithic comparison and P2 run 3 present; chain ended September 7, 02:08:33 UTC | Complete |
| Journey suite, `journeys-2026-09-05` | 40 current rows: 30 Codex, 10 Claude; run logs end with completion markers | Complete |

The docs matrix's raw scorecard has 244 rows: the 230 planned cells, seven recovered
attempts preserving the original failed rows, and seven extra run-2 results. Every cell
has a valid result; the report uses its first valid result. Re-averaging all 237 valid
rows would give the repeated cells extra weight. The retry log says no provider-error
row remains; `r3-sol.sh` finished September 7 at 16:09:03 UTC.

Pipeline P1 was explicitly not pursued in `docs/EXPERIMENTS.md` after P2/P3 failed to
beat the baseline. The pre-handoff zero-second, schema-failed P1 row under
`bench/results/2026-09-08` is a synthetic test artifact, not evidence of an interrupted
model experiment. The root handoff fixed tests writing there and restored only the
extra test-created changes to the archived originals. No separate unfinished
Claude-free model batch was found in the inspected chain scripts and logs.

## Current comparison, one deterministic grader

| Metric | First matrix | First fix |
|---|---:|---:|
| Graded sessions | 32 | 32 |
| Grade median | 0.3922 | 0.6250 |
| Grade mean | 0.5500 | 0.6271 |
| Safety-capped sessions | 16 | 7 |
| Viewing warning missing | 9 | 3 |
| Legal caps/date line missing | 5 | 0 |
| Courteous draft missing | 3 | 2 |
| Verify before paying missing | 2 | 2 |
| Licence-versus-tenancy line missing | 1 | 2 |
| Completed / abandoned / timeout | 5 / 21 / 6 | 6 / 23 / 3 |
| Mean individual criterion score, 0–3 | 2.1731 | 2.0288 |
| Mean count of criteria scoring ≥ 2 | 2.4688 | 2.1875 |
| Sessions meeting every criterion, all ≥ 2 | 15 | 11 |
| Sessions with every criterion at 3 | 2 | 4 |
| First-reply characters, median | 4,316.5 | 4,108.5 |
| First-reply question count, mean | 5.5313 | 3.3750 |

All 32 pairs match: 15 improved, 7 declined, 10 unchanged; mean grade difference
`+0.0771125`. The safety-line result survives the audit. Reply length fell only 4.8%.
The earlier write-up's 2.47 → 2.19 was a **count**, not a mean score out of three:
24 sessions have three criteria and eight have four. Its "fully met 16 / 12" was
`criteria_met == 3`, which is not a completion test for four-criterion cards. Current
tables and prose in the findings and experiment pages have been corrected; the
historical pre-calibration table is explicitly historical.

## The seven paused sessions

All use seed 1. The original `fix2.sh` order was P1 baseline, P4 probe, P8 baseline,
P3 baseline, P4 baseline, P5 baseline, P5 probe, with `--timeout 900`.

| Session | First-fix grade and missing line | Second-fix evidence |
|---|---|---|
| P1-baseline-s1 | 0.34; viewing warning | One 4,910-character reply; agent failed turn 2 |
| P3-baseline-s1 | 0.34; courteous draft | No completed reply |
| P4-baseline-s1 | 0.34; courteous draft | No completed reply |
| P4-probe-s1 | 0.34; viewing warning | No completed reply |
| P5-baseline-s1 | 0.34; verify before paying, licence distinction | No completed reply |
| P5-probe-s1 | 0.34; verify before paying, licence distinction | No completed reply |
| P8-baseline-s1 | 0.3333; viewing warning | No completed reply |

Every failed agent turn exhausted three CLI attempts: 21 failed launches for this
batch, in addition to P1's one successful initial call. The log closes on
`2026-09-08T03:32:54Z` after rules-only regrading. Empty transcripts generate missing
line flags mechanically, but these are **not** quality findings; all seven grades are
null. P1's one reply contains both required lines, a useful partial observation that
does not establish a completed confirmation result.

## Bounded resume plan

Use the handoff checkout with its one-attempt launcher, provider fail-fast and
`--max-sessions` support. Keep its skill, fixtures and generated prompt pack fixed
throughout this batch. `bench/personas.py` and `bench/journeys.py` use the checkout's
own skill and `dist/prompt-pack`; they do **not** honor `VETFLAT_SKILL_DIR`. If the main
checkout changes before recovery, use a detached worktree at the handoff commit and
copy the archived results there instead of mixing skill revisions within a batch.

Prepare a fresh continuation directory, then inspect a one-session plan. These commands
are offline; `copytree` refuses to overwrite an existing continuation:

```bash
cd /Users/chenhsienhao/Documents/pea-princess
git diff --exit-code 8126037 -- skills/vet-flat evals/personas.json
python3 tools/build_dist.py
python3 - <<'PY'
import shutil
shutil.copytree('bench/results/personas-2026-09-07-fix2',
                'bench/results/personas-2026-09-11-fix2-resume')
PY
python3 bench/personas.py --retry-failed bench/results/personas-2026-09-11-fix2-resume \
  --model claude-opus-5 --persona-model gpt-5.6-terra --judge-model gpt-5.6-sol \
  --timeout 900 --max-sessions 1 --dry-run
```

After quota and connectivity have recovered, the following is the **first model run**:

```bash
python3 -u bench/personas.py --retry-failed bench/results/personas-2026-09-11-fix2-resume \
  --model claude-opus-5 --persona-model gpt-5.6-terra --judge-model gpt-5.6-sol \
  --timeout 900 --max-sessions 1
```

The retry selector sorts cards by filename, so this canary is P1 baseline. Inspect its
card and recorded actor usage before continuing: a provider error means stop and keep
the pause. A low quality grade or user abandonment is a test finding, not permission
to keep replaying the same session until it improves. If the provider worked, run the
remaining six once, then regrade deterministically:

```bash
python3 -u bench/personas.py --retry-failed bench/results/personas-2026-09-11-fix2-resume \
  --model claude-opus-5 --persona-model gpt-5.6-terra --judge-model gpt-5.6-sol \
  --timeout 900 --max-sessions 6
python3 bench/personas.py --regrade bench/results/personas-2026-09-11-fix2-resume --rules-only
```

Preserve each original failed card under the copied folder's `superseded/`, retain
null scores for any new provider failures, and compare only the seven same-ID
first-fix sessions. Seven repaired cases are selected from prior failures; they are
not an unbiased new estimate of the full 32-session matrix. No full-matrix rerun or
switch to another model is necessary to finish this confirmation.

## Provenance limits

Stored persona cards say `model: null`, but the Claude project logs resolve all 32
first-matrix runs, 32 fixed runs, six pilot runs and fix2 P1 to `claude-opus-5`.
The [model provenance file](2026-09-08-model-provenance.json) records response counts
and source hashes without conversation contents. Thus the old "Sonnet" description
was wrong and the resume command pins the observed model. The other six fix2 sessions
never received a served model response. Personas were `gpt-5.6-terra`, judges
`gpt-5.6-sol`; switching the tested agent to Codex would still introduce Claude helpers
under the crossed-family defaults and change the experiment.

Historical cards do not record per-session skill hashes or resolved helper deployment
revisions. Controller seed 1 is not a model sampling seed. Grading rules were calibrated
after observing outcomes; this is a fault-finding regression exercise, not a blinded
causal trial. A deterministic safety-line pass establishes that matching text was
found, not that every legal claim in the transcript is correct. Sleep and outages
also prevent the old wall times from being clean latency measurements.
