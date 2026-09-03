#!/usr/bin/env python3
"""GOV.UK Energy Performance Certificate (EPC) register — official, free, no key.

There is NO JSON API on find-energy-certificate.service.gov.uk (the old
/api/domestic/... paths return 404). This tool reads the public HTML pages.
Note: the site's robots.txt disallows crawling for everyone; run this only for
addresses you are actually vetting, keep the built-in 1.2 s spacing, and do not
bulk-harvest. Chat products that honour robots.txt cannot fetch these pages —
ask the user to paste the certificate page instead (see references/inputs.md).

Usage:
  epc.py search --postcode "SE1 9SG"
  epc.py search --street "London Bridge Street" --town London
  epc.py cert 1090-0965-0722-3091-3203         # id or full URL
  epc.py building --postcode "SE8 3GS" [--match "Collier Point"] [--limit 80]
All commands print JSON. Every record carries source_url, retrieved_at,
http_status and evidence_class "G" (official register).
"""
import argparse
import collections
import html as htmlmod
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402

BASE = "https://find-energy-certificate.service.gov.uk"
CERT_RE = re.compile(r"/energy-certificate/([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4})")
# Three pages that are real answers, not failures, and none of which carries a result
# table. A search that comes back on one of these has been answered; the answer is
# "nothing here" or "too many to list", and recording it as a fetch failure hides a
# fact behind an error.
TOO_MANY_MARKER = "Too many results for this address"    # busy street: search by postcode
NIL_POSTCODE_MARKER = "No results for"                   # postcode with no certificates
NIL_STREET_MARKER = "was not found at this address"      # street with no certificates


def _clean(s):
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


# ---------------------------------------------------------------- search ----
def search(postcode=None, street=None, town=None):
    if postcode:
        pc = re.sub(r"\s+", " ", postcode.strip().upper())
        url = f"{BASE}/find-a-certificate/search-by-postcode?postcode={pc.replace(' ', '%20')}"
    elif street and town:
        url = (f"{BASE}/find-a-certificate/search-by-street-name-and-town?"
               f"street_name={street.strip().replace(' ', '%20')}&town={town.strip().replace(' ', '%20')}")
    else:
        raise SystemExit("search needs --postcode or --street and --town")
    res = fetch(url, expect=lambda b: "epb-search-results" in b or "no certificates" in b.lower()
                or "could not find" in b.lower() or TOO_MANY_MARKER in b
                or NIL_STREET_MARKER in b or NIL_POSTCODE_MARKER in b)
    too_many = bool(res["ok"] and TOO_MANY_MARKER in res["body"]
                    and "epb-search-results" not in res["body"])
    rows = []
    if res["ok"]:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", res["body"], re.S):
            m = CERT_RE.search(tr)
            if not m:
                continue
            a = re.search(r"<a[^>]*href=\"/energy-certificate/[0-9-]+\"[^>]*>(.*?)</a>", tr, re.S)
            cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            rows.append({
                "certificate_id": m.group(1),
                "address": _clean(a.group(1)) if a else None,
                "rating": cells[0] if cells else None,
                "valid_until": cells[1] if len(cells) > 1 else None,
                "certificate_url": f"{BASE}/energy-certificate/{m.group(1)}",
            })
    out = {
        "query": {"postcode": postcode, "street": street, "town": town},
        "source_url": url, "http_status": res["status"], "ok": res["ok"], "note": res["note"],
        "retrieved_at": res["retrieved_at"], "evidence_class": "G",
        "count": len(rows), "results": rows,
        "too_many_results": too_many,
        "no_results": bool(res["ok"] and not rows and not too_many),
        "caveat": ("Large buildings are often split across several postcodes; if a flat is missing, "
                   "search by street name and town."),
    }
    if out["no_results"]:
        out["not_found"] = {
            "query": url,
            "meaning": ("the register answered and listed nothing: it holds no certificate "
                        "for this search. It only lists properties that have one."),
            "next_step": "try the other search (street instead of postcode, or the reverse)",
        }
    if too_many:
        # The register refuses a street search that would return too many rows and says
        # so on a page of its own: "There are too many results. Search by postcode
        # instead." That is a real answer, not a fetch failure, and it hits exactly the
        # busiest streets - so a caller enumerating an area must fall back to postcodes
        # or it will silently lose the streets with the most homes on them.
        out["not_found"] = {
            "query": url,
            "meaning": ("the register returned its 'Too many results for this address' page: "
                        "this street has more certificates than the street search will list. "
                        "Search by postcode instead."),
            "next_step": "epc.py search --postcode <pc> for each postcode on the street",
        }
    return out


# ------------------------------------------------------------------ cert ----
def parse_certificate(body):
    d = {}
    pairs = re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", body, re.S)
    kv = {}
    for k, v in pairs:
        k, v = _clean(k), _clean(v)
        kv.setdefault(k, v)  # first occurrence wins
    d["property_type"] = kv.get("Property type")
    m = re.search(r"([\d.]+)\s*square metres", kv.get("Total floor area", "") or "")
    d["total_floor_area_m2"] = float(m.group(1)) if m else None
    d["total_floor_area_sqft"] = round(d["total_floor_area_m2"] * 10.7639) if d["total_floor_area_m2"] else None
    d["date_of_assessment"] = kv.get("Date of assessment")
    d["date_of_certificate"] = kv.get("Date of certificate")
    m = re.search(r"Type of assessment\s+Show information about the (SAP|RdSAP)", _clean(body))
    d["assessment_type"] = m.group(1) if m else None
    m = re.search(r"<label>\s*Valid until\s*</label>\s*<p[^>]*>(.*?)</p>", body, re.S)
    d["valid_until"] = _clean(m.group(1)) if m else None
    m = re.search(r"<label>\s*Certificate number\s*</label>\s*<p[^>]*>(.*?)</p>", body, re.S)
    d["certificate_number"] = _clean(m.group(1)) if m else None
    m = re.search(r"energy rating is ([A-G]) with a score of (\d+)", _clean(body))
    d["energy_rating"] = m.group(1) if m else None
    d["energy_score"] = int(m.group(2)) if m else None
    m = re.search(r"potential energy rating of ([A-G]) with a score of (\d+)", _clean(body))
    d["potential_rating"] = m.group(1) if m else None
    # address: first <h1>/<p> block after "Energy performance certificate (EPC)" heading
    m = re.search(r"<p class=\"epc-address govuk-body\">(.*?)</p>", body, re.S)
    if not m:
        m = re.search(r"Energy performance certificate \(EPC\)\s*</h1>\s*<p[^>]*>(.*?)</p>", body, re.S)
    addr = _clean(m.group(1)) if m else None
    d["address"] = addr if addr and len(addr) <= 200 else None
    # features table
    feats = {}
    for tb in re.findall(r"<table[^>]*>(.*?)</table>", body, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S)
        if not rows or "Feature" not in _clean(rows[0]):
            continue
        for r in rows[1:]:
            cells = [_clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
            if len(cells) >= 2:
                feats[cells[0]] = {"description": cells[1], "rating": cells[2] if len(cells) > 2 else None}
    d["features"] = feats
    mh = (feats.get("Main heating") or {}).get("description", "") or ""
    hw = (feats.get("Hot water") or {}).get("description", "") or ""
    heat = "unknown"
    low = (mh + " " + hw).lower()
    if "community" in low:
        heat = "community_heat_network"
    elif "heat pump" in low:
        heat = "heat_pump"
    elif "mains gas" in low or "boiler" in low:
        heat = "gas_boiler"
    elif "electric" in low or "storage heater" in low:
        heat = "electric"
    d["heating_class"] = heat
    d["main_heating"] = mh or None
    d["hot_water"] = hw or None
    m = re.search(r"Air permeability\s*([\d.]+)\s*m", (feats.get("Air tightness") or {}).get("description", "") or "")
    d["air_permeability"] = float(m.group(1)) if m else None
    d["mechanical_ventilation_inferred"] = (d["air_permeability"] is not None and d["air_permeability"] <= 5.0)
    c = _clean(body)
    m = re.search(r"([\d,]+)\s*kWh per year for heating", c)
    d["kwh_per_year_heating"] = int(m.group(1).replace(",", "")) if m else None
    m = re.search(r"([\d,]+)\s*kWh per year for hot water", c)
    d["kwh_per_year_hot_water"] = int(m.group(1).replace(",", "")) if m else None
    pt = (d["property_type"] or "").lower()
    d["floor_position"] = ("ground" if "ground" in pt else "basement" if "basement" in pt
                           else "top" if "top" in pt else "mid" if "mid" in pt else None)
    m = re.search(r"Other certificates for this property</h\d>(.*?)(?:<h2|</main)", body, re.S)
    d["other_certificates"] = sorted(set(CERT_RE.findall(m.group(1)))) if m else []
    d["first_assessment_year"] = None
    m = re.search(r"(\d{4})$", d["date_of_assessment"] or "")
    if m:
        d["first_assessment_year"] = int(m.group(1))  # earliest known; refine via other_certificates
    return d


def cert(id_or_url, follow_history=False):
    m = CERT_RE.search(id_or_url) or re.search(r"([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4})", id_or_url)
    if not m:
        raise SystemExit("not a certificate id/url: " + id_or_url)
    cid = m.group(1)
    url = f"{BASE}/energy-certificate/{cid}"
    res = fetch(url, cache_ttl=7 * 86400, expect=lambda b: "Total floor area" in b)
    out = {"certificate_id": cid, "source_url": url, "http_status": res["status"], "ok": res["ok"],
           "note": res["note"], "retrieved_at": res["retrieved_at"], "evidence_class": "G"}
    if res["ok"]:
        out.update(parse_certificate(res["body"]))
        if follow_history and out.get("other_certificates"):
            hist = []
            for oc in out["other_certificates"]:
                r2 = fetch(f"{BASE}/energy-certificate/{oc}", cache_ttl=7 * 86400,
                           expect=lambda b: "Total floor area" in b)
                if r2["ok"]:
                    p = parse_certificate(r2["body"])
                    hist.append({"certificate_id": oc, "date_of_assessment": p["date_of_assessment"],
                                 "energy_rating": p["energy_rating"], "energy_score": p["energy_score"],
                                 "total_floor_area_m2": p["total_floor_area_m2"]})
            out["history"] = hist
            years = [int(h["date_of_assessment"][-4:]) for h in hist if h.get("date_of_assessment")]
            if out.get("first_assessment_year"):
                years.append(out["first_assessment_year"])
            if years:
                out["first_assessment_year"] = min(years)
    return out


# -------------------------------------------------------------- building ----
def building(postcode=None, street=None, town=None, match=None, limit=120):
    s = search(postcode=postcode, street=street, town=town)
    rows = s["results"]
    if match:
        rows = [r for r in rows if match.lower() in (r["address"] or "").lower()]
    rows = rows[:limit]
    certs = []
    for r in rows:
        c = cert(r["certificate_id"])
        c["address"] = r["address"] or c.get("address")
        certs.append(c)
    ok = [c for c in certs if c.get("ok")]
    areas = [c["total_floor_area_m2"] for c in ok if c.get("total_floor_area_m2")]
    years = [c["first_assessment_year"] for c in ok if c.get("first_assessment_year")]
    hist = collections.Counter()
    for a in areas:
        hist[f"{int(a // 10) * 10}-{int(a // 10) * 10 + 9} m2"] += 1
    summary = {
        "certificates_found": len(rows), "certificates_parsed": len(ok),
        "floor_area_m2": {"min": min(areas) if areas else None, "median": sorted(areas)[len(areas) // 2] if areas else None,
                          "max": max(areas) if areas else None, "histogram": dict(sorted(hist.items()))},
        "property_types": dict(collections.Counter(c.get("property_type") for c in ok)),
        "ground_or_basement_flats": sum(1 for c in ok if c.get("floor_position") in ("ground", "basement")),
        "earliest_assessment_year": min(years) if years else None,
        "assessment_year_counts": dict(sorted(collections.Counter(years).items())),
        "assessment_types": dict(collections.Counter(c.get("assessment_type") for c in ok)),
        "heating_classes": dict(collections.Counter(c.get("heating_class") for c in ok)),
        "air_permeability_values": sorted(c["air_permeability"] for c in ok if c.get("air_permeability") is not None),
        "caveat": ("Earliest assessment year approximates completion year for new builds (SAP) but a building "
                   "may have older certificates under other postcodes. Floor areas exclude balconies."),
    }
    return {"query": s["query"], "search_url": s["source_url"], "retrieved_at": now_iso(),
            "evidence_class": "G", "summary": summary, "certificates": certs}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search"); p.add_argument("--postcode"); p.add_argument("--street"); p.add_argument("--town")
    p = sub.add_parser("cert"); p.add_argument("id"); p.add_argument("--history", action="store_true",
                                                                       help="also fetch earlier certificates")
    p = sub.add_parser("building"); p.add_argument("--postcode"); p.add_argument("--street"); p.add_argument("--town")
    p.add_argument("--match"); p.add_argument("--limit", type=int, default=120)
    a = ap.parse_args()
    if a.cmd == "search":
        out = search(a.postcode, a.street, a.town)
    elif a.cmd == "cert":
        out = cert(a.id, follow_history=a.history)
    else:
        out = building(a.postcode, a.street, a.town, a.match, a.limit)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
