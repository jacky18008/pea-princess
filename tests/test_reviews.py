# -*- coding: utf-8 -*-
"""Offline tests for scripts/reviews.py, the deterministic reader for pasted review pages.

No network - the script never fetches anything. The inputs are four invented pages in
tests/fixtures/reviews/ (star glyphs, "rated X out of 5.00" with a Viewing header, "Rating, N
stars" with resident tags, and a Traditional Chinese page), the 41-review page in
tests/fixtures/find/, and - when it is present - the three de-identified real shapes under
bench/private/docs/cases/R1..R3, which are checked against the counts their own gold states.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
FIXTURES = os.path.join(HERE, "fixtures", "reviews")
PRIVATE = os.path.join(ROOT, "bench", "private", "docs", "cases")

sys.path.insert(0, SCRIPTS)
import reviews  # noqa: E402

STARS = os.path.join(FIXTURES, "stars.txt")
RATED = os.path.join(FIXTURES, "rated-out-of.txt")
WORDS = os.path.join(FIXTURES, "stars-word.txt")
CHINESE = os.path.join(FIXTURES, "chinese.txt")
BIG = os.path.join(HERE, "fixtures", "find", "resident-reviews.txt")
NOT_REVIEWS = os.path.join(HERE, "fixtures", "find", "listing.txt")


def parse(path):
    return reviews.parse_file(path)[0]


def page(path):
    return reviews.parse_file(path)[1]


def stats(path, lowest=5):
    found, one_page, _problems = reviews.parse_file(path)
    return reviews.stats_of(found, {path: one_page}, lowest)


def run_cli(*args):
    proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "reviews.py")] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8"), err.decode("utf-8")


def gold_counts(case):
    """(reviews on the page, site total or None) as the case's own gold answer states them."""
    with io.open(os.path.join(PRIVATE, case, "gold.json"), encoding="utf-8") as handle:
        gold = json.load(handle)
    for question in gold["questions"]:
        text = question["question"].lower()
        if not text.startswith("how many") or "review" not in text:
            continue
        answer = question["answer"]
        if "value" in answer:
            return answer["value"], None
        shown = total = None
        for item in answer.get("list", []):
            shown, total = item.get("shown", shown), item.get("total", total)
        return shown, total
    return None, None


class Counts(unittest.TestCase):
    def test_a_star_page_splits_into_one_review_per_star_line(self):
        self.assertEqual(len(parse(STARS)), 10)

    def test_a_viewing_header_gives_shown_and_total(self):
        self.assertEqual(page(RATED), {"shown": 3, "total": 11})
        self.assertEqual(len(parse(RATED)), 3)

    def test_the_page_average_is_not_counted_as_a_review(self):
        """"This development is rated 4.29 out of 5.00" is the site's average, not a review."""
        text = "This development is rated 4.29 out of 5.00."
        self.assertIsNone(reviews.rating_on_line(text))
        self.assertEqual(reviews.rating_on_line("This is rated 4.00 out of 5.00."), 4.0)

    def test_a_page_with_no_header_says_so_rather_than_guessing(self):
        self.assertEqual(page(WORDS), {})

    def test_a_chinese_page_counts_its_own_total(self):
        self.assertEqual(len(parse(CHINESE)), 5)
        self.assertEqual(page(CHINESE)["total"], 5)

    def test_the_forty_one_review_page_parses_whole(self):
        self.assertEqual(len(parse(BIG)), 41)


class Ratings(unittest.TestCase):
    def test_star_glyphs_count_the_filled_stars(self):
        self.assertEqual([r["rating"] for r in parse(STARS)],
                         [1.0, 1.0, 2.0, 3.0, 5.0, 5.0, 5.0, 5.0, 4.0, 2.0])

    def test_rated_out_of_five_parses(self):
        self.assertEqual([r["rating"] for r in parse(RATED)], [3.0, 5.0, 4.0])

    def test_the_word_form_parses(self):
        self.assertEqual([r["rating"] for r in parse(WORDS)], [2.0, 5.0, 4.0, 3.0])
        self.assertEqual(reviews.rating_on_line("Rating, 5 stars"), 5.0)
        self.assertEqual(reviews.rating_on_line("4/5"), 4.0)

    def test_a_chinese_rating_parses(self):
        self.assertEqual([r["rating"] for r in parse(CHINESE)], [2.0, 5.0, 5.0, 5.0, 3.0])


class Dates(unittest.TestCase):
    def test_month_and_year_only_stays_a_partial_date(self):
        self.assertEqual([r["date"] for r in parse(RATED)], ["2019-07", "2024-02", "2024-03"])

    def test_a_full_written_date_becomes_iso(self):
        self.assertEqual([r["date"] for r in parse(STARS)][:3],
                         ["2026-08-02", "2026-07-14", "2026-06-20"])

    def test_iso_and_written_dates_mix_on_one_page(self):
        self.assertEqual([r["date"] for r in parse(WORDS)],
                         ["2026-03-12", "2026-07-14", "2026-06-01", "2026-05-03"])

    def test_a_chinese_date_becomes_iso(self):
        self.assertEqual([r["date"] for r in parse(CHINESE)][:2], ["2026-03-12", "2026-02-04"])


class Incentives(unittest.TestCase):
    def test_in_exchange_for_a_voucher_is_an_incentive(self):
        marked = [r for r in parse(STARS) if r["incentivised"]]
        self.assertEqual([r["incentive_marker"] for r in marked],
                         ["in exchange for", "in return for"])

    def test_the_site_s_own_incentive_line_is_read(self):
        self.assertEqual([r["incentivised"] for r in parse(RATED)], [True, False, True])

    def test_a_chinese_invited_review_is_an_incentive(self):
        marked = [r["incentive_marker"] for r in parse(CHINESE) if r["incentivised"]]
        self.assertEqual(marked, ["邀評", "換取"])

    def test_a_voucher_in_the_page_footer_is_not_a_review_s_incentive(self):
        """The footer's "How to access my voucher" sits below the last review, not inside it."""
        self.assertFalse(parse(RATED)[1]["incentivised"])


class Residents(unittest.TestCase):
    def test_former_and_current_tags_are_read(self):
        self.assertEqual([r["resident_status"] for r in parse(STARS)][:4],
                         ["former", "former", "current", "current"])

    def test_moved_in_is_not_a_move_out(self):
        """"the carpet has not been cleaned since I moved in" is a current resident."""
        self.assertEqual(parse(WORDS)[3]["resident_status"], "current")

    def test_a_chinese_move_out_is_read(self):
        self.assertEqual(parse(CHINESE)[0]["resident_status"], "former")

    def test_move_out_reviews_are_listed_for_reading(self):
        listed = stats(STARS)["move_out_reviews"]
        self.assertEqual([r["id"] for r in listed], [1, 2, 9, 10])
        self.assertEqual(listed[0]["line_start"], 5)


class Numbers(unittest.TestCase):
    def test_the_lowest_five_are_lowest_first_with_the_recent_tie_first(self):
        """Both 1.00s, then both 2.00s - and inside each tie the more recent one first."""
        lowest = stats(STARS)["lowest"]
        self.assertEqual([(r["rating"], r["date"]) for r in lowest],
                         [(1.0, "2026-08-02"), (1.0, "2026-07-14"), (2.0, "2026-06-20"),
                          (2.0, "2025-11-11"), (3.0, "2026-05-05")])

    def test_the_organic_mean_drops_the_incentivised_reviews(self):
        numbers = stats(STARS)
        self.assertEqual(numbers["mean"], 3.3)
        self.assertEqual(numbers["organic_mean"], 2.88)
        self.assertEqual(numbers["organic_sample"], 8)
        self.assertEqual(numbers["share_incentivised"], 0.2)

    def test_three_reviews_on_one_day_are_a_review_drive(self):
        burst = stats(STARS)["same_day_bursts"]
        self.assertEqual(len(burst), 1)
        self.assertEqual((burst[0]["date"], burst[0]["count"], burst[0]["mean"]),
                         ("2026-02-04", 3, 5.0))

    def test_a_same_month_run_at_one_rating_is_a_drive_too(self):
        big = stats(BIG)
        self.assertEqual([(b["month"], b["rating"], b["count"]) for b in big["same_month_bursts"]],
                         [("2026-02", 5.0, 6)])
        self.assertEqual(big["same_day_bursts"][0]["count"], 6)

    def test_the_verdict_score_drops_the_drive_days_as_well(self):
        self.assertEqual(stats(STARS)["organic_mean_excl_bursts"], 2.17)

    def test_every_number_says_what_it_means(self):
        for number in stats(STARS)["numbers"]:
            self.assertTrue(number["meaning"] and number["label"] and number["unit"],
                            "a number with no plain-language meaning: %r" % number)

    def test_the_date_span_keeps_a_partial_date_partial(self):
        self.assertEqual(stats(RATED)["date_span"], {"earliest": "2019-07", "latest": "2024-03"})


class Mentions(unittest.TestCase):
    def test_damp_and_mould_in_english(self):
        found = parse(STARS)
        self.assertTrue(found[0]["mentions"]["mould"])
        self.assertTrue(found[1]["mentions"]["damp"])
        self.assertFalse(found[3]["mentions"]["damp"])

    def test_damp_and_mould_in_chinese(self):
        first = parse(CHINESE)[0]
        self.assertTrue(first["mentions"]["damp"] and first["mentions"]["mould"])

    def test_a_chinese_review_raises_noise_and_the_heat_network(self):
        last = parse(CHINESE)[4]["mentions"]
        self.assertTrue(last["noise"] and last["heat_network"] and last["bills"])

    def test_the_site_s_own_facet_labels_are_not_the_resident_speaking(self):
        """Every card on this shape prints a "Management" label; that is not a complaint."""
        self.assertFalse(parse(RATED)[2]["mentions"]["management"])

    def test_a_topic_nobody_raised_counts_zero(self):
        self.assertEqual(stats(RATED)["mentions"]["damp"], 0)


class CommandLine(unittest.TestCase):
    def test_lowest_prints_the_reviews_whole_with_their_line_spans(self):
        code, out, _err = run_cli("lowest", "--plain", "--n", "2", STARS)
        self.assertEqual(code, 0)
        self.assertIn("Black mould came back on the bathroom ceiling", out)
        self.assertIn("stars.txt:5-8", out)
        self.assertIn("stars.txt:9-12", out)

    def test_mentions_prints_the_matching_reviews_whole(self):
        code, out, _err = run_cli("mentions", "--plain", "--topic", "damp", CHINESE)
        self.assertEqual(code, 0)
        self.assertIn("臥室牆角一到冬天就潮濕", out)

    def test_json_is_the_default_and_carries_the_spans(self):
        code, out, _err = run_cli("parse", STARS)
        self.assertEqual(code, 0)
        first = json.loads(out)["reviews"][0]
        self.assertEqual((first["line_start"], first["line_end"]), (5, 8))
        self.assertEqual(sorted(first["mentions"]), sorted(reviews.TOPICS))

    def test_a_page_with_no_review_exits_one_and_says_why(self):
        code, _out, err = run_cli("stats", NOT_REVIEWS)
        self.assertEqual(code, 1)
        self.assertIn("No review could be parsed", err)

    def test_unread_reviews_are_reported_not_hidden(self):
        code, _out, err = run_cli("stats", "--plain", RATED)
        self.assertEqual(code, 0)
        self.assertIn("8 unread", err)

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(run_cli()[0], 2)

    def test_selftest_passes(self):
        code, out, _err = run_cli("--selftest")
        self.assertEqual(code, 0, out)
        self.assertIn("all pass", out)


class PrivateShapes(unittest.TestCase):
    """The three de-identified real pages, if this checkout has them."""

    def setUp(self):
        if not os.path.isdir(PRIVATE):
            self.skipTest("bench/private is not in this checkout")

    def test_each_private_case_parses_to_the_count_its_gold_states(self):
        for case in ("R1", "R2", "R3"):
            doc = os.path.join(PRIVATE, case, "doc.txt")
            if not os.path.isfile(doc):
                continue
            shown, total = gold_counts(case)
            found, one_page, _problems = reviews.parse_file(doc)
            self.assertEqual(len(found), shown, "%s: gold says %s reviews" % (case, shown))
            if total:
                self.assertEqual(one_page["total"], total,
                                 "%s: gold says %s in total" % (case, total))

    def test_the_private_pages_agree_on_which_reviews_were_bought(self):
        """R1 and R3 are wholly incentivised; R2 has exactly one organic review."""
        wanted = {"R1": 0, "R2": 1, "R3": 0}
        for case, organic in wanted.items():
            doc = os.path.join(PRIVATE, case, "doc.txt")
            if not os.path.isfile(doc):
                continue
            found = reviews.parse_file(doc)[0]
            self.assertEqual(len([r for r in found if not r["incentivised"]]), organic, case)


if __name__ == "__main__":
    unittest.main()
