Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

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
