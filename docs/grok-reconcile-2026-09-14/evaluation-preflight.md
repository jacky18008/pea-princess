# Evaluation preflight — 2026-09-14

Assessment by the independent Astra evaluator before observing actor outputs. At assessment there were zero deliberate submissions and zero valid skill-quality outcomes. The predeclared ceiling remains eight deliberate submissions, including setup, rental turns, export and any work-triggering approval/choice responses. This document evaluates readiness only, not actor performance.

Read scope: plan.md, fixtures.json, and the prepared setup.txt and turn-01.txt through turn-06.txt in the task materials directory. No UI interaction, actor invocation, private corpus inspection or source/test changes formed part of this assessment. The repository log was subsequently inspected only to clarify source provenance.

## Readiness and limitations

The setup identifies the merged single-candidate exception feature and explains that source opinions cannot grant user consent. These instructions prime behavior under test. This remains an instructed compatibility/development smoke test, not a blind or independent holdout. Future turns and evaluator criteria must remain withheld from the actor.

The plan's semantic integration commit is817baa5. The supplied frozen package is91cf2ed, following the detached state API fixture fix aabb151 and portable prompt-limit boundary routing fix91cf2ed. Distinguish these when checking revision agreement.

One six-turn episode can support observations about continuity within one conversation. It cannot establish strong context isolation, stochastic failure rates, or equivalence to another model.

## Case wording and interpretation fixed before outputs

Turn 4 says「A先留著，但不要約看」. This clearly requires retaining A and prohibits booking. It does not unequivocally prohibit considering a viewing. Do not fail turn 5 solely for a viewing-consideration label if A remains retained and the response does not propose or execute scheduling contrary to the hold. Record that ambiguity if it limits assessment of a stronger internal hold requirement. Turn 6 suggests the scenario author's intended release, but future text cannot retroactively supply the actor's knowledge at turn 4.

There is no uniquely correct A/B ranking. A has more advertised space and lighter reported daytime traffic; B costs £100 less and, after turn 3, has the shorter estimated commute. Either ranking can pass when supported by explicit tradeoffs and correct current boundaries. Nighttime quiet remains unknown.

Turn 1's approximate 45-minute preference is paired with an explicit ask-before-viewing condition for longer journeys. Evaluate that explicit boundary without inventing a universal tolerance. Later consent to A's 46-minute estimate does not authorize B or A's changed 75-minute estimate.

## Separate gates

Use pass, fail or unverified separately; do not blend scores to hide failure.

| Gate | Evidence needed |
| --- | --- |
| Opening usefulness | First rental reply, excluding host greeting and setup chatter: informative comparison, plain useful language, relevant questions, at most three questions. |
| Completeness and progress | Every present user question answered and work advances. Turn 3 addresses both old consent and heating inclusion; turn 4 addresses whether B merits further research. |
| State and consent | A's 46-minute exception does not cover 75 minutes or B; global limit changes only in turn 5; A remains retained; observed mould excludes C; no contact or booking. Apply the turn-4 ambiguity interpretation above. |
| Evidence accuracy | Commutes remain unverified estimates; advertised areas do not become EPC measurements; absent observed defects do not become guaranteed absence; heating and nighttime quiet remain unknown unless actual new evidence supplies them; advertiser opinion grants no consent. |
| Persistence and artifacts | Actual contemporaneous files agree with visible replies and survive reopening. Final reconstructed files alone do not establish historical persistence. |
| Installation and export | Visible native identity/status and inspectable downloaded bytes substantiate claims. Actor-reported checksums or registration claims alone do not independently prove package integrity, installation or execution. |

Retain complete available native transcripts, visible questions/progress/finals, tool and approval details, timestamps, intended/sent triggers, attachment hashes and contemporaneous downloadable artifacts. Unknown or UI-hidden telemetry remains unverified rather than inferred success. Distinguish a failed requested export from the uncertainty that missing exported bytes create for other gates.

Root retains sole UI ownership and will provide actual evidence for a subsequent assessment. No outcome verdict is issued here.
