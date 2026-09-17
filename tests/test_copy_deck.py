"""Guards for the copy deck: deterministic extract, safe write-back, no silent corruption."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, "tools", "copy_deck.py")

_spec = importlib.util.spec_from_file_location("copy_deck", TOOL)
copy_deck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(copy_deck)


# --------------------------------------------------------------- a small fake repo --
FILES = {
    "README.md": """\
# Fake Princess

**EN** — A skill that vets a flat. This is the first prose paragraph and it is
long enough to be worth rewriting.

**繁中** — 這是一個不綁定任何廠商的技能，用官方與公開的資料審查一間出租公寓，最後給出白話判決。

> Status: **draft**. Everything here is a fixture.

## Modes
| Mode | You have |
|---|---|
| Shell | python3 |

## Install
```bash
npx skills add example/example
```
Codex: enable sandbox network or use manual mode.

## Why
In the fairy tale only the real princess feels the pea. Here you are the princess.
""",
    "docs/INSTALL.md": """\
# Install

Part of Pea Princess (vet-flat) by Somebody — CC BY 4.0
Verified against vendor documentation on 2026-09-03.

## A. Agents with a shell

The skill does not care which harness runs it.

| Product | Install |
|---|---|
| Claude Code | a command |
""",
    "docs/EXPERIMENTS.md": """\
Part of Pea Princess (vet-flat) by Somebody — CC BY 4.0

# Experiments

This page exists so you can choose with evidence instead of vibes.

**The public default is a cheap model for the workers.** The numbers are below.

## Results

| Arm | Recall |
|---|---|
| `B-lean` | 0.57 |

## What it means

- **Scripts cost nothing and save the bill.** The clean one-factor pair is
  `B-lean` against `B-raw`, and the finding rate is identical.
- **Breadth is what finds landmines.** You pay for breadth.

## Caveats

Five flats only.
""",
    "skills/vet-flat/references/onboarding.md": """\
Part of Pea Princess (vet-flat) by Somebody — CC BY 4.0

# What this skill does

Read this when the user asks what it can do.

## 1. The pitch

**English**
> I check a flat the way a careful surveyor would, using official data.

**繁體中文**
> 我用官方與公開資料，像謹慎的驗屋師一樣審查一間出租公寓，最後給出白話判決。

**简体中文**
> 我用官方与公开数据，像谨慎的验房师一样审查一套出租公寓，最后给出白话结论。

Then offer the starting points:
1. **I have a listing** → paste it and I vet it.
2. **I have an area** → I sweep around it.

Do not list the axes in the pitch.

## 2. Intake

| # | Ask |
|---|---|
| 1 | Where to? |

## 3. Primer

1. **Timing.** Listings appear four to eight weeks before the move-in date.
2. **What you pay.** Rent, plus council tax and energy.

## 4. Short answers

- **Only London?** The law is England-wide.
- **Do you scrape portals?** No. Their terms forbid it.
""",
    "skills/vet-flat/references/sharing.md": """\
Part of Pea Princess (vet-flat) by Somebody — CC BY 4.0

# Sharing a seed

## 3. Share your questions

> If this is unusually cheap, what is the hidden problem?

## 4. The social post, ready to send

**English**

> I found a flat with this seed — paste it into any agent.

**繁體中文**

> 我用這組條件碼找到房子了——把它貼給任何裝了這個技能的代理。

## 5. Something else

Not in the deck.

## 6. Importing somebody else's seed

> This is somebody else's taste, not a recommendation.
""",
    "skills/vet-flat/references/inputs.md": """\
# When the agent cannot get something

Part of Pea Princess (vet-flat). CC BY 4.0.

## What to ask for

| Axis | Try first |
|---|---|
| Identity | a script |

## Template for the ask (copy, fill, send once)
```
I can finish X of 12 axes myself. To complete the rest I need 2 things:
1. The certificate page for the flat.
2. The floor plan image from the listing.
```
""",
    "skills/vet-flat/profiles/example-fixture.yaml": """\
# Part of Pea Princess (vet-flat) — CC BY 4.0

flat_type: one_bed

my_questions:
  - text: "If this flat is unusually cheap, what is the hidden problem?"
    when: compare
    kind: answer
  - text: "If it is pricier, am I buying value I care about?"
    when: compare

self_intro_template: >-
  I am a full-time postgraduate student looking for a home for one person,
  non-smoking, no pets.

story_summary: >-
  Cares more about sleeping well than about views.
  Has been burned by bills that only appeared after signing.
story_taken_on: "2026-09-05"
""",
    "skills/vet-flat/scripts/seed.py": '''\
"""A fixture that looks like the real seed script."""


def sentences(seed):
    """Three sentences."""
    one = "I want %s" % seed
    two = "I will not take: %s." % seed
    three = ("Price is not in my top three: I will pay to the top of the band "
             "for a benefit I can name")
    return [one, two, three, seed.get("flat_type")]


def card(seed, code):
    out = ["Pea Princess seed",
           "what I am looking for, and nothing about where I live.",
           "seed:"]
    return "\\n".join(out) + code


def journey_lines(journey):
    return ["what I found: %d flats vetted" % len(journey), "the one I took"]
''',
}


def make_repo():
    root = tempfile.mkdtemp(prefix="copydeck-")
    for rel, body in FILES.items():
        full = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)
    return root


def read(root, rel):
    with open(os.path.join(root, rel.replace("/", os.sep)), encoding="utf-8") as fh:
        return fh.read()


def write(root, rel, body):
    with open(os.path.join(root, rel.replace("/", os.sep)), "w", encoding="utf-8") as fh:
        fh.write(body)


class DeckCase(unittest.TestCase):
    def setUp(self):
        self.root = make_repo()
        self.addCleanup(shutil.rmtree, self.root, True)

    @staticmethod
    def quietly(call):
        """The tool talks to a person; a test run should not have to listen."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return call()

    def run_extract(self, force=False):
        return self.quietly(lambda: copy_deck.cmd_extract(self.root, force=force))

    def extract(self, force=False):
        self.assertEqual(0, self.run_extract(force=force))
        return read(self.root, copy_deck.DECK_REL)

    def apply(self, dry_run=False):
        return self.quietly(lambda: copy_deck.cmd_apply(self.root, dry_run=dry_run))

    def lock(self):
        return json.loads(read(self.root, copy_deck.LOCK_REL))


class TestExtract(DeckCase):
    def test_html_layout_blocks_are_not_copy(self):
        lines = ['<p align="center">', '  <img src="x.png" width="300" alt="hero">', '</p>', '',
                 '<h1 align="center">Pea Princess</h1>', '', 'A real paragraph.', '',
                 '<details>', '<summary><b>For engineers</b></summary>', '', 'Inside the fold.', '', '</details>']
        kinds = [(kind, lines[first]) for kind, first, _last, _a, _b in copy_deck.md_chunks(lines, 0, len(lines))]
        self.assertEqual([k for k, _ in kinds], ["html", "html", "para", "html", "para", "html"])
        self.assertEqual([line for k, line in kinds if k == "para"], ["A real paragraph.", "Inside the fold."])

    def test_deterministic(self):
        first, first_lock = self.extract(), read(self.root, copy_deck.LOCK_REL)
        second, second_lock = self.extract(), read(self.root, copy_deck.LOCK_REL)
        self.assertEqual(first, second, "same sources must give a byte-identical deck")
        self.assertEqual(first_lock, second_lock, "same sources must give a byte-identical lock")

    def test_ids_are_unique_and_well_formed(self):
        deck = self.extract()
        blocks, order = copy_deck.parse_deck(deck)
        self.assertEqual(len(order), len(set(order)), "duplicate id in the deck")
        self.assertEqual(set(order), set(self.lock()["blocks"]), "deck and lock disagree on ids")
        for block_id in order:
            self.assertRegex(block_id, r"^deck:[a-z0-9-]+:\d+$")

    def test_every_block_is_verbatim_from_its_source(self):
        self.extract()
        for block_id, entry in self.lock()["blocks"].items():
            source = read(self.root, entry["source"])
            self.assertIn(entry["text"], source, block_id)
            self.assertEqual(copy_deck.sha256(entry["text"]), entry["sha256"], block_id)

    def test_covers_every_surface_and_excludes_the_model_facing_parts(self):
        deck = self.extract()
        sources = {e["source"] for e in self.lock()["blocks"].values()}
        self.assertEqual(sources, {
            "README.md", "docs/INSTALL.md", "docs/EXPERIMENTS.md",
            "skills/vet-flat/references/onboarding.md",
            "skills/vet-flat/references/sharing.md",
            "skills/vet-flat/references/inputs.md",
            "skills/vet-flat/profiles/example-fixture.yaml",
            "skills/vet-flat/scripts/seed.py",
        })
        self.assertIn("In the fairy tale only the real princess feels the pea.", deck)
        self.assertIn("I check a flat the way a careful surveyor would", deck)
        self.assertIn("**Timing.** Listings appear four to eight weeks", deck)
        self.assertIn("I found a flat with this seed", deck)
        self.assertIn("I can finish X of 12 axes myself", deck)
        self.assertIn("Cares more about sleeping well", deck)
        # tables, code fences and model-facing sections stay out
        self.assertNotIn("npx skills add example/example", deck)
        self.assertNotIn("| Shell | python3 |", deck)
        self.assertNotIn("Do not list the axes in the pitch", deck)
        self.assertNotIn("Not in the deck.", deck)
        self.assertNotIn("Five flats only.", deck)
        self.assertNotIn("Part of Pea Princess (vet-flat) by Somebody", deck)

    def test_languages(self):
        self.extract()
        langs = {}
        for entry in self.lock()["blocks"].values():
            langs.setdefault(entry["lang"], []).append(entry["text"])
        self.assertTrue(any("驗屋師" in t for t in langs.get("zh-TW", [])))
        self.assertTrue(any("验房师" in t for t in langs.get("zh-CN", [])))
        self.assertTrue(any("careful surveyor" in t for t in langs.get("en", [])))

    def test_refuses_to_discard_unapplied_edits(self):
        deck = self.extract()
        write(self.root, copy_deck.DECK_REL, deck.replace("Here you are the princess.",
                                                          "Here YOU are the princess.", 1))
        self.assertEqual(1, self.run_extract())
        self.assertIn("Here YOU are the princess.", read(self.root, copy_deck.DECK_REL))
        self.assertEqual(0, self.run_extract(force=True))
        self.assertNotIn("Here YOU are the princess.", read(self.root, copy_deck.DECK_REL))


class TestApply(DeckCase):
    def test_round_trips_with_no_edits(self):
        deck = self.extract()
        before = {rel: read(self.root, rel) for rel in FILES}
        self.assertEqual(0, self.apply())
        for rel, body in before.items():
            self.assertEqual(body, read(self.root, rel), "%s changed on a no-op apply" % rel)
        self.assertEqual(deck, self.extract(), "extract → apply → extract must be a fixed point")

    def test_a_changed_block_is_written_back(self):
        self.extract()
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL,
              deck.replace("In the fairy tale only the real princess feels the pea.",
                           "Only the real princess feels the pea, through twenty mattresses.", 1))
        self.assertEqual(0, self.apply())
        readme = read(self.root, "README.md")
        self.assertIn("Only the real princess feels the pea, through twenty mattresses.", readme)
        self.assertNotIn("In the fairy tale only", readme)
        # the lock now carries the new text, so a second apply is a no-op
        self.assertEqual(0, self.apply())
        self.assertEqual(readme, read(self.root, "README.md"))

    def test_dry_run_changes_nothing(self):
        self.extract()
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL, deck.replace("Here you are the princess.",
                                                          "Here you are the pea.", 1))
        before = read(self.root, "README.md")
        self.assertEqual(0, self.apply(dry_run=True))
        self.assertEqual(before, read(self.root, "README.md"))

    def test_a_yaml_block_keeps_its_shape(self):
        self.extract()
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL,
              deck.replace("  Cares more about sleeping well than about views.",
                           "  Cares about sleep, not views.", 1))
        self.assertEqual(0, self.apply())
        profile = read(self.root, "skills/vet-flat/profiles/example-fixture.yaml")
        self.assertIn("story_summary: >-\n  Cares about sleep, not views.", profile)

    def test_a_moved_source_is_refused_and_nothing_is_written(self):
        self.extract()
        readme = read(self.root, "README.md")
        write(self.root, "README.md",
              readme.replace("In the fairy tale only the real princess feels the pea.",
                             "In the story only the real princess feels the pea.", 1))
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL,
              deck.replace("In the fairy tale only the real princess feels the pea.",
                           "A princess feels the pea through twenty mattresses.", 1))
        after = read(self.root, "README.md")
        self.assertEqual(1, self.apply(), "a moved source must make apply fail")
        self.assertEqual(after, read(self.root, "README.md"), "the source must be left alone")
        self.assertNotIn("A princess feels the pea", read(self.root, "README.md"))

    def test_an_ambiguous_match_is_refused(self):
        """Two copies of the block, and the recorded position no longer holds it."""
        self.extract()
        entry = [e for e in self.lock()["blocks"].values()
                 if e["source"] == "README.md" and "fairy tale" in e["text"]][0]
        readme = read(self.root, "README.md")
        write(self.root, "README.md", entry["text"] + "\n\n" + readme)
        after = read(self.root, "README.md")
        self.assertEqual(2, after.count(entry["text"]))
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL, deck.replace(entry["text"], "Rewritten.", 1))
        self.assertEqual(1, self.apply())
        self.assertEqual(after, read(self.root, "README.md"))
        self.assertNotIn("Rewritten.", read(self.root, "README.md"))

    def test_an_unmoved_block_still_applies_when_a_copy_appears_elsewhere(self):
        """The recorded position wins: a duplicate added below must not block the edit."""
        self.extract()
        entry = [e for e in self.lock()["blocks"].values()
                 if e["source"] == "README.md" and "fairy tale" in e["text"]][0]
        write(self.root, "README.md", read(self.root, "README.md") + "\n" + entry["text"] + "\n")
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL, deck.replace(entry["text"], "Rewritten.", 1))
        self.assertEqual(0, self.apply())
        readme = read(self.root, "README.md")
        self.assertIn("Rewritten.", readme)
        self.assertEqual(1, readme.count(entry["text"]), "only the tracked copy may change")

    def test_a_read_only_block_is_refused(self):
        self.extract()
        block_id = [k for k, v in self.lock()["blocks"].items()
                    if v["source"].endswith("seed.py") and "Pea Princess seed" in v["text"]][0]
        self.assertFalse(self.lock()["blocks"][block_id]["writable"])
        deck = read(self.root, copy_deck.DECK_REL)
        write(self.root, copy_deck.DECK_REL,
              deck.replace('"Pea Princess seed"', '"Pea Princess Seed Card"', 1))
        before = read(self.root, "skills/vet-flat/scripts/seed.py")
        self.assertEqual(1, self.apply())
        self.assertEqual(before, read(self.root, "skills/vet-flat/scripts/seed.py"))

    def test_two_edits_in_one_file_both_land(self):
        self.extract()
        deck = read(self.root, copy_deck.DECK_REL)
        deck = deck.replace("**Timing.** Listings appear four to eight weeks",
                            "**Timing.** Listings show up four to eight weeks", 1)
        deck = deck.replace("- **Only London?** The law is England-wide.",
                            "- **Only London?** The law covers all of England.", 1)
        write(self.root, copy_deck.DECK_REL, deck)
        self.assertEqual(0, self.apply())
        body = read(self.root, "skills/vet-flat/references/onboarding.md")
        self.assertIn("Listings show up four to eight weeks", body)
        self.assertIn("The law covers all of England.", body)


class TestBoardAndMerge(DeckCase):
    """The phone board writes edits out; `merge` folds them back into the deck."""

    def test_board_refreshes_its_data_island(self):
        self.extract()
        page = os.path.join(self.root, copy_deck.BOARD_REL)
        os.makedirs(os.path.dirname(page), exist_ok=True)
        write(self.root, copy_deck.BOARD_REL,
              "<title>x</title>\n" + copy_deck.ISLAND_OPEN + "{}" + copy_deck.ISLAND_CLOSE + "\n")
        self.assertEqual(0, self.quietly(lambda: copy_deck.cmd_board(self.root)))
        body = read(self.root, copy_deck.BOARD_REL)
        island = body.split(copy_deck.ISLAND_OPEN, 1)[1].split(copy_deck.ISLAND_CLOSE, 1)[0]
        data = json.loads(island.replace("<\\/", "</"))
        self.assertNotIn("</script", island, "the island must not be able to close its own tag")
        self.assertEqual(len(data["blocks"]), len(self.lock()["blocks"]))
        self.assertTrue(all(s["ids"] for s in data["surfaces"]))
        ids = [b["id"] for b in data["blocks"]]
        self.assertEqual(sorted(ids), sorted(self.lock()["blocks"]))

    def test_merge_from_markdown_then_apply(self):
        self.extract()
        block_id = [k for k, v in self.lock()["blocks"].items()
                    if v["source"] == "README.md" and "fairy tale" in v["text"]][0]
        paste = os.path.join(self.root, "edits.md")
        with open(paste, "w", encoding="utf-8") as fh:
            fh.write("### %s\n\n```text\nOnly a real princess feels it.\n```\n" % block_id)
        self.assertEqual(0, self.quietly(lambda: copy_deck.cmd_merge(self.root, paste)))
        self.assertIn("Only a real princess feels it.", read(self.root, copy_deck.DECK_REL))
        self.assertEqual(0, self.apply())
        self.assertIn("Only a real princess feels it.", read(self.root, "README.md"))

    def test_merge_from_json_documents_and_ignores_unknown_ids(self):
        self.extract()
        block_id = [k for k, v in self.lock()["blocks"].items()
                    if v["source"] == "README.md" and "fairy tale" in v["text"]][0]
        folder = os.path.join(self.root, "out", "edits")
        os.makedirs(folder)
        with open(os.path.join(folder, "one.json"), "w", encoding="utf-8") as fh:
            json.dump({"id": block_id, "text": "A princess, a pea, twenty mattresses."}, fh)
        with open(os.path.join(folder, "ghost.json"), "w", encoding="utf-8") as fh:
            json.dump({"id": "deck:nowhere:9", "text": "ignored"}, fh)
        self.assertEqual(0, self.quietly(
            lambda: copy_deck.cmd_merge(self.root, os.path.join(self.root, "out"))))
        deck = read(self.root, copy_deck.DECK_REL)
        self.assertIn("A princess, a pea, twenty mattresses.", deck)
        self.assertNotIn("ignored", deck)
        self.assertEqual(0, self.apply())
        self.assertIn("A princess, a pea, twenty mattresses.", read(self.root, "README.md"))


class TestAgainstTheRealRepo(unittest.TestCase):
    """Read-only: the deck must describe this repo without writing to it."""

    def test_builds_and_every_block_is_present_in_its_source(self):
        with contextlib.redirect_stderr(io.StringIO()):
            groups, _notes = copy_deck.build(ROOT)
        ids = []
        for _surface, blocks in groups:
            for block in blocks:
                ids.append(block["id"])
                source = os.path.join(ROOT, block["source"])
                with open(source, encoding="utf-8") as fh:
                    self.assertIn(block["text"], fh.read(), block["id"])
        self.assertEqual(len(ids), len(set(ids)), "ids must be unique across the whole deck")
        self.assertGreater(len(ids), 40, "the deck should not be nearly empty")

    def test_the_board_page_is_current_and_within_budget(self):
        page = os.path.join(ROOT, copy_deck.BOARD_REL)
        if not os.path.exists(page):
            self.skipTest("no board page committed yet")
        with open(page, encoding="utf-8") as fh:
            body = fh.read()
        self.assertLess(len(body.encode("utf-8")), 200 * 1024, "the board must stay under 200 KB")
        self.assertIn("<title>Pea Princess Copy Deck</title>", body)
        for tag in ("<!doctype", "<html", "<head>", "<body>"):
            self.assertNotIn(tag, body.lower(), "the publisher supplies the page skeleton")
        island = body.split(copy_deck.ISLAND_OPEN, 1)[1].split(copy_deck.ISLAND_CLOSE, 1)[0]
        data = json.loads(island.replace("<\\/", "</"))
        with contextlib.redirect_stderr(io.StringIO()):
            groups, _notes = copy_deck.build(ROOT)
        live = [b["id"] for _s, blocks in groups for b in blocks]
        self.assertEqual(sorted(b["id"] for b in data["blocks"]), sorted(live),
                         "the board is stale: run `python3 tools/copy_deck.py board`")

    def test_the_committed_deck_matches_the_sources(self):
        deck_path = os.path.join(ROOT, copy_deck.DECK_REL)
        if not os.path.exists(deck_path):
            self.skipTest("no deck committed yet")
        self.assertEqual([], copy_deck.pending_edits(ROOT),
                         "the deck has edits that were never applied: run "
                         "`python3 tools/copy_deck.py apply`")


class TestWritebackSecurity(DeckCase):
    def save_lock(self, lock):
        write(self.root, copy_deck.LOCK_REL, json.dumps(lock))

    def test_lock_cannot_target_absolute_parent_or_unregistered_paths(self):
        self.extract()
        original = self.lock()
        first = next(iter(original["blocks"]))
        for source in ("../outside.txt", "/tmp/outside.txt", "local-secret.txt"):
            lock = json.loads(json.dumps(original))
            lock["blocks"][first]["source"] = source
            self.save_lock(lock)
            with self.assertRaisesRegex(SystemExit, "unsafe|registered surface"):
                self.apply()

    def test_allowed_surface_symlink_is_refused_before_writeback(self):
        self.extract()
        original = read(self.root, "README.md")
        target = os.path.join(self.root, "outside.txt")
        write(self.root, "outside.txt", original)
        os.unlink(os.path.join(self.root, "README.md"))
        os.symlink(target, os.path.join(self.root, "README.md"))
        with self.assertRaisesRegex(SystemExit, "symlinks"):
            self.apply()
        self.assertEqual(original, read(self.root, "outside.txt"))

    def test_lock_cannot_promote_a_read_only_source(self):
        self.extract()
        lock = self.lock()
        entry = next(e for e in lock["blocks"].values() if not e["writable"])
        entry["writable"] = True
        self.save_lock(lock)
        with self.assertRaisesRegex(SystemExit, "read-only surface"):
            self.apply()

    def test_board_json_escapes_html_parser_state_delimiters(self):
        # A paragraph that carries markup (a line that *starts* with a tag is layout, not copy).
        payload = "Untrusted: <!--<script> untrusted </ScRiPt><img src=x onerror=alert(1)>"
        write(self.root, "README.md", "# Example\n\n" + payload + "\n")
        write(self.root, copy_deck.BOARD_REL,
              copy_deck.ISLAND_OPEN + "{}" + copy_deck.ISLAND_CLOSE)
        self.quietly(lambda: copy_deck.cmd_board(self.root))
        page = read(self.root, copy_deck.BOARD_REL)
        island = page.split(copy_deck.ISLAND_OPEN, 1)[1].split(copy_deck.ISLAND_CLOSE, 1)[0]
        self.assertNotIn("<", island)
        self.assertTrue(any(b["text"] == payload for b in json.loads(island)["blocks"]))


if __name__ == "__main__":
    unittest.main()
