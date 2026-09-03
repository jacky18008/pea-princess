#!/usr/bin/env python3
"""Companies House - who the legal entity behind a tenancy actually is.

Source: the public "Find and update company information" site,
https://find-and-update.company-information.service.gov.uk - official, free,
no key, no login. The host serves **no robots.txt at all** (404), so nothing is
disallowed for any user agent; keep the built-in 1.2 s spacing anyway.

Optional REST API: if a file named `.env` sits next to this script and contains
a line `COMPANIES_HOUSE_KEY=<key>` (or the same name is in the environment),
`--api` switches to https://api.company-information.service.gov.uk, which is the
same data as JSON. The key is free but registering for one is a human step, so
the HTML path is the default and is enough for vetting.

Why the *advanced* search and not /search/companies: the plain search page does
not carry company status, so a dissolved shell looks exactly like a trading
company. /advanced-search/get-results?companyNameIncludes=<text> returns status,
company type, incorporation date, dissolution date, registered office and SIC
codes in one server-rendered table. Address lookup uses the same endpoint with
?registeredOfficeAddress=<text>; the site's own count is a loose token match, so
this script re-filters the rows itself and reports both numbers.

Brand is not landlord. The name on the hoarding, the website and the viewing
appointment is very often a different legal entity from the one that will sign
the tenancy agreement. Vet the entity printed on the agreement.

Usage:
  company.py search --name "Get Living"
  company.py profile 08854998
  company.py filings 08854998 --limit 40
  company.py address-search --query "SE1 9SG"
  company.py heat-supplier --name "Loka Energy"
All commands print one JSON object. Every fetched record carries source_url,
http_status, ok, note, retrieved_at and evidence_class ("G" official register,
"I" where this script infers something the register does not state).
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402

BASE = "https://find-and-update.company-information.service.gov.uk"
API_BASE = "https://api.company-information.service.gov.uk"
HERE = os.path.dirname(os.path.abspath(__file__))

BRAND_NOTE = ("brand != landlord; the legal entity named on the tenancy agreement is what matters")

# SIC -> what the company probably does with property.
SIC_LANDLORD_HINTS = {
    "68209": ("owner_or_investor",
              "68209 letting and operating of own or leased real estate - likely owns the property"),
    "68310": ("agent_not_owner",
              "68310 real estate agencies - an agent acting for an owner, not the owner"),
    "68320": ("managing_agent",
              "68320 management of real estate on a fee basis - managing agent"),
    "68100": ("buying_selling",
              "68100 buying and selling of own real estate - trades property rather than lets it"),
}
SIC_PRIORITY = ["68209", "68310", "68320", "68100"]

RMC_PATTERNS = [
    (r"\bR\.?T\.?M\.?\b", "RTM in the name"),
    (r"RIGHT[\s-]*TO[\s-]*MANAGE", "'right to manage' in the name"),
    (r"RESIDENTS?'?S?\s+(MANAGEMENT|ASSOCIATION|COMPANY)", "residents' management company"),
    (r"\bMANAGEMENT\s+(COMPANY|CO\.?|LIMITED|LTD)\b", "'management company' in the name"),
    (r"\bFREEHOLD\b", "'freehold' in the name"),
    (r"\bLESSEES?\b", "'lessee(s)' in the name"),
    (r"\bCOMMONHOLD\b", "'commonhold' in the name"),
]

INSOLVENCY_WORDS = [
    "liquidation", "liquidator", "administration", "administrator",
    "receivership", "receiver", "insolvenc", "winding up", "winding-up",
    "strike off", "strike-off", "struck off", "dissolution", "voluntary arrangement",
    "gazette",
]


# ------------------------------------------------------------------ utils ----
def _clean(s):
    if s is None:
        return None
    t = htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()
    return t or None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def read_dotenv(path=None):
    """Parse KEY=VALUE lines from a .env next to this script. No dependencies."""
    path = path or os.path.join(HERE, ".env")
    out = {}
    if not os.path.exists(path):
        return out
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            out[k.strip()] = v
    except OSError:
        return {}
    return out


def api_key():
    return os.environ.get("COMPANIES_HOUSE_KEY") or read_dotenv().get("COMPANIES_HOUSE_KEY")


def _note(res):
    """_fetch keeps the note from a cached failure even when this run's assertion
    passed. Do not report a stale failure as a live one."""
    n = res.get("note") or ""
    return "" if res["ok"] and "assertion failed" in n else n


def _envelope(url, res, evidence_class="G"):
    return {"source_url": url, "http_status": res["status"], "ok": res["ok"],
            "note": _note(res), "retrieved_at": res["retrieved_at"],
            "evidence_class": evidence_class}


# --------------------------------------------------------- SIC classifier ----
def classify_sic(sic_codes):
    """sic_codes: list of {"code","description"} or bare code strings."""
    codes = []
    for s in sic_codes or []:
        codes.append(s.get("code") if isinstance(s, dict) else str(s))
    codes = [c for c in codes if c]
    for want in SIC_PRIORITY:
        if want in codes:
            hint, why = SIC_LANDLORD_HINTS[want]
            return {"landlord_type_hint": hint, "matched_sic": want, "reason": why,
                    "note": BRAND_NOTE, "evidence_class": "I"}
    return {"landlord_type_hint": "other", "matched_sic": None,
            "reason": ("no property SIC code (68100/68209/68310/68320) on the record; "
                       "this company's registered activity is something else"),
            "note": BRAND_NOTE, "evidence_class": "I"}


# ------------------------------------------------------- advanced search  ----
def parse_advanced_results(body):
    """Rows of /advanced-search/get-results. One <td> per company."""
    rows = []
    for cell in re.findall(r'<td class="govuk-table__cell">(.*?)</td>', body, re.S):
        m = re.search(r'href=["\']?/company/([0-9A-Z]+)["\']?', cell)
        if not m:
            continue
        number = m.group(1)
        a = re.search(r'href=["\']?/company/[0-9A-Z]+["\']?[^>]*>(.*?)(?:<span|</a>)', cell, re.S)
        name = _clean(a.group(1)) if a else None
        st = re.search(r'<span class="govuk-body govuk-!-font-weight-bold">(.*?)</span>', cell, re.S)
        status = _clean(st.group(1)) if st else None
        lis = [_clean(x) or "" for x in re.findall(r"<li>(.*?)</li>", cell, re.S)]
        incorporated = dissolved = sic_raw = event = None
        used = set()
        for i, li in enumerate(lis):
            # "12503016 - Incorporated on 6 March 2020"; overseas entities say
            # "OE006451 - Registered on 5 December 2022"
            mi = re.match(r"^[0-9A-Z]+\s*-\s*([A-Za-z ]+?)\s+on\s+(.+)$", li)
            if mi and incorporated is None:
                event = mi.group(1).strip()
                incorporated = mi.group(2).strip()
                used.add(i)
                continue
            md = re.match(r"^Dissolved on\s+(.+)$", li)
            if md and dissolved is None:
                dissolved = md.group(1).strip()
                used.add(i)
                continue
            ms = re.match(r"^SIC codes?\s*-\s*(.+)$", li)
            if ms and sic_raw is None:
                sic_raw = ms.group(1).strip()
                used.add(i)
                continue
        ctype = lis[0] if lis else None
        if lis:
            used.add(0)
        address = None
        for i, li in enumerate(lis):
            if i in used or not li:
                continue
            address = li
        sic_codes = [c.strip() for c in re.split(r"[,\s]+", sic_raw) if c.strip()] if sic_raw else []
        rows.append({
            "company_number": number, "name": name, "status": status,
            "incorporated": incorporated, "registration_event": event,
            "dissolved_on": dissolved,
            "company_type": ctype, "address": address, "sic_codes": sic_codes,
            "company_url": BASE + "/company/" + number,
            "dissolved": bool(status and "dissolv" in status.lower()),
        })
    return rows


ADV_RESULTS_RE = re.compile(r'<p class="govuk-heading-m">\s*[\d,]+\s*results?\s*</p>')


def _is_advanced_results(body):
    """A 200 from the wrong page is a failure. The results page renders either a
    "<n> results" count or an explicit "No results found" panel; anything else
    (a cookie page, a 404, an outage) is not an answer."""
    return bool(ADV_RESULTS_RE.search(body)) or 'id="no-results"' in body


def _advanced_total(body):
    m = re.search(r'<p class="govuk-heading-m">\s*([\d,]+)\s*results?\s*</p>', body)
    return int(m.group(1).replace(",", "")) if m else None


def _advanced_fetch(param, value, page=None, verbose=False):
    url = "%s/advanced-search/get-results?%s=%s" % (BASE, param, _q(value))
    if page and page > 1:
        url += "&page=%d" % page
    res = fetch(url, expect=_is_advanced_results, verbose=verbose)
    return url, res


def _q(s):
    return re.sub(r"\s+", "+", (s or "").strip()).replace("&", "%26")


# ---------------------------------------------------------------- search  ----
def search(name, limit=40, verbose=False):
    url, res = _advanced_fetch("companyNameIncludes", name, verbose=verbose)
    out = {"query": {"name": name}}
    out.update(_envelope(url, res))
    out["endpoint_used"] = ("advanced-search/get-results?companyNameIncludes= "
                            "(the plain /search/companies page omits company status)")
    rows = parse_advanced_results(res["body"]) if res["ok"] else []
    out["total_reported_by_site"] = _advanced_total(res["body"]) if res["ok"] else None
    if res["ok"] and out["total_reported_by_site"] is None and 'id="no-results"' in res["body"]:
        out["total_reported_by_site"] = 0
    out["count"] = len(rows[:limit])
    out["results"] = rows[:limit]
    diss = [r for r in rows[:limit] if r["dissolved"]]
    out["dissolved_count"] = len(diss)
    out["dissolved_company_numbers"] = [r["company_number"] for r in diss]
    out["same_name_warning"] = (
        "Several companies can share almost the same name, and a dissolved shell keeps its name "
        "on the register forever. Match on the company NUMBER printed on the tenancy agreement, "
        "not on the name. " + BRAND_NOTE)
    if not rows:
        out["not_found"] = {"query": name, "endpoint": url}
    return out


# --------------------------------------------------------------- profile  ----
def parse_profile(body):
    d = {}
    m = re.search(r'<h1 class="heading-xlarge"[^>]*>(.*?)</h1>', body, re.S)
    d["name"] = _clean(m.group(1)) if m else None
    m = re.search(r'<p id="company-number">.*?<strong>(.*?)</strong>', body, re.S)
    d["company_number"] = _clean(m.group(1)) if m else None
    m = re.search(r'id="roa-address"[^>]*>(.*?)</span>', body, re.S)
    d["registered_office_address"] = _clean(m.group(1)) if m else None
    m = re.search(r'id="company-status"[^>]*>(.*?)</dd>', body, re.S)
    d["status"] = _clean(m.group(1)) if m else None
    m = re.search(r'id="company-type-value"[^>]*>(.*?)</span>', body, re.S)
    d["company_type"] = _clean(m.group(1)) if m else None
    m = re.search(r'id="company-creation-date"[^>]*>(.*?)</dd>', body, re.S)
    d["incorporated_on"] = _clean(m.group(1)) if m else None
    m = re.search(r'id="cessation-date"[^>]*>(.*?)</dd>', body, re.S)
    d["dissolved_on"] = _clean(m.group(1)) if m else None

    # ----- accounts / confirmation statement blocks
    acc = re.search(r"<strong>Accounts</strong>(.*?)(?:<div class=\"column-half\">|</div>)", body, re.S)
    acc_txt = acc.group(1) if acc else ""
    d["accounts"] = {
        "next_made_up_to": _first_strong(acc_txt, r"Next accounts made up to"),
        "next_due": _first_strong(acc_txt, r"due by"),
        "last_made_up_to": _first_strong(acc_txt, r"Last accounts made up to"),
        "overdue": bool(re.search(r"overdue", acc_txt, re.I)),
    }
    cs = re.search(r"<strong>Confirmation statement</strong>(.*?)</div>", body, re.S)
    cs_txt = cs.group(1) if cs else ""
    d["confirmation_statement"] = {
        "next_statement_date": _first_strong(cs_txt, r"Next statement date"),
        "next_due": _first_strong(cs_txt, r"due by"),
        "last_statement_dated": _first_strong(cs_txt, r"Last statement dated"),
        "overdue": bool(re.search(r"overdue", cs_txt, re.I)),
    }

    # ----- SIC
    sic = []
    for raw in re.findall(r'<span id="sic\d+">(.*?)</span>', body, re.S):
        t = _clean(raw) or ""
        m = re.match(r"^(\d{4,5})\s*-\s*(.+)$", t)
        if m:
            sic.append({"code": m.group(1), "description": m.group(2).strip()})
        elif t:
            sic.append({"code": None, "description": t})
    d["sic_codes"] = sic

    # ----- previous names
    prev = []
    for m in re.finditer(r'id="previous-name-(\d+)">(.*?)</td>.*?id="previous-date-\1">(.*?)</td>',
                         body, re.S):
        prev.append({"name": _clean(m.group(2)), "period": _clean(m.group(3))})
    d["previous_names"] = prev

    # ----- insolvency signals visible on the profile itself
    sig = []
    if re.search(r'id="insolvency-tab"', body):
        sig.append("profile page shows an Insolvency tab")
    st = (d["status"] or "").lower()
    for w in ("liquidation", "administration", "receivership", "strike off", "strike-off",
              "insolvenc", "voluntary arrangement", "dissolved"):
        if w in st:
            sig.append("company status is '%s'" % d["status"])
            break
    d["insolvency_signals_profile"] = sig
    return d


def _first_strong(block, label):
    m = re.search(re.escape(label) + r"\s*<strong>(.*?)</strong>", block, re.S | re.I)
    return _clean(m.group(1)) if m else None


def parse_charges(body):
    d = {"total": None, "outstanding": None, "satisfied": None, "part_satisfied": None,
         "charges": []}
    m = re.search(r'id="company-mortgages"[^>]*>\s*([\d,]+)\s*charges? registered', body)
    if m:
        d["total"] = int(m.group(1).replace(",", ""))
    m = re.search(r'id="company-mortgages-breakdown"[^>]*>\s*([^<]*)', body)
    if m:
        t = m.group(1)
        for key, pat in (("outstanding", r"([\d,]+)\s+outstanding"),
                         ("satisfied", r"([\d,]+)\s+satisfied"),
                         ("part_satisfied", r"([\d,]+)\s+part satisfied")):
            mm = re.search(pat, t)
            if mm:
                d[key] = int(mm.group(1).replace(",", ""))
    for m in re.finditer(r'id="mortgage-heading-(\d+)"[^>]*>(.*?)</a>', body, re.S):
        i = m.group(1)
        item = {"charge": _clean(m.group(2)), "created": None, "delivered": None,
                "status": None, "persons_entitled": []}
        for key, pat in (("created", r'id="mortgage-created-on-%s"[^>]*>(.*?)</dd>'),
                         ("delivered", r'id="mortgage-delivered-on-%s"[^>]*>(.*?)</dd>'),
                         ("status", r'id="mortgage-status-%s"[^>]*>(.*?)</dd>')):
            mm = re.search(pat % i, body, re.S)
            if mm:
                item[key] = _clean(mm.group(1))
        pe = re.search(r'id="persons-entitled-%s">(.*?)</ul>' % i, body, re.S)
        if pe:
            item["persons_entitled"] = [_clean(x) for x in re.findall(r"<li[^>]*>(.*?)</li>",
                                                                      pe.group(1), re.S)]
        d["charges"].append(item)
    return d


def parse_officers(body):
    """Names, roles and dates only. Dates of birth, nationality and residence are
    deliberately not extracted - they are personal data this tool has no use for."""
    officers = []
    for m in re.finditer(r'id="officer-name-(\d+)"[^>]*>(.*?)</span>', body, re.S):
        i = m.group(1)
        o = {"name": _clean(m.group(2)), "role": None, "status": None,
             "appointed_on": None, "resigned_on": None}
        for key, pat in (("status", r'id="officer-status-tag-%s"[^>]*>(.*?)</span>'),
                         ("role", r'id="officer-role-%s"[^>]*>(.*?)</dd>'),
                         ("appointed_on", r'id="officer-appointed-on-%s"[^>]*>(.*?)</dd>'),
                         ("resigned_on", r'id="officer-resigned-on-%s"[^>]*>(.*?)</dd>')):
            mm = re.search(pat % i, body, re.S)
            if mm:
                o[key] = _clean(mm.group(1))
        if o["status"] is None:
            o["status"] = "Resigned" if o["resigned_on"] else "Active"
        officers.append(o)
    m = re.search(r'id="company-appointments">(.*?)</h2>', body, re.S)
    head = _clean(m.group(1)) if m else None
    total = resignations = None
    if head:
        mm = re.search(r"([\d,]+)\s+officers?", head)
        total = int(mm.group(1).replace(",", "")) if mm else None
        mm = re.search(r"([\d,]+)\s+resignations?", head)
        resignations = int(mm.group(1).replace(",", "")) if mm else None
    active = [o for o in officers if (o["status"] or "").lower().startswith("active")]
    return {"officers": officers, "active_officer_count": len(active),
            "officers_listed": len(officers), "officers_header": head,
            "officers_total_reported": total, "resignations_reported": resignations}


def profile(number, skip_filings=False, verbose=False):
    number = number.strip().upper()
    purl = "%s/company/%s" % (BASE, number)
    pres = fetch(purl, expect=lambda b: 'id="company-status"' in b, verbose=verbose)
    out = {"company_number": number}
    out.update(_envelope(purl, pres))
    if not pres["ok"]:
        out["not_found"] = {"query": number, "endpoint": purl}
        return out
    out.update(parse_profile(pres["body"]))

    curl = "%s/company/%s/charges" % (BASE, number)
    cres = fetch(curl, expect=lambda b: 'id="company-mortgages"' in b, verbose=verbose)
    ch = parse_charges(cres["body"]) if cres["ok"] else {}
    out["charges_source_url"] = curl
    out["charges_count"] = {"total": ch.get("total"), "outstanding": ch.get("outstanding"),
                            "satisfied": ch.get("satisfied"),
                            "part_satisfied": ch.get("part_satisfied"),
                            "ok": cres["ok"], "http_status": cres["status"]}
    out["charges"] = ch.get("charges", [])

    ourl = "%s/company/%s/officers" % (BASE, number)
    ores = fetch(ourl, expect=lambda b: 'id="company-appointments"' in b, verbose=verbose)
    of = parse_officers(ores["body"]) if ores["ok"] else {}
    out["officers_source_url"] = ourl
    out["officers"] = of.get("officers", [])
    out["active_officer_count"] = of.get("active_officer_count")
    out["officers_header"] = of.get("officers_header")

    signals = list(out.get("insolvency_signals_profile") or [])
    if not skip_filings:
        f = filings(number, limit=60, verbose=verbose)
        out["filing_history_source_url"] = f.get("source_url")
        for e in f.get("filings", []):
            blob = ((e.get("type") or "") + " " + (e.get("description") or "")).lower()
            for w in INSOLVENCY_WORDS:
                if w in blob:
                    signals.append("filing %s: %s" % (e.get("date"), (e.get("description") or "")[:120]))
                    break
        out["last_accounts_filed"] = (f.get("accounts_filings") or [None])[0]
    out["insolvency_flag"] = bool(signals)
    out["insolvency_signals"] = signals
    out["insolvency_note"] = ("insolvency_flag is a keyword scan of the profile and the most "
                              "recent filings; a clean flag is not a solvency opinion")
    cls = classify_sic(out.get("sic_codes"))
    out["landlord_type_hint"] = cls["landlord_type_hint"]
    out["landlord_type_matched_sic"] = cls["matched_sic"]
    out["landlord_type_reason"] = cls["reason"]
    out["landlord_type_evidence_class"] = cls["evidence_class"]
    out["note"] = ((out.get("note") + " ") if out.get("note") else "") + BRAND_NOTE
    return out


# --------------------------------------------------------------- filings  ----
FILING_ROW = re.compile(r"<tr>\s*<td class=\"nowrap\">(.*?)</td>\s*"
                        r"<td class=\"filing-type[^\"]*\">(.*?)</td>\s*"
                        r"<td>(.*?)</td>(.*?)</tr>", re.S)


def parse_filings(body, number=None, limit=40):
    entries = []
    for m in FILING_ROW.finditer(body):
        date = _clean(m.group(1))
        ftype = _clean(m.group(2))
        desc = _clean(m.group(3))
        doc = re.search(r'href="([^"]*/filing-history/[^"]+)"', m.group(4))
        url = doc.group(1) if doc else None
        if url and url.startswith("/"):
            url = BASE + url
        entries.append({"date": date, "type": ftype, "description": desc,
                        "document_url": htmlmod.unescape(url) if url else None})
        if len(entries) >= limit:
            break
    return entries


def _flag_filings(entries):
    addr, names, accounts = [], [], []
    for e in entries:
        blob = ((e.get("type") or "") + " " + (e.get("description") or "")).lower()
        if "registered office address changed" in blob or (e.get("type") or "").upper() == "AD01":
            addr.append(e)
        if "company name changed" in blob or (e.get("type") or "").upper().startswith("CERTNM") \
                or "change of name" in blob:
            names.append(e)
        if re.search(r"\baccounts\b", blob):
            m = re.search(r"made up to (.+)$", e.get("description") or "", re.I)
            accounts.append({"date": e["date"], "type": e["type"],
                             "made_up_to": (m.group(1).strip() if m else None),
                             "description": e["description"],
                             "document_url": e["document_url"]})
    return addr, names, accounts


def filings(number, limit=40, page=1, verbose=False):
    number = number.strip().upper()
    url = "%s/company/%s/filing-history" % (BASE, number)
    if page and page > 1:
        url += "?page=%d" % page
    res = fetch(url, expect=lambda b: 'id="fhTable"' in b or 'id="filing-history-content"' in b,
                verbose=verbose)
    out = {"company_number": number}
    out.update(_envelope(url, res))
    entries = parse_filings(res["body"], number, limit) if res["ok"] else []
    addr, names, accounts = _flag_filings(entries)
    out["count"] = len(entries)
    out["filings"] = entries
    out["registered_office_changes"] = addr
    out["name_changes"] = names
    out["accounts_filings"] = accounts
    out["page"] = page
    out["pages_available"] = sorted({int(x) for x in
                                     re.findall(r"filing-history\?page=(\d+)", res["body"])}) \
        if res["ok"] else []
    out["flags_note"] = ("A registered-office change or a name change around the time a block "
                         "was sold often marks a change of owner or a move away from the "
                         "developer's own address. Read them next to the accounts dates. "
                         "The site paginates: pass --page to read older filings.")
    if not entries:
        out["not_found"] = {"query": number, "endpoint": url}
    return out


# -------------------------------------------------------- address search  ----
def address_search(query, limit=100, pages=1, verbose=False):
    rows, urls, statuses, oks, notes = [], [], [], [], []
    total_site = None
    for p in range(1, max(1, pages) + 1):
        url, res = _advanced_fetch("registeredOfficeAddress", query, page=p, verbose=verbose)
        urls.append(url)
        statuses.append(res["status"])
        oks.append(res["ok"])
        notes.append(_note(res))
        if not res["ok"]:
            break
        page_rows = parse_advanced_results(res["body"])
        if p == 1:
            total_site = _advanced_total(res["body"])
            if total_site is None and 'id="no-results"' in res["body"]:
                total_site = 0
        rows += page_rows
        if len(page_rows) < 20:
            break

    needle = _norm(query)
    exact = [r for r in rows if needle and needle in _norm(r.get("address"))]
    rmc = []
    for r in exact or rows:
        why = [reason for pat, reason in RMC_PATTERNS
               if re.search(pat, (r.get("name") or "").upper())]
        if why:
            r = dict(r)
            r["rmc_rtm_signals"] = why
            rmc.append(r)
    out = {
        "query": {"address": query},
        "source_url": urls[0] if urls else None,
        "source_urls": urls,
        "http_status": statuses[0] if statuses else None,
        "ok": bool(oks and oks[0]),
        "note": (notes[0] if notes else ""),
        "retrieved_at": now_iso(),
        "evidence_class": "G",
        "endpoint_used": "advanced-search/get-results?registeredOfficeAddress=<text>",
        "endpoint_note": ("The site matches this field loosely (token match), so its own result "
                          "count can be far larger than the number of companies actually at the "
                          "address. This script re-filters the rows on the normalised address."),
        "total_reported_by_site": total_site,
        "rows_read": len(rows),
        "count": len(exact[:limit]),
        "results": exact[:limit],
        "rmc_rtm_candidates": rmc[:limit],
        "rmc_rtm_count": len(rmc),
    }
    if not rmc:
        out["rmc_rtm_inference"] = {
            "evidence_class": "I",
            "finding": ("zero RMC/RTM entries at this address means residents may have no route "
                        "to replace the managing agent"),
            "caveat": ("Inference, not a register fact. An RMC can be registered at its "
                       "accountant's or agent's address instead of the building, and a "
                       "right-to-manage company can be formed later. Confirm from the lease."),
        }
        out["not_found"] = {"query": query, "looked_for": "company names containing RMC/RTM markers",
                            "endpoint": urls[0] if urls else None}
    return out


# --------------------------------------------------------- heat supplier  ----
def heat_supplier(name, verbose=False):
    s = search(name, limit=20, verbose=verbose)
    best = None
    n = _norm(name)
    for r in s.get("results", []):
        if r["dissolved"]:
            continue
        if n and n in _norm(r["name"]):
            best = r
            break
    if best is None:
        for r in s.get("results", []):
            if not r["dissolved"]:
                best = r
                break
    out = {"query": {"name": name}, "retrieved_at": now_iso(), "evidence_class": "G",
           "search": {"source_url": s.get("source_url"), "count": s.get("count"),
                      "results": s.get("results", [])[:10],
                      "dissolved_count": s.get("dissolved_count")},
           "best_match": best}
    if best:
        p = profile(best["company_number"], verbose=verbose)
        out["profile"] = p
        acc = (p.get("last_accounts_filed") or {})
        out["latest_accounts"] = {
            "made_up_to": acc.get("made_up_to"),
            "filed": acc.get("date"),
            "document_url": acc.get("document_url"),
            "next_due": (p.get("accounts") or {}).get("next_due"),
            "overdue": (p.get("accounts") or {}).get("overdue"),
        }
    out["note"] = ("A heat network's supplier is often a single-purpose company owned by the "
                   "developer. Read the accounts dates and the charges: a supplier with one "
                   "asset and a secured lender has little room to absorb a price shock. "
                   + BRAND_NOTE)
    return out


# ------------------------------------------------------------------- API  ----
def api_profile(number, verbose=False):
    key = api_key()
    if not key:
        return {"access": "manual", "ok": False,
                "note": ("no COMPANIES_HOUSE_KEY in the environment or in a .env next to this "
                         "script; the HTML path (default) needs no key"),
                "register_at": "https://developer.company-information.service.gov.uk/",
                "retrieved_at": now_iso(), "evidence_class": "U"}
    import base64
    auth = base64.b64encode((key + ":").encode("ascii")).decode("ascii")
    url = "%s/company/%s" % (API_BASE, number.strip().upper())
    res = fetch(url, headers={"Authorization": "Basic " + auth, "Accept": "application/json"},
                expect=lambda b: b.lstrip().startswith("{"), verbose=verbose)
    out = {"company_number": number}
    out.update(_envelope(url, res))
    if res["ok"]:
        try:
            out["api"] = json.loads(res["body"])
        except ValueError:
            out["ok"] = False
            out["note"] = "response was not JSON"
    return out


# ------------------------------------------------------------------ main  ----
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

    p = sub.add_parser("search", parents=[common], help="companies whose name contains <text>")
    p.add_argument("--name", required=True)
    p.add_argument("--limit", type=int, default=40)

    p = sub.add_parser("profile", parents=[common], help="status, SIC, officers, charges, insolvency signals")
    p.add_argument("number")
    p.add_argument("--skip-filings", action="store_true",
                   help="do not read filing history (one fewer request, weaker insolvency check)")
    p.add_argument("--api", action="store_true",
                   help="also return the REST API record (needs COMPANIES_HOUSE_KEY)")

    p = sub.add_parser("filings", parents=[common], help="filing history with address/name/accounts flags")
    p.add_argument("number")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--page", type=int, default=1, help="filing-history page (1 = newest)")

    p = sub.add_parser("address-search", parents=[common], help="companies registered at an address (find the RMC/RTM)")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--pages", type=int, default=1)

    p = sub.add_parser("heat-supplier", parents=[common], help="search + profile + latest accounts for a heat supplier")
    p.add_argument("--name", required=True)

    a = ap.parse_args()
    a.verbose = getattr(a, "verbose", False)
    try:
        if a.cmd == "search":
            out = search(a.name, a.limit, verbose=a.verbose)
        elif a.cmd == "profile":
            out = profile(a.number, skip_filings=a.skip_filings, verbose=a.verbose)
            if a.api:
                out["api_record"] = api_profile(a.number, verbose=a.verbose)
        elif a.cmd == "filings":
            out = filings(a.number, a.limit, page=a.page, verbose=a.verbose)
        elif a.cmd == "address-search":
            out = address_search(a.query, a.limit, a.pages, verbose=a.verbose)
        else:
            out = heat_supplier(a.name, verbose=a.verbose)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("company.py: %s" % e, file=sys.stderr)
        sys.exit(1)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not out.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
