#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn a pasted resident-review page into numbers you can check, and the reviews you must read.

Axis 6's method is a reading method: take every review, drop the ones the site says were paid
for, drop the same-day drives, read the lowest ones in the original wording, and weigh the
people who moved out heaviest. Written as prose, cheap models skip it - the reading pilot found
BM25 search put the answer in its top five on only a quarter of the review questions, against a
clean sweep on contracts. So this is that method as a script: it splits the page into reviews,
reads each one's rating, date, resident status and incentive marker, counts the bursts, and
hands back the lowest N in full for a person to read.

It fetches nothing. Review sites forbid automated access, so the user pastes the pages.
Standard library only, Python 3.9.

Usage:
  reviews.py parse    pasted/*.txt [--plain]
  reviews.py stats    pasted/*.txt [--lowest 5] [--plain]
  reviews.py lowest   pasted/*.txt [--n 5] [--plain]
  reviews.py mentions pasted/*.txt --topic damp [--plain]
  reviews.py --selftest

Formats it reads: "This is rated 4.00 out of 5.00.", star glyphs, "4/5", "Rating, 5 stars",
"評分：4 分"; dates "Jul 2019", "14 July 2026", "2026-03-12", "2026年3月12日"; the header
"Viewing 1-5 out of 17"; incentive and move-out markers in English and Chinese. A rating is a
sorting key, never a finding: `lowest` and `mentions` print the reviews whole so they can be
quoted, and nothing here summarises a review.

Exit codes: 0 output, 1 no review could be parsed, 2 wrong arguments.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import re
import sys

MAX_HEADER_LINES = 6      # a header run is name, tag, building, date, marker, score - and no
                          # more, or the walk back starts eating the card above
BURST_SAME_DAY = 3        # this many reviews on one date is a review-drive day
BURST_SAME_MONTH = 5      # this many in one month at one rating is a drive too
SHORT_LINE = 80           # a loose rating ("4/5") only counts on a line this short
SENTENCE_END = ".!?。！？"  # a line ending here is prose, so it belongs to the review above

FILLED = "★⭐✭✩"
STAR_RUN = re.compile("[" + FILLED + "☆✧]{3,}")   # a run of filled and empty stars
NOT_REVIEW = re.compile(r"\b(?:development|building|property|block|scheme|overall|average|"
                        r"all[- ]time)\b[^.]{0,40}\brated\b", re.I)
RATED = re.compile(r"rat(?:ed|ing)\W{0,6}([0-5](?:\.\d+)?)\s*(?:out of|/)\s*5", re.I)
LOOSE = [re.compile("[評评]分\\W{0,4}([0-5](?:\\.\\d+)?)"),
         re.compile(r"rat(?:ed|ing)\W{0,6}([0-5](?:\.\d+)?)\s*(?:stars?|分)?\b", re.I),
         re.compile(r"(?<![\d.])([0-5](?:\.\d)?)\s*/\s*5(?![\d.])"),
         re.compile(r"\b([0-5](?:\.\d+)?)\s*stars?\b", re.I)]

VIEWING = re.compile(r"(?:viewing|showing|displaying)\s*(\d+)\s*[-–—]\s*(\d+)"
                     r"\s*(?:out of|of)\s*(\d+)", re.I)
TOTALS = [re.compile(r"(\d+)\s+total\s+reviews?", re.I),
          re.compile(r"\(\s*(\d+)\s+reviews?\s*\)", re.I),
          re.compile("共\\s*(\\d+)\\s*[則则筆笔條条]"),
          re.compile(r"\b(\d+)\s+reviews?\b", re.I)]
FOOTER = re.compile(r"^(?:page\s+\d+\s+of\s+\d+|©|about us|contact us|privacy policy|"
                    r"terms of (?:use|service)|cookie policy|follow us|"
                    r"these reviews are the subjective opinion)", re.I)
TAIL_MARK = re.compile(r"^(?:useful\s*\(|report$|share$|read more$|posted by|manager response|"
                       r"helpful\b|page\s+\d+\s+of\s+\d+)", re.I)
BOILER = frozenset(["facilities", "design", "location", "value", "management", "experience",
                    "read more", "share", "report", "unverified", "verified resident",
                    "posted by", "manager response", "filter", "latest", "usefulness",
                    "write a review", "how we verify reviews", "rating (high to low)"])

MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
DATES = [("ymd", re.compile(r"\b(20\d\d)[-/](\d{1,2})[-/](\d{1,2})\b")),
         ("dmy", re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + MONTH + r"\s+(20\d\d)\b", re.I)),
         ("mdy", re.compile(MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", re.I)),
         ("dmy", re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b")),
         ("ymd", re.compile("(20\\d\\d)\\s*年\\s*(\\d{1,2})\\s*月\\s*(\\d{1,2})\\s*日")),
         ("my", re.compile(MONTH + r"\s+(20\d\d)\b", re.I)),
         ("ym", re.compile("(20\\d\\d)\\s*年\\s*(\\d{1,2})\\s*月"))]

INCENTIVE = re.compile(r"in (?:exchange|return) for|vouchers?|gift cards?|prize draw|raffle|"
                       r"incentiv(?:e|es|ised|ized)|invit(?:ed|ation) to (?:leave a )?review|"
                       r"reviewed as part of a|sponsored|paid review|compensat(?:ed|ion)|"
                       "邀評|邀請評價|邀请评价|有償|有偿|禮券|礼券|抽獎|抽奖|換取|换取", re.I)
FORMER = re.compile(r"\bformer resident\b|\bex[- ]resident\b|\bmoved? out\b|\bmoving out\b|"
                    r"\bi left\b|\bgave notice\b|\bduring my tenancy\b|\bno longer live\b|"
                    r"搬走|搬離|搬离|前住戶|退租", re.I)   # "since I moved in" is not a move-out
CURRENT = re.compile(r"\bcurrent resident\b|\bcurrently liv\w+|\bi live here\b|\bstill live\b|"
                     r"現住戶|目前住|住在這", re.I)

TOPICS = {
    "damp": r"\bdamp\w*|\bcondensation\b|\bmoisture\b|\bwet walls?\b|潮濕|潮湿|濕氣|湿气|反潮",
    "mould": r"\bmould\w*|\bmold\w*|\bmildew\b|發霉|发霉|霉|黴",
    "noise": r"\bnoise\b|\bnoisy\b|\bloud\b|\bfootsteps?\b|\bsoundproof\w*|\bpart(?:y|ies)\b|"
             r"\bshouting\b|\bthin walls?\b|噪音|很吵|隔音|吵鬧|吵闹",
    "management": r"\bmanagement\b|\bmanaging agent\b|\bconcierge\b|\bletting agent\b|"
                  r"\blandlord\b|\bstaff\b|\bon-?site team\b|\bleasing office\b|"
                  r"管理|物業|物业|房東|房东|仲介|中介",
    "repairs": r"\brepairs?\b|\bmaintenance\b|\bfix(?:ed|ing)?\b|\bbroken\b|\bleaks?\b|"
               r"\bout of service\b|\bnot working\b|維修|维修|修理|漏水|故障",
    "short_let": r"\bairbnb\b|\bshort[- ]lets?\b|\bholiday lets?\b|\bshort stays?\b|"
                 r"\bserviced apartments?\b|\bsub-?let\w*|短租|民宿|日租",
    "security": r"\bsecurity\b|\bsafe(?:ty)?\b|\bunsafe\b|\bbreak-?ins?\b|\bburglar\w*|\btheft\b|"
                r"\bstolen\b|\bthie(?:f|ves)\b|\bintercom\b|\bcrime\b|治安|安全|門禁|门禁|小偷",
    "heat_network": r"\bheat network\b|\bdistrict heating\b|\bcommunal heating\b|"
                    r"\bheat interface\b|\bstanding charge\b|\bcommunal boiler\b|"
                    r"集中供暖|中央供暖|熱網|热网",
    "bills": r"\bbills?\b|\bbilling\b|\bservice charge\b|\bcouncil tax\b|\bstanding charge\b|"
             r"\brent (?:rise|increase)\b|\butilit\w+|帳單|账单|服務費|服务费|管理費|管理费",
}
TOPIC_RE = dict((name, re.compile(pattern, re.I)) for name, pattern in TOPICS.items())


# ------------------------------------------------------------------ reading one page ---
def rating_on_line(line):
    """The rating this line states, or None. A page-level average is not a review rating."""
    text = line.strip()
    if not text or NOT_REVIEW.search(text):
        return None
    run = STAR_RUN.search(text)
    if run:
        return float(sum(1 for char in run.group(0) if char in FILLED))
    found = RATED.search(text)
    if not found and len(text) <= SHORT_LINE:
        for pattern in LOOSE:
            found = pattern.search(text)
            if found:
                break
    return float(found.group(1)) if found else None


def date_in(lines):
    """The first date these lines state, ISO or a YYYY-MM partial, most precise form first."""
    for line in lines:
        for kind, pattern in DATES:
            found = pattern.search(line)
            if not found:
                continue
            groups = list(found.groups())
            if kind == "dmy":
                groups.reverse()                         # day, month, year -> year, month, day
            elif kind == "mdy":
                groups = [groups[2], groups[0], groups[1]]
            elif kind == "my":
                groups = [groups[1], groups[0], 0]
            elif kind == "ym":
                groups = groups + [0]
            try:
                year = int(groups[0])
                month = int(groups[1]) if str(groups[1]).isdigit() else MONTHS[groups[1].lower()]
                day = int(groups[2])
            except (KeyError, ValueError):
                continue
            if not 1 <= month <= 12 or day > 31:
                continue
            return "%04d-%02d-%02d" % (year, month, day) if day else "%04d-%02d" % (year, month)
    return None


def page_of(lines):
    """{shown, total} from a "Viewing 1-5 out of 17" header, or a bare total, or {}."""
    for line in lines:
        found = VIEWING.search(line)
        if found:
            first, last, total = (int(g) for g in found.groups())
            return {"shown": max(0, last - first + 1), "total": total}
    for pattern in TOTALS:
        for line in lines:
            found = pattern.search(line)
            if found:
                return {"shown": None, "total": int(found.group(1))}
    return {}


def block_start(lines, anchor, floor):
    """Walk back from a rating line over the header lines (name, tag, date, marker) above it.

    A rating line carrying its own date is already a whole header, so it starts its review where
    it stands. Otherwise the walk stops at the first finished sentence above, which is the
    previous review still talking."""
    if date_in([lines[anchor]]):
        return anchor
    start, seen, i = anchor, 0, anchor - 1
    while i >= floor and seen < MAX_HEADER_LINES:
        text = lines[i].strip()
        if not text:
            i -= 1
            continue
        if TAIL_MARK.search(text) or text[-1] in SENTENCE_END:
            break
        start, seen, i = i, seen + 1, i - 1
    return start


def split_reviews(lines):
    """[(start, end, anchor, rating)] one per review; 0-based line indexes, inclusive."""
    header = -1
    for i, line in enumerate(lines):
        if VIEWING.search(line):
            header = i
            break
    anchors = [(i, rating_on_line(lines[i])) for i in range(header + 1, len(lines))]
    anchors = [(i, rating) for i, rating in anchors if rating is not None]
    if not anchors:
        return []
    end = len(lines) - 1
    for i in range(anchors[-1][0], len(lines)):
        if FOOTER.match(lines[i].strip()):
            end = i - 1
            break
    starts, floor = [], header + 1
    for anchor, _rating in anchors:
        starts.append(block_start(lines, anchor, floor))
        floor = anchor + 1
    return [(starts[n], max(starts[n + 1] - 1 if n + 1 < len(anchors) else end, anchor), anchor,
             rating) for n, (anchor, rating) in enumerate(anchors)]


def body_text(lines):
    """The block kept whole, with runs of blank lines collapsed to one."""
    out = []
    for line in lines:
        if line.strip() or (out and out[-1]):
            out.append(line.rstrip())
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


def resident_words(lines):
    """The block minus the facet labels the site prints - only what the resident wrote."""
    return "\n".join(line for line in lines if line.strip().lower() not in BOILER
                     and not TAIL_MARK.search(line.strip()))


def parse_file(path, first_id=1):
    """(reviews, page, problems) for one pasted page."""
    with io.open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    page, reviews, problems = page_of(lines), [], []
    for n, (start, end, _anchor, rating) in enumerate(split_reviews(lines)):
        block = lines[start:end + 1]
        words = resident_words(block)
        marker = INCENTIVE.search(words)
        reviews.append({
            "id": first_id + n, "file": path, "rating": rating, "date": date_in(block),
            "resident_status": ("former" if FORMER.search(words) else
                                "current" if CURRENT.search(words) else "unknown"),
            "incentivised": marker is not None,
            "incentive_marker": marker.group(0).lower() if marker else None,
            "mentions": dict((topic, bool(pattern.search(words)))
                             for topic, pattern in TOPIC_RE.items()),
            "text": body_text(block), "line_start": start + 1, "line_end": end + 1})
    if not reviews:
        problems.append("%s: no review found - no rating line this script recognises" % path)
    undated = [str(r["id"]) for r in reviews if not r["date"]]
    if undated:
        problems.append("%s: %d review(s) with no date I could read (ids %s)"
                        % (path, len(undated), ", ".join(undated)))
    if page.get("shown") and page["shown"] != len(reviews):
        problems.append("%s: the page header says %d shown, I split out %d - check the split"
                        % (path, page["shown"], len(reviews)))
    if page.get("total") and page["total"] > len(reviews):
        problems.append("%s: the site says %d reviews exist, this page carries %d - %d unread"
                        % (path, page["total"], len(reviews), page["total"] - len(reviews)))
    return reviews, page, problems


def parse_paths(paths):
    reviews, pages, problems = [], {}, []
    for path in paths:
        try:
            found, page, trouble = parse_file(path, len(reviews) + 1)
        except (IOError, OSError) as exc:
            problems.append("%s: cannot read it (%s)" % (path, exc))
            continue
        reviews.extend(found)
        pages[path] = page
        problems.extend(trouble)
    return reviews, pages, problems


# ----------------------------------------------------------------------- the numbers ---
def date_key(review):
    """Sortable date. A month-only date pads to day 00; an undated review sorts last."""
    date = review.get("date") or ""
    return date + "-00" if len(date) == 7 else date


def unpad(key):
    return key[:7] if key.endswith("-00") else key


def lowest_first(reviews, count=None):
    """Lowest rating first; a tie goes to the most recent, which is the one still true."""
    ordered = sorted(reviews, key=date_key, reverse=True)
    ordered.sort(key=lambda r: (r["rating"] is None,
                                r["rating"] if r["rating"] is not None else 0.0))
    return ordered[:count] if count and count > 0 else ordered


def mean_of(reviews):
    rated = [r["rating"] for r in reviews if r["rating"] is not None]
    return round(sum(rated) / float(len(rated)), 2) if rated else None


def bursts(reviews):
    """Same-day drives, and same-month runs at one rating. Both are drives, not opinion."""
    by_day, by_month, same_day, same_month = {}, {}, [], []
    for review in reviews:
        date = review.get("date")
        if not date:
            continue
        if len(date) == 10:
            by_day.setdefault(date, []).append(review)
        by_month.setdefault(date[:7], []).append(review)
    for date in sorted(by_day):
        group = by_day[date]
        if len(group) >= BURST_SAME_DAY:
            same_day.append({"date": date, "count": len(group), "mean": mean_of(group),
                             "ids": [r["id"] for r in group]})
    for month in sorted(by_month):
        counts = {}
        for review in by_month[month]:
            if review["rating"] is not None:
                counts.setdefault(review["rating"], []).append(review["id"])
        for rating in sorted(counts):
            if len(counts[rating]) >= BURST_SAME_MONTH:
                same_month.append({"month": month, "rating": rating,
                                   "count": len(counts[rating]), "ids": counts[rating]})
    return same_day, same_month


def tally(keys):
    counts = {}
    for key in keys:
        counts[key] = counts.get(key, 0) + 1
    return counts


def brief(review):
    return dict((k, review[k]) for k in ("id", "rating", "date", "resident_status",
                                         "incentivised", "file", "line_start", "line_end"))


def stats_of(reviews, pages, lowest=5):
    rated = [r for r in reviews if r["rating"] is not None]
    organic = [r for r in reviews if not r["incentivised"]]
    same_day, same_month = bursts(reviews)
    burst_ids = set(i for group in same_day + same_month for i in group["ids"])
    clean = [r for r in organic if r["id"] not in burst_ids]
    former = [r for r in reviews if r["resident_status"] == "former"]
    dates = sorted(date_key(r) for r in reviews if r.get("date"))
    months, histogram = tally(r["date"][:7] for r in reviews if r.get("date")), \
        tally(str(int(round(r["rating"]))) for r in rated)
    shown = [p.get("shown") for p in pages.values() if p.get("shown")]
    total = [p.get("total") for p in pages.values() if p.get("total")]
    out = {
        "count": len(reviews), "rated": len(rated), "unrated": len(reviews) - len(rated),
        "page": {"shown": sum(shown) if shown else None, "total": sum(total) if total else None},
        "histogram": histogram, "by_month": months,
        "mean": mean_of(reviews), "organic_mean": mean_of(organic),
        "organic_mean_excl_bursts": mean_of(clean),
        "organic_sample": len(organic), "organic_sample_excl_bursts": len(clean),
        "share_incentivised": (round(1.0 - len(organic) / float(len(reviews)), 3)
                               if reviews else None),
        "share_former_resident": round(len(former) / float(len(reviews)), 3) if reviews else None,
        "same_day_bursts": same_day, "same_month_bursts": same_month,
        "date_span": {"earliest": unpad(dates[0]) if dates else None,
                      "latest": unpad(dates[-1]) if dates else None},
        "lowest": [brief(r) for r in lowest_first(reviews, lowest)],
        "move_out_reviews": [brief(r) for r in former],
        "mentions": dict((topic, len([r for r in reviews if r["mentions"][topic]]))
                         for topic in sorted(TOPICS)),
    }
    out["numbers"] = numbers_for(out)
    return out


def numbers_for(stats):
    """Every figure with what it means in one clause - the report copies these verbatim."""
    rows = [
        ("reviews parsed", stats["count"], "reviews",
         "how many reviews this script split out of the pages you pasted"),
        ("reviews the site claims", stats["page"].get("total"), "reviews",
         "the site's own total; anything above what you pasted is unread, not clean"),
        ("mean rating", stats["mean"], "stars",
         "the average of every rating on the page, paid-for reviews included"),
        ("organic mean", stats["organic_mean"], "stars",
         "the same average with the reviews the site marks as incentivised removed, over %d "
         "reviews" % stats["organic_sample"]),
        ("organic mean without drive days", stats["organic_mean_excl_bursts"], "stars",
         "and with review-drive days removed too, over %d reviews - the only score axis 6 lets "
         "into the verdict" % stats["organic_sample_excl_bursts"]),
        ("incentivised share", stats["share_incentivised"], "share of reviews",
         "how much of the sample was bought; a rising share with a rising score is a changing "
         "sample, not an improving building"),
        ("move-out share", stats["share_former_resident"], "share of reviews",
         "how many were written by people who left; one of those outweighs ten from residents "
         "still in the building"),
        ("review-drive days", len(stats["same_day_bursts"]), "days",
         "days carrying %d or more reviews - a drive, even when none is marked paid"
         % BURST_SAME_DAY)]
    return [{"label": label, "value": value, "unit": unit, "meaning": meaning}
            for label, value, unit, meaning in rows
            if value is not None or "the site claims" not in label]


# ------------------------------------------------------------------------- rendering ---
def one_line(review):
    return "#%-3s %-6s %-10s %-7s %-14s %s:%d-%d" % (
        review["id"], "%.2f" % review["rating"] if review["rating"] is not None else "-",
        review["date"] or "no date", review["resident_status"],
        "INCENTIVISED" if review["incentivised"] else "", review["file"],
        review["line_start"], review["line_end"])


def plain_reviews(reviews, whole=False):
    out = []
    for review in reviews:
        out.append(one_line(review))
        if whole:
            out += [review["text"], ""]
    return "\n".join(out)


def plain_stats(stats, problems):
    lines = ["%d reviews parsed%s" % (stats["count"], ", of the site's %d total"
             % stats["page"]["total"] if stats["page"].get("total") else "")]
    for number in stats["numbers"]:
        lines.append("  %-32s %-8s %s" % (number["label"],
                                          "-" if number["value"] is None else number["value"],
                                          number["meaning"]))
    lines.append("  ratings: " + ", ".join("%s star x%d" % (star, stats["histogram"][star])
                                           for star in sorted(stats["histogram"])))
    lines.append("  months:  " + ", ".join("%s x%d" % (month, stats["by_month"][month])
                                           for month in sorted(stats["by_month"])))
    for burst in stats["same_day_bursts"]:
        lines.append("  ! %d reviews on %s (mean %s) - a review-drive day"
                     % (burst["count"], burst["date"], burst["mean"]))
    for burst in stats["same_month_bursts"]:
        lines.append("  ! %d reviews all rated %.2f in %s - a drive, not a month"
                     % (burst["count"], burst["rating"], burst["month"]))
    lines.append("  mentions: " + ", ".join("%s %d" % (topic, hits)
                                            for topic, hits in sorted(stats["mentions"].items())))
    for name, rows in (("move-out reviews, they weigh most", stats["move_out_reviews"]),
                       ("lowest %d, read them whole with `lowest`" % len(stats["lowest"]),
                        stats["lowest"])):
        if rows:
            lines.append("  " + name + ":")
            lines += ["    " + one_line(row) for row in rows]
    return "\n".join(lines + ["  ? " + problem for problem in problems])


def emit(payload, plain_text, plain):
    sys.stdout.write((plain_text if plain else
                      json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)) + "\n")
    return 0


# ------------------------------------------------------------------------ the command ---
def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--selftest", action="store_true", help="run the built-in checks")
    subs = parser.add_subparsers(dest="cmd")
    for name, helptext in (("parse", "every review as a row"), ("stats", "the numbers"),
                           ("lowest", "the worst reviews, whole"),
                           ("mentions", "reviews raising one topic, whole")):
        sub = subs.add_parser(name, help=helptext)
        sub.add_argument("files", nargs="+")
        sub.add_argument("--plain", action="store_true", help="a table instead of JSON")
        if name == "stats":
            sub.add_argument("--lowest", type=int, default=5, help="how many worst to list")
        if name == "lowest":
            sub.add_argument("--n", type=int, default=5, help="how many to print")
        if name == "mentions":
            sub.add_argument("--topic", required=True, choices=sorted(TOPICS))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.cmd:
        sys.stderr.write("Give a subcommand: parse, stats, lowest or mentions. See --help.\n")
        return 2
    reviews, pages, problems = parse_paths(args.files)
    if not reviews:
        for problem in problems:
            sys.stderr.write(problem + "\n")
        sys.stderr.write("No review could be parsed. Paste the review page as text, or read it "
                         "by hand and say in the report that you did.\n")
        return 1
    for problem in problems:
        sys.stderr.write("note: " + problem + "\n")
    if args.cmd == "parse":
        return emit({"reviews": reviews, "pages": pages, "problems": problems,
                     "computed_by": "reviews.py"}, plain_reviews(reviews), args.plain)
    if args.cmd == "stats":
        stats = stats_of(reviews, pages, args.lowest)
        stats["problems"], stats["computed_by"] = problems, "reviews.py"
        return emit(stats, plain_stats(stats, problems), args.plain)
    if args.cmd == "lowest":
        picked = lowest_first(reviews, max(1, args.n))
    else:
        picked = [r for r in reviews if r["mentions"][args.topic]]
        if not picked:
            return emit({"topic": args.topic, "reviews": [], "count": 0,
                         "computed_by": "reviews.py"},
                        "No review mentions %s. A zero is a finding: record it, do not read it "
                        "as clean." % args.topic, args.plain)
    payload = {"reviews": picked, "count": len(picked), "computed_by": "reviews.py"}
    if args.cmd == "mentions":
        payload["topic"] = args.topic
    return emit(payload, plain_reviews(picked, whole=True), args.plain)


PAGE = "\n".join([
    "Viewing 1-4 out of 9", "", "★★☆☆☆  A. — 2 August 2026 — Former resident",
    "Damp came through the bedroom wall and there was black mould by February.", "",
    "★★★★★  B. — 4 February 2026 — Current resident",
    "Reviewed in exchange for a voucher. Lovely building.", "",
    "★★★☆☆  C. — 4 February 2026 — Current resident", "Fine. The lifts break monthly.", "",
    "★★☆☆☆  D. — 12 March 2026 — Former resident", "住了一年就搬走了。臥室潮濕，窗邊發霉。"])


def selftest():
    import os
    import tempfile
    handle, path = tempfile.mkstemp(suffix=".txt")
    with io.open(handle, "w", encoding="utf-8") as out:
        out.write(PAGE + "\n")
    try:
        reviews, pages, problems = parse_paths([path])
        stats, got = stats_of(reviews, pages), lambda key: [r[key] for r in reviews]
        checks = [
            ("four reviews", len(reviews) == 4),
            ("page header", pages[path] == {"shown": 4, "total": 9}),
            ("ratings", got("rating") == [2.0, 5.0, 3.0, 2.0]),
            ("dates", got("date") == ["2026-08-02", "2026-02-04", "2026-02-04", "2026-03-12"]),
            ("incentive", got("incentivised") == [False, True, False, False]),
            ("status", got("resident_status") == ["former", "current", "current", "former"]),
            ("chinese damp", reviews[3]["mentions"]["damp"] and reviews[3]["mentions"]["mould"]),
            ("english mould", reviews[0]["mentions"]["mould"]),
            ("unread flagged", any("unread" in problem for problem in problems)),
            ("mean", stats["mean"] == 3.0),
            ("organic mean", stats["organic_mean"] == 2.33),
            ("lowest order", [r["id"] for r in stats["lowest"]] == [1, 4, 3, 2]),
            ("every number explained", all(n["meaning"] for n in stats["numbers"]))]
    finally:
        os.unlink(path)
    bad = [name for name, ok in checks if not ok]
    sys.stdout.write("selftest: %d checks, %s\n"
                     % (len(checks), "all pass" if not bad else "FAILED: " + ", ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
