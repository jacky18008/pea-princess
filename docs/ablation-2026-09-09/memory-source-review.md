# Selective rental memory source review

**Post-hoc selective AI source review, not human ground truth.** The eight failed exact-quote checks all concern supported facts attributed to the correct user message. They remain invalid exact quotations. No frozen checks or raw records were changed.

I inspected stored checks in all 12 rental memories and reproduced the exact string-match results against canonical user sources. Those files contain 552 fact-record occurrences; only the eight flagged records received this semantic review. This does not establish complete memory recall or semantic accuracy, including for the 544 records that passed exact membership. Summary prose, all status/qualification choices and all omitted facts were not audited.

The source boundary is generation time: T1-stage memory uses user history only, and T2-stage memory may additionally use prior T1. The later T2 question is excluded. In particular, an absence recorded before S3’s future completed-check update is not retroactively an unsupported absence. This offline review used no model CLI/API calls and is outside benchmark CLI token totals. The earlier blinded rental review is unchanged.

## Results and lineage

| Original record | Propagated unchanged record | Quote defect | Semantic/source support |
| --- | --- | --- | --- |
| S2-r1-T1-group-memory / F46 | S2-r1-T2-group-memory / F46 | “no guaranteed repair date” rewrites a coordinated negative | Supported by S2 U5 |
| S3-r1-T1-group-memory / f34 | S3-r1-T2-group-memory / f34 | Ellipsis joins parts of the recipient-relationship sentence | Supported by S3 U3 |
| S3-r1-T1-group-memory / f40 | S3-r1-T2-group-memory / f40 | Ellipsis joins parts of the promised-certificate sentence | Supported by S3 U4 |
| S3-r2-T1-group-memory / F33 | S3-r2-T2-group-memory / F33 | Same relationship-ellipsis pattern in another initial run | Supported by S3 U3 |

There are **four original defective fact records in three initial memory calls, plus four unchanged propagated occurrences**. The T2 files declare their respective T1 memory as an input dependency, and each selected fact object is identical to that earlier record. This is record-level evidence of carry-forward, without an inference about hidden model reasoning. There are three distinct quote/source patterns: the relationship ellipsis appears in two separate initial S3 calls. Consequently, eight occurrences are not eight independent generation errors; neither are the four originating records claimed to be statistically independent.

## Source findings

S2 U5 says: “My current packet contains no agreed accessibility work or guaranteed repair date”. The negative governs both coordinated objects. F46’s value, “none in packet,” correctly captures absence of a guaranteed repair date. Its alleged quote, “no guaranteed repair date,” relocates the negative across omitted words and is not contiguous source text. This is a supported paraphrase presented in an exact-quote field. Prior T1 adds the zero-step requirement, not a repair guarantee.

S3 U3 says: “The packet does not name the owner, provide letting authority or explain how this person is related to the company.” The stored “does not ... explain how this person is related to the company” accurately joins two pieces of that sentence and preserves its negation, but the inserted ellipsis is absent from the source. Both r1 f34 (“unexplained”) and r2 F33 (“absent”) are supported as statements about the missing packet evidence. The recipient’s actual real-world relationship is not inferred.

S3 U4 says: “The agent says an updated certificate and an owner letter are being prepared, but neither has arrived.” The quote “updated certificate ... being prepared, but neither has arrived” omits the intervening owner-letter phrase and inserts an ellipsis. The certificate’s “not received” state is explicit in the source. Prior T1 states no new document accompanied the deadline, so it does not cure either missing-document condition. Future T2 is not used.

Among these eight selected occurrences, the review finds **zero unsupported fact values and zero wrong source attributions**. That conclusion qualifies the meaning of the exact-quote failures; it does not erase them or validate the remainder of each memory. A quote can preserve meaning while violating the required verbatim source contract.

## Occurrence audit

The JSON contains one row per call ID + fact ID occurrence, preserving the original check, quote, value, source ID, exact source anchors with character offsets, generation boundary, semantic judgment and lineage. Each row keeps `recomputed_exact_quote_match=false` and `semantic_supported=true`.

- `S2-r1-T1-group-memory:F46`: non_verbatim_negative_coordination_paraphrase; original_in_initial_memory; source `U5`; value `none in packet`; semantic support **true**.
- `S2-r1-T2-group-memory:F46`: non_verbatim_negative_coordination_paraphrase; propagated_unchanged; source `U5`; value `none in packet`; semantic support **true**.
- `S3-r1-T1-group-memory:f34`: non_verbatim_joined_excerpts_with_ellipsis; original_in_initial_memory; source `U3`; value `unexplained`; semantic support **true**.
- `S3-r1-T1-group-memory:f40`: non_verbatim_joined_excerpts_with_ellipsis; original_in_initial_memory; source `U4`; value `not received`; semantic support **true**.
- `S3-r1-T2-group-memory:f34`: non_verbatim_joined_excerpts_with_ellipsis; propagated_unchanged; source `U3`; value `unexplained`; semantic support **true**.
- `S3-r1-T2-group-memory:f40`: non_verbatim_joined_excerpts_with_ellipsis; propagated_unchanged; source `U4`; value `not received`; semantic support **true**.
- `S3-r2-T1-group-memory:F33`: non_verbatim_joined_excerpts_with_ellipsis; original_in_initial_memory; source `U3`; value `absent`; semantic support **true**.
- `S3-r2-T2-group-memory:F33`: non_verbatim_joined_excerpts_with_ellipsis; propagated_unchanged; source `U3`; value `absent`; semantic support **true**.
