# -*- coding: utf-8 -*-
"""scripts/panel.py and viewer/requirements.html: the requirements frame no assistant has to write.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
TEMPLATE = os.path.join(ROOT, "viewer", "requirements.html")
PROFILE_TEMPLATE = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")
sys.path.insert(0, SCRIPTS)
import panel  # noqa: E402

SAMPLE = """flat_type: one_bed
occupants: 1
budget_mode: standard
language: "zh-TW"
story_summary: "PRIVATE lines that must never reach the page"
priorities:
  - quiet
  - commute
avoid:
  - "main road or railway facade"
must_haves:
  - washing_machine_in_flat
budget:
  all_in_pcm_ceiling: 2200
commute:
  destination: "Paddington station"
  destination_precision: station
  arrive_by: "09:00"
  max_door_to_door_min: 35
move_in_window:
  earliest: 2026-10-01
  latest: 2026-10-20
floors:
  reject_ground_floor: true
light:
  reject_no_sky: true
  aspect_scores:
    S: 4
quiet_over_light: true
"""


def write_profile(text):
    folder = tempfile.mkdtemp(prefix="vetflat-panel-")
    path = os.path.join(folder, "profile.yaml")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestTemplate(unittest.TestCase):
    def setUp(self):
        self.html = io.open(TEMPLATE, encoding="utf-8").read()

    def test_self_contained_no_network_nothing_stored(self):
        self.assertNotRegex(self.html, r'(?:src|href)="https?://', "the page must load nothing from the network")
        self.assertIn("connect-src 'none'", self.html)
        self.assertNotIn("localStorage", self.html)
        self.assertNotIn("fetch(", self.html)

    def test_has_the_two_data_blocks_and_the_paste_box(self):
        self.assertIn('<script type="application/json" id="pea-profile">{}</script>', self.html)
        self.assertIn('<script type="application/json" id="pea-agent">{}</script>', self.html)
        self.assertIn('id="import"', self.html)
        self.assertIn('id="export"', self.html)

    def test_every_form_key_is_a_profile_key(self):
        keys = set(re.findall(r'data-key="([^"]+)"', self.html))
        known = {"commute.destination", "commute.destination_precision", "commute.arrive_by", "commute.max_door_to_door_min",
                 "flat_type", "occupants", "separate_bedroom_required", "move_in_window.earliest", "move_in_window.latest",
                 "floors.reject_ground_floor", "light.reject_no_sky", "quiet_over_light", "budget_mode", "language"}
        self.assertEqual(known, keys, keys ^ known)
        template = io.open(PROFILE_TEMPLATE, encoding="utf-8").read()
        for key in keys:
            self.assertIn(key.split(".")[-1] + ":", template, key)

    def test_the_deal_breaker_strings_match_onboarding(self):
        onboarding = io.open(os.path.join(ROOT, "skills", "vet-flat", "references", "onboarding.md"), encoding="utf-8").read()
        for avoid in re.findall(r'data-avoid="([^"]+)"', self.html):
            self.assertIn('"%s"' % avoid, onboarding, avoid)

    def test_home_types_match_the_profile_validator(self):
        import profile_check
        options = set(re.findall(r'<select id="flat-type"[^>]*>(.*?)</select>', self.html, re.S)[0].split('value="')[1:])
        values = {o.split('"')[0] for o in options}
        self.assertEqual(profile_check.ENUMS["flat_type"] if hasattr(profile_check, "ENUMS") else values, values)


class TestPanel(unittest.TestCase):
    def test_inlines_the_page_subset_and_nothing_private(self):
        path = write_profile(SAMPLE)
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "panel.py"), "--profile", path,
                               "--summary", "Two areas within 35 minutes of Paddington.", "--next", "Send me a listing page", "--revision", "3"],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        html = proc.stdout
        block = re.search(r'id="pea-profile">(.*?)</script>', html, re.S).group(1)
        data = json.loads(block)
        self.assertEqual("Paddington station", data["commute"]["destination"])
        self.assertEqual(2200, data["budget"]["all_in_pcm_ceiling"])
        self.assertEqual(["quiet", "commute"], data["priorities"])
        self.assertTrue(data["floors"]["reject_ground_floor"])
        self.assertEqual({"reject_no_sky": True}, data["light"])
        self.assertNotIn("story_summary", html)
        self.assertNotIn("PRIVATE", html)
        agent = json.loads(re.search(r'id="pea-agent">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(["Two areas within 35 minutes of Paddington."], agent["summary"])
        self.assertEqual(3, agent["revision"])

    def test_the_repository_template_profile_renders(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "panel.py"), "--profile", PROFILE_TEMPLATE],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn('id="pea-profile">{', proc.stdout)

    def test_a_closing_script_tag_in_a_value_cannot_break_out(self):
        path = write_profile('commute:\n  destination: "</script><b>x</b>"\n')
        html = panel.inline(io.open(TEMPLATE, encoding="utf-8").read(), panel.load_profile(path))
        self.assertNotIn("</script><b>", html)
        self.assertIn("<\\/script>", html)

    def test_missing_profile_is_exit_1(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "panel.py"), "--profile", "/nonexistent/profile.yaml"],
                              capture_output=True, text=True)
        self.assertEqual(1, proc.returncode)


if __name__ == "__main__":
    unittest.main()
