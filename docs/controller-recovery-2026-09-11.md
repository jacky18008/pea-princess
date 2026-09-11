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

The processed-token ceiling is checked between calls and can be exceeded by one call. Keep original and recovery usage separate, and show known combined usage alongside any unresolved historical unknowns. Raw prompts, outputs, request manifests and conversation transcripts remain in ignored private run directories for later evaluation.

## Validation and quality interpretation

Offline validation of the controller repair:

- The same two-process regression fails against the historical `_restore` implementation: the nested persona directory disappears after the first successful call. It passes with the fix. Both processes use local Python fixtures, not a model.
- All 37 durable-run tests pass, including completed-call replay, file/directory collisions, removal of future files and missing-cwd rejection before dispatch.
- The required repository suite passes: **2,282 tests**, 127.999 seconds. Existing resource warnings were emitted; there were no test failures.
- An independent code reviewer found no blocking issue under the documented file-only contract.

Live conversation recovery has not yet run at this checkpoint. Its result will be appended separately; these offline results do not establish model availability or conversation quality.

The initial 633-character / 3-question reply is evidence of a shorter opening, not proof of better conversation quality. This repair does not change the skill or conversational prompt. Any completed continuation must still be reviewed for usefulness, unnecessary questions, correct handling of the user's replies, progress towards a housing decision, and eventual outcome. A simulated user's satisfaction and a model judge's score are supporting signals, not human acceptance.

The independent initial-reply review does **not** pass the opening UX gate. Its P1 findings include changing an arrival date into an enrolment date and leading with unsupported urgency claims. Claims about income screening, guarantors and tax eligibility also need evidence and scope before they constrain the user's options; this review did not independently adjudicate the law. Its P2 finding is the amount of intake and general explanation before providing a useful comparison. Destination and budget interpretation are useful clarifications; guarantor details can wait. No P0 was demonstrated. These are findings about the retained original response, not changes made by this controller repair.
