#!/usr/bin/env python3
"""Build distributables from the single source of truth (skills/vet-flat/).

  python3 tools/build_dist.py            → dist/vet-flat-skill.zip  (zip root = vet-flat/)
                                         → dist/prompt-pack/        (INSTRUCTIONS.md + references)
                                         → dist/CHECKSUMS.txt
The zip is what claude.ai, Claude Cowork, ChatGPT Skills and the Gemini app accept.
The prompt pack is for chat boxes without a Skills feature: INSTRUCTIONS.md is the
SKILL.md body (front matter stripped) and must stay under 8,000 characters.
"""
import hashlib
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "vet-flat")
DIST = os.path.join(ROOT, "dist")
LIMIT = 8000


DIGEST_SOURCES = [  # in priority order; short, high-value sections first
    ("references/inputs.md", "## Rules for asking", "## What to ask for"),
    ("references/report-contract.md", "## The fourteen fixed questions", "## Plain-language rules"),
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
    """SKILL.md body plus a manual-mode digest of the key references, trimmed from the end to fit."""
    skill_md = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
    body = re.sub(r"^---\n.*?\n---\n", "", skill_md, count=1, flags=re.S).strip() + "\n"
    parts = []
    for rel, start, end in DIGEST_SOURCES:
        path = os.path.join(SKILL, rel)
        if os.path.exists(path):
            sec = _section(open(path, encoding="utf-8").read(), start, end)
            if sec:
                parts.append(sec)
    header = "\n---\n# Manual-mode digest (from the references; the full files are attached)\n\n"
    kept = []
    for sec in parts:  # greedy in priority order: keep every section that still fits
        candidate = body + header + "\n".join(kept + [sec])
        if len(candidate) <= limit:
            kept.append(sec)
    if not kept:
        raise SystemExit("SKILL.md leaves no room for the manual-mode digest; shorten SKILL.md")
    return body + header + "\n".join(kept)


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    # 1) zip with the skill folder as root
    zpath = os.path.join(DIST, "vet-flat-skill.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for dp, dns, fns in os.walk(SKILL):
            dns[:] = [d for d in dns if d not in ("__pycache__",)]
            for fn in fns:
                if fn.endswith(".pyc") or fn == ".DS_Store":
                    continue
                full = os.path.join(dp, fn)
                z.write(full, os.path.join("vet-flat", os.path.relpath(full, SKILL)))
        viewer = os.path.join(ROOT, "viewer", "viewer.html")
        if os.path.exists(viewer):
            z.write(viewer, os.path.join("vet-flat", "viewer", "viewer.html"))
    # 2) prompt pack
    pack = os.path.join(DIST, "prompt-pack")
    os.makedirs(pack)
    body = compose_instructions()
    if len(body) > LIMIT:
        print(f"ERROR: INSTRUCTIONS.md is {len(body)} chars; limit {LIMIT}", file=sys.stderr)
        sys.exit(1)
    open(os.path.join(pack, "INSTRUCTIONS.md"), "w", encoding="utf-8").write(body)
    refs = os.path.join(SKILL, "references")
    if os.path.isdir(refs):
        shutil.copytree(refs, os.path.join(pack, "references"))
    prof = os.path.join(SKILL, "profile.template.yaml")
    if os.path.exists(prof):
        shutil.copy(prof, pack)
    profiles = os.path.join(SKILL, "profiles")
    if os.path.isdir(profiles):
        shutil.copytree(profiles, os.path.join(pack, "profiles"))
    viewer = os.path.join(ROOT, "viewer", "viewer.html")
    if os.path.exists(viewer):
        shutil.copy(viewer, pack)
    open(os.path.join(pack, "README.txt"), "w", encoding="utf-8").write(
        "Pea Princess (vet-flat) prompt pack.\n"
        "1. Paste INSTRUCTIONS.md into your chat product's project/system instructions.\n"
        "2. Attach the files in references/ (and your filled profile.template.yaml).\n"
        "3. Ask: 'Vet this flat: <address>, flat <n>'. The skill will list, once, what to paste.\n"
        "4. Paste the report JSON into viewer.html (open it in any browser) to get the standard report page.\n"
        "Source and licence: https://github.com/jacky18008/pea-princess (CC BY 4.0 docs, MIT code).\n")
    # 3) checksums
    lines = []
    for dp, _, fns in os.walk(DIST):
        for fn in sorted(fns):
            full = os.path.join(dp, fn)
            if fn == "CHECKSUMS.txt":
                continue
            h = hashlib.sha256(open(full, "rb").read()).hexdigest()
            lines.append(f"{h}  {os.path.relpath(full, DIST)}")
    open(os.path.join(DIST, "CHECKSUMS.txt"), "w").write("\n".join(lines) + "\n")
    print(f"zip: {os.path.getsize(zpath)} bytes; INSTRUCTIONS.md: {len(body)} chars; files: {len(lines)}")


if __name__ == "__main__":
    main()
