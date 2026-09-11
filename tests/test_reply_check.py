# -*- coding: utf-8 -*-
"""scripts/reply_check.py: the pre-send check for numbers without a source, jargon, simplified
characters and questions after a go-ahead.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import reply_check as RC  # noqa: E402


def kinds(findings):
    return sorted(set(f["kind"] for f in findings))


class TestNumbers(unittest.TestCase):
    def test_a_number_with_a_cue_passes_and_one_without_is_flagged(self):
        self.assertEqual([], RC.scan("Southerton 比 Milton 便宜 £450，這兩個數字來自你給的 PDF。"))
        self.assertEqual([], RC.scan("附近半年犯罪 255 件（警方資料）。"))
        self.assertEqual([], RC.scan("通勤大約 37 分鐘。"))
        found = RC.scan("押金最多 5 週房租。")
        self.assertEqual(["numbers"], kinds(found))
        self.assertIn("5 週", found[0]["say"])

    def test_dates_and_times_are_not_numbers(self):
        self.assertEqual([], RC.scan("2026-05-01 起適用。9/21 開學。09:00 到。"))


class TestJargon(unittest.TestCase):
    def test_codes_files_skill_names_and_internal_words(self):
        found = RC.scan("信⑲ 還沒回。證據等級是 G。見 `report.json`，用 vet-flat 的 L4 規則判。")
        self.assertEqual(["jargon"], kinds(found))
        says = " ".join(f["say"] for f in found)
        for word in ("圈號", "內部編號", "反引號", "檔名", "技能名稱"):
            self.assertIn(word, says, word)

    def test_plain_language_passes(self):
        self.assertEqual([], RC.scan("這一戶的面積來自官方能源證書，48 平方公尺；廣告寫的 52 是仲介自述。"))


class TestScriptAndAsking(unittest.TestCase):
    def test_simplified_characters_in_a_traditional_reply(self):
        text = "這一間的房租來自你給的頁面，每月 £1,800。我們先看看它的問題在哪裡，再決定要不要約看房。" + "这个问题很重要，我们来说说。"
        found = RC.scan(text)
        self.assertIn("script", kinds(found))
        self.assertEqual([], [f for f in RC.scan("這一間的房租來自你給的頁面，每月 £1,800，我們先看它的問題。") if f["kind"] == "script"])

    def test_more_than_three_questions_and_questions_after_a_go_ahead(self):
        self.assertEqual(["asking"], kinds(RC.scan("要嗎？好嗎？行嗎？可以嗎？")))
        self.assertEqual(["asking"], kinds(RC.scan("要不要我現在就查？", previous="都同意，Go")))
        self.assertEqual([], RC.scan("查好了：這三間裡兩間過關。", previous="都同意，Go"))


class TestOpening(unittest.TestCase):
    def test_a_praise_opener_is_flagged_and_an_answer_is_not(self):
        self.assertEqual(["opening"], kinds(RC.scan("問得好——這件事要分兩層看。")))
        self.assertEqual(["opening"], kinds(RC.scan("**你說得對**，橋接不是額外成本。")))
        self.assertEqual([], RC.scan("橋接不是額外成本：那一週你付的是週租，不是長租的房租。"))


class TestCli(unittest.TestCase):
    def test_exit_code_and_json(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "reply_check.py"), "-", "--json"],
                              input="押金最多 5 週房租。", capture_output=True, text=True)
        self.assertEqual(1, proc.returncode)
        out = json.loads(proc.stdout)
        self.assertFalse(out["ok"]); self.assertEqual(1, out["counts"]["numbers"])
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "reply_check.py"), "-"],
                              input="這一戶的面積來自官方能源證書。", capture_output=True, text=True)
        self.assertEqual(0, proc.returncode)
        self.assertIn("clean", proc.stdout)


if __name__ == "__main__":
    unittest.main()
