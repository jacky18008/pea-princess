# Prospective source-review reconciliation

Prospective 36-answer blinded AI source review, then root unblinding. Not human ground truth or replacement of primary results.

Criterion differences include rubric interpretation. More secondary points do not establish that the primary grader was wrong or that an answer model improved.

36 answers; 180 criteria; primary 148, secondary 151; 43 criterion disagreements.

| Answer | Primary | Source review | Differing criteria |
|---|---:|---:|---|
| S1-r1-T2-state_no_sources | 3/5 | 5/5 | S1-T2-F1, S1-T2-F4 |
| S1-r1-T2-state_neither | 3/5 | 5/5 | S1-T2-F1, S1-T2-F4 |
| S1-r1-T2-state | 3/5 | 5/5 | S1-T2-F1, S1-T2-F4 |
| S1-r1-T2-prose | 4/5 | 5/5 | S1-T2-F4 |
| S1-r1-T2-state_no_updates | 3/5 | 4/5 | S1-T2-F4 |
| S1-r1-T2-full | 4/5 | 5/5 | S1-T2-F4 |
| S2-r2-T1-state_neither | 5/5 | 3/5 | S2-T1-F2, S2-T1-F4 |
| S2-r2-T1-prose | 3/5 | 2/5 | S2-T1-F2 |
| S2-r2-T1-state_no_sources | 5/5 | 3/5 | S2-T1-F2, S2-T1-F4 |
| S2-r2-T1-full | 5/5 | 5/5 | — |
| S2-r2-T1-state | 5/5 | 3/5 | S2-T1-F2, S2-T1-F4 |
| S2-r2-T1-state_no_updates | 5/5 | 4/5 | S2-T1-F2 |
| S3-r1-T2-state_no_updates | 3/5 | 5/5 | S3-T2-F2, S3-T2-F4 |
| S3-r1-T2-state_neither | 2/5 | 4/5 | S3-T2-F2, S3-T2-F4 |
| S3-r1-T2-state_no_sources | 3/5 | 4/5 | S3-T2-F4 |
| S3-r1-T2-state | 3/5 | 4/5 | S3-T2-F2, S3-T2-F3, S3-T2-F4 |
| S3-r1-T2-prose | 2/5 | 3/5 | S3-T2-F2 |
| S3-r1-T2-full | 3/5 | 4/5 | S3-T2-F2, S3-T2-F3, S3-T2-F4 |
| E1-long-raw_full | 5/5 | 5/5 | — |
| E1-long-oracle | 5/5 | 5/5 | — |
| E1-long-full | 5/5 | 5/5 | — |
| E1-long-lexical | 4/5 | 4/5 | — |
| E1-long-adaptive | 3/5 | 5/5 | E1-F3, E1-F4 |
| E1-long-summary | 3/5 | 5/5 | E1-F3, E1-F4 |
| E2-short-lexical | 5/5 | 4/5 | E2-F5 |
| E2-short-oracle | 5/5 | 4/5 | E2-F5 |
| E2-short-raw_full | 5/5 | 4/5 | E2-F5 |
| E2-short-adaptive | 5/5 | 4/5 | E2-F5 |
| E2-short-summary | 5/5 | 4/5 | E2-F4 |
| E2-short-full | 5/5 | 4/5 | E2-F5 |
| E3-long-lexical | 5/5 | 4/5 | E3-F3 |
| E3-long-summary | 5/5 | 4/5 | E3-F3 |
| E3-long-raw_full | 5/5 | 5/5 | — |
| E3-long-oracle | 4/5 | 4/5 | — |
| E3-long-full | 5/5 | 5/5 | — |
| E3-long-adaptive | 5/5 | 3/5 | E3-F3, E3-F4 |

## S1-r1-T2-state_no_sources / S1-T2-F1

Rubric: Retain T1’s current £2,130 all-in ceiling, 41 m² minimum and studio acceptance; do not let historical thresholds, property area or the assistant’s prior answer overwrite those user requirements.

Primary: It correctly states “£2,130 cap” and “current minimum is 41 m²,” but does not communicate the retained acceptance of a studio conditional on desk fit.

Source reviewer: Answer span: “Your current minimum is 41 m²”. The prose also gives the £2,130 cap and distinguishes the 47/43 m² certificate areas from that minimum. Available memory F49/F50 preserves the current thresholds and F51/F52 studio acceptance; the response rejects Pennythorn for cost, not layout. T1/T2 in the full reference support this use.

## S1-r1-T2-state_no_sources / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: It identifies the changed rent and utility lines, but does not attribute the rent to M-C2 or the Pennythorn update to the agent’s previous-occupant usage sheet as required.

Source reviewer: Answer span: “Pennythorn’s utility estimate rose from £160 to £240”. It keeps the rent replacement distinct from an estimated utility line and ties the changed values to T2 in the fact rows. T2 explicitly supplies M-C2 and the usage-sheet update. I accept that source anchor plus the correct differentiated lines as substantive attribution; repeating both document-origin phrases verbatim is not required.

## S1-r1-T2-state_neither / S1-T2-F1

Rubric: Retain T1’s current £2,130 all-in ceiling, 41 m² minimum and studio acceptance; do not let historical thresholds, property area or the assistant’s prior answer overwrite those user requirements.

Primary: It correctly retains “£2,130/month all-in” and “41 m²,” but never communicates that studios remain acceptable if the desk fits.

Source reviewer: Answer span: “Your current cap is £2,130/month all-in and minimum internal area is 41 m²”. These current values exist in available memory F49/F50 despite historical values elsewhere in the same memory. It says both certificate areas clear the minimum and excludes Pennythorn on cost, without reviving the withdrawn studio rule (T1/T2).

## S1-r1-T2-state_neither / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: It describes the rent and utility changes but omits that the former came from M-C2 and the latter from the agent’s previous-occupant usage sheet.

Source reviewer: Answer span: “Mosslantern’s rent fell from £1,850 to £1,770, while Pennythorn’s utility estimate rose from £160 to £240”. This correctly distinguishes the two current source lines, labels the utility number an estimate, and cites their source T2 in the fact rows. T2 contains their respective landlord M-C2 and agent/usage-sheet origins; no contradictory or invented provenance is asserted.

## S1-r1-T2-state / S1-T2-F1

Rubric: Retain T1’s current £2,130 all-in ceiling, 41 m² minimum and studio acceptance; do not let historical thresholds, property area or the assistant’s prior answer overwrite those user requirements.

Primary: It states the current “£2,130/month” cap and “41 m²” minimum but does not retain or mention studio acceptance subject to desk fit.

Source reviewer: Answer span: “current all-in cap is £2,130/month and minimum internal area is 41 m²”. Available memory F49/F50 quotes T1 and carries supersession status. It retains those thresholds in prose and scalar rows without substituting a certificate area or treating the studio as prohibited.

## S1-r1-T2-state / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: Although it distinguishes the rent reduction from the utility increase, it does not name M-C2 or attribute Pennythorn’s figure to the agent’s usage-sheet update.

Source reviewer: Answer span: “Pennythorn’s utilities rose by £80”. Together with “Mosslantern’s rent fell by £80”, the current component sums, “Both totals remain estimates” and T2 fact-source anchors, this preserves the distinct replacements and source status. It does not repeat the usage-sheet story, but does not invent another basis.

## S1-r1-T2-prose / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: It identifies both changes but does not attribute the rent reduction specifically to M-C2 or the utility increase to the agent’s previous-occupant usage sheet.

Source reviewer: Answer span: “Pennythorn’s utility estimate increase from £160 to £240”. The answer separates the rent reduction from the utility-estimate increase, cites available latest_user_question for those values, and says both totals remain estimates. latest_user_question is the packet’s T2 alias, not an unavailable source.

## S1-r1-T2-state_no_updates / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: It distinguishes the £80 rent reduction from the £80 utility increase but omits M-C2 and the agent’s previous-occupant usage-sheet provenance.

Source reviewer: Answer span: “Pennythorn’s updated utilities estimate is £240”. The component distinction and estimate status are preserved, and fact rows cite T2 for both updates. This is adequate substantive source attribution even without restating M-C2’s name and the previous-occupant usage-sheet detail.

## S1-r1-T2-full / S1-T2-F4

Rubric: Attribute Mosslantern’s rent reduction to M-C2 and Pennythorn’s higher utility estimate to the agent’s usage-sheet update, preserving the distinction between a changed rent quote and an uncapped running-cost estimate.

Primary: It correctly names “M-C2” for Mosslantern and treats Pennythorn’s £240 as a replacement estimate, but omits that Pennythorn’s agent derived it from the previous occupant’s usage sheet.

Source reviewer: Answer span: “M-C2 reduced Mosslantern’s rent from £1,850 to £1,770”. It names the rent quote, contrasts it with Pennythorn’s replacement utility estimate and cites T2. The current user message supplies the utility update’s usage-sheet provenance; the answer preserves its estimate status without claiming a fixed bill.

## S2-r2-T1-state_neither / S2-T1-F2

Rubric: Use CM-11 as the current operating evidence: the only passenger lift is out of service, contractor visit provisionally 19 February, completion unknown. The 12 January email about a lift existing does not resolve the outage.

Primary: “sole passenger lift is documented out of service… only a provisional contractor visit on 19 February” correctly uses the current outage evidence and does not treat the earlier working report as current.

Source reviewer: It correctly gives the current outage and provisional 19 February visit, but discusses an “earlier ‘working’ status” instead of explaining why the later existence-only email does not resolve CM-11. The full reference U3 contains that distinction; this candidate’s memory omits the later email. That unavailable-source omission is a coverage miss, not a false assertion that the lift works.

## S2-r2-T1-state_neither / S2-T1-F4

Rubric: Offer a focused verification path before assigning the full viewing: obtain a dated operational update and test the complete street-entrance route/flat doorway with the user’s usual aid, recording observed barriers without invasive work or a medical judgment.

Primary: “Use the earlier access-only visit, if permitted, to trace the exact pavement-to-flat route with your normal aid” gives a focused complete-route test, while requiring operational evidence for Flat 10.

Source reviewer: “Use the earlier access-only visit, if permitted” and the full route with the normal aid are useful partial coverage. However, “Use the 16 January full viewing to repeat that route end-to-end” does not reserve the full slot for a flat that passes first, and no dated current operational update is explicitly requested. It asks generally for evidence of future operation instead.

## S2-r2-T1-prose / S2-T1-F2

Rubric: Use CM-11 as the current operating evidence: the only passenger lift is out of service, contractor visit provisionally 19 February, completion unknown. The 12 January email about a lift existing does not resolve the outage.

Primary: It states the “only passenger lift is documented out of service,” the contractor visit is provisional for 19 February, and there is “no completion date.”

Source reviewer: It gives the 11 January outage, provisional 19 February visit and unknown completion, but never explains why the later agent email about existence does not resolve operation. Its actual memory explicitly includes that later-email limitation, so this is an answer omission rather than missing input.

## S2-r2-T1-state_no_sources / S2-T1-F2

Rubric: Use CM-11 as the current operating evidence: the only passenger lift is out of service, contractor visit provisionally 19 February, completion unknown. The 12 January email about a lift existing does not resolve the outage.

Primary: The prose correctly states the lift is “out of service,” the visit is “provisional for 19 February,” completion is unknown, and there is no alternative lift.

Source reviewer: Prose correctly says “only provisional for 19 February” and unknown completion, but the contractor-date scalar is “unknown”, contradicting both that prose and visible F27=19 February. The response also omits the later existence-only email, which its memory does not preserve. The former is a genuine scalar/prose inconsistency; the latter is incomplete coverage, not invented access approval.

## S2-r2-T1-state_no_sources / S2-T1-F4

Rubric: Offer a focused verification path before assigning the full viewing: obtain a dated operational update and test the complete street-entrance route/flat doorway with the user’s usual aid, recording observed barriers without invasive work or a medical judgment.

Primary: “Use an earlier access-only visit, if the manager permits, to test the exact pavement-to-flat route with your normal aid” supplies the focused route test, with operational verification for Flat 10 before reconsideration.

Source reviewer: The earlier permitted access-only visit and normal-aid route trial are useful, but “Use the 16 January full viewing to repeat that route” does not gate that scarce full slot on an initial route pass. The request for a confirmed working lift by the move is not an explicit dated current operational update before slot assignment.

## S2-r2-T1-state / S2-T1-F2

Rubric: Use CM-11 as the current operating evidence: the only passenger lift is out of service, contractor visit provisionally 19 February, completion unknown. The 12 January email about a lift existing does not resolve the outage.

Primary: The prose correctly states that the only lift is out of service, there is no alternative, the contractor visit is provisional for 19 February, and no repair date is guaranteed.

Source reviewer: Prose correctly gives a provisional 19 February visit and no guaranteed repair date, but the contractor-date scalar says “unknown” while citing U3. Visible memory F27 quotes “Contractor visit provisionally 19 February”. The later existence-only email is also omitted, and that part of U3 was not retained in this memory.

## S2-r2-T1-state / S2-T1-F4

Rubric: Offer a focused verification path before assigning the full viewing: obtain a dated operational update and test the complete street-entrance route/flat doorway with the user’s usual aid, recording observed barriers without invasive work or a medical judgment.

Primary: “Use an access-only visit, if permitted, to take your normal aid along the entire pavement-to-flat route” is an appropriate focused check, with the full viewing retained as a later fallback.

Source reviewer: The permitted access-only visit with the normal aid is useful, but the full viewing is called a “fallback opportunity to repeat that full-route check”. This does not reserve the only full slot for a route already evidenced to work, and it does not explicitly seek a dated current operational update before that assignment.

## S2-r2-T1-state_no_updates / S2-T1-F2

Rubric: Use CM-11 as the current operating evidence: the only passenger lift is out of service, contractor visit provisionally 19 February, completion unknown. The 12 January email about a lift existing does not resolve the outage.

Primary: It states that the only lift is out of service, no alternative exists, the contractor visit is provisional for 19 February, and completion is not guaranteed; it properly rejects the superseded earlier working statement.

Source reviewer: It correctly retains outage, no alternative lift and the provisional 19 February visit, but discusses “earlier ... working” versus the fault notice rather than the subsequent 12 January existence-only email. That last email is not in the supplied memory. This omission fails complete literal coverage without making the safe access refusal wrong.

## S3-r1-T2-state_no_updates / S3-T2-F2

Rubric: Use F-E2 for Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim; do not retain the old Flat 12 certificate as the target’s current evidence. The new area meets the unchanged 40 m² user minimum within the fictional packet.

Primary: The response correctly states “Flat 12B, 52 Foxbarrel Reach, at 44 m² with EPC C” and treats the old discrepancy as superseded, but it never checks the 44 m² figure against the separate 40 m² minimum.

Source reviewer: It gives the replacement official extract as Flat 12B, 44 m², EPC C and explicitly notes withdrawal of the same-unit claim (T2). The unchanged 40 m² minimum in U1/memory is not recited, but the response correctly advances on the 44 m² record without retaining Flat 12/38 m² as target evidence.

## S3-r1-T2-state_no_updates / S3-T2-F4

Rubric: Update fallback state precisely: the old £330 quote expired, the new £345 offer remains subject to availability and unbooked, and its stated refund cutoff is now 3 March 2027 at 15:00 if booked. Do not keep unknown deadline or invent a held room.

Primary: “Threadleaf is not booked. The current quote is £345, subject to availability” and the cutoff are correct, but the response omits the required update that the old £330 quote expired.

Source reviewer: “Current quote is £345, subject to availability,” “not booked,” and the conditional 2027-03-03 at 15:00 cutoff correctly replace the U5 £330/unknown-deadline record using T2. It need not repeat the expired price to use the replacement offer precisely.

## S3-r1-T2-state_neither / S3-T2-F2

Rubric: Use F-E2 for Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim; do not retain the old Flat 12 certificate as the target’s current evidence. The new area meets the unchanged 40 m² user minimum within the fictional packet.

Primary: It accurately gives “Flat 12B, 52 Foxbarrel Reach, at 44 m² (rating C)” and notes withdrawal of the same-unit claim, but does not separately establish that 44 m² satisfies the 40 m² minimum.

Source reviewer: The response correctly gives Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim (T2). It does not repeat the unchanged 40 m² minimum, but it uses the correct replacement area without a stale unit/space rejection. Its scalar memory citations are separately audited below.

## S3-r1-T2-state_neither / S3-T2-F4

Rubric: Update fallback state precisely: the old £330 quote expired, the new £345 offer remains subject to availability and unbooked, and its stated refund cutoff is now 3 March 2027 at 15:00 if booked. Do not keep unknown deadline or invent a held room.

Primary: The response correctly calls it a “new £345 quote,” subject to availability and unbooked, and gives the cutoff, but does not state that the old £330 quote expired.

Source reviewer: The answer correctly uses the new £345 quote, subject to availability and not booked/paid, with refund cutoff 2027-03-03 15:00 if booked (T2). It never retains the old £330 price or unknown deadline.

## S3-r1-T2-state_no_sources / S3-T2-F4

Rubric: Update fallback state precisely: the old £330 quote expired, the new £345 offer remains subject to availability and unbooked, and its stated refund cutoff is now 3 March 2027 at 15:00 if booked. Do not keep unknown deadline or invent a held room.

Primary: “Threadleaf is not booked; the new £345 quote is subject to availability” and the stated cutoff are correct, but the response never explicitly says the old £330 quote expired.

Source reviewer: The new £345 quote, availability condition, unbooked state and stated 3 March 2027 at 15:00 cutoff if booked all match T2; no stale £330 offer or unknown deadline is used.

## S3-r1-T2-state / S3-T2-F2

Rubric: Use F-E2 for Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim; do not retain the old Flat 12 certificate as the target’s current evidence. The new area meets the unchanged 40 m² user minimum within the fictional packet.

Primary: It correctly identifies “Flat 12B, 52 Foxbarrel Reach, at 44 m² (C)” as current evidence, but does not explicitly compare 44 m² with the distinct 40 m² minimum.

Source reviewer: The replacement supplied official extract is specifically Flat 12B, 44 m²/C. It treats the old mismatch as resolved rather than retaining Flat 12 as the target’s current certificate. It does not restate the 40 m² profile threshold, but makes no contrary size conclusion.

## S3-r1-T2-state / S3-T2-F3

Rubric: Use the corrected £240 invoice to Foxbarrel Residential Ltd, user-reported independent callback/bank check and supplied owner-authority letter; acknowledge written reservation terms now exist without treating the assistant as their independent verifier or certifying legal compliance.

Primary: “corrected £240 reservation invoice names Foxbarrel Residential Ltd,” the independently matched account, and the written unit-specific refund terms accurately cover the supplied payment evidence; the opening conclusion also recognizes all three gates, including authority.

Source reviewer: The £240 company invoice, independently matched account ending 4812 and written terms are correctly retained (T2), but the answer never identifies the supplied owner-authority letter or its substantive landlord-to-agent authorisation. “Your three verification gates ... answered” gives the overall conclusion without this required authority basis. This is an omission, not an incorrect payee, fabricated check or claim that the letter is still absent.

## S3-r1-T2-state / S3-T2-F4

Rubric: Update fallback state precisely: the old £330 quote expired, the new £345 offer remains subject to availability and unbooked, and its stated refund cutoff is now 3 March 2027 at 15:00 if booked. Do not keep unknown deadline or invent a held room.

Primary: The “new Threadleaf £345 quote” is correctly described as subject to availability and unbooked with the correct cutoff, but the response does not state that the old £330 quote expired.

Source reviewer: It states the new £345 Threadleaf quote is subject to availability, not booked, and conditionally refundable by 2027-03-03 15:00. The old offer/deadline is not retained.

## S3-r1-T2-prose / S3-T2-F2

Rubric: Use F-E2 for Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim; do not retain the old Flat 12 certificate as the target’s current evidence. The new area meets the unchanged 40 m² user minimum within the fictional packet.

Primary: It correctly uses the Flat 12B extract at 44 m²/C and says to use 44 rather than the listing’s 47, but it does not separately say that 44 m² meets the 40 m² requirement.

Source reviewer: It gives the exact current Flat 12B official extract at 44 m²/EPC C, and uses 44 rather than the listing’s 47 m². That listing figure is genuinely present in this candidate’s memory (from U2), so this extra comparison is supported. No unchanged 40 m² recital is required to recognise that the new official area supports progression.

## S3-r1-T2-full / S3-T2-F2

Rubric: Use F-E2 for Flat 12B at 44 m²/C and the agent’s withdrawal of the same-unit claim; do not retain the old Flat 12 certificate as the target’s current evidence. The new area meets the unchanged 40 m² user minimum within the fictional packet.

Primary: The current record correctly says “Flat 12B, 52 Foxbarrel Reach, 44 m², C” and supersedes the old mismatch, but it does not explicitly test 44 m² against the user’s 40 m² minimum.

Source reviewer: It correctly records the replacement official Flat 12B certificate at 44 m²/C and treats Flat 12’s old certificate as corrected history, not interchangeable current evidence. The omitted recital of the 40 m² minimum does not cause any contrary size conclusion.

## S3-r1-T2-full / S3-T2-F3

Rubric: Use the corrected £240 invoice to Foxbarrel Residential Ltd, user-reported independent callback/bank check and supplied owner-authority letter; acknowledge written reservation terms now exist without treating the assistant as their independent verifier or certifying legal compliance.

Primary: It correctly states “Foxbarrel Residential Ltd; reservation amount—£240” and accurately summarizes the written credit and refund triggers while limiting what those terms establish.

Source reviewer: The corrected company payee, £240 amount, and stated credit/refund terms are accurate, but the response does not describe the completed callback/bank match or the owner-authority letter/result. The general “three stated verification gates ... answered” is a correct conclusion without the frozen criterion’s required authority and independent-recipient evidence basis. No check is falsely said to be missing or performed by the assistant.

## S3-r1-T2-full / S3-T2-F4

Rubric: Update fallback state precisely: the old £330 quote expired, the new £345 offer remains subject to availability and unbooked, and its stated refund cutoff is now 3 March 2027 at 15:00 if booked. Do not keep unknown deadline or invent a held room.

Primary: The response accurately describes the “new £345 quote” as subject to availability, unbooked, and conditionally refundable by the correct cutoff, but does not explicitly state that the old £330 quote expired.

Source reviewer: It correctly replaces the old offer with a new £345 quote, subject to availability and unbooked, and gives the refund cutoff as 3 March 2027 at 15:00 if booked. No held accommodation or unknown deadline is invented.

## E1-long-adaptive / E1-F3

Rubric: Account for the operational gate: endpoint restriction remained enabled and rollback to Larch was exercised successfully with readback/smoke results. These recorded controls support the bounded action.

Primary: It correctly reports that rollback was exercised and read back, but it does not state that endpoint restriction remained enabled during the comparison; “執行前後應核對…端點限制啟用” is only a proposed future check.

Source reviewer: It describes the comparison under the same runner and restrictions, says the acceptance gate is met, and states completed same-runner rollback with “Larch was restored, two smoke scenarios passed, and runner readback showed Larch.” This communicates the operating controls in substance; the additional future endpoint check is ordinary verification, not a claim that prior controls were missing.

## E1-long-adaptive / E1-F4

Rubric: Use exact source excerpts to support the decision and distinguish an approved future selection from a completed deployment; the current scheduled default remains Larch pending review.

Primary: The response distinguishes the pending change from execution, but all purported excerpts cite only “summary.” A model-made summary is not an exact excerpt from a source document with a source ID, so the explicit source-excerpt requirement is unmet.

Source reviewer: It cites only exact excerpts of its available summary, records “HBR-14 尚未執行”, and gives current_scheduled_default=Larch. The admission “僅有摘要可用” matches actual visibility and is not dishonest merely because this reviewer sees full documents.

## E1-long-summary / E1-F3

Rubric: Account for the operational gate: endpoint restriction remained enabled and rollback to Larch was exercised successfully with readback/smoke results. These recorded controls support the bounded action.

Primary: It accurately communicates successful same-runner rollback, but never clearly says the endpoint restriction remained enabled during the comparison. “相同…限制” is too nonspecific, and its later destination check is prospective.

Source reviewer: The response presents the comparison under the same restrictions and successful same-runner rollback, and its finding gives restored Larch, two passed smoke scenarios and readback. The summary contains the enabled endpoint gate and those completed controls; the later operational checks do not negate that recorded success.

## E1-long-summary / E1-F4

Rubric: Use exact source excerpts to support the decision and distinguish an approved future selection from a completed deployment; the current scheduled default remains Larch pending review.

Primary: It correctly says HBR-14 has not executed and Larch remains selected, but its quotations are solely from “summary,” not exact excerpts attributed to underlying source-document IDs.

Source reviewer: The limitation says “尚無HBR-14已執行的紀錄；目前排程預設仍為Larch”. All five evidence excerpts are exact substrings of the candidate’s available summary. No original-document inspection or completed deployment is invented.

## E2-short-lexical / E2-F5

Rubric: Recommend preserving opaque identifier strings or otherwise enforcing the stated contract, then validating both collision examples and suitable additional distinct-key cases against independent references before reconsideration; retaining Cedar is justified. Do not assert that a fix has already passed.

Primary: “修正 Birch 的不透明字串保留行為，使用固定 MFT-60 參考檔重跑” proposes a contract-preserving correction and independent frozen-reference rerun containing both collision fixtures and other identifier categories; it also correctly notes that no fixed result exists.

Source reviewer: It usefully proposes preserving opaque identifiers and rerunning the frozen MFT-60 suite to 60/60, which includes both known collisions. However, “以固定 MFT-60 參考檔重跑” never adds suitable additional distinct-key cases as this composite frozen criterion explicitly requires. This is a verification-coverage omission, not a wrong refusal or an unsafe action recommendation.

## E2-short-oracle / E2-F5

Rubric: Recommend preserving opaque identifier strings or otherwise enforcing the stated contract, then validating both collision examples and suitable additional distinct-key cases against independent references before reconsideration; retaining Cedar is justified. Do not assert that a fix has already passed.

Primary: “修正或關閉…數字尾碼正規化，僅保留…周邊空白修剪” followed by a frozen-reference full rerun and zero-error gate is a supported correction and verification plan covering the collision fixtures and regression cases.

Source reviewer: “以相同凍結參考檔重跑60案” and independent confirmation of zero errors are useful. The answer never proposes additional distinct-key cases beyond those fixed 60, so it incompletely covers the literal criterion’s additional-coverage requirement. Maintaining Cedar pending this work is still the correct immediate action.

## E2-short-raw_full / E2-F5

Rubric: Recommend preserving opaque identifier strings or otherwise enforcing the stated contract, then validating both collision examples and suitable additional distinct-key cases against independent references before reconsideration; retaining Cedar is justified. Do not assert that a fix has already passed.

Primary: “修正 Birch 後以同一凍結參考檔完整重跑，確認60/60且無錯誤再評估” is a justified verification plan; the next steps also require examining leading-zero keys and slots.

Source reviewer: The answer proposes fixing numeric-suffix normalization and “對相同凍結 MFT-60 參考檔完整重跑”, with intermediate-key inspection. That is useful but does not explicitly add new distinct-key cases beyond the existing suite, which E2-F5 requires. No corrected result is falsely claimed.

## E2-short-adaptive / E2-F5

Rubric: Recommend preserving opaque identifier strings or otherwise enforcing the stated contract, then validating both collision examples and suitable additional distinct-key cases against independent references before reconsideration; retaining Cedar is justified. Do not assert that a fix has already passed.

Primary: “只作容許的空白修剪” and rerunning “同一凍結參考集…確認零不符” provide a contract-aligned correction and verification before reconsideration, while retaining Cedar.

Source reviewer: It correctly proposes preserving the trimmed string and rerunning all 60 frozen cases, but “以相同凍結參考檔重跑60個情境” does not introduce suitable additional distinct-key coverage. The literal criterion is incomplete although the immediate decision and next step are useful.

## E2-short-summary / E2-F4

Rubric: Distinguish the observed wrong-target preview from actual harm: dispatch was disabled, no parcel dispatch or inventory mutation occurred, and the default remains Cedar.

Primary: “維持 Cedar 預設” and the limitation “沒有…部署” communicate the unchanged operational state; its recommendation not to enable or operate dispatch is consistent with the summary’s preview-only, no-dispatch boundary.

Source reviewer: The answer does not clearly communicate that the observed evaluation was preview-only with no dispatch or inventory mutation. “不啟用或操作明日批次” is a future instruction, and dispatch_enabled is “unknown”. Its actual summary does state “preview-only” and “No dispatch, inventory mutation…occurred”. This is a missing historical boundary, not an assertion that real harm occurred. The summary does not reproduce the literal configuration flag, so unknown for that exact flag is not classified as fabricated fact.

## E2-short-full / E2-F5

Rubric: Recommend preserving opaque identifier strings or otherwise enforcing the stated contract, then validating both collision examples and suitable additional distinct-key cases against independent references before reconsideration; retaining Cedar is justified. Do not assert that a fix has already passed.

Primary: “只修剪周邊空白、保留字串” followed by a frozen MFT-60 rerun requiring 60/60 and zero wrong targets is a contract-aligned remediation and verification step before approval.

Source reviewer: It usefully recommends preserving strings, prohibiting numeric suffix conversion and rerunning the same frozen MFT-60 suite to zero errors. It does not add further distinct-key scenarios beyond those 60, leaving E2-F5’s explicit additional-coverage element unmet. The refusal and proposed regression check remain useful.

## E3-long-lexical / E3-F3

Rubric: Identify the decisive evidence gap: original body expired, resolved input/binding not captured, and current-pointer observation occurs after the run with no historical binding/cache record. The digest has no trusted R7 reference mapping. Exact relevant excerpts should support the gap.

Primary: 「完整PDF已依保留政策到期，封包亦無列級驗證或已解析修訂值」指出核心內容與綁定缺口；「事後指標狀態，也不能單獨回推H17啟動時」保留歷史限制，limitations亦正確指出「沒有R7-only的可信對照雜湊」。

Source reviewer: It correctly identifies the expired body, unrecorded binding, absent row verification and lack of an R7-only trusted digest. However, “即使取得事後指標狀態” presents later pointer evidence generically, while the limitation declines a pointer timeline because E3-D02/D03 bodies are unavailable. Its actual summary already states the 26 August observation after H17 with no start-time history; that known observation is not communicated. This leaves the specific historical-pointer part of the composite finding incomplete, rather than making its refusal wrong.

## E3-long-summary / E3-F3

Rubric: Identify the decisive evidence gap: original body expired, resolved input/binding not captured, and current-pointer observation occurs after the run with no historical binding/cache record. The digest has no trusted R7 reference mapping. Exact relevant excerpts should support the gap.

Primary: 「未保存解析後版本、列快照、指標目標、快取身分或列級驗證」涵蓋綁定缺口；另指出PDF過期、26日指標晚於執行且「不能倒推25日」，並引用摘要說 digest 等不能確立版本。

Source reviewer: It quotes and explains the expired PDF, unrecorded resolved revision/snapshot/pointer/cache, and the 26 August observation after the run without start-time history. It also quotes that the digest does not establish revision. It does not explain the frozen criterion’s specific missing trusted R7 reference mapping. That mapping detail is itself absent from its actual summary-only evidence; this is literal composite-criterion incompleteness, not an unsupported digest claim or an incorrect decision.

## E3-long-adaptive / E3-F3

Rubric: Identify the decisive evidence gap: original body expired, resolved input/binding not captured, and current-pointer observation occurs after the run with no historical binding/cache record. The digest has no trusted R7 reference mapping. Exact relevant excerpts should support the gap.

Primary: 「未保存實際解析版本、列快照或列級驗證；完整 PDF 已依保留期過期」指出主要缺口；另說26日指標不能倒推25日，並警告不得以「摘要值」替代表格證據，實質涵蓋digest不能確立版本。

Source reviewer: Exact summary excerpts support the expired original and uncaptured revision/snapshot/pointer/cache/validation; prose preserves the 26 August versus 25 August timing limit. The next step prohibits substituting a digest for content evidence, but does not give the specific no-trusted-R7-reference-mapping explanation required by this composite criterion. That detail is absent from its summary-only visibility. This is an incomplete explanation, not an unsupported claim that the digest proves a revision.

## E3-long-adaptive / E3-F4

Rubric: Preserve what is established: H17 completed and an 18-page artifact was accepted; missing content evidence does not prove render failure, corruption, or an incorrect revision. The retained preview covers only the cover page.

Primary: 「可支持的僅是已完成的 18 頁產物，以及簽署申請與首頁預覽」保留完成、頁數和僅首頁預覽的事實；沒有將缺證據推成渲染失敗、損壞或錯誤修訂。

Source reviewer: It correctly reports completed status, 18 pages and a one-page retained preview, and does not invent corruption or a wrong revision. It does not communicate the known archive-acceptance fact, even though its available summary explicitly includes archive acceptance among the retained evidence. E3-F4’s preservation of the produced-and-accepted artifact is therefore incomplete; this does not mean its completion statement is false.
