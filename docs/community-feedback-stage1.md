# Community feedback stage 1: local public choices, private device notes

Implemented 2026-09-09. This is a local form and import pipeline, with no account service, online submission endpoint, public dataset, deployment, or seeded real reviews. The shipped catalog has three explicitly fictional places. The earlier [design](community-feedback-design.md) describes the product boundary.

## Use the form

Open [`community/index.html`](../community/index.html) directly in a modern browser. The file contains its own JavaScript, styles, schema and demo catalog. It loads no remote fonts, scripts, analytics or APIs. The CC0 explanation link opens only if the person chooses to visit it.

1. Choose a catalog place, a completed experience month and the fixed answers. The month selector covers the preceding 60 completed UTC months; it does not accept the current month or an exact date.
2. Read the explicit CC0-1.0 consent statement. It explains copying, modification and reuse without attribution, and the limits of later withdrawal. Consent starts unchecked. It applies only to these newly submitted public choices, not existing project data, the catalog, or private notes.
3. Select **產生公開預覽** and review the actual JSON. Downloading **公開 JSON** creates `community-public.json` locally. Changing any answer requires a new preview; the download handler also checks for changes even if a DOM change event was missed.
4. Optional private notes use an independent textarea and independent save/copy/download/delete actions. `PRIVATE-community-note.txt` is a private document, not a submission file. Never hand it to the public importer.

The optional note is stored only after **存到此瀏覽器** succeeds. The storage key is `pea-princess:private-note:v1`. Reloading the same browser origin can restore it. A failed or blocked localStorage operation is reported as unavailable; the UI does not claim the note was saved. The 8,000-character limit is a UI/storage bound, not a public field. Direct `file:` storage behavior depends on the browser. This is not encrypted storage or cross-device identity isolation: other users of that browser, browser extensions or other same-origin scripts may have access. Saving/downloading is optional.

Deleting the note clears the current page and attempts to remove its localStorage entry. If storage deletion fails, the UI says so. Downloaded files, the clipboard, backups and copies the author already shared are unaffected. Text pasted into one's own private note remains untrusted content when subsequently given to an Agent.

## Exact public contract

[`public-schema.json`](../community/public-schema.json) is generated from the same constants used by the Python validator and embeds the demo catalog allowlist. A custom catalog build generates its corresponding allowlist. Both browser and importer require exactly these fields:

| Field | Accepted values |
|---|---|
| `schema_version` | Integer `1`; booleans and floats are rejected by Python |
| `place_id` | One ID in the selected operator-controlled catalog |
| `experience_month` | `YYYY-MM`, one of the previous 60 completed UTC months at import |
| `experience_kind` | `lived`, `visited`, `hearsay`, `undisclosed` |
| `cleanliness`, `noise`, `transport`, `facilities`, `maintenance` | `very_bad`, `bad`, `mixed`, `good`, `very_good`, `unknown`, `not_applicable` |
| `overall` | `would_return`, `would_not_return`, `unsure`, `not_applicable` |
| `consent` | Boolean `true` |
| `license` | Exact string `CC0-1.0` |

`noise` is labelled **安靜程度**: `good` means a favorable assessment of quietness, not more noise. There is no “other text”, author name, address, arbitrary URL, uploaded attachment, private comment, prompt or model-produced summary field. The importer rejects extra keys instead of stripping them and silently accepting the remainder. Duplicate JSON keys, nonfinite values, invalid types, unknown IDs, oversized input and malformed JSON are also rejected. JSON Schema describes the shape; the rolling month window is additionally enforced in Python and JavaScript. Accepted records remain searchable as they age beyond the initial five-year ingestion window.

This shape cannot prove consent was given by a real person, residency, truthfulness, unique authors or statistical representativeness. Sparse choices and coarse dates can still be identifying when combined with external knowledge. It removes free-text channels from the public ingestion path; it is not an anonymity guarantee.

## Local CLI workflow

Python 3.9+ standard library; no pip, models or internet calls. Run these from the repository root. The input is the public JSON downloaded from the form. Keep the private store outside a public checkout or release directory:

```sh
python3 community/feedback.py validate ~/Downloads/community-public.json
python3 community/feedback.py import ~/Downloads/community-public.json \
  --store ~/.local/share/pea-princess-community-demo
python3 community/feedback.py search \
  --store ~/.local/share/pea-princess-community-demo \
  --place-id demo-orchid-court
python3 community/feedback.py export \
  --store ~/.local/share/pea-princess-community-demo \
  --out ~/Downloads/community-public-index.json
```

`import` reports `imported_local_only`, `duplicate` or `withdrawn_duplicate`. It never posts online. `search` returns one machine-readable JSON object with evidence class `S`, `unverified: true`, catalog scope and per-place sample counts, month counts, experience-kind counts and categorical rating counts. It does not generate a PASS/KILL conclusion or turn subjective votes into facts. Unknown/not-applicable answers retain their own buckets; no misleading average treats them as zero.

The count is **distinct active canonical payloads, not verified people**. Exact duplicates collapse to one record. Different people can legitimately choose identical answers, so deduplication can undercount; an attacker can vary an answer to create multiple distinct payloads, so it does not prevent ballot stuffing. There is no IP tracking, cookie identity or hosted rate limiter in this version.

`export` writes only the same validated aggregate index, outside the private store. It refuses an existing destination: choose a new name for a revised export. Exporting creates a local file, not a publication. Each read revalidates stored payloads and their content IDs before aggregation; a corrupted record carrying a private field cannot pass through to public output. Errors use fixed codes, with no submitted value, key, filename, SQL details or note snippets in stdout/stderr.

### Withdrawal and pause

A successful first import creates a cryptographically random withdrawal token in:

```
<store>/receipts/<record_id>.json
```

The receipt is private and must be retained or securely given back to the contributor by the local operator. The token is not included in the public file, index or CLI success output. The database keeps only its hash. Anyone holding the receipt can withdraw that record; there is no author account or identity check. Losing both the receipt and its backup loses this automated withdrawal capability. The local operator still controls the database, so this is not protection against a malicious operator.

```sh
python3 community/feedback.py withdraw /private/path/to/receipt.json \
  --store ~/.local/share/pea-princess-community-demo
python3 community/feedback.py pause \
  --store ~/.local/share/pea-princess-community-demo
python3 community/feedback.py resume \
  --store ~/.local/share/pea-princess-community-demo
```

Withdrawal is idempotent. It removes the payload from subsequent local searches/exports and leaves a tombstone so reimporting an old copy cannot silently restore it. This is local index withdrawal, not erasure of the retained private database record or recall of old public exports, git history, forks or third-party copies. Correcting a choice means withdraw the old record and import a new, explicitly consented public file.

Pausing blocks imports, including duplicate imports. Search, export and withdrawal remain available. `resume` is an explicit local operator action. The switch and a 10,000-record capacity ceiling are operational stop controls, not rate limiting or a solution to Sybil attacks. There is no online dispute/report portal in this stage; the operator must provide a contact and governance workflow before real public collection.

### Persistence boundaries

The store directory uses mode `0700`; the SQLite database and receipt files use `0600`. No private note is sent to this store. Imports use a SQLite write transaction; the private receipt is saved before commit, and an orphan receipt from an interrupted import is reused safely on retry. Concurrent duplicate imports cannot create two counted rows. Paths containing symlinks and non-regular input/output files are rejected. Input is limited to 16 KiB, a catalog to 128 KiB/500 places and the store to 10,000 records. Error messages contain fixed codes only.

The SQLite file and receipt directory are still private operational artifacts even though the report choices are intended for public reuse. Do not publish the store, receipt files, downloaded private notes, browser storage or arbitrary files beside the form. These local permissions are not a sandbox against another program running as the same user.

## Operator-curated catalogs and builds

The shipped [`catalog.json`](../community/catalog.json) is fictional, with `demo: true`; empty searches contain zero samples. There are no made-up real reviews. A real catalog must come from an operator-controlled workflow, not from public form submissions.

A catalog has exactly `schema_version: 1`, `catalog_id`, `demo`, and `places`. Each place has only `place_id` and `name`. IDs are 3–64 ASCII lowercase letters/digits/hyphens, beginning with a letter; place IDs are unique. Names are 1–100 characters with no control characters. The build preserves approved IDs verbatim: it does not invent IDs from addresses, rename primary keys from labels, or accept crowdsourced free-text places. Operators must have permission to use the catalog's names; public feedback consent does not relicense that source data.

```sh
python3 community/feedback.py catalog-check --catalog /private/catalog-approved.json
python3 community/build.py --catalog /private/catalog-approved.json \
  --out /private/local-form/index.html \
  --schema-out /private/local-form/public-schema.json
python3 community/feedback.py import ~/Downloads/community-public.json \
  --catalog /private/catalog-approved.json \
  --store ~/.local/share/pea-princess-community-curated-v1
```

Pass the same catalog to all later CLI operations. A store binds its catalog digest on creation; a changed catalog cannot silently relabel existing records. Catalog migration is not implemented: archive the old store and plan an explicit migration with withdrawal handling before merging or relabelling datasets. A fresh independent store can use a newly approved catalog. Keep stable primary IDs for the same places.

To regenerate the shipped demo form and schema, run `python3 community/build.py`. The builder embeds the schema and catalog as escaped inert JSON, inserts the actual script, and computes CSP hashes for script/style blocks. CSP disables connections, external content and form submission. Catalog names enter the DOM through `textContent`, never HTML interpolation. Hosting this form later on a shared origin would require a fresh privacy review of other same-origin scripts and storage access; this work did not deploy it.

## Verification and integration

```sh
python3 -m unittest tests.test_community tests.test_community_ui
node --check community/form.js
python3 community/build.py
```

On 2026-09-09, 18 focused offline tests passed. They exercise schema boundaries, duplicate/malformed/deep JSON, month limits, catalog identity, duplicate imports, interrupted-import receipt recovery, pause/resume, local withdrawal, receipt privacy, restricted permissions, output symlinks, malicious extra fields, tampered database contents and deterministic builds. The JavaScript test runs the actual DOM event handlers against isolated in-memory browser dependencies: private-note save/copy/download/delete, public preview/download, changed-answer invalidation and storage failures are exercised with a private sentinel that must never appear in public output or status messages. It requires Node and is explicitly skipped if Node is unavailable.

Safari loaded the generated page through a temporary loopback-only preview; the real DOM showed the complete catalog-driven form and consent boundary. The desktop layout was visually checked, including a Safari select-height fix. The preview server and added tab were closed afterward. No real public submission or private user note was created. Mobile layout has CSS breakpoints but has not received a separate device test.

Root-level integration should link this form and guide, expose the read-only aggregate lookup to Agent documentation, and exclude all private stores/receipts/operator exports from release tooling. Existing skill/release licenses remain unchanged. Before an online stage: define who operates the catalog, how disputes and receipt recovery work, traffic/abuse controls, the publication destination, and a truthful withdrawal policy. Those are still open operational requirements.
