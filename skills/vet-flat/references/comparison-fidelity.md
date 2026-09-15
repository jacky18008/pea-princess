Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Saving a comparison, its sources and next steps

`save_gate.py --scope comparison` checks only the current journal, evidence hash,
review and context export. Use `--scope comparison-full` before telling the
person that the comparison **and its sources and next steps** are formally
saved. The full scope needs `--evidence <file> --fidelity-document-id <id>`.
Exit 0 returns the current revision/event hash, each registered source SHA,
the fidelity document SHA, journey-plan SHA and pending-check SHA. Exit 2 means
the full claim is unavailable; explain which piece remains to be captured.

Capture source bytes **from the actual user extract or tool observation** before
normalising the comparison. Register each source file with `document.add` in
the same private project. Tool records must retain `source_url`, `http_status`,
`retrieved_at` and `evidence_class`; keep failures and `not_found` statuses,
too. Do not use an assistant-written source summary as the source document. A
user extract has `kind: user_extract` and document provenance `actor: user`;
a tool record has `kind: tool_record` and document provenance `actor: tool` or
`external`. The evidence `sources` text and each field quote must occur in the
registered document bytes. Source snapshots are content-addressed by the
state store; the registered SHA is the one used in the fidelity document.

For each candidate with journey fields, retain the complete `commute.py journey`
JSON output as one tool source, including `query`, `plans.all`, `plans.rail`,
`plans.bus`, successful alternatives and failed plan statuses. The fidelity
document repeats the exact query and, for each mode, its `ok`, `http_status`,
`duration_min`, `start`, `arrival`, `alternatives_min`, `journeys_returned` and
`note`. The gate checks all three requests used one origin, endpoint, date and
arrival time, with only mode filters varying. It checks the fastest duration
and a 09:00 arrival field against that raw result. Keep a later or faster rail
option even when the default plan is the one quoted in the comparison.

Write a private JSON fidelity document with exactly these top-level keys:

```json
{
  "schema_version": "pea-princess/comparison-fidelity/1",
  "evidence_sha256": "<canonical evidence SHA>",
  "sources": {
    "listing-a": {"document_id": "listing-a-raw", "sha256": "<registered SHA>", "kind": "user_extract"},
    "tfl-b": {"document_id": "tfl-b-raw", "sha256": "<registered SHA>", "kind": "tool_record"}
  },
  "journeys": {
    "B": {"source_id": "tfl-b", "query": {"from": "<origin>", "to": "<endpoint>", "date": "<YYYYMMDD>", "arrive_by": "09:00", "door_buffer_min": 0, "plans": ["all", "rail", "bus"]}, "plans": {"all": {}, "rail": {}, "bus": {}}}
  },
  "pending_checks": {
    "B": {
      "unit_number": {"action": "request_user_detail", "needed": "Obtain the exact B unit or full postcode from the supplied advert.", "requirement_ids": []},
      "epc_internal_area_m2": {"action": "obtain_document", "needed": "Match an EPC certificate to that exact B unit before using its area.", "requirement_ids": []},
      "heating_type": {"action": "obtain_document", "needed": "Read heating from the same-unit EPC or tenancy paperwork.", "requirement_ids": []},
      "monthly_bills": {"action": "obtain_document", "needed": "Obtain the B tariff or billed amount before estimating monthly total.", "requirement_ids": []}
    }
  }
}
```

The example is a shape guide, not a complete passing file. Include **every**
source ID, compared candidate and unknown field. Each candidate's open
requirement ID in the review must have a pending check on its actual evidence
field; the check gives a concrete action and needed information. Keep retained
viewing holds in the journal and review. Register the fidelity JSON with
`document.add` using `actor: assistant` **before** the final `boundary.py
reconcile`, because a later document event changes the revision and makes the
review export stale. Run the full gate on that final revision. Editing the
fidelity file afterward invalidates the receipt until it is registered anew.

This gate verifies local retention and structural coverage. It cannot
authenticate a provider response or prove that a caller who registered a
document used the real tool output. A native host must capture its tool
observations itself, register those bytes and run the gate; merely installing
the skill does not add that host integration. If host tool observations are
missing, leave the full save claim unverified. No unknown EPC, heating or bill
may be invented to make the gate pass.
