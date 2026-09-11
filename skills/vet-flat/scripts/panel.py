#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the requirements page: a read-only view of profile.yaml, plus the assistant's summary.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

The person talks to the assistant; the assistant edits profile.yaml; whenever the person wants
to see where things stand they open this page. The page does nothing: no form, no script, no
network, nothing stored. Blank in the profile shows as "not yet known". Only the keys below go
into the page, so a story summary or a seed never ends up in an HTML file.

Usage:
    panel.py --profile profile.yaml --out requirements.html
    panel.py --profile profile.yaml --out requirements.html --revision 3 \\
             --summary "Two areas within 35 minutes of Paddington; the budget fits a one-bed in both." \\
             --next "Send me the page of any listing you like" --next "Tell me your arrival date"

Re-run it after every change to the profile; the file is the current state, not a history.
Exit codes: 0 ok, 1 profile unreadable, 2 wrong arguments. Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import datetime
import io
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from profile_check import load as load_profile  # noqa: E402

SOURCE_URL = "https://github.com/jacky18008/pea-princess"
UNKNOWN = "還不知道 · not yet known"
TYPE_LABEL = {"any": "還沒決定 · not decided", "room_in_shared_flat": "合租一個房間 · a room in a shared flat",
              "studio": "套房 · studio", "one_bed": "一房 · one-bed", "two_bed": "兩房 · two-bed",
              "three_bed_plus": "三房以上 · three-bed or more"}
PRECISION_LABEL = {"unknown": "還不確定 · not sure", "district": "區域 · area", "station": "車站 · station",
                   "address": "地址 · address"}
PRIORITY_LABEL = {"quiet": "安靜 · quiet", "commute": "通勤 · commute", "price": "價格 · price",
                  "light": "採光 · light", "space": "空間 · space"}
AVOID_LABEL = {"main road or railway facade": "不臨大馬路或鐵路 · not on a main road or railway",
               "active works during tenancy": "租期內隔壁不施工 · no building works next door",
               "heat network without a written tariff": "帳單要白紙黑字 · no unwritten heat-network tariff",
               "management with no resident route to replace it": "管理要有人能投訴 · management I can complain to",
               "short-let or student churn neighbours": "不要旅館式鄰居 · no short-let churn",
               "no cooling": "夏天不能是烤箱 · no summer oven",
               "shared ventilation odours": "通風不能傳味道 · no smells through the vents"}
MUST_LABEL = {"washing_machine_in_flat": "屋內要有洗衣機 · washing machine in the flat"}
DEPTH_LABEL = {"lite": "快速初查 · quick check", "standard": "通常檢查 · usual checks", "deep": "仔細看名單 · closer review"}

CSS = """
  :root { color-scheme: light dark;
    --bg: light-dark(#f6f5f0, #171d1b); --panel: light-dark(#fffefa, #202925); --ink: light-dark(#223a33, #e6eee9);
    --muted: light-dark(#586a62, #adbbb3); --line: light-dark(#d9e1d8, #425149); --accent: light-dark(#226349, #a4dabb);
    --on-accent: light-dark(#ffffff, #123725); --tint: light-dark(#e9f1e8, #2b3d32); }
  body { margin: 0; padding: 16px; background: var(--bg); color: var(--ink); font: 15px/1.6 system-ui, sans-serif; }
  main { max-width: 860px; margin: auto; }
  header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; padding-bottom: 14px; border-bottom: 1px solid var(--line); margin-bottom: 18px; }
  .brand { display: flex; gap: 10px; align-items: center; font-weight: 500; }
  .monogram { display: grid; place-items: center; width: 32px; height: 32px; background: var(--accent); color: var(--on-accent); border-radius: 50%; }
  .caption { color: var(--muted); font-size: 12px; }
  h1 { font-size: 24px; font-weight: 500; letter-spacing: -.02em; margin: 0 0 6px; }
  h2 { font-size: 17px; font-weight: 500; margin: 0 0 14px; }
  h3 { font-size: 14px; font-weight: 500; margin: 14px 0 6px; }
  p { margin: 0 0 8px; }
  section { padding: 22px; background: var(--panel); border: 1px solid var(--line); border-radius: 15px; margin-bottom: 16px; }
  .agent { border-top: 4px solid var(--accent); }
  .pill { font-size: 12px; color: var(--accent); background: var(--tint); border-radius: 6px; padding: 3px 8px; white-space: nowrap; }
  dl { margin: 0; }
  .row { display: grid; grid-template-columns: 170px minmax(0, 1fr); gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); }
  .row:last-child { border-bottom: 0; }
  dt { color: var(--muted); }
  dd { margin: 0; overflow-wrap: anywhere; }
  dd.unknown { color: var(--muted); font-style: italic; }
  ul { margin: 0; padding-left: 20px; }
  .unknowns ul { color: var(--muted); }
  footer { color: var(--muted); font-size: 12px; margin-top: 10px; }
  @media (max-width: 520px) { .row { grid-template-columns: minmax(0, 1fr); gap: 2px; } section { padding: 16px; } }
"""


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _text(value):
    return escape(str(value), quote=True)


def _row(label, value, unknown=False):
    cls = ' class="unknown"' if unknown else ""
    return '<div class="row"><dt>%s</dt><dd%s>%s</dd></div>' % (_text(label), cls, value)


def _money(n):
    try:
        return "£{:,.0f}".format(float(n))
    except (TypeError, ValueError):
        return _text(n)


def rows(profile):
    """(label, html, unknown) for every line the page shows."""
    out = []
    c = profile.get("commute") if isinstance(profile.get("commute"), dict) else {}
    dest = c.get("destination")
    prec = str(c.get("destination_precision") or "unknown")
    if dest:
        out.append(("目的地 · destination", "%s（%s）" % (_text(dest), _text(PRECISION_LABEL.get(prec, prec))), False))
    else:
        out.append(("目的地 · destination", UNKNOWN, True))
    bits = []
    if c.get("arrive_by"):
        bits.append("到達 %s · arrive by %s" % (_text(c["arrive_by"]), _text(c["arrive_by"])))
    if c.get("max_door_to_door_min"):
        bits.append("最長 %s 分鐘門到門 · at most %s min door to door" % (_text(c["max_door_to_door_min"]), _text(c["max_door_to_door_min"])))
    out.append(("通勤 · commute", "；".join(bits) if bits else UNKNOWN, not bits))
    b = profile.get("budget") if isinstance(profile.get("budget"), dict) else {}
    if b.get("all_in_pcm_ceiling"):
        out.append(("每月上限 · ceiling", _money(b["all_in_pcm_ceiling"]) + "／月，房租＋帳單 · rent + bills", False))
    elif b.get("rent_pcm_target"):
        out.append(("每月上限 · ceiling", _money(b["rent_pcm_target"]) + "／月，只含房租 · rent only; bills not yet counted", False))
    else:
        out.append(("每月上限 · ceiling", UNKNOWN, True))
    ft = str(profile.get("flat_type") or "any")
    home = _text(TYPE_LABEL.get(ft, ft))
    if profile.get("occupants"):
        home += "，%s 人 · %s living there" % (_text(profile["occupants"]), _text(profile["occupants"]))
    if profile.get("separate_bedroom_required") is True:
        home += "；臥室要有門和窗 · a real bedroom"
    out.append(("房型 · home", home, ft == "any"))
    w = profile.get("move_in_window") if isinstance(profile.get("move_in_window"), dict) else {}
    if w.get("earliest") or w.get("latest"):
        out.append(("入住 · move-in", "%s 到 %s" % (_text(w.get("earliest") or "?"), _text(w.get("latest") or "?")), False))
    else:
        out.append(("入住 · move-in", UNKNOWN, True))
    pri = profile.get("priorities") if isinstance(profile.get("priorities"), list) else []
    out.append(("最在意 · priorities", "、".join(_text(PRIORITY_LABEL.get(str(p), str(p))) for p in pri) if pri else "還沒說 · none given", not pri))
    avoid = []
    if _get(profile, "floors", "reject_ground_floor") is True:
        avoid.append("不考慮地面層 · no ground floor")
    if _get(profile, "light", "reject_no_sky") is True:
        avoid.append("要看得到天空 · must see sky")
    if profile.get("quiet_over_light") is True:
        avoid.append("安靜比採光重要 · quiet beats light")
    for a in (profile.get("avoid") if isinstance(profile.get("avoid"), list) else []):
        avoid.append(AVOID_LABEL.get(str(a), str(a)))
    for m in (profile.get("must_haves") if isinstance(profile.get("must_haves"), list) else []):
        avoid.append(MUST_LABEL.get(str(m), str(m)))
    out.append(("不要／一定要 · deal-breakers", "<br>".join(_text(x) for x in avoid) if avoid else "沒有 · none", not avoid))
    depth = str(profile.get("budget_mode") or "standard")
    out.append(("查多深 · depth", _text(DEPTH_LABEL.get(depth, depth)), False))
    if profile.get("language"):
        out.append(("回覆語言 · language", _text(profile["language"]), False))
    qs = profile.get("my_questions") if isinstance(profile.get("my_questions"), list) else []
    qtexts = [(q.get("question") if isinstance(q, dict) else q) for q in qs]
    qtexts = [str(q) for q in qtexts if q]
    if qtexts:
        out.append(("你自己的問題 · your questions", "<br>".join(_text(q) for q in qtexts), False))
    return out


def unknowns(profile):
    out = []
    c = profile.get("commute") if isinstance(profile.get("commute"), dict) else {}
    prec = str(c.get("destination_precision") or "unknown")
    if not c.get("destination") or prec == "unknown":
        out.append("目的地還不明確，通勤不能算。 Destination not exact yet; no commute check.")
    elif prec == "district":
        out.append("目的地只到區域，通勤只能估。 Area only; the commute is an estimate.")
    b = profile.get("budget") if isinstance(profile.get("budget"), dict) else {}
    if not (b.get("all_in_pcm_ceiling") or b.get("rent_pcm_target")):
        out.append("每月上限還沒定。 Monthly ceiling not set.")
    elif b.get("rent_pcm_target") and not b.get("all_in_pcm_ceiling"):
        out.append("帳單還沒算進去。 Bills not yet included.")
    w = profile.get("move_in_window") if isinstance(profile.get("move_in_window"), dict) else {}
    if not (w.get("earliest") or w.get("latest")):
        out.append("入住時間還沒定。 Move-in window not set.")
    if str(profile.get("flat_type") or "any") == "any":
        out.append("房型還沒決定。 Home type not decided.")
    return out


def page(profile, summary=(), next_steps=(), revision=None, now=None):
    now = now or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    parts = ['<!doctype html>', '<html lang="zh-TW">', '<head>', '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<meta name="referrer" content="no-referrer">',
             "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src data:\">",
             '<title>Pea Princess · 我的需求 / My requirements</title>', '<style>' + CSS + '</style>', '</head>', '<body>', '<main>',
             '<header><div class="brand"><span class="monogram" aria-hidden="true">P</span><span>Pea Princess <span class="caption">／ 我的需求 · My requirements</span></span></div>'
             '<span class="caption">%s%s</span></header>' % (("第 %d 版 · revision %d · " % (revision, revision)) if revision else "", _text(now)),
             '<h1>目前的需求 <span class="caption" style="font-size:14px">Where things stand</span></h1>',
             '<p class="caption">這一頁由助理從設定檔產生，只能看。要改任何一項，直接跟助理說；它會改設定檔、重新產生這一頁。'
             ' Written by the assistant from profile.yaml; read-only. To change anything, tell the assistant.</p>']
    if summary or next_steps:
        parts.append('<section class="agent"><h2>助理的摘要 · What the assistant will do</h2>')
        for s in summary:
            parts.append('<p>%s</p>' % _text(s))
        if next_steps:
            parts.append('<h3>下一步 · Next</h3><ul>' + "".join('<li>%s</li>' % _text(n) for n in next_steps) + '</ul>')
        parts.append('</section>')
    parts.append('<section><h2>我的需求 · My requirements</h2><dl>')
    for label, html, unknown in rows(profile):
        parts.append(_row(label, html, unknown))
    parts.append('</dl>')
    u = unknowns(profile)
    parts.append('<div class="unknowns"><h3>還不知道的 · Not yet known</h3><ul>'
                 + ("".join('<li>%s</li>' % _text(x) for x in u) if u else '<li>三個核心都有了。 The three essentials are in.</li>')
                 + '</ul></div></section>')
    parts.append('<footer>Generated with vet-flat — %s. 留空就是未知，助理不會猜。 Blank means unknown; the assistant does not guess.</footer>' % _text(SOURCE_URL))
    parts += ['</main>', '</body>', '</html>', '']
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, help="profile.yaml")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--summary", action="append", default=[], help="a sentence from the assistant; repeatable")
    ap.add_argument("--next", action="append", default=[], help="a next step from the assistant; repeatable")
    ap.add_argument("--revision", type=int, help="the profile revision this page shows")
    args = ap.parse_args()
    try:
        profile = load_profile(args.profile)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("panel: %s\n" % exc)
        return 1
    html = page(profile, args.summary, args.next, args.revision)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html)
        sys.stderr.write("panel: wrote %s (%d bytes)\n" % (args.out, len(html.encode("utf-8"))))
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
