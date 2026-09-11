# Persona conversation controller recovery — 2026-09-11

## Confirmed incident

The C1 / 雨萱 conversation stopped after its first assistant reply. This was a local runner defect, before the second model process started. It is not evidence of a model failure or a skill-quality regression.

The original private run is `.pea-playground/conv-check-20260911/`:

| Record | Observed result |
| --- | --- |
| `call-000001`, turn 1 assistant | Claude Sonnet 5; exit 0; 633 reply characters and 3 questions according to the runner |
| Direct terminal usage for call 1 | 23,653 input tokens, including 3,298 cached input tokens; 1,453 output tokens; 25,106 processed tokens |
| `call-000002`, turn 2 persona | Codex `gpt-5.6-terra`; process did not start; exit code absent; stdout/stderr empty |
| Actual error | `FileNotFoundError` for the nested `_persona` working directory |
| Original controller classification | `process_error`, followed by a batch pause |

The launcher retained the underlying exception in `control/checkpoint.json`, under the second call's `record.launch_result.attempt_records[0].start_error`. `progress.json` is only the abbreviated report. An exit code of `null` here must not be described as Codex returning a nonzero exit code.

Consequently, “two dispatched calls” in this historical controller means two registered attempts, not two completed model requests. This defect lost progress and time; the trace does not show a second model request consuming tokens. The successful first response must not be purchased again just to advance the run.

The original ledger has unknown usage for the failed startup. Preserve that historical record and its unknown total; do not rewrite it to zero. The retained exception establishes that this particular process never started. The successful first call's usage above is the controller's direct-terminal accounting scope; it is not an independent audit of all provider-side ancillary work.

## Cause and repair

1. `personas.py` creates an empty `_persona` directory before the first assistant call.
2. The durable controller snapshots file contents, not empty directories.
3. After the first successful call, its restoration code removes empty directories while restoring the file snapshot.
4. That cleanup deletes `_persona`. The next `Popen(..., cwd=...)` fails before Codex executes.

The repair preserves empty runtime directories during file restoration, while retaining removal of later files and restoration of saved file contents. This is **file-artifact rollback**, not an exact recreation of directory existence, directory permissions or native provider session state. Missing working directories must be rejected locally before dispatch is registered or a model is called.

The regression must exercise the sequence of a successful parent-directory call followed by a nested persona-directory call. Testing only JSON parsing or only `mkdir` would miss the defect. Replay, stale-file removal, path collisions and the no-dispatch preflight also need coverage.

OpenAI documents `codex exec --json` as an event stream with separate completion/failure events. Here there was no stream to parse, so relaxing completion checks or accepting empty output would hide the real defect. See [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

## Recovery protocol

The original run remains immutable and paused. The corrected implementation belongs to a new run with its own frozen manifest and physical-call ledger. The original plan allowed at most 30 physical attempts; two were already recorded, leaving at most 28 new attempts for this recovery. This is one conversation, not another model matrix.

Reuse the original successful first reply without another Claude call or another usage charge in the new ledger. Bind the original request, checkpoint and persona fixture by hash. Preserve the original frozen system prompt: both the skill entry file and generated instruction pack changed after the original run began, so loading today's files would silently change the experiment. Check the first recovered persona request against the original failed request.

Continue with the same models and persona. Use explicit transcript replay in the new run, rather than claiming to restore the mutable original Claude session. Record that protocol difference. Stop on any failed call or rate limit; do not retry automatically. The user's Claude permission applies only to this conversation; other paused experiments remain paused.

This original C1 case uses the legacy **chat harness**, synthetic fixture documents and a tools-disabled Claude assistant. Continuing it tests that frozen conversation's behaviour and the repaired runner. It does not test live housing research, native clarification widgets, or acceptance of the currently shipped agent skill.

The processed-token ceiling is checked between calls and can be exceeded by one call. Keep original and recovery usage separate, and show known combined usage alongside any unresolved historical unknowns. These counters cover benchmark CLI actors; they exclude this coordinating Codex conversation and its review subagents and are not an account-wide spending report. Raw prompts, outputs, request manifests and conversation transcripts remain in ignored private run directories for later evaluation.

## Validation and quality interpretation

Offline validation of the controller repair:

- The same two-process regression fails against the historical `_restore` implementation: the nested persona directory disappears after the first successful call. It passes with the fix. Both processes use local Python fixtures, not a model.
- All 37 durable-run tests pass, including completed-call replay, file/directory collisions, removal of future files and missing-cwd rejection before dispatch.
- The required repository suite passes: **2,282 tests**, 127.999 seconds. Existing resource warnings were emitted; there were no test failures.
- An independent code reviewer found no blocking issue under the documented file-only contract.
- All seven original run files remain byte-identical after the repair and full suite. Local CLI versions are `codex-cli 0.153.4` and `Claude Code 2.1.261`.

The recovery entry point has 13 additional passing synthetic tests. These cover exact request reconstruction, one-time first-reply reuse, transcript continuation, failure/rate-limit stopping, refusal to restart, fixture deletion/change, corrupt evidence, and preservation of partial transcripts. A second independent implementation review found no remaining blocking issue.

After adding that entry point, the full repository suite also passed: **2,295 tests**, 129.700 seconds.

The actual original run also passed offline preparation: both reconstructed requests match their frozen originals and **zero model calls** were dispatched. Recovery preparation reserves at most 28 new attempts and 1,474,894 further known processed tokens (1,500,000 minus the original known 25,106); the historical unknown remains visible.

Avoiding a duplicate first response does not establish that transcript recovery uses fewer total tokens than native session continuation. The protocols differ and no A/B comparison was run for that claim.

The continuation completed in `.pea-playground/conv-check-20260911-recovery-v1/`. Controller repair commit: `0297e94`; recovery implementation commit: `46ef16b`.

## Live result

Execution passed: all **12 assistant turns** are retained, including the reused original first response. All **24 new physical CLI calls** completed; there were no failed new calls, automatic CLI retries or unresolved calls. Four unused slots were explicitly skipped. The original seven files remain byte-identical. Counting the original successful call and original failed startup gives 26 registered attempts against the 30-attempt ceiling; only 25 of those attempts actually started model processes.

| New role | Calls | Processed tokens |
| --- | ---: | ---: |
| Claude assistant | 11 | 340,671 |
| Codex Terra simulated user | 11 | 246,554 |
| Simulated satisfaction response | 1 | 25,135 |
| Original Codex Sol judge | 1 | 29,975 |
| **Total new work** | **24** | **642,335** |

The new total consists of 612,558 input and 29,777 output tokens; 411,107 input tokens were cached and are already included in the input count. Known original-plus-new usage is 667,441 processed tokens. The combined ledger's exact total remains `null` because the original failed-start record still has unknown usage. The new run itself has complete direct counters.

The runner's conversation outcome is **`abandoned`**, after reaching the 12-turn limit without a persona `[END]` closure. That is not evidence that a real user abandoned the product. The simulated satisfaction rating is 2, with listing existence/availability still unresolved. The legacy judge returns 0.34 after a safety cap; neither that number nor the simulated rating is a calibrated human UX score.

Reply lengths are 633, 1,351, 865, 1,253, 856, 274, 1,134, 1,348, 401, 192, 256 and 781 characters, with a median of 818.5. These describe the recovered conversation, not a matched comparison with the old 4,220-character first-reply statistic supplied in the incident report.

Machine-readable aggregates and artifact hashes are in [the result JSON](controller-recovery-2026-09-11-results.json). Raw requests, expanded pasted documents and responses remain private for independent evaluation.

## Reproduce this specific recovery

This command supports only the observed C1, seed-1 chat run with one successful first response followed by a local persona startup failure. It rejects changed/missing fixtures, changed original records, overrides and unsupported configurations. Use a fresh destination; an existing started recovery cannot be rerun automatically.

```sh
python3 bench/persona_recovery.py prepare \
  .pea-playground/conv-check-20260911 \
  .pea-playground/conv-check-20260911-recovery-v1
python3 bench/persona_recovery.py run \
  .pea-playground/conv-check-20260911-recovery-v1 --allow-claude
```

The first command is offline. The second makes model calls and requires the separately granted permission for this conversation. Do not issue the second command again against the already-used destination in this report.

`recovery.json` binds source evidence and the changed continuation protocol. `original/` preserves the seven original files, byte for byte. `continuation/control/progress.json` reports only new physical attempts. `actor-trace/` preserves exact actor requests/results, including expanded document context in the requests. `conversation-trace.md` is a readable incremental view, including the initial user request; it can contain raw persona paste markers. `conversation.json` and `results/` contain the completed conversation when execution reaches the existing writer. `recovery-result.json` distinguishes execution status, conversation outcome, new usage and combined known/unknown usage.

## Conversation assessment

The initial 633-character / 3-question reply is evidence of a shorter opening, not proof of better conversation quality. This repair does not change the skill or conversational prompt. Any completed continuation must still be reviewed for usefulness, unnecessary questions, correct handling of the user's replies, progress towards a housing decision, and eventual outcome. A simulated user's satisfaction and a model judge's score are supporting signals, not human acceptance.

The independent review does **not** pass the opening UX gate: it leads with pressure and general intake rather than a useful tailored comparison. Destination and budget interpretation are useful clarifications; guarantor details can wait. Arrival-to-enrolment wording and the opening tone are P2 unless a consequential decision depends on them. No P0 was demonstrated.

The full-source review corrected the preliminary assessment preserved in the first repair commit: the 4–8-week listing window, fast turnover, and general student-tax assertions were already present in the frozen prompt. They must be attributed to that prompt, not described as inventions absent from supplied instructions. This review does not independently establish their legal or factual accuracy. Reading only the reply and persona opening was insufficient to attribute those defects correctly.

The finalized independent Astra review is retained privately at `.pea-playground/conv-check-20260911-recovery-v1/astra-review.md`, alongside the exact evidence it cites. It reviewed all twelve turns, expanded pastes, the frozen prompt and the legacy judge. **Engineering recovery passes; conversation acceptance fails; the rental goal remains waiting/unresolved.** This recovery did not alter the prompts midway or silently repair the saved answers.

| Priority | Demonstrated issue | Next change to validate separately |
| --- | --- | --- |
| P1 | T2/T7/T11 repeatedly suggest 6–12 months' advance rent despite the supplied one-month, agreement-scoped rule; T2 confuses a rent amount with the time between signing and moving in. | Use unambiguous, sourced agreement-specific payment rules; check proposed payment routes against them before presenting an option. |
| P1 | A previously promised written-tenancy condition disappears from later holding-deposit guidance. | Keep the entire applicable payment condition through later answers. Review the source rule's scope itself; this is evidence of inconsistency, not an assertion that every frozen blanket rule is correct law. |
| P1 | T8 calls live viewing unforgeable; T12 implies cooperative video checks largely eliminate fake/wrong-property risks. | Describe which uncertainties a check reduces and what remains, including identity and authority to let. Do not convert a helpful check into a guarantee. |
| P2 | Pasted-document handling creates more tasks; the passport-scan refusal is incompletely carried into suggested routes; duplicate paste gets a corrective response. | Preserve user boundaries, answer the present concern, and track explicit waiting states without repeating a broad intake. |
| P2 | Area/floor hints and one room-side measurement are presented as stronger identity/size evidence than they are; displayed rounding is inconsistent by two pence. | Keep matching clues distinct from verified identity, avoid unsupported size inference, and round only final monetary results. |

There are useful local successes: the assistant answers EPC navigation, accepts the refusal to disclose savings, and drafts viewing questions. There is still no returned EPC match, verified availability, full monthly-cost comparison or established referencing route. Missing browsing capability in this old chat harness is not itself an actor error; claiming or promising unavailable verification is.

## Review of the evaluation process and avoidable use

The legacy judge gives the first reply 3/3 and marks `law_caps_and_date` as passed, despite the later advance-rent and amount/timing contradictions. It notices the omitted viewing-day warning and caps the overall grade, but does not identify the most consequential errors above. Its five counted questions omit imperative requests such as obtaining EPC information, checking schemes and supplying financial information. Its failed “settings summary shown” check contradicts the instruction to hide execution settings. These metrics need correction; exposing settings or shortening replies to satisfy them would make the product worse.

The independent review also required correction: full prompt provenance changed attribution and severity of several preliminary opening findings. Preserve that disagreement and correction rather than treating either model judge as human truth. Future review should always include the complete frozen instructions, visible user input, expanded documents, relevant state and the entire dialogue before assigning causal blame. Hidden persona settings must not become requirements the answering model was never told.

About **47.0% of the new processed tokens** went to the simulated user, satisfaction response and judge, rather than the answering assistant. That is evaluation overhead with a purpose, not automatically waste. This also explains why twelve assistant replies require more than twelve model calls: the original first reply was reused; eleven new assistant replies, eleven simulated replies and two assessment calls remained.

Some use is avoidable: after T10 the conversation is waiting for an EPC result, but the harness has no EPC fixture to return and generates a duplicate document paste at T11. That persona/assistant pair consumes **59,135 processed tokens** without supplying new evidence. T12 then asks a useful new video-verification question, so it would be wrong to classify every later turn as waste. A future design should record the waiting state, supply the missing fixture when testing resumed research, and test an intentional interruption separately from accidental repetition.

For further controller changes, use the local two-process regression and synthetic recovery tests first. No model is needed to reproduce this filesystem failure. Additional model experiments should test a defined conversation hypothesis with an explicit stopping condition; this run provides no evidence that a broader matrix or another restart is needed.
