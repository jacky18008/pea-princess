#!/usr/bin/env python3
"""Pure TfL comparison audit over saved ``commute.py journey`` JSON receipts.

The audit checks the query basis and every returned plan before a human ranks
homes. It does not fetch routes, infer a person's actual door, or prove that a
draft contains no other unsupported prose. A host may call the CLI before
accepting a reply; a third-party model is not forced to run it before sending.
"""

import argparse
import datetime
import json
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse

EXPECTED_MODE_FILTERS = {
    "all": None,
    "rail": "tube,dlr,overground,elizabeth-line,national-rail,walking",
    "bus": "bus,walking",
}


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _stamp(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _endpoint(route):
    if route.get("actual_endpoint"):
        return route["actual_endpoint"]
    legs = route.get("legs") or []
    return legs[-1].get("to") if legs else None


def _source_basis(url):
    """Return the path/query basis of a TfL journey URL, or None."""
    if not url:
        return None
    parsed = urlparse(url)
    match = re.search(r"/Journey/JourneyResults/(.*?)/to/([^/]+)$", parsed.path)
    if not match:
        return None
    args = parse_qs(parsed.query)
    return {"from": unquote(match.group(1)), "to": unquote(match.group(2)),
            "date": (args.get("date") or [None])[0],
            "time": (args.get("time") or [None])[0],
            "time_is": (args.get("timeIs") or [None])[0],
            "mode": (args.get("mode") or [None])[0]}


def _arrival_buffer(arrival, query):
    arrived = _stamp(arrival)
    if not arrived:
        return None
    try:
        day = datetime.datetime.strptime(str(query["date"]), "%Y%m%d").date()
        hour, minute = [int(n) for n in query["arrive_by"].split(":")]
        deadline = datetime.datetime.combine(day, datetime.time(hour, minute))
        if arrived.tzinfo:
            deadline = deadline.replace(tzinfo=arrived.tzinfo)
    except (KeyError, TypeError, ValueError):
        return None
    return int((deadline - arrived).total_seconds() // 60)


def _finding(code, detail, severity="review", candidate=None, mode=None):
    return {"code": code, "severity": severity, "candidate": candidate,
            "mode": mode, "detail": detail}


def _draft_claims(draft, labels):
    """Detect only explicit, bounded arrival generalizations; no semantic pass."""
    if not draft:
        return []
    claims = []
    for sentence in re.split(r"[。！？\n]+", draft):
        s = re.sub(r"\s+", " ", sentence).strip()
        if not s:
            continue
        for label in labels:
            cue = r"(?<![A-Za-z])" + re.escape(label) + r"(?![A-Za-z])"
            if not re.search(cue, s, re.I):
                continue
            if re.search(r"(?:只有|唯有|only)\s*" + cue +
                         r".{0,65}(?:緩衝|餘裕|提早|buffer|early)", s, re.I):
                claims.append({"kind": "exclusive_buffer", "candidate": label,
                               "excerpt": s[:180]})
            if re.search(cue + r".{0,110}(?:幾乎貼著\s*9:00|9:00\s*前較緊|幾乎.*9:00|"
                         r"只剩\s*[0-5]\s*分鐘|almost\s*(?:late|9:00|09:00)|"
                         r"nearly\s*(?:late|9:00|09:00))", s, re.I):
                claims.append({"kind": "near_deadline", "candidate": label,
                               "excerpt": s[:180]})
            if re.search(cue + r".{0,65}(?:到站較早|arrives? earlier)", s, re.I):
                claims.append({"kind": "earlier_arrival", "candidate": label,
                               "excerpt": s[:180]})
    return claims


def audit_commute_comparison(receipts, target_endpoint, draft=None,
                             origin_descriptions=None, near_buffer_min=5):
    """Audit candidate receipts without I/O; preserve failures as unknowns.

    ``target_endpoint`` is the human-chosen named destination, e.g. London
    Bridge Rail Station, because a TfL stop ID can still yield a different
    station in a returned journey. ``origin_descriptions`` records whether a
    postcode, street midpoint or exact door was used; it is never inferred.
    """
    if not isinstance(receipts, dict) or not receipts or not target_endpoint:
        raise ValueError("candidate receipts and a named target endpoint are required")
    origin_descriptions = origin_descriptions or {}
    findings, candidates = [], {}
    shared_basis = None
    for label, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise ValueError("%s receipt must be a JSON object" % label)
        query = receipt.get("query") or {}
        basis = {k: query.get(k) for k in ("to", "to_kind", "date", "arrive_by",
                                             "door_buffer_min")}
        basis_ok = True
        if shared_basis is None:
            shared_basis = basis
        elif basis != shared_basis:
            basis_ok = False
            findings.append(_finding("comparison_basis_mismatch",
                "%s has a different destination/date/arrival/door-buffer basis" % label,
                "correction", label))
        origin = {"value": query.get("from"), "kind": query.get("from_kind"),
                  "description": origin_descriptions.get(label)}
        if not origin["description"]:
            findings.append(_finding("origin_precision_unstated",
                "%s origin is %s; state whether it represents a postcode, street sample or door" %
                (label, origin["kind"] or "unknown"), candidate=label))
        rows = []
        listed = query.get("plans") or []
        present = list((receipt.get("plans") or {}).keys())
        requested = list(dict.fromkeys(listed + present))
        for extra in present:
            if listed and extra not in listed:
                findings.append(_finding("unlisted_plan_mode",
                    "%s %s plan exists in the receipt but not its query plan list" %
                    (label, extra), candidate=label, mode=extra))
        for mode in requested:
            plan = (receipt.get("plans") or {}).get(mode)
            if not isinstance(plan, dict):
                rows.append({"mode": mode, "status": "unknown", "note": "no plan receipt"})
                findings.append(_finding("missing_plan_receipt",
                    "%s %s plan receipt is missing" % (label, mode), candidate=label, mode=mode))
                continue
            source = _source_basis(plan.get("source_url"))
            expected_time = str(query.get("arrive_by") or "").replace(":", "")
            source_ok = bool(source) and not (_norm(source["from"]) != _norm(query.get("from")) or
                              _norm(source["to"]) != _norm(query.get("to")) or
                              source["date"] != query.get("date") or
                              source["time"] != expected_time or
                              source["time_is"] != "Arriving")
            if not source_ok:
                findings.append(_finding("source_query_mismatch",
                    "%s %s source URL does not match its retained query basis" % (label, mode),
                    "correction", label, mode))
            elif ((mode in EXPECTED_MODE_FILTERS and
                   source["mode"] != EXPECTED_MODE_FILTERS[mode]) or
                  (plan.get("mode_filter") and mode != "all" and
                   source["mode"] != plan["mode_filter"])):
                source_ok = False
                findings.append(_finding("source_mode_mismatch",
                    "%s %s plan source URL does not match its mode label/filter" % (label, mode),
                    "correction", label, mode))
            if not plan.get("ok"):
                rows.append({"mode": mode, "status": "unknown", "note": plan.get("note"),
                             "http_status": plan.get("http_status")})
                continue
            alternatives = plan.get("alternatives")
            routes = [r for r in alternatives if isinstance(r, dict)] if isinstance(alternatives, list) else []
            primary_key = (plan.get("duration_min"), plan.get("start"),
                           plan.get("arrival"), _norm(_endpoint(plan)))
            if not any((r.get("duration_min"), r.get("start"), r.get("arrival"),
                        _norm(_endpoint(r))) == primary_key for r in routes):
                routes.insert(0, plan)
            for index, route in enumerate(routes):
                actual = _endpoint(route)
                buffer_min = _arrival_buffer(route.get("arrival"), query)
                route_date = (_stamp(route.get("arrival")) or datetime.datetime.min).date()
                expected_date = str(query.get("date") or "")
                if not basis_ok or not source_ok:
                    status = "incomparable"
                elif actual is None or buffer_min is None:
                    status = "unknown"
                    findings.append(_finding("route_endpoint_or_arrival_unknown",
                        "%s %s route %d lacks a verifiable endpoint or arrival" %
                        (label, mode, index), candidate=label, mode=mode))
                elif route_date.strftime("%Y%m%d") != expected_date:
                    status = "incomparable"
                    findings.append(_finding("route_date_mismatch",
                        "%s %s route %d arrives on a different date" %
                        (label, mode, index), "correction", label, mode))
                elif _norm(actual) != _norm(target_endpoint):
                    status = "other_endpoint"
                    findings.append(_finding("unexpected_endpoint",
                        "%s %s route %d ends at %s, not %s" %
                        (label, mode, index, actual, target_endpoint), candidate=label, mode=mode))
                else:
                    status = "target_endpoint"
                rows.append({"mode": mode, "route_index": index, "status": status,
                             "actual_endpoint": actual, "duration_min": route.get("duration_min"),
                             "start": route.get("start"), "arrival": route.get("arrival"),
                             "buffer_min": buffer_min, "modes": route.get("modes") or [],
                             "zero_wait_joins": route.get("zero_wait_joins"),
                             "http_status": plan.get("http_status")})
        valid = [r for r in rows if r.get("status") == "target_endpoint"]
        durations = [r["duration_min"] for r in valid if isinstance(r.get("duration_min"), (int, float))]
        buffers = [r["buffer_min"] for r in valid if isinstance(r.get("buffer_min"), int)]
        candidates[label] = {"query": basis, "origin": origin, "plans": rows,
                             "target_routes": len(valid),
                             "shortest_target_duration_min": min(durations) if durations else None,
                             "largest_target_buffer_min": max(buffers) if buffers else None}
        if not valid:
            findings.append(_finding("no_verified_target_route",
                "%s has no successful route confirmed to reach %s; this is unknown, not a commute failure" %
                (label, target_endpoint), candidate=label))
    kinds = {c["origin"]["kind"] for c in candidates.values()}
    if len(kinds) > 1:
        findings.append(_finding("origin_precision_differs",
            "Candidates use different origin kinds; retain each sample point in the comparison"))
    for claim in _draft_claims(draft, candidates):
        label = claim["candidate"]
        own = candidates[label]["largest_target_buffer_min"]
        others = [c["largest_target_buffer_min"] for k, c in candidates.items()
                  if k != label and c["largest_target_buffer_min"] is not None]
        unsupported = ((claim["kind"] == "exclusive_buffer" and any(v > 0 for v in others)) or
                       (claim["kind"] == "near_deadline" and own is not None and
                        own > near_buffer_min) or
                       (claim["kind"] == "earlier_arrival" and own is not None and
                        any(v >= own for v in others)))
        if unsupported:
            findings.append(_finding("unsupported_" + claim["kind"],
                "%s conflicts with successful target-endpoint route buffers: %s" %
                (claim["excerpt"], {k: c["largest_target_buffer_min"]
                                    for k, c in candidates.items()}),
                "correction", label))
    severity = {f["severity"] for f in findings}
    status = "correction_required" if "correction" in severity else (
        "review_required" if findings else "checked_scope_only")
    return {"status": status, "target_endpoint": target_endpoint,
            "shared_query_basis": shared_basis, "candidates": candidates,
            "findings": findings, "near_buffer_min": near_buffer_min,
            "draft_detection_scope":
            "literal arrival-generalization cues only; semantic/source review still required"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", required=True,
                        help="LABEL=path to saved commute.py journey JSON; repeat")
    parser.add_argument("--target-endpoint", required=True,
                        help="the named station the person chose")
    parser.add_argument("--origin", action="append", default=[],
                        help="LABEL=postcode point, street midpoint, or exact door")
    parser.add_argument("--draft", help="optional final-reply draft text file")
    args = parser.parse_args(argv)
    receipts, origins = {}, {}
    for spec in args.candidate:
        label, path = spec.split("=", 1)
        with open(path, encoding="utf-8") as fh:
            receipts[label] = json.load(fh)
    for spec in args.origin:
        label, description = spec.split("=", 1)
        origins[label] = description
    if args.draft:
        with open(args.draft, encoding="utf-8") as fh:
            draft = fh.read()
    else:
        draft = None
    result = audit_commute_comparison(receipts, args.target_endpoint, draft, origins)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 2 if result["status"] == "correction_required" else 0


if __name__ == "__main__":
    sys.exit(main())
