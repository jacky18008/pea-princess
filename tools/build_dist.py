#!/usr/bin/env python3
"""Build distributables from the single source of truth (skills/vet-flat/).

  python3 tools/build_dist.py            → dist/pea-princess-skill.zip  (zip root = pea-princess/)
                                         → dist/prompt-pack/        (INSTRUCTIONS.md + references)
                                         → dist/CHECKSUMS.txt
Build from a Git checkout: only indexed source files are eligible. Runtime state,
credentials and symlinks are excluded; review tracked edits before distributing.
Existing unrelated dist/ files (including private bundles) are preserved and are
never included in the public CHECKSUMS.txt.

The zip is what claude.ai, Claude Cowork, ChatGPT Skills and the Gemini app accept.
The prompt pack is for chat boxes without a Skills feature: INSTRUCTIONS.md is the
SKILL.md body (front matter stripped) and must stay under 8,000 characters.
"""
import hashlib
import os
import re
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "vet-flat")
DIST = os.path.join(ROOT, "dist")
LIMIT = 8000
SKILL_NAME = "pea-princess"
ARCHIVE_NAME = SKILL_NAME + "-skill.zip"


DIGEST_SOURCES = [  # in priority order; short, high-value sections first
    ("references/inputs.md", "## Rules for asking", "## What to ask for"),
    ("references/report-contract.md", "## The fixed form", "## Plain-language rules"),
    ("references/arithmetic.md", "## Without a shell", "## Constants"),
    ("references/report-contract.md", "## Plain-language rules", "## Never"),
    ("references/report-contract.md", "## What every report contains", "## Plain-language rules"),
]


def _section(text, start, end):
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:j if j > 0 else len(text)].strip() + "\n"


def compose_instructions(limit=LIMIT):
    """Keep the asking rules and all fixed questions; only other digest parts are optional."""
    skill_md = Path(SKILL, "SKILL.md").read_text(encoding="utf-8")
    body = re.sub(r"^---\n.*?\n---\n", "", skill_md, count=1, flags=re.S).strip() + "\n"
    parts = []
    for index, (rel, start, end) in enumerate(DIGEST_SOURCES):
        path = Path(SKILL, rel)
        section = _section(path.read_text(encoding="utf-8"), start, end) if path.exists() else ""
        if index < 2 and not section:
            raise ValueError("required manual digest section missing: %s in %s" % (start, rel))
        parts.append(section)
    header = "\n---\n# Manual-mode digest (from the references; the full files are attached)\n\n"
    kept = parts[:2]
    required = body + header + "\n".join(kept)
    if len(required) > limit:
        raise ValueError("required manual instructions need %d characters (limit %d); "
                         "shorten SKILL.md by at least %d characters; asking rules and fixed "
                         "questions cannot be dropped" %
                         (len(required), limit, len(required) - limit))
    for section in parts[2:]:
        if section and len(body + header + "\n".join(kept + [section])) <= limit:
            kept.append(section)
    return body + header + "\n".join(kept)


def checked_file(root, rel):
    """Only regular files below root; never dereference a checkout symlink."""
    if os.path.isabs(rel) or any(p in ("", ".", "..") for p in rel.split("/")):
        raise ValueError("unsafe package member: %r" % rel)
    path = Path(root)
    for part in rel.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink is not a package source: %s" % rel)
    if not path.is_file():
        raise ValueError("package source is not a regular file: %s" % rel)
    return str(path)


def distributable(rel):
    """Runtime state and credentials stay out even if accidentally tracked."""
    parts = rel.replace(os.sep, "/").split("/")
    return not any(p.startswith(".") or p in ("__pycache__", "profile.yaml", "results")
                   or p.endswith((".pyc", ".pem", ".key")) for p in parts)


def tracked_files(root, paths):
    """Git's index is the release allowlist; untracked local notes are not assets."""
    try:
        output = subprocess.check_output(
            ["git", "-C", root, "ls-files", "--cached", "-z", "--"] + list(paths))
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("build packages from a Git checkout with a reviewed index") from exc
    return sorted(set(os.fsdecode(p) for p in output.split(b"\0") if p))


def public_members():
    rows = []
    for rel in tracked_files(ROOT, ["skills/vet-flat", "viewer/viewer.html"]):
        if distributable(rel):
            rows.append((checked_file(ROOT, rel), rel))
    if not any(rel == "skills/vet-flat/SKILL.md" for _, rel in rows):
        raise ValueError("tracked skills/vet-flat/SKILL.md is required")
    return rows


def main():
    # Validate every source before touching an existing release. Public builds do
    # not remove other dist/ files: it can also hold a private A/B handoff archive.
    members = public_members()
    allowed = {rel for _, rel in members}
    for rel, _, _ in DIGEST_SOURCES:
        if os.path.exists(os.path.join(SKILL, rel)) and "skills/vet-flat/" + rel not in allowed:
            raise ValueError("manual digest source is not a reviewed tracked file: %s" % rel)
    identity = Path(SKILL, "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---(?:\n|$)", identity, re.S)
    name = re.search(r"^name: *([^\n]+)$", frontmatter[1], re.M) if frontmatter else None
    if not name or name[1].strip().strip("\"\'") != SKILL_NAME:
        raise ValueError("public skill frontmatter name must be " + SKILL_NAME)
    body = compose_instructions()
    if len(body) > LIMIT:
        raise ValueError("INSTRUCTIONS.md exceeds %d characters" % LIMIT)
    if Path(DIST).is_symlink():
        raise ValueError("dist must not be a symlink")
    os.makedirs(DIST, exist_ok=True)
    pack_dest = os.path.join(DIST, "prompt-pack")
    if os.path.lexists(pack_dest) and (os.path.islink(pack_dest) or not os.path.isdir(pack_dest)):
        raise ValueError("prompt-pack must be a real directory")
    for name in (ARCHIVE_NAME, "CHECKSUMS.txt"):
        target = Path(DIST, name)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("public output must be a regular file: %s" % name)
    with tempfile.TemporaryDirectory(prefix=".public-build-", dir=DIST) as stage:
        zpath = os.path.join(stage, ARCHIVE_NAME)
        pack = os.path.join(stage, "prompt-pack")
        os.makedirs(pack)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for full, rel in members:
                inside = (SKILL_NAME + "/" + rel[len("skills/vet-flat/"):]
                          if rel.startswith("skills/vet-flat/") else SKILL_NAME + "/" + rel)
                z.write(full, inside)
                short = rel[len("skills/vet-flat/"):] if rel.startswith("skills/vet-flat/") else rel
                if short.startswith(("references/", "profiles/")) or short == "profile.template.yaml":
                    target = os.path.join(pack, short)
                elif rel == "viewer/viewer.html":
                    target = os.path.join(pack, "viewer.html")
                else:
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(full, target)
        Path(pack, "INSTRUCTIONS.md").write_text(body, encoding="utf-8")
        Path(pack, "README.txt").write_text(
            "Pea Princess prompt pack.\n"
            "1. Paste INSTRUCTIONS.md into your chat product's project/system instructions.\n"
            "2. Attach the files in references/ (and your filled profile.template.yaml).\n"
            "3. Ask: 'Vet this flat: <address>, flat <n>'. The skill will list, once, what to paste.\n"
            "4. Paste the report JSON into viewer.html (open it in any browser) to get the standard report page.\n"
            "Source and licence: https://github.com/jacky18008/pea-princess (CC BY 4.0 docs, MIT code).\n",
            encoding="utf-8")
        lines = []
        for full in sorted(Path(stage).rglob("*")):
            if full.is_file():
                lines.append("%s  %s" % (hashlib.sha256(full.read_bytes()).hexdigest(),
                                         full.relative_to(stage).as_posix()))
        Path(stage, "CHECKSUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Keep the previous release until every new output is in place. A failed
        # rename must not leave a new prompt pack beside an old ZIP/checksum set.
        previous = Path(stage, "previous")
        previous.mkdir()
        saved, installed = [], []
        try:
            for name in ("prompt-pack", ARCHIVE_NAME, "CHECKSUMS.txt"):
                destination = Path(DIST, name)
                if destination.exists():
                    os.replace(destination, previous / name)
                    saved.append(name)
                os.replace(Path(stage, name), destination)
                installed.append(name)
        except OSError:
            for name in reversed(installed):
                destination = Path(DIST, name)
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            for name in reversed(saved):
                os.replace(previous / name, Path(DIST, name))
            raise
    print("zip: %d bytes; INSTRUCTIONS.md: %d chars; files: %d" %
          (os.path.getsize(os.path.join(DIST, ARCHIVE_NAME)), len(body), len(lines)))


if __name__ == "__main__":
    main()
