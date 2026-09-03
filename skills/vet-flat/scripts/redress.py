#!/usr/bin/env python3
"""Compliance registers: client money protection, heat networks, rogue landlords.

Four sources, three of them fetchable, two deliberately manual.

1. Client Money Protect (`cmp`) - https://www.clientmoneyprotect.co.uk/agent-search/
   The visible page is a shell, but the search itself is server-side: the form
   posts `action=member_search_third_party&keyword=<text>&auto=0` to WordPress
   admin-ajax and gets JSON back. clientmoneyprotect.co.uk/robots.txt disallows
   /wp-admin/ but explicitly ALLOWS /wp-admin/admin-ajax.php, which is the path
   used here. The API also returns each member's email and phone; this script
   drops both - they are personal contact data with no vetting value.
   A letting agent that holds rent or deposits must be in a client money
   protection scheme by law. CMP is one of six approved schemes, so "not found"
   here is not proof of non-compliance: check Propertymark, Money Shield, RICS,
   Safeagent and UKALA before concluding anything.

2. Heat Trust (`heat-trust`) - https://heattrust.org/our-members
   Plain server-rendered HTML listing every Registered Participant (heat
   supplier) and every Registered Site (heat network), with a headline count and
   an "as at" date. Joomla defaults in robots.txt only; this page is allowed.
   Registration is voluntary, so an unregistered network is not a fault - it
   just means no scheme-level complaint route and no price-transparency pledge.

3. GLA Rogue Landlord and Agent Checker (`rogue`) - www.london.gov.uk
   A server-rendered Drupal exposed form: `?name=` and `?address=` filter the
   result cards without any JavaScript. It lists only enforcement actions that
   London boroughs chose to publish, so a miss proves nothing.

4. Property Redress Scheme (`prs`) and The Property Ombudsman (`tpo`)
   Both return `access: manual`, no fetch. PRS's public feed
   (portal.propertyredress.co.uk/propertyagent/GetMemberByAPI) ignores every
   filter parameter and returns the same ten recent members whatever you ask,
   so it cannot answer "is this agent a member". tpos.co.uk/robots.txt carries
   an explicit `User-agent: ClaudeBot / Disallow: /`, so this tool does not
   fetch it at all.

Usage:
  redress.py cmp --agent "Foxtons"
  redress.py heat-trust --site "Greenwich Peninsula"
  redress.py heat-trust --supplier "Loka"
  redress.py rogue --name "Smith" [--address "Ilford"]
  redress.py prs
  redress.py tpo
All commands print one JSON object with source_url, http_status, ok, note,
retrieved_at and evidence_class.
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402

CMP_PAGE = "https://www.clientmoneyprotect.co.uk/agent-search/"
CMP_AJAX = "https://www.clientmoneyprotect.co.uk/wp-admin/admin-ajax.php"
HEAT_TRUST = "https://heattrust.org/our-members"
GLA_ROGUE = ("https://www.london.gov.uk/programmes-strategies/housing-and-land/renting-home/"
             "private-renting/check-landlord-or-agent/rogue-landlord-and-agent-checker")
PRS_URL = "https://www.propertyredress.co.uk/agent-finder"
TPO_URL = "https://www.tpos.co.uk/find-a-member"

OTHER_CMP_SCHEMES = [
    "Propertymark (ARLA) - https://www.propertymark.co.uk",
    "Money Shield - https://www.money-shield.co.uk",
    "RICS - https://www.rics.org",
    "Safeagent - https://www.safeagents.co.uk",
    "UKALA - https://www.ukala.org.uk",
]


def _clean(s):
    if s is None:
        return None
    t = htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)))
    t = t.replace(" ", " ").strip()
    return t or None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _note(res):
    """_fetch keeps the note from a cached failure even when this run's assertion
    passed. Do not report a stale failure as a live one."""
    n = res.get("note") or ""
    return "" if res["ok"] and "assertion failed" in n else n


# ------------------------------------------------------ client money protect --
def parse_cmp(payload):
    """payload: the admin-ajax JSON string. Returns (status, matches)."""
    try:
        j = json.loads(payload)
    except ValueError:
        return None, []
    status = j.get("status")
    rows = []
    for r in (j.get("results") or []):
        branches = []
        for b in (r.get("branch") or []):
            branches.append({"name": _clean(b.get("bcname")), "address": _clean(b.get("baddress"))})
        rows.append({
            "name": _clean(r.get("cname")),
            "membership_number": _clean(r.get("number")),
            "address": _clean(r.get("address")) if r.get("fdDisplayAddress") else None,
            "membership_status": _clean(r.get("status")),
            "valid_until": None,
            "branches": branches,
        })
    return status, rows


def cmp_search(agent, verbose=False):
    data = "action=member_search_third_party&keyword=%s&auto=0" % _form(agent)
    res = fetch(CMP_AJAX, method="POST", data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                         "Accept": "application/json"},
                expect=lambda b: b.lstrip().startswith("{") and '"status"' in b,
                cache_ttl=6 * 3600, verbose=verbose)
    out = {"query": {"agent": agent},
           "source_url": CMP_PAGE,
           "endpoint_used": CMP_AJAX + " (POST action=member_search_third_party&keyword=&auto=0)",
           "http_status": res["status"], "ok": res["ok"], "note": _note(res),
           "retrieved_at": res["retrieved_at"], "evidence_class": "G",
           "access": "automated"}
    if not res["ok"]:
        out["access"] = "manual"
        out["manual_instructions"] = ("open %s, type the agent's name or postcode into the search "
                                      "box and paste the result" % CMP_PAGE)
        return out
    status, rows = parse_cmp(res["body"])
    out["api_status"] = status
    out["count"] = len(rows)
    out["matches"] = rows
    out["valid_until_note"] = ("the search API returns a membership status (Active / expired) but "
                               "no expiry date, so valid_until is always null here; ask the agent "
                               "for their certificate to see the dates")
    out["privacy_note"] = ("the API also returns each member's email and phone; this tool does not "
                           "record them")
    if not rows:
        out["evidence_class"] = "U"
        out["not_found"] = {"query": agent, "endpoint": CMP_AJAX}
        out["interpretation"] = ("no Client Money Protect member matched %r. CMP is one of six "
                                 "government-approved schemes, so this is not proof the agent is "
                                 "uninsured - check the others." % agent)
        out["other_schemes"] = OTHER_CMP_SCHEMES
    return out


def _form(s):
    return re.sub(r"[^A-Za-z0-9._~-]", lambda m: "%%%02X" % ord(m.group(0)), (s or "").strip())


# ------------------------------------------------------------------ heat trust --
UNDERLINE = r'<span style="text-decoration: underline;">'


def _sites_from_block(block, region):
    """Sites live either as <li> items (London) or as <br>-separated text after an
    underlined 'Area:' label (everywhere else). One pass handles both."""
    sites = []
    spans = list(re.finditer(UNDERLINE + r"(.*?)</span>", block, re.S))
    area = None
    for i, m in enumerate(spans):
        label = (_clean(m.group(1)) or "").rstrip(":").strip()
        if label:  # an empty underlined span is a stray <br>, not a new area
            area = label
        end = spans[i + 1].start() if i + 1 < len(spans) else len(block)
        tail = block[m.end():end]
        names = []
        if "<li" in tail:
            names = [_clean(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", tail, re.S)]
        else:
            for piece in re.split(r"<br\s*/?>", tail):
                t = _clean(piece)
                if t:
                    names.append(t)
        for n in names:
            if n:
                sites.append({"name": n, "area": area or None, "region": region})
    return sites


def parse_heat_trust(body):
    d = {}
    cut = body.find("<!-- End Content -->")   # the footer also has <p>/<span> text
    if cut > 0:
        body = body[:cut]
    m = re.search(r"Heat Trust in numbers\s*\(at ([^)<]+)\)", _clean(body) or "")
    d["as_at"] = m.group(1).strip() if m else None
    for key, label in (("total_members", r"Registered Participants \(heat suppliers\)"),
                       ("total_sites", r"Registered Sites \(heat networks\)"),
                       ("consumers_protected", r"Consumers protected")):
        mm = re.search(label + r":\s*</td>?\s*<strong>\s*([\d,]+)", body)
        if not mm:
            mm = re.search(label + r":\s*<strong>\s*([\d,]+)", body)
        d[key] = int(mm.group(1).replace(",", "")) if mm else None

    heads = [(m.start(), _clean(m.group(1)) or "")
             for m in re.finditer(r"<h4[^>]*>(.*?)</h4>", body, re.S)]
    bounds = []
    for i, (pos, txt) in enumerate(heads):
        nxt = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        bounds.append((txt, pos, nxt))

    participants, sites = [], []
    for txt, start, end in bounds:
        low = txt.lower()
        if low.startswith("registered participants"):
            block = body[start:end]
            participants += [x for x in
                             (_clean(y) for y in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S))
                             if x]
        elif low.startswith("registered sites"):
            region = txt
            # a "Registered Sites in ..." heading is followed by accordion sub-headings
            # that are also <h4>; absorb everything up to the next top-level sites heading
            j = [k for k, (t, s, e) in enumerate(bounds) if s == start][0]
            end2 = end
            for t2, s2, e2 in bounds[j + 1:]:
                if t2.lower().startswith("registered "):
                    break
                end2 = e2
            sites += _sites_from_block(body[start:end2], region)

    # de-duplicate, keep order
    seen = set()
    uniq = []
    for s in sites:
        k = (s["name"], s["area"], s["region"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    d["participants"] = participants
    d["sites"] = uniq
    d["participants_listed"] = len(participants)
    d["sites_listed"] = len(uniq)
    return d


def heat_trust(site=None, supplier=None, verbose=False):
    res = fetch(HEAT_TRUST, expect=lambda b: "Registered Participants" in b and "Registered Sites" in b,
                cache_ttl=7 * 86400, verbose=verbose)
    out = {"query": {"site": site, "supplier": supplier},
           "source_url": HEAT_TRUST, "http_status": res["status"], "ok": res["ok"],
           "note": _note(res), "retrieved_at": res["retrieved_at"], "evidence_class": "C"}
    if not res["ok"]:
        return out
    d = parse_heat_trust(res["body"])
    out["as_at"] = d["as_at"]
    out["total_members"] = d["total_members"]
    out["total_sites"] = d["total_sites"]
    out["consumers_protected"] = d["consumers_protected"]
    out["participants_listed"] = d["participants_listed"]
    out["sites_listed"] = d["sites_listed"]
    matches = {}
    if site:
        n = _norm(site)
        matches["sites"] = [s for s in d["sites"] if n and n in _norm(s["name"])]
    if supplier:
        n = _norm(supplier)
        matches["suppliers"] = [p for p in d["participants"] if n and n in _norm(p)]
    if not site and not supplier:
        matches = {"sites": d["sites"], "suppliers": d["participants"]}
    out["matches"] = matches
    hits = sum(len(v) for v in matches.values())
    out["match_count"] = hits
    if hits == 0:
        out["evidence_class"] = "U"
        out["not_found"] = {"site": site, "supplier": supplier, "endpoint": HEAT_TRUST}
        out["interpretation"] = (
            "no Heat Trust entry matched. Registration is voluntary and a supplier may register "
            "some of its networks and not others, so this says nothing about whether the building "
            "has a heat network - only that this one has no Heat Trust protections.")
    out["caveat"] = ("A logo on the Heat Trust page does not mean every network that supplier runs "
                     "is registered; the site list is the part that matters.")
    return out


# ---------------------------------------------------------------------- rogue --
ROGUE_FIELDS = {
    "enforcement action type": "enforcement_action_type",
    "enforcement authority": "enforcement_authority",
    "rental property address": "address",
    "offence": "offence",
    "offence description": "offence_description",
    "fine": "fine",
    "enforcement date": "enforcement_date",
    "record expires": "record_expires",
}


def parse_rogue(body):
    cards = []
    chunks = body.split('<div data-card=')[1:]
    for chunk in chunks:
        m = re.search(r'<h3[^>]*>(.*?)</h3>', chunk, re.S)
        entry = {"name": _clean(m.group(1)) if m else None}
        for label, value in re.findall(r"<strong>(.*?):\s*</strong>\s*</span>(.*?)</li>", chunk, re.S):
            key = ROGUE_FIELDS.get((_clean(label) or "").lower().rstrip(":").strip())
            if key:
                entry[key] = _clean(value)
        for k in ROGUE_FIELDS.values():
            entry.setdefault(k, None)
        cards.append(entry)
    return cards


def rogue(name=None, address=None, verbose=False):
    parts = []
    if name:
        parts.append("name=" + _form(name))
    if address:
        parts.append("address=" + _form(address))
    url = GLA_ROGUE + (("?" + "&".join(parts)) if parts else "")
    res = fetch(url, expect=lambda b: "<div data-card=" in b or "no results were found" in b,
                verbose=verbose)
    query_desc = ", ".join(filter(None, [("name=%r" % name) if name else None,
                                         ("address=%r" % address) if address else None])) or "no filter"
    out = {"query": {"name": name, "address": address},
           "source_url": url, "http_status": res["status"], "ok": res["ok"],
           "note": _note(res), "retrieved_at": res["retrieved_at"]}
    if not res["ok"]:
        out["evidence_class"] = "U"
        return out
    cards = parse_rogue(res["body"])
    out["count"] = len(cards)
    out["results"] = cards
    out["no_results_banner"] = bool(re.search(r"Sorry, no results were found", res["body"]))
    pages = sorted({int(x) for x in re.findall(r"\?page=(\d+)", res["body"])})
    out["more_pages"] = pages[-1] + 1 if pages else 1
    out["evidence_class"] = "G" if cards else "U"
    if not cards:
        out["not_found"] = {"query": query_desc, "endpoint": url}
        out["interpretation"] = (
            "no entry found for query %s in the checker (which lists only enforcement actions "
            "boroughs chose to publish)" % query_desc)
    out["caveat"] = ("The checker holds only what London boroughs sent the GLA and only for as "
                     "long as each record runs. Absence is not a clean record; presence names a "
                     "specific enforcement action against a specific person or company.")
    return out


# ------------------------------------------------------------- manual sources --
def prs():
    return {
        "source": "Property Redress Scheme - agent finder",
        "source_url": PRS_URL,
        "access": "manual",
        "ok": True,
        "http_status": None,
        "note": ("No fetch. The scheme's public feed "
                 "(portal.propertyredress.co.uk/propertyagent/GetMemberByAPI) returns the same ten "
                 "recent members for every value of name=, search=, searchTerm= and companyName=, "
                 "so it cannot answer a membership question. It also emits members' personal "
                 "contact details."),
        "retrieved_at": now_iso(),
        "evidence_class": "U",
        "manual_instructions": [
            "Open %s and search the agent's trading name." % PRS_URL,
            "Ask the agent, in writing: which redress scheme are you a member of, what is your "
            "membership number, and on what date does it expire?",
            "Every letting agent and property manager in England must belong to a government-"
            "approved redress scheme; there are two (Property Redress Scheme and The Property "
            "Ombudsman). Ask which one and check that one.",
            "Paste the membership name, number and expiry date back into the report.",
        ],
    }


def tpo():
    return {
        "source": "The Property Ombudsman - find a member",
        "source_url": TPO_URL,
        "access": "manual",
        "ok": True,
        "http_status": None,
        "note": ("No fetch. https://www.tpos.co.uk/robots.txt contains an explicit "
                 "'User-agent: ClaudeBot / Disallow: /', and the member-search URL redirects to "
                 "/consumers/make-a-complaint anyway."),
        "retrieved_at": now_iso(),
        "evidence_class": "U",
        "manual_instructions": [
            "Open %s in a browser and search the agent's trading name." % TPO_URL,
            "Ask the agent for their TPO membership number and the name of the legal entity the "
            "membership is held by - it is often not the brand on the window.",
            "Check that the membership covers lettings, not only sales.",
            "Paste the membership name, number and status back into the report.",
        ],
    }


# ------------------------------------------------------------------------ main --
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # --verbose is accepted before or after the subcommand; SUPPRESS keeps the
    # subparser default from clobbering a value given at the top level.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS,
                        help="print curl commands to stderr")
    ap.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS,
                    help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("cmp", parents=[common], help="Client Money Protect member search")
    p.add_argument("--agent", required=True)

    p = sub.add_parser("heat-trust", parents=[common], help="Heat Trust registered sites and participants")
    p.add_argument("--site")
    p.add_argument("--supplier")

    p = sub.add_parser("rogue", parents=[common], help="GLA Rogue Landlord and Agent Checker")
    p.add_argument("--name")
    p.add_argument("--address")

    sub.add_parser("prs", parents=[common], help="Property Redress Scheme (manual, no fetch)")
    sub.add_parser("tpo", parents=[common], help="The Property Ombudsman (manual, no fetch)")

    a = ap.parse_args()
    a.verbose = getattr(a, "verbose", False)
    try:
        if a.cmd == "cmp":
            out = cmp_search(a.agent, verbose=a.verbose)
        elif a.cmd == "heat-trust":
            out = heat_trust(a.site, a.supplier, verbose=a.verbose)
        elif a.cmd == "rogue":
            if not a.name and not a.address:
                ap.error("rogue needs --name and/or --address")
            out = rogue(a.name, a.address, verbose=a.verbose)
        elif a.cmd == "prs":
            out = prs()
        else:
            out = tpo()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("redress.py: %s" % e, file=sys.stderr)
        sys.exit(1)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not out.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
