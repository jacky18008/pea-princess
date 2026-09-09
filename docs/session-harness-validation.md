# Offline session lifecycle validation

All scenarios use synthetic data and make zero LLM calls. The expected-state oracle consists of hand-authored semantic fact updates. The lossy comparator retains only the last 4 fact records; it is a deterministic truncation proxy, not an implementation of Codex or Claude compaction.

The 401 fact checks repeat 38 distinct semantic facts across 12 checkpoints. They are not independent model trials.

| Path | Fact checks | State errors |
|---|---:|---:|
| full_history_oracle | 401 | 0 |
| naive_recent_records | 401 | 297 |
| durable_resume | 401 | 0 |

The oracle's zero error count is definitional: the full fixture is the reference, not a tested reasoning agent.

| Checkpoint | Full input characters | Lossy fact characters | Durable packet characters | Durable errors |
|---|---:|---:|---:|---:|
| initial-complete-state | 1615 | 395 | 3703 | 0 |
| raise-housing-budget-only | 1820 | 202 | 3933 | 0 |
| lower-budget-and-retain-other-scopes | 2016 | 169 | 3924 | 0 |
| retire-without-forgetting-history | 2153 | 225 | 3648 | 0 |
| add-scoped-requirement | 2331 | 408 | 4009 | 0 |
| prohibit-to-scoped-conditional | 2710 | 990 | 4888 | 0 |
| new-document-supersedes-old-fact | 3080 | 1003 | 5579 | 0 |
| pending-exact-user-request | 3250 | 1118 | 5806 | 0 |
| resolved-request-preserves-budgets | 3417 | 890 | 5601 | 0 |
| paused-workflow-survives-steering-and-restart | 3713 | 198 | 5566 | 0 |
| workflow-resume-retains-full-state | 3801 | 87 | 5567 | 0 |
| explicit-token-budget-change | 4057 | 95 | 5657 | 0 |

Character counts measure different representations and do not include provider tokenization, cache writes/reads, model output or subsequent document retrieval. They are not measured token or cost savings.

On this short fixture, durable packets include provenance, status and version metadata, so they can be larger than the full input history. Continuity checks are useful independently of whether the chosen representation is smaller.

| Safety invariant | Passed | Detail |
|---|---|---|
| stale-writer-rejected | true | A second writer cannot commit using an earlier revision; journal unchanged. |
| stale-decision-rejected | true | Current write revision cannot launder an older reasoning receipt. |
| every-active-requirement-covered | true | Even a preferred requirement must be acknowledged; unmet preference alone need not block PASS. |
| conditional-pass-requires-predicate-evidence | true | The word met cannot silently satisfy an exception predicate. |
| unknown-hard-condition-cannot-pass | true | An unknown hard requirement keeps PASS unavailable. |
| source-bound-quote-must-be-verbatim | true | A fabricated quote cannot become checked document evidence. |
| raw-document-hash-and-exact-retrieval | true | Both source versions retain byte hashes; retrieval ignores later edits to the original file. |
| damaged-source-snapshot-rejected | true | Hash verification detects modified retained bytes before state use. |
| source-supersession-invalidates-dependent-work | true | A new source invalidates direct and derived facts, decisions and prior task completion. |
| retired-fact-invalidates-transitive-evidence | true | Retiring a cited fact also invalidates copied downstream facts, even when not labelled derived. |
| pending-request-blocks-dispatch | true | Exact raw steering must be reconciled before a new dispatch. |
| pause-persists-through-steering | true | A pause survives capture/reconciliation and still prevents workflow dispatch. |
| mid-call-steering-rejects-stale-result | true | An earlier physical response cannot complete against newer user requirements. |
| unsettled-stale-call-blocks-next-dispatch | true | Reconciled user text does not settle the old physical call or its usage. |
| unknown-usage-is-not-zero | true | Unknown token usage pauses new spending. |
| overspend-prevents-followup | true | A measured ceiling overrun remains recorded and prevents another call. |
| housing-budget-cannot-become-api-credit | true | Stable budget IDs cannot change economic scope or unit. |
| task-bound-budget-cannot-be-omitted | true | A caller cannot bypass an unknown task-bound budget with an empty dispatch list. |
| usage-recovery-is-idempotent | true | Same dispatch usage is counted once; conflicting telemetry is rejected. |
| paused-goal-blocks-descendant-work | true | A paused parent goal also pauses its prerequisite work, not just its own dispatch. |
| goal-needs-current-complete-dependencies | true | A saved source document cannot bypass an unfinished prerequisite task. |
| blocking-question-prevents-final-receipt | true | An unresolved material question prevents a current decision receipt for affected work. |
| small-context-fails-without-truncation | true | Insufficient context capacity is an explicit failure, not omitted requirements. |
| restart-prefers-journal-over-stale-checkpoint | true | Fresh recovery exposes pending input that arrived after the saved checkpoint. |

This run checks state storage, retrieval, lifecycle transitions and rejection boundaries. It does not establish semantic extraction accuracy, source truth, prompt-injection containment of a tool-enabled model, real native hook delivery, or equivalence of final answer quality. A coverage receipt can still contain an incorrect claim; exact retained quotes establish provenance, not truth.
