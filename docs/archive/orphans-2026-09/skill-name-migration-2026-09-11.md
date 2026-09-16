# Pea Princess skill name

The public skill identity is `pea-princess`, displayed as **Pea Princess**. Its frontmatter, Codex UI metadata, Claude plugin and marketplace entry, installation examples, report attribution and upload archive now use that name.

`python3 tools/build_dist.py` creates `dist/pea-princess-skill.zip`, containing a single `pea-princess/` skill folder, and the accompanying prompt pack and public checksums. The builder rejects mismatched frontmatter before replacing existing release files.

The repository source remains under `skills/vet-flat/` so existing script imports, benchmark configuration and recorded experiment paths continue to work. Existing report/schema identifiers and caches retain their compatibility names. This directory does not represent a second installed skill. Historical experiment outputs, embedded report samples and fixtures were not renamed.

The local installation was migrated from `~/.agents/skills/vet-flat/` to `~/.agents/skills/pea-princess/`. The old directory and its prior public ZIP were preserved outside skill discovery in the private migration backup. The installed 93-file package matches its archive byte for byte, with only `pea-princess` discoverable among the two names. A session that already loaded the former skill list may need to reload that list or start a new session.

Validation on 2026-09-11:

- 192 focused packaging, renderer, security and copy-deck tests passed. Packaging tests extract a working single skill and ensure a naming mismatch preserves the previous release.
- 123 focused runner tests passed using offline data and fake local processes. New snapshot preparation reads the canonical archive; isolated calls exclude both installed names. Previously frozen single-path plans keep their recorded policy.
- The skill validator passed for the source, extracted ZIP and installed skill.
- Extracted calculation, renderer, session-state and listing parser entrypoints load independently of the repository; linked entrypoint references resolve.
- All public checksums matched; the ZIP contains one skill and its display metadata. The prompt pack contains 7,986 characters and retains its required asking rules and fixed questions.
- Current copy-deck and review-board data were regenerated after checking there were no unapplied author edits.

No model calls, external publication or unrelated agent configuration changes were made for this rename. These checks establish packaging and loading, not a new conversation-quality result.
