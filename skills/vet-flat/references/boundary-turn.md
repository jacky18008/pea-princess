Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Compare supplied candidates and record a boundary decision

For a ranked comparison, a saved comparison/TODO, a candidate just outside a stated limit, or a viewing hold, use this turn tool. It constructs the required state schema, captures the actual message, applies explicit changes atomically and generates the current comparison and TODOs together. This is not the full assessment/report workflow. Do not register the generated comparison as a new evidence source or create a second condition file; its generated TODOs are the current comparison work list.

Start with the saved state and provided facts. Explain a useful difference; when a worthwhile candidate exceeds a limit and the person has not already decided, ask whether they accept that actual tradeoff. Distinguish accepting this candidate, keeping it without viewing, and declining. Use native choices plus free text when available. The proposal's wording must ask about the offered value, not merely “keep it for comparison” when the proposed effect would permit viewing. Exact user quotes still need interpretation; neither this script nor a copied quote proves semantic consent.

A viewing hold on one candidate does not stop research on another. Sort gaps as in [onboarding.md](onboarding.md): fetch what a script can find, ask only for facts or preferences the person holds, and keep comparing facts that do not depend on a pending viewing decision. A ranking-only gap never holds back the current comparison or report.

Run from the user's private project. Set `PEA_SKILL` to the installed skill directory and `PEA_PROJECT` to that project, not the skill folder. Python 3.9+, no dependencies or network calls.

```bash
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" context --max-chars 64000
python3 "$PEA_SKILL/scripts/boundary.py" --project "$PEA_PROJECT" reconcile --expected-revision "$PEA_REVISION" --input turn.json --evidence evidence.json
```

Read the complete context and its revision. An empty project returns revision 0; reconciliation initializes it. Write one private `turn.json` for the actual message. In this **syntax example**, the quote is a placeholder that must be replaced with the person's exact words:

```json
{
  "request": {"id":"u1","text":"Keep commutes at most 45 minutes; ask me before viewing anything above that."},
  "requirements": [{
    "id":"commute","strength":"must","scope":"all candidates",
    "quote":"Keep commutes at most 45 minutes; ask me before viewing anything above that.",
    "label":"Ask before viewing beyond the stated commute limit",
    "check":{"field":"commute_minutes","type":"number","operator":"lte","value":45,"unit":"minutes","basis":["observed","estimate"],"scope":{"kind":"journey","destination_id":"destination-1","time_window":"weekday-arrival-09:00"}}
  }],
  "proposals":[{
    "id":"offer-a","candidate_id":"A","requirement_id":"commute",
    "text":"Would you consider A with its estimated 46-minute journey, for this candidate only?",
    "why":"The supplied comparison shows A has the larger separate bedroom.",
    "accepted_check":{"field":"commute_minutes","type":"number","operator":"lte","value":46,"unit":"minutes","basis":["observed","estimate"],"scope":{"kind":"journey","destination_id":"destination-1","time_window":"weekday-arrival-09:00"}}
  }]
}
```

Supply only evidence-backed advantages. Include every actual condition, including preferences and categorical exclusions; do not copy these example limits. `requirements` adds new IDs or explicitly updates existing IDs with the quoted instruction. `check` is a number/boolean/string comparison using `lte`/`gte`/`eq`; it needs `field,type,operator,value,unit,basis`. For a prohibition, encode the desired comparison, e.g. `mould eq false` with `strength:"prohibit"`. “Quiet would be nice” uses `prefer`, never a hard noise threshold. “About 45” alone is a preference; a separate explicit instruction to ask before viewing is a consent gate, not grounds to call the home categorically unsuitable.

Use field names/types/units from the provided evidence. Commutes need the same exact journey scope in check and evidence. If the evidence is not already normalized, read [eligibility-api.md](eligibility-api.md) for the data shape; use [inputs.md](inputs.md) for supplied pages/files. A typical item is `{value,unit,qualifier,source_id,quote,scope?}` with qualifier `observed`, `estimate`, `reported` or `unknown`; retained quotes occur in the bundle's `sources`. Unknown is not observed or passed. Do not browse a commercial listing link to fill the bundle.

When the person initiates a decision, record it immediately with `instructions`; no earlier assistant proposal is needed. Do not fabricate an offer followed by assent or ask the person to repeat a clear instruction. Omit unchanged requirements. For example:

```json
{"request":{"id":"u2","text":"Keep A, but do not arrange a viewing; leave the other conditions unchanged."},"instructions":[{"id":"retain-a","decision":"retain","candidate_id":"A","requirement_id":"commute","quote":"Keep A, but do not arrange a viewing; leave the other conditions unchanged."}]}
```

`retain` records a real viewing hold and needs no accepted bound. A direct `candidate` instruction instead requires a complete `accepted_check` describing the bound the person actually accepted for that candidate and journey. It must cover the current known evidence under the permitted basis. Neither action changes the overall condition.

A direct `global` instruction changes the requirement for every candidate and has no `candidate_id`. It does not remove existing retained holds. If the person also expressly permits considering A, record a separate `release` after the global instruction in the same turn:

```json
{"request":{"id":"u3","text":"Change the overall commute limit to 50 minutes; A can now be considered for viewing."},"instructions":[{"id":"global-50","decision":"global","requirement_id":"commute","quote":"Change the overall commute limit to 50 minutes; A can now be considered for viewing.","global_check":{"field":"commute_minutes","type":"number","operator":"lte","value":50,"unit":"minutes","basis":["observed","estimate"],"scope":{"kind":"journey","destination_id":"destination-1","time_window":"weekday-arrival-09:00"}}},{"id":"release-a","decision":"release","candidate_id":"A","requirement_id":"commute","quote":"Change the overall commute limit to 50 minutes; A can now be considered for viewing."}]}
```

`release` removes only the current retained hold for that candidate/condition, whether the condition is active or retired. Later undecided assistant offers cannot erase that hold. Release adds no numerical exception; current conditions, other holds and unknown evidence still gate viewing. Use each instruction's actual scope and exact quote. The constructor does not determine semantic permission from words such as “okay.” Direct instructions are recorded with `origin:"user"`; this describes their captured source, not proof that the caller interpreted them correctly. This initial direct path supports `retain`, `candidate`, `global` and `release`; refusal of an actual earlier offer uses `decisions` below.

For a reply to an actual earlier proposal, capture the new message and use `decisions`:

```json
{"request":{"id":"u2","text":"Only A is okay at 46 minutes; leave the general limit unchanged."},"decisions":[{"id":"offer-a","decision":"candidate","quote":"Only A is okay at 46 minutes; leave the general limit unchanged."}]}
```

Decisions: `candidate` accepts that offered bound only; `retain` keeps the option without viewing; `decline` refuses; `global` also supplies `global_check` with the expressly changed overall bound. Use a global instruction/decision instead of also updating the same requirement in `requirements`. A later message can decide a retained assistant proposal; a direct instruction is never treated as that earlier offer. A declined or materially changed proposal needs a new proposal or a fresh explicit direct instruction. `retire:[{id,quote}]` retires an explicitly removed requirement. None of these actions books a viewing or authorizes contacting another person.

Retiring a condition does not cancel an explicit retained viewing hold. After retirement, an explicit `decisions:[{id,decision:"release",quote}]` can release the latest retained proposal's hold. It needs a fresh exact user reply and leaves all remaining conditions in force. Decisions on superseded proposals are rejected; use the current proposal ID.

The same call validates all mapped conditions before saving the batch, then returns full current context and comparison, and saves `.pea-state/boundary-review.json` and `.pea-state/boundary-context.json` at one revision. Base the answer and current work on that output. An unmapped requirement is an error to resolve, never permission to leave it out or switch to a hand-authored alternative ranking. A stale revision or invalid batch commits no events; reload and reconcile, without automatic retry. If the journal saved but artifact export failed, use `context` and `evaluate` to recover instead of resubmitting the message.

Use `boundary.py validate --evidence evidence.json --review .pea-state/boundary-review.json` before reusing a saved artifact. File equality alone is not source truth or full semantic coverage. Candidate ordering is administrative (permission, missing evidence, ID), not a preference score; explain the substantive comparison yourself. Accepted estimated `<=46` remains unconfirmed and may cover 45.5, never 75, unknown duration or another journey. No universal allowance or noise tolerance is inferred.

Before saying the **comparison and its TODOs** are saved, run `python3 "$PEA_SKILL/scripts/save_gate.py" --project "$PEA_PROJECT" --scope comparison --evidence evidence.json --json` on the same evidence bundle. Exit 0 gives a current journal/review/context revision and hash receipt; a plain JSON comparison file does not. This does not certify a complete report, an available home, or permission to contact/book. For a completed report, register the snapshotted document, output and validated task using [state-sources-api.md](state-sources-api.md), then run the separate `--scope report --output-id <registered-output-id>` gate. If either gate fails, describe what has been saved without saying the requested scope is complete; repair from current state before retrying, never replay the old user turn.

Advanced individual operations and observed-evidence conditional exceptions: [boundary-api.md](boundary-api.md), [eligibility-api.md](eligibility-api.md). Use the general [state-api.md](state-api.md) only when additional task/source operations are actually needed. For the draft lint command, use the file as its **positional** argument: `python3 "$PEA_SKILL/scripts/reply_check.py" draft.md --previous "the actual latest message" --json`; do not turn linting into repeated cosmetic rewrites.

Without shell/Python access, use the manual fallback in [boundary-api.md](boundary-api.md): retain exact quotes, scope, accepted bounds and viewing holds in private notes, update the current comparison/TODOs together, and label machine validation unavailable. This preserves the decision record without claiming the tool ran.
