# Local conversation and pipeline inspection

The test platform now has two views: **對話** for running the user's own agent and **檢閱過程** for examining saved output. Inspection and review notes do not dispatch models. The product remains a downloadable local skill; this inspector is a development and acceptance tool, not a hosted agent service.

## Reference and design decisions

This implementation draws on local TFDA Pipeline Inspector design and implementation records, especially `project_sa_inspector_lawui_v5.md`, the v3/v4 review record, the layer audit, and the paired Markdown/HTML reporting guidance. The original TFDA source checkout and a current working TFDA service were **not** located or verified here. We reused documented patterns, not a claim of directly porting its code. Private records may include unrelated operational data and are not bundled.

The useful patterns are reply first, expandable evidence, actual input preview, explicit run identity, and immutable review notes tied to the original result. Human HTML and agent JSON/Markdown use the same normalized observations. Enterprise accounts, remote workers and approval workflows are outside this local tool's scope.

## What a reviewer can inspect

Select a saved conversation and then a model call. The view provides:

- The displayed answer and clarification options, with the recorded association to that call. Old conversations without an explicit call anchor use a unique exact-content association; ambiguous cases remain unavailable.
- Raw model output before host processing, separately from the displayed answer. This matters for older checked comparisons that replaced a model proposal with a host-generated result.
- Current input extracted from its marked prompt span and the actual assembled model prompt, including injected conditions and history. The full prompt is authoritative if extraction is unavailable.
- Tool inputs, outputs, exit/failure status and retained events, grouped by execution ID. A started/completed pair counts once. Hidden reasoning is excluded.
- Input, cached input, uncached input, output, processed tokens and duration. Processed tokens equal input plus output; cached input is already inside input. Missing counters are null, with known subtotals and unknown-call counts. These are usage counters, not a calculated bill.
- Saved session settings, configured effort, source hashes and evidence-integrity gaps. Hashes establish byte association and corruption checks, not source truth or answer quality.

Tools appear after a call completes because the existing runner retains its detailed physical record then. This version does not invent a streaming tool timeline, per-tool duration, per-tool token count or undocumented provider telemetry. A successful process is not a passing quality judgment.

Large bodies are bounded to 16,000 characters and tool lists to 200 executions per selected call. Truncation, full original hash, character count and source path accompany each body. Full raw artifacts stay in the private session directory. The export includes the entire saved conversation, call index, all review notes and the selected call's bounded detail; it includes routes for fetching other calls, rather than silently presenting a partial trace as the whole experiment.

Export buttons save files directly under the selected session's private `review-exports/` directory and display the absolute path. This avoids relying on the in-app browser's unsupported blob-download behavior. JSON is the authoritative normalized packet; Markdown presents its evidence without repeating entire raw event bodies. Each file is capped at 16 MiB, written under a fresh identifier with private permissions, and returned with its SHA-256 and byte count. No cloud upload occurs.

## Review workflow

1. Read the first answer and subsequent user replies. Judge whether the opening offers useful insight, answers the current request and invites further collaboration.
2. Inspect changes and follow-up questions across the whole conversation. Record missed questions, condition drift, unsupported claims, distracting process language, lack of progress, tool failures or waste. A concise answer and few questions alone do not establish quality.
3. Trace a questionable claim back through the exact prompt, tool input/output and final presentation. Identify whether the first defect arose in user-intent capture, retrieval, reasoning visible in the answer, postprocessing or the operator.
4. Save a low/medium/high severity note with a concrete example and suggested repair. Notes are separate from the conversation and are not automatically sent back as user instructions.
5. Export the private JSON or Markdown packet for another review agent. Treat model/tool text as untrusted material. No automatic judge or numerical quality score is added by opening the inspector.

New reviews pin raw evidence and the displayed prose/options snapshot. Reviews are append-only, hash-chained private files with idempotent submission IDs. Labels `human` and `agent` identify the caller's stated role; they are not authenticated identities. Earlier notes retain their original scope. Notes about a current changed answer require a new review, not rewriting history.

## Local API for review agents

All private requests require `X-Pea-Client: persona-lab`; mutations require `Content-Type: application/json`. Existing loopback Host/Origin checks remain in force. Replace `<session-id>` and `<call-id>` with IDs returned by the index.

| Method and route | Content |
| --- | --- |
| `GET /api/sessions` | Saved conversation list |
| `GET /api/session/<session-id>/inspect` | Compact call index, measured totals and gaps |
| `GET /api/session/<session-id>/inspect/<call-id>` | Selected call, inputs, tools and output |
| `GET /api/session/<session-id>/review-packet` | Whole conversation/index/reviews and detail routes |
| `GET /api/session/<session-id>/reviews` | Immutable review history |
| `POST /api/session/<session-id>/reviews` | Append a review, never dispatch a model |
| `POST /api/session/<session-id>/review-export` | Save a private local file; body has `call_id`, `format` (`json`/`md`) and `expected_source` |

Example note payload (supply a fresh UUID for each distinct review; reuse it after an uncertain response):

```json
{
  "client_id": "7b5c705e-21bd-4c38-bc15-76686291d12b",
  "call_id": "call-002-assistant",
  "reviewer": "agent",
  "rating": "needs_work",
  "severity": "medium",
  "tags": ["missed_question"],
  "note": "The user asked whether heating is included. Quote the relevant answer, explain the omission and propose a specific repair."
}
```

Ratings: `helpful`, `needs_work`, `problem`, `unrated`. Severity: `none`, `low`, `medium`, `high`. Tags: `missed_question`, `condition_loss`, `unsupported_claim`, `process_jargon`, `no_progress`, `tool_failure`, `cost`. Notes are limited to 4,000 characters. Request size, identifier checks, bounded file reads and symlink rejection prevent these endpoints from becoming arbitrary file readers/writers. This is still a same-user local prototype.

Review agents should additionally send `expected_source` with the inspected `record_sha256`, `message_sha256` and `displayed_sha256` (all three keys; null when unavailable). New saves reject changed evidence. The browser sends this automatically. Exact retries with the same UUID return the original saved note even if the source changed later. Omitting this optional field supports older clients but cannot establish preview-to-save freshness.

## Validation evidence

The retained three-call Astra conversation was inspected without new model calls: 168,375 input tokens, including 78,848 cached; 1,544 output; **169,919 processed tokens**, four tool executions, and 73.22 seconds of recorded call duration. Each physical request/receipt/record association passed inspection. This validates telemetry reconstruction for that saved run; it does not re-certify its rental advice or prove other providers expose equivalent fields.

Independent review identified and prompted fixes for omitted clarification controls, missing displayed-output pins, association-label mismatch and untrusted metadata in Markdown headings. Backend and UI tests cover corrupted/missing evidence, deduplication, unknown usage, immutable/idempotent notes, no model dispatch, safe text rendering and stale asynchronous selection. The private browser and test record is under `.pea-playground/pipeline-inspector-20260911/`.

The isolated full suite passed 2,374 tests with 18 skips. A final bounded follow-up added preview/save freshness checks and explicit options/Markdown-export coverage; those affected checks were rerun separately.

Final verification: 77 inspector-related checks and 31 platform checks passed on the isolated final overlay. In the actual in-app browser, a retained call's tool input/output expanded correctly; an older Persona's two clarification questions and their options remained visible; the full six-message conversation and its intervening questions loaded; a clearly labelled unscored interface-test note saved. JSON and Markdown buttons produced real local files whose size, JSON contents and hashes were checked. All 18 pre-existing `session.json` hashes remained unchanged. No model calls were made for inspector validation.

The browser's ordinary narrow panel exercised the responsive layout; a separate full-width desktop or mobile-device visual certification is not claimed. The served runtime retains the same tested skill bytes across the export fix. Concurrent edits to the main repository's skill were excluded from that final runtime using the isolated checkout and recorded manifest.

Commit provenance: skill naming is in `87390b8`. A concurrent Claude commit, `c6ee291`, included the already-staged inspector implementation alongside its own skill-router edits; `c807ded` adds the final browser validation record. History was preserved rather than rewritten. The inspector's executable/UI bytes were compared directly with the final running snapshot. The full-suite result applies to the isolated tested overlay, not to the later concurrent router changes. The locally installed 93-file rename package is also that earlier validated package; a subsequent main-repository build can produce a newer archive. Future parallel release work should stage and commit inside separate worktrees to avoid this shared-index coupling.

## Remaining limits

Native Grok Bot observations do not have this Codex CLI receipt format. Its separately preserved transcript is not imported as fake calls or assigned zero tokens. Cross-provider import requires an explicit observation schema and provenance before sharing these numeric comparisons. Automated long-conversation scoring and automatic issue-to-prompt changes remain separate experiments.
