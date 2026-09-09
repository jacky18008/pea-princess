# Blinded rental source-audit sample

Blinded AI source review, not human ground truth. This artifact currently covers only `S1-r1-T2-group`, with six anonymous answers. The sole input was its review packet, including the full reference and each candidate's actual available evidence. No plans, masks, costs, call records, primary judgments, experiment summaries or result-analysis documents were read. No benchmark model CLI/API, external-model or Claude calls were made. Current agent/parent review sits outside measured CLI totals. The reviewer did not author these rental fixtures.

All six candidates correctly retain the £2,130 all-in ceiling and 41 m² minimum, replace Mosslantern's rent with £1,770 and Pennythorn's utility estimate with £240, recompute £2,080 and £2,175, and switch the viewing priority to Mosslantern. Each gives the correct £50-under/£45-over margins. No numerical or threshold contradiction was found in prose or the six scalar rows.

| Group | Anonymous candidate | Criteria met | Main finding |
| --- | --- | ---: | --- |
| S1-r1-T2-group | candidate_1 | 5/5 | Correct update, source-qualified areas and a cost check. |
| S1-r1-T2-group | candidate_2 | 5/5 | Correct update with non-fixed cost/noise uncertainty. |
| S1-r1-T2-group | candidate_3 | 5/5 | Correct update with specific desk/noise checks. |
| S1-r1-T2-group | candidate_4 | 5/5 | Correct update, reported desk evidence and follow-up checks. |
| S1-r1-T2-group | candidate_5 | 4/5 | Correct decision/numbers, but unqualified desk/commute fit. |
| S1-r1-T2-group | candidate_6 | 5/5 | Correct update with named M-C2 and source-qualified travel/checks. |

Candidate_5 ends with “Mosslantern otherwise still meets the stated area, desk, commute, and preferred separate-bedroom requirements.” Its available memory marks the desk wall and route as reported claims; no physical fit or reliable journey verification is supplied. I record that wording as a minor unsupported certainty and F5 as incomplete, while retaining useful-next-step credit for the correct viewing switch. It is not a contradiction proving the desk does not fit or the route is wrong. Correct scalar rows do not erase this prose issue.

No unsupported source attribution was found. Candidate source IDs refer to supplied memory, source quotations actually embedded in that memory, or the current T2 message. `latest_user_question` is T2's available alias, and M-C2's changed rent is explicitly present in T2. The responses do not claim external access or use their previous assistant answer as source authority.

For F4, I accept the correct differentiated rent/utility replacements plus attribution to available T2 as substantive provenance. I do not require each answer to repeat both the literal M-C2 name and the previous-occupant usage-sheet phrase. Candidate_6 names M-C2 explicitly; the others still identify the correct source lines and preserve estimate status. This interpretation is documented so later adjudication can disagree openly without rewriting primary labels.

The review distinguishes omissions, unsupported certainty and false facts. It does not demand a repeated profile or full property checklist when one useful remaining check is enough. No critical frozen criterion was missed in this group. This one-group result is not an arm-level comparison or a claim about the full ablation. Two further groups will be appended only when separately supplied.

Detailed quoted reasons are in `independent-rental-sample-review.json`.


## Appended group: S2-r2-T1-group

This second group was reviewed only after its packet was separately supplied. The S1 judgments above remain unchanged. The only additional evidence read was `S2-r2-T1-group.json`, including the complete reference and each candidate's actual memory/history. The packet's full-history candidate was verified to receive exactly the reference history; the others were checked against their own visible facts and source snippets. No plan, mask, arm, cost, call record or primary judgment was inspected.

All six answers correctly decline to certify either flat as meeting independent zero-step access on 15 February 2027. None invents an installed ramp, working lift, acceptable carrying fallback or completed booking. Literal rubric coverage nevertheless differs:

| Group | Anonymous candidate | Criteria met | Main issue |
| --- | --- | ---: | --- |
| S2-r2-T1-group | candidate_1 | 3/5 | Later-email explanation omitted; full-viewing slot not clearly gated; chronology unsupported by date-stripped memory. |
| S2-r2-T1-group | candidate_2 | 2/5 | Uses £2,050 ceiling as Flat 10 cost; omits later-email explanation and earlier access-first sequence. |
| S2-r2-T1-group | candidate_3 | 3/5 | Prose says 19 February but contractor-date scalar says unknown; incomplete conflict/slot sequencing. |
| S2-r2-T1-group | candidate_4 | 5/5 | Correct source chronology, barriers and access-first viewing allocation; cost appears only in scalar section. |
| S2-r2-T1-group | candidate_5 | 3/5 | Contradictory unknown appointment scalar; zero-step rule misattributed to memory; full slot used as fallback access check. |
| S2-r2-T1-group | candidate_6 | 4/5 | Sound access-first advice; later-email explanation absent and two source-support limitations. |

Candidate_2 states “Flat 10 estimated all-in: £2,050/month” and returns 2050 in the matching scalar. Reference U2 gives £2,010; £2,050 is the user's ceiling. Its actual memory omits the unit amount. Honest uncertainty would have been incomplete but defensible; filling the property field with the ceiling is a wrong fact. The unsupported memory attribution and factual contradiction share one issue ID to avoid treating them as two independent numerical errors.

Candidates_3 and _5 state 19 February in prose but return `provisional_contractor_date=unknown`, despite that date being present in their own memory. Unknown completion is a different field. Each is one internal/source inconsistency; correct prose does not cancel the conflicting scalar. Other longer lift-status strings (“out of service following door fault”) are semantically correct, not false merely because they include an extra supported qualifier.

Candidates_5 and _6 cite memory alone for zero steps. Their memory contains the older stairs tolerance and not-yet-final access change; the new zero-step rule is in the latest T1 question. The rule is correct but the attribution is unsupported. Candidates_1 and _6 also narrate earlier/later lift chronology from memory that lacks dates or supersession markers. That ordering is true in the full reference, but not established by their visible records; it is recorded as a minor source-support limitation rather than a wrong operating conclusion.

F2 is a composite frozen criterion: its complete content includes why the later existence-only email does not override the outage. Only candidate_4 explains that distinction. For candidates_1, _3, _5 and _6, the email is absent from actual memory; this is incomplete evidence coverage, not a fabricated claim or unsafe recommendation. Candidate_2's memory does preserve the later-email limitation, but its answer omits it. Calling the composite criterion critical must not be misreported as five unsafe approvals: all six refuse to certify current access.

F4 requires an access-first allocation of the scarce full viewing, not just a useful route checklist. Candidates_4 and _6 explicitly preserve the full slot for a flat whose route first passes. Candidates_1, _3 and _5 use the full slot to repeat/fall back on the access check; candidate_2 combines viewing/access on 16 January instead of using the separate earlier option. Their checklists retain useful-next-step credit, while full criterion coverage is incomplete.

For F5, an accurately labeled estimated-cost scalar supplies the requested figure if prose omits it and does not contradict it. Thus candidates_1, _4 and _5 are not failed solely for placing £2,010 in the facts section. The appointment-scalar issues are recorded under F2 and contradictions rather than counted again as independent cost/booking errors. These explicit interpretations distinguish literal rubric completeness from practical consequence and remain open to later, separately recorded adjudication.

The final S3-r1-T2 group remains unreviewed until supplied. No further packet was polled or opened.


## Final selected group: S3-r1-T2-group

Blinded AI source review, not human ground truth. This section uses only the separately supplied S3-r1-T2-group packet, its full fictional reference history and frozen gold, and each candidate’s actual evidence. It does not use arm labels, costs, model judgments or other reviewers. All six receive the same T2 replacement facts; their previous answers are explicitly non-source material. This agent review is outside measured model CLI totals.

| Anonymous candidate | Criteria met | Main coverage issue | Unsupported attribution | Contradictions |
| --- | ---: | --- | ---: | ---: |
| candidate_1 | 5/5 | None | 0 | 0 |
| candidate_2 | 4/5 | F5: omits remaining cost-estimate limit | 4 scalar fields | 0 |
| candidate_3 | 4/5 | F5: omits remaining cost-estimate limit | 0 | 0 |
| candidate_4 | 4/5 | F3: omits substantive owner-authority basis | 0 | 0 |
| candidate_5 | 3/5 | F4: omits new £345 quote; F5: omits cost-estimate limit | 0 | 0 |
| candidate_6 | 4/5 | F3: omits substantive authority and independent recipient-check basis | 0 | 0 |

All six correctly advance to reviewing the final tenancy pack and keep payment/signature outside the authorised scope. None retains the old Flat 12/38 m² certificate, L. Cress recipient, unknown fallback cutoff or a stale hold. Every scalar value is semantically correct and consistent with prose: Flat 12B, 44 m², Foxbarrel Residential Ltd, £240, unbooked, and 3 March 2027 at 15:00. Full addresses, “not booked,” and an ISO `T` separator do not create factual errors.

Candidate_2 attributes all six scalars to memory. Its memory supports the unchanged £240 and unbooked facts, but four updated roles/values appear only in T2: the certificate’s Flat 12B identity, its 44 m² area, the corrected company payee and the known cutoff. The memory instead gives an EPC for Flat 12/38 m², names L. Cress as payee, and records an unknown cutoff. Merely having Flat 12B as the target or the company as invoice issuer does not support those new certificate/payee assignments. These are four unsupported source attributions, not four false values: T2 is actually available and supports all four. Candidate_5’s `latest_user_question` citation is an unambiguous alias for T2 and is supported.

The frozen F3 asks for the authority and independent-recipient evidence basis as well as the corrected payment details. Candidate_4 records the independent account match but does not identify the owner-authority letter or its substantive authorisation. Candidate_6 gives the correct recipient and terms but omits both that authority basis and the completed callback/bank check. Their general “three ... gates ... answered” conclusion is correct, so these are coverage omissions rather than wrongful advancement or invented verification. Candidate_3 states the substantive landlord-authority and independently confirmed recipient result; it need not name every document again.

F4 accepts “new/current £345” as a replacement of the old quote without demanding that the expired £330 price be recited. Candidate_5 omits the new price entirely; its unbooked status and conditional refund cutoff remain correct. F5 separately requires a remaining cost limitation. Candidate_1’s £2,160 “not re-verified here,” candidate_4’s “remains an estimate,” and candidate_6’s review of “all-in assumptions” retain that limitation in substance. Candidates_2, _3 and _5 omit it. Their other uncertainty statements remain appropriate and none claims a fixed bill or comprehensive rental/legal PASS.

All six have useful next steps and acceptable user burden. Candidate_5’s extra listing-versus-official-area comparison (47 versus 44 m²) is supported by its actual memory and does not reintroduce a blocker. The unchanged 40 m² minimum need not be recited where the correct current 44 m² record is used without an obsolete rejection. These explicit interpretations preserve literal coverage requirements while distinguishing omission, wrong fact, unsupported attribution and practical consequence.

## Completed bounded review scope

All three planned groups are now complete: S1-r1-T2-group, S2-r2-T1-group and S3-r1-T2-group, with 18 anonymous answers and 90 criterion decisions. The previous 12 JSON assessment objects are preserved unchanged. Earlier pending-scope statements above describe the review state when those sections were written and are superseded by this completion record. This is the prospectively selected source-audit sample only, not a claim about every answer in the ablation. No model CLI/API calls, frozen-file edits or commits were made for this review.
