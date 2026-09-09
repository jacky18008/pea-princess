# Generated numerical tables

Primary model-judge labels; source reviews are separate. All pipeline costs include required automatic generation/update. Arm totals share generator calls and must not be summed.

| Experiment | Arm | Answer tokens | Generator tokens | Pipeline tokens | Δ pipeline vs baseline | Findings | Scalars | Critical misses |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rental | full | 228,626 | 0 | 228,626 | +0.00% | 46/60 | 59/72 | 5 |
| rental | prose | 212,947 | 237,459 | 450,406 | +97.01% | 41/60 | 63/72 | 5 |
| rental | state | 254,078 | 237,459 | 491,537 | +115.00% | 38/60 | 59/72 | 9 |
| rental | state_no_sources | 241,805 | 237,459 | 479,264 | +109.63% | 41/60 | 58/72 | 7 |
| rental | state_no_updates | 246,215 | 237,459 | 483,674 | +111.56% | 43/60 | 58/72 | 5 |
| rental | state_neither | 233,499 | 237,459 | 470,958 | +105.99% | 42/60 | 58/72 | 6 |
| retrieval | raw_full | 114,923 | 0 | 114,923 | +0.00% | 27/30 | 34/36 | 0 |
| retrieval | full | 116,557 | 106,853 | 223,410 | +94.40% | 29/30 | 34/36 | 0 |
| retrieval | summary | 95,402 | 106,853 | 202,255 | +75.99% | 23/30 | 28/36 | 0 |
| retrieval | lexical | 106,476 | 106,853 | 213,329 | +85.63% | 26/30 | 32/36 | 0 |
| retrieval | adaptive | 163,811 | 106,853 | 270,664 | +135.52% | 26/30 | 32/36 | 0 |
| retrieval | oracle | 107,197 | 106,853 | 214,050 | +86.26% | 28/30 | 34/36 | 0 |

## Per-answer results

Incremental pipeline tokens add only the generation/update introduced at that turn. Summed per arm, these equal the union-of-dependencies pipeline total.

| Answer | Answer tokens | Incremental pipeline | Findings | Scalars | Critical misses |
|---|---:|---:|---:|---:|---|
| E1-long-adaptive | 15,940 | 35,652 | 3/5 | 5/6 | — |
| E1-long-full | 21,241 | 40,953 | 5/5 | 6/6 | — |
| E1-long-lexical | 18,583 | 38,295 | 4/5 | 5/6 | — |
| E1-long-oracle | 18,780 | 38,492 | 5/5 | 6/6 | — |
| E1-long-raw_full | 21,033 | 21,033 | 5/5 | 6/6 | — |
| E1-long-summary | 15,949 | 35,661 | 3/5 | 5/6 | — |
| E1-short-adaptive | 32,709 | 48,935 | 5/5 | 5/6 | — |
| E1-short-full | 17,712 | 33,938 | 5/5 | 6/6 | — |
| E1-short-lexical | 16,876 | 33,102 | 4/5 | 5/6 | — |
| E1-short-oracle | 17,081 | 33,307 | 5/5 | 6/6 | — |
| E1-short-raw_full | 17,510 | 17,510 | 5/5 | 6/6 | — |
| E1-short-summary | 15,885 | 32,111 | 2/5 | 4/6 | — |
| E2-long-adaptive | 34,338 | 53,753 | 4/5 | 6/6 | — |
| E2-long-full | 20,981 | 40,396 | 4/5 | 6/6 | — |
| E2-long-lexical | 18,338 | 37,753 | 4/5 | 6/6 | — |
| E2-long-oracle | 18,658 | 38,073 | 4/5 | 6/6 | — |
| E2-long-raw_full | 20,663 | 20,663 | 3/5 | 6/6 | — |
| E2-long-summary | 15,814 | 35,229 | 5/5 | 6/6 | — |
| E2-short-adaptive | 32,435 | 48,546 | 5/5 | 6/6 | — |
| E2-short-full | 17,633 | 33,744 | 5/5 | 6/6 | — |
| E2-short-lexical | 16,775 | 32,886 | 5/5 | 6/6 | — |
| E2-short-oracle | 16,998 | 33,109 | 5/5 | 6/6 | — |
| E2-short-raw_full | 17,409 | 17,409 | 5/5 | 6/6 | — |
| E2-short-summary | 15,734 | 31,845 | 5/5 | 5/6 | — |
| E3-long-adaptive | 15,892 | 35,211 | 5/5 | 5/6 | — |
| E3-long-full | 21,096 | 40,415 | 5/5 | 5/6 | — |
| E3-long-lexical | 18,721 | 38,040 | 5/5 | 5/6 | — |
| E3-long-oracle | 18,722 | 38,041 | 4/5 | 5/6 | — |
| E3-long-raw_full | 20,933 | 20,933 | 5/5 | 5/6 | — |
| E3-long-summary | 15,943 | 35,262 | 5/5 | 5/6 | — |
| E3-short-adaptive | 32,497 | 48,567 | 4/5 | 5/6 | — |
| E3-short-full | 17,894 | 33,964 | 5/5 | 5/6 | — |
| E3-short-lexical | 17,183 | 33,253 | 4/5 | 5/6 | — |
| E3-short-oracle | 16,958 | 33,028 | 5/5 | 5/6 | — |
| E3-short-raw_full | 17,375 | 17,375 | 4/5 | 5/6 | — |
| E3-short-summary | 16,077 | 32,147 | 3/5 | 3/6 | — |
| S1-r1-T1-full | 18,846 | 18,846 | 4/5 | 6/6 | — |
| S1-r1-T1-prose | 17,700 | 35,858 | 4/5 | 6/6 | — |
| S1-r1-T1-state | 21,119 | 39,277 | 4/5 | 6/6 | — |
| S1-r1-T1-state_neither | 19,373 | 37,531 | 4/5 | 6/6 | — |
| S1-r1-T1-state_no_sources | 20,025 | 38,183 | 4/5 | 6/6 | — |
| S1-r1-T1-state_no_updates | 20,579 | 38,737 | 4/5 | 6/6 | — |
| S1-r1-T2-full | 19,459 | 19,459 | 4/5 | 6/6 | — |
| S1-r1-T2-prose | 17,997 | 39,820 | 4/5 | 6/6 | — |
| S1-r1-T2-state | 21,633 | 43,456 | 3/5 | 6/6 | S1-T2-F1 |
| S1-r1-T2-state_neither | 19,866 | 41,689 | 3/5 | 6/6 | S1-T2-F1 |
| S1-r1-T2-state_no_sources | 20,580 | 42,403 | 3/5 | 6/6 | S1-T2-F1 |
| S1-r1-T2-state_no_updates | 21,018 | 42,841 | 3/5 | 6/6 | — |
| S1-r2-T1-full | 18,932 | 18,932 | 5/5 | 6/6 | — |
| S1-r2-T1-prose | 17,637 | 35,887 | 4/5 | 6/6 | — |
| S1-r2-T1-state | 21,311 | 39,561 | 1/5 | 6/6 | S1-T1-F2 |
| S1-r2-T1-state_neither | 19,495 | 37,745 | 4/5 | 6/6 | — |
| S1-r2-T1-state_no_sources | 20,168 | 38,418 | 5/5 | 6/6 | — |
| S1-r2-T1-state_no_updates | 20,439 | 38,689 | 4/5 | 6/6 | — |
| S1-r2-T2-full | 19,422 | 19,422 | 3/5 | 6/6 | — |
| S1-r2-T2-prose | 17,979 | 39,711 | 3/5 | 6/6 | S1-T2-F1 |
| S1-r2-T2-state | 21,671 | 43,403 | 2/5 | 6/6 | S1-T2-F1 |
| S1-r2-T2-state_neither | 19,840 | 41,572 | 2/5 | 6/6 | S1-T2-F1 |
| S1-r2-T2-state_no_sources | 20,485 | 42,217 | 2/5 | 6/6 | S1-T2-F1 |
| S1-r2-T2-state_no_updates | 20,825 | 42,557 | 2/5 | 6/6 | S1-T2-F1 |
| S2-r1-T1-full | 18,676 | 18,676 | 5/5 | 5/6 | — |
| S2-r1-T1-prose | 17,488 | 35,521 | 5/5 | 5/6 | — |
| S2-r1-T1-state | 20,830 | 38,863 | 5/5 | 6/6 | — |
| S2-r1-T1-state_neither | 19,246 | 37,279 | 5/5 | 5/6 | — |
| S2-r1-T1-state_no_sources | 20,035 | 38,068 | 5/5 | 5/6 | — |
| S2-r1-T1-state_no_updates | 20,296 | 38,329 | 5/5 | 5/6 | — |
| S2-r1-T2-full | 19,399 | 19,399 | 4/5 | 6/6 | S2-T2-F2 |
| S2-r1-T2-prose | 18,017 | 39,617 | 4/5 | 5/6 | S2-T2-F2 |
| S2-r1-T2-state | 21,376 | 42,976 | 4/5 | 6/6 | S2-T2-F2 |
| S2-r1-T2-state_neither | 19,655 | 41,255 | 5/5 | 5/6 | — |
| S2-r1-T2-state_no_sources | 20,331 | 41,931 | 4/5 | 5/6 | S2-T2-F2 |
| S2-r1-T2-state_no_updates | 20,724 | 42,324 | 5/5 | 5/6 | — |
| S2-r2-T1-full | 18,657 | 18,657 | 5/5 | 6/6 | — |
| S2-r2-T1-prose | 17,385 | 35,151 | 3/5 | 5/6 | — |
| S2-r2-T1-state | 20,545 | 38,311 | 5/5 | 4/6 | — |
| S2-r2-T1-state_neither | 19,024 | 36,790 | 5/5 | 5/6 | — |
| S2-r2-T1-state_no_sources | 19,767 | 37,533 | 5/5 | 4/6 | — |
| S2-r2-T1-state_no_updates | 20,122 | 37,888 | 5/5 | 5/6 | — |
| S2-r2-T2-full | 19,430 | 19,430 | 5/5 | 5/6 | — |
| S2-r2-T2-prose | 17,953 | 38,985 | 5/5 | 5/6 | — |
| S2-r2-T2-state | 21,156 | 42,188 | 4/5 | 5/6 | S2-T2-F2 |
| S2-r2-T2-state_neither | 19,488 | 40,520 | 5/5 | 5/6 | — |
| S2-r2-T2-state_no_sources | 20,227 | 41,259 | 4/5 | 6/6 | S2-T2-F2 |
| S2-r2-T2-state_no_updates | 20,619 | 41,651 | 5/5 | 5/6 | — |
| S3-r1-T1-full | 18,566 | 18,566 | 3/5 | 3/6 | S3-T1-F2 |
| S3-r1-T1-prose | 17,349 | 35,515 | 3/5 | 5/6 | — |
| S3-r1-T1-state | 20,864 | 39,030 | 3/5 | 3/6 | S3-T1-F2 |
| S3-r1-T1-state_neither | 19,133 | 37,299 | 3/5 | 3/6 | S3-T1-F2 |
| S3-r1-T1-state_no_sources | 19,722 | 37,888 | 2/5 | 3/6 | S3-T1-F2 |
| S3-r1-T1-state_no_updates | 20,196 | 38,362 | 2/5 | 3/6 | S3-T1-F2 |
| S3-r1-T2-full | 19,396 | 19,396 | 3/5 | 4/6 | S3-T2-F2 |
| S3-r1-T2-prose | 18,126 | 39,762 | 2/5 | 5/6 | S3-T2-F2 |
| S3-r1-T2-state | 21,467 | 43,103 | 3/5 | 4/6 | S3-T2-F2 |
| S3-r1-T2-state_neither | 19,789 | 41,425 | 2/5 | 4/6 | S3-T2-F2 |
| S3-r1-T2-state_no_sources | 20,485 | 42,121 | 3/5 | 4/6 | — |
| S3-r1-T2-state_no_updates | 20,736 | 42,372 | 3/5 | 4/6 | S3-T2-F2 |
| S3-r2-T1-full | 18,491 | 18,491 | 3/5 | 3/6 | S3-T1-F2 |
| S3-r2-T1-prose | 17,334 | 35,383 | 1/5 | 4/6 | S3-T1-F2 |
| S3-r2-T1-state | 20,748 | 38,797 | 2/5 | 3/6 | S3-T1-F2 |
| S3-r2-T1-state_neither | 18,967 | 37,016 | 1/5 | 3/6 | S3-T1-F2 |
| S3-r2-T1-state_no_sources | 19,649 | 37,698 | 1/5 | 3/6 | S3-T1-F2 |
| S3-r2-T1-state_no_updates | 20,082 | 38,131 | 2/5 | 3/6 | S3-T1-F2 |
| S3-r2-T2-full | 19,352 | 19,352 | 2/5 | 3/6 | S3-T2-F2 |
| S3-r2-T2-prose | 17,982 | 39,196 | 3/5 | 5/6 | S3-T2-F2 |
| S3-r2-T2-state | 21,358 | 42,572 | 2/5 | 4/6 | S3-T2-F2 |
| S3-r2-T2-state_neither | 19,623 | 40,837 | 3/5 | 4/6 | S3-T2-F2 |
| S3-r2-T2-state_no_sources | 20,331 | 41,545 | 3/5 | 4/6 | S3-T2-F2 |
| S3-r2-T2-state_no_updates | 20,579 | 41,793 | 3/5 | 4/6 | S3-T2-F2 |

## Memory metadata factorial effects

Positive quality effects indicate more findings/scalars when metadata is present; positive token effects indicate more usage. Counts are per answer, not percentage points. These metadata-consumption effects use a common rich updater.

| Turn stratum | Metric | Source effect | Replacement effect | Interaction |
|---|---|---:|---:|---:|
| all | required_met | -0.083 | -0.250 | -0.333 |
| all | scalar_passed | 0.042 | 0.042 | 0.083 |
| all | answer_tokens | 1041.208 | 673.708 | -36.917 |
| all | incremental_pipeline_tokens | 1041.208 | 673.708 | -36.917 |
| T1 | required_met | -0.167 | -0.167 | -0.333 |
| T1 | scalar_passed | 0.083 | -0.083 | 0.167 |
| T1 | answer_tokens | 1043.917 | 652.583 | -70.833 |
| T1 | incremental_pipeline_tokens | 1043.917 | 652.583 | -70.833 |
| T2 | required_met | 0.000 | -0.333 | -0.333 |
| T2 | scalar_passed | 0.000 | 0.167 | 0.000 |
| T2 | answer_tokens | 1038.500 | 694.833 | -3.000 |
| T2 | incremental_pipeline_tokens | 1038.500 | 694.833 | -3.000 |

## Retrieval mechanism contrasts

After minus before; critical criterion IDs belong to their own turns.

| Before | After | Δ answer tokens | Δ incremental pipeline | Δ findings | Δ scalars |
|---|---|---:|---:|---:|---:|
| E1-long-raw_full | E1-long-full | +208 | +19,920 | +0 | +0 |
| E1-long-full | E1-long-summary | -5,292 | -5,292 | -2 | -1 |
| E1-long-summary | E1-long-lexical | +2,634 | +2,634 | +1 | +0 |
| E1-long-lexical | E1-long-oracle | +197 | +197 | +1 | +1 |
| E1-long-adaptive | E1-long-oracle | +2,840 | +2,840 | +2 | +1 |
| E1-short-raw_full | E1-short-full | +202 | +16,428 | +0 | +0 |
| E1-short-full | E1-short-summary | -1,827 | -1,827 | -3 | -2 |
| E1-short-summary | E1-short-lexical | +991 | +991 | +2 | +1 |
| E1-short-lexical | E1-short-oracle | +205 | +205 | +1 | +1 |
| E1-short-adaptive | E1-short-oracle | -15,628 | -15,628 | +0 | +1 |
| E2-long-raw_full | E2-long-full | +318 | +19,733 | +1 | +0 |
| E2-long-full | E2-long-summary | -5,167 | -5,167 | +1 | +0 |
| E2-long-summary | E2-long-lexical | +2,524 | +2,524 | -1 | +0 |
| E2-long-lexical | E2-long-oracle | +320 | +320 | +0 | +0 |
| E2-long-adaptive | E2-long-oracle | -15,680 | -15,680 | +0 | +0 |
| E2-short-raw_full | E2-short-full | +224 | +16,335 | +0 | +0 |
| E2-short-full | E2-short-summary | -1,899 | -1,899 | +0 | -1 |
| E2-short-summary | E2-short-lexical | +1,041 | +1,041 | +0 | +1 |
| E2-short-lexical | E2-short-oracle | +223 | +223 | +0 | +0 |
| E2-short-adaptive | E2-short-oracle | -15,437 | -15,437 | +0 | +0 |
| E3-long-raw_full | E3-long-full | +163 | +19,482 | +0 | +0 |
| E3-long-full | E3-long-summary | -5,153 | -5,153 | +0 | +0 |
| E3-long-summary | E3-long-lexical | +2,778 | +2,778 | +0 | +0 |
| E3-long-lexical | E3-long-oracle | +1 | +1 | -1 | +0 |
| E3-long-adaptive | E3-long-oracle | +2,830 | +2,830 | -1 | +0 |
| E3-short-raw_full | E3-short-full | +519 | +16,589 | +1 | +0 |
| E3-short-full | E3-short-summary | -1,817 | -1,817 | -2 | -2 |
| E3-short-summary | E3-short-lexical | +1,106 | +1,106 | +1 | +2 |
| E3-short-lexical | E3-short-oracle | -225 | -225 | +1 | +0 |
| E3-short-adaptive | E3-short-oracle | -15,539 | -15,539 | +1 | +0 |

## Rental repeat contrasts

After minus before; critical criterion IDs belong to their own turns.

| Before | After | Δ answer tokens | Δ incremental pipeline | Δ findings | Δ scalars |
|---|---|---:|---:|---:|---:|
| S1-r1-T1-full | S1-r2-T1-full | +86 | +86 | +1 | +0 |
| S1-r1-T2-full | S1-r2-T2-full | -37 | -37 | -1 | +0 |
| S1-r1-T1-prose | S1-r2-T1-prose | -63 | +29 | +0 | +0 |
| S1-r1-T2-prose | S1-r2-T2-prose | -18 | -109 | -1 | +0 |
| S1-r1-T1-state | S1-r2-T1-state | +192 | +284 | -3 | +0 |
| S1-r1-T2-state | S1-r2-T2-state | +38 | -53 | -1 | +0 |
| S1-r1-T1-state_no_sources | S1-r2-T1-state_no_sources | +143 | +235 | +1 | +0 |
| S1-r1-T2-state_no_sources | S1-r2-T2-state_no_sources | -95 | -186 | -1 | +0 |
| S1-r1-T1-state_no_updates | S1-r2-T1-state_no_updates | -140 | -48 | +0 | +0 |
| S1-r1-T2-state_no_updates | S1-r2-T2-state_no_updates | -193 | -284 | -1 | +0 |
| S1-r1-T1-state_neither | S1-r2-T1-state_neither | +122 | +214 | +0 | +0 |
| S1-r1-T2-state_neither | S1-r2-T2-state_neither | -26 | -117 | -1 | +0 |
| S2-r1-T1-full | S2-r2-T1-full | -19 | -19 | +0 | +1 |
| S2-r1-T2-full | S2-r2-T2-full | +31 | +31 | +1 | -1 |
| S2-r1-T1-prose | S2-r2-T1-prose | -103 | -370 | -2 | +0 |
| S2-r1-T2-prose | S2-r2-T2-prose | -64 | -632 | +1 | +0 |
| S2-r1-T1-state | S2-r2-T1-state | -285 | -552 | +0 | -2 |
| S2-r1-T2-state | S2-r2-T2-state | -220 | -788 | +0 | -1 |
| S2-r1-T1-state_no_sources | S2-r2-T1-state_no_sources | -268 | -535 | +0 | -1 |
| S2-r1-T2-state_no_sources | S2-r2-T2-state_no_sources | -104 | -672 | +0 | +1 |
| S2-r1-T1-state_no_updates | S2-r2-T1-state_no_updates | -174 | -441 | +0 | +0 |
| S2-r1-T2-state_no_updates | S2-r2-T2-state_no_updates | -105 | -673 | +0 | +0 |
| S2-r1-T1-state_neither | S2-r2-T1-state_neither | -222 | -489 | +0 | +0 |
| S2-r1-T2-state_neither | S2-r2-T2-state_neither | -167 | -735 | +0 | +0 |
| S3-r1-T1-full | S3-r2-T1-full | -75 | -75 | +0 | +0 |
| S3-r1-T2-full | S3-r2-T2-full | -44 | -44 | -1 | -1 |
| S3-r1-T1-prose | S3-r2-T1-prose | -15 | -132 | -2 | -1 |
| S3-r1-T2-prose | S3-r2-T2-prose | -144 | -566 | +1 | +0 |
| S3-r1-T1-state | S3-r2-T1-state | -116 | -233 | -1 | +0 |
| S3-r1-T2-state | S3-r2-T2-state | -109 | -531 | -1 | +0 |
| S3-r1-T1-state_no_sources | S3-r2-T1-state_no_sources | -73 | -190 | -1 | +0 |
| S3-r1-T2-state_no_sources | S3-r2-T2-state_no_sources | -154 | -576 | +0 | +0 |
| S3-r1-T1-state_no_updates | S3-r2-T1-state_no_updates | -114 | -231 | +0 | +0 |
| S3-r1-T2-state_no_updates | S3-r2-T2-state_no_updates | -157 | -579 | +0 | +0 |
| S3-r1-T1-state_neither | S3-r2-T1-state_neither | -166 | -283 | -2 | +0 |
| S3-r1-T2-state_neither | S3-r2-T2-state_neither | -166 | -588 | +1 | +0 |

## Rental turn progression (different questions and criteria)

After minus before; critical criterion IDs belong to their own turns.

| Before | After | Δ answer tokens | Δ incremental pipeline | Δ findings | Δ scalars |
|---|---|---:|---:|---:|---:|
| S1-r1-T1-full | S1-r1-T2-full | +613 | +613 | +0 | +0 |
| S1-r2-T1-full | S1-r2-T2-full | +490 | +490 | -2 | +0 |
| S1-r1-T1-prose | S1-r1-T2-prose | +297 | +3,962 | +0 | +0 |
| S1-r2-T1-prose | S1-r2-T2-prose | +342 | +3,824 | -1 | +0 |
| S1-r1-T1-state | S1-r1-T2-state | +514 | +4,179 | -1 | +0 |
| S1-r2-T1-state | S1-r2-T2-state | +360 | +3,842 | +1 | +0 |
| S1-r1-T1-state_no_sources | S1-r1-T2-state_no_sources | +555 | +4,220 | -1 | +0 |
| S1-r2-T1-state_no_sources | S1-r2-T2-state_no_sources | +317 | +3,799 | -3 | +0 |
| S1-r1-T1-state_no_updates | S1-r1-T2-state_no_updates | +439 | +4,104 | -1 | +0 |
| S1-r2-T1-state_no_updates | S1-r2-T2-state_no_updates | +386 | +3,868 | -2 | +0 |
| S1-r1-T1-state_neither | S1-r1-T2-state_neither | +493 | +4,158 | -1 | +0 |
| S1-r2-T1-state_neither | S1-r2-T2-state_neither | +345 | +3,827 | -2 | +0 |
| S2-r1-T1-full | S2-r1-T2-full | +723 | +723 | -1 | +1 |
| S2-r2-T1-full | S2-r2-T2-full | +773 | +773 | +0 | -1 |
| S2-r1-T1-prose | S2-r1-T2-prose | +529 | +4,096 | -1 | +0 |
| S2-r2-T1-prose | S2-r2-T2-prose | +568 | +3,834 | +2 | +0 |
| S2-r1-T1-state | S2-r1-T2-state | +546 | +4,113 | -1 | +0 |
| S2-r2-T1-state | S2-r2-T2-state | +611 | +3,877 | -1 | +1 |
| S2-r1-T1-state_no_sources | S2-r1-T2-state_no_sources | +296 | +3,863 | -1 | +0 |
| S2-r2-T1-state_no_sources | S2-r2-T2-state_no_sources | +460 | +3,726 | -1 | +2 |
| S2-r1-T1-state_no_updates | S2-r1-T2-state_no_updates | +428 | +3,995 | +0 | +0 |
| S2-r2-T1-state_no_updates | S2-r2-T2-state_no_updates | +497 | +3,763 | +0 | +0 |
| S2-r1-T1-state_neither | S2-r1-T2-state_neither | +409 | +3,976 | +0 | +0 |
| S2-r2-T1-state_neither | S2-r2-T2-state_neither | +464 | +3,730 | +0 | +0 |
| S3-r1-T1-full | S3-r1-T2-full | +830 | +830 | +0 | +1 |
| S3-r2-T1-full | S3-r2-T2-full | +861 | +861 | -1 | +0 |
| S3-r1-T1-prose | S3-r1-T2-prose | +777 | +4,247 | -1 | +0 |
| S3-r2-T1-prose | S3-r2-T2-prose | +648 | +3,813 | +2 | +1 |
| S3-r1-T1-state | S3-r1-T2-state | +603 | +4,073 | +0 | +1 |
| S3-r2-T1-state | S3-r2-T2-state | +610 | +3,775 | +0 | +1 |
| S3-r1-T1-state_no_sources | S3-r1-T2-state_no_sources | +763 | +4,233 | +1 | +1 |
| S3-r2-T1-state_no_sources | S3-r2-T2-state_no_sources | +682 | +3,847 | +2 | +1 |
| S3-r1-T1-state_no_updates | S3-r1-T2-state_no_updates | +540 | +4,010 | +1 | +1 |
| S3-r2-T1-state_no_updates | S3-r2-T2-state_no_updates | +497 | +3,662 | +1 | +1 |
| S3-r1-T1-state_neither | S3-r1-T2-state_neither | +656 | +4,126 | -1 | +1 |
| S3-r2-T1-state_neither | S3-r2-T2-state_neither | +656 | +3,821 | +2 | +1 |
