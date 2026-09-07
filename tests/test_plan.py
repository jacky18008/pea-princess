# -*- coding: utf-8 -*-
"""The plan scaffold hands executors a retry ladder, not an abstraction.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

The pipeline pilot (2026-09-07) shipped axes with `scripts: []`; the executor for the
building's age invented a call, had no fallback, and wrote a dead fetch down as zero.
"""
from __future__ import unicode_literals

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import plan  # noqa: E402

# Axes whose evidence at the standard depth is a paste, not a script: reviews (6) and
# aspect (9, a floor plan or a window photo).
PASTE_ONLY_AT_STANDARD = {6, 9}


class TestScaffoldCalls(unittest.TestCase):
    def setUp(self):
        self.plan = plan.scaffold("standard", values={"postcode": "SE1 8BW", "lat": "51.5",
                                                      "lng": "-0.1", "rent_pcm": "2300"})
        self.axes = {axis["id"]: axis for axis in self.plan["axes"]}

    def test_every_scripted_axis_has_a_primary_call_at_standard(self):
        for axis_id in plan.AXES_BY_MODE["standard"]:
            if axis_id in PASTE_ONLY_AT_STANDARD:
                continue
            primaries = [c for c in self.axes[axis_id]["scripts"] if not c.get("fallback")]
            self.assertTrue(primaries, "axis %d ships no primary call" % axis_id)

    def test_fabric_reads_the_whole_building_and_place_walks_three_minutes(self):
        self.assertTrue(any("epc.py building" in c["cmd"] for c in self.axes[3]["scripts"]))
        self.assertTrue(any("geo.py nearby" in c["cmd"] and "--radius 300" in c["cmd"]
                            for c in self.axes[12]["scripts"]))

    def test_fallbacks_are_marked_and_not_required(self):
        fallbacks = [c for axis in self.plan["axes"] for c in axis["scripts"] if c.get("fallback")]
        self.assertGreaterEqual(len(fallbacks), 4)
        for call in fallbacks:
            self.assertIs(True, call["fallback"])
            self.assertIs(False, call["required"])
            self.assertIn("FALLBACK", call["why"])
        shapes = [plan.call_shape(c["cmd"])[:2] for c in fallbacks]
        self.assertIn(("epc.py", "search"), shapes)
        self.assertIn(("planning.py", "planit"), shapes)

    def test_placeholders_are_filled_from_values(self):
        cmds = " ".join(c["cmd"] for axis in self.plan["axes"] for c in axis["scripts"])
        self.assertIn('--postcode "SE1 8BW"', cmds)
        self.assertNotIn("<postcode>", cmds)
        self.assertIn("<building>", cmds, "a value nobody gave stays a placeholder")

    def test_a_plan_that_drops_a_fallback_is_shrunk_too(self):
        """The ladder is part of what the executor needs; a planner may not thin it."""
        thinner = plan.scaffold("standard")
        for axis in thinner["axes"]:
            axis["scripts"] = [c for c in axis["scripts"] if not c.get("fallback")]
        result = plan.check(thinner, "standard")
        self.assertFalse(result["ok"])
        self.assertIn(1, [m["axis"] for m in result["missing_calls"]])

    def test_primary_calls_come_before_fallbacks(self):
        for axis in self.plan["axes"]:
            flags = [bool(c.get("fallback")) for c in axis["scripts"]]
            self.assertEqual(sorted(flags), flags, axis["id"])

    def test_a_plan_that_drops_a_primary_call_is_shrunk(self):
        shrunk = plan.scaffold("standard")
        for axis in shrunk["axes"]:
            if axis["id"] == 3:
                axis["scripts"] = []
        result = plan.check(shrunk, "standard")
        self.assertFalse(result["ok"])
        self.assertTrue(any(m["axis"] == 3 for m in result["missing_calls"]))

    def test_the_scaffold_validates_against_its_schema(self):
        result = plan.check(plan.scaffold("standard"), "standard")
        self.assertTrue(result["schema_ok"], result)
        self.assertTrue(result["ok"], result)
        for mode in ("lite", "deep"):
            self.assertTrue(plan.check(plan.scaffold(mode), mode)["ok"], mode)


if __name__ == "__main__":
    unittest.main()
