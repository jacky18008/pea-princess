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

    def test_web_citations_stay_with_the_numbered_claim(self):
        replies = [
            "[房源頁](https://www.example.org/uk/flat) 列出「£2,250 pcm」「484 sq ft」。",
            "[Example.co.uk](https://www.example.org/flat?view=facts) lists £2,250 pcm.",
            "£2,250 pcm (https://www.example.org/flat).",
            "租金 £2,250，https://www.example.org/flat。",
            "[房源頁](https://www.example.org/flat_(first.floor)) 列出 £2,250。",
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                self.assertNotIn("numbers", kinds(RC.scan(reply)))

    def test_a_link_in_another_sentence_does_not_source_a_number(self):
        replies = [
            "See https://www.example.org/flat. Rent is £2,250.",
            "See [page](https://www.example.org/flat). Rent is £2,250.",
            "£2,250 pcm. See https://www.example.org/flat.",
            "[房源頁](https://www.example.org/flat)\n租金 £2,250。",
            "£2,250 pcm (file:///tmp/page).",
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                self.assertIn("numbers", kinds(RC.scan(reply)))

    def test_decimal_points_do_not_detach_sources_or_hide_amounts(self):
        self.assertNotIn("numbers", kinds(RC.scan("根據頁面，每月 £2,250.50，面積 44.9 平方公尺。")))
        found = [f for f in RC.scan("面積 44.9 平方公尺。") if f["kind"] == "numbers"]
        self.assertEqual(1, len(found))
        self.assertIn("44.9 平方公尺", found[0]["say"])


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
        self.assertIn("terms", kinds(RC.scan("隔壁交了 CEMP [文件](https://www.example.org/record)。")))

    def test_an_empty_claim_is_flagged_and_a_full_one_is_not(self):
        self.assertIn("claims", kinds(RC.scan("排序已驗證。房租來自你給的頁面。")))
        self.assertEqual([], [f for f in RC.scan("排序已核對：Anchor 從第 3 升到第 1，因為 Bale 的面積來自能源證書是 41 平方公尺。") if f["kind"] == "claims"])

    def test_negated_verification_is_not_an_affirmative_claim(self):
        replies = [
            "以上是廣告聲稱，並非已確認的可租狀態。",
            "這不是已驗證的房源。",
            "不能視為已確認的可租狀態。",
            "Availability is not confirmed.",
            "Availability has not yet been independently verified.",
            "Availability hasn't been confirmed.",
            "Availability was never verified.",
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                self.assertNotIn("claims", kinds(RC.scan(reply)))

    def test_negation_does_not_excuse_another_affirmative_claim(self):
        replies = [
            "這不是已確認的租金，但可租狀態已確認。",
            "The rent is not confirmed, but availability is confirmed.",
            "Availability is not only confirmed but guaranteed.",
            "沒有照片，但可租狀態已確認。",
            "已確認可租。[房源頁](https://www.example.org/flat)。",
            "可租狀態已確認 [房源頁](https://www.example.org/flat/2250)。",
        ]
        for reply in replies:
            with self.subTest(reply=reply):
                self.assertIn("claims", kinds(RC.scan(reply)))


class TestAuthority(unittest.TestCase):
    """2026-09-13: Terra turned "偏好安靜" into "只有…才值得"; the checker now flags a necessity or exclusion
    that quotes neither the person nor a proposal marker, and no longer flags scan-derived figures."""

    def test_a_condition_without_the_persons_words_or_a_proposal_marker_is_flagged(self):
        found = RC.scan("Southerton 只有在臥室背向主幹道、晚間實聽仍可接受時，才值得用每月省下的錢交換。")
        self.assertIn("authority", kinds(found)); self.assertIn("我建議先確認", [f for f in found if f["kind"] == "authority"][0]["say"])
        self.assertIn("authority", kinds(RC.scan("臥室正對大馬路的房源一律排除。")))

    def test_the_persons_own_rule_and_an_explicit_suggestion_pass(self):
        self.assertEqual([], [f for f in RC.scan("你說臥室正對大馬路就排除，所以 B 要先確認窗向。") if f["kind"] == "authority"])
        self.assertEqual([], [f for f in RC.scan("我建議先確認臥室朝向；如果背向主幹道，Southerton 才值得看。") if f["kind"] == "authority"])
        self.assertEqual([], [f for f in RC.scan("Only if you want it: I would rule out B until the bedroom side is known.") if f["kind"] == "authority"])

    def test_decision_flags_wording_stronger_than_the_persons(self):
        # 2026-09-15 Grok Bot validation: 可考慮看房 became 可排看房; an unanswered offer became 已拒
        self.assertIn("decision", kinds(RC.scan("好，A 目前可排看房，我把它列為下一步。")))
        self.assertIn("decision", kinds(RC.scan("B 的例外已拒，先不深挖。")))
        self.assertIn("decision", kinds(RC.scan("A viewing is booked for Thursday.")))
        self.assertIn("你還沒回應", [f for f in RC.scan("B 的例外已拒。") if f["kind"] == "decision"][0]["say"])

    def test_decision_keeps_the_persons_words_and_proposals(self):
        for ok in ("你說 A 可以考慮看房，B 的條件不變。", "如果你同意，我再幫你排看房。", "A 你先留著，先不約看。",
                   "你已預約週四看 A，我列出當天要確認的三件事。", "仲介回信說「已排週四」，你要不要去？",
                   "You said A may be considered for a viewing; nothing is booked."):
            self.assertEqual([], [f for f in RC.scan(ok) if f["kind"] == "decision"], ok)

    def test_scan_and_saved_data_count_as_a_source_for_numbers(self):
        self.assertEqual([], [f for f in RC.scan("保存資料在 300 米內未標出地面鐵路、酒吧、夜店或俱樂部。") if f["kind"] == "numbers"])
        self.assertEqual([], [f for f in RC.scan("掃描資料顯示 300 公尺內沒有地面鐵路。") if f["kind"] == "numbers"])
        self.assertEqual(["numbers"], kinds(RC.scan("押金最多 5 週房租。")), "a bare rule-of-thumb figure is still flagged")


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
