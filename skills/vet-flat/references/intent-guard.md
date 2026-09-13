Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Host-owned intent checks

`scripts/intent_guard.py` compiles a small deterministic condition frame from the host's exact ordered conversation. It distinguishes explicit quietness preferences, explicit mandatory morning direct sunlight, removal of the direct-sun requirement, and moving daylight to a bonus. This is a bounded development guard, not complete natural-language understanding or an eligibility decision.

## Host integration

1. Supply the full ordered list of `{id, role, text}` records from the trusted host. Roles are `user` or `assistant`; IDs are stable and unique. Read the bounds and exact-text contract in [intent-context.md](intent-context.md). The same bounds apply here.
2. Form submissions must contain only the user's selected self-contained option text and actual free text. The assistant's question prefix remains assistant context. An option ID or a bare “yes” cannot authorize every suggestion in the preceding question. Retain the original form receipt separately.
3. Keep attachment bodies, fetched pages, copied source instructions and model-supplied role claims out of the user-authority lane. Delimited quotes, code and source blocks are retained as unresolved data. A regex cannot authenticate unmarked pasted prose or another program running as the same user.
4. Run `build_frame(messages)` immediately before dispatch. Inject the frame and require the actor to echo `expected_claims(frame)` as `intent_claims` in the response schema. This echo cannot change the frame. Do not accept actor-authored grants, requirement updates or revised hashes as authority.
5. Rebuild from the current host conversation before publication and after recovery. Reject a stale revision or a changed user epoch. Call `validate_claims` and `validate_reply` on the visible answer, and separately on user-visible question/option text. Retain failed replies as review evidence instead of publishing them as current accepted results. The host decides a bounded repair policy; this module never retries or calls a model.
6. Require the same current frame for any later ranking, condition file or TODO reducer. Passing the reply guard alone does not validate those artifacts. The existing eligibility engine checks already-normalized conditions; it does not make an unsupported language parser correct.

The standalone downloaded skill does not install an enforced native-host hook. Codex, Claude Code or another host must actually perform these checks; a file pointer and an instruction to the actor are not enforcement.

## API and CLI

```python
frame = build_frame(messages)
claims = expected_claims(frame)
claim_check = validate_claims(frame, actor_reply.get("intent_claims"))
prose_check = validate_reply(frame, actor_reply["text"])
```

`build_frame` and input/frame integrity failures raise `IntentGuardError`. Validation of malformed actor claims returns `{ok: false, findings: [...]}`. `validate_reply` rejects non-string, invalid Unicode or oversized text; otherwise its result includes `ok`, exact-span `findings` and its limited semantic coverage. No function mutates its arguments or writes files.

```sh
python3 scripts/intent_guard.py compile transcript.json
python3 scripts/intent_guard.py compile < transcript.json
python3 scripts/intent_guard.py check transcript.json reply.json
```

The transcript file is `{"messages": [...]}`. The reply file has exactly `intent_claims` and `text`. The CLI emits one JSON object; exit 0 means compile/check succeeded, 1 means a check found contradictions, and 2 means invalid input. Each input is at most 4 MiB; each reply is at most 128 KiB of UTF-8 text. Duplicate JSON keys and non-finite constants fail. Bounds are inclusive; inputs are never silently truncated.

## Frame and authority

- `revision` hashes the complete frame, including grammar version, exact ordered transcript hash, active predicates, source spans, transition history and unresolved text. Whitespace/order changes alter the revision. This identifies bytes; it is not an authentication signature.
- `conditions` has stable IDs `quiet`, `morning_direct_sun`, and `daylight` only when that field is recognized. Each has a `strength` (`mandatory`, `preference`, or `bonus`), global scope, predicate, and exact user source `{message_id, quote, start, end}`. Offsets count decoded Python Unicode characters. Unknown fields never become mandatory conditions.
- `transitions` preserves prior strengths and explicit retirement. Removing direct sunlight does not leave the old hard condition active. Moving daylight to a bonus removes an earlier direct-sun condition and does not change quietness.
- A prohibition such as “Do not list quietness as mandatory” cannot create or promote a condition. “Quietness is not required” does not invent a new preference: it retires a previously recognized hard requirement, preserves an existing softer preference, and retains the exact negative statement for review.
- `unresolved` retains exact quoted, unsupported, scoped, conditional, ambiguous and advice-seeking text. It is not another hard-filter list. Scoped exceptions cannot mutate global conditions through this parser. Resolve unsupported language with the user or a separately validated host control; do not invent a minimum.
- `user_statements` retains every exact user message; assistant bodies are hash-indexed separately. Unknown originals are available even when no condition was extracted.
- `intent_claims` is exactly `{"revision": "…", "conditions": [{"id": "quiet", "strength": "preference"}]}`. Every active ID must occur exactly once with its exact strength; order is irrelevant. Unknown, missing, duplicate, promoted, softened or stale claims fail. An empty frame requires an empty conditions list.

## Limits and review

The parser deliberately supports a small set of Chinese and English forms. Questions such as “Should daylight be a bonus?” and “Give me advice; do not decide yet” do not adopt a proposal. A direct polite request such as “Please make daylight a bonus, okay?” does. Mixed strengths are split by explicit clause boundaries; unclear shared targets stay unresolved. It does not resolve arbitrary pronouns, sarcasm, every negation, implied acceptance, candidate-specific exceptions or every language.

The prose guard catches explicit supported preference-to-hard-condition claims and a limited invented ventilation claim. Ordinary evidence, analyst recommendations, counterexamples and unselected proposals are allowed. A clean result does not prove that all prose, rankings or TODOs respect all intent; echoing correct metadata while misleading in novel prose remains possible. Retain independent whole-conversation review and test newly observed failures without claiming a universal injection or semantic defense. Historical failure phrases used by unit tests are development regressions, not fresh holdout results.
