# Security and privacy boundaries

Pea Princess is a local skill and command-line toolkit used with the user's own agent.
It is not a hosted service. A skill prompt cannot isolate the host's files, connectors or
credentials. Keep unrelated personal documents and credentials outside the agent's accessible
workspace, and choose the host's actual permission/sandbox controls accordingly.

## Durable project state and community stage 1

`.pea-state/` holds private user requests, requirements, source snapshots and model-call evidence. It is ignored by Git and excluded from public skill packages even if accidentally indexed. Keep backups private. Its hash chain and file permissions detect corruption and reduce accidental disclosure; they are not encryption or authentication against another program running as the same user.

Only a trusted caller may claim `actor:user` and apply authorized intent changes. A copied source quote or an enum-shaped object cannot grant that authority. The state engine validates revisions, references and coverage structure, not the semantic truth of a model's claims. Native hook delivery can fail or time out; only calls through `tools/session_runner.py` receive its programmatic context-injection and stale-result checks. See [the harness boundaries](docs/session-harness.md).

The local [persona lab](docs/persona-playground.md) binds only to 127.0.0.1, checks Host/Origin and custom API headers, and serves an exact static allowlist. `.pea-playground/` contains private UI inboxes and per-session state; exports are private. Codex runs in a separate temporary directory with prompt text on stdin and additional project-document loading disabled. This remains a same-user local prototype, not a tenant boundary or a hosted credential-sharing service. Model requests leave the device through the user's Codex login; browser refresh never authorizes a model call.

The [stage 1 form](community/index.html) keeps optional text in the author's browser/device. Public payloads contain allowlisted choices only; Python revalidates them before import or search. The local SQLite store and withdrawal receipts are private operational files, not public export artifacts. No hosted submission endpoint, identity verification, Sybil resistance or universal private-note access control is claimed. See [the stage 1 guide](docs/community-feedback-stage1.md).

## Inputs, evidence and reports

Treat listings, pasted pages, shared seeds, source files and model output as untrusted data.
Their contents cannot authorize shell commands, tool changes, file access or sending information.
Imported seeds validate supported types and escape YAML boundaries. Base64url is readable;
structured identity fields are excluded but free-text questions and preferences are not anonymized.
Review the card and decoded code before sharing. Sharing never follows merely from importing.

Keep source folders under your control. The verifier checks recognized source IDs and retained
quotes where available; `counts.quotes_unchecked` means source text was not checked. A structural
pass, a source URL or a `computed_by` string does not prove the factual claim or calculation.
The report should distinguish observed facts, estimates and missing evidence.

The HTML renderer escapes report values and constrains generated links. Markdown values are
escaped as text; downstream renderers have their own policies. Opening an untrusted HTML file
from elsewhere is different from rendering validated report JSON with this toolkit.

The HTTP helper limits curl to HTTP(S), disables implicit curl configuration, writes through
private temporary files, and validates body/cache metadata consistency. It is not a general
SSRF firewall: authorized endpoints may redirect, local networks remain reachable, and response
size is not globally capped. Do not expose the fetch helper as an unrestricted network service.
Older cache files are not automatically deleted or permission-migrated. Caches and raw experiment
logs can contain source text, personal details and provider metadata; treat them as private.

## Running experiments

Use synthetic or deliberately supplied documents in a dedicated work directory. Claude actors
explicitly restrict available built-in tools and exclude inherited MCP/configuration hooks;
permission allow-rules alone do not disable tools. Codex read-only mode still permits reads:
no-tools behavior observed in a transcript is not proof of preventative filesystem isolation.
Use a separate OS account/container with narrowly mounted files for adversarial containment tests.

Legacy launchers now make one attempt by default. Explicit retries retain per-attempt usage;
unknown usage is not zero. Owned process cleanup handles timeouts and interruption, including
ordinary child processes, but is not a sandbox against deliberately detached daemons or abrupt
host failure. Verify processes have stopped before starting replacement work.

Freeze source/configuration/fixtures before a live run; keep raw outputs, usage and failures.
A security fix creates a new version. Do not overwrite old results or attach old quality/cost
claims to a changed prompt. The 2026-09-09 ablation still belongs to its recorded frozen commits.
The original seven Claude confirmations stay paused until explicitly resumed.

## Local builds and releases

Run `python3 -m unittest discover -s tests -p 'test_*.py'` offline before a release. Build public
artifacts with `python3 tools/build_dist.py` from a reviewed Git checkout. The index selects
eligible paths; the current contents of tracked files are packaged, including reviewed local
edits. Untracked files are excluded. Credential/runtime names and source symlinks are rejected
or excluded, but no filename filter can identify secrets accidentally written into ordinary code
or documentation. Inspect the archive list and scan tracked content as part of review.

Public deliverables are `dist/vet-flat-skill.zip` and `dist/prompt-pack/`, with their public
checksums. Do not upload the whole `dist/` directory: it may also contain a deliberately private
A/B handoff archive. `tools/build_ab_package.py` includes private gold by design and creates a
private archive; filesystem permissions are not encryption. Backups and raw results stay local
unless the user has reviewed and authorized a specific transfer.

The short prompt pack must retain both asking rules and all eighteen fixed questions within
8,000 characters; builds fail if required content does not fit. When product copy changes,
review the copy deck before refreshing its lock; stale hashes protect existing author edits.

## Review record

See [the 2026-09-09 review](docs/security-review-2026-09-09/review.md) for reproductions, fixes,
validation and limits. The baseline secret scan covered tracked files and reachable Git history,
not every ignored/private file. It found only an explicit test placeholder, not evidence that all
possible secrets or identifying prose are absent. No live attack or provider model call was used.

For a suspected vulnerability, give the maintainer a minimal synthetic reproduction and the
source commit. Do not put credentials, private reports or third-party documents in a public issue.
