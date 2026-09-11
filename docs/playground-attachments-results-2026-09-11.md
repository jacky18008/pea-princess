# File-input delivery and verification

The running localhost test platform now accepts file uploads, drag/drop and explicitly selected local paths for human-led Agent conversations. Files can accompany the first request or a later message. The implementation is in `811a668` on the isolated development branch, applied to main as `844da75`. It does not alter Claude's separate requirements-panel integration.

## Actual actor test

A frozen runtime used GPT-6 Astra at low effort for one bounded call. The browser uploaded a text file and a PNG, then imported a PDF through a local path containing Chinese characters and spaces. Creating the conversation retained all three files and dispatched zero model calls; pressing the research button dispatched the one call.

The answer correctly reported the text document's code and rent ceiling, the PDF's code and rent, and the left/right image colors. An independent reviewer matched the answer to the actual completed shell tool output: it read the selected text, PDF bytes and image pixels. The answers were not present in the prompt. The request's three file receipts matched the physical request and saved human-message metadata; original byte counts and SHA-256 hashes also matched. The PNG alone was marked for native image input. Inspector integrity reported no gaps. No web tool or network command appeared in the retained tool observations.

This establishes access to these three simple supplied files. The PDF contained uncompressed text and the PNG contained two solid colors. It does not establish arbitrary PDF/Office decoding, independent visual reasoning through the image channel, or overall conversation quality. Later-message file handling was tested offline; a real attachment follow-up was not run.

| Recorded usage | Tokens |
| --- | ---: |
| Input, including cached input | 73,622 |
| Cached input, already included above | 48,000 |
| Output | 745 |
| Processed total | 74,367 |

There was one actor call, one physical attempt, no retry and no pending call. The plan allowed at most two calls with an 80,000-token session ceiling. With 5,633 tokens remaining after the first, the optional second call was omitted. These counters are not a billing-price estimate or a zero-token claim about development and independent review. No token-saving or quality-equivalence conclusion follows from this test.

## Offline and browser checks

The full offline run executed 2,429 tests with 18 skips. One failed because the new isolated worktree lacked an ignored historical calibration fixture used by an older ablation test. Copying only its 15 required existing private fixture files restored that dependency; all 12 tests in the affected module then passed. Historical experiments were not rerun against real models.

Focused final checks included 22 storage/security tests, 11 request/receipt tests, six lab integration tests and two UI functional harnesses. Existing lab, runner and review modules also passed. The checks cover exact file bytes, nonregular paths, size/quota bounds, corruption, idempotent retries, empty-text attachment submissions, session-switch races, safe display and evidence binding. Subsequent narrow validation fixes were rerun in the affected modules rather than repeating the entire suite.

Independent review led to three corrections before the live smoke:

- A path quoted in prose can be a prohibition or source data. Automatic import now requires a path-only message; mixed prose uses the explicit path control.
- Original path provenance may legitimately contain a parent component. It is retained unchanged, while the actual supplied snapshot path must be absolute without traversal.
- Filename/path control-character and length validation now agree between storage and the durable runner, preventing late dispatch failures after a successful upload.

The deployed browser accepted and removed a selected file, enabled attachment-only creation, and loaded an existing conversation in the inspector without a model call or browser script error. All 19 pre-existing `session.json` files retained their exact hashes after rollout. Older-version conversations remain readable/exportable; create a new conversation to exercise the changed runtime.

## Evidence and runtime

Private evidence lives in `.pea-playground/file-input-smoke-20260911/`, including the original plan, synthetic files, browser checks, complete actor session, full-suite output, independent-review inputs and before/after preservation hashes. The actor session ID is `d2cde4d94566525ea73d97b9d1c1a714`, under that folder's `sessions/`. These files are excluded from Git and public skill packages.

The actual model test used frozen runtime `20260911T164305Z-cca8f9741359`. The 8765 deployment uses `20260911T164619Z-205f3f7d6cfe`; the intervening main-branch change touched the unrelated `bench/link_probe.py`. Attachment implementation bytes were preserved by the cherry-pick. The deployed browser was checked separately.

Usage and limits: [file-input guide](playground-attachments-2026-09-11.md). General operation: [test-platform guide](persona-playground.md).
