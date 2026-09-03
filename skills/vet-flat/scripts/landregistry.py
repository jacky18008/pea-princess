#!/usr/bin/env python3
"""HM Land Registry open linked data - Price Paid, by postcode. Official, keyless.

Endpoint: https://landregistry.data.gov.uk/landregistry/query - a public SPARQL
endpoint published by HM Land Registry. No key, no login, no fee. It answers
both POST (form field `query=`) and GET (`?query=`); this script POSTs by
default because long queries overflow a URL, and `--method get` is there for
hosts that only allow GET. Send `Accept: application/sparql-results+json`.

Price Paid Data covers *sales* of freehold and leasehold property in England and
Wales lodged for registration. It does not show lettings, and it does not name
the owner. To learn who owns a flat today you need the title register, which
costs GBP 7 and is behind a sign-in and a Cloudflare challenge - see the
`title` subcommand, which prints instructions and fetches nothing.

Why the earliest new-build sale matters: a transaction with `newBuild = true` is
the Land Registry recording the first sale of a newly built dwelling. The
earliest such date in a postcode is a hard lower bound on the building's
completion year, and it is independent of the marketing brochure.

The SPARQL used by `price-paid`:

    PREFIX lrppi:    <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
    PREFIX xsd:      <http://www.w3.org/2001/XMLSchema#>
    SELECT ?date ?amount ?paon ?saon ?street ?town ?ptype ?newbuild ?estate ?category
    WHERE {
      ?tx lrppi:propertyAddress ?addr ;
          lrppi:pricePaid        ?amount ;
          lrppi:transactionDate  ?date ;
          lrppi:transactionCategory ?category .
      ?addr lrcommon:postcode "<POSTCODE>" .
      OPTIONAL { ?addr lrcommon:paon   ?paon }
      OPTIONAL { ?addr lrcommon:saon   ?saon }
      OPTIONAL { ?addr lrcommon:street ?street }
      OPTIONAL { ?addr lrcommon:town   ?town }
      OPTIONAL { ?tx lrppi:propertyType ?ptype }
      OPTIONAL { ?tx lrppi:newBuild     ?newbuild }
      OPTIONAL { ?tx lrppi:estateType   ?estate }
      # with --since: FILTER (?date >= "<YEAR>-01-01"^^xsd:date)
    }
    ORDER BY ?date
    LIMIT <n>

The postcode literal must be upper case and spaced exactly as the register holds
it ("SE1 9SG", not "se19sg"); this script normalises it for you.

Usage:
  landregistry.py price-paid --postcode "SE1 2BE"
  landregistry.py price-paid --postcode "SE1 2BE" --since 2015 --paon "ST. SAVIOURS WHARF"
  landregistry.py title --help-only
Prints one JSON object with source_url, http_status, ok, note, retrieved_at and
evidence_class "G" (official register).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402

ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"
TITLE_SERVICE = "https://search-property-information.service.gov.uk/"
TITLE_GUIDE = "https://www.gov.uk/search-property-information-land-registry"


def normalise_postcode(pc):
    s = re.sub(r"\s+", "", (pc or "")).upper()
    if len(s) < 5:
        return (pc or "").strip().upper()
    return s[:-3] + " " + s[-3:]


def build_query(postcode, since=None, limit=500):
    flt = ''
    if since:
        flt = '  FILTER (?date >= "%d-01-01"^^xsd:date)\n' % int(since)
    return (
        'PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>\n'
        'PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>\n'
        'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n'
        'SELECT ?date ?amount ?paon ?saon ?street ?town ?ptype ?newbuild ?estate ?category\n'
        'WHERE {\n'
        '  ?tx lrppi:propertyAddress ?addr ;\n'
        '      lrppi:pricePaid ?amount ;\n'
        '      lrppi:transactionDate ?date ;\n'
        '      lrppi:transactionCategory ?category .\n'
        '  ?addr lrcommon:postcode "%s" .\n'
        '  OPTIONAL { ?addr lrcommon:paon ?paon }\n'
        '  OPTIONAL { ?addr lrcommon:saon ?saon }\n'
        '  OPTIONAL { ?addr lrcommon:street ?street }\n'
        '  OPTIONAL { ?addr lrcommon:town ?town }\n'
        '  OPTIONAL { ?tx lrppi:propertyType ?ptype }\n'
        '  OPTIONAL { ?tx lrppi:newBuild ?newbuild }\n'
        '  OPTIONAL { ?tx lrppi:estateType ?estate }\n'
        '%s'
        '}\n'
        'ORDER BY ?date\n'
        'LIMIT %d' % (postcode, flt, int(limit))
    )


def _pct(s):
    return re.sub(r"[^A-Za-z0-9._~-]", lambda m: "".join("%%%02X" % b for b in m.group(0).encode()), s)


def _note(res):
    """_fetch keeps the note from a cached failure even when this run's assertion
    passed. Do not report a stale failure as a live one."""
    n = res.get("note") or ""
    return "" if res["ok"] and "assertion failed" in n else n


def _local(uri):
    if not uri:
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def _val(binding, key):
    b = binding.get(key)
    return b.get("value") if b else None


def parse_results(payload):
    """SPARQL JSON results -> list of transaction dicts, sorted by date."""
    j = payload if isinstance(payload, dict) else json.loads(payload)
    rows = []
    for b in j.get("results", {}).get("bindings", []):
        nb = _val(b, "newbuild")
        amount = _val(b, "amount")
        rows.append({
            "date": _val(b, "date"),
            "price": int(amount) if amount and amount.isdigit() else None,
            "paon": _val(b, "paon"),
            "saon": _val(b, "saon"),
            "street": _val(b, "street"),
            "town": _val(b, "town"),
            "property_type": _local(_val(b, "ptype")),
            "new_build": (nb == "true") if nb is not None else None,
            "estate_type": _local(_val(b, "estate")),
            "category": _local(_val(b, "category")),
        })
    rows.sort(key=lambda r: (r["date"] or "", r["price"] or 0))
    return rows


def summarise(rows, paon=None):
    out = {"count": len(rows)}
    out["earliest_transaction"] = rows[0] if rows else None
    out["latest_transaction"] = rows[-1] if rows else None
    nb = [r for r in rows if r["new_build"]]
    out["new_build_count"] = len(nb)
    out["earliest_new_build_transaction"] = nb[0] if nb else None
    out["earliest_new_build_year"] = int(nb[0]["date"][:4]) if nb and nb[0]["date"] else None
    out["completion_year_note"] = (
        "earliest_new_build_transaction is the first recorded sale of a newly built dwelling in "
        "this postcode: strong evidence the building was finished by that year. Absence of a "
        "new-build row is not evidence the building is old - flats sold by the developer under a "
        "different postcode, or never sold at all (build to rent), leave no trace here.")
    if paon:
        needle = re.sub(r"[^a-z0-9]+", " ", paon.lower()).strip()
        same = [r for r in rows
                if needle and needle in re.sub(r"[^a-z0-9]+", " ",
                                               ((r["paon"] or "") + " " + (r["saon"] or "")).lower())]
        out["same_building_matches"] = {"query": paon, "count": len(same), "transactions": same}
        if same:
            out["same_building_price_range"] = {
                "min": min(r["price"] for r in same if r["price"]) if any(r["price"] for r in same) else None,
                "max": max(r["price"] for r in same if r["price"]) if any(r["price"] for r in same) else None,
                "first_date": same[0]["date"], "last_date": same[-1]["date"]}
    return out


def price_paid(postcode, since=None, paon=None, limit=500, method="post", verbose=False):
    pc = normalise_postcode(postcode)
    q = build_query(pc, since=since, limit=limit)
    if method == "get":
        url = ENDPOINT + "?query=" + _pct(q)
        res = fetch(url, headers={"Accept": "application/sparql-results+json"},
                    expect=_expect, cache_ttl=7 * 86400, timeout=45, verbose=verbose)
    else:
        url = ENDPOINT
        res = fetch(ENDPOINT, method="POST", data="query=" + _pct(q),
                    headers={"Content-Type": "application/x-www-form-urlencoded",
                             "Accept": "application/sparql-results+json"},
                    expect=_expect, cache_ttl=7 * 86400, timeout=45, verbose=verbose)
    out = {"query": {"postcode": pc, "postcode_as_given": postcode, "since": since, "paon": paon},
           "source_url": url, "http_method": method.upper(),
           "http_status": res["status"], "ok": res["ok"], "note": _note(res),
           "retrieved_at": res["retrieved_at"], "evidence_class": "G",
           "sparql": q}
    if not res["ok"]:
        return out
    rows = parse_results(res["body"])
    out["transactions"] = rows
    out.update(summarise(rows, paon=paon))
    if not rows:
        out["not_found"] = {"query": pc, "endpoint": ENDPOINT,
                            "meaning": ("no Price Paid rows for this postcode. Common causes: the "
                                        "block is build-to-rent and has never been sold flat by "
                                        "flat; the postcode was issued after the sales; or the "
                                        "postcode is spaced differently in the register.")}
    out["coverage_note"] = ("Price Paid Data is sales lodged for registration in England and Wales. "
                            "It excludes lettings, transfers that were not sales, and most "
                            "commercial transactions. It does not name the owner.")
    return out


def _expect(b):
    t = b.lstrip()
    return t.startswith("{") and '"bindings"' in b


def title_help():
    return {
        "source": "HM Land Registry - title register / title plan",
        "source_url": TITLE_GUIDE,
        "service_url": TITLE_SERVICE,
        "access": "manual",
        "ok": True,
        "http_status": None,
        "retrieved_at": now_iso(),
        "evidence_class": "U",
        "note": ("No fetch. search-property-information.service.gov.uk serves a Cloudflare "
                 "interactive challenge (its robots.txt is challenged too), requires a GOV.UK "
                 "One Login sign-in, and charges GBP 7 per title register (GBP 11 per filed "
                 "document). Three barriers stack; this is a human step, never automate it."),
        "cost": {"title_register": "GBP 7", "title_plan": "GBP 7", "filed_document": "GBP 11"},
        "manual_instructions": [
            "Open %s and follow 'Search for property information'." % TITLE_GUIDE,
            "Sign in with GOV.UK One Login (or create one), search the address, and buy the "
            "title register for the flat. It arrives as a PDF within minutes.",
            "Do not buy the title plan unless you need the boundary; the register carries the "
            "text you want.",
        ],
        "paste_back_fields": [
            "proprietor name(s) - the registered owner(s); compare against the name on the "
            "tenancy agreement and against Companies House",
            "title number - e.g. TGL123456",
            "tenure - freehold or leasehold",
            "date of registration - when the current proprietor was registered",
            "lease term and start date, if leasehold - the unexpired term",
            "restrictions and charges - a lender's restriction, or a restriction requiring a "
            "third party's consent to a letting",
            "any rentcharge or estate rentcharge",
        ],
        "why": ("Price Paid tells you what a flat sold for; only the title register tells you who "
                "owns it now, on what tenure, and what the lease and the lender restrict."),
    }


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

    p = sub.add_parser("price-paid", parents=[common], help="Price Paid transactions for a postcode")
    p.add_argument("--postcode", required=True)
    p.add_argument("--since", type=int, help="only transactions from this year onward")
    p.add_argument("--paon", help="building name or number, for same_building_matches")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--method", choices=["post", "get"], default="post")

    p = sub.add_parser("title", parents=[common], help="how to buy a title register (manual, no fetch)")
    p.add_argument("--help-only", action="store_true",
                   help="print the manual route (this is the only mode)")

    a = ap.parse_args()
    a.verbose = getattr(a, "verbose", False)
    try:
        if a.cmd == "price-paid":
            out = price_paid(a.postcode, since=a.since, paon=a.paon, limit=a.limit,
                             method=a.method, verbose=a.verbose)
        else:
            out = title_help()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("landregistry.py: %s" % e, file=sys.stderr)
        sys.exit(1)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not out.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
