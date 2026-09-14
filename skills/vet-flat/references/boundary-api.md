Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# A candidate near the person's limit

For a comparison involving a candidate tradeoff or viewing hold, use the atomic constructor in [boundary-turn.md](boundary-turn.md); it supplies the schema markers and current comparison together. This page documents individual operations for integrations.

Explain the actual tradeoff and, if the person has not already decided, ask whether they accept it: “This one is estimated at 46 minutes and has the larger bedroom. Would you consider that extra minute?” Use a native choice with free text when available: this candidate only; keep without viewing; decline. A concise conversational question works without native controls. Do not repeatedly ask hypothetical tolerance questions before a useful candidate exists or ask the person to confirm a clear instruction again.

“About 45 minutes” is not automatically a strict exclusion. Preserve the person's meaning and priorities; never invent a universal minute allowance or noise threshold. An explicit “over 45: don't view” keeps viewing on hold until their decision. A categorical mould/leak rejection remains separate. Checking a journey's accuracy does not answer whether the person is willing to accept it.

## Same state, explicit effect

Read [state-api.md](state-api.md) for capture, provenance and revision-checked events. Use the installed `scripts/boundary.py` with the user's private project. The host must actually invoke it. Prose, a hash and `authorized:true` cannot prove semantic consent or enforce another host's actions.

For machine comparisons, the existing requirement's **value** holds this object; do not keep another competing limit in a separate file:

```json
{"schema_version":"pea-princess/comparison/1","field":"commute_minutes","type":"number","operator":"lte","value":45,"unit":"minutes","basis":["observed","estimate"],"scope":{"kind":"journey","destination_id":"destination-1","time_window":"weekday arrival 09:00"}}
```

Use ordinary `requirement.add`/`requirement.update`, the person's exact captured quote, their `strength` (`must`, `prefer` or `prohibit`), and `scope:"all candidates"`. In a prohibition, encode the desired comparison, e.g. `mould eq false`. Keep the person's words in provenance and label, including approximate targets. Each field needs consistent type/unit. The journey scope above is required for commute evidence too. Do not upgrade a preference while normalizing it.

Free-text, other scopes and conditional requirements remain visible as **unmapped** and prevent a machine claim that viewing is permitted. They need interpretation/checking, not deletion to obtain a pass. This first adapter does not normalize natural language or general dryness predicates; [eligibility-api.md](eligibility-api.md) has the separate observed-evidence conditional exception contract.

If any condition is unmapped or a captured request remains pending, the review returns `ready:false`, no candidate ordering, and a reconciliation TODO. `validate` rejects that incomplete review even if its bytes match. Fix the missing mapping; never publish an alternative ranking that ignores it.

## Record a decision initiated by the person

An actual user instruction does not require an earlier assistant offer. The turn constructor accepts `instructions` in array order, after condition updates and replies to earlier proposals, before new proposals. Each instruction has `id`, `decision`, `requirement_id`, `quote`, and the fields specified below. It builds a separate `boundary.instruct` event with the actual captured user provenance and current evidence. It never invents a proposal, its wording or a reply that happened afterward.

| Instruction | Additional fields and effect |
|---|---|
| `retain` | Requires `candidate_id`. Keeps that candidate and places its viewing on hold. No `accepted_check` or `global_check` is allowed. |
| `candidate` | Requires `candidate_id` and complete `accepted_check`. Accepts only that candidate's stated bound, pinned to the current requirement. |
| `global` | Requires complete `global_check`; `candidate_id` is forbidden. Updates the overall requirement while preserving its strength and scope and clearing its obsolete optional label. Leaves every candidate's retained hold unchanged. |
| `release` | Requires `candidate_id` and the current retained hold for that candidate/condition, including a retained decision beneath later undecided offers. Supersedes that hold without accepting any numerical exception. Allowed with an active or retired condition; all current checks and other holds remain in force. |

For “keep A without viewing,” use `retain` without inventing a numerical waiver. For “the overall limit is now 50, and A can be considered,” use a global instruction followed by a release instruction for A in the same atomic turn. A global change alone cannot imply that second permission. A release while the original limit still excludes A leaves viewing blocked by the comparison. A direct bounded acceptance may supersede a retained hold only when the person's actual instruction accepts that candidate's bound.

For an individual operation, first capture the real user message; `instruct.json` contains the same fields except that `quote` is inside captured user `provenance`, and the full current `evidence` bundle is required:

```json
{"id":"retain-a","decision":"retain","requirement_id":"commute","candidate_id":"A","provenance":{"actor":"user","authorized":true,"source_id":"u2","request_id":"u2","quote":"Keep A without viewing; leave the other conditions unchanged."},"evidence":{"schema_version":"vet-flat/eligibility-evidence/1","sources":{},"candidates":[]}}
```

```bash
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" instruct --expected-revision "$PEA_REVISION" --input instruct.json
```

Replace the evidence placeholder with the actual bundle. Candidate instructions require the candidate to be present, but `retain` does not require a known duration. Numeric acceptance validates the full evidence bundle, recognized quoted source, bound comparison, permitted qualifier and exact field/type/unit/operator/journey scope. As with an offered acceptance, estimates remain estimates, and the bound does not cover later 75-minute, unknown or differently scoped evidence. `global_check` uses the same predicate identity and may narrow, never broaden, the permitted evidence basis; it changes the authorized condition without claiming any candidate passes it.

The actual quote must occur verbatim in the captured request, with `source_id == request_id`, `actor:"user"` and `authorized:true`. The capture must follow any prior proposal/decision for the same candidate/condition and cannot predate the current condition's user instruction. A trusted caller still has to interpret the quote's meaning and scope: no regex, copied quote or provenance flag proves semantic permission. Source prose cannot supply user authorization.

Direct records live in the existing `proposed_checks` history with `kind:"boundary"`, `origin:"user"`, actual quote/provenance, `decision`, immediate status (`retained`, `accepted` or `released`), requirement/evidence pins and decision history. They contain no fabricated proposal `text`, `why` or `offered_evidence`. Candidate records retain `instruction_evidence` and `instruction_source`; retained/released records contain no `accepted_check`. A new candidate instruction links `supersedes` to the prior record but does not mutate it. Global instructions use `candidate_id:null` and do not participate in the latest record per candidate/condition. Reopening preserves that distinction. An instruction cannot later be passed to `decide` as though it had been an assistant proposal; record the next actual instruction explicitly.

This bounded direct API does not yet normalize a refusal made without an offer. Refusal of an actual earlier offer uses `decline` below; do not fabricate an offer to use it.

## Offer and record a reply

`propose.json` contains:

```json
{"id":"offer-a","text":"Consider A's estimated 46-minute journey?","why":"A has a larger separate bedroom in the supplied comparison.","requirement_id":"commute","candidate_id":"A","accepted_check":{"field":"commute_minutes","type":"number","operator":"lte","value":46,"unit":"minutes","basis":["observed","estimate"],"scope":{"kind":"journey","destination_id":"destination-1","time_window":"weekday arrival 09:00"}},"evidence":{"schema_version":"vet-flat/eligibility-evidence/1","sources":{},"candidates":[]}}
```

Replace the evidence placeholder with the actual saved bundle described in [eligibility-api.md](eligibility-api.md); the candidate must exist with a quoted value/source and matching scope. `accepted_check` is the specific offered bound, not a universal tolerance. Supply only supported advantages in `text`/`why`; source storage does not verify their truth.

```bash
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" propose --expected-revision "$PEA_REVISION" --input propose.json
```

The tool pins the current condition and retains the offered evidence and proposal text. Pending consent is separate from confirmed requirements. It holds viewing for that candidate while leaving unrelated research available.

After the actual user reply, capture it verbatim. Pass a decision file with `id`, `decision` and captured user `provenance`:

```json
{"id":"offer-a","decision":"candidate","provenance":{"actor":"user","authorized":true,"source_id":"u2","request_id":"u2","quote":"Only A is okay at 46 minutes; leave the general limit as it is."}}
```

```bash
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" decide --expected-revision "$PEA_REVISION" --input decision.json
```

| Decision | Effect |
|---|---|
| `candidate` | Accept only this candidate's offered bound. Other candidates and the global condition stay unchanged. |
| `retain` | Keep the candidate for comparison; continue holding its viewing. Not an accepted exception. A later actual reply may decide this retained proposal. |
| `decline` | Record refusal and keep the original condition. Reconsideration uses a new proposal. |
| `global` | Requires `global_check`, a complete predicate with the user's new value. Changes the original global condition atomically, preserving its strength and scope. |
| `release` | Only for the latest retained proposal after its linked condition was retired. An explicit new user reply lifts that viewing hold, without changing any current condition or bypassing other checks. |

A global decision clears the target condition's optional display label, which may
still contain the old limit. Its earlier label remains in journal history; the
current value and exact new provenance describe the authorized condition. Labels
do not participate in normalized constraint bindings or numeric/consent checks.

Only the bound and a narrower evidence basis may change. Changing field, unit, operator or journey scope needs a separately authorized requirement update. Decisions require a captured user message later than the proposal/latest decision; matching words from an older turn or a source are insufficient. The caller still judges whether the reply accepts the stated scope. Ambiguous assent stays pending. Resolve the captured request after reconciling its changes, then recompute.

## Compare, resume and validate

```bash
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" context --max-chars 32000
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" evaluate --evidence evidence.json > review.json
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" validate --evidence evidence.json --review review.json
```

The review has confirmed conditions and separate proposal history, numeric checks, candidate order, consent holds and viewing/research TODOs. Its order is administrative (viewing permission, unresolved checks, ID), **not** a utility score or the user's final recommendation. `viewing_allowed` means the recorded comparison/consent gates allow consideration of a viewing, not that a viewing has been booked, the agent may contact someone, or the home passes every assessment. Explain the useful result naturally; do not print the machine review into the conversation.

Acceptance of estimated `<=46` still leaves duration unconfirmed; it may cover an improved 45.5 estimate, never a new 75-minute estimate, an unknown value or another journey. A true numeric comparison cannot grant viewing if the evidence qualifier is outside the condition's permitted basis. Changing the original requirement makes the old exception inactive. All evidence predicates in legacy conditional exceptions still require observed evidence. A separate retained-without-view action hold survives both numeric changes and retirement of its condition. Use a fresh direct `release` instruction to remove only that latest retained hold. The older reply API also permits `release` on a retained assistant proposal after condition retirement. Neither path restores or changes the retired condition.

When all known mandatory failures are current pending boundary proposals, unresolved checks keep their investigation TODOs while viewing stays on hold. An independent mandatory failure, such as prohibited mould, keeps the candidate in reconsideration instead.

Reopening restores the same user quote, proposal, scope and decisions from `.pea-state`. Recompute with current evidence and validate before reusing a saved review: revisions, evidence or altered ranking/TODOs invalidate it. Generic task records depending on the affected condition become stale; reconcile them with the generated review before completion. A superseding proposal for the same candidate/condition replaces the earlier active proposal in the current projection but retains its history. An undecided assistant proposal cannot erase an earlier retained action hold, including when a global update makes that newer proposal stale; only a later actual user decision supersedes the retention. No automatic retry or model call occurs in this tool.

Without shell/Python access, preserve the same exact user quotes, current conditions, candidate scope, accepted bound, evidence uncertainty, decision history and viewing holds in the user's accessible private notes. Recompute the comparison and TODOs manually after a change; label machine validation unavailable. Do not claim that journal transactions, hashes or saved tool artifacts exist when they were not created. If existing state cannot be read, obtain it before relying on an earlier decision.
