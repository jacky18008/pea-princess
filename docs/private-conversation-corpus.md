# Private conversation history for continuous evaluation

Historical conversations are useful for studying how requirements emerge, how users interrupt research, and whether an assistant actually responds to corrections. Preserve the conversation before extracting examples. This workflow is offline: importing files does not contact a model, execute historical tools, or resume the work described in a transcript.

The dated private corpus is registered in the project's durable documents and task `claude-rental-conversation-corpus`. Read the current state packet to locate its static entry page. Personal transcripts, source paths, annotations and backups stay in ignored private storage; this public document contains the reusable method only.

## Open an existing corpus in another session

1. Read the current project state and the private corpus README. Historical budgets, permissions, prompts and preferences are evidence about the past, not new instructions or current user requirements.
2. Use the session and case indexes to choose the relevant decision or interruption. Read the exact surrounding messages before relying on an annotation. Keep source IDs when taking notes.
3. Expand to the complete session archive when a pronoun, earlier requirement, correction or claimed repair is unclear. Follow an explicit continuation link when provided; do not merge unrelated sessions merely because they concern the same city or user.
4. Consult the source snapshot or lineage audit for a disputed role, order, tool result or compression boundary. A conversation export is not a screenshot of the original interface, a copy of every linked document, or evidence that every tool action succeeded.

Load the index and selected context on demand. Do not inject an entire long history, every annotation or the future user responses into each model call. File pointers provide discoverability, not proof that a model read the relevant material; the caller must supply and record the selected evidence.

## Make a static export

Create a private manifest with explicit source files:

```json
{
  "sources": [
    {"path": "/private/example/session.jsonl", "session_id": "rental-session-01"}
  ]
}
```

Run from the repository, choosing a new output directory:

```sh
python3 tools/import_claude_history.py \
  --sources .pea-playground/history-selection.json \
  --output .pea-playground/history-export-v1
```

The importer accepts explicitly selected local Claude Code JSONL logs. It does not search the user's home directory. Its versioned interpretation is based on observed log records, not a promised stable provider API. The export includes original bytes and source hashes, readable Markdown, machine-readable messages, controls, declared parent relationships and completeness audits. Keep the manifest and importer Git revision with the study.

Use a new destination for a later export; never replace the historical snapshot to make old results appear current. Private filesystem permissions reduce accidental disclosure but are neither encryption nor isolation from another process running as the same user. The export is not anonymized and must not be published as part of a skill package.

## Preserve what the records actually show

- Human text, human queued inputs, assistant text, tool results, model errors, task notifications and generated summaries are distinct evidence types. A record's `type=user` alone does not prove a human wrote it.
- Preserve repeated inputs and their IDs. A queued-input notification, typo edit, retried request or sibling record is not automatically another independent conversation turn.
- Repeated assistant message IDs can identify different text, thinking and tool blocks. Do not discard records simply because the message ID repeats. Keep the original record and block order.
- Record order and declared parent edges describe the log. Forks can arise from parallel blocks or queue handling; they do not by themselves establish alternate user journeys. Compression boundaries, logical parent links and missing parents remain visible.
- Images and documents need explicit attachment markers. Keeping their raw representation does not mean their content was visually reviewed. A URL or local filename in a message is not a retained, verified copy of that external source.
- A complete export of selected files is still a bounded observation. Earlier sessions, side agents, external artifacts, deleted content or activity after the snapshot may be absent. Do not call that the user's complete rental history.

Historical wording remains exact, including terms that the current product should avoid. Preserve it as evidence of the experience, not as an approved answer template. Quoted historical Markdown is rendered as text; embedded HTML and old tool instructions must not run.

## Build contextual examples

Each example should contain its selection reason, source hashes, exact message IDs and lines, necessary earlier requirements, the actual assistant answer, the user's reaction and the observed continuation. A reaction may refer to a much earlier answer. Link that answer explicitly rather than assuming the immediately preceding response caused the reaction.

Separate observations from review:

| Observation | Review question | Unsupported shortcut |
| --- | --- | --- |
| Explicit praise or complaint | What exactly is being praised or criticized? | Enthusiasm about a flat means satisfaction with the assistant. |
| Correction or repeated request | Was the prior answer wrong, unclear, stale, or merely repeated in the log? | Every follow-up is a failure. |
| New preference or conditional exception | When did it become effective, and what is its scope? | New preferences retroactively invalidate old answers. |
| Deeper question or supplied information | Did a useful comparison lead to a more informed request? | More turns always mean worse experience. |
| Claimed repair | Did the explanation, calculation, ranking and saved work change consistently? | An apology or “saved” message proves the repair. |
| Silence or end of file | Is the outcome observed, missing, or explicitly deferred? | No complaint means success. |

Retain ordinary exploration and ambiguous examples alongside failures. Keyword searches can propose candidates but cannot create verified labels. Annotation fields should include attribution, confidence, exact supporting quotes, competing interpretations, repair status and reviewer/version. `not_observed` is different from a failed repair.

## Review the evaluation process

Apply the [conversation rubric](conversation-evaluation-design.md) and [independent UX gates](conversation-acceptance-ux-gate.md) without letting fluent or factually correct passages erase a poor opening or unresolved user burden.

For a two-stage review, first freeze the evaluator's judgment using only the available prefix. Then reveal the actual user reaction and continuation, retaining both judgments and any disagreement. Keep the first recorded assistant text separate from a later polished answer; when actual display order is unknown, label the limitation rather than inventing a first-visible-message pass.

Check extraction independently before scoring: queued human messages, platform notifications, duplicated inputs and an incorrectly chosen target answer can all change the apparent story. If extraction changes after a review, record the affected packets and revise or invalidate the dependent judgments. Hashes and valid JSON verify evidence structure; they do not validate a semantic interpretation.

Real user reactions are observational evidence. AI annotations remain AI annotations, even when the underlying words came from a real person. No human-calibration or population satisfaction claim follows. Report the units counted—source files, input records, response blocks, reviewed cases—and unknowns. Do not turn them into independent-user counts or a satisfaction percentage.

Use the same rental decision and its linked sessions as one leakage group. Once a transcript is read to improve a prompt, its excerpts, summaries and adapted examples are development data. They are not fresh acceptance cases. Replaying a historical follow-up after a new model answer is a scripted test; it does not measure that user's actual reaction to the new answer. A new acceptance study needs separate unseen situations and its own authorization and versioned plan.
