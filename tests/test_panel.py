# -*- coding: utf-8 -*-
"""scripts/panel.py: the requirements page is a read-only view of profile.yaml that no assistant writes by hand.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import io
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
PROFILE_TEMPLATE = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")
sys.path.insert(0, SCRIPTS)
import panel  # noqa: E402

SAMPLE = """flat_type: one_bed
occupants: 1
separate_bedroom_required: true
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
my_questions:
  - question: "Is the ground floor dry?"
budget:
  all_in_pcm_ceiling: 2200
commute:
  destination: "Paddington station <b>x</b>"
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
quiet_over_light: true
"""


def write_profile(text):
    folder = tempfile.mkdtemp(prefix="vetflat-panel-")
    path = os.path.join(folder, "profile.yaml")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestPage(unittest.TestCase):
    def setUp(self):
        self.profile = panel.load_profile(write_profile(SAMPLE))
        self.html = panel.page(self.profile, ["Two areas within 35 minutes of Paddington."], ["Send me a listing page"], revision=3,
                               now="2026-09-11 17:00 UTC")

    def test_it_is_a_view_and_nothing_else(self):
        self.assertNotIn("<script", self.html)
        self.assertNotIn("<form", self.html)
        self.assertNotIn("<input", self.html)
        self.assertNotRegex(self.html, r'(?:src|href)="https?://')
        self.assertIn("default-src 'none'", self.html)

    def test_every_value_the_person_gave_is_on_the_page_and_escaped(self):
        for needle in ("Paddington station", "車站 · station", "£2,200", "一房 · one-bed", "2026-10-01", "2026-10-20",
                       "安靜 · quiet", "通勤 · commute", "不考慮地面層", "要看得到天空", "安靜比採光重要",
                       "不臨大馬路或鐵路", "屋內要有洗衣機", "Is the ground floor dry?", "到達 09:00", "最長 35 分鐘"):
            self.assertIn(needle, self.html, needle)
        self.assertNotIn("<b>x</b>", self.html)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", self.html)

    def test_private_fields_never_reach_the_page(self):
        self.assertNotIn("PRIVATE", self.html)
        self.assertNotIn("story_summary", self.html)

    def test_the_assistant_block_and_revision(self):
        self.assertIn("Two areas within 35 minutes of Paddington.", self.html)
        self.assertIn("Send me a listing page", self.html)
        self.assertIn("revision 3", self.html)
        self.assertIn("三個核心都有了", self.html)

    def test_blank_means_unknown_not_a_guess(self):
        html = panel.page({"flat_type": "any"})
        self.assertIn("還不知道 · not yet known", html)
        self.assertIn("目的地還不明確", html)
        self.assertIn("每月上限還沒定", html)
        self.assertIn("入住時間還沒定", html)
        self.assertIn("房型還沒決定", html)
        self.assertNotIn("助理的摘要", html)

    def test_rent_only_budget_says_bills_are_not_counted(self):
        html = panel.page({"budget": {"rent_pcm_target": 1500}, "commute": {"destination": "Bank", "destination_precision": "district"}})
        self.assertIn("只含房租", html)
        self.assertIn("帳單還沒算進去", html)
        self.assertIn("通勤只能估", html)

    def test_total_ceiling_explicitly_includes_council_tax(self):
        self.assertIn("£2,200／月，房租＋帳單＋council tax · rent + bills + council tax", self.html)


class TestCli(unittest.TestCase):
    def test_the_repository_template_profile_renders_to_a_file(self):
        out = os.path.join(tempfile.mkdtemp(prefix="vetflat-panel-"), "requirements.html")
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "panel.py"), "--profile", PROFILE_TEMPLATE, "--out", out],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        html = io.open(out, encoding="utf-8").read()
        self.assertIn("我的需求 · My requirements", html)
        self.assertIn("wrote", proc.stderr)

    def test_missing_profile_is_exit_1(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "panel.py"), "--profile", "/nonexistent/profile.yaml"],
                              capture_output=True, text=True)
        self.assertEqual(1, proc.returncode)


if __name__ == "__main__":
    unittest.main()
