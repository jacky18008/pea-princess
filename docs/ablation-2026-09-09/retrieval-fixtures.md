# Retrieval fixtures for the 2026-09-09 ablation

These are three new agent-authored synthetic cases, not real production records or untouched population holdouts. Every entity, artifact, measurement, rule and event is invented. They are distinct from the earlier A1–A4 reporting/analysis pilot and contain one supported narrow approval, one observed regression requiring rejection of a promotion, and one historical content question that the retained evidence cannot settle.

Only `evals/ablation-2026-09-09/retrieval-cases.json` and this note were written by the fixture author. No benchmark, CLI model, external-model, network or Claude call was made. Current agent authorship/review is not zero-cost work and sits outside any later measured CLI workload. No summary was prepared: the root runner will generate each variant's neutral summary live and account for that generation separately.

## Pair construction and bounds

| Case | Decision supported by source | Short document characters | Long document characters | Essential oracle sources |
| --- | --- | ---: | ---: | --- |
| E1 | Approve the sandbox nightly-default request within its stated gate and scope | 7,591 | 26,521 | E1-D01, E1-D02 |
| E2 | Reject/hold automatic routing promotion because opaque identifiers are changed | 7,057 | 24,879 | E2-D01, E2-D02 |
| E3 | Cannot certify the archived export's actual catalog revision | 6,765 | 24,413 | E3-D01, E3-D02 |

Each case has one question and one gold object outside its variants. Each variant has four documents with identical IDs and titles. Every short document is an exact prefix of its long counterpart. The additions are corresponding operational documentation: field meanings, workflow boundaries, configuration ownership, source/reference provenance, lifecycle and archival records. They add no scored scenarios, new decisive outcome, repaired build, recovered historical content, or changed requirement. They are not repeated copies of source paragraphs. Some factual concepts recur naturally across different source roles; the long condition is a context-length/content-expansion manipulation, not a claim that token length is isolated from all semantic emphasis or ranking effects.

All decisive evidence already appears in the short documents, and every required finding can be justified from D01+D02. D03/D04 supply ordinary integration and provenance context. Their presence can affect a query-based ranker; that is an observable retrieval result, not a reason to edit the fixture after seeing output. Titles describe source types and contain no verdict labels. Outcome labels in this note and all gold/oracle metadata must stay out of answering and summary-generation prompts.

The oracle IDs deliberately use gold knowledge. Oracle retrieval is a diagnostic comparison and not a deployable selector or guaranteed quality ceiling: an answerer can still misread the selected evidence. A generated summary may preserve enough evidence for any particular finding, or may omit it. In E3 especially, summary-only abstention is adequate only if the actual generated summary contains the necessary missing-evidence facts and field semantics. No summary-success outcome is presumed from the fixture design.

## Independently authored gold rationale

Gold and scalar checks were written from source statements, before any target or summarizer output, rather than from a summary or shared extraction function. Recommendations below are reviewer inferences from the specified gate or evidence gap; they are not represented as completed source actions. Exact source excerpts remain identical across each pair.

### E1: bounded approval

| Finding | Source basis and interpretation |
| --- | --- |
| E1-F1 | D01 requests only the existing nightly sandbox default and states, “Broader deployment requires another review and is outside HBR-14.” Its declared gate and D02 results support approval of that limited change. Requiring proof of production-wide reliability would expand the actual request. |
| E1-F2 | D01 records “Candidate accepted runs: 48/48.” D02 has “total, 48, 46, 48” and “Cobalt wrong_record_updates=0; non_sandbox_writes=0”. The category sums independently agree: 20+12+8+8=48; baseline 20+10+8+8=46; candidate 48. |
| E1-F3 | D01 states “Endpoint restriction: enabled throughout the comparison.” D02 records restoration to Larch and two accepted smoke scenarios. Those meet the operational gate, rather than merely suggesting a rollback might be possible. |
| E1-F4 | D02 states “The default remains Larch pending HBR-14.” A reviewer can approve the request without claiming the operator already changed the scheduled job. Exact citation supports that temporal distinction. |
| E1-F5 | D01 limits the change to a fixture job and D02 supplies a single comparison plus a usable rollback. Checking the first nightly effective configuration, accepted count and destination audit is a proportionate subsequent operating check. Source data do not establish general population reliability. |

A response that approves only the bounded job can be correct even while flagging broader unknowns. A response that withholds approval solely because the data are not a universal reliability proof should not receive the same decision credit. A substantive newly identified problem would need source support rather than a generic disclaimer.

### E2: observed identifier regression

| Finding | Source basis and interpretation |
| --- | --- |
| E2-F1 | D01 states that a reference mismatch is blocking “regardless of parsing duration”; Cedar matches 60/60 while Birch matches 58/60. The requested automatic promotion therefore fails its own gate. |
| E2-F2 | D02 states, “Route identifiers are opaque strings. Leading zeroes are significant.” The trace changes suffix “007” to numerical 7 and joins “A-7”, selecting east-70 instead of A-007/east-07. A separate B-004/B-4 trace shows the second mismatch. The observed transformation and wrong lookup support a specific mechanism, not an allegation of intent. |
| E2-F3 | D01 reports median parser durations 145 ms and 91 ms separately from the reference-match counts. The category sums are 20+20+18+2=60 and Birch's matches are 20+20+18+0=58. Timing improvement does not waive the identity contract. These authored frequencies are not production incidence estimates. |
| E2-F4 | D01/D02 explicitly record “dispatch_enabled=false”; no dispatch or inventory mutation is represented. The wrong preview is real within the invented run, while actual misdelivery would be an unsupported additional claim. |
| E2-F5 | The preserve-string contract, traced coercion and absence of a corrected run justify retaining Cedar, changing the transformation, and checking independent reference targets before reconsideration. Alternative sound enforcement strategies are acceptable; no particular code patch is presumed to be tested. |

The expected decision is a grounded hold/rejection of this promotion, not rejection of all future versions or a prediction that every identifier will fail. The output must locate the concrete contract violation rather than merely express generic caution.

### E3: unanswerable historical content claim

| Finding | Source basis and interpretation |
| --- | --- |
| E3-F1 | D01 has “resolved_table_catalog_revision=not_recorded”; D02 says the full body expired and input/binding snapshots were not captured. Neither R7 throughout nor an alternative actual revision is established by this packet. |
| E3-F2 | D01 defines the cover label as copied from the form: “It is not derived from the table-data binding.” Completed status and page count describe the render, not which catalog rows were read. |
| E3-F3 | D02's pointer observation is dated 26 August, after H17 began on 25 August, and lacks earlier history/cache binding. D01 supplies no trusted R7 output digest reference. The surviving digest, cover and later pointer state cannot fill the missing content observation. |
| E3-F4 | D01 records “status=completed” and “rendered_page_count=18”. The preview is page 1 and has no table rows. These facts support successful artifact generation/acceptance, not a failed renderer or a known wrong revision. |
| E3-F5 | D02 limits its absence statement to this archive and leaves BR-H17 pending. Seeking an independent original or immutable run binding is a conditional verification path. A later export is explicitly a new artifact, so reconstruction needs a historical qualification rather than a claim to recover the original by rerunning. |

The correct uncertainty is about the historical source/content, not whether a job ran. “Unknown” in the scalar check is from the supplied packet; it does not claim that nobody anywhere could possess an independent copy. A summary reader must not invent the unreceived table pages or pretend a future record request succeeded.

## Scalar checks and scoring interpretation

Each case has six string-valued checks linked to sources. E1 checks 48 candidate passes, 46 baseline passes, 48 scenarios, zero non-sandbox writes, current default Larch and completed rollback. E2 checks 60 scenarios, 58 candidate matches, 60 baseline matches, two wrong targets, A-7 for the selected candidate trace and disabled dispatch. E3 checks completed status, 18 pages, one retained preview page, requested label R7, absent full body in this archive and unknown actual table revision.

These are exact scalar targets, not a substitute for the five substantive findings. A correct scalar can be copied without understanding the decision, while a useful response may express a value equivalently in prose. The runner should keep scalar extraction/normalization, exact quotation existence, semantic support and overall decision judgments separate. “completed” for E3 must not be graded as a claim that its content was validated, and “absent” is scoped to the reviewed archive.

Honest uncertainty, missing finding coverage and unsupported confident claims are different outcomes. A reader with only a lossy summary may correctly withhold claims about unseen records while missing a supported approval or concrete regression; that is not the same error as inventing the records. Conversely, generic refusal is not full task completion on E1. Exact available-summary quotations are legitimate only when the runner supplies and labels that summary as a source; unseen document titles never substitute for their contents.

## Validation and limitations

Validation parsed the JSON; checked three unique cases, four unique document IDs per variant, shared titles/IDs, exact short-prefix nesting, the requested character ranges, exactly five findings per case, six scalar checks per case, valid source references and two-document oracle limits. Category arithmetic in E1 and E2 was independently checked from their rows. No target outputs were used to revise these fixtures.

This is a small, constructed three-decision pilot. Having an approval control corrects the earlier all-challenge design but does not make the set representative, balanced across real error costs, or sufficient for statistical equivalence. Long variants include authored operational detail rather than naturally sampled production histories; they can change salience and retrieval ranking as well as token volume. The run must account for live summary-generation cost and all adaptive selection/follow-up calls rather than treating fixed summaries or oracle choices as free production capabilities.
