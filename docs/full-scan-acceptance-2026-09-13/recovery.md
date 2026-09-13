# Disconnect and low-context recovery

The network or HTTP observer can disappear while a paid model call completes.
Losing its acknowledgement must not cause another model invocation.

The coordinator writes a checksummed, fsynced intent before sending a step or
message, or handing over a reserved UI submission. A global pending entry blocks
the other condition as well. Each command buys at most one answer; there is no
automatic retry, delayed dispatch or reconnect-triggered continuation.

After reconnecting:

1. Read the private study's short `RESUME.md`, `operator-checkpoint.json`, and
   coordinator `report`. These identify the exact runtime, session, stage,
   pending turn, known usage and next operation without loading old chat text.
2. Verify the pinned manifest and current local project constraints. A byte-equal
   complete context can reuse its recorded prior audit. Changed constraints must
   be read with their exact deltas; old summaries cannot override them. Retain
   all active requirements even when historical document bodies move behind a
   hash-addressed index.
3. If a turn is pending, inspect the existing lab session and durable receipt.
   If still running, observe that same call. If the lab already finalized it, `record-observed` imports its saved usage
   and evidence. If the physical receipt completed but the server died before
   finalizing its session, first verify no worker is active and use the lab
   `recover` control, which reads receipts without a model call; then record it.
   Do not resend the input. A terminal
   failure or unknown usage stays paused; receipt recovery is not permission to
   purchase a replacement.
4. A stopped local server may restart from the **same frozen snapshot and state
   directory**. Restart itself does not dispatch. Preserve the session's
   research-results; the next actual model call receives their existing index.

Only load a completed answer, source span or original historical conversation
when judging its meaning or resolving a discrepancy. Do not reread all raw tool
streams to discover progress, reconstruct the entire corpus, or repeat source
queries to recover already saved observations.

The short status is a derivative of authoritative checksummed state, not a
replacement for it. Hashes verify identity, not source truth or semantic
authorization. Filesystem permissions do not isolate another process running
under the same OS user. The initial and final accounting must still include any
paid call whose transport acknowledgement was lost.
