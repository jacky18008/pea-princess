# Research depth and reasoning effort in the test lab

New human conversations explicitly save `standard` research depth and `low` reasoning effort when the caller does not supply choices. The creation and replay forms offer depth `lite`, `standard`, `deep`, and effort `low`, `medium`, `high`. Existing synthetic persona cards supply their own default depth; an explicit selection overrides that card for the new test only.

These are separate controls. Research depth is a baseline instruction for deciding the scope of checks and the depth of shipped tools. It is injected into the actual assistant prompt, including later live turns that regenerate their reference selection. It does not force the model to complete every check, change the user's rental requirements, or establish verified factual coverage. Later explicit user requests to narrow or broaden research take precedence within their scope and remain in the conversation. The UI therefore calls the saved depth a baseline; it does not automatically infer a new machine setting from arbitrary prose.

Reasoning effort is sent through the selected model's `model_reasoning_effort` CLI option. It is no longer unconditionally set to `low` by the lab. This records the requested setting, not hidden reasoning or measured quality. Settings do not change the selected model or token/call limits.

## Stored and exported values

`session.execution_settings` and exported `execution_settings` contain:

```json
{
  "research_depth": "standard",
  "reasoning_effort": "low",
  "research_depth_source": "host_default",
  "reasoning_effort_source": "host_default"
}
```

The forms send the selected values explicitly, so their source is `user_selected`, including when the person keeps the displayed defaults. API callers that omit them receive recorded `host_default` values. An unchanged persona default is `persona_card`.

Every call retains its own `execution_settings` in the pending/call record and in the durable request manifest. The request hash includes these fields and is bound to the physical result. Inspector index/detail records expose `execution_settings` and `execution_settings_evidence`, so reviews and JSON/Markdown exports can distinguish verified binding, missing fields and invalid evidence. Inspector never substitutes the current session's settings for a historical call's missing request metadata. A simulated user's call has research depth `null` with source `not_applicable`; its configured reasoning effort remains recorded.

Historical sessions are not rewritten. A depth actually saved in old persona `runtime_settings.budget_mode` can be shown with source `legacy_record`. Missing values remain `null` / `unrecorded`; neither the public skill's default nor today's CLI settings prove what a historical request explicitly contained. Thus an old export may still show unknown depth or effort after this update. Replaying that conversation creates a separate record with explicit settings, while preserving the original questions, attachments and results.

## Validation and scope

Offline checks cover default/explicit settings, actual prompt injection, CLI arguments, manifest hash binding, invalid-value rejection, replay with different settings, persona applicability and unchanged historical records. UI and Inspector tests cover selection, retry identity, displayed/exported values and unknown history. Browser smoke checks use deterministic callbacks rather than native model experiments. Deployment evidence and test logs remain private under `.pea-playground/settings-ui-20260912/`.

The relevant regression run passed 245 tests: 173 playground checks, 31 persona-playground checks, 9 live-research checks and 32 durable session-runner checks. Independent review passed 15 focused checks; the found persona applicability display issue was fixed. Browser testing created a `deep/high` conversation and replayed it with `lite/medium`; the two callback requests, downloaded conversation JSON and integrity-bound Inspector records agreed. No browser JavaScript errors or native model calls were observed. Callback-only telemetry does not stand in for a real provider usage trace.

This is instrumentation and configuration support. It does not claim improved model quality or token savings. The public skill ZIP remains the same pinned artifact as the preceding rollout; this update changes the test host and adds an explicit depth baseline to its prompt.
