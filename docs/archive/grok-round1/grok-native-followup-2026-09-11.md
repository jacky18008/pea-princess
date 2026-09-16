# Grok Bot follow-up: operator blocked before a valid quality sample

The requested current-skill test was attempted by a dedicated operator subagent in the native Grok Bot app. **One invalid setup submission was observed; zero valid conversation-quality samples were obtained.** This is an input-automation failure, not evidence that Grok failed the rental task or encountered a rate limit.

## Frozen setup and observation

The predeclared plan was a six-turn regression conversation covering an informative opening, supplied A/B adverts, a lower rent ceiling, a candidate-specific conditional exception, an EPC area that fails that exception, and returning to the same chat. The evidence was deliberately supplied/simulated test material; no fresh listing availability claim was intended. The package contained 92 public files from the pre-rename version based on commit `e02ea8add1a1fe2ea7366f8c3e38db53cecb7cc2`.

- Archive SHA-256: `fcc693dba1c5d4b21c0c5dc62fc7f9ee5161cbabbc90f7c23ee4926648226d1c`.
- Expected SKILL.md SHA-256: `4aa1e8c6b2754de2ec394efc024e2daf315a5f64239597828f8c218f6eb4dfc9`.
- Native app: `/Applications/Grok Bot.app`, bundle `com.anysphere.sand`.
- Model, effort and token usage: **unknown**, not zero. No model picker or direct usage counter was observed on the inspected surface.

The ZIP attachment was accepted. Native paste timed out; subsequent input operations lost text, and an incomplete setup message was unexpectedly submitted. The exact cause of submission is uncertain. Grok noticed the truncated instructions and asked how to continue. It reported unpacking 92 files and gave the expected skill hash, but no downloaded bytes independently confirmed its installation.

The original run stopped. A separately authorized controlled recovery attempted one short single-line question, with exact input verification required before sending. `setValue` left the composer empty and plain-text paste timed out. No second message was sent. Final observed state was replied, with a pending native question and an empty composer.

The new Bot also mentioned the older Pea Princess Test. Creating a new Bot therefore did not establish a verified isolated context; no conclusion about its source or extent is warranted from that mention alone.

## Severity and conclusion

| Finding | Severity for testing | Consequence |
| --- | --- | --- |
| Native input corruption and unintended submission | High | Verify exact composer bytes before sending; stop this automation route when verification fails |
| New Bot refers to prior test context | Medium | Establish workspace/context provenance before claiming a clean run |
| No provider model/usage telemetry | Measurement limitation | Exclude from token-efficiency comparisons; do not infer underlying call count from messages |
| Matching hash is only a Bot statement | Evidence limitation | Require downloaded artifact verification before asserting installed file/state continuity |

An independent Astra review agrees that no reply-quality score is justified. The observed truncated-input response cannot stand in for the planned opening. A future retry should first demonstrate reliable native input and context isolation, then record a new package/version and run the frozen conversation. The skill was subsequently renamed to `pea-princess`; this record deliberately retains its historical `vet-flat` archive identity.

Exact intended/sent messages, replies, native accessibility observations, metadata and the package manifest remain private in `.pea-playground/grokbot-native-20260911-v1/`. No raw account UI or unrelated history is included in this public report.
