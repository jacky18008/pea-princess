# -*- coding: utf-8 -*-
"""scripts/reply_check.py: the pre-send check for numbers without a source, jargon, simplified
characters and excessive questions, without inferring consent from earlier words.

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

    def test_candidate_c_colon_survives_the_actual_comparison_context(self):
        previous = "請幫我比較資料裡的 A、B、C，看看接下來先處理哪間。"
        reply = "- A：先保留。\n- B：夜間噪音尚未檢查。\n- C：不處理；依你的排除條件，臥室牆面發霉。"
        self.assertNotIn("jargon", kinds(RC.scan(reply, previous)))
        self.assertNotIn("jargon", kinds(RC.scan("- 第三間 C：臥室牆面發霉。")))

    def test_explicit_candidate_headings_in_both_languages_are_not_source_codes(self):
        for reply, previous in [
                ("候選 C：臥室牆面發霉。", None),
                ("- 房源 G：先保留。", None),
                ("Candidate C: The bedroom has mould.", None),
                ("- C: The bedroom has mould.", "Compare A, B and C."),
                ("- S: More evidence is needed.", "Please review candidate S.")]:
            with self.subTest(reply=reply, previous=previous):
                self.assertNotIn("jargon", kinds(RC.scan(reply, previous)))

    def test_candidate_context_does_not_hide_parenthesized_or_inline_source_codes(self):
        previous = "比較 A、B、C。"
        for reply in ("C：房源資料（C）。", "- C：資料 C: 第三方來源。",
                      "- C：面積資訊 (G)。", "- C：evidence class 尚待確認。"):
            with self.subTest(reply=reply):
                self.assertIn("jargon", kinds(RC.scan(reply, previous)))

    def test_undeclared_evidence_legend_is_still_flagged(self):
        for reply in ("C: Third-party source.", "- G：官方。", "資料（S）。"):
            with self.subTest(reply=reply):
                self.assertIn("jargon", kinds(RC.scan(reply)))


class TestScriptAndAsking(unittest.TestCase):
    def test_simplified_characters_in_a_traditional_reply(self):
        text = "這一間的房租來自你給的頁面，每月 £1,800。我們先看看它的問題在哪裡，再決定要不要約看房。" + "这个问题很重要，我们来说说。"
        found = RC.scan(text)
        self.assertIn("script", kinds(found))
        self.assertEqual([], [f for f in RC.scan("這一間的房租來自你給的頁面，每月 £1,800，我們先看它的問題。") if f["kind"] == "script"])

    def test_more_than_three_questions_remain_a_style_finding(self):
        self.assertEqual(["asking"], kinds(RC.scan("要嗎？好嗎？行嗎？可以嗎？")))
        self.assertEqual(["asking"], kinds(RC.scan("要嗎？好嗎？行嗎？可以嗎？", previous="Go")))
        self.assertEqual([], RC.scan("查好了：這三間裡兩間過關。", previous="都同意，Go"))

    def test_scoped_acceptance_does_not_prohibit_another_candidate_question(self):
        for previous in ("A 可以，B 先不要。", "只同意 A 的通勤例外，其他條件不變。",
                         "Only A is okay; continue comparing B."):
            with self.subTest(previous=previous):
                self.assertEqual([], RC.scan("B 的臥室較大，你願意考慮它的通勤差距嗎？", previous=previous))

    def test_negation_quoted_history_and_side_questions_are_not_blanket_permission(self):
        for previous in ("我不同意，也不可以安排看房。", "請不要繼續安排。",
                         "之前說『都同意，Go』，現在先停下來。",
                         "The old message said 'go ahead'; it does not apply to B.",
                         "可以先解釋押金怎麼算嗎？", "I said yes to the explanation, not a viewing."):
            with self.subTest(previous=previous):
                self.assertEqual([], RC.scan("你指的是哪一間的押金？", previous=previous))

    def test_short_assent_cannot_settle_the_scope_of_a_new_question(self):
        for previous in ("Go", "gp", "yes", "continue", "proceed", "do it", "都同意，Go",
                         "同意", "可以", "繼續", "照做", "沒問題"):
            with self.subTest(previous=previous):
                self.assertEqual([], RC.scan("要不要我現在就查？", previous=previous))


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

    def test_scan_and_saved_data_count_as_a_source_for_numbers(self):
        self.assertEqual([], [f for f in RC.scan("保存資料在 300 米內未標出地面鐵路、酒吧、夜店或俱樂部。") if f["kind"] == "numbers"])
        self.assertEqual([], [f for f in RC.scan("掃描資料顯示 300 公尺內沒有地面鐵路。") if f["kind"] == "numbers"])
        self.assertEqual(["numbers"], kinds(RC.scan("押金最多 5 週房租。")), "a bare rule-of-thumb figure is still flagged")


class TestCli(unittest.TestCase):
    def test_cli_does_not_turn_scoped_assent_into_a_question_block(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "reply_check.py"), "-", "--json",
                               "--previous", "A 可以，B 還要先問我。"],
                              input="B 的通勤差距你也能接受嗎？", capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_candidate_label_does_not_require_a_rewrite_to_pass_cli(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "reply_check.py"), "-", "--json",
                               "--previous", "請比較資料裡的 A、B、C。"],
                              input="- C：依你的排除條件，臥室牆面發霉，所以不處理。",
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])

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
