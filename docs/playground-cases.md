# Private evaluation candidates from tester interventions

`tools/playground_cases.py` turns saved mid-conversation questions and scenario amendments into local evaluation candidates. It makes no model calls and does not change the original session, managed state, public feed, or test fixtures. The recorded assistant reply is an observation, not an expected answer or ground truth.

Run from the repository with a session ID shown by the persona lab:

```sh
python3 tools/playground_cases.py --session <32-hex-session-id>
```

For a separate private lab directory:

```sh
python3 tools/playground_cases.py --state-dir /absolute/private/lab --session <32-hex-session-id>
```

The tool prints one JSON object containing the new private file path, pinned session revision, digest and candidate counts. It does not print conversation text. The default filename is `eval-candidates-r<revision>-<source-digest-prefix>.private.json` inside the session directory. An existing output is never overwritten. To make another deliberate snapshot, use `--output-name comparison.private.json`; directory paths and public-looking filenames are rejected. Exit code 2 means validation or publication stopped.

The lab already saves raw input when it enters the queue. Extraction is an explicit local operation; it is not an automatic data upload or training pipeline. A running lab may advance immediately after extraction, so each output identifies the particular revision and bytes it read. Re-run against a later revision to include a subsequently saved reply.

## What each candidate preserves

- Exact intervention text, selected `question` or `amendment` kind, and client intent ID.
- Source action and queue pointers. Repeated records of one identical intent become one candidate; identical text sent under two different intent IDs remains two candidates.
- A transcript range ending just before the applied human message, when the association is supported by the saved record. Ranges use zero-based indexes into the output's shared `transcript`; `end_exclusive` excludes the intervention itself. Keeping one shared transcript avoids repeating private text many times.
- The immediately following assistant reply, if it is explicitly a reply to a human intervention and its association is consistent.
- Saved model name, implementation source hashes, persona/fixture/system hashes and runtime settings. These are recorded versions, not a claim that the current checkout still matches them. Full hidden persona scoring criteria are not copied into candidate prompts.
- A unique matching usage receipt reference where one exists; otherwise `usage_ref` is null. The shared `calls` collection retains original receipt data, including unknown usage, failures and physical record hashes. Referenced external files are not followed or reopened.

All candidate IDs are stable for a session and client intent. The private output has its own `{sha256,value}` envelope. Its source includes both the original envelope file digest and the original value digest; the source bytes remain untouched.

## Answer and association states

| Status | Meaning |
|---|---|
| `answered` | A saved assistant reply is structurally associated with the applied input. This does not assess correctness. |
| `queued` | The intent is still present in the saved inbox. It has no claimed resulting reply. |
| `unknown` | The input was recorded, but its applied position or reply cannot be established reliably. Interrupted and failed steps can produce this state. |

Existing version 1 transcripts do not attach client IDs to every human message. For those records, the extractor requires an exact match of the entire applied intent sequence against the human-message sequence, including text and kind. It labels the result `exact_fifo_legacy`. It does not search for the same words elsewhere and assume a match. Optional explicit message/reply IDs are checked when present; disagreement does not produce an answered candidate.

Queue-time transcript boundaries were not recorded by this UI version. For a queued item, `preceding_transcript` is therefore null. `context_at_snapshot` points to the saved conversation and explicitly says it may contain messages produced after enqueueing. For an applied item, the range is the conversation before application, not necessarily the browser content visible at the time the user clicked Send.

If two physical receipts contain identical answer text, the extractor preserves both in `calls` and leaves the candidate's usage reference unknown unless an explicit call ID resolves the ambiguity. It never converts missing tokens into zero or treats an observed reply as quality acceptance.

For `choices-v1` replies, the raw provider artifact is JSON. The extractor uses the versioned strict decoder to reconstruct the exact visible message and options before matching a receipt, and checks any saved display fields for agreement. It records the decoder hash. A malformed reply, disagreement or ambiguous duplicate still leaves the usage association unknown; original raw receipts remain intact.

## Privacy and integrity boundary

Outputs contain the original private text and can contain personal details. They are not anonymized. Keep them in the ignored `.pea-playground/` directory or another private location. No public export or publication option exists. Promotion into a shared benchmark requires a separate deliberate curation step: define the desired behavior, evaluate evidence and remove identifying content before any authorized sharing. This tool does not claim to complete that work.

The reader checks the lab envelope digest and intent dedupe hashes. It rejects duplicate JSON keys, invalid numeric constants, unsupported identities, path traversal, symlink components, hardlinked input files and artifacts owned by another user. Source filenames inside metadata are only references. It reads one bounded session snapshot, then publishes a new complete file with mode `0600` using an atomic no-overwrite operation. Size limits fail without truncating inputs or deleting old records.

These checks detect accidental corruption and unsafe local paths. Hashes and file permissions are not encryption or authentication against another process running as the same user. Conversation text remains untrusted data, including any instructions it contains. Future evaluation code must preserve that boundary.

Offline validation:

```sh
python3 -m unittest discover -s tests -p 'test_playground_cases.py'
```
