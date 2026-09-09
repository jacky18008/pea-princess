# Scalar source review — complete failed-field coverage

**Post-hoc selective unblinded AI review.** Arm IDs and expected/got values were visible. This is a parent/subagent source check, not a primary judge, not a blinded review, and not a whole-answer or citation audit. No primary-judge or other-reviewer artifacts were read. Parent/subagent review is excluded from measured CLI token totals; no model CLI/API calls were made.

Scope: E1-long, E1-short, E2-long, E2-short, E3-long, E3-short, S1-r1-T1, S1-r1-T2, S1-r2-T1, S1-r2-T2, S2-r1-T1, S2-r1-T2, S2-r2-T1, S2-r2-T2, S3-r1-T1, S3-r1-T2, S3-r2-T1, S3-r2-T2. All 108 answer artifacts in these groups were checked; 99 deterministic mismatches affect 62 answers. Frozen inputs, original answers, expected/got strings and all deterministic labels remain unchanged.

Selected mismatches: 86 wording/format equivalents; 3 dates recoverable from visible context; 9 missing/unknown scalars; 1 actual wrong values. Context-equivalent dates still fail the required ISO/year format. Other supported wording variants fail the exact matcher without necessarily violating the requested concise-scalar format. These post-hoc findings do not replace the original deterministic metric.

In S2, the £2,050 versus £2,010 mismatch reflects two distinct stages: the prose memory omitted the exact unit estimate, and the answerer substituted the retained budget ceiling. The two unknown contractor-date scalars arise at the answer stage: memory and prose retain 19 February, separately from unknown repair completion.

In the reviewed S3 groups, fuller unit identifiers retain the decisive 12 versus 12B distinction and add the correct street address. Not booked and unbooked express the same booking status; where present, the extra unpaid qualification is supported by the visible source. S3-r2-T2-full additionally omits 15:00 from its refund-deadline scalar even though its prose and visible source include the time; this is a minor answer-level scalar omission, not an equivalent complete cutoff. These findings address only the selected scalar fields, not the overall adequacy of the payment or tenancy advice.

E1 adds four supported successful/completed rollback aliases and three missing baseline totals. The long lexical answer ignores 46/48 explicitly present in its visible summary. The short summary and short lexical answers lack that total in their actual evidence, so their unknown outputs are justified; the original ledger still knows 46. The short lexical selection omits that ledger. Missing source information and honest answerer uncertainty remain separate from answerer error.

Completed retrieval coverage: E1 — 12 answers, 72 scalar fields, 7 failed checks; E2 — 12 answers, 72 scalar fields, 1 failed checks; E3 — 12 answers, 72 scalar fields, 14 failed checks. Zero failed checks means no mismatch rows to append; passing fields are not semantically re-adjudicated.

E2 has one missing dispatch_enabled scalar in the short summary arm. The original flag is false; its literal key/value is omitted from the visible summary, which still preserves preview-only execution and no dispatch. Unknown is not equivalent to false, but withholding an unquoted configuration flag can be defensible; the row distinguishes that narrow field loss from losing the operational boundary or claiming that dispatch occurred.

Both E3 lengths use false/no as supported aliases for a full body absent from the reviewed archive. The short summary-only arm omits the explicit reported counts (18 rendered pages, one retained preview page), while preserving the cover-only preview and expired body. Those missing count outputs differ from the actual table revision, which is unknown in the original packet itself; the requested/displayed R7 label never establishes the consumed revision. Reported page counts also do not mean the table body was inspected.

Final coverage is complete: 108 answers, 648 scalar fields, 549 original passes and 99 original failures. Every failure has exactly one review row; there are no duplicate answer_id + key pairs, omitted failures, or extra review rows. Of these 99 selected failures, 89 express a supported equivalent value and 10 do not. All original deterministic labels remain unchanged.

| Answer ID | Key | Expected | Got | Classification | Equivalent | Severity |
|---|---|---|---|---|---|---|
| E1-long-adaptive | rollback_exercise_status | completed | successful | exact_format_or_wording_equivalent | yes | none |
| E1-long-lexical | baseline_accepted_runs | 46 | unknown | missing_or_unknown_information | no | minor |
| E1-long-summary | rollback_exercise_status | completed | successful | exact_format_or_wording_equivalent | yes | none |
| E1-short-adaptive | rollback_exercise_status | completed | successful | exact_format_or_wording_equivalent | yes | none |
| E1-short-lexical | baseline_accepted_runs | 46 | unknown | missing_or_unknown_information | no | minor |
| E1-short-summary | baseline_accepted_runs | 46 | unknown | missing_or_unknown_information | no | minor |
| E1-short-summary | rollback_exercise_status | completed | successful | exact_format_or_wording_equivalent | yes | none |
| E2-short-summary | dispatch_enabled | false | unknown | missing_or_unknown_information | no | minor |
| E3-long-adaptive | full_output_body_in_reviewed_archive | absent | no | exact_format_or_wording_equivalent | yes | none |
| E3-long-full | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-long-lexical | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-long-oracle | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-long-raw_full | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-long-summary | full_output_body_in_reviewed_archive | absent | no | exact_format_or_wording_equivalent | yes | none |
| E3-short-adaptive | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-short-full | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-short-lexical | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-short-oracle | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-short-raw_full | full_output_body_in_reviewed_archive | absent | false | exact_format_or_wording_equivalent | yes | none |
| E3-short-summary | rendered_page_count | 18 | unknown | missing_or_unknown_information | no | minor |
| E3-short-summary | retained_preview_page_count | 1 | unknown | missing_or_unknown_information | no | minor |
| E3-short-summary | full_output_body_in_reviewed_archive | absent | no | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T1-full | current_documented_lift_status | out of service | out_of_service | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T1-prose | current_documented_lift_status | out of service | out of service on 2027-01-11 | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T1-state_neither | provisional_contractor_date | 2027-02-19 | 19 February | context_resolvable_abbreviated_date | yes | none |
| S2-r1-T1-state_no_sources | provisional_contractor_date | 2027-02-19 | 19 February | context_resolvable_abbreviated_date | yes | none |
| S2-r1-T1-state_no_updates | provisional_contractor_date | 2027-02-19 | 19 February | context_resolvable_abbreviated_date | yes | none |
| S2-r1-T2-prose | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T2-state_neither | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T2-state_no_sources | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r1-T2-state_no_updates | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T1-prose | flat10_estimated_all_in_gbp | 2010 | 2050 | actual_wrong_value | no | major |
| S2-r2-T1-state | current_documented_lift_status | out of service | out of service following door fault | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T1-state | provisional_contractor_date | 2027-02-19 | unknown | missing_or_unknown_information | no | minor |
| S2-r2-T1-state_neither | current_documented_lift_status | out of service | out of service following door fault | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T1-state_no_sources | current_documented_lift_status | out of service | out of service following door fault | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T1-state_no_sources | provisional_contractor_date | 2027-02-19 | unknown | missing_or_unknown_information | no | minor |
| S2-r2-T1-state_no_updates | current_documented_lift_status | out of service | out of service following door fault | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T2-full | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T2-prose | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T2-state | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T2-state_neither | current_documented_lift_status | operational | operating | exact_format_or_wording_equivalent | yes | none |
| S2-r2-T2-state_no_updates | current_documented_lift_status | operational | repaired and returned to operation | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-full | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-full | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-full | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-prose | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_neither | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_neither | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_neither | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_sources | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_sources | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_sources | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_updates | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_updates | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T1-state_no_updates | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-full | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-full | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-prose | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_neither | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_neither | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_no_sources | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_no_sources | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_no_updates | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r1-T2-state_no_updates | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-full | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-full | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-full | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-prose | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-prose | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_neither | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_neither | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_neither | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_sources | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_sources | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_sources | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_updates | target_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_updates | supplied_certificate_flat | Flat 12 | Flat 12, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T1-state_no_updates | threadleaf_booking_status | unbooked | not booked or paid | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-full | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-full | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-full | threadleaf_refund_deadline | 2027-03-03 15:00 | 2027-03-03 | missing_or_unknown_information | no | minor |
| S3-r2-T2-prose | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_neither | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_neither | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_no_sources | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_no_sources | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_no_updates | current_certificate_flat | Flat 12B | Flat 12B, 52 Foxbarrel Reach | exact_format_or_wording_equivalent | yes | none |
| S3-r2-T2-state_no_updates | threadleaf_booking_status | unbooked | not booked | exact_format_or_wording_equivalent | yes | none |

## Per-field evidence

### E1-long-adaptive · rollback_exercise_status

**Expected:** `completed` · **Got:** `successful` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Successful denotes a completed successful rollback in this packet. The source explicitly says the exercise completed, restored Larch, and accepted both smoke scenarios; the visible summary likewise records an exercised rollback with successful smoke results. This is not merely a planned or required rollback. The scalar uses a supported outcome word instead of the expected lifecycle word, without claiming an additional full 48-case rerun. This same-value judgment is context-specific: completed alone would not generally imply successful without these outcome records.

**Original source anchors:**

- `E1-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/long/documents/0/text`: “Rollback exercise: completed, Larch restored and two fixed smoke scenarios accepted.”
- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/long/documents/1/text`: “ROLLBACK EXERCISE, after comparison
18:40 set nightly_default=Larch; reload configuration accepted.
18:41 execute fixed smoke hb-001: accepted=true.
18:42 execute fixed smoke hb-040: accepted=true.
18:43 read effective configuration: nightly_default=Larch.”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 is a fictional, pending request to change only the existing nightly harbor-48 revision 2 sandbox replay job’s local default parser from Larch to Cobalt. It explicitly excludes production traffic, production parser settings, endpoints, credentials, corpus changes, schedules, and broader deployment. The fixed acceptance gate requires 48/48 accepted candidate scenarios, zero wrong-record updates, zero non-sandbox writes, enabled endpoint restriction, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt accepted all 48 scenarios, with zero wrong-record updates, non-sandbox writes, and runner exceptions. Larch accepted 46/48, failing two repeated-delivery cases by producing duplicate acknowledgements; Cobalt reused the stored acknowledgement in the illustrated cases. Both builds used the same frozen inputs, runner, expected records, and restrictions. The destination audit reports writes only to sandbox-store/harbor-48. Rollback was exercised: Larch was restored, two smoke scenarios passed, and runner readback showed Larch.

Cobalt remains installed but unselected; Larch is still the scheduled default and no HBR-14 execution is recorded. Evidence covers one authored comparison run, not production behavior, population reliability, or untested workloads.

**Relevant answer prose:**

> 建議核准此受限變更：紀錄顯示 Cobalt 在同一凍結輸入、runner 與限制下達成 48/48，且未見錯誤更新或非沙箱寫入；回復 Larch 亦已在相同 runner 演練並讀回確認。核准範圍應嚴限既有 harbor-48 nightly sandbox replay 的本地預設，不延伸至生產或其他工作負載。這只支持一次作者設計的比較，不能推論廣泛可靠性。執行前後應核對排程仍僅指向該沙箱 job、端點限制啟用，並留存 readback 與寫入目的地稽核。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-long-lexical · baseline_accepted_runs

**Expected:** `46` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The original ledger records 46 accepted Larch runs, and the actual visible summary explicitly says Larch accepted 46/48. D02 is absent from the lexical documents, but the answerer was supplied the correct count in its summary and may report it as summary evidence. Calling the scalar unknown therefore loses an available fact; it is an answer-level omission, not generator loss or a truly unknown source value. The limitation about lacking the raw ledger can remain valid without discarding what the supplied summary reports. Minor severity is specific to the missing requested baseline count; it does not independently overturn the candidate acceptance gate.

**Original source anchors:**

- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/long/documents/1/text`: “category, scenarios, Larch_accepted, Cobalt_accepted
ordinary acknowledgements, 20, 20, 20
repeated delivery identifiers, 12, 10, 12
out-of-order acknowledgements, 8, 8, 8
empty optional metadata, 8, 8, 8
total, 48, 46, 48”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 is a fictional, pending request to change only the existing nightly harbor-48 revision 2 sandbox replay job’s local default parser from Larch to Cobalt. It explicitly excludes production traffic, production parser settings, endpoints, credentials, corpus changes, schedules, and broader deployment. The fixed acceptance gate requires 48/48 accepted candidate scenarios, zero wrong-record updates, zero non-sandbox writes, enabled endpoint restriction, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt accepted all 48 scenarios, with zero wrong-record updates, non-sandbox writes, and runner exceptions. Larch accepted 46/48, failing two repeated-delivery cases by producing duplicate acknowledgements; Cobalt reused the stored acknowledgement in the illustrated cases. Both builds used the same frozen inputs, runner, expected records, and restrictions. The destination audit reports writes only to sandbox-store/harbor-48. Rollback was exercised: Larch was restored, two smoke scenarios passed, and runner readback showed Larch.

Cobalt remains installed but unselected; Larch is still the scheduled default and no HBR-14 execution is recorded. Evidence covers one authored comparison run, not production behavior, population reliability, or untested workloads.

**Relevant answer prose:**

> 應核准，但僅核准 HBR-14 所界定的既有 harbor-48 rev.2 夜間沙箱工作之本地預設改為 Cobalt，且不得視為部署或生產背書。固定門檻已有候選 48/48、錯記錄與非沙箱寫入皆為 0，端點限制持續啟用，並已在同一 runner 回復 Larch。實務上仍應由操作員在執行後讀回有效 parser，於下一次夜跑記錄計數與目的地稽核；目前仍是 Larch、請求未執行。Cobalt 的證據只涵蓋單一作者化回放包，不能推論未測工作負載或生產可靠性。

Attribution: `answer_scalar_omission_despite_visible_summary`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-long-summary · rollback_exercise_status

**Expected:** `completed` · **Got:** `successful` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Successful denotes a completed successful rollback in this packet. The source explicitly says the exercise completed, restored Larch, and accepted both smoke scenarios; the visible summary likewise records an exercised rollback with successful smoke results. This is not merely a planned or required rollback. The scalar uses a supported outcome word instead of the expected lifecycle word, without claiming an additional full 48-case rerun. This same-value judgment is context-specific: completed alone would not generally imply successful without these outcome records.

**Original source anchors:**

- `E1-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/long/documents/0/text`: “Rollback exercise: completed, Larch restored and two fixed smoke scenarios accepted.”
- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/long/documents/1/text`: “ROLLBACK EXERCISE, after comparison
18:40 set nightly_default=Larch; reload configuration accepted.
18:41 execute fixed smoke hb-001: accepted=true.
18:42 execute fixed smoke hb-040: accepted=true.
18:43 read effective configuration: nightly_default=Larch.”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 is a fictional, pending request to change only the existing nightly harbor-48 revision 2 sandbox replay job’s local default parser from Larch to Cobalt. It explicitly excludes production traffic, production parser settings, endpoints, credentials, corpus changes, schedules, and broader deployment. The fixed acceptance gate requires 48/48 accepted candidate scenarios, zero wrong-record updates, zero non-sandbox writes, enabled endpoint restriction, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt accepted all 48 scenarios, with zero wrong-record updates, non-sandbox writes, and runner exceptions. Larch accepted 46/48, failing two repeated-delivery cases by producing duplicate acknowledgements; Cobalt reused the stored acknowledgement in the illustrated cases. Both builds used the same frozen inputs, runner, expected records, and restrictions. The destination audit reports writes only to sandbox-store/harbor-48. Rollback was exercised: Larch was restored, two smoke scenarios passed, and runner readback showed Larch.

Cobalt remains installed but unselected; Larch is still the scheduled default and no HBR-14 execution is recorded. Evidence covers one authored comparison run, not production behavior, population reliability, or untested workloads.

**Relevant answer prose:**

> 建議有條件核准 HBR-14 的狹義變更：僅把既有 harbor-48 夜間沙箱重播工作在其既定門檻下改選 Cobalt，勿延伸為生產或其他工作負載的核准。候選在同一凍結輸入、runner、預期紀錄與限制下達成48/48，且未見錯誤紀錄更新或非沙箱寫入；基線僅46/48，重複投遞會產生重複確認。回復亦已在同一runner演練成功。惟這只是一次作者設定的比較，不能推論生產可靠性。執行前應確認排程目標仍限定harbor-48沙箱，執行後讀回所選parser及目的地稽核結果。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-short-adaptive · rollback_exercise_status

**Expected:** `completed` · **Got:** `successful` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Successful denotes a completed successful rollback in this packet. The source explicitly says the exercise completed, restored Larch, and accepted both smoke scenarios; the visible summary likewise records an exercised rollback with successful smoke results. This is not merely a planned or required rollback. The scalar uses a supported outcome word instead of the expected lifecycle word, without claiming an additional full 48-case rerun. This same-value judgment is context-specific: completed alone would not generally imply successful without these outcome records.

**Original source anchors:**

- `E1-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/0/text`: “Rollback exercise: completed, Larch restored and two fixed smoke scenarios accepted.”
- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/1/text`: “ROLLBACK EXERCISE, after comparison
18:40 set nightly_default=Larch; reload configuration accepted.
18:41 execute fixed smoke hb-001: accepted=true.
18:42 execute fixed smoke hb-040: accepted=true.
18:43 read effective configuration: nightly_default=Larch.”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 requests making Cobalt the default parser only for the existing nightly harbor-48 sandbox replay job; it explicitly excludes production traffic, production parser changes, and endpoint changes. The fixed acceptance bundle is harbor-48 revision 2 with 48 scenarios. Required gates are 48/48 accepted runs, zero wrong-record updates, zero non-sandbox writes, endpoint restriction enabled, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt met these conditions in one comparison run: 48/48 accepted, zero wrong-record updates, zero non-sandbox writes, and no runner exceptions. It improved repeated-delivery cases from Larch’s 10/12 to 12/12; Larch duplicated acknowledgements in hb-023 and hb-027. Destination audit reports writes only to the single sandbox store. Rollback set the default to Larch and two smoke scenarios were accepted.

Cobalt remains an available candidate and Larch remains scheduled pending decision. Evidence concerns frozen authored fixtures and one run, not production behavior, broader reliability, or external validity.
- `/available_evidence/documents/0/text`: Rollback exercise: completed, Larch restored and two fixed smoke scenarios accepted.

**Relevant answer prose:**

> 建議核准 HBR-14 的受限變更：僅將既有 harbor-48 夜間沙箱重播工作預設改為 Cobalt，且僅在已記錄的 acceptance gate 下執行。固定 48 情境的單次比較中，Cobalt 48/48 通過、未誤更新紀錄、未寫入非沙箱目的地；端點限制持續啟用，且同一 runner 已成功回復 Larch 並通過兩個 smoke 情境。這也修正了 Larch 在重複投遞類別的兩個失敗。核准不代表生產或廣泛可靠性結論：證據僅涵蓋凍結的虛構 fixtures 與一次執行。下一步應在實際切換前重新確認有效設定仍限該沙箱工作與單一允許目的地，並保留可在下一夜間執行前切回 Larch 的操作紀錄；本答覆不執行部署。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-short-lexical · baseline_accepted_runs

**Expected:** `46` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The complete source ledger knows the Larch total (46), but the generated short summary omits it and retains only 10/12 in repeated-delivery cases. That category result and the two named duplicate-acknowledgement failures do not establish accepted counts in every other category. The lexical arm additionally supplies D01 and D03, which describe the candidate gate and corpus composition without reporting the overall baseline accepted count; the required ledger D02 is not supplied. Thus unknown is honest for the answerer’s actual evidence, while still failing the end-to-end requested source-fact recovery check. This is upstream information loss, not a true-source unknown and not a fabricated or incorrect answer value. The omission is minor for this scalar: it loses the exact baseline comparison count without itself disproving the candidate acceptance gate.

**Original source anchors:**

- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/1/text`: “category, scenarios, Larch_accepted, Cobalt_accepted
ordinary acknowledgements, 20, 20, 20
repeated delivery identifiers, 12, 10, 12
out-of-order acknowledgements, 8, 8, 8
empty optional metadata, 8, 8, 8
total, 48, 46, 48”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 requests making Cobalt the default parser only for the existing nightly harbor-48 sandbox replay job; it explicitly excludes production traffic, production parser changes, and endpoint changes. The fixed acceptance bundle is harbor-48 revision 2 with 48 scenarios. Required gates are 48/48 accepted runs, zero wrong-record updates, zero non-sandbox writes, endpoint restriction enabled, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt met these conditions in one comparison run: 48/48 accepted, zero wrong-record updates, zero non-sandbox writes, and no runner exceptions. It improved repeated-delivery cases from Larch’s 10/12 to 12/12; Larch duplicated acknowledgements in hb-023 and hb-027. Destination audit reports writes only to the single sandbox store. Rollback set the default to Larch and two smoke scenarios were accepted.

Cobalt remains an available candidate and Larch remains scheduled pending decision. Evidence concerns frozen authored fixtures and one run, not production behavior, broader reliability, or external validity.
- `/available_evidence/documents/0/text`: Candidate accepted runs: 48/48.
- `/available_evidence/documents/1/text`: Corpus manifest records 20 ordinary acknowledgement cases, 12 repeated-delivery cases, 8 out-of-order cases and 8 cases with empty optional metadata.

**Relevant answer prose:**

> 建議核准 HBR-14 的受限變更：僅將既有 harbor-48 夜間沙箱重播工作的預設解析器改為 Cobalt，且須維持既定驗收門檻。候選者在固定 48 情境的一次比較中已達 48/48、零錯誤紀錄更新與零非沙箱寫入，並已在同一 runner 完成回復 Larch 的演練；重複投遞情境亦較 Larch 改善。此結論不支持任何生產流量或廣泛可靠性的宣稱，因證據僅涵蓋凍結的虛構 fixtures 與一次執行。實施前應記錄核准範圍，並在下一次夜跑後確認端點限制仍啟用、輸出僅在沙箱封存，異常時依既測回復路徑切回 Larch。

Attribution: `generator_omission_and_retrieval_evidence_gap`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-short-summary · baseline_accepted_runs

**Expected:** `46` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The complete source ledger knows the Larch total (46), but the generated short summary omits it and retains only 10/12 in repeated-delivery cases. That category result and the two named duplicate-acknowledgement failures do not establish accepted counts in every other category. The summary arm supplies no original documents. Thus unknown is honest for the answerer’s actual evidence, while still failing the end-to-end requested source-fact recovery check. This is upstream information loss, not a true-source unknown and not a fabricated or incorrect answer value. The omission is minor for this scalar: it loses the exact baseline comparison count without itself disproving the candidate acceptance gate.

**Original source anchors:**

- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/1/text`: “category, scenarios, Larch_accepted, Cobalt_accepted
ordinary acknowledgements, 20, 20, 20
repeated delivery identifiers, 12, 10, 12
out-of-order acknowledgements, 8, 8, 8
empty optional metadata, 8, 8, 8
total, 48, 46, 48”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 requests making Cobalt the default parser only for the existing nightly harbor-48 sandbox replay job; it explicitly excludes production traffic, production parser changes, and endpoint changes. The fixed acceptance bundle is harbor-48 revision 2 with 48 scenarios. Required gates are 48/48 accepted runs, zero wrong-record updates, zero non-sandbox writes, endpoint restriction enabled, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt met these conditions in one comparison run: 48/48 accepted, zero wrong-record updates, zero non-sandbox writes, and no runner exceptions. It improved repeated-delivery cases from Larch’s 10/12 to 12/12; Larch duplicated acknowledgements in hb-023 and hb-027. Destination audit reports writes only to the single sandbox store. Rollback set the default to Larch and two smoke scenarios were accepted.

Cobalt remains an available candidate and Larch remains scheduled pending decision. Evidence concerns frozen authored fixtures and one run, not production behavior, broader reliability, or external validity.

**Relevant answer prose:**

> 建議有條件核准：僅把既有 harbor-48 夜間 sandbox replay 的預設解析器改為 Cobalt，且必須沿用已記錄的 acceptance gate；不得推論為生產或其他端點的核准。其一輪固定 fixture 比較已達 48/48、零錯誤更新及零非 sandbox 寫入，並在重複投遞案例優於 Larch；rollback 亦已在同一 runner 冒煙成功。風險是證據只涵蓋凍結的作者測資與單次執行。下次夜間執行後，應核對 48/48 gate、目的地寫入仍限單一 sandbox store，若失敗即依既定路徑回復 Larch。

Attribution: `generator_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E1-short-summary · rollback_exercise_status

**Expected:** `completed` · **Got:** `successful` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Successful denotes a completed successful rollback in this packet. The source explicitly says the exercise completed, restored Larch, and accepted both smoke scenarios; the visible summary likewise records an exercised rollback with successful smoke results. This is not merely a planned or required rollback. The scalar uses a supported outcome word instead of the expected lifecycle word, without claiming an additional full 48-case rerun. This same-value judgment is context-specific: completed alone would not generally imply successful without these outcome records.

**Original source anchors:**

- `E1-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/0/text`: “Rollback exercise: completed, Larch restored and two fixed smoke scenarios accepted.”
- `E1-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/0/variants/short/documents/1/text`: “ROLLBACK EXERCISE, after comparison
18:40 set nightly_default=Larch; reload configuration accepted.
18:41 execute fixed smoke hb-001: accepted=true.
18:42 execute fixed smoke hb-040: accepted=true.
18:43 read effective configuration: nightly_default=Larch.”

**Actual visible evidence:**

- `/available_evidence/summary`: HBR-14 requests making Cobalt the default parser only for the existing nightly harbor-48 sandbox replay job; it explicitly excludes production traffic, production parser changes, and endpoint changes. The fixed acceptance bundle is harbor-48 revision 2 with 48 scenarios. Required gates are 48/48 accepted runs, zero wrong-record updates, zero non-sandbox writes, endpoint restriction enabled, and a successful rollback to Larch in the same runner configuration.

The supplied ledger reports Cobalt met these conditions in one comparison run: 48/48 accepted, zero wrong-record updates, zero non-sandbox writes, and no runner exceptions. It improved repeated-delivery cases from Larch’s 10/12 to 12/12; Larch duplicated acknowledgements in hb-023 and hb-027. Destination audit reports writes only to the single sandbox store. Rollback set the default to Larch and two smoke scenarios were accepted.

Cobalt remains an available candidate and Larch remains scheduled pending decision. Evidence concerns frozen authored fixtures and one run, not production behavior, broader reliability, or external validity.

**Relevant answer prose:**

> 建議有條件核准：僅把既有 harbor-48 夜間 sandbox replay 的預設解析器改為 Cobalt，且必須沿用已記錄的 acceptance gate；不得推論為生產或其他端點的核准。其一輪固定 fixture 比較已達 48/48、零錯誤更新及零非 sandbox 寫入，並在重複投遞案例優於 Larch；rollback 亦已在同一 runner 冒煙成功。風險是證據只涵蓋凍結的作者測資與單次執行。下次夜間執行後，應核對 48/48 gate、目的地寫入仍限單一 sandbox store，若失敗即依既定路徑回復 Larch。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E2-short-summary · dispatch_enabled

**Expected:** `false` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The original source explicitly records dispatch_enabled=false. The summary-only arm supplies no documents and drops that literal configuration key/value, while retaining that the benchmark was preview-only and no dispatch or inventory mutation occurred. Thus the source is not unknown and the execution boundary is still known; only the exact flag/readback is absent. An unknown scalar does not equal the source’s false value. On a literal configuration-field reading, withholding an unquoted flag is defensible: no dispatch event by itself does not prove which configuration mechanism prevented it. On a looser operational reading the supplied preview-only boundary already communicates disabled execution. This review therefore attributes the failed exact field to summary loss of the explicit flag, records the preserved semantic boundary, and does not classify the answer as fabricated or as claiming real dispatch. Minor severity is specific to this field; the answer retains the blocking identifier mismatch and does not authorize or perform dispatch.

**Original source anchors:**

- `E2-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/1/variants/short/documents/0/text`: “Evaluation mode: route preview only. dispatch_enabled=false.”
- `E2-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/1/variants/short/documents/1/text`: “All traces end after preview output. dispatch_enabled=false in both parser invocations.”

**Actual visible evidence:**

- `/available_evidence/summary`: The fictional MFT-31 request seeks to make Birch the default parser for a future warehouse-demo batch; it remains unexecuted, with Cedar still default. In a 60-scenario preview-only benchmark using frozen references, Cedar matched all 60 target identifiers and Birch matched 58, while Birch’s median duration was 91 ms versus Cedar’s 145 ms. The two Birch mismatches, MF-059 and MF-060, converted significant leading-zero suffixes (A-007 to A-7; B-004 to B-4), selecting separate existing manifest entries and different slots. The stated identifier contract treats identifiers as opaque strings, permits only surrounding-whitespace trimming, and defines any reference mismatch as blocking irrespective of timing. Both parsers used identical source rows, reference matching, destination adapter, and serializer; traces attribute Birch’s results to numeric-suffix canonicalisation. The small authored fixture pack includes only two leading-zero cases and does not indicate their real-world frequency. No dispatch, inventory mutation, corrected Birch build, post-fix benchmark, deployment, or rollback occurred.

**Relevant answer prose:**

> 不應將 Birch 提升為明日批次的自動路由。身份契約把任何 reference mismatch 視為阻擋條件，Birch 雖較快，仍僅 58/60 正確，且錯誤會導向既有但不同的 manifest 與槽位，屬錯目標而非可忽略失敗。觀察到的機制是數字尾碼正規化移除前導零；但現有小型 fixture 只有兩例，無法推論實際頻率或修復後風險。維持 Cedar 預設；先修正 Birch 使識別碼保持 opaque string，並以凍結參考資料重跑涵蓋前導零與回歸案例的 benchmark，確認零 mismatch 後再評估。

Attribution: `generator_exact_flag_omission_with_operational_boundary_retained`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-adaptive · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `no` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed 18-page internal equipment-handover export on 25 August 2026. Its signed request and retained first-page preview display “Catalog R7,” but this label was copied to the cover and was separate from the table-data binding. The schema-4 record did not capture the resolved table catalog revision, row snapshot, pointer target, cache identity, or row-level validation; its value is explicitly not recorded. Both R6 and R7 were schema-compatible source files, and the normal input path could use a mutable `/catalog/current` pointer or a worker cache. A maintenance record shows the pointer at R7 on 26 August, after H17, but no start-time history exists. The PDF body expired on 1 September under seven-day retention; only metadata, receipt, and cover preview remain. The digest, page count, completion status, and archive acceptance identify a produced artifact but do not establish its table rows or revision. No recovered copy, content inspection, completed review, or binding evidence is supplied. Build-record request BR-H17 remains pending; other copies may or may not exist outside the reviewed archive.

**Relevant answer prose:**

> 不能認證 H17 的設備表全程採用核准的 R7。可支持的僅是已完成的 18 頁產物，以及簽署申請與首頁預覽顯示「Catalog R7」；該標籤與表格資料綁定分離，屬請求／展示值，非觀察到的表格內容。記錄亦明示未保存實際解析版本、列快照或列級驗證；完整 PDF 已依保留期過期。26 日指標為 R7 只能形成事後假設，不能倒推 25 日執行時狀態。下一步應查待處理的 BR-H17 建置紀錄或其他未納入本歸檔審查的副本；即使找到後續指標紀錄，因缺乏起始時間歷史，仍無法單獨證明當時表格綁定。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-full · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed 18-page internal equipment-handover export on 25 August 2026. Its signed request and retained first-page preview display “Catalog R7,” but this label was copied to the cover and was separate from the table-data binding. The schema-4 record did not capture the resolved table catalog revision, row snapshot, pointer target, cache identity, or row-level validation; its value is explicitly not recorded. Both R6 and R7 were schema-compatible source files, and the normal input path could use a mutable `/catalog/current` pointer or a worker cache. A maintenance record shows the pointer at R7 on 26 August, after H17, but no start-time history exists. The PDF body expired on 1 September under seven-day retention; only metadata, receipt, and cover preview remain. The digest, page count, completion status, and archive acceptance identify a produced artifact but do not establish its table rows or revision. No recovered copy, content inspection, completed review, or binding evidence is supplied. Build-record request BR-H17 remains pending; other copies may or may not exist outside the reviewed archive.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。已支持的是 H17 完成、18頁，且請求與封面顯示 R7；這是被複製的展示／請求值，不等於設備表實際綁定。實際 revision 明列未記錄，封面無表列，PDF 正文已過期；R6、R7皆相容且可能經 mutable pointer 或快取讀取。摘要、頁數、收據與 digest 只能識別已產出檔案，不能證明各表皆為 R7。應暫緩該句，改稱「請求及封面標示 R7」；追查待處理 BR-H17 及任何獨立原始副本，若取得須比對表列／不可變綁定與原 digest。但事後資料未必存在，且新匯出不能證明 H17 歷史內容。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-lexical · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed 18-page internal equipment-handover export on 25 August 2026. Its signed request and retained first-page preview display “Catalog R7,” but this label was copied to the cover and was separate from the table-data binding. The schema-4 record did not capture the resolved table catalog revision, row snapshot, pointer target, cache identity, or row-level validation; its value is explicitly not recorded. Both R6 and R7 were schema-compatible source files, and the normal input path could use a mutable `/catalog/current` pointer or a worker cache. A maintenance record shows the pointer at R7 on 26 August, after H17, but no start-time history exists. The PDF body expired on 1 September under seven-day retention; only metadata, receipt, and cover preview remain. The digest, page count, completion status, and archive acceptance identify a produced artifact but do not establish its table rows or revision. No recovered copy, content inspection, completed review, or binding evidence is supplied. Build-record request BR-H17 remains pending; other copies may or may not exist outside the reviewed archive.
- `/available_evidence/documents/0/text`: output_body_retained=false

**Relevant answer prose:**

> 不能認證。H17已完成且產生18頁檔案，但「Catalog R7」僅是由簽署申請複製到封面，並非設備表格的實際資料綁定。已保存的預覽只有第1頁且沒有表格列；完整PDF已依保留政策到期，封包亦無列級驗證或已解析修訂值。因此可報告「申請／封面顯示R7」，不可稱其設備表全程使用R7。下一步應追查仍可能存在的獨立PDF或BR-H17所要求的當時有效設定與綁定中繼資料，再以檔案雜湊識別副本並逐列比對；但即使取得事後指標狀態，也不能單獨回推H17啟動時的資料來源。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-oracle · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed 18-page internal equipment-handover export on 25 August 2026. Its signed request and retained first-page preview display “Catalog R7,” but this label was copied to the cover and was separate from the table-data binding. The schema-4 record did not capture the resolved table catalog revision, row snapshot, pointer target, cache identity, or row-level validation; its value is explicitly not recorded. Both R6 and R7 were schema-compatible source files, and the normal input path could use a mutable `/catalog/current` pointer or a worker cache. A maintenance record shows the pointer at R7 on 26 August, after H17, but no start-time history exists. The PDF body expired on 1 September under seven-day retention; only metadata, receipt, and cover preview remain. The digest, page count, completion status, and archive acceptance identify a produced artifact but do not establish its table rows or revision. No recovered copy, content inspection, completed review, or binding evidence is supplied. Build-record request BR-H17 remains pending; other copies may or may not exist outside the reviewed archive.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。H17 的已核准／顯示標籤是 R7，但它只證明請求與封面文字，不能推論設備表實際綁定的版本。工作完成、18 頁、收檔收據與摘要皆證明曾產出並收檔，非逐列驗證；PDF 本體已到期，封面預覽也沒有表格列。R6、R7 皆可被同一表格結構渲染，且起始時的指標／快取狀態未留存。建議暫停該句，待 BR-H17 回覆或查得具來源鏈的原始副本後，檢視表格及綁定資料；但該請求仍 pending，且現有封存無法保證其他副本存在。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-raw_full · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。H17已完成且申請與封面均顯示／要求R7，但這只證明請求標籤與封面展示，不等同設備表實際讀取R7。表格綁定版本明列未記錄，且封面沒有表列、完整PDF已過期；R6與R7又皆相容同一表格架構，故完成狀態、18頁與摘要均不能補足內容證據。應暫緩該句或改述為「申請及封面標示R7」。下一步可等待BR-H17查找當時有效設定或獨立綁定資料；即使取得，仍須核對其日期與來源，且不能由現今重跑或26日的指標觀測回推25日原始表格。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-long-summary · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `no` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/long/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed 18-page internal equipment-handover export on 25 August 2026. Its signed request and retained first-page preview display “Catalog R7,” but this label was copied to the cover and was separate from the table-data binding. The schema-4 record did not capture the resolved table catalog revision, row snapshot, pointer target, cache identity, or row-level validation; its value is explicitly not recorded. Both R6 and R7 were schema-compatible source files, and the normal input path could use a mutable `/catalog/current` pointer or a worker cache. A maintenance record shows the pointer at R7 on 26 August, after H17, but no start-time history exists. The PDF body expired on 1 September under seven-day retention; only metadata, receipt, and cover preview remain. The digest, page count, completion status, and archive acceptance identify a produced artifact but do not establish its table rows or revision. No recovered copy, content inspection, completed review, or binding evidence is supplied. Build-record request BR-H17 remains pending; other copies may or may not exist outside the reviewed archive.

**Relevant answer prose:**

> 不能認證 H17 的設備表全程使用核准 R7。可支持的僅是已完成的 18 頁產物，以及申請與保留首頁顯示「Catalog R7」；該標籤與表格資料綁定分離，不能推論實際列內容。紀錄明言未保存解析後版本、列快照、指標目標、快取身分或列級驗證；R6、R7又皆相容，且可經可變指標或快取輸入。應追查仍待處理的 BR-H17 建置紀錄或其他保存副本，檢視當時綁定／列快照；但已審查封存本體逾期，且無開工時點歷史，即使查到 26 日指標為 R7也不能倒推 25 日。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-adaptive · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。H17雖已完成，且簽署表單與僅存封面均顯示 R7，但這是請求／展示標籤，並非設備表格實際讀取的版本。封面沒有表格列，正文與表格輸入快照均未保存；R6、R7又都可成功渲染，故收據、頁數及摘要不能排除 R6、混用或快取來源。應等待 BR-H17 的部署／獨立綁定資料，並查詢是否有他方保存原始副本；即使取得較晚的指標紀錄，也不能回溯證明 H17 啟動時的綁定。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-full · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證該句。R7僅是簽署表單所選與封面顯示的請求標籤；其欄位會獨立複製，並不證明設備表列實際來源。H17雖已完成、18頁且獲歸檔接受，但這些只證明產出流程，非逐列內容。完整PDF、表格輸入快照與來源綁定皆未留存，且R6、R7均可成功渲染；8月26日指標為R7也晚於H17且無較早歷史。應維持「未解決」而非簽署該斷言。下一步是等待BR-H17的部署設定及任何獨立綁定中繼資料，並查明是否有其他持有者保存原件；即使找到今日指標後重跑，也只能產生新檔，不能還原原H17內容。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-lexical · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證該句。H17已完成且申請／封面顯示R7，但此為請求與展示標籤，未證明設備表實際綁定R7；R6、R7皆可成功渲染，且表身與輸入快照均未留存。收據、頁數及雜湊只證明產出和歸檔接受，不能證明逐表內容。下一步應等待BR-H17所尋的部署設定或獨立綁定中繼資料；即使取得，也須確認其時間點覆蓋2026-08-25，因8月26日的指標紀錄沒有較早歷史。若仍無原始時點證據，報告應改述為「申請及封面標示R7」，不可稱全表使用R7。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-oracle · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.
- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。H17雖完成且申請/封面均顯示R7，但該標示獨立複製至封面，非表格資料綁定；封面預覽亦沒有設備列。實際表格版本未記錄，且R6、R7皆可成功渲染，故不能由完成狀態、18頁、摘要或收據推定「全程R7」。應將提案改為「申請及保留封面標示R7；表格實際版本未能由現存證據確認」。下一步可等待BR-H17的部署設定或獨立綁定資料；但即使取得較晚的指標狀態，也不能回溯證明H17起始時的輸入，且不得重建輸出冒充原件。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-raw_full · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `false` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/documents/0/text`: output_body_retained=false
- `/available_evidence/documents/1/text`: handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.

**Relevant answer prose:**

> 不能認證。R7僅被請求並顯示於封面，並非設備表實際綁定版本；完成狀態與18頁輸出也不代表內容已核驗。封面沒有設備列，完整PDF及表格輸入快照均未留存，且R6、R7皆可通過相同表格綱要，故不能排除R6或快取來源。可等待BR-H17取得部署設定或獨立綁定中繼資料；但若仍無當時指標／快取或獨立原件，歷史內容無法由現存封面與收據證實。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-summary · rendered_page_count

**Expected:** `18` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The retained source job record reports 18 rendered pages. This is known metadata, not a claim that 18 pages of table content were inspected or verified against R7. The generated summary discusses page count only generically and omits 18; the answerer receives no documents. Unknown is therefore justified for the exact count from its visible evidence, but it still fails recovery of a known requested source field. The loss occurs in summary generation, not because the original page count is unknown. The answer correctly treats completion/count metadata as insufficient to certify actual table revision, a separate question.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “rendered_page_count=18”
- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “rendered_page_count counts output pages, not the number of pages checked against an approved catalog.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.

**Relevant answer prose:**

> 不能認證 H17 的設備表全程採用已核准的 R7。已留存的簽署申請與封面預覽只顯示「Catalog R7」，且該標籤會獨立複製到封面，不能證明表格列的實際來源；收據、完成狀態、頁數及摘要值亦僅證明產生與歸檔接受。表格解析版本、來源綁定與列級驗證均未保存，且 R6、R7 都可被轉譯器使用，故此句應改為「申請及封面標示 R7，實際表格版本未能由留存紀錄確認」。下一步可查當時獨立保存的建置紀錄、來源綁定清單或已簽核逐列審閱；但完整 PDF 已依保留期到期，且現有指標歷史只顯示 H17 之後的 R7，無法回溯補證。

Attribution: `generator_exact_count_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-summary · retained_preview_page_count

**Expected:** `1` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The original packet explicitly identifies page 1 and says no other page preview is retained, so the exact retained-page count is 1. The generated summary retains a cover-only preview but drops the page number and the explicit no-other-page statement. The singular preview description supplies useful partial evidence; it is not a direct archived page-count record. On a strict count-field reading, unknown avoids inventing an omitted number, while still losing a source-known scalar. This is summary loss of explicit count detail, not proof that no preview exists and not a true-source unknown. A retained cover-only image also does not verify the equipment tables.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “The retained cover preview shows page 1 of 18, headed Equipment Handover, with "Catalog R7" below the title. It contains no equipment-table rows. No other page preview is retained.”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “cover-page-1.png: present; cover banner only, no equipment rows.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.

**Relevant answer prose:**

> 不能認證 H17 的設備表全程採用已核准的 R7。已留存的簽署申請與封面預覽只顯示「Catalog R7」，且該標籤會獨立複製到封面，不能證明表格列的實際來源；收據、完成狀態、頁數及摘要值亦僅證明產生與歸檔接受。表格解析版本、來源綁定與列級驗證均未保存，且 R6、R7 都可被轉譯器使用，故此句應改為「申請及封面標示 R7，實際表格版本未能由留存紀錄確認」。下一步可查當時獨立保存的建置紀錄、來源綁定清單或已簽核逐列審閱；但完整 PDF 已依保留期到期，且現有指標歷史只顯示 H17 之後的 R7，無法回溯補證。

Attribution: `generator_exact_count_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### E3-short-summary · full_output_body_in_reviewed_archive

**Expected:** `absent` · **Got:** `no` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The field asks whether the complete H17 output body is in the reviewed archive. False/no expresses the same negative presence state as absent. D01 explicitly records output_body_retained=false and D02 says the PDF body expired and is not present in this archive; the summary, when supplied, likewise says only metadata, receipt and a cover preview remain. The answer does not turn a missing body into evidence that H17 never completed, nor claim that no independent copy could exist elsewhere. The alias changes representation, not the scoped archival fact.

**Original source anchors:**

- `E3-D01` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/0/text`: “output_body_retained=false”
- `E3-D02` at `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json#/cases/2/variants/short/documents/1/text`: “handover-H17.pdf: body expired under seven-day retention on 2026-09-01; not present in this archive.”

**Actual visible evidence:**

- `/available_evidence/summary`: H17 was a completed internal equipment-handover export started on 2026-08-25. Its signed request form and retained cover preview display “Catalog R7,” but that label is copied independently to the cover and does not establish which catalog supplied the equipment-table rows. The relevant schema did not record the resolved table catalog, source-binding manifest, table-input snapshot, cache state, or row-level validation. Both R6 and R7 were compatible with the renderer; R7 added a connector-inspection column. The normal configuration used a mutable `/catalog/current` pointer, while a worker could alternatively use a cached table file. A maintenance log shows the pointer at R7 on 2026-08-26, after H17, with no earlier history. The PDF body expired on 2026-09-01 under normal seven-day retention; only metadata, receipt, and a cover-only preview remain. The receipt, completion status, page count, and digest confirm generation and archive acceptance, not content or catalog binding. No independent copy, reconstruction, signed row-by-row review, or build-record result is supplied. The proposed claim that R7 was used throughout the tables is therefore unresolved by the retained evidence.

**Relevant answer prose:**

> 不能認證 H17 的設備表全程採用已核准的 R7。已留存的簽署申請與封面預覽只顯示「Catalog R7」，且該標籤會獨立複製到封面，不能證明表格列的實際來源；收據、完成狀態、頁數及摘要值亦僅證明產生與歸檔接受。表格解析版本、來源綁定與列級驗證均未保存，且 R6、R7 都可被轉譯器使用，故此句應改為「申請及封面標示 R7，實際表格版本未能由留存紀錄確認」。下一步可查當時獨立保存的建置紀錄、來源綁定清單或已簽核逐列審閱；但完整 PDF 已依保留期到期，且現有指標歷史只顯示 H17 之後的 R7，無法回溯補證。

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T1-full · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out_of_service` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Replacing spaces with underscores preserves the documented out-of-service state. The prose also explicitly states out of service; there is no substantive factual discrepancy in this field.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”

**Actual visible evidence:**

- `/available_evidence/history/4/text`: Dated messages: on 9 January the letting agent wrote, 'The lift is working; the upper flats are normally reached that way.' On 11 January the building manager issued notice CM-11: 'Only passenger lift out of service following door fault. Contractor visit provisionally 19 February. Completion date unknown. No alternative lift.' The notice concerns the same building, not a neighbouring block. On 12 January the agent sent a new email saying only, 'The advert is correct: a lift is included in this building.' That email does not mention operation, the fault, CM-11 or the appointment date. I have no engineer release or later operational report.

**Relevant answer prose:**

> Flat 2 has a measured 80 mm raised threshold, so it fails the zero-step requirement as documented. Flat 10 depends on the building’s only passenger lift; its current documented status is out of service, with a contractor visit only provisionally dated 19 February—after the move date—and completion unknown. Its pavement approach and flat threshold are also unmeasured. Flat 10’s estimate is £2,010 all-in per month.
> Use the earlier access-only visit with your normal aid to test and record one continuous pavement-to-flat route: approach, street door, hall, any doorway thresholds, and (for Flat 10) whether the lift is actually operating. Reserve the 16 January full viewing only for a flat that passes that route check, or use it to verify the remaining access points if neither can be checked earlier.
> The decision could change only with evidence of a genuinely zero-step independent route: for Flat 2, an installed and acceptable resolution of the 80 mm threshold; for Flat 10, the lift restored and operating by 15 February, plus a tested zero-step route and doorway threshold. Carrying or an unconfirmed later repair does not meet your requirement.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T1-prose · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out of service on 2027-01-11` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The scalar retains the exact out-of-service state and adds its notice date. The January year follows the same 2027 move timeline; prose treats this as the latest documented outage, without claiming a later repair. The added date causes exact-string failure but does not change the field’s factual state.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”
- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “On 11 January the building manager issued notice CM-11:”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory`: Fictional comparison: Flat 10 and Flat 2 at 38 Copperlark Court for a 15 February 2027 move. Requirements are £2,050/month all-in maximum, at least 42 m², a separate bedroom, no building-age limit, and at most 35 minutes to Snowglass Workshop; units must remain distinct. Both supplied packets state separate bedrooms, 15 February availability, and a shared 31-minute journey. Flat 10 is 48 m² and £2,010 estimated all-in; Flat 2 is 44 m² and £2,035 estimated all-in. Neither total is fixed. The building’s only passenger lift was reported working on 9 January but was out of service on 11 January, with a provisional 19 February contractor visit and unknown completion; no later operational report exists. Access remains uncertain: Flat 2 has an 80 mm threshold and no ramp plan; Flat 10’s threshold and pavement approach are unmeasured. One full viewing remains on 16 January; an earlier, manager-permitted access-only visit is possible, and the user will book it.

**Relevant answer prose:**

> Neither flat is currently evidenced to meet the final access requirement. Flat 2 is ruled out on the present packet: its 80 mm threshold, with no ramp plan, is not zero-step access. Flat 10 is not evidenced either: its pavement approach and threshold have not been measured, and the only passenger lift was last reported out of service on 11 January. The provisional contractor visit is 19 February, after your move date, with completion unknown.
> Use the manager-permitted access-only visit before the 16 January full viewing to test the entire route from pavement to Flat 10 using your normal mobility aid, independently: every entrance and door, any lip/threshold, lift operation and internal route. Get the lift’s confirmed operational status for 15 February (not merely a contractor appointment), and measure/photograph the pavement approach and all thresholds. Those checks could change Flat 10 from unproven to suitable; Flat 2 would need the threshold condition itself resolved.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T1-state_neither · provisional_contractor_date

**Expected:** `2027-02-19` · **Got:** `19 February` · **Original deterministic pass:** false.

**Verdict:** context_resolvable_abbreviated_date; semantic-equivalent=true; severity=none.

The visible memory retains the provisional visit as 19 February and explicitly retains the move date as 15 February 2027; the source describes one continuous January/February move timeline. In that context the abbreviated date resolves to 2027-02-19. The answer omits the required ISO/year formatting, so exact-format compliance still fails. Equality would not be justified from the isolated day/month string alone. The original visit source itself omits a printed year, so this is not evidence that the generator discarded an explicit visit year.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Contractor visit provisionally 19 February. Completion date unknown.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory/facts/2`: {"id": "F3", "key": "search.move_date", "value": "15 February 2027", "qualification": "confirmed_in_source"}
- `/available_evidence/memory/facts/29`: {"id": "F30", "key": "building.lift_contractor_visit_date", "value": "19 February", "qualification": "reported"}
- `/available_evidence/memory/facts/30`: {"id": "F31", "key": "building.lift_repair_completion_date", "value": "unknown", "qualification": "unknown"}

**Relevant answer prose:**

> Flat 2 is not suitable on the current packet: its entrance-floor position does not remove the documented 80 mm raised front-door threshold, and no ramp is installed or agreed. Flat 10 is also not evidenced: it is on the second floor and the only passenger lift is documented out of service, with no alternative lift or repair-completion date. The contractor visit is only provisional for 19 February, after your move date.
> Use the access-only visit (if the manager permits) before the 16 January full viewing to trace the exact pavement-to-door route with your normal aid: confirm the street entrance rather than the two-step courtyard route, measure any thresholds and doorway clearances, and for Flat 10 obtain written confirmation that the lift is working before 15 February—not merely that a contractor will attend. Also confirm no unrecorded steps, gates, or route changes between pavement and each flat. Do not rely on carrying or a later repair.

Attribution: `answer_date_format_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T1-state_no_sources · provisional_contractor_date

**Expected:** `2027-02-19` · **Got:** `19 February` · **Original deterministic pass:** false.

**Verdict:** context_resolvable_abbreviated_date; semantic-equivalent=true; severity=none.

The visible memory retains the provisional visit as 19 February and explicitly retains the move date as 15 February 2027; the source describes one continuous January/February move timeline. In that context the abbreviated date resolves to 2027-02-19. The answer omits the required ISO/year formatting, so exact-format compliance still fails. Equality would not be justified from the isolated day/month string alone. The original visit source itself omits a printed year, so this is not evidence that the generator discarded an explicit visit year.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Contractor visit provisionally 19 February. Completion date unknown.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory/facts/2`: {"id": "F3", "key": "search.move_date", "value": "15 February 2027", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/29`: {"id": "F30", "key": "building.lift_contractor_visit_date", "value": "19 February", "qualification": "reported", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/30`: {"id": "F31", "key": "building.lift_repair_completion_date", "value": "unknown", "qualification": "unknown", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Flat 10 is on the second floor and its only passenger lift is documented out of service. The contractor visit is only provisional for 19 February, after move-in, with no repair-completion date or alternative lift. Flat 2 is on the entrance floor, but its front-door threshold is measured at 80 mm, with no installed or agreed ramp. The continuous pavement-to-flat route is also not evidenced for either flat.

Attribution: `answer_date_format_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T1-state_no_updates · provisional_contractor_date

**Expected:** `2027-02-19` · **Got:** `19 February` · **Original deterministic pass:** false.

**Verdict:** context_resolvable_abbreviated_date; semantic-equivalent=true; severity=none.

The visible memory retains the provisional visit as 19 February and explicitly retains the move date as 15 February 2027; the source describes one continuous January/February move timeline. In that context the abbreviated date resolves to 2027-02-19. The answer omits the required ISO/year formatting, so exact-format compliance still fails. Equality would not be justified from the isolated day/month string alone. The original visit source itself omits a printed year, so this is not evidence that the generator discarded an explicit visit year.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Contractor visit provisionally 19 February. Completion date unknown.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory/facts/2`: {"id": "F3", "key": "search.move_date", "value": "15 February 2027", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "move on 15 February 2027"}
- `/available_evidence/memory/facts/29`: {"id": "F30", "key": "building.lift_contractor_visit_date", "value": "19 February", "qualification": "reported", "source_id": "U3", "quote": "provisionally 19 February"}
- `/available_evidence/memory/facts/30`: {"id": "F31", "key": "building.lift_repair_completion_date", "value": "unknown", "qualification": "unknown", "source_id": "U3", "quote": "Completion date unknown"}

**Relevant answer prose:**

> Flat 10 is not evidenced because its only passenger lift is documented out of service; 19 February is only a provisional contractor visit, with no completion or later operational confirmation. Flat 2 is not evidenced because its front-door threshold measures 80 mm, with no installed or agreed ramp; that is incompatible with zero steps.
> Move date: 15 February 2027. Permitted steps: 0. Lift status: documented out of service (conflicting earlier report said working). Provisional contractor date: 19 February. Flat 2 threshold: 80 mm. Flat 10 estimated all-in: £2,010/month.

Attribution: `answer_date_format_omission`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T2-prose · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route, even though the pre-question memory still describes the earlier outage. The answer uses the new operation evidence; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for a full viewing on the access evidence. CM-14 and your independent access-only visit now document the sole passenger lift as operating, released on 14 January 2027, and a zero-step route from pavement through Flat 10’s doorway using your usual aid. CM-11 is stale evidence and adds no newer inspection.
> This is access-route approval only: you did not inspect the rooms, so it is not approval of the flat overall or a guarantee that the lift will remain operational on the 15 February 2027 move date. Confirm room layout, internal circulation and the remaining viewing checks at the full viewing. Flat 2 remains unsuitable on the stated access requirement because its 80 mm threshold is unchanged. Flat 10’s estimated all-in cost remains £2,010. Do not book or pay.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T2-state_neither · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route, even though the pre-question memory still describes the earlier outage. The answer uses the new operation evidence; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Manual mode. Yes—approve Flat 10 for a full viewing on access grounds only. The signed release says the sole passenger lift was repaired and returned to operation on 14 January 2027; the later CM-11 forwarding adds no newer inspection. Your permitted access-only visit independently completed the pavement-to-Flat-10 doorway route with your usual aid and found zero steps or raised thresholds.
> This changes Flat 10 from an unverified access route to one directly observed as meeting your zero-step route requirement. The provisional 19 February appointment is cancelled, so it is no longer the relevant lift date. Flat 2 remains unsuitable on this point: its 80 mm threshold is unchanged.
> The approval is limited: you did not inspect Flat 10’s rooms, and the £2,010 all-in figure remains an estimate rather than a fixed cap. The lift is operating now, but no future reliability guarantee is supplied. Your required move date is 15 February 2027. Do not book or pay.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T2-state_no_sources · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route, even though the pre-question memory still describes the earlier outage. The answer uses the new operation evidence; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for the full viewing on the access evidence now available. The only passenger lift is documented as operating, released after the door-fault repair on 14 January 2027; the former 19 February appointment is cancelled. Your access-only visit then independently confirmed a continuous pavement-to-Flat-10 route using your usual aid, with 0 steps or raised thresholds, including the lift and flat doorway.
> The approval is limited to access for a full viewing; you did not inspect Flat 10’s rooms, and the lift is the building’s only passenger lift, so ongoing reliability is not established. The target move date is 15 February 2027 and Flat 10’s estimated all-in cost is £2,010. Do not book or pay through me, and do not sign or pay at the viewing.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r1-T2-state_no_updates · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route, even though the pre-question memory still describes the earlier outage. The answer uses the new operation evidence; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for the full viewing on the access evidence alone. CM-14’s signed engineer release records the only passenger lift as returned to operation on 14 January 2027, and your permitted access-only visit independently completed the pavement-to-Flat-10-doorway route with your usual aid and zero steps or raised thresholds. The provisional 19 February appointment is cancelled; the re-forwarded CM-11 is stale and adds no newer inspection.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-prose · flat10_estimated_all_in_gbp

**Expected:** `2010` · **Got:** `2050` · **Original deterministic pass:** false.

**Verdict:** actual_wrong_value; semantic-equivalent=false; severity=major.

The original unit packet gives Flat 10’s estimate as £2,010, while £2,050 is the user’s budget ceiling. The generated prose memory omits the exact Flat 10 amount, retains the £2,050 ceiling, and says only that the units meet the estimated all-in criterion. The latest question asks for the estimate without supplying it. Thus the generator loses the requested exact fact; the answer then substitutes the retained ceiling as an unsupported exact estimate in both prose and scalar. This is a real £40/month overstatement, not formatting. Returning unknown would have respected the answerer’s visible evidence. This is a requested cost-fact error; it does not by itself reverse the access decision.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/2/text`: “Its rent plus estimated utilities, broadband and tax provision total £2,010 a month.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “My ceiling is £2,050 per month all-in”

**Actual visible evidence:**

- `/available_evidence/memory`: The user is comparing Flat 10 and Flat 2 at 38 Copperlark Court for a fictional 15 February 2027 move and wants the units assessed separately. Requirements are a £2,050/month all-in ceiling, at least 42 m², a separate bedroom, no building-age limit, and a maximum 35-minute journey to Snowglass Workshop. Both supplied packets meet the stated area, bedroom, estimated all-in, availability, and shared 31-minute journey criteria; totals are estimates rather than capped bills. Flat 10 is second floor and was preferred for its higher view; Flat 2 is entrance floor. Lift evidence changed from working on 9 January to the building’s only passenger lift being out of service on 11 January, with a provisional 19 February contractor visit and no known completion; the later agent email does not establish operation. Access remains uncertain: Flat 2 has an 80 mm threshold and no ramp plan; route and Flat 10 threshold details are incomplete. One full viewing slot remains on 16 January; the user may arrange a manager-permitted access-only visit and will book personally.

**Relevant answer prose:**

> Key facts: move date 15 February 2027; permitted steps 0; current documented lift status: only passenger lift out of service (11 January); provisional contractor date: 19 February 2027; Flat 2 threshold: 80 mm; Flat 10 estimated all-in: £2,050/month (estimate). Do not book or pay at the viewing.

Attribution: `generator_omission_followed_by_answer_error`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out of service following door fault` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The added following-door-fault qualification is explicitly present in CM-11 and in the visible memory row. It preserves the expected out-of-service state. This is extra supported wording, not a wrong current-state value.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/25`: {"id": "F26", "key": "building.passenger_lift_operational_status", "value": "out of service following door fault", "qualification": "confirmed_in_source", "source_id": "U3", "quote": "Only passenger lift out of service following door fault", "status": "current", "supersedes": ["F25"]}

**Relevant answer prose:**

> Flat 10 relies on the only passenger lift, which is documented as out of service after a door fault; there is no alternative lift, no guaranteed repair date, and the contractor visit is only provisional for 19 February. It therefore cannot be treated as accessible on move day.
> Use an access-only visit, if permitted, to take your normal aid along the entire pavement-to-flat route and test every doorway, threshold and any required lift. The 16 January full viewing slot is the fallback opportunity to repeat that full-route check. The decision could change only with evidence that Flat 2 has a genuinely step-free, independently usable route by move day, or that Flat 10’s lift is working reliably by then; neither is currently documented. You make any booking.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state · provisional_contractor_date

**Expected:** `2027-02-19` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The source and the actual visible memory separately preserve a provisional contractor visit of 19 February and an unknown repair-completion date. The answer’s own prose explicitly gives the provisional 19 February visit, but the requested date scalar says unknown. This is an answer-level scalar omission/inconsistency, not an unavailable contractor date or a generator omission. A cautious refusal to invent a completion date does not justify discarding the known provisional visit date. Minor severity is specific to this scalar defect because the prose preserves the date and does not promise completion.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Contractor visit provisionally 19 February. Completion date unknown.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F01", "key": "comparison.move_date", "value": "15 February 2027", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "move on 15 February 2027", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/26`: {"id": "F27", "key": "building.lift_contractor_visit_date", "value": "19 February", "qualification": "reported", "source_id": "U3", "quote": "Contractor visit provisionally 19 February", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/27`: {"id": "F28", "key": "building.lift_repair_completion_date", "value": "unknown", "qualification": "unknown", "source_id": "U3", "quote": "Completion date unknown", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Flat 10 relies on the only passenger lift, which is documented as out of service after a door fault; there is no alternative lift, no guaranteed repair date, and the contractor visit is only provisional for 19 February. It therefore cannot be treated as accessible on move day.

Attribution: `answer_scalar_omission_and_prose_inconsistency`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state_neither · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out of service following door fault` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The added following-door-fault qualification is explicitly present in CM-11 and in the visible memory row. It preserves the expected out-of-service state. This is extra supported wording, not a wrong current-state value.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/25`: {"id": "F26", "key": "building.passenger_lift_operational_status", "value": "out of service following door fault", "qualification": "confirmed_in_source"}

**Relevant answer prose:**

> Flat 2 has an 80 mm raised entrance threshold and no agreed or installed ramp. Flat 10 is on the second floor; its sole passenger lift is documented out of service after a door fault, with no alternative lift and only a provisional contractor visit on 19 February—after the move date. A reported earlier “working” status conflicts with that documentation and does not establish access on the required date.
> Use the earlier access-only visit, if permitted, to trace the exact pavement-to-flat route with your normal aid: confirm every entrance, door and threshold is step-free, and check Flat 2’s 80 mm threshold cannot remain. For Flat 10, require clear evidence that the lift will be operational by 15 February and that the route to and from it is independently step-free. Use the 16 January full viewing to repeat that route end-to-end. Until those checks are evidenced, treat both as unsuitable for this requirement; do not rely on a later repair or carrying.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state_no_sources · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out of service following door fault` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The added following-door-fault qualification is explicitly present in CM-11 and in the visible memory row. It preserves the expected out-of-service state. This is extra supported wording, not a wrong current-state value.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/25`: {"id": "F26", "key": "building.passenger_lift_operational_status", "value": "out of service following door fault", "qualification": "confirmed_in_source", "status": "current", "supersedes": ["F25"]}

**Relevant answer prose:**

> Flat 10 depends on the only passenger lift, which is documented as out of service after a door fault. The contractor visit is only provisional for 19 February; no repair-completion date or alternative lift is documented. It therefore cannot be relied on for 15 February.
> Use an earlier access-only visit, if the manager permits, to test the exact pavement-to-flat route with your normal aid: the entrance chosen, every threshold/doorway, and—only for Flat 10—the lift operating independently. Use the 16 January full viewing to repeat that route. The decision could change only with evidence of a genuinely continuous zero-step route for Flat 2, or a confirmed, working lift by 15 February for Flat 10, plus verification of the whole route. Do not treat a planned repair, contractor attendance, or carrying as sufficient.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state_no_sources · provisional_contractor_date

**Expected:** `2027-02-19` · **Got:** `unknown` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The source and the actual visible memory separately preserve a provisional contractor visit of 19 February and an unknown repair-completion date. The answer’s own prose explicitly gives the provisional 19 February visit, but the requested date scalar says unknown. This is an answer-level scalar omission/inconsistency, not an unavailable contractor date or a generator omission. A cautious refusal to invent a completion date does not justify discarding the known provisional visit date. Minor severity is specific to this scalar defect because the prose preserves the date and does not promise completion.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Contractor visit provisionally 19 February. Completion date unknown.”
- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/0/text`: “for a move on 15 February 2027”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F01", "key": "comparison.move_date", "value": "15 February 2027", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/26`: {"id": "F27", "key": "building.lift_contractor_visit_date", "value": "19 February", "qualification": "reported", "status": "current", "supersedes": []}
- `/available_evidence/memory/facts/27`: {"id": "F28", "key": "building.lift_repair_completion_date", "value": "unknown", "qualification": "unknown", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Flat 10 depends on the only passenger lift, which is documented as out of service after a door fault. The contractor visit is only provisional for 19 February; no repair-completion date or alternative lift is documented. It therefore cannot be relied on for 15 February.
> Use an earlier access-only visit, if the manager permits, to test the exact pavement-to-flat route with your normal aid: the entrance chosen, every threshold/doorway, and—only for Flat 10—the lift operating independently. Use the 16 January full viewing to repeat that route. The decision could change only with evidence of a genuinely continuous zero-step route for Flat 2, or a confirmed, working lift by 15 February for Flat 10, plus verification of the whole route. Do not treat a planned repair, contractor attendance, or carrying as sufficient.

Attribution: `answer_scalar_omission_and_prose_inconsistency`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T1-state_no_updates · current_documented_lift_status

**Expected:** `out of service` · **Got:** `out of service following door fault` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The added following-door-fault qualification is explicitly present in CM-11 and in the visible memory row. It preserves the expected out-of-service state. This is extra supported wording, not a wrong current-state value.

**Original source anchors:**

- `U3` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/history/4/text`: “Only passenger lift out of service following door fault.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/25`: {"id": "F26", "key": "building.passenger_lift_operational_status", "value": "out of service following door fault", "qualification": "confirmed_in_source", "source_id": "U3", "quote": "Only passenger lift out of service following door fault"}

**Relevant answer prose:**

> Flat 2 has an 80 mm raised front-door threshold and no installed or agreed ramp plan. Flat 10 is on the second floor; its only passenger lift is documented out of service, with no alternative lift, and the provisional contractor visit is 19 February—after move-in, with no completion date guaranteed. The earlier statement that the lift was working conflicts with the later fault notice, so it cannot support access evidence.
> The few decision-changing checks are: a continuous route demonstration with your aid; confirmation that Flat 2’s 80 mm threshold has been permanently made zero-step by 15 February; or, for Flat 10, documented lift restoration before 15 February plus a successful independent route trial. A later repair, a contractor visit, or carrying you or the aid does not meet your requirement.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T2-full · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route. The answer uses this new operation evidence and treats the old outage as superseded; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for the full viewing on the access evidence now available. CM-14’s signed engineer release records that the building’s only passenger lift was repaired and returned to operation on 14 January 2027; the cancelled 19 February appointment is no longer relevant. Your own permitted access-only test then covered the continuous pavement-to-Flat-10 route independently with your usual aid, with zero steps or raised thresholds.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T2-prose · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route. The answer uses this new operation evidence and treats the old outage as superseded; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for a full viewing on access grounds. The only passenger lift was repaired and returned to operation on 14 January 2027, and your permitted access-only test recorded a continuous independent pavement-to-flat route using your usual aid with 0 steps or raised thresholds, including the lift and Flat 10 doorway.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T2-state · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route. The answer uses this new operation evidence and treats the old outage as superseded; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for a full viewing on access grounds only. What changed is that CM-14 records the sole lift as repaired and returned to operation on 14 January 2027, and your own permitted route test found zero steps or raised thresholds from pavement through Flat 10’s doorway, independently with your usual aid. That meets your stated access requirement for this route.
> CM-11 adds no newer contrary inspection; its 11 January attachment is superseded for this point by the signed 14 January release. This is not an approval of the flat overall: the rooms were not inspected, and the lift’s ongoing reliability and all other suitability checks remain unassessed. Flat 2’s 80 mm threshold remains incompatible with the zero-threshold requirement. Do not book or pay.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T2-state_neither · current_documented_lift_status

**Expected:** `operational` · **Got:** `operating` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Operating and operational denote the same current lift state here. The latest question itself supplies CM-14 release and the successful observed operating-lift route. The answer uses this new operation evidence and treats the old outage as superseded; this scalar mismatch is lexical, not a stale-outage conclusion.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for the full viewing on access grounds, but only as a limited access approval. The sole passenger lift was repaired and returned to operation on 14 January 2027, and your access-only visit independently confirmed a zero-step route from the street pavement through the entrance, lift and Flat 10 doorway using your usual aid. That resolves the previous access blocker; the cancelled 19 February appointment and re-forwarded 11 January CM-11 do not change the newer release evidence.
> Limits: this was not a room inspection, so it is not approval of the flat overall or confirmation of continuing lift reliability through the 15 February 2027 move date. At the full viewing, repeat the route and inspect the flat itself. Flat 2 remains unsuitable for the zero-step requirement because its 80 mm threshold is unchanged. Flat 10’s estimated all-in cost is £2,010, within your £2,050 ceiling. Do not book or pay.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S2-r2-T2-state_no_updates · current_documented_lift_status

**Expected:** `operational` · **Got:** `repaired and returned to operation` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Repaired and returned to operation states the same documented operational status, using wording directly supported by the latest question’s CM-14 signed release. The answer also distinguishes the old outage and cancelled appointment from the new release and successful route test. This is additional supported wording, not a wrong current-state value.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/1/turns/1/text`: “the only passenger lift was returned to operation on 14 January 2027”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: New records dated 14 January: the building manager sent CM-14 with the engineer's signed release attached: the door fault was repaired that morning and the only passenger lift was returned to operation on 14 January 2027.

**Relevant answer prose:**

> Yes—approve Flat 10 for a full viewing on access grounds only. The current record is the signed CM-14 release: the sole passenger lift was repaired and returned to operation on 14 January 2027; the 19 February appointment was cancelled. Your permitted access-only trial then independently completed the pavement-to-Flat-10 route with your usual aid and zero steps or raised thresholds.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-full · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/history/0/text`: The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.

**Relevant answer prose:**

> Current record: target flat is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach; the invoice is £240 to L. Cress. Threadleaf is not booked, and no refund deadline is known.
> “Before I can consider the £240 reservation payment for Flat 12B, 52 Foxbarrel Reach, please send today: (1) evidence linking the supplied certificate or another certificate to Flat 12B and its stated 47 m²; (2) written authority linking the owner, Foxbarrel Residential Ltd/Foxbarrel Homes, and L. Cress to this specific reservation; and (3) the written reservation, cancellation and refund terms, including what happens if these checks cannot be completed. I will independently confirm the recipient details through my existing office contact route before making any transfer.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-full · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/history/2/text`: The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.

**Relevant answer prose:**

> Current record: target flat is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach; the invoice is £240 to L. Cress. Threadleaf is not booked, and no refund deadline is known.
> “Before I can consider the £240 reservation payment for Flat 12B, 52 Foxbarrel Reach, please send today: (1) evidence linking the supplied certificate or another certificate to Flat 12B and its stated 47 m²; (2) written authority linking the owner, Foxbarrel Residential Ltd/Foxbarrel Homes, and L. Cress to this specific reservation; and (3) the written reservation, cancellation and refund terms, including what happens if these checks cannot be completed. I will independently confirm the recipient details through my existing office contact route before making any transfer.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-full · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/history/8/text`: but I have not booked or paid and the refund cutoff was not displayed.

**Relevant answer prose:**

> Current record: target flat is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach; the invoice is £240 to L. Cress. Threadleaf is not booked, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-prose · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory`: Target is Flat 12B, 52 Foxbarrel Reach (not Flat 12). Requirements are at least 40 m² internal space, separate bedroom, all-in monthly cost no more than £2,250, move on 4 March 2027, and a trip to fictional Ashmill Library of no more than 35 minutes; there is no building-age limit. Listing F-L states one bedroom, 47 m², 4 March availability, £2,160 estimated all-in monthly, and 29-minute route, but these items are unverified. An alleged official EPC instead identifies Flat 12 and 38 m², with no unit cross-reference or plan match; the agent’s marketing-label explanation is unproven. No money has been sent. A £240 reservation invoice names Foxbarrel Residential Ltd and payee L. Cress, but owner/authority, payee relationship and written refund terms are absent; phone-only refund assurance is unverified. A separate brochure phone route and bank confirmation remain unused/unreceived. Fallback Threadleaf quote is £330 for three refundable-described nights from 4 March, but is unbooked, cutoff unknown, and not guaranteed.

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm on the current packet. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate identifies Flat 12 (38 m²), not 12B; that mismatch is unresolved and would also miss your 40 m² minimum if it were the target. The current invoice is £240 to L. Cress, despite naming Foxbarrel Residential Ltd, with no written authority/payee link or refund terms. Threadleaf is not booked; its refund deadline is unknown.
> Draft: “Before I can consider the £240 reservation payment, please send the written document confirming that it is for Flat 12B, 52 Foxbarrel Reach; the relationship between Foxbarrel Residential Ltd and payee L. Cress; and the full written refund/cancellation terms, including what happens if the flat or referencing does not proceed. Please also explain, in writing, why the supplied certificate is for Flat 12 rather than Flat 12B and provide a unit-specific supporting document. I cannot transfer against a phone-only assurance.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "f1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "The target is Flat 12B, 52 Foxbarrel Reach", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach; there is no document tying them together. The current invoice is £240 payable to L. Cress, whose relationship to Foxbarrel Residential Ltd is unexplained, and it has no written refund terms. Threadleaf is not booked, and its refund deadline is unknown.
> “Before I can pay, please send the written evidence linking Flat 12B to the supplied certificate for Flat 12, the owner/letting authority, confirmation through the independent brochure contact that L. Cress is the authorised £240 payee, and the written reservation and refund terms. I cannot transfer on the basis of a verbal refund assurance or documents still being prepared.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "f22", "key": "epc_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "source_id": "U2", "quote": "instead names Flat 12, 52 Foxbarrel Reach", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach; there is no document tying them together. The current invoice is £240 payable to L. Cress, whose relationship to Foxbarrel Residential Ltd is unexplained, and it has no written refund terms. Threadleaf is not booked, and its refund deadline is unknown.
> “Before I can pay, please send the written evidence linking Flat 12B to the supplied certificate for Flat 12, the owner/letting authority, confirmation through the independent brochure contact that L. Cress is the authorised £240 payee, and the written reservation and refund terms. I cannot transfer on the basis of a verbal refund assurance or documents still being prepared.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/44`: {"id": "f45", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "source_id": "U5", "quote": "I have not booked or paid", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach; there is no document tying them together. The current invoice is £240 payable to L. Cress, whose relationship to Foxbarrel Residential Ltd is unexplained, and it has no written refund terms. Threadleaf is not booked, and its refund deadline is unknown.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_neither · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "f1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source"}

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm on the current packet. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no cross-reference. The invoice is £240 payable to L. Cress, while the connection to Foxbarrel Residential Ltd is unexplained and written refund terms are absent. Threadleaf Rooms is not booked or paid; its refund deadline is unknown.
> “Before I can pay the £240 reservation amount, please send the existing written evidence for: (1) confirmation that the supplied certificate for Flat 12 applies to Flat 12B, or the correct certificate; (2) the owner’s authority for Foxbarrel Residential Ltd/Foxbarrel Homes to reserve Flat 12B; (3) confirmation through the separate brochure contact that L. Cress is the authorised payee and the bank details are correct; and (4) the written reservation, cancellation and refund terms. I cannot transfer on the basis of a verbal deadline alone.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_neither · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "f22", "key": "epc_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported"}

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm on the current packet. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no cross-reference. The invoice is £240 payable to L. Cress, while the connection to Foxbarrel Residential Ltd is unexplained and written refund terms are absent. Threadleaf Rooms is not booked or paid; its refund deadline is unknown.
> “Before I can pay the £240 reservation amount, please send the existing written evidence for: (1) confirmation that the supplied certificate for Flat 12 applies to Flat 12B, or the correct certificate; (2) the owner’s authority for Foxbarrel Residential Ltd/Foxbarrel Homes to reserve Flat 12B; (3) confirmation through the separate brochure contact that L. Cress is the authorised payee and the bank details are correct; and (4) the written reservation, cancellation and refund terms. I cannot transfer on the basis of a verbal deadline alone.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_neither · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/44`: {"id": "f45", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source"}

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm on the current packet. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no cross-reference. The invoice is £240 payable to L. Cress, while the connection to Foxbarrel Residential Ltd is unexplained and written refund terms are absent. Threadleaf Rooms is not booked or paid; its refund deadline is unknown.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_sources · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "f1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no evidence linking it to 12B. The current invoice is £240 payable to L. Cress; the packet does not establish that person’s authority or their relationship to Foxbarrel Residential Ltd, and it contains no written cancellation/refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.
> “Before I can transfer the £240 reservation payment for Flat 12B, please send the currently available written evidence linking the supplied certificate to Flat 12B, confirming Foxbarrel Residential Ltd’s authority for L. Cress to receive this payment, and stating the reservation cancellation and refund terms. I will review those documents promptly once received.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_sources · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "f22", "key": "epc_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no evidence linking it to 12B. The current invoice is £240 payable to L. Cress; the packet does not establish that person’s authority or their relationship to Foxbarrel Residential Ltd, and it contains no written cancellation/refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.
> “Before I can transfer the £240 reservation payment for Flat 12B, please send the currently available written evidence linking the supplied certificate to Flat 12B, confirming Foxbarrel Residential Ltd’s authority for L. Cress to receive this payment, and stating the reservation cancellation and refund terms. I will review those documents promptly once received.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_sources · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/44`: {"id": "f45", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), with no evidence linking it to 12B. The current invoice is £240 payable to L. Cress; the packet does not establish that person’s authority or their relationship to Foxbarrel Residential Ltd, and it contains no written cancellation/refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_updates · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "f1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "The target is Flat 12B, 52 Foxbarrel Reach"}

**Relevant answer prose:**

> Do not transfer the £240 before the stated deadline. The target is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m², D), with no cross-reference proving it is 12B. The current invoice is £240 payable to L. Cress, whose link to Foxbarrel Residential Ltd is not evidenced in the packet. Threadleaf Rooms is not booked or paid, and its refund deadline is unknown.
> Send this for review: “I am ready to proceed once the current packet evidences that the certificate applies to Flat 12B, confirms the owner/agent authority and L. Cress’s authority to receive the £240, and provides the written reservation and refund terms. Please send those documents; I cannot transfer on the basis of a promised future document.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_updates · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "f22", "key": "epc_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "source_id": "U2", "quote": "instead names Flat 12, 52 Foxbarrel Reach"}

**Relevant answer prose:**

> Do not transfer the £240 before the stated deadline. The target is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m², D), with no cross-reference proving it is 12B. The current invoice is £240 payable to L. Cress, whose link to Foxbarrel Residential Ltd is not evidenced in the packet. Threadleaf Rooms is not booked or paid, and its refund deadline is unknown.
> Send this for review: “I am ready to proceed once the current packet evidences that the certificate applies to Flat 12B, confirms the owner/agent authority and L. Cress’s authority to receive the £240, and provides the written reservation and refund terms. Please send those documents; I cannot transfer on the basis of a promised future document.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T1-state_no_updates · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/44`: {"id": "f45", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "source_id": "U5", "quote": "I have not booked or paid"}

**Relevant answer prose:**

> Do not transfer the £240 before the stated deadline. The target is Flat 12B, 52 Foxbarrel Reach; the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m², D), with no cross-reference proving it is 12B. The current invoice is £240 payable to L. Cress, whose link to Foxbarrel Residential Ltd is not evidenced in the packet. Threadleaf Rooms is not booked or paid, and its refund deadline is unknown.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-full · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. Your three stated verification gates are now sufficiently answered to move on to reviewing the final tenancy pack; the old Flat 12 mismatch no longer blocks that next step because it was expressly corrected with an official extract for Flat 12B. Keep the older mismatch as a resolved record, not a reason to treat later documents as interchangeable.
> Current record: certificate—Flat 12B, 52 Foxbarrel Reach, 44 m², C. Corrected payee—Foxbarrel Residential Ltd; reservation amount—£240. Threadleaf is not booked; its new £345 quote is only subject to availability, with a refund cutoff of 3 March 2027 at 15:00 if booked.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-full · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Current record: certificate—Flat 12B, 52 Foxbarrel Reach, 44 m², C. Corrected payee—Foxbarrel Residential Ltd; reservation amount—£240. Threadleaf is not booked; its new £345 quote is only subject to availability, with a refund cutoff of 3 March 2027 at 15:00 if booked.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-prose · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes—the three verification gates are now answered sufficiently to move on to reviewing the final tenancy pack. The old Flat 12/12B mismatch no longer blocks that step: the supplied official extract is specifically for Flat 12B, 52 Foxbarrel Reach, at 44 m² (EPC C). The corrected £240 invoice/payee, authority letter, accounts callback, bank payee check, and written reservation terms resolve the identity and payment-purpose concerns.
> Current details: certificate: Flat 12B, 52 Foxbarrel Reach; 44 m². Payee: Foxbarrel Residential Ltd. Reservation amount: £240. Threadleaf remains unbooked; if booked, the stated refund cutoff is 3 March 2027 at 15:00, subject to availability.
> Remaining limits: the listing’s 47 m² figure still differs from the 44 m² official figure, so use 44 m². The Threadleaf quote is not a secured stay. Reviewing the pack is not a reason to pay or sign; check that it names Flat 12B and preserves the stated reservation-credit and refund terms.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. Your three verification gates are now sufficiently answered to move on to reviewing the final tenancy pack; the old Flat 12/12B mismatch no longer blocks that next step because the supplied official extract specifically identifies Flat 12B. This is only clearance to review the pack, not to pay or sign.
> Current details: the certificate is for Flat 12B, 52 Foxbarrel Reach, at 44 m² (C). The corrected £240 reservation invoice names Foxbarrel Residential Ltd, with the company/account ending 4812 independently matched. The written terms identify Flat 12B and state the stated refund cases.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Remaining limits: the final tenancy pack still needs checking against these terms and the exact flat; the £2,160 all-in figure remains an estimate; and the new Threadleaf £345 quote is only subject to availability. Threadleaf is not booked. If booked, its stated refundable-cancellation cutoff is 2027-03-03 15:00.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_neither · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. On the supplied facts, the three pre-payment verification gates are now sufficiently answered to move on to reviewing the final tenancy pack. The old Flat 12 / 12B mismatch no longer blocks that next step: the replacement official extract is for Flat 12B, 52 Foxbarrel Reach, at 44 m² (rating C), and the agent has withdrawn the claim that the units are the same.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_neither · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”
- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “It is the following afternoon; I have paid nothing.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.
- `/available_evidence/latest_user_question/text`: It is the following afternoon; I have paid nothing.

**Relevant answer prose:**

> Threadleaf is not booked or paid. The new £345 quote is subject to availability; if booked, its stated refund cutoff is 2027-03-03 15:00. Remaining limits: the final tenancy pack has not yet been supplied for review, and Threadleaf availability is not guaranteed until booked.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_no_sources · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. On the supplied account, all three gates are now sufficiently answered for you to review the final tenancy pack: the official extract is for Flat 12B and meets your 40 m² minimum; the landlord’s authority and the corrected company payee/account were independently confirmed; and the £240 written reservation terms identify the flat, credit the payment toward rent, and state the stated full-refund triggers. The old Flat 12/L. Cress mismatch is superseded rather than a block.
> Current details: certificate — Flat 12B, 52 Foxbarrel Reach, 44 m² (C); payee — Foxbarrel Residential Ltd; reservation amount — £240. Threadleaf is not booked; the new £345 quote is subject to availability, with the stated refund cutoff of 3 March 2027 at 15:00 if booked. Remaining limits: I have not seen the final tenancy pack or independently verified its terms, and the accommodation is not held without a booking. No payment or signature is implied.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_no_sources · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Current details: certificate — Flat 12B, 52 Foxbarrel Reach, 44 m² (C); payee — Foxbarrel Residential Ltd; reservation amount — £240. Threadleaf is not booked; the new £345 quote is subject to availability, with the stated refund cutoff of 3 March 2027 at 15:00 if booked. Remaining limits: I have not seen the final tenancy pack or independently verified its terms, and the accommodation is not held without a booking. No payment or signature is implied.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_no_updates · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. On the supplied updates, the three stated verification gates are now sufficiently answered to move to a review of the final tenancy pack; the old Flat 12/12B mismatch no longer blocks that next step. It remains a historical discrepancy, but the replacement official extract specifically identifies Flat 12B, 52 Foxbarrel Reach, at 44 m² with EPC C, and the agent has withdrawn the claim that the two flats are the same.
> The corrected reservation recipient is Foxbarrel Residential Ltd for £240. The supplied authority letter, accounts callback, landlord confirmation, and bank payee check support the landlord–agent link and recipient details. The written terms also identify Flat 12B and state the specified credit/refund conditions. This is sufficient to review, not a recommendation to pay or sign.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r1-T2-state_no_updates · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Threadleaf is not booked. The current quote is £345, subject to availability; if booked, its stated refund cutoff is 2027-03-03 at 15:00. Remaining limits: the £2,160 all-in figure is unchanged but not re-verified here, and the final tenancy pack still needs review before any commitment.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-full · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/history/0/text`: The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.

**Relevant answer prose:**

> Do not transfer now. Flat 12B, 52 Foxbarrel Reach is still not evidenced by the supplied certificate: it names Flat 12, not 12B. The current invoice is £240 payable to L. Cress, with no documented landlord/agent authority, recipient confirmation, or written refund terms. Threadleaf is not booked, and its refund deadline is unknown.
> “Before I can consider the £240 reservation payment for Flat 12B, 52 Foxbarrel Reach, please provide in one reply: (1) exact-unit evidence linking Flat 12B to the certificate/47 m² listing, (2) written authority linking the owner, Foxbarrel Residential Ltd and L. Cress to this invoice, and (3) the written reservation, cancellation and refund terms. I will then review the packet and complete my own callback/payee check before deciding.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-full · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/history/2/text`: The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.

**Relevant answer prose:**

> Do not transfer now. Flat 12B, 52 Foxbarrel Reach is still not evidenced by the supplied certificate: it names Flat 12, not 12B. The current invoice is £240 payable to L. Cress, with no documented landlord/agent authority, recipient confirmation, or written refund terms. Threadleaf is not booked, and its refund deadline is unknown.
> “Before I can consider the £240 reservation payment for Flat 12B, 52 Foxbarrel Reach, please provide in one reply: (1) exact-unit evidence linking Flat 12B to the certificate/47 m² listing, (2) written authority linking the owner, Foxbarrel Residential Ltd and L. Cress to this invoice, and (3) the written reservation, cancellation and refund terms. I will then review the packet and complete my own callback/payee check before deciding.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-full · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/history/8/text`: but I have not booked or paid and the refund cutoff was not displayed.

**Relevant answer prose:**

> Do not transfer now. Flat 12B, 52 Foxbarrel Reach is still not evidenced by the supplied certificate: it names Flat 12, not 12B. The current invoice is £240 payable to L. Cress, with no documented landlord/agent authority, recipient confirmation, or written refund terms. Threadleaf is not booked, and its refund deadline is unknown.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-prose · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory`: Fictional rental exercise concerning Flat 12B, 52 Foxbarrel Reach (not Flat 12). Requirements are at least 40 m² internal area, separate bedroom, all-in cost up to £2,250/month, move on 4 March 2027, and travel to fictional Ashmill Library within 35 minutes; no building-age limit. Listing F-L states one bedroom, 47 m², 4 March availability, £2,160 estimated all-in monthly cost, and a supplied 29-minute route. However, the labelled EPC extract identifies Flat 12 and 38 m² (rating D); no cross-reference or matching plan substantiates the agent’s claim that the suffix is only marketing. Unit identity, area, route and bills remain unverified. No payment has been transferred. The £240 reservation invoice names Foxbarrel Residential Ltd but payee L. Cress lacks documented owner/agent authority, recipient confirmation, and written cancellation/refund terms. An older brochure offers an uncompleted separate-route invoice check; promised documents have not arrived. A Threadleaf Rooms fallback quote is £330 for three refundable-described nights from 4 March, but is unbooked and not guaranteed.

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm. The packet does not yet tie the supplied certificate to Flat 12B or establish that L. Cress is authorised to receive Foxbarrel Residential Ltd’s reservation payment; it also lacks written cancellation/refund terms.
> Target flat: Flat 12B, 52 Foxbarrel Reach. Supplied certificate: Flat 12, 52 Foxbarrel Reach. Current invoice: £240, named payee L. Cress. Threadleaf Rooms is not booked, and no refund deadline is known.
> “Before I can transfer the £240 reservation payment, please send the written confirmation that the invoice payee L. Cress is authorised to receive payment for Foxbarrel Residential Ltd, confirmation that the reservation is for Flat 12B (not Flat 12), and the written cancellation/refund terms. Once received, I can review them promptly.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-prose · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match. The prose memory abbreviates the certificate unit to Flat 12 while supplying the comparison’s full address at its start; the original certificate source explicitly confirms that same address. No alternative certificate address is introduced.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory`: Fictional rental exercise concerning Flat 12B, 52 Foxbarrel Reach (not Flat 12). Requirements are at least 40 m² internal area, separate bedroom, all-in cost up to £2,250/month, move on 4 March 2027, and travel to fictional Ashmill Library within 35 minutes; no building-age limit. Listing F-L states one bedroom, 47 m², 4 March availability, £2,160 estimated all-in monthly cost, and a supplied 29-minute route. However, the labelled EPC extract identifies Flat 12 and 38 m² (rating D); no cross-reference or matching plan substantiates the agent’s claim that the suffix is only marketing. Unit identity, area, route and bills remain unverified. No payment has been transferred. The £240 reservation invoice names Foxbarrel Residential Ltd but payee L. Cress lacks documented owner/agent authority, recipient confirmation, and written cancellation/refund terms. An older brochure offers an uncompleted separate-route invoice check; promised documents have not arrived. A Threadleaf Rooms fallback quote is £330 for three refundable-described nights from 4 March, but is unbooked and not guaranteed.

**Relevant answer prose:**

> Do not transfer the £240 by 5 pm. The packet does not yet tie the supplied certificate to Flat 12B or establish that L. Cress is authorised to receive Foxbarrel Residential Ltd’s reservation payment; it also lacks written cancellation/refund terms.
> Target flat: Flat 12B, 52 Foxbarrel Reach. Supplied certificate: Flat 12, 52 Foxbarrel Reach. Current invoice: £240, named payee L. Cress. Threadleaf Rooms is not booked, and no refund deadline is known.
> “Before I can transfer the £240 reservation payment, please send the written confirmation that the invoice payee L. Cress is authorised to receive payment for Foxbarrel Residential Ltd, confirmation that the reservation is for Flat 12B (not Flat 12), and the written cancellation/refund terms. Once received, I can review them promptly.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Target: Flat 12B, 52 Foxbarrel Reach. Supplied certificate: Flat 12, 52 Foxbarrel Reach (38 m², D), not demonstrably Flat 12B. Current invoice: £240 payable to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.
> “Before I can authorise the £240 for Flat 12B, please send the existing written evidence that links the supplied certificate to Flat 12B, confirms your authority/owner link and L. Cress’s relationship to Foxbarrel Residential Ltd, and states the reservation and refund terms. Please also confirm whether the 5 pm deadline remains once those documents are supplied. I will review the documents before making any payment.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "F22", "key": "epc_extract_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "source_id": "U2", "quote": "instead names Flat 12, 52 Foxbarrel Reach", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Target: Flat 12B, 52 Foxbarrel Reach. Supplied certificate: Flat 12, 52 Foxbarrel Reach (38 m², D), not demonstrably Flat 12B. Current invoice: £240 payable to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.
> “Before I can authorise the £240 for Flat 12B, please send the existing written evidence that links the supplied certificate to Flat 12B, confirms your authority/owner link and L. Cress’s relationship to Foxbarrel Residential Ltd, and states the reservation and refund terms. Please also confirm whether the 5 pm deadline remains once those documents are supplied. I will review the documents before making any payment.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/42`: {"id": "F43", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "source_id": "U5", "quote": "I have not booked or paid", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Target: Flat 12B, 52 Foxbarrel Reach. Supplied certificate: Flat 12, 52 Foxbarrel Reach (38 m², D), not demonstrably Flat 12B. Current invoice: £240 payable to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_neither · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source"}

**Relevant answer prose:**

> Do not transfer now. The target is **Flat 12B, 52 Foxbarrel Reach**, but the supplied certificate is for **Flat 12, 52 Foxbarrel Reach** (38 m²), so it does not establish the advertised 12B/47 m² unit. The current invoice is **£240** payable to **L. Cress**; the packet does not show that person’s authority or the written refund terms. Threadleaf is **not booked or paid**, and no refund deadline is known.
> > I want to proceed with Flat 12B, but I cannot transfer the £240 to L. Cress yet. Please send, today, the document linking Flat 12B to its current certificate/area, confirmation that Foxbarrel Residential Ltd authorises this named payee to receive the reservation payment, and the written reservation and refund terms. Once those match the unit and payment recipient, I can review them promptly.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_neither · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "F22", "key": "epc_extract_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported"}

**Relevant answer prose:**

> Do not transfer now. The target is **Flat 12B, 52 Foxbarrel Reach**, but the supplied certificate is for **Flat 12, 52 Foxbarrel Reach** (38 m²), so it does not establish the advertised 12B/47 m² unit. The current invoice is **£240** payable to **L. Cress**; the packet does not show that person’s authority or the written refund terms. Threadleaf is **not booked or paid**, and no refund deadline is known.
> > I want to proceed with Flat 12B, but I cannot transfer the £240 to L. Cress yet. Please send, today, the document linking Flat 12B to its current certificate/area, confirmation that Foxbarrel Residential Ltd authorises this named payee to receive the reservation payment, and the written reservation and refund terms. Once those match the unit and payment recipient, I can review them promptly.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_neither · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/42`: {"id": "F43", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source"}

**Relevant answer prose:**

> Do not transfer now. The target is **Flat 12B, 52 Foxbarrel Reach**, but the supplied certificate is for **Flat 12, 52 Foxbarrel Reach** (38 m²), so it does not establish the advertised 12B/47 m² unit. The current invoice is **£240** payable to **L. Cress**; the packet does not show that person’s authority or the written refund terms. Threadleaf is **not booked or paid**, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_sources · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), so the unit evidence remains unresolved. The current invoice is £240 payable to L. Cress; the packet does not establish that payee’s authority or provide written refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.
> “Before I can pay the £240, please send written confirmation that the supplied certificate applies specifically to Flat 12B, confirmation that L. Cress is authorised to receive the payment for Foxbarrel Residential Ltd, and the written reservation/refund terms. Please also confirm what the £240 secures and the proposed tenancy terms. I cannot transfer on the basis of the current documents.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_sources · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "F22", "key": "epc_extract_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), so the unit evidence remains unresolved. The current invoice is £240 payable to L. Cress; the packet does not establish that payee’s authority or provide written refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.
> “Before I can pay the £240, please send written confirmation that the supplied certificate applies specifically to Flat 12B, confirmation that L. Cress is authorised to receive the payment for Foxbarrel Residential Ltd, and the written reservation/refund terms. Please also confirm what the £240 secures and the proposed tenancy terms. I cannot transfer on the basis of the current documents.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_sources · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/42`: {"id": "F43", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "status": "current", "supersedes": []}

**Relevant answer prose:**

> Do not transfer now. The target is Flat 12B, 52 Foxbarrel Reach, but the supplied certificate is for Flat 12, 52 Foxbarrel Reach (38 m²), so the unit evidence remains unresolved. The current invoice is £240 payable to L. Cress; the packet does not establish that payee’s authority or provide written refund terms. Threadleaf Rooms is not booked or paid, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_updates · target_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar retains the decisive Flat 12B suffix and appends the correct street address explicitly present in the original source and visible evidence. It does not conflate Flat 12B with Flat 12. This is a supported fuller identifier for the same target, not a wrong unit.

**Original source anchors:**

- `U1` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/0/text`: “The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/0`: {"id": "F1", "key": "target_property.identity", "value": "Flat 12B, 52 Foxbarrel Reach", "qualification": "confirmed_in_source", "source_id": "U1", "quote": "The target is Flat 12B, 52 Foxbarrel Reach, never Flat 12 without the B."}

**Relevant answer prose:**

> Do not transfer the £240 by the stated deadline. The packet still does not link the supplied certificate’s Flat 12 to target Flat 12B, and it contains no authority link, verified recipient relationship, or written refund terms. The current invoice is £240 to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.
> “Before I can pay, please provide the existing written evidence that the certificate for Flat 12 applies to Flat 12B, confirmation of Foxbarrel Residential Ltd’s authority for Flat 12B and L. Cress’s relationship to it, and the written reservation and refund terms for the £240 payment. Please also confirm the payment details through the separate office contact route shown in the brochure. Until those items are provided and verified, I cannot transfer funds.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_updates · supplied_certificate_flat

**Expected:** `Flat 12` · **Got:** `Flat 12, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The reported scalar preserves the supplied certificate’s Flat 12 identifier without adding the B suffix; it only adds the same correct street address. The answer continues to distinguish this certificate from the Flat 12B target. This is a supported fuller certificate identifier, not an incorrect exact-unit match.

**Original source anchors:**

- `U2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/2/text`: “The attached document labelled official EPC extract F-E instead names Flat 12, 52 Foxbarrel Reach, and gives 38 m², D.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/21`: {"id": "F22", "key": "epc_extract_F-E.property_identity", "value": "Flat 12, 52 Foxbarrel Reach", "qualification": "reported", "source_id": "U2", "quote": "instead names Flat 12, 52 Foxbarrel Reach"}

**Relevant answer prose:**

> Do not transfer the £240 by the stated deadline. The packet still does not link the supplied certificate’s Flat 12 to target Flat 12B, and it contains no authority link, verified recipient relationship, or written refund terms. The current invoice is £240 to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.
> “Before I can pay, please provide the existing written evidence that the certificate for Flat 12 applies to Flat 12B, confirmation of Foxbarrel Residential Ltd’s authority for Flat 12B and L. Cress’s relationship to it, and the written reservation and refund terms for the £240 payment. Please also confirm the payment details through the separate office contact route shown in the brochure. Until those items are provided and verified, I cannot transfer funds.”

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T1-state_no_updates · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked or paid` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The extra unpaid qualification is also supported: U5 explicitly says no booking or payment, and T2, where applicable, states that nothing has been paid and there is still no booking. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `U5` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/history/8/text`: “but I have not booked or paid and the refund cutoff was not displayed.”

**Actual visible evidence:**

- `/available_evidence/memory/facts/42`: {"id": "F43", "key": "fallback.Threadleaf_Rooms.booking_status", "value": "not booked or paid", "qualification": "confirmed_in_source", "source_id": "U5", "quote": "I have not booked or paid"}

**Relevant answer prose:**

> Do not transfer the £240 by the stated deadline. The packet still does not link the supplied certificate’s Flat 12 to target Flat 12B, and it contains no authority link, verified recipient relationship, or written refund terms. The current invoice is £240 to L. Cress. Threadleaf is not booked or paid, and no refund deadline is known.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-full · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. Your three gates are now sufficiently answered to move to a review of the final tenancy pack; the old Flat 12/12B mismatch is superseded by the supplied official extract for Flat 12B and the agent’s withdrawal of the earlier claim. Keep the old mismatch in the record, but it no longer blocks that next review.
> Current facts: the certificate is for Flat 12B, 52 Foxbarrel Reach, 44 m², C. The corrected £240 reservation invoice names Foxbarrel Residential Ltd, and your callback, landlord confirmation, and bank payee check align with its account ending 4812. The written terms identify Flat 12B and state the specified credit/refund conditions.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-full · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Threadleaf is not booked. The current £345 quote is subject to availability; if you book it, the stated refund cutoff is 2027-03-03 15:00. This is only clearance to review the tenancy pack, not to pay or sign.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-full · threadleaf_refund_deadline

**Expected:** `2027-03-03 15:00` · **Got:** `2027-03-03` · **Original deterministic pass:** false.

**Verdict:** missing_or_unknown_information; semantic-equivalent=false; severity=minor.

The requested refund cutoff is a date and time. The original source and the directly visible latest T2 question explicitly give 3 March 2027 at 15:00. The scalar retains only 2027-03-03, losing the decisive time; a date alone does not identify the same precise cutoff. The answer prose correctly states 2027-03-03 15:00, so the defect is an answer-level scalar omission/inconsistency rather than missing source information or generator loss. Minor severity is specific to this field because the usable complete cutoff remains in prose. This differs from the earlier context-resolvable missing-year dates: 15:00 is an explicit requested precision component, not a year inferable from a shared narrative timeline.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “with cancellation by 3 March 2027 at 15:00 for a refund if booked.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: with cancellation by 3 March 2027 at 15:00 for a refund if booked.

**Relevant answer prose:**

> Threadleaf is not booked. The current £345 quote is subject to availability; if you book it, the stated refund cutoff is 2027-03-03 15:00. This is only clearance to review the tenancy pack, not to pay or sign.

Attribution: `answer_scalar_omission_and_prose_inconsistency`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-prose · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes—the three stated gates are now sufficiently answered to move on to a review of the final tenancy pack. The earlier Flat 12/12B mismatch has been corrected by the supplied official extract, and the payee/authority and reservation-refund checks now align. It no longer blocks document review.
> Current certificate: Flat 12B, 52 Foxbarrel Reach; 44 m² (C). Corrected reservation payee: Foxbarrel Residential Ltd; £240. Threadleaf is still unbooked; the new £345 quote is availability-dependent, and if booked its stated refund cutoff is 2027-03-03 15:00.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. The three verification gates are now sufficiently answered to move on to reviewing the final tenancy pack; the old Flat 12 / 12B mismatch no longer blocks that next step because the supplied official extract is specifically for Flat 12B. This is only clearance to review documents, not to pay or sign.
> Current certificate: Flat 12B, 52 Foxbarrel Reach — 44 m², EPC C. The listing’s former 47 m² claim remains a discrepancy, so use 44 m² as the evidenced internal area.
> Reservation: corrected payee Foxbarrel Residential Ltd, £240, with the account ending 4812 confirmed through the bank check and accounts callback. The written terms identify Flat 12B and state the specified credit/refund conditions. Remaining limit: the supplied facts do not say whether any deadline still applies or whether the final tenancy pack is yet available.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Threadleaf: not booked. The new £345 quote remains subject to availability; its stated refundable-cancellation cutoff is 2027-03-03 15:00.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_neither · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. The three gates are now sufficiently answered to move to a review of the final tenancy pack; the old Flat 12/12B mismatch is resolved rather than a continuing blocker. This is only permission to review documents, not to pay or sign.
> Current position: the supplied official certificate is for Flat 12B, 52 Foxbarrel Reach: 44 m², EPC C. The corrected reservation invoice is £240 payable to Foxbarrel Residential Ltd, with the company/account independently matched and written terms identifying Flat 12B and stating the specified refund protections. The £2,160 all-in estimate remains below your £2,250 limit, but remains an estimate.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_neither · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Threadleaf is not booked. The new £345 quote is subject to availability; if booked, its stated refund cutoff is 2027-03-03 at 15:00. Remaining limits: the final tenancy pack has not yet been reviewed, the stay is not guaranteed until booked, and the quoted Threadleaf price/availability may change.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_no_sources · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Yes. The three verification gates are now sufficiently answered to move on to reviewing the final tenancy pack; the old Flat 12/12B mismatch has been explicitly corrected and no longer blocks that review. This is only clearance to review, not to pay or sign.
> Current position: the official certificate is for Flat 12B, 52 Foxbarrel Reach, showing 44 m² and rating C. The corrected £240 reservation invoice names Foxbarrel Residential Ltd, with the account confirmation and authority checks described. Its written terms identify Flat 12B and state the stated credit/refund conditions.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_no_sources · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Remaining limits: the final tenancy pack has not yet been reviewed, and the £2,160 all-in figure remains an estimate. Threadleaf is not booked; the new £345 quote is subject to availability. If booked under that quote, its stated refund cutoff is 3 March 2027 at 15:00.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_no_updates · current_certificate_flat

**Expected:** `Flat 12B` · **Got:** `Flat 12B, 52 Foxbarrel Reach` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

The latest question explicitly supplies the replacement certificate for Flat 12B at this full address. The scalar retains the correct B suffix and adds the supported address. The prose uses the replacement document and does not carry the old Flat 12 mismatch forward as the current certificate. This is a supported fuller identifier for the same corrected unit.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: F-E2 is the supplied official extract for Flat 12B, 52 Foxbarrel Reach: 44 m², C; the agent withdrew the claim that 12 and 12B are the same.

**Relevant answer prose:**

> Current certificate: Flat 12B, 52 Foxbarrel Reach — 44 m², EPC C. The corrected reservation invoice is £240 payable to Foxbarrel Residential Ltd, credited toward rent if an agreement is entered, with the stated refund conditions. Remaining limits: the £2,160 all-in figure is still an estimate, and the new Threadleaf quote is subject to availability.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

### S3-r2-T2-state_no_updates · threadleaf_booking_status

**Expected:** `unbooked` · **Got:** `not booked` · **Original deterministic pass:** false.

**Verdict:** exact_format_or_wording_equivalent; semantic-equivalent=true; severity=none.

Not booked and unbooked express the same booking state. The answer does not promote a quote into a reservation or guaranteed accommodation. This is a supported status wording variation.

**Original source anchors:**

- `T2` at `bench/results/ablation-2026-09-09/live-v1/rental-cases.json#/cases/2/turns/1/text`: “I still have no booking.”

**Actual visible evidence:**

- `/available_evidence/latest_user_question/text`: I still have no booking.

**Relevant answer prose:**

> Current certificate: Flat 12B, 52 Foxbarrel Reach — 44 m², EPC C. The corrected reservation invoice is £240 payable to Foxbarrel Residential Ltd, credited toward rent if an agreement is entered, with the stated refund conditions. Remaining limits: the £2,160 all-in figure is still an estimate, and the new Threadleaf quote is subject to availability.
> Threadleaf is not booked. Its current £345 quote can be cancelled for a refund by 2027-03-03 15:00 if booked.

Attribution: `scalar_surface_form_only`. Original exact normalized match remains false; supported wording variation alone is not a prompt-format violation.

## Reproducibility and limits

Machine-readable records, exact JSON pointers, answer SHA-256 hashes, original fact records and frozen expected anchors are in `scalar-source-review.json`. The rental source SHA-256 is `52eba1f2998a3da1bfe23a819af4cd439673afe180988976e5452a179e3c40c8`. The fixed scope includes only the named completed groups and only failed scalar checks; it makes no claims about other groups, passing fields, whole-answer quality or experimental superiority.

Source manifests:

- `bench/results/ablation-2026-09-09/live-v1/rental-cases.json`: SHA-256 `52eba1f2998a3da1bfe23a819af4cd439673afe180988976e5452a179e3c40c8`.
- `bench/results/ablation-2026-09-09/live-v1/retrieval-cases.json`: SHA-256 `434c78c5dd73d4e1224892a6701fd4197936e89ae1eab0885b3812e6a2649ae6`.
