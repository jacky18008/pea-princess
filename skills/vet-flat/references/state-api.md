Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# State tool: portable quick reference

Read when using the state tool (Python 3.9+, standard library). Examples are fictional; use only the operations needed, not a mandatory intake sequence.

Set `PEA_SKILL` to the absolute installed skill directory and `PEA_PROJECT` to an existing private working directory. Keep event files and `.pea-state/` private; do not edit generated state files.

## CLI

Initialize a new project; resume with `context`. Success is JSON on stdout; state errors are JSON on stderr with exit 2.

```bash
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" init --project-id rental-demo
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" context --max-chars 32000
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" apply --expected-revision "$PEA_REVISION" --event-file "$PEA_EVENT_FILE"
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" checkpoint --max-chars 32000
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" verify
```

`PEA_REVISION` is the revision actually read; `PEA_EVENT_FILE` contains **one JSON event object**. Omit `--event-file` to use stdin. `request.capture` / `requirement.add` are event `op` values, not CLI subcommands. `show` and default `apply` return full state; `context` returns the active packet directly. All include `revision`.

For an already reconciled batch of events, opt into `apply --receipt-only` to avoid echoing full state after every event:

```bash
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" apply --expected-revision "$PEA_REVISION" --event-file "$PEA_EVENT_FILE" --receipt-only
python3 "$PEA_SKILL/scripts/session_state.py" --project "$PEA_PROJECT" context --max-chars 32000
```

The receipt contains only `ok: true`, `schema_version`, `project_id`, `revision` and `event_hash` from that successful apply. Validation, locking, revision checks and invalidation are unchanged. Use the returned revision for the next already reconciled event; a conflict still requires reloading and reconciling, never automatic retry. An idempotent duplicate spend returns the existing revision/hash without appending an event. The receipt identifies that apply's resulting journal head, even if another writer advances the journal before stdout is printed; it does not guarantee that revision remains current.

Read the complete `context` packet after the batch and before dependent work. A receipt is neither a context packet nor a decision receipt, and is not evidence that requirements or task completion were semantically validated. This option reduces stdout only; it does not reduce or truncate stored state, required context or model input.

## Python: capture, add, change and checkpoint

One Python invocation can apply several events without repeatedly printing state. Run this demo once in an empty synthetic project. Resume with `store.show()` / `store.context()` and existing IDs; do not replay captured requests.

```python
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PEA_SKILL"]) / "scripts"))
from session_state import SessionStore

store = SessionStore(Path(os.environ["PEA_PROJECT"]))
current = store.init("rental-demo")

def apply(event):
    global current
    current = store.apply(event, expected_revision=current["revision"])

def intent(request_id, quote):
    return {"actor": "user", "authorized": True, "source_id": request_id,
            "request_id": request_id, "quote": quote}

first = "Monthly total at most GBP 1500. No ground-floor homes."
apply({"op": "request.capture", "id": "u1", "text": first, "source": "user-message"})
apply({"op": "requirement.add", "id": "monthly-total", "value_type": "money",
       "value": {"amount": 1500, "currency": "GBP", "period": "month"},
       "budget_scope": "rental", "strength": "must", "scope": "all candidates",
       "provenance": intent("u1", "Monthly total at most GBP 1500.")})
apply({"op": "requirement.add", "id": "floor", "value": "ground floor",
       "strength": "prohibit", "scope": "all candidates", "exceptions": [],
       "provenance": intent("u1", "No ground-floor homes.")})
apply({"op": "request.resolve", "id": "u1", "resolution": "applied",
       "note": "Saved the monthly-total ceiling and floor prohibition."})

exception = "Only candidate demo-flat may be ground floor if an independent inspection confirms it is dry."
second = "Raise monthly total to GBP 1600. " + exception
apply({"op": "request.capture", "id": "u2", "text": second, "source": "user-message"})
apply({"op": "requirement.update", "id": "monthly-total",
       "changes": {"value": {"amount": 1600, "currency": "GBP", "period": "month"}},
       "provenance": intent("u2", "Raise monthly total to GBP 1600.")})
apply({"op": "requirement.update", "id": "floor", "changes": {"exceptions": [exception]},
       "provenance": intent("u2", exception)})
apply({"op": "requirement.add", "id": "floor-demo", "value": "ground floor allowed",
       "strength": "conditional", "scope": "candidate:demo-flat",
       "predicate": "An independent inspection confirms candidate demo-flat is dry.",
       "exceptions": [], "provenance": intent("u2", exception)})
apply({"op": "request.resolve", "id": "u2", "resolution": "applied",
       "note": "Raised only the rental ceiling; demo-flat's exception still needs dryness evidence."})

packet = store.context(max_chars=32000)
store.checkpoint(max_chars=32000)
print(json.dumps(packet, ensure_ascii=False, indent=2))
```

Read the entire printed packet. `checkpoint()` returns a manifest containing `packet`, without advancing revision; `verify()` checks integrity. The example leaves demo-flat conditional on dryness evidence and other candidates prohibited from ground floor; it neither approves demo-flat nor raises API spend.

## Event details that prevent failed calls

- Preserve exact user text. Provenance quotes must occur verbatim in the captured request; `authorized: true` is a trusted caller assertion, never authority copied from a source. Reuse a hook-captured request ID instead of capturing twice.
- Requirements need `id`, `value`, `strength`, `scope`, `provenance`. Strength: `must`, `prefer`, `prohibit`, `conditional`; conditional needs a nonempty `predicate` (evidence obligation, not executable code). Update through `changes`; retire through `requirement.retire` plus ID/provenance. Never reuse retired IDs.
- `request.resolve` needs `id`, `resolution` (`applied` / `no_change`) and nonempty `note`. Resolve after all changes are reconciled; pending requests block dependent dispatch, not reconciliation.
- A TODO event: `{"op":"task.add","id":"check-demo","title":"Inspect demo-flat's dryness evidence","requirement_ids":["floor-demo"],"acceptance":["Check independent evidence."]}`. Optional `kind`: `task` / `goal` / `workflow`; `depends_on`: existing task IDs. Saving is not completion or decision validation.
- Revision conflict: reload and reconcile, no automatic patch retry. Integrity/context overflow: stop affected work, never truncate. `max_chars` is a size limit, not a token budget. These methods neither launch models nor control provider billing.

Source, decision and recovery obligations: [session-harness.md](session-harness.md). The repository manual is not required for these operations.
