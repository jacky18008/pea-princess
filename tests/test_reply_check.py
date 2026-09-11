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


class TestReviewAdditions(unittest.TestCase):
    """From the Opus and Codex terra checkpoint reviews (2026-09-11)."""

    def test_machine_paths_and_file_urls(self):
        found = RC.scan("報告存在 /private/var/folders/ab/T/report.html，打開看。")
        self.assertIn("paths", kinds(found))
        self.assertIn("paths", kinds(RC.scan("see file:///Users/me/Desktop/x.html")))
        self.assertEqual([], [f for f in RC.scan("報告的第一區是排序，第二區是這次改了什麼。") if f["kind"] == "paths"])

    def test_third_person_address(self):
        self.assertIn("address", kinds(RC.scan("使用者可以先看第一戶，這一戶的房租來自你給的頁面，其他兩戶下週再排，都以官方資料為準。")))
        self.assertEqual([], [f for f in RC.scan("你可以先看第一戶，這一戶的房租來自你給的頁面。") if f["kind"] == "address"])

    def test_codes_and_acronyms_need_an_explanation_in_the_sentence(self):
        found = RC.scan("這一戶先 HOLD。")
        self.assertEqual(["terms"], kinds(found)); self.assertIn("HOLD", found[0]["say"])
        self.assertEqual([], [f for f in RC.scan("這一戶先保留（HOLD：等押金證明再決定）。") if f["kind"] == "terms"])
        self.assertIn("terms", kinds(RC.scan("隔壁交了 CEMP，工程快開始了。")))
        self.assertEqual([], [f for f in RC.scan("隔壁交了 CEMP（施工環境管理計畫，開工前的文件），工程快開始了。") if f["kind"] == "terms"])

    def test_an_empty_claim_is_flagged_and_a_full_one_is_not(self):
        self.assertIn("claims", kinds(RC.scan("排序已驗證。房租來自你給的頁面。")))
        self.assertEqual([], [f for f in RC.scan("排序已核對：Anchor 從第 3 升到第 1，因為 Bale 的面積來自能源證書是 41 平方公尺。") if f["kind"] == "claims"])


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
