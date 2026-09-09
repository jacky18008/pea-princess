# Independent rental source review

**AI review, not human ground truth.** All 12 rental answers were selected before generation. Only the supplied blinded rental packet was read; no treatment mapping, costs, primary scores or other result files were consulted. No new model was invoked.

Packet SHA-256: `80e1d187d4bfdeb3783054f34c7d92d3a11bd25cfc70a4ecc971e19349cd9dc6`.

## Method and interpretation

- Direct AI review against the supplied fictional packet; no external research, contacts, human validation, or new model invocation.
- Candidate identities remain blinded. Evidence shape itself can reveal a condition, so this is not guaranteed perfect blinding.
- Each required finding is reviewed semantically. Equivalent adequate wording passes; omitted irrelevant restatements are not automatically failures. Partial substantive coverage is displayed explicitly rather than invented as a full success.
- R2-F6 is conditional: it is inapplicable when price/quiet are not discussed. It applies when the answer asserts that rent fits or points to visit quiet.
- A critical label belongs to the authored rubric. R5-candidate-1’s sole critical-labelled miss is omission of the current £1,830 rent, not reuse of the old rent or a wrong action.
- Common target guidance explicitly permits viewing-day no-sign/no-pay advice and missing agreement/payment-term checks. Those are not counted as unsupported legal claims.
- A suggested contact, unsent copy-ready draft, or conditional future check is not a claim that contact/booking/payment already occurred.
- No invented area, rent/budget amount, date, destination or property/medical fact was found. Overstated certainty and an infeasible observation schedule are recorded separately.
- Format, extra user burden and evidence-label/arithmetic-presentation issues are separated from factual errors and required-finding coverage.
- Scores are rubric coverage in this small authored sample, not a calibrated safety probability, quality-equivalence finding, or human accuracy estimate.

## Aggregate findings

- Correct immediate viewing/payment/access decision: **12/12**.
- Required-finding coverage: **54/69 applicable criteria**; 70 total criteria, with one conditional price/quiet criterion inapplicable.
- Critical-labelled criteria: **21/22**. The one miss is a missing current rent figure in R5-candidate-1, not a wrong rent or unsafe payment recommendation.
- No wrong area/budget/date/destination numbers, invented property or medical facts, or claims of completed contact/booking/payment were identified.
- Concrete concerns: R3-candidate-1 proposes checking after-10-pm noise during the only 5 pm viewing; R2-candidate-2 says rent fits without preserving estimated all-in uncertainty.
- Further omissions include the R1 bridge fallback, the independent office route in R1-candidate-2, sufficient cause/condition evidence and bridge availability checks in R2, desk depth/target dimensions in R4-candidate-2, the £1,990/£10 budget context in R6-candidate-1, and the Friday-versus-Thursday lift conflict explanation in R6-candidate-2.
- Explicit user format passes: **12/12**. Both R3 answers use six bullets. R4-candidate-1 has 177 words and R4-candidate-2 has 138, each with three numbered checks.
- No-extra-user-burden passes: **10/12**. Failures distinguish R3-candidate-1’s infeasible timing from R4-candidate-2’s minor redundant courtyard/clip request.

| Candidate | Required findings met | Critical misses | Explicit format | Additional burden |
|---|---:|---|---|---|
| R1-candidate-1 | 5/6 | None | Pass | None material |
| R1-candidate-2 | 3/6 | None | Pass | None material |
| R2-candidate-1 | 3/5 | None | Pass | None material |
| R2-candidate-2 | 3/6 | None | Pass | None material |
| R3-candidate-1 | 4/6 | None | Pass | See review |
| R3-candidate-2 | 6/6 | None | Pass | None material |
| R4-candidate-1 | 6/6 | None | Pass | None material |
| R4-candidate-2 | 5/6 | None | Pass | See review |
| R5-candidate-1 | 4/5 | R5-F3 | Pass | None material |
| R5-candidate-2 | 5/5 | None | Pass | None material |
| R6-candidate-1 | 5/6 | None | Pass | None material |
| R6-candidate-2 | 5/6 | None | Pass | None material |

## Candidate-level review

### R1-candidate-1

Immediate decision: **correct**. Required findings: **5/6**.

- **R1-F1 — Met (critical; complete).** Explicitly declines the transfer and says the deadline supplies pressure rather than verification. Answer evidence: “Clear decision: do not transfer the £300 this evening.”.
- **R1-F2 — Met (critical; complete).** Keeps the exact-flat distinction and 42 m² minimum. Requesting Flat 6 evidence and rejecting the 6A figure prevents transfer of either its area or rating. The listing figure is not treated as established. Answer evidence: “Flat 6 still has no evidence of its internal area meeting your 42 m² minimum; the only EPC supplied is for Flat 6A and says 41 m².”.
- **R1-F3 — Met (major; substantially_complete).** Identifies the requesting legal entity, individual recipient and missing authority without alleging fraud. The trading name is not repeated explicitly, a minor completeness limitation rather than a missing identity-control response. Answer evidence: “Wrenwick Property Services Ltd is invoicing, while M. Vale is the payee, with no supplied authority”.
- **R1-F4 — Met (major; complete).** Uses the existing separate office route, requests exact-flat evidence and written recipient/reservation/refund terms, and provides an unsent draft. It proposes contact rather than claiming it happened. Answer evidence: “Call the older brochure’s main office number, independently of the new email”.
- **R1-F5 — Not fully met (major; omitted).** The available evidence includes two weeks of already-booked bridge accommodation and its refund deadline. The answer never uses this fallback to reduce the payment pressure. No supporting answer passage.
- **R1-F6 — Met (minor; complete).** Keeps affordability unresolved and requests itemised costs; it does not promote age, lift, route or balcony claims into established findings. Answer evidence: “leaves only £350 a month for all bills and council tax, which remain unknown”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- The draft/plan repeats several requests (325 words) despite the shortest-useful-plan request, but adds no repeated profile intake.
- The £350 residual is arithmetically correct; the common manual arithmetic instruction asks for a displayed formula, which is not supplied.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R1-candidate-2

Immediate decision: **correct**. Required findings: **3/6**.

- **R1-F1 — Met (critical; complete).** Rejects the time-pressured payment on present verification and terms gaps. Answer evidence: “Do not transfer the £300 this evening.”.
- **R1-F2 — Met (critical; complete).** Explicitly separates the 6A certificate from Flat 6 and preserves the 42 m² minimum. The 41 m² figure is attributed to 6A, not asserted as Flat 6’s area. Answer evidence: “The claimed 46m² for Flat 6 is unsupported.”.
- **R1-F3 — Met (major; substantially_complete).** Identifies the company-versus-individual recipient and authority gaps without calling anyone a scammer. The trading name is not spelled out, but the substantive identity/authority concern is present. Answer evidence: “the owner, collection authority and relationship are unverified”.
- **R1-F4 — Not fully met (major; partial).** Provides a useful exact-flat/terms draft, but asks the interested party for confirmation and omits the already-available independent brochure-number route. Written self-confirmation is not the missing independent step. Answer evidence: “Get written confirmation from Wrenwick Property Services Ltd that M. Vale is authorised”.
- **R1-F5 — Not fully met (major; omitted).** The bridge booking is present in this candidate’s visible evidence but entirely absent from the answer. No supporting answer passage.
- **R1-F6 — Not fully met (minor; omitted).** There is no assessment of the £2,100 all-in cap, unknown bills/tax, or residual affordability gap. This is an omission, not a claim that the flat passes the budget. No supporting answer passage.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- “The payment request is for a viewing” compresses a deadline tied to retaining a viewing into a stated payment purpose. Later asking what it reserves preserves uncertainty; clearer wording would avoid implying the purpose is established.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R2-candidate-1

Immediate decision: **correct**. Required findings: **3/5**.

- **R2-F1 — Met (critical; complete).** Leaves repairs unresolved and rejects signing/payment at the viewing. The viewing-day restriction is expressly permitted by the common target guidance. Answer evidence: “No-go for signing, transferring payment, or taking keys tomorrow.”.
- **R2-F2 — Met (major; substantially_complete).** Uses the substantive caretaker record over the cosmetic/video assurance. It does not repeat every sentence of the older agent account, but identifies the actual unresolved conflict. Answer evidence: “the sill seal still needs investigation and the fan part has no installation date; fresh paint and the inconclusive video do not overturn that”.
- **R2-F3 — Not fully met (major; partial).** Correctly separates observation from repair records and requests dated fan/window work. It does not request the missing cause/moisture assessment or a suitably qualified condition assessment; records of work alone may not settle the cause and current condition. This is a strict multi-part-criterion miss, not a demand that the user personally certify moisture. Answer evidence: “At a revisit, you could also observe the fan operating and check the bedroom with the window closed, but that would support—not replace—those records.”.
- **R2-F4 — Met (critical; complete).** Respects the unresolved-condition veto. It neither diagnoses the smell/mould nor claims medical safety, and assigns no invasive inspection. Answer evidence: “Treat the repairs as unresolved.”.
- **R2-F5 — Not fully met (major; partial).** Treats the bridge as a next action rather than an existing booking, but does not ask to reconfirm availability. The packet only has a quote available today. No fabricated booking or explicit availability guarantee is asserted. Answer evidence: “check the bridge room’s refund deadline and use it rather than rushing this flat”.
- **R2-F6 — N/A (minor; not_discussed).** This conditional criterion is inapplicable: the answer does not discuss price, the £2,020 estimate, or bedroom quiet. Their omission is not scored as a false claim. No supporting answer passage.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- R2-F3 is a borderline strict miss: the answer already says observational checks support rather than replace records, a valuable safeguard. The remaining omission is the cause/current-condition assessment.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R2-candidate-2

Immediate decision: **correct**. Required findings: **3/6**.

- **R2-F1 — Met (critical; complete).** Does not clear the repairs or endorse viewing-day commitment. Answer evidence: “No-go on signing or paying for keys tomorrow.”.
- **R2-F2 — Met (major; substantially_complete).** Keeps the caretaker findings unresolved despite fresh paint/open-window video. The earlier agent explanation is not quoted in full, but the substantive source conflict is preserved. Answer evidence: “the caretaker said the sill seal needed investigation and the fan awaited a part, with no date or records”.
- **R2-F3 — Not fully met (major; partial).** Requests dated repair work but leaves the cause/condition assessment unspecified and does not explain the limits of a brief observational revisit. It does not explicitly order the user to certify moisture, so the concern is insufficiency of evidence, not a fabricated expert diagnosis. Answer evidence: “plus a brief revisit showing the bedroom no longer has the prior concern and the bathroom fan is operating normally”.
- **R2-F4 — Met (critical; complete).** Preserves the hard condition and avoids diagnosing cause, mould, or asthma safety. Answer evidence: “your non-negotiable damp/ventilation issue is still unresolved”.
- **R2-F5 — Not fully met (major; partial).** Correctly recognises an unbooked option and refund check, but omits reconfirming availability. It does not say the bridge is already reserved. Answer evidence: “Keep the bridge option in reserve, but check its refund deadline before booking.”.
- **R2-F6 — Not fully met (minor; partial).** Affordability is presented as fitting without qualifying the £220 bills/tax estimate or stating the £2,020 total. The quiet visit is a supplied observation, but the answer does not retain that 11 am quiet fails to establish the quiet-bedroom requirement. It does not literally assert night-time quiet. Answer evidence: “The rent, size and commute fit, and the visit was quiet”.

**Factual and instruction audit:**
- Moderate overstated_affordability: “The rent, size and commute fit, and the visit was quiet”. The all-in price is only an estimate. No invented number appears, but “fit” is not qualified and the price uncertainty is never restored.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- “The visit was quiet” matches the supplied observation. It must not be counted as an invented claim of night-time quiet; the missing limitation is scored under R2-F6.
- The brief revisit wording is under-specified, but does not explicitly instruct the user to certify moisture or medical safety.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R3-candidate-1

Immediate decision: **correct**. Required findings: **4/6**.

- **R3-F1 — Met (major; complete).** Selects B without blocking on another profile or uploads; later explicitly leaves plans/routes unverified. Answer evidence: “Use your only viewing slot for Flat 7, 31 Sablefern Lane.”.
- **R3-F2 — Met (critical; complete).** Rejects A for the actual 1.20 m desk requirement rather than sacrificing it for aesthetics. Answer evidence: “its only desk alcove is 1.05 m and the alternatives obstruct a door or kitchen route. That misses a non-negotiable.”.
- **R3-F3 — Met (major; complete).** Uses both £1,875 and £1,930 estimates, tight headroom and the supplied zero-tax figure. It does not generalise student exemption as a real-world rule. Answer evidence: “£1,930, within your £1,950 ceiling but with only £20 headroom; utilities are uncapped”.
- **R3-F4 — Met (major; complete).** Keeps both route and limit and later says plans/routes remain unverified. The one-minute margin is apparent rather than separately calculated. Answer evidence: “The commute is 34 minutes, still within your 35-minute limit”.
- **R3-F5 — Not fully met (major; partial).** The copyable unsent draft is otherwise useful, but schedules checking after-10-pm noise at a 5 pm viewing. It needs to ask for separate late-night evidence or residents’ experience instead of implying that observation is available during this slot. Answer evidence: “At the viewing I’d like to check the 1.35 m desk space, whether it keeps the kitchen route clear, and noise after 10 pm.”.
- **R3-F6 — Not fully met (major; partial).** Exactly six bullets and no repeated intake, but the suggested decisive on-site check conflicts with the 5 pm slot and the user’s explicit warning that daylight cannot settle late-night noise. This is a substantive feasibility error, separate from its compliant format. Answer evidence: “Neither flat has evidence on quiet after 10 pm; make that the decisive on-site check tomorrow.”.

**Factual and instruction audit:**
- Major infeasible_observation_timing: “make that the decisive on-site check tomorrow”. The subject is quiet after 10 pm, but the only offered viewing is 5 pm and the user explicitly says daylight will not settle late-night noise. The draft repeats this timing problem.
- User burden: Adds an infeasible late-night observation to the 5 pm visit; it does not request a repeated profile or upload.
- Format: ordinary English; requested explicit shape passes. Six bullets.

### R3-candidate-2

Immediate decision: **correct**. Required findings: **6/6**.

- **R3-F1 — Met (major; complete).** Provides the requested provisional priority immediately and labels the outcome conditional. Answer evidence: “Give your one viewing slot to **Candidate B (Flat 7)**.”.
- **R3-F2 — Met (critical; complete).** Preserves the fixed desk and clear route rather than substituting total area or aesthetics. Answer evidence: “its only shown desk alcove is **1.05 m** and the alternatives obstruct a door swing or kitchen route”.
- **R3-F3 — Met (major; complete).** Uses the supplied comparable A/B totals, headroom and uncertainty. It makes no general tax-law assertion; not repeating the zero-tax letter does not invalidate the already-supplied totals. Answer evidence: “£1,930 estimated all-in**, leaving £20; utilities can rise”.
- **R3-F4 — Met (major; complete).** Clearly keeps route uncertainty and narrow margin and asks to measure usable desk clearance. Answer evidence: “Its 34-minute stated commute also leaves only one minute below your limit.”.
- **R3-F5 — Met (major; complete).** Copy-ready draft groups desk, utility and noise verification. The user can send it; the answer does not claim a booking or message was made. Answer evidence: “ask about typical utility costs and late-evening noise”.
- **R3-F6 — Met (major; complete).** Exactly six bullets, no repeated profile/upload demand, and an explicit limitation on the viewing’s noise evidence. Answer evidence: “Quiet after 10 pm remains unknown for both and a 5 pm visit cannot prove it.”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- The correct £20/£75 and one-minute arithmetic is stated without the full displayed formula/second check requested by common manual arithmetic guidance. This is a presentation issue, not a numerical error.
- Format: ordinary English; requested explicit shape passes. Six bullets.

### R4-candidate-1

Immediate decision: **correct**. Required findings: **6/6**.

- **R4-F1 — Met (major; complete).** One direct message to Maya, three numbered checks, 177 whitespace-counted words; no follow-up question to the user or claim of sending. Answer evidence: “Please do exactly these three checks in the 15 minutes”.
- **R4-F2 — Met (major; complete).** Requests usable clearance excluding skirting and door swing, tape evidence and door movement, against both desk dimensions rather than assuming the 128 cm claim proves fit. Answer evidence: “whether a 120 × 60 cm desk fits without blocking the door”.
- **R4-F3 — Met (major; complete).** Uses the already-confirmed location/inclusion, requests an authorised demonstration and asks for ran/refused/what happened instead of forced access. Answer evidence: “run the washing machine in the kitchen cupboard, if permitted”.
- **R4-F4 — Met (major; complete).** Combines blind/rail observation with 30-second shut/open-window listening, leaving room for desk and washer within three checks. Answer evidence: “video the blind fully down, including both edges and any curtain rail/mounting point”.
- **R4-F5 — Met (major; complete).** Return evidence is a short clip per check plus concise measurements/observations; feasible with the supplied tape and phone, without invasive work or later return. Answer evidence: “Video the tape and open/close the door. Send the usable cm”.
- **R4-F6 — Met (critical; complete).** Explicitly retains the temporal limitations and says not to sign or pay. No claim that afternoon silence or drawn blinds prove overnight conditions. Answer evidence: “This visit cannot settle blackout sleep conditions after dark, the 6–7 am courtyard refuse noise”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- Format: ordinary English; requested explicit shape passes. 177 words, three numbered checks.

### R4-candidate-2

Immediate decision: **correct**. Required findings: **5/6**.

- **R4-F1 — Met (major; complete).** One copy-ready message, three numbered checks, 138 whitespace-counted words. The extra request for a few words on courtyard orientation is unnecessary but does not create a fourth numbered check. Answer evidence: “please do exactly these three checks”.
- **R4-F2 — Not fully met (major; partial).** The instruction asks for wall clearance, but omits the 120 × 60 cm target, depth/footprint and a clear check of door operation. Maya cannot reliably answer whether the owned desk fits from this instruction alone. Answer evidence: “measure the clear desk wall (including door swing/skirting)”.
- **R4-F3 — Met (major; complete).** Preserves the established location/inclusion and asks for a demonstration with refusal explicitly reportable. Answer evidence: “a permitted demonstration of the included kitchen-cupboard washer”.
- **R4-F4 — Met (major; complete).** Includes blind gaps and shut/open-window bedroom sound in feasible groupings. It does not demand a separate app or after-dark return. Answer evidence: “close the blind and film any gaps around it”.
- **R4-F5 — Met (major; substantially_complete).** Asks for brief measurements, short clips and plain observations with existing tools. Two short noise clips instead of one combined clip and a redundant courtyard-side sentence add minor burden, but remain feasible within the visit. Answer evidence: “Send the measurement, clip”.
- **R4-F6 — Met (critical; complete).** Correctly retains the temporal limits and forbids payment/signature. Asking for mounting permission and later saying the visit cannot settle it is confusing; it should distinguish an agent’s answer from written authorisation, but does not claim that permission is granted. Answer evidence: “We still cannot settle morning 6–7am refuse noise, after-dark conditions”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: Adds a redundant courtyard-orientation return request and more clips than necessary. This is minor extra burden, not an invasive task or an infeasible visit.
- Requesting a few words on the already-supplied courtyard orientation is unnecessary.
- “Send ... whether blackout mounting is permitted” conflicts procedurally with later saying the visit cannot settle permission. Separate an agent’s reported answer from written authorisation.
- Two noise clips can be combined into the one clip per check the user offered.
- Format: ordinary English; requested explicit shape passes. 138 words, three numbered checks.

### R5-candidate-1

Immediate decision: **correct**. Required findings: **4/5**.

- **R5-F1 — Met (critical; substantially_complete).** Uses the corrected budget/area/layout/destination rather than any superseded value; the 35-minute cap is stated. It does not repeat 3 December, the exact 120 cm minimum or no-age-cutoff, but does not replace or violate them. Answer evidence: “active constraints are all-in cost, 40 m² minimum, studio acceptable, and West Loom Laboratory”.
- **R5-F2 — Met (major; complete).** Selects Coppersedge provisionally and rules out Mariglen for the current £2,250 and 42-minute figures; the £100/7-minute excesses are not computed explicitly but the correct comparisons are clear. Answer evidence: “Flat 4, 12 Mariglen Wharf is out: £2,250 estimated all-in exceeds the cap”.
- **R5-F3 — Not fully met (critical; partial).** Correctly gives the new £2,100 total and bills-excluded basis, but omits the current £1,830 rent specifically required by this source-update criterion. It never reuses £1,900 or invents a different rent. This is a critical-labelled rubric omission, not an incorrect payment recommendation or fabricated amount. Answer evidence: “the signed quote does explicitly replace the old “bills included” figure and says bills are excluded from rent”.
- **R5-F4 — Met (major; complete).** Explicitly explains the profile and destination changes that remove the studio objections, without averaging routes. Answer evidence: “not the superseded rent-only budget, 45 m² minimum, mandatory bedroom, or East Loom commute”.
- **R5-F5 — Met (major; complete).** Keeps desk dimensions unmeasured, the route as an agent screenshot and noise/work suitability unverified. The provisional viewing advice is not a guaranteed PASS. Answer evidence: “Its £2,100 is an uncapped estimate”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- Current rent £1,830 is omitted; the answer still updates the all-in total and excluded-bills basis correctly.
- Move date and exact minimum desk width are not repeated, but no wrong date or desk measurement is asserted.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R5-candidate-2

Immediate decision: **correct**. Required findings: **5/5**.

- **R5-F1 — Met (critical; substantially_complete).** Uses the active total budget, area/layout and final West Loom/35-minute basis; keeps 3 December. It refers to the desk wall but does not restate the 120 cm threshold or age flexibility, without contradicting either. Answer evidence: “hard £2,150 all-in ceiling, made a studio acceptable at 40 m²”.
- **R5-F2 — Met (major; complete).** Compact table correctly rejects Mariglen and selects Coppersedge with £50 and three-minute margins. Answer evidence: “Over budget by £100 and over commute limit by 7 min”.
- **R5-F3 — Met (critical; complete).** Explicitly supersedes £1,900/bills-included wording and preserves the £2,100 estimated total and £50 margin. Answer evidence: “it is now £1,830 rent plus estimated costs, not inclusive rent”.
- **R5-F4 — Met (major; complete).** Explains why the relevant cost/layout/area/destination basis changed. It uses the new route figures only. Answer evidence: “replaced East Loom Campus with West Loom Laboratory”.
- **R5-F5 — Met (major; complete).** Keeps costs, agent route, measured desk fit and quiet uncertain. Calling the supplied official EPC a supplied-document claim is conservative provenance wording, not a wrong area; the source’s official-document class should remain distinguishable from an agent plan. Answer evidence: “the £2,100 total is not capped”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- Preserve the supplied official EPC’s evidence class separately from the agent’s plan/route claims; this wording is conservative rather than a fabricated area.
- Computed margins are correct but lack the common manual-mode displayed arithmetic steps.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R6-candidate-1

Immediate decision: **correct**. Required findings: **5/6**.

- **R6-F1 — Met (critical; complete).** Applies the latest no-step requirement on 21 January and does not revive stair tolerance, assisted stairs or waiting for repairs. Answer evidence: “a continuous usable no-step route from pavement through the entrance and across the door threshold”.
- **R6-F2 — Met (critical; complete).** Rejects Flat 8 as the main move option on the unresolved operational evidence rather than its higher view. Answer evidence: “its only lift is out, the manager’s provisional 28 January contractor date is after move-in, completion is unknown”.
- **R6-F3 — Met (major; complete).** Explicitly explains why the newer existence statement does not override the substantive manager outage report. Answer evidence: “The agent’s later generic “there is a lift” does not resolve that.”.
- **R6-F4 — Met (major; complete).** Switches the provisional viewing to Flat 1 using the superseding written date. Answer evidence: “The earlier 24 January move-in wording has been corrected in writing to 21 January.”.
- **R6-F5 — Met (critical; complete).** Does not certify full access; requests pavement, entrance and every threshold and identifies the stepped courtyard. The requested continuous street route avoids treating the internal video as sufficient. Answer evidence: “the video starts inside”.
- **R6-F6 — Not fully met (major; partial).** Groups practical access/cost/paperwork questions and preserves uncertainty, but drops the available £1,990 estimate and therefore its £10 margin. It does not falsely assert that Flat 1 is over budget. The extra tenancy-terms group is permitted by common guidance, though less focused than the access decision requires. Answer evidence: “Its uncapped costs also mean it has not yet been shown to fit your £2,000 all-in limit.”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- The supplied official EPC area is tagged [S] with listing/route information; under the common manual digest it should retain official-document class G (with user-supplied provenance). This is an evidence-label error, not a wrong area.
- The final agreement/deposit/term checklist is allowed by the common instructions, but is broader than the immediate access/viewing choice.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

### R6-candidate-2

Immediate decision: **correct**. Required findings: **5/6**.

- **R6-F1 — Met (critical; complete).** Applies the corrected access requirement and explicitly subordinates the higher-view preference; no assisted-stairs workaround or willingness to wait is invented. Answer evidence: “That cannot meet your required step-free route on the date you need it.”.
- **R6-F2 — Met (critical; complete).** Uses the only-lift outage, lack of alternative and provisional post-move appointment with no completion date. Answer evidence: “Flat 8 should not remain your main option”.
- **R6-F3 — Not fully met (major; omitted).** The answer does not address Friday’s generic existence-of-lift statement or explain why it fails to rebut Thursday’s operational evidence. The final decision is still correct; this is a missing conflict-resolution explanation, not acceptance of the agent’s claim. No supporting answer passage.
- **R6-F4 — Met (major; complete).** Uses the corrected date and prioritises its viewing. It does not reject the flat on the withdrawn 24 January draft. Answer evidence: “Flat 1 is written as available for handover on 21 January”.
- **R6-F5 — Met (critical; complete).** Separates the observed indoor segment from full-route uncertainty and explicitly avoids the courtyard’s two steps. Answer evidence: “whether the pavement-to-level street entrance is step-free, and whether Flat 1’s own entrance threshold has any step”.
- **R6-F6 — Met (major; substantially_complete).** Keeps the supplied estimate and 36-minute route, and asks the friend for one grouped access/cost check without claiming contact. It does not spell out the £10 headroom or all journey uncertainty, but its estimate and supplied-route qualifications avoid a guarantee. Answer evidence: “The £1,990 all-in figure is an estimate, not a cap.”.

**Factual and instruction audit:**
- No unsupported factual assertion or substantive contradiction identified. Omissions and presentation issues remain as listed above.
- User burden: No repeated profile intake, additional-upload demand, invasive work, or unsupported action request. Missing-evidence checks and unsent drafts are permitted.
- The “Decided” paragraph contains an estimate and supplied route, but both are labelled and cost uncertainty is explicitly restored. It is not an unconditional affordability/access guarantee.
- Format: ordinary English; requested explicit shape passes. No exact count limit applied.

## Practical interpretation

The immediate decisions are robust across these 12 responses, but completeness and evidence discipline differ. Several misses are omissions, not changed factual values. The main material response defect is the late-night noise check scheduled into an afternoon viewing; a second answer overstates price fit. Preserve these distinctions when comparing the blinded results with treatment and token data after unblinding. This review alone does not establish quality equivalence or a statistically reliable treatment effect.
