# Native conversation continuity: follow-up design

2026-09-09. Offline design review of the `e001e06` transport and locally installed **codex-cli 0.153.4**. No model was called, no unrelated Codex session or authentication file was read, and no experiment transport was changed. This is a later experiment proposal, not a claim that native resume or native compaction has been tested.

The user requested completion of the original matrix before applying waste-reduction changes and lifted the 6,000,000 processed-token ceiling. Preserve that study and its budget amendment. The new [portable state API guide](../skills/vet-flat/references/state-api.md) belongs to a subsequent version; do not insert it into the frozen `e001e06` ZIP or attribute its behavior to existing results.

## What the current experiment actually does

| Component | Observed behavior | Interpretation |
| --- | --- | --- |
| `bench/conversation_native.py:invoke` | Starts `codex exec` with `--ephemeral` for every answer/judge invocation; enables native shell/file work in the owned synthetic workspace. | Real native tool execution, but each conversational turn starts a new native session. |
| `bench/conversation_ablation.py:answer_request` | Normally supplies all prior user/assistant messages, plus the current message, as text in a new prompt. Reuses the working files. | Application-level conversation replay and file persistence. Prior native tool results are not replayed as native conversation events. |
| Turn 6 | Supplies only the latest message inline; the complete conversation remains in `conversation.json`. | A deliberate file-recovery challenge, not a native compact operation or an observed native restart recovery. |
| Reference treatment | Bulk arms preload inputs/onboarding on each fresh call; routed arms expose the same files without those inserts. | Changing transport can change the frequency of document loading. That must become a named experimental factor. |
| Native configuration | Ignores user configuration, disables automatic project-document loading, pins model/effort, and uses a synthetic local workspace. | Controlled native execution, not a complete reproduction of the user's interactive desktop setup, plugins, hooks, permissions or interruptions. |

The preserved first three calls (`s02-t01`, `s10-t01`, `s28-t01`) are **all T1**. Their **908,860 processed tokens**, including **366,898** for the first call, cannot be explained by a failure to resume an earlier conversational turn: none existed. The first call's 20 completed shell commands include substantial API/schema discovery. See the [pilot cost diagnosis](native-pilot-cost-diagnosis.md) for actual counters and the distinction between tool-output characters and tokens.

Fresh starts may cause rediscovery on **later** turns; that is a hypothesis to measure after the original matrix. Native continuation may also retain more tool output than the current replayed messages, increasing context size or triggering compaction. It is neither inherently cheaper nor a guarantee of complete memory.

## What local CLI inspection establishes

Read-only commands run for this review:

```text
codex --version
codex exec --help
codex exec resume --help
codex exec --ignore-user-config --cd . --sandbox workspace-write resume --help
```

The installed help exposes `codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]`. A session ID can be a UUID or a thread name; `-` supplies the prompt on stdin. It also exposes model/config overrides, JSONL output and a per-call final-answer output file. `--ephemeral` prevents session-file persistence. `--ignore-user-config` skips configuration loading, **not authentication**. The final help command checks parser acceptance of parent working-directory/sandbox options; it does not prove those settings' effective behavior in a resumed model turn.

Only the three experiment-owned stdout files were inspected for identity shape. Each contains exactly one `thread.started` object with `thread_id` holding a valid UUID, and one `turn.completed` event. UUID values remain private. The current reducer preserves the raw streams but does not bind that UUID into an application-level ownership manifest. An emitted UUID alone does not prove a persisted session can be resumed; these calls used `--ephemeral`.

No session listing, `--last`, `--all`, account configuration or authentication inspection was needed. This local evidence does not establish resume usage-counter semantics, native retention policy, interrupt routing or automatic compaction behavior.

## Safe future transport

1. **Start a new owned thread.** In a new experiment version, create a fresh owned workspace and make its first native invocation without `--ephemeral`. Keep the current model/effort, sandbox, source freeze, exact prompts, output limits, process cleanup and serial durable-call ledger. Do not attempt to convert or silently continue an old ephemeral run.
2. **Bind the returned UUID.** Parse the first invocation's own `thread.started.thread_id`. Require one valid UUID; save it atomically outside the model-writable workspace with experiment/session ID, workspace ownership hash, source/version hashes, CLI version, model/effort, request hash and physical invocation ID. Never accept a thread ID from model prose, a document, a user-supplied file, or a globally selected “latest” session.
3. **Resume only that exact UUID.** Later invocations use `codex exec … resume OWNED_UUID -`, passing only the new user turn and necessary authoritative changes on stdin. Never use `--last`, `--all` or a mutable thread name. Keep the trusted execution configuration explicit and verify its behavior during qualification; `resume` is not permission to broaden access. A missing, mismatched or unowned identity stops the session; do not fall back to an unrelated thread or a fresh session under the same treatment label.
4. **Avoid duplicate conversation injection.** Keep the complete raw transcript and frozen source snapshots for audit, but do not append that transcript again to an already resumed thread. First-turn skill/reference bytes remain frozen. Add newly released evidence only at its scheduled turn, validate current requirements after steering, and read exact saved evidence where needed. Native context is a working memory; it does not replace the authoritative requirement/source store.
5. **Serialize each owned thread.** Lock the experiment/session UUID and expected turn before dispatch. Only one unresolved invocation may own it. Save input identity before starting; save result, observed UUID, usage and artifact/history hashes before accepting completion. The same UUID cannot be shared by another matrix cell, actor or evaluator.
6. **Recover without resubmission.** A timeout or disconnect may leave a persisted partial turn and incurred usage. Inspect only the owned call's saved receipts and any explicitly supported read-only metadata for that owned thread. Do not run `resume` just to inspect: it can submit another model turn. Materialize a completed saved result locally; unresolved usage or an ambiguous appended user turn blocks new dispatch. No automatic retry of the same prompt.

Persistence adds native session files to the existing private artifacts. Record that storage surface and keep it out of public releases; do not copy credentials or enumerate unrelated account sessions. Workspace-write is still not adversarial read isolation from the host account. A real hostile-input containment experiment needs separately bounded operating-system access.

## Usage and comparison rules

- Keep **native CLI invocation count**, **provider-request count** and **processed tokens** separate. One native turn can contain multiple model/tool iterations. If individual provider requests are not observable, that count stays unknown.
- Preserve every raw usage event and its owning invocation. The current code expects exactly one `turn.completed` usage object per CLI invocation. A resumed-turn qualification must establish whether reported counters cover the current turn, the session-to-date total, or some other scope. Do not blindly sum cumulative counters or subtract a previous total without evidence of matching scope; detect resets and duplicate events.
- Under the current metric, `processed = input_tokens + output_tokens`; cached input is already included in input. Show noncached input separately where counters support it. Do not add cached input twice, equate output tokens with visible answer length, or infer a monetary bill/subscription rate-limit charge from processed totals.
- Compare T1 separately from T2 onward. Record repeated API/schema reads, tool-output volume, newly read reference bytes, token/cache counters, latency and actual report/state artifacts. Fewer reads are useful only if requirement coverage, source qualifiers, scope changes and final decision quality survive.
- In a future paired comparison, freeze the same entry, tool/reference corpus, model, effort, depth and user-turn schedule while changing only fresh replay versus native resume. Test the state API guide separately, or explicitly cross guide version with continuity mode; changing both together cannot identify which caused savings.
- Treat file-only recovery, application crash recovery, mid-turn human interruption and native compaction as different cases. A resumed thread may still remember earlier messages at T6, so it is not equivalent to the current T6 prompt-history omission. Claim native compaction coverage only after an actual supported compaction operation/event is observed and recorded; this review did not test one.

## Required tests before future dispatch

| Test | Required evidence |
| --- | --- |
| Owned UUID routing | Fake native streams yield a recorded UUID; the next command uses exactly it. Reject absent/multiple/malformed IDs, a different resumed UUID, `--last` and `--all`. No lookup of unrelated sessions. |
| Configuration and payload | Assert fresh-versus-resume command shape, absence of `--ephemeral` for persisted sessions, pinned working root/model/effort/sandbox, unchanged stdin, and no full-history duplication after T1. Qualify effective settings with an explicitly budgeted native test later. |
| Crash and concurrency | Two workers cannot append simultaneously. Crashes before/after identity, usage and history persistence never duplicate a submitted user turn or charge a saved receipt twice. Failed or unknown-spend calls remain blocked. |
| Usage scope | Fixtures cover per-turn and cumulative counter shapes, resets, cached-input subsets, duplicate/missing terminal events and contradictory telemetry. Unknown scope is rejected instead of producing a fabricated total. |
| Evidence and outcomes | Delayed documents stay unavailable before release; changed input hashes stop progress. Scoped requirement edits persist. Evaluate actual saved files and cited source bytes, not the agent's claim of completion. |
| Recovery distinctions | Preserve separate labels for text replay, file reconstruction, same-thread restart, true mid-turn interruption and observed compaction. A passing file-resume case must not be reported as all five. |

Source anchors: [native adapter](../bench/conversation_native.py), [ablation runner](../bench/conversation_ablation.py), [usage extraction](../bench/durable_run.py), [durable ledger](../bench/call_control.py). The observations above refer to frozen `e001e06` behavior and the local help commands, not to a newly executed continuation. This proposal supplies no new model-call authorization and does not alter the ongoing matrix.
