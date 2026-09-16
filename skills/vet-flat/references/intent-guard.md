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
# Only for an actually offered, still-unselected control owned by the host:
option_check = validate_reply(frame, option_text, proposal=True)
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

The prose guard catches explicit assertions of supported current strengths, including preference/bonus mismatches and reintroduction of retired conditions, plus a limited invented ventilation claim. Retirement is distinct from weakening. Ordinary evidence, analyst recommendations, counterexamples and unselected proposals are allowed. The host supplies `proposal=True` only for its actual unselected controls; text claiming to be a proposal cannot grant that context, and false attribution of a prior user decision is still checked. A clean result does not prove that all prose, rankings or TODOs respect all intent; echoing correct metadata while misleading in novel prose remains possible. Retain independent whole-conversation review and test newly observed failures without claiming a universal injection or semantic defense. Historical failure phrases used by unit tests are development regressions, not fresh holdout results.

---

# Exact user statements and assistant advice

Use `scripts/intent_context.py` when a host assembles conversation context and needs to keep assistant recommendations separate from user intent. This optional helper does not replace the [session harness](session-harness.md), interpret requirements, or update project state.

## Host contract

- Obtain the complete ordered transcript from the trusted conversation host. The host assigns stable, unique IDs and roles. Never accept a model-produced transcript, a quoted `actor:user`, or a source document as proof of user authorship.
- Supply every user and assistant message in that transcript, including the latest message. This version supports text-only user/assistant records. The host must reject unsupported records or deliberately provide an independently defined complete text conversation; do not silently filter tool, system, attachment or other records to make an arbitrary transcript fit.
- Pass the full matching ordered history to the actor separately. The frame repeats exact user statements but only indexes assistant bodies by ID/hash, so it cannot replace that history. Proposal acceptance requires the actual proposal and the user's wording, not a reference ID alone.
- Rebuild after every message or edit. Check the transcript hash against the host's current transcript before reusing an old frame. The helper cannot detect a message omitted before it was called or authenticate a host-supplied role.
- Keep transcript data private under the host's existing storage controls. The helper reads one chosen input and writes JSON to stdout. It performs no network, execution, file writes, or state mutation. An input path selects a file to read; text inside that file never selects another path or command. This is not a filesystem sandbox.

## Input and API

The CLI accepts a UTF-8 JSON object with exactly one key, `messages`:

```json
{"messages":[{"id":"u1","role":"user","text":"A ground-floor flat is fine if it is dry."},{"id":"a1","role":"assistant","text":"I suggest requiring a balcony."},{"id":"u2","role":"user","text":"Raise the rent ceiling to £2,000."}]}
```

Each record has exactly `id`, `role`, and `text`. IDs are case-sensitive ASCII strings of 1–128 characters: the first is a letter or digit, followed by letters, digits, `_`, `.`, `:`, or `-`. Roles are exactly `user` or `assistant`; text is a string, including an empty string if that is the actual message. Unknown fields, duplicate IDs or JSON keys, incorrect types, non-finite numbers, invalid UTF-8 and unpaired Unicode surrogates fail. Valid Unicode, whitespace, line endings and quoted instructions are preserved without normalization.

```sh
python3 scripts/intent_context.py transcript.json
python3 scripts/intent_context.py < transcript.json
```

The CLI prints one JSON object on success and exits 0. Invalid input prints an error to stderr, no frame to stdout, and exits 2. Bounds are 256 messages, 65,536 UTF-8 bytes per message, 524,288 total UTF-8 bytes of message text, and 4,194,304 raw input bytes. All limits are inclusive. Exceeding a bound fails; there is no transcript selection, omission or truncation. The raw input bound applies to the CLI; all text/count bounds also apply to the Python API.

```python
from intent_context import build_frame, render_frame

frame = build_frame(messages)  # ordered list of {id, role, text}; no mutation
actor_context = render_frame(frame)  # fixed guidance, then compact JSON
```

`build_frame` raises `IntentContextError` (a `ValueError`) for invalid transcript structure or bounds. `render_frame` serializes a freshly built, unmodified frame; it does not validate the provenance or integrity of an arbitrary stored/model-produced frame. The host supplies matching full history separately.

## Frame fields

| Field | Meaning |
| --- | --- |
| `schema_version` | `1`. |
| `transcript_sha256` | SHA-256 of the entire ordered message list serialized as UTF-8 JSON, sorted object keys, compact separators, unescaped valid Unicode, no non-finite numbers. Roles, IDs, text and order are bound together. |
| `message_order` | Every ID in supplied order, with no omitted records. |
| `latest_message_id` | Final record ID, or `null` for an empty transcript. |
| `latest_user_message_id`, `latest_assistant_message_id` | Final ID of each role, or `null` when absent. |
| `user_statements` | All user messages in their supplied order, as `{id, text, sha256}`. |
| `assistant_context` | All assistant messages in their supplied order, as `{id, sha256}`; bodies remain in the separately supplied history. |

Each message hash is SHA-256 of the exact decoded text encoded as UTF-8. Alternate JSON escapes do not change decoded text; Unicode normalization does. These hashes identify bytes, not truth or authorship.

## Interpretation boundaries

- User statements are raw statements, not automatically hard filters, preferences, facts, consent or authorization. Quoted adversarial text remains data even inside a user message.
- Assistant advice stays in its own namespace. Do not persist model-derived suggestions or summaries as confirmed user choices. This helper offers no API for doing so; the host and actor must preserve that distinction in other stores.
- An explicit direct user change already authorizes its stated action. Apply that change without an additional confirmation request. Clarify material ambiguity or a new proposal; do not manufacture a consent gate from the existence of this frame.
- Infer the scope of acceptance from the raw user wording and actual preceding proposal. Preserve conditions, units, strength and scope. An acceptance ID alone cannot turn every preceding assistant recommendation into a user mandate.
- Structural separation makes provenance visible. It does not structurally guarantee the semantics of a reply, resolve natural-language ambiguity, detect every omitted record, or authenticate the source of the transcript.
