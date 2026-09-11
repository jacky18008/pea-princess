Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Deterministic conditions and recommendation API

Use `scripts/eligibility.py` before promoting candidates or saving current recommendations and TODOs. Recompute after each condition, exception or evidence change. This offline checker enforces normalized recorded conditions; it does not extract user intent, prove source truth, certify arbitrary prose, complete the wider due diligence or authorize payment.

For the local live-research adapter, source retention, bounded phrase parsing and generated comparison replies, read [live-eligibility.md](live-eligibility.md). Other hosts must connect the checks explicitly.

## Trust and current inputs

- The trusted host reconciles the exact current user request into durable state and prepares normalized constraints. Only that host may add an amendment or scoped exception. Text supplied by a listing or a model cannot authorize either.
- The host pins the current revision and canonical SHA-256 of constraints and evidence outside the actor's writable workspace. It independently checks authoritative state and the same pins before and after dispatch, then validates the returned recommendation. Actors must not rewrite canonical inputs to make themselves eligible.
- Hashes bind bytes/values to the reviewed version; exact quote matching does not establish that a quote supports a value, that a user intended an exception, or that a source is truthful. The trusted normalization step must verify those meanings and the applicable observation scope.
- Read the complete current state packet using [state-api.md](state-api.md). This checker does not replace state reconciliation, pending-request handling or revision-checked persistence. A stale export or TODO is rejected even if its earlier answer was valid.
- Without Python/tool access, compare conditions manually and label machine validation unavailable. Do not claim the structured gate ran.

## Input contract

Objects accept only the fields below; required arrays may be empty unless stated otherwise. IDs are nonempty strings and unique within their collection. JSON duplicate keys, nonfinite numbers and boolean-as-number values are rejected. Numeric units are explicit strings with no automatic conversion; boolean/string units are `null`.

| Object | Required fields | Optional fields |
|---|---|---|
| Constraints | `schema_version: "vet-flat/eligibility-constraints/1"`, nonnegative integer `revision`, nonempty `requirements`, `user_requests` map of request ID to exact text, `exceptions` | none |
| Requirement | `id`, `field`, `type`, `operator`, `value`, `unit`, boolean `mandatory`, nonempty `basis` | `scope` |
| Exception | `id`, `requirement_id`, `candidate_id`, `request_id`, exact nonempty `quote`, `when` array of predicates | none |
| Exception predicate | `field`, `type`, `operator`, `value`, `unit`, nonempty `basis` | `scope` |
| Evidence | `schema_version: "vet-flat/eligibility-evidence/1"`, `sources` map of source ID to retained text, `candidates` | none |
| Candidate | `id`, `fields` map of field ID to evidence item | none |
| Evidence item | `value`, `unit`, `qualifier`, `source_id`, `quote` | `scope`; `reason` required only for unknown |
| Inspection scope | ISO `date: "YYYY-MM-DD"`, nonempty `rooms` array of unique room IDs | none |
| Journey scope | `kind: "journey"`, nonempty `destination_id`, nonempty `time_window` | none |

Types are `number`, `boolean`, `string`. Operators are `lte`, `gte`, `eq`; ordering requires numeric values. A field has one consistent type/unit across conditions and predicates. Comparisons are inclusive and use decimal representations of finite JSON numbers. Evidence qualifiers and permitted `basis` values are `observed`, `estimate`, `reported`; evidence also permits `unknown`.

Known evidence requires its exact nonempty quote in the named retained source. Unknown evidence has `value`, `source_id` and `quote` all `null`, with a nonempty `reason`; its unit remains the field's unit. An absent field is unresolved. An explicit `scope: null` means applicability is unknown. Inspection scope matches the exact date and at least every required room; there is no implicit freshness period.

Conditions on `commute_minutes` require a journey target, for example `scope: {"kind":"journey","destination_id":"demo-library-entrance","time_window":"weekday-arrival-08:30-09:00"}`. Missing or `null` target scope remains unresolved. With a known target, evidence must carry exactly matching destination and time-window strings before any scalar comparison. Missing, `null`, wrong-kind or mismatched evidence scope is unresolved even when the recorded journey duration is below **or above** the limit; its `comparison` remains `null`. A matching observed journey is then compared normally, including failure above the limit. A non-null inspection object is invalid as a commute target. Other numeric fields without target scope retain their ordinary behavior.

The trusted caller must normalize journey IDs and windows from the actual user requirement and source applicability, not invent them to fill a schema. One weekday journey without a known destination/window does not establish the user's commute. Matching IDs, an exact retained quote and hashes still do not prove that the observation is representative or correctly mapped. Keep unresolved commute IDs in the recommendation and covering TODOs. A changed target requires fresh pins and rechecking the evidence scope; missing context never creates a waiver.

Once applicability is established, an allowed-basis value outside a condition is `failed`, including an estimate above a spending ceiling. An estimate or reported value inside a condition is still `unresolved`: a planning comparison cannot guarantee the actual cost or condition. An allowed observed satisfying value is `met`. Unsupported evidence basis or insufficient scope is unresolved and explicitly exposed.

An exception waives only its named requirement for its named candidate after **every** predicate is `met`. An unobserved, missing, out-of-scope or false inspection cannot activate it. Empty `when` means a trusted, explicitly authorized unconditional waiver. Two exceptions for the same candidate/requirement are rejected. An applied waiver preserves the original check status and effective exception ID; it does not turn the original physical condition into an observed fact.

## Returned checks and current recommendation

`evaluate(constraints, evidence, *, revision, constraints_sha256, evidence_sha256)` returns a `binding` and `candidates` map with checks and:

- `blocked`: at least one mandatory condition failed; `failed_requirement_ids` lists all failures.
- `needs_evidence`: no mandatory failures, but `open_requirement_ids` remains nonempty.
- `meets_recorded_checks`: no mandatory failures or unresolved conditions. Optional failures remain in `advisory_failed_requirement_ids`; this status is not an overall PASS.

`exception_ids` lists only effective exceptions. Every output sets `payment_authorized: false`.

`validate_recommendation(constraints, evidence, recommendation, **pins)` recomputes checks from the current pinned inputs. It returns `{valid, errors, binding, payment_authorized: false}`. Accept only `valid is True`. Bad constraints, evidence or external pins raise `EligibilityError`; malformed or inconsistent recommendations return `valid: false`.

The recommendation has exactly `schema_version: "vet-flat/eligibility-recommendation/1"`, `binding`, `first_choice`, `ranking`, `backups`, `blocked`, `not_selected`, `todos`:

- Binding is `{revision, constraints_sha256, evidence_sha256}`. Every TODO also carries this exact current binding.
- Each ranking/backup entry has `{candidate_id, status, open_requirement_ids, exception_ids}` matching computed checks. Every candidate appears in exactly one pool. All mandatory failures belong in `blocked`, whose entries are `{candidate_id, failed_requirement_ids}`. `not_selected` is an array of nonblocked candidate IDs.
- `first_choice` equals the first ranking entry, or `null` for an empty ranking. Backups require a ranked first choice. Unresolved candidates may be ranked for conditional investigation, with all open IDs retained.
- A TODO has `{id, candidate_id, action, requirement_ids, binding}`. Selected nonblocked candidates permit `investigate` or `view`, using only current open IDs; investigation requires at least one ID. Their TODOs collectively cover every open condition. A view TODO may use an empty array when no conditions remain open.
- A blocked candidate permits only `reconsider`, naming all failed IDs. This means reconsider if the user changes conditions or new evidence changes the result; it is outside eligible ranking and does not authorize immediate viewing/promotion. Nonselected candidates have no active TODOs.
- No free-form waiver, overall verdict or payment fields are accepted. Review user-facing prose and other saved artifacts separately against the validated structured result; this API cannot detect a contradictory sentence in an unrelated file.

## Runnable synthetic example

Set `PEA_SKILL` to the installed skill directory. These values are demonstration inputs, never personal defaults. Computing pins here is appropriate for an offline example; in a model run the host supplies independently retained pins for already-reviewed current inputs.

```python
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(os.environ["PEA_SKILL"]) / "scripts"))
from eligibility import canonical_hash, evaluate, validate_recommendation

constraints = {
    "schema_version": "vet-flat/eligibility-constraints/1", "revision": 3,
    "requirements": [
        {"id": "budget", "field": "monthly_total", "type": "number", "operator": "lte",
         "value": 1500, "unit": "GBP/month", "mandatory": True, "basis": ["observed", "estimate"]},
        {"id": "floor", "field": "ground_floor", "type": "boolean", "operator": "eq",
         "value": False, "unit": None, "mandatory": True, "basis": ["observed"]}],
    "user_requests": {"u1": "For demo-c only, ground floor is acceptable if both rooms are observed dry on 2026-01-12."},
    "exceptions": [{"id": "floor-c", "requirement_id": "floor", "candidate_id": "demo-c",
        "request_id": "u1", "quote": "For demo-c only, ground floor is acceptable",
        "when": [{"field": "dry_inspection", "type": "boolean", "operator": "eq", "value": True,
                  "unit": None, "basis": ["observed"],
                  "scope": {"date": "2026-01-12", "rooms": ["bedroom", "living_room"]}}]}]}
evidence = {
    "schema_version": "vet-flat/eligibility-evidence/1",
    "sources": {"s1": "Estimated monthly total GBP 1400. Observed ground floor. Both rooms observed dry on 2026-01-12."},
    "candidates": [{"id": "demo-c", "fields": {
        "monthly_total": {"value": 1400, "unit": "GBP/month", "qualifier": "estimate",
                          "source_id": "s1", "quote": "Estimated monthly total GBP 1400."},
        "ground_floor": {"value": True, "unit": None, "qualifier": "observed",
                         "source_id": "s1", "quote": "Observed ground floor."},
        "dry_inspection": {"value": True, "unit": None, "qualifier": "observed",
                           "source_id": "s1", "quote": "Both rooms observed dry on 2026-01-12.",
                           "scope": {"date": "2026-01-12", "rooms": ["bedroom", "living_room"]}}}}]}
pins = {"revision": 3, "constraints_sha256": canonical_hash(constraints),
        "evidence_sha256": canonical_hash(evidence)}
checks = evaluate(constraints, evidence, **pins)
assert checks["candidates"]["demo-c"]["status"] == "needs_evidence"
assert checks["candidates"]["demo-c"]["open_requirement_ids"] == ["budget"]
recommendation = {
    "schema_version": "vet-flat/eligibility-recommendation/1", "binding": dict(pins),
    "first_choice": "demo-c",
    "ranking": [{"candidate_id": "demo-c", "status": "needs_evidence",
                 "open_requirement_ids": ["budget"], "exception_ids": ["floor-c"]}],
    "backups": [], "blocked": [], "not_selected": [],
    "todos": [{"id": "check-total", "candidate_id": "demo-c", "action": "investigate",
               "requirement_ids": ["budget"], "binding": dict(pins)}]}
result = validate_recommendation(constraints, evidence, recommendation, **pins)
assert result["valid"] is True and result["payment_authorized"] is False
print(json.dumps(result))
```

The CLI accepts the same external pins:

```bash
python3 "$PEA_SKILL/scripts/eligibility.py" evaluate --constraints "$CONSTRAINTS_FILE" --evidence "$EVIDENCE_FILE" --revision "$CURRENT_REVISION" --constraints-sha256 "$CONSTRAINTS_SHA256" --evidence-sha256 "$EVIDENCE_SHA256"
python3 "$PEA_SKILL/scripts/eligibility.py" validate --constraints "$CONSTRAINTS_FILE" --evidence "$EVIDENCE_FILE" --revision "$CURRENT_REVISION" --constraints-sha256 "$CONSTRAINTS_SHA256" --evidence-sha256 "$EVIDENCE_SHA256" --recommendation "$RECOMMENDATION_FILE"
```

Successful evaluation exits 0 even when candidates are blocked. Validation exits 0 only for `valid: true`, 1 for a rejected recommendation, and 2 for malformed input or stale external pins. Results are one JSON object on stdout; input errors are JSON on stderr. `canonical_hash` uses sorted compact JSON, `ensure_ascii=False`, `allow_nan=False`, encoded as UTF-8; formatting does not matter, while changing a JSON number from `1` to `1.0` changes its pin.
