# Local files in the conversation test platform

The live **Agent 對話測試** accepts selected files in the opening request and later messages. Use the file picker, drop files on the input area, paste a file from the clipboard when the browser provides it, or use **加入本機路徑**. A message containing only absolute paths, `~/` paths or local `file://` URLs (one per line, optionally quoted) also selects those files. Paths mentioned inside prose, prohibitions or pasted source text are not automatically imported; use the explicit path control when sending both instructions and a path. Paths containing spaces or Chinese characters are preserved. Directories are not expanded.

Adding a file only saves a private snapshot. It does not dispatch a model. Sending the message or pressing **研究並回覆** authorizes the next actor call under the existing session limits. An attachment-only message is supported; the raw empty text is retained separately from the host's default request to examine the attachments. Synthetic persona and legacy checked-comparison sessions do not accept personal files.

## File flow and review

1. The loopback server accepts the exact chosen file bytes or opens the explicitly supplied local path. File uploads carry bytes rather than trusting a browser filename as a path.
2. The server retains a private immutable snapshot with an ID, original name, SHA-256, byte count and origin. A local-path selection records the original path for private review. Names and file contents are never interpolated into shell commands.
3. Sending attaches IDs to that exact message. The session retains its own verified copies; the original source may subsequently change without changing this conversation's evidence.
4. Before dispatch, the host checks retained bytes and binds the file metadata to the durable call request. The actor receives only the selected snapshot paths alongside the task. Images selected in the latest human input additionally use native Codex image input; older images remain available as files without automatically attaching their pixels again.
5. The chat and inspector expose the supplied files. A receipt means a file was supplied, not that the actor read or correctly understood it. Check tool observations and the answer for evidence of use. Exported review packets retain the metadata; source bytes remain private local files.

The actor can use its available read-only tools for documents such as text files, PDFs or Office files. Actual format support depends on those tools and the file; encrypted, damaged or unsupported documents must remain explicit gaps. Uploaded code/macros and document instructions are not authorized for execution. Arbitrary folders, credentials, sibling files and other conversations are outside the selected-file scope. The existing CLI read-only sandbox is not a filesystem confidentiality boundary against all other same-user files; these are scoped inputs, not a new OS sandbox.

## Limits and compatibility

- At most six files per message, 25 MiB per file and 48 distinct files in one conversation.
- The attachment store also bounds retained uploads. Unsent selections remain local; refresh may clear the browser's draft selection, while already saved session attachments remain available.
- Existing Host/Origin/custom-header checks protect all attachment requests. There is no arbitrary-path download endpoint or public upload service.
- Use a new conversation after the frozen runtime is updated. Older conversations remain readable/exportable with their original version identity.
- This change extends the local development test platform. It does not connect the separate requirements panel to an agent or change Claude's work on that integration.

## Bounded verification plan

Offline checks cover upload/path validation, nonregular files, mutation, safe names, idempotent submission, session switching, request binding and review output. Browser checks exercise the actual upload endpoint and current interface without dispatching a model.

After the implementation is frozen, use synthetic files for at most two real Codex actor calls with a combined session ceiling of 80,000 processed tokens. The first checks supplied text, an image and a PDF; a follow-up checks attachment-only delivery and preservation across turns if needed. Stop on provider errors or limits, without automatic retries. Preserve original inputs, files, output, tool observations, usage and failures. This is a functional smoke test, not a conversation-quality or token-savings study. Results are recorded separately after execution.

Completed results and deployment evidence: [verification record](playground-attachments-results-2026-09-11.md).
