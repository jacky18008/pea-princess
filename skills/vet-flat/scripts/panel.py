#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the requirements page with the current profile.yaml inlined. No model, no network.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

The standard is profile.yaml, not the HTML: the assistant edits the YAML, this script produces
the page (viewer/requirements.html with the profile written into its data block), and the
person opens it in any browser from disk. The same page also takes a pasted profile, for
people without a shell. The assistant can put its own summary on the page too.

Usage:
    panel.py --profile profile.yaml > requirements.html
    panel.py --profile profile.yaml --out requirements.html --summary "Two areas within 30 minutes; budget fits a one-bed in both." --next "Send me the page of any listing you like" --next "Tell me your arrival date"
    panel.py --template ../viewer/requirements.html --profile profile.yaml

Exit codes: 0 ok, 1 profile or template unreadable, 2 wrong arguments.
Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from profile_check import load as load_profile  # noqa: E402

TEMPLATE_CANDIDATES = [
    os.path.join(HERE, "..", "..", "..", "viewer", "requirements.html"),   # the repository
    os.path.join(HERE, "..", "viewer", "requirements.html"),               # the distributed zip
]
PAGE_KEYS = ("flat_type", "occupants", "separate_bedroom_required", "budget_mode", "language", "priorities",
             "avoid", "must_haves", "my_questions", "quiet_over_light", "budget", "commute", "move_in_window",
             "floors", "light")


def find_template(explicit=None):
    for path in ([explicit] if explicit else []) + TEMPLATE_CANDIDATES:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    raise IOError("requirements.html template not found; pass --template")


def page_subset(profile):
    """Only the keys the page shows, so nothing private in a profile leaks into an HTML file."""
    out = {}
    for key in PAGE_KEYS:
        if key in profile and profile[key] not in (None, "", [], {}):
            out[key] = profile[key]
    light = out.get("light")
    if isinstance(light, dict):
        out["light"] = {k: v for k, v in light.items() if k == "reject_no_sky"}
    return out


def inline(template_html, profile, agent=None):
    data = json.dumps(page_subset(profile), ensure_ascii=False, default=str).replace("</", "<\\/")
    marker = '<script type="application/json" id="pea-profile">'
    if marker not in template_html:
        raise ValueError("template has no pea-profile block")
    start = template_html.index(marker) + len(marker)
    end = template_html.index("</script>", start)
    html = template_html[:start] + data + template_html[end:]
    if agent:
        marker2 = '<script type="application/json" id="pea-agent">'
        start2 = html.index(marker2) + len(marker2)
        end2 = html.index("</script>", start2)
        html = html[:start2] + json.dumps(agent, ensure_ascii=False, default=str).replace("</", "<\\/") + html[end2:]
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, help="profile.yaml")
    ap.add_argument("--template", help="viewer/requirements.html (found automatically in the repo or the zip)")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--summary", action="append", default=[], help="a sentence from the assistant; repeatable")
    ap.add_argument("--next", action="append", default=[], help="a next step from the assistant; repeatable")
    ap.add_argument("--revision", type=int, help="the profile revision this page shows")
    args = ap.parse_args()
    try:
        profile = load_profile(args.profile)
        template = io.open(find_template(args.template), encoding="utf-8").read()
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("panel: %s\n" % exc)
        return 1
    agent = {}
    if args.summary:
        agent["summary"] = args.summary
    if args.next:
        agent["next"] = args.next
    if args.revision:
        agent["revision"] = args.revision
    html = inline(template, profile, agent or None)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html)
        sys.stderr.write("panel: wrote %s (%d bytes)\n" % (args.out, len(html.encode("utf-8"))))
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
