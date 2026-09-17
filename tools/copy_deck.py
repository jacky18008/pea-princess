#!/usr/bin/env python3
"""Copy deck: every outward-facing sentence in one file, editable, with write-back.

  python3 tools/copy_deck.py extract           → docs/COPY-DECK.md + docs/copy-deck.lock.json
  python3 tools/copy_deck.py board             → refreshes docs/review-board.html (phone editor)
  python3 tools/copy_deck.py merge --from X    → folds the board's edits into the deck
  python3 tools/copy_deck.py apply --dry-run   → the diffs, changing nothing
  python3 tools/copy_deck.py apply             → writes every edited block back to its source

The deck holds only text a *reader* sees: the README prose, the install and
experiment pages, the pitches and the primer, the ask template, the profile
sentences.  Model-facing instructions (SKILL.md, axes/, budget modes, question
tables, schemas, thresholds, sources) are deliberately not in it.

Contract
  - Text is captured **verbatim**, as a span of source lines.  Whatever prefix a
    line carries in the file (`> `, `- `, two spaces of list indent, a YAML key)
    is part of the block and must survive an edit.
  - `extract` is deterministic: same sources → byte-identical deck and lock.  No
    timestamps are written into either file.
  - `apply` matches on the exact original text stored in the lock, not on line
    numbers, and refuses a block whose original text is no longer uniquely
    present in its source.  Nothing is written for a file with a refusal in it.
  - `extract` refuses to overwrite a deck that has unapplied edits (`--force`
    discards them).

Python 3.9, standard library only.
"""
import argparse
import ast
import difflib
import hashlib
import json
import os
import re
import sys

ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK_REL = "docs/COPY-DECK.md"
LOCK_REL = "docs/copy-deck.lock.json"
LOCK_VERSION = 1

HEADER = """\
# Copy deck — Pea Princess (`pea-princess`)

Every sentence a *reader* sees, in one place, so it can be rewritten in one voice.
Model-facing text (SKILL.md, the axis files, budget modes, the question tables, the
schemas, thresholds and sources) is deliberately **not** here.

**Edit the fenced text only. Keep the ids. Run `python3 tools/copy_deck.py apply`.**

How it works
- Each block below is a verbatim span of lines from its source file. Keep the line
  prefixes you see — `> `, `- `, `1. `, two spaces of indent, a `key:` — they are part
  of the file, not decoration.
- `apply` finds the old text in the source by exact match (not by line number) and
  swaps it. If the old text is gone or appears twice, that block is refused by name
  and **nothing in that file is written**.
- `deck:<file>:<n>` is positional: `n` counts blocks in that file, top to bottom. A
  re-extract after the source is restructured can renumber; the ids are stable as long
  as blocks are not inserted above one another.
- Blocks marked `write-back: no` are read-only in this deck. Edit those in the source.
- Line numbers are informational and go stale; the exact text is what matches.

On a phone
- `docs/review-board.html` is the same deck as a page you can edit with your thumbs.
  Publish it as an Artifact with `capabilities: {"db": {}}` and its edits land in the
  artifact store; `python3 tools/copy_deck.py board` refreshes what it shows.
- To bring those edits home: read the store into a file (or use the page's
  "Copy edits as Markdown"), then `merge --from <file>` and `apply`.
"""

# --------------------------------------------------------------- what is a surface --
# kinds: para | blockquote | ol | ul | fence   (markdown; html blocks are layout and never extracted)
#        yaml (a key's value)                  (yaml)
#        pystr (a string literal)              (python)
SURFACES = [
    {
        "path": "README.md",
        "title": "README — the front page (Traditional Chinese, the page GitHub shows)",
        "note": "All prose paragraphs. Tables, headings and code blocks are not in the deck.",
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para", "blockquote", "ol"]}],
    },
    {
        "path": "README.en.md",
        "title": "README.en.md — the front page, English",
        "note": "All prose paragraphs. Tables, headings and code blocks are not in the deck.",
        "optional": True,
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para", "blockquote", "ol"]}],
    },
    {
        "path": "docs/USING.md",
        "title": "docs/USING.md — the plain-words walkthrough (English)",
        "note": "Every paragraph, step and bullet. Headings are not in the deck.",
        "optional": True,
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para", "ol", "ul", "blockquote"]}],
    },
    {
        "path": "docs/USING.zh-TW.md",
        "title": "docs/USING.zh-TW.md — the walkthrough, Traditional Chinese",
        "note": "Every paragraph, step and bullet. Headings are not in the deck.",
        "optional": True,
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para", "ol", "ul", "blockquote"]}],
    },
    {
        "path": "docs/USING.zh-CN.md",
        "title": "docs/USING.zh-CN.md — the walkthrough, Simplified Chinese",
        "note": "Every paragraph, step and bullet. Headings are not in the deck.",
        "optional": True,
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para", "ol", "ul", "blockquote"]}],
    },
    {
        "path": "docs/INSTALL.md",
        "title": "docs/INSTALL.md — install page",
        "note": "The intro and every section's prose. The install tables are not in the deck.",
        "extractor": "markdown",
        "sections": [{"match": "*", "title": None, "kinds": ["para"]}],
    },
    {
        "path": "docs/EXPERIMENTS.md",
        "title": "docs/EXPERIMENTS.md — which configuration to run",
        "note": "The intro, and the “What it means” bullets. Result tables and caveats are not in the deck.",
        "extractor": "markdown",
        "sections": [
            {"match": None, "title": "Intro", "kinds": ["para"]},
            {"match": r"^##\s*What it means", "title": "What it means", "kinds": ["ul"]},
        ],
    },
    {
        "path": "skills/vet-flat/references/onboarding.md",
        "title": "onboarding.md — what the skill says to a new user",
        "note": "The three pitches, the four starting points, the ten-fact primer, the Q&A answers. "
                "The intake tables and the distilling rules are model-facing and not in the deck.",
        "extractor": "markdown",
        "sections": [
            {"match": r"^##\s*1\.", "title": "The pitch, and the starting points",
             "kinds": ["blockquote", "ol"]},
            {"match": r"^##\s*3\.", "title": "The primer: ten facts", "kinds": ["ol"]},
            {"match": r"^##\s*4\.", "title": "Short answers to common questions", "kinds": ["ul"]},
        ],
    },
    {
        "path": "skills/vet-flat/references/sharing.md",
        "title": "sharing.md — social posts and the card description",
        "note": "The three social posts, the two questions worth copying, and what to say to "
                "somebody importing another person's seed. The rest of the file is model-facing.",
        "optional": True,
        "extractor": "markdown",
        "sections": [
            {"match": r"^##\s*3\.", "title": "Questions worth copying", "kinds": ["blockquote"]},
            {"match": r"^##\s*4\.", "title": "The social post", "kinds": ["blockquote"]},
            {"match": r"^##\s*6\.", "title": "Importing somebody else's seed",
             "kinds": ["blockquote"]},
        ],
    },
    {
        "path": "skills/vet-flat/references/inputs.md",
        "title": "inputs.md — the one message that asks the user for what is missing",
        "note": "The ask template only. The per-axis table is model-facing.",
        "extractor": "markdown",
        "sections": [{"match": r"^##\s*Template for the ask", "title": "Template for the ask",
                      "kinds": ["fence"]}],
    },
    {
        "path": "skills/vet-flat/profiles/*.yaml",
        "title": "profiles/ — the sentences a profile carries",
        "note": "`story_summary`, `self_intro_template` and the `my_questions` texts. "
                "Keep the YAML shape: the key, the indent and the quotes are part of the block.",
        "extractor": "yaml",
        "keys": ["story_summary", "self_intro_template", "my_questions"],
        "item_prose_keys": ["text"],
    },
    {
        "path": "skills/vet-flat/scripts/seed.py",
        "title": "seed.py — the seed card sentences (read-only here)",
        "note": "Fragments the card assembles at run time; `%s` is filled in from the profile. "
                "Shown verbatim as Python literals. Write-back is off for this file — edit it in "
                "the source.",
        "extractor": "python",
        "functions": ["sentences", "card", "journey_lines"],
        "writable": False,
    },
]

# --------------------------------------------------------------------- language --
_TRAD_ONLY = set("這個廠資據樣間證屋齡週邊評價規採決標級請貼掃圍區較棟則預條們門講識認環報長負責層篩墊驗實線網項單別於應說見語數論結樓")
_SIMP_ONLY = set("这个厂资据样间证楼龄周边评价规采决标级请贴扫围区较栋则预条们门讲识认环报长负责层筛垫验实线网项单别于应说见语数论结")
_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def detect_lang(text):
    """en / zh-TW / zh-CN, decided by character set. Deterministic, no dependencies."""
    han = _CJK.findall(text)
    dense = len("".join(text.split()))
    if len(han) < 3 or not dense or len(han) / float(dense) < 0.10:
        return "en"
    trad = sum(1 for c in han if c in _TRAD_ONLY)
    simp = sum(1 for c in han if c in _SIMP_ONLY)
    if simp > trad:
        return "zh-CN"
    return "zh-TW"


# ---------------------------------------------------------------------- helpers --
def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_path(root, rel):
    """Deck metadata cannot redirect reads or writes outside the checkout or through links."""
    if not isinstance(rel, str) or os.path.isabs(rel) or "\\" in rel \
            or any(part in ("", ".", "..") for part in rel.split("/")):
        raise SystemExit("unsafe copy-deck path: %r" % rel)
    current = os.path.abspath(root)
    for part in rel.split("/"):
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise SystemExit("copy-deck paths must not contain symlinks: %s" % rel)
    return current


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def fence_for(text):
    """A backtick fence longer than any run of backticks inside the text."""
    longest = 0
    for run in re.findall(r"`+", text):
        longest = max(longest, len(run))
    return "`" * max(3, longest + 1)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def file_slugs(paths):
    """Basename slug where unique, full-path slug where it collides. Deterministic."""
    base = {}
    for path in paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        base.setdefault(slugify(stem), []).append(path)
    out = {}
    for slug, group in base.items():
        if len(group) == 1:
            out[group[0]] = slug
        else:
            for path in group:
                out[path] = slugify(os.path.splitext(path)[0])
    return out


# ------------------------------------------------------------- markdown chunking --
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_HR = re.compile(r"^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$")
_OL = re.compile(r"^(\s*)\d+[.)]\s+\S")
_UL = re.compile(r"^(\s*)[-*+]\s+\S")
_TABLE = re.compile(r"^\s*\|")
_QUOTE = re.compile(r"^\s*>")
_ATTRIB = re.compile(r"^Part of Pea Princess")


def _starts_block(line):
    return bool(
        not line.strip()
        or _FENCE.match(line)
        or _HEADING.match(line)
        or _HR.match(line)
        or _OL.match(line)
        or _UL.match(line)
        or _TABLE.match(line)
        or _QUOTE.match(line)
    )


def md_chunks(lines, start, stop):
    """(kind, first, last, inner_first, inner_last) for every chunk in [start, stop)."""
    out = []
    i = start
    while i < stop:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = _FENCE.match(line)
        if m:
            mark = m.group(1)
            j = i + 1
            while j < stop:
                stripped = lines[j].strip()
                if stripped.startswith(mark[0] * len(mark)) and set(stripped) == {mark[0]}:
                    break
                j += 1
            close = j if j < stop else stop - 1
            out.append(("fence", i, close, i + 1, close - 1))
            i = close + 1
            continue
        if _HEADING.match(line):
            out.append(("heading", i, i, i, i))
            i += 1
            continue
        if _HR.match(line):
            out.append(("hr", i, i, i, i))
            i += 1
            continue
        if _TABLE.match(line):
            j = i
            while j < stop and _TABLE.match(lines[j]):
                j += 1
            out.append(("table", i, j - 1, i, j - 1))
            i = j
            continue
        if _QUOTE.match(line):
            j = i
            while j < stop and _QUOTE.match(lines[j]):
                j += 1
            out.append(("blockquote", i, j - 1, i, j - 1))
            i = j
            continue
        if _OL.match(line) or _UL.match(line):
            kind = "ol" if _OL.match(line) else "ul"
            j = i + 1
            while j < stop and not _starts_block(lines[j]):
                j += 1
            out.append((kind, i, j - 1, i, j - 1))
            i = j
            continue
        if _ATTRIB.match(line):
            out.append(("attribution", i, i, i, i))
            i += 1
            continue
        if line.lstrip().startswith("<"):
            # An HTML block (a centred header, a <details> fold, an <img>): layout, not copy.
            j = i + 1
            while j < stop and lines[j].strip() and not _starts_block(lines[j]):
                j += 1
            out.append(("html", i, j - 1, i, j - 1))
            i = j
            continue
        j = i + 1
        while j < stop and not _starts_block(lines[j]):
            j += 1
        out.append(("para", i, j - 1, i, j - 1))
        i = j
    return out


def md_sections(lines, spec):
    """[(title, start, stop, kinds)] for the configured sections of one file."""
    heads = [i for i, line in enumerate(lines) if re.match(r"^##\s", line)]
    bounds = []
    for pos, idx in enumerate(heads):
        end = heads[pos + 1] if pos + 1 < len(heads) else len(lines)
        bounds.append((idx, end))
    out = []
    for rule in spec:
        match = rule.get("match")
        if match == "*":
            out.append((rule.get("title"), 0, len(lines), rule["kinds"]))
        elif match is None:
            out.append((rule.get("title"), 0, heads[0] if heads else len(lines), rule["kinds"]))
        else:
            rx = re.compile(match)
            for idx, end in bounds:
                if rx.match(lines[idx]):
                    out.append((rule.get("title") or lines[idx].lstrip("# ").strip(),
                                idx, end, rule["kinds"]))
    out.sort(key=lambda row: row[1])
    return out


def nearest_heading(lines, index):
    for i in range(index, -1, -1):
        m = _HEADING.match(lines[i])
        if m:
            return lines[i].strip()
    return None


def extract_markdown(text, surface):
    lines = text.split("\n")
    found = []
    for title, start, stop, kinds in md_sections(lines, surface["sections"]):
        for kind, first, last, inner_first, inner_last in md_chunks(lines, start, stop):
            if kind not in kinds:
                continue
            if kind == "fence":
                if inner_first > inner_last:
                    continue
                first, last = inner_first, inner_last
            body = "\n".join(lines[first:last + 1])
            if not body.strip():
                continue
            found.append({
                "section": title,
                "anchor": nearest_heading(lines, first),
                "first": first,
                "last": last,
                "text": body,
                "kind": kind,
            })
    found.sort(key=lambda row: row["first"])
    return found


# ------------------------------------------------------------------ yaml values --
_YKEY = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_.-]*):\s*(.*?)\s*$")
_YITEM = re.compile(r"^(\s*)-\s+\S")
_BLOCK_SCALAR = {">", ">-", ">+", "|", "|-", "|+"}


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def extract_yaml(text, surface):
    lines = text.split("\n")
    keys = surface["keys"]
    prose_keys = surface.get("item_prose_keys") or []
    found = []
    i = 0
    while i < len(lines):
        m = _YKEY.match(lines[i])
        if not m or m.group(2) not in keys:
            i += 1
            continue
        indent, key, rest = m.group(1), m.group(2), m.group(3)
        if rest in _BLOCK_SCALAR:
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or _indent_of(lines[j]) > len(indent)):
                j += 1
            last = j - 1
            while last > i and not lines[last].strip():
                last -= 1
            if last > i:
                found.append({"section": key, "anchor": "%s:" % key, "first": i + 1, "last": last,
                              "text": "\n".join(lines[i + 1:last + 1]), "kind": "yaml"})
            i = j
            continue
        if rest == "":
            j = i + 1
            items = []
            while j < len(lines):
                if not lines[j].strip():
                    j += 1
                    continue
                im = _YITEM.match(lines[j])
                if not im or len(im.group(1)) <= len(indent):
                    break
                item_indent = len(im.group(1))
                first = j
                j += 1
                while j < len(lines) and lines[j].strip() and not _YITEM.match(lines[j]) \
                        and _indent_of(lines[j]) > item_indent:
                    j += 1
                items.append((first, j - 1))
            for first, last in items:
                prose = None
                for k in range(first, last + 1):
                    pm = re.match(r"^\s*(?:-\s+)?([A-Za-z_][A-Za-z0-9_.-]*):\s*\S", lines[k])
                    if pm and pm.group(1) in prose_keys:
                        prose = (k, k)
                        break
                first, last = prose if prose else (first, last)
                found.append({"section": key, "anchor": "%s:" % key, "first": first, "last": last,
                              "text": "\n".join(lines[first:last + 1]), "kind": "yaml"})
            i = j
            continue
        found.append({"section": key, "anchor": "%s:" % key, "first": i, "last": i,
                      "text": lines[i], "kind": "yaml"})
        i += 1
    found.sort(key=lambda row: row["first"])
    return found


# ------------------------------------------------------- python string literals --
def _byte_slice(line, start=None, stop=None):
    raw = line.encode("utf-8")
    return raw[start:stop].decode("utf-8")


def _prose_like(value):
    """Prose, not an identifier: a dict key or a field name is never card text."""
    if " " not in value.strip():
        return False
    clean = re.sub(r"%[-+ #0-9.]*[sdrfgxi%]", " ", value)
    words = re.findall(r"[A-Za-z']+", clean)
    return len(words) >= 2 and sum(len(w) for w in words) >= 5


def extract_python(text, surface):
    lines = text.split("\n")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:                                          # noqa: BLE001
        sys.stderr.write("note: %s could not be parsed (%s); its blocks are skipped\n"
                         % (surface["path"], exc))
        return []
    wanted = set(surface["functions"])
    found = []
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in wanted:
            continue
        skip = set()
        first_stmt = node.body[0] if node.body else None
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) \
                and isinstance(first_stmt.value.value, str):
            skip.add((first_stmt.value.lineno, first_stmt.value.col_offset))
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Constant) or not isinstance(sub.value, str):
                continue
            key = (sub.lineno, sub.col_offset)
            if key in skip or key in seen or not _prose_like(sub.value):
                continue
            seen.add(key)
            first, last = sub.lineno - 1, sub.end_lineno - 1
            if first == last:
                body = _byte_slice(lines[first], sub.col_offset, sub.end_col_offset)
            else:
                parts = [_byte_slice(lines[first], sub.col_offset)]
                parts.extend(lines[first + 1:last])
                parts.append(_byte_slice(lines[last], None, sub.end_col_offset))
                body = "\n".join(parts)
            found.append({"section": node.name + "()", "anchor": "def %s(" % node.name,
                          "first": first, "last": last, "text": body, "kind": "pystr"})
    found.sort(key=lambda row: (row["first"], row["text"]))
    return found


EXTRACTORS = {"markdown": extract_markdown, "yaml": extract_yaml, "python": extract_python}


# ---------------------------------------------------------------------- extract --
def surface_files(root, surface):
    pattern = surface["path"]
    if "*" not in pattern:
        full = os.path.join(root, pattern)
        return [pattern] if os.path.exists(full) else []
    head, tail = pattern.rsplit("/", 1)
    folder = os.path.join(root, head)
    if not os.path.isdir(folder):
        return []
    rx = re.compile("^" + re.escape(tail).replace(r"\*", "[^/]*") + "$")
    return sorted("%s/%s" % (head, name) for name in os.listdir(folder) if rx.match(name))


def build(root):
    """[(surface, [block, ...]), ...] plus the notes for surfaces that are not there."""
    groups, notes = [], []
    paths = []
    for surface in SURFACES:
        paths.extend(surface_files(root, surface))
    slugs = file_slugs(paths)
    for surface in SURFACES:
        files = surface_files(root, surface)
        if not files:
            notes.append("`%s` is not in the repo yet — skipped. Re-run `extract` once it exists."
                         % surface["path"])
            continue
        blocks = []
        for rel in files:
            text = read_text(repo_path(root, rel))
            raw = EXTRACTORS[surface["extractor"]](text, dict(surface, path=rel))
            for n, item in enumerate(raw, 1):
                start = sum(len(line) + 1 for line in text.split("\n")[:item["first"]])
                blocks.append({
                    "id": "deck:%s:%d" % (slugs[rel], n),
                    "source": rel,
                    "section": item["section"],
                    "anchor": item["anchor"],
                    "line_from": item["first"] + 1,
                    "line_to": item["last"] + 1,
                    "char_from": start,
                    "char_to": start + len(item["text"]),
                    "lang": detect_lang(item["text"]),
                    "kind": item["kind"],
                    "writable": surface.get("writable", True),
                    "text": item["text"],
                    "sha256": sha256(item["text"]),
                    "source_sha256": sha256(text),
                })
        groups.append((surface, blocks))
    return groups, notes


def render_deck(groups, notes):
    out = [HEADER]
    out.append("\n## Contents\n")
    out.append("| Surface | Blocks | Source |")
    out.append("|---|---|---|")
    total = 0
    for surface, blocks in groups:
        total += len(blocks)
        out.append("| %s | %d | `%s` |" % (surface["title"], len(blocks), surface["path"]))
    out.append("| **Total** | **%d** | |" % total)
    if notes:
        out.append("")
        for note in notes:
            out.append("> Not yet present: %s" % note)
    out.append("")
    for surface, blocks in groups:
        out.append("---")
        out.append("")
        out.append("## %s" % surface["title"])
        out.append("")
        out.append("%s" % surface["note"])
        out.append("")
        for block in blocks:
            out.append("### %s" % block["id"])
            out.append("")
            anchor = block["anchor"] or "(top of file)"
            span = ("L%d" % block["line_from"] if block["line_from"] == block["line_to"]
                    else "L%d-L%d" % (block["line_from"], block["line_to"]))
            out.append("- source: `%s` · %s" % (block["source"], span))
            out.append("- under: %s" % anchor)
            out.append("- lang: %s" % block["lang"])
            out.append("- write-back: %s" % ("yes" if block["writable"] else "no (read-only)"))
            out.append("")
            mark = fence_for(block["text"])
            out.append(mark + "text")
            out.append(block["text"])
            out.append(mark)
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def render_lock(groups):
    payload = {"version": LOCK_VERSION, "blocks": {}}
    for _surface, blocks in groups:
        for block in blocks:
            payload["blocks"][block["id"]] = {
                key: block[key] for key in
                ("source", "section", "anchor", "line_from", "line_to", "char_from", "char_to",
                 "lang", "kind", "writable", "text", "sha256", "source_sha256")
            }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def cmd_extract(root, force=False):
    deck_path = repo_path(root, DECK_REL)
    lock_path = repo_path(root, LOCK_REL)
    if os.path.exists(deck_path) and os.path.exists(lock_path) and not force:
        pending = pending_edits(root)
        if pending:
            sys.stderr.write(
                "refusing to overwrite %s: %d block(s) have edits that are not applied yet "
                "(%s).\nRun `apply` first, or `extract --force` to discard them.\n"
                % (DECK_REL, len(pending), ", ".join(sorted(pending)[:5])))
            return 1
    groups, notes = build(root)
    os.makedirs(os.path.dirname(deck_path), exist_ok=True)
    write_text(deck_path, render_deck(groups, notes))
    write_text(lock_path, render_lock(groups))
    total = 0
    for surface, blocks in groups:
        total += len(blocks)
        print("%4d  %s" % (len(blocks), surface["path"]))
    for note in notes:
        print("   -  %s" % note)
    print("%4d  blocks written to %s (lock: %s)" % (total, DECK_REL, LOCK_REL))
    return 0


# ------------------------------------------------------------------------ apply --
def scan_deck(text):
    """[(id, body_first_line, body_stop_line, body_text)] in document order."""
    lines = text.split("\n")
    out = []
    seen = set()
    i = 0
    while i < len(lines):
        m = re.match(r"^###\s+(deck:[A-Za-z0-9._-]+:\d+)\s*$", lines[i])
        if not m:
            i += 1
            continue
        block_id = m.group(1)
        j = i + 1
        mark = None
        while j < len(lines):
            if re.match(r"^#{1,3}\s", lines[j]):
                break
            fm = re.match(r"^(`{3,})", lines[j])
            if fm:
                mark = fm.group(1)
                break
            j += 1
        if mark is None:
            raise ValueError("%s has no fenced text block" % block_id)
        k = j + 1
        while k < len(lines) and lines[k].rstrip() != mark:
            k += 1
        if k >= len(lines):
            raise ValueError("%s has an unterminated fence" % block_id)
        if block_id in seen:
            raise ValueError("%s appears twice in the deck" % block_id)
        seen.add(block_id)
        out.append((block_id, j + 1, k, "\n".join(lines[j + 1:k])))
        i = k + 1
    return out


def parse_deck(text):
    """{id: text} in document order, from a deck file."""
    scanned = scan_deck(text)
    return {row[0]: row[3] for row in scanned}, [row[0] for row in scanned]


def load_lock(root):
    lock_path = repo_path(root, LOCK_REL)
    if not os.path.exists(lock_path):
        raise SystemExit("no %s — run `extract` first" % LOCK_REL)
    data = json.loads(read_text(lock_path))
    if data.get("version") != LOCK_VERSION:
        raise SystemExit("%s is version %r; this tool writes version %d"
                         % (LOCK_REL, data.get("version"), LOCK_VERSION))
    allowed = {}
    for surface in SURFACES:
        for rel in surface_files(root, surface):
            allowed[rel] = surface.get("writable", True)
    blocks = data.get("blocks")
    if not isinstance(blocks, dict):
        raise SystemExit("copy-deck lock must contain a blocks object")
    for entry in blocks.values():
        if not isinstance(entry, dict):
            raise SystemExit("copy-deck lock entry must be an object")
        rel = entry.get("source")
        repo_path(root, rel)
        if rel not in allowed:
            raise SystemExit("copy-deck source is not a registered surface: %s" % rel)
        if entry.get("writable", True) and not allowed[rel]:
            raise SystemExit("copy-deck lock cannot make a read-only surface writable: %s" % rel)
    return data


def pending_edits(root):
    """Ids whose deck text differs from the locked original."""
    try:
        lock = load_lock(root)
    except SystemExit:
        return []
    deck_path = repo_path(root, DECK_REL)
    if not os.path.exists(deck_path):
        return []
    try:
        blocks, _order = parse_deck(read_text(deck_path))
    except ValueError:
        return []
    out = []
    for block_id, text in blocks.items():
        entry = lock["blocks"].get(block_id)
        if entry and text != entry["text"]:
            out.append(block_id)
    return out


def locate(content, entry):
    """(start, stop) of the locked original inside content, or None if it moved."""
    start, stop = entry["char_from"], entry["char_to"]
    if content[start:stop] == entry["text"]:
        return start, stop
    hits = content.count(entry["text"])
    if hits == 1:
        start = content.find(entry["text"])
        return start, start + len(entry["text"])
    return None


def guard_shape(entry, new_text):
    """A one-line sanity check so a YAML or list block cannot lose its own prefix."""
    old_first = entry["text"].split("\n")[0]
    new_first = new_text.split("\n")[0]
    prefix = re.match(r"^\s*(?:-\s+)?(?:[A-Za-z_][A-Za-z0-9_.-]*:)?", old_first).group(0)
    if entry["kind"] in ("yaml",) and prefix and not new_first.startswith(prefix):
        return ("the first line must still start with %r (the YAML key and indent are part of "
                "the block)" % prefix)
    if entry["kind"] in ("ol", "ul"):
        marker = re.match(r"^\s*(?:\d+[.)]|[-*+])\s+", old_first)
        if marker and not re.match(r"^\s*(?:\d+[.)]|[-*+])\s+", new_first):
            return "the first line must still start with its list marker (%r)" % marker.group(0)
    if entry["kind"] == "blockquote" and old_first.lstrip().startswith(">") \
            and not new_first.lstrip().startswith(">"):
        return "every line must still start with `> ` (it is a Markdown blockquote)"
    return None


def cmd_apply(root, dry_run=False, strict=False):
    lock = load_lock(root)
    deck_path = repo_path(root, DECK_REL)
    if not os.path.exists(deck_path):
        raise SystemExit("no %s — run `extract` first" % DECK_REL)
    try:
        deck_blocks, order = parse_deck(read_text(deck_path))
    except ValueError as exc:                                           # noqa: BLE001
        raise SystemExit("the deck could not be read: %s" % exc)

    edits, refusals, unknown = [], [], []
    for block_id in order:
        new_text = deck_blocks[block_id]
        entry = lock["blocks"].get(block_id)
        if entry is None:
            unknown.append(block_id)
            continue
        if new_text == entry["text"]:
            continue
        if not entry.get("writable", True):
            refusals.append((block_id, entry["source"],
                             "this block is read-only in the deck; edit it in the source file"))
            continue
        problem = guard_shape(entry, new_text)
        if problem:
            refusals.append((block_id, entry["source"], problem))
            continue
        edits.append((block_id, entry, new_text))

    for block_id in unknown:
        sys.stderr.write("unknown id in the deck, ignored: %s\n" % block_id)

    by_file = {}
    for block_id, entry, new_text in edits:
        by_file.setdefault(entry["source"], []).append((block_id, entry, new_text))

    changed_files, changed_blocks = [], []
    for rel in sorted(by_file):
        full = repo_path(root, rel)
        content = read_text(full)
        if sha256(content) != by_file[rel][0][1]["source_sha256"]:
            message = "%s changed since the deck was extracted" % rel
            if strict:
                for block_id, entry, _new in by_file[rel]:
                    refusals.append((block_id, rel, message + " (--strict)"))
                continue
            sys.stderr.write("note: %s; matching on the exact text instead of line numbers\n" % rel)
        spans = []
        file_refused = False
        for block_id, entry, new_text in by_file[rel]:
            found = locate(content, entry)
            if found is None:
                hits = content.count(entry["text"])
                refusals.append((block_id, rel,
                                 "the source moved: the original text is %s in %s. Nothing in this "
                                 "file was written. Re-run `extract` (this loses the edit) or make "
                                 "the change by hand."
                                 % ("no longer there" if hits == 0
                                    else "there %d times, so the match is ambiguous" % hits, rel)))
                file_refused = True
                continue
            spans.append((found[0], found[1], block_id, entry, new_text))
        spans.sort(key=lambda row: row[0])
        for pos in range(1, len(spans)):
            if spans[pos][0] < spans[pos - 1][1]:
                refusals.append((spans[pos][2], rel, "this block overlaps %s in the source"
                                 % spans[pos - 1][2]))
                file_refused = True
        if file_refused:
            continue
        for start, stop, block_id, entry, new_text in spans:
            print("~ %s  %s L%d" % (block_id, rel, entry["line_from"]))
            if dry_run:
                diff = difflib.unified_diff(entry["text"].split("\n"), new_text.split("\n"),
                                            lineterm="", fromfile="before", tofile="after")
                for line in list(diff)[2:]:
                    print("    " + line)
        if dry_run:
            changed_blocks.extend(row[2] for row in spans)
            changed_files.append(rel)
            continue
        for start, stop, block_id, entry, new_text in sorted(spans, key=lambda row: -row[0]):
            content = content[:start] + new_text + content[stop:]
        write_text(full, content)
        changed_files.append(rel)
        changed_blocks.extend(row[2] for row in spans)
        applied = {row[2]: row[4] for row in spans}
        new_hash = sha256(content)
        for block_id, entry in lock["blocks"].items():
            if entry["source"] != rel:
                continue
            if block_id in applied:
                entry["text"] = applied[block_id]
                entry["sha256"] = sha256(applied[block_id])
            entry["source_sha256"] = new_hash
            found = locate(content, entry)
            if found:
                entry["char_from"], entry["char_to"] = found
                entry["line_from"] = content[:found[0]].count("\n") + 1
                entry["line_to"] = entry["line_from"] + entry["text"].count("\n")

    if not dry_run and changed_blocks:
        write_text(repo_path(root, LOCK_REL),
                   json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    for block_id, rel, why in refusals:
        sys.stderr.write("REFUSED %s (%s): %s\n" % (block_id, rel, why))

    verb = "would change" if dry_run else "changed"
    if changed_blocks:
        print("%s %d block(s) in %d file(s): %s"
              % (verb, len(changed_blocks), len(set(changed_files)), ", ".join(sorted(set(changed_files)))))
    else:
        print("no changes: every block matches its source")
    if not dry_run and changed_blocks:
        print("line numbers in the deck are now stale; re-run `extract` to refresh them")
    return 1 if refusals else 0


# ------------------------------------------------------ the phone review board --
BOARD_REL = "docs/review-board.html"
ISLAND_OPEN = '<script type="application/json" id="deck-data">'
ISLAND_CLOSE = "</script>"


def short_label(path):
    stem = path.rsplit("/", 1)[-1]
    if "*" in stem:
        stem = path.rsplit("/", 2)[-2]
    return re.sub(r"\.[A-Za-z0-9]+$", "", stem).upper()[:12]


def board_payload(groups):
    surfaces, blocks = [], []
    for surface, group in groups:
        surfaces.append({
            "title": surface["title"],
            "path": surface["path"],
            "note": surface["note"],
            "short": short_label(surface["path"]),
            "ids": [block["id"] for block in group],
        })
        for block in group:
            blocks.append({
                "id": block["id"], "src": block["source"], "anchor": block["anchor"] or "",
                "from": block["line_from"], "to": block["line_to"], "lang": block["lang"],
                "kind": block["kind"], "rw": bool(block["writable"]), "text": block["text"],
            })
    return {"surfaces": surfaces, "blocks": blocks}


def cmd_board(root):
    """Refresh the data island inside docs/review-board.html. The design is hand-written."""
    path = repo_path(root, BOARD_REL)
    if not os.path.exists(path):
        raise SystemExit("no %s — the page is a hand-written file; restore it from git" % BOARD_REL)
    page = read_text(path)
    start = page.find(ISLAND_OPEN)
    if start < 0:
        raise SystemExit("%s has no `%s` island to fill" % (BOARD_REL, ISLAND_OPEN))
    stop = page.find(ISLAND_CLOSE, start + len(ISLAND_OPEN))
    if stop < 0:
        raise SystemExit("%s has an unterminated data island" % BOARD_REL)
    groups, _notes = build(root)
    data = board_payload(groups)
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e")
    page = page[:start + len(ISLAND_OPEN)] + payload + page[stop:]
    write_text(path, page)
    size = len(page.encode("utf-8"))
    print("%s: %d blocks in %d surfaces, %.1f KB"
          % (BOARD_REL, len(data["blocks"]), len(data["surfaces"]), size / 1024.0))
    if size > 200 * 1024:
        sys.stderr.write("warning: the page is over the 200 KB artifact budget\n")
    return 0


# ---------------------------------------------- edits coming back from the board --
def read_edits(source):
    """{id: text} from a Markdown paste, a JSON file, or a directory of JSON documents."""
    if os.path.isdir(source):
        out = {}
        for folder, _dirs, names in os.walk(source):
            for name in sorted(names):
                if name.endswith(".json"):
                    out.update(read_edits(os.path.join(folder, name)))
        return out
    text = read_text(source)
    if source.endswith(".json"):
        data = json.loads(text)
        rows = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and "blocks" in data and isinstance(data["blocks"], dict):
            rows = [dict(row, id=key) for key, row in data["blocks"].items()]
        elif isinstance(data, dict) and "id" not in data:
            rows = [dict(row if isinstance(row, dict) else {"text": row}, id=key)
                    for key, row in data.items()]
        out = {}
        for row in rows:
            if isinstance(row, dict) and row.get("id") and isinstance(row.get("text"), str):
                out[row["id"]] = row["text"]
        return out
    return parse_deck(text)[0]


def cmd_merge(root, source):
    deck_path = repo_path(root, DECK_REL)
    if not os.path.exists(deck_path):
        raise SystemExit("no %s — run `extract` first" % DECK_REL)
    incoming = read_edits(source)
    if not incoming:
        print("nothing to merge: %s carries no block ids" % source)
        return 0
    deck = read_text(deck_path)
    lines = deck.split("\n")
    changed, same, unknown = [], [], []
    edits = []
    for block_id, first, stop, body in scan_deck(deck):
        if block_id not in incoming:
            continue
        if incoming[block_id] == body:
            same.append(block_id)
            continue
        edits.append((first, stop, incoming[block_id].split("\n")))
        changed.append(block_id)
    for block_id in incoming:
        if block_id not in changed and block_id not in same:
            unknown.append(block_id)
    for first, stop, body in sorted(edits, key=lambda row: -row[0]):
        lines[first:stop] = body
    if changed:
        write_text(deck_path, "\n".join(lines))
    for block_id in sorted(changed):
        print("~ %s" % block_id)
    for block_id in sorted(unknown):
        sys.stderr.write("not in the deck, ignored: %s\n" % block_id)
    print("merged %d block(s) into %s (%d already matched, %d unknown)"
          % (len(changed), DECK_REL, len(same), len(unknown)))
    if changed:
        print("next: python3 tools/copy_deck.py apply --dry-run")
    return 0


# ------------------------------------------------------------------------- main --
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=ROOT_DEFAULT, help="repo root (default: this repo)")
    subs = parser.add_subparsers(dest="command")
    ex = subs.add_parser("extract", help="write docs/COPY-DECK.md and the lock")
    ex.add_argument("--force", action="store_true", help="discard unapplied edits in the deck")
    ap = subs.add_parser("apply", help="write edited blocks back to their source files")
    ap.add_argument("--dry-run", action="store_true", help="list the diffs, change nothing")
    ap.add_argument("--strict", action="store_true",
                    help="refuse a file that changed at all since extract")
    subs.add_parser("board", help="refresh the data in docs/review-board.html")
    mg = subs.add_parser("merge", help="fold edits from the board back into the deck")
    mg.add_argument("--from", dest="source", required=True,
                    help="a Markdown paste, a JSON file, or a directory of JSON documents")
    args = parser.parse_args(argv)
    if args.command == "extract":
        return cmd_extract(args.root, force=args.force)
    if args.command == "apply":
        return cmd_apply(args.root, dry_run=args.dry_run, strict=args.strict)
    if args.command == "board":
        return cmd_board(args.root)
    if args.command == "merge":
        return cmd_merge(args.root, args.source)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
