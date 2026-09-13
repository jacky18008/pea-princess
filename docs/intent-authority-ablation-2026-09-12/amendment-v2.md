# Cost-driven scope amendment, before v2 dispatch

Registered after the first package/tool executions, on 2026-09-13 London time. The original [plan](plan.md), `8d8b514` runner and `run-v1` evidence remain unchanged. This amendment is a new version, not a successful retry attached to an old slot.

## What happened

The first two calls used 305,745 and 288,771 processed tokens. A third call was already in flight when the version change was applied; it completed with 352,553. The three calls total **947,069**, including **809,216 cached input**, 122,633 uncached input and 15,220 output tokens. None had unknown usage or a physical model failure.

The first call performed 11 distinct completed tool operations: broad file inventory, skill/reference/script reads, arithmetic, draft edits, and three reply-check runs (two failures followed by success). Small source fixtures therefore did not imply small total processed context. The execution estimate failed to account for repeated context processing at each tool step. The maintainer should have used a cost checkpoint after the first completed call before allowing the next one; this serial runner immediately dispatched the next slot, so the cost decision arrived during the third call. This is a process weakness, not a reason to erase the earlier usage.

Creating the new runner source intentionally activated the old controller's existing source-drift guard. It allowed the current physical call to finish and preserve its usage, then refused the next call. All three completed calls, the one complete two-turn conversation, the partial conversation and the **33 not-dispatched original slots** remain separately inspectable. `source_matches:false` now means the checkout advanced beyond the frozen v1 source; it does not mean v1's frozen input files were modified. Do not resume the incomplete original matrix automatically.

## Focused version

Keep the same baseline, B/C treatment files, two actor fixtures, three repetitions, two actual-history turns, model, effort, 180-second timeout, balanced ordering algorithm, independent frozen rubric and private expected notes. No actor answer is used to rewrite the cases, treatment or grading standard. The change is in common delivery/execution scope for all arms:

- Inline the exact bytes of `SKILL.md`, `references/rules.md`, `references/inputs.md` and `references/conversation-quality.md` from each arm's frozen package. There is no model-written summary or manually filled correct constraint table.
- Instruct the actor to perform the conversation-policy task with the supplied data and conceptual checks. Tool calls, filesystem reads and additional research are outside this lane. The same native CLI still exposes tools; `allow_tools:false` stops later dispatches if tool events are observed. This is a **post-call protocol check**, not preventative filesystem or network isolation.
- Retain C's program-generated exact user statement frame and the common full history. Keep synthetic evidence explicitly labelled, unknown facts unresolved and actual assistant replies in the continuation.
- Preserve the same four semantic scores and separate first-visible-message opening score. No changes to the evaluator's expected answers, scoring thresholds or treatment-selection rule.

The new matrix has 36 response slots. Its token ceiling is **1,052,931**, the original 2,000,000 actor budget minus v1's 947,069. This is still checked between calls and can overshoot by one call. Across both versions the maximum number of dispatched responses is now **39**, an explicit amendment to the original 36-response ceiling; it does not allow completing the old 33 missing slots as well. Any technical failure or budget stop is retained without a replacement. Semantic failures still remain outcomes, not retry triggers.

The focused CLI defaults to at most one new physical call per invocation. Run the first planned slot, inspect its usage, and record the cost forecast before releasing the remaining 35 slots with `--max-new-calls 35`. The first result stays in the matrix; it is not a disposable quality pilot. A completed slot replays from its existing receipt without redispatch. If the first call's total × 36 already exceeds this version's budget, stop for cost review rather than silently release the remaining calls. This checkpoint does not inspect semantic grades to decide whether to continue.

## What the results can establish

V2 tests the three decision-ownership treatments under a common inline, tool-free conversation-policy wrapper. It cannot establish that an arbitrary host will discover/read the relevant files, that full neighbourhood scanning works, that saved conditions/rankings/TODOs agree, or that native clarification controls work. `standard` remains the configured research-depth label; with frozen evidence and no research, this is not empirical validation of the complete standard research workflow.

A and B are baseline/current policy text **under this wrapper**, not an untouched live-product experience. Giving the opening rules before any visible reply may itself affect first-message quality. V1 is incomplete and uses a different wrapper, so its three observations do not provide a controlled estimate of v2's cost savings or a causal proof that inlining improves quality. Report the observed costs separately. Even a clean v2 winner requires later actual-tool acceptance before promotion.

The original budget underestimate and delayed cost stop are part of the experiment-process review. Future full-tool studies should freeze a cost checkpoint after one pilot call, set a review trigger, and offer an explicit stop-after-current-call operation before starting the remaining matrix.
