# -*- coding: utf-8 -*-
"""bench/history_replay.py: the date of the message being answered comes from the case's sidecar.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import history_replay as H  # noqa: E402


class TestCaseDate(unittest.TestCase):
    def setUp(self):
        self.corpus = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.corpus, "cases"))
        case = {"case_id": "case-01",
                "prefix": [{"role": "user", "timestamp": "2026-08-14T23:50:00.000Z"}, {"role": "assistant", "timestamp": "2026-08-15T12:36:55.524Z"}],
                "reaction": {"role": "user", "timestamp": "2026-08-15T12:45:15.495Z"}}
        io.open(os.path.join(self.corpus, "cases", "case-01.json"), "w", encoding="utf-8").write(json.dumps(case))

    def test_ask_uses_the_last_prefix_record_and_reaction_its_own_stamp(self):
        self.assertEqual("2026-08-15", H.case_date(self.corpus, "case-01", "ask"))
        self.assertEqual("2026-08-15", H.case_date(self.corpus, "case-01", "reaction"))
        self.assertIsNone(H.case_date(self.corpus, "case-99", "ask"))

    def test_the_prompt_states_the_date_only_when_given(self):
        with_date = H.answer_prompt([("user", "hi")], "還有嗎", today="2026-08-15")
        self.assertIn("今天是 2026-08-15", with_date)
        self.assertNotIn("今天是", H.answer_prompt([("user", "hi")], "還有嗎"))


if __name__ == "__main__":
    unittest.main()
