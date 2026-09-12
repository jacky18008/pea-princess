#!/usr/bin/env python3
"""GLA Planning London Datahub — open guest Elasticsearch, all 33 London LPAs.

Source: https://planningdata.london.gov.uk/api-guest/applications/_search
Official? Yes — the Greater London Authority's own aggregation of the planning
registers of every London planning authority. Open guest account, NO key, NO
login, NO fee. The host serves no robots.txt (404), so nothing is disallowed.
Both POST and the GET `?source=<json>&source_content_type=application/json`
form work; this tool uses POST.

WHAT THE INDEX ACTUALLY EXPOSES (probed 2026-09-03; `_mapping` is 403 for the
guest role `api_read_only`, so the shape below was read off `_search` samples
and confirmed field-by-field with `exists`/`terms` probes):

  documents          1,280,679  (default `hits.total` caps at 10000 —
                                 send "track_total_hits": true for a real count)
  _id / id           "Islington-P2025_0271_FUL"   (keyword; `term` works)
  GEO
    centroid                geo_point  {lat, lon}  — present on 100 % of docs.
                            `geo_distance` filter and `_geo_distance` sort both
                            work. THIS IS THE FILTER THIS TOOL USES.
    centroid_easting/       integer OSGB36 National Grid metres — 94 % of docs,
    centroid_northing       and never present when `centroid` is absent, so they
                            add no coverage. Used only by the --bbox fallback.
    wgs84_polygon           geo_shape (83 % of docs); `geo_shape` circle queries
                            work but are slower and miss the other 17 %.
    polygon                 usually null (OSGB WKT when present).
    postcode, borough, ward — ward is the only keyword-typed one of the three.
  IDENTITY / TEXT (all `text`, NO `.keyword` sub-field — aggregations on them
  fail, so filter with match_phrase, not term):
    lpa_app_no, lpa_name, borough, postcode, site_name, site_number,
    street_name, secondary_street_name, locality, description,
    application_type, application_type_full, status, decision, bo_system
  KEYWORD (aggregatable / term-filterable): development_type, ward, id
  DATES: valid_date, decision_date, decision_target_date, lapsed_date,
    actual_commencement_date, actual_completion_date, appeal_start_date,
    appeal_decision_date, last_updated, last_synced.  The date fields use the
    format dd/MM/yyyy — a range query MUST pass "format": "dd/MM/yyyy" or the
    server throws parse_exception on an ISO bound.
  DECISION DETAIL: decision, decision_agency, appeal_status, appeal_decision,
    cil_liability, and — surprisingly — `decision_conditions`, a string array of
    the full condition text, populated on 670,027 docs (52 %). See `stages`.
  application_details.* (per-scheme, only on the fuller records):
    building_details        NESTED array [{no_storeys, building_ref}] — a plain
                            `exists` on the dotted path returns 0; it needs a
                            {"nested": {"path": "application_details.
                            building_details", ...}} query. 79,243 docs carry a
                            no_storeys value; 3,689 of those are >= 8 storeys.
    residential_details.total_no_proposed_residential_units (and _existing_,
                            plus a tenure breakdown and residential_units[])
    scheme_name, site_area, building_age, building_type, occupation_status,
    projected_cost_of_works, constraints_details, existing_uprns, s106_agreement
  NOT PRESENT: building height in metres (only storey counts), and the
    condition-discharge decision for each individual condition.

Coverage caveat that matters more than any of the above: the Datahub carries
applications as the boroughs report them. Small householder cases may be
absent, and back-catalogues differ by borough. Zero hits is not proof of no
activity — check the borough portal (printed as `portal_url`).

Usage:
  planning.py near --lat 51.5045 --lng -0.0865 [--radius 250] [--since 2018] [--limit 200]
  planning.py near --lat 51.5045 --lng -0.0865 --bbox      # OSGB easting/northing fallback
  planning.py search --text "Emery Wharf" [--lpa "Tower Hamlets"] [--since 2015] [--limit 50]
  planning.py stages --reference "26/AP/0812" --lpa Southwark
  planning.py planit --postcode "E1W 2SF" [--km 0.3] [--limit 20]
All commands print one JSON object. Records carry source_url, http_status, ok,
note, retrieved_at and evidence_class "G" (official register aggregation);
the PlanIt fallback is evidence_class "C" (third-party mirror).
"""
import argparse
import json
import math
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import post_json, fetch  # noqa: E402

ES_URL = "https://planningdata.london.gov.uk/api-guest/applications/_search"
PLANIT_URL = "https://www.planit.org.uk/api/applics/json"
BOROUGHS_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "references", "boroughs.yaml")
DESC_CHARS = 300

SOURCE_FIELDS = [
    "id", "lpa_app_no", "lpa_name", "borough", "ward", "postcode",
    "site_name", "site_number", "street_name", "secondary_street_name", "locality",
    "description", "application_type", "application_type_full", "development_type",
    "status", "decision", "decision_date", "valid_date", "decision_target_date",
    "lapsed_date", "actual_commencement_date", "actual_completion_date",
    "appeal_status", "appeal_decision", "url_planning_app",
    "centroid", "centroid_easting", "centroid_northing",
    "application_details.scheme_name",
    "application_details.building_details",
    "application_details.residential_details.total_no_proposed_residential_units",
    "application_details.residential_details.total_no_existing_residential_units",
]

DATAHUB_CAVEAT = ("the Datahub carries applications reported by boroughs; small householder "
                  "cases may be absent; zero hits is not proof of no activity")


# ------------------------------------------------------------- geodesy ------
def _haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def centroid_of(src):
    """(lat, lng) from the `centroid` geo_point, whatever shape it arrives in.

    Elasticsearch accepts a geo_point as {lat, lon}, as the string "lat,lon" and
    as the array [lon, lat]; the Datahub emits mostly dicts but not only, and
    numbers sometimes arrive as strings.
    """
    c = src.get("centroid")
    if isinstance(c, dict):
        return _num(c.get("lat")), _num(c.get("lon"))
    if isinstance(c, str) and "," in c:
        a, b = c.split(",", 1)
        return _num(a), _num(b)
    if isinstance(c, (list, tuple)) and len(c) == 2:
        return _num(c[1]), _num(c[0])            # GeoJSON order
    return None, None


def wgs84_to_osgb36(lat, lon, height=0.0):
    """WGS84 lat/lon -> OSGB36 National Grid easting/northing, in pure Python.

    Helmert 7-parameter datum shift (WGS84 -> OSGB36) followed by the Airy 1830
    Transverse Mercator projection of the National Grid. This is the standard
    "small Helmert" route, NOT the OSTN15 grid-shift file that Ordnance Survey
    publishes as the definitive transformation.

    ACCURACY, measured: the projection half is exact — it reproduces the OS
    worked example (Annexe C of "A guide to coordinate systems in Great
    Britain": OSGB36 52 39 27.2531 N, 1 43 04.5177 E -> E 651409.903,
    N 313177.270) to under a millimetre. The datum-shift half is the lossy part:
    the Helmert route lands about 5 m from the OSTN15 answer in central London
    (WGS84 51.5074, -0.1278 -> this function gives 530029/180380 where OSTN15
    gives 530034/180381) and is quoted as within ~5 m anywhere in Great Britain.
    Ellipsoidal height barely matters (0 vs 60 m moves the result by ~1 cm), so
    it defaults to 0. Five metres is far finer than any radius this tool
    searches on, but do not use these numbers to identify a plot boundary.
    Returns (easting, northing) rounded to whole metres.
    """
    # WGS84 ellipsoid -> geocentric cartesian
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    phi, lam = math.radians(lat), math.radians(lon)
    nu = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    x = (nu + height) * math.cos(phi) * math.cos(lam)
    y = (nu + height) * math.cos(phi) * math.sin(lam)
    z = ((1 - e2) * nu + height) * math.sin(phi)
    # Helmert: WGS84 -> OSGB36
    tx, ty, tz = -446.448, 125.157, -542.060                      # metres
    s = 20.4894e-6                                                # scale
    rx, ry, rz = (math.radians(v / 3600.0) for v in (-0.1502, -0.2470, -0.8421))
    x2 = tx + x * (1 + s) - y * rz + z * ry
    y2 = ty + x * rz + y * (1 + s) - z * rx
    z2 = tz - x * ry + y * rx + z * (1 + s)
    # cartesian -> Airy 1830 geodetic
    a2, b2 = 6377563.396, 6356256.909
    e2b = (a2 * a2 - b2 * b2) / (a2 * a2)
    p = math.sqrt(x2 * x2 + y2 * y2)
    phi2, nu2 = math.atan2(z2, p * (1 - e2b)), 0.0
    for _ in range(12):
        nu2 = a2 / math.sqrt(1 - e2b * math.sin(phi2) ** 2)
        phi2 = math.atan2(z2 + e2b * nu2 * math.sin(phi2), p)
    lam2 = math.atan2(y2, x2)
    # Airy 1830 -> National Grid (Transverse Mercator)
    f0, phi0, lam0, e0, n0 = 0.9996012717, math.radians(49), math.radians(-2), 400000.0, -100000.0
    n = (a2 - b2) / (a2 + b2)
    rho = a2 * f0 * (1 - e2b) * (1 - e2b * math.sin(phi2) ** 2) ** -1.5
    eta2 = nu2 * f0 / rho - 1
    nu2f = nu2 * f0
    dphi, sphi = phi2 - phi0, phi2 + phi0
    m = b2 * f0 * (
        (1 + n + 1.25 * n ** 2 + 1.25 * n ** 3) * dphi
        - (3 * n + 3 * n ** 2 + 2.625 * n ** 3) * math.sin(dphi) * math.cos(sphi)
        + (1.875 * n ** 2 + 1.875 * n ** 3) * math.sin(2 * dphi) * math.cos(2 * sphi)
        - (35.0 / 24.0) * n ** 3 * math.sin(3 * dphi) * math.cos(3 * sphi))
    sp, cp, tp = math.sin(phi2), math.cos(phi2), math.tan(phi2)
    i = m + n0
    ii = nu2f / 2 * sp * cp
    iii = nu2f / 24 * sp * cp ** 3 * (5 - tp ** 2 + 9 * eta2)
    iiia = nu2f / 720 * sp * cp ** 5 * (61 - 58 * tp ** 2 + tp ** 4)
    iv = nu2f * cp
    v = nu2f / 6 * cp ** 3 * (nu2 * f0 / rho - tp ** 2)
    vi = nu2f / 120 * cp ** 5 * (5 - 18 * tp ** 2 + tp ** 4 + 14 * eta2 - 58 * tp ** 2 * eta2)
    dl = lam2 - lam0
    northing = i + ii * dl ** 2 + iii * dl ** 4 + iiia * dl ** 6
    easting = e0 + iv * dl + v * dl ** 3 + vi * dl ** 5
    return int(round(easting)), int(round(northing))


# --------------------------------------------------- borough portal map -----
_PORTALS = None


def borough_portals(path=None):
    """{normalised borough name: planning portal root} read out of boroughs.yaml.

    Deliberately a line scanner, not a YAML parser: the repo is stdlib-only and
    only two keys are needed. Shape relied on:
        `  - name: "X"` then `    planning_search:` then `      url: "..."`.
    """
    global _PORTALS
    if _PORTALS is not None and path is None:
        return _PORTALS
    out = {}
    name, in_planning = None, False
    try:
        fh = open(path or BOROUGHS_YAML, encoding="utf-8")
    except IOError:
        return {}
    with fh:
        for line in fh:
            m = re.match(r'^  - name:\s*"?([^"\n]+?)"?\s*$', line)
            if m:
                name, in_planning = m.group(1), False
                continue
            if re.match(r'^    \S', line):
                in_planning = line.strip().startswith("planning_search:")
                continue
            if in_planning and name:
                m = re.match(r'^      url:\s*"?([^"\n]+?)"?\s*$', line)
                if m and m.group(1) != "null":
                    out[_norm_borough(name)] = {"borough": name, "portal_url": m.group(1)}
                    in_planning = False
    if path is None:
        _PORTALS = out
    return out


def _norm_borough(s):
    s = (s or "").lower().replace("&", "and")
    s = re.sub(r"\b(london borough of|royal borough of|lb|the)\b", " ", s)
    s = re.sub(r"\b(council|custodian code)\b", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s == "city of westminster":
        s = "westminster"
    return s


MDC_NOTE = ("Mayoral Development Corporation, not a borough: it is not in boroughs.yaml. "
            "Look the case up on the host borough's portal.")


def portal_for(lpa_name):
    """-> (portal_url or None, note or None)."""
    if not lpa_name:
        return None, None
    key = _norm_borough(lpa_name)
    if key in ("lldc", "opdc"):
        return None, lpa_name.upper() + ": " + MDC_NOTE
    table = borough_portals()
    if key in table:
        return table[key]["portal_url"], None
    for k, v in table.items():                       # "kingston" -> "kingston upon thames"
        if k.startswith(key) or key.startswith(k):
            return v["portal_url"], None
    return None, "no portal URL for LPA '%s' in boroughs.yaml" % lpa_name


# ----------------------------------------------------- query builders -------
def geo_filter(lat, lng, radius_m, bbox=False):
    """The Elasticsearch clause that restricts to `radius_m` around a point.

    Default: a `geo_distance` filter on `centroid` (a real geo_point, present on
    every document). With bbox=True: a pair of `range` clauses on the OSGB36
    `centroid_easting`/`centroid_northing` integers, using the pure-Python
    WGS84->OSGB36 conversion. The bbox is a SQUARE, so it over-selects the
    corners by up to sqrt(2)x the radius; callers re-filter on the true distance.
    """
    if not bbox:
        return {"geo_distance": {"distance": "%dm" % int(radius_m),
                                 "centroid": {"lat": lat, "lon": lng}}}
    e, n = wgs84_to_osgb36(lat, lng)
    r = int(radius_m)
    return {"bool": {"filter": [
        {"range": {"centroid_easting": {"gte": e - r, "lte": e + r}}},
        {"range": {"centroid_northing": {"gte": n - r, "lte": n + r}}}]}}


def since_filter(year):
    """Applications valid or decided on/after 1 January `year` (dd/MM/yyyy fields)."""
    if not year:
        return None
    bound = "01/01/%d" % int(year)
    return {"bool": {"minimum_should_match": 1, "should": [
        {"range": {"valid_date": {"gte": bound, "format": "dd/MM/yyyy"}}},
        {"range": {"decision_date": {"gte": bound, "format": "dd/MM/yyyy"}}}]}}


# ------------------------------------------------- tall-building hint -------
_WORD_NUM = {"eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
             "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
             "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
             "twenty-five": 25, "thirty": 30, "forty": 40, "fifty": 50}
_STOREY_RE = re.compile(r"(\d{1,3})\s*[-– ]?\s*stor(?:e?y|ies|eys)", re.I)
# "part 26 and part 16 storeys" — a very common London phrasing where only the
# last number sits next to the word.
_PART_STOREY_RE = re.compile(r"\bpart\s+(\d{1,3})\b(?=[^.;]{0,60}?stor(?:e?y|ies|eys))", re.I)
_WORDSTOREY_RE = re.compile(r"\b(%s)\s*[-– ]?\s*stor(?:e?y|ies|eys)" % "|".join(_WORD_NUM), re.I)
_TALL_RE = re.compile(r"\btall building\b", re.I)
_TOWER_RE = re.compile(r"\btowers?\b", re.I)
# place names and plant that are not evidence of a tall building
_TOWER_FALSE = re.compile(r"\btowers?\s+(?:hamlets|bridge|hill|gateway|of london)\b|"
                          r"\b(?:cooling|water|clock|bell|church|pylon|telecom|scaffold)"
                          r"\s+towers?\b", re.I)
STOREY_THRESHOLD = 8
UNITS_THRESHOLD = 100


def storeys_in_text(text):
    """Largest storey count stated in free text, or None."""
    vals = [int(m) for m in _STOREY_RE.findall(text or "")]
    vals += [int(m) for m in _PART_STOREY_RE.findall(text or "")]
    vals += [_WORD_NUM[w.lower()] for w in _WORDSTOREY_RE.findall(text or "")]
    return max(vals) if vals else None


def tall_building_hint(description, storeys=None, units=None, extra_text=""):
    """(hint: bool, reasons: [str]) — cheap screen for 'is this a big scheme?'.

    True when the record states >= 8 storeys, >= 100 residential units, or the
    words "tall building"/"tower" (minus the London place names that contain
    "Tower"). It is a HINT: it reads self-reported text, not a drawing.
    """
    reasons = []
    text = " ".join(x for x in (description, extra_text) if x)
    text_storeys = storeys_in_text(text)
    best = max([v for v in (storeys, text_storeys) if v is not None] or [None]) \
        if (storeys is not None or text_storeys is not None) else None
    if best is not None and best >= STOREY_THRESHOLD:
        reasons.append("%d storeys" % best)
    if units is not None and units >= UNITS_THRESHOLD:
        reasons.append("%d residential units" % units)
    if _TALL_RE.search(text):
        reasons.append('description says "tall building"')
    if _TOWER_RE.search(_TOWER_FALSE.sub(" ", text)):
        reasons.append('description says "tower"')
    return bool(reasons), reasons


# ---------------------------------------------------------- shaping ---------
def _trim(s, n=DESC_CHARS):
    s = re.sub(r"\s+", " ", s or "").strip()
    if not s:
        return None
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _str(v):
    """Datahub fields are loosely typed: site_number arrives as an int about as
    often as a string, and lists show up in the street fields."""
    if v is None or isinstance(v, bool):
        return ""
    if isinstance(v, (list, tuple)):
        return re.sub(r"\s+", " ", " ".join(_str(x) for x in v)).strip()
    return re.sub(r"\s+", " ", str(v)).strip()


def _address(src):
    ad = src.get("application_details") or {}
    if not isinstance(ad, dict):
        ad = {}
    parts = [_str(src.get("site_name")) or _str(ad.get("scheme_name"))]
    parts.append(" ".join(x for x in [_str(src.get("site_number")),
                                      _str(src.get("street_name"))] if x))
    parts += [_str(src.get("secondary_street_name")), _str(src.get("locality"))]
    seen, out = set(), []
    for part in parts:
        if part and part.lower() not in seen:
            seen.add(part.lower())
            out.append(part)
    return ", ".join(out) or None


def _details(src):
    ad = src.get("application_details")
    return ad if isinstance(ad, dict) else {}


def _storeys(src):
    bd = _details(src).get("building_details") or []
    if isinstance(bd, dict):
        bd = [bd]
    vals = []
    for b in bd:
        if not isinstance(b, dict):
            continue
        v = b.get("no_storeys")
        if isinstance(v, bool) or v is None:
            continue
        n = _num(v)                    # the Datahub sends 17.0 as often as 17
        if n is not None:
            vals.append(int(round(n)))
    return max(vals) if vals else None


def _units(src):
    rd = _details(src).get("residential_details") or {}
    if not isinstance(rd, dict):
        return None
    v = rd.get("total_no_proposed_residential_units")
    if isinstance(v, bool) or v is None:
        return None
    n = _num(v)
    return int(round(n)) if n is not None else None


def rows_from_hits(data, lat, lng, radius=None, bbox=False):
    """Elasticsearch response -> shaped, distance-sorted rows. No network.

    Distance comes from the `_geo_distance` sort value when the query asked for
    one, and is recomputed from `centroid` otherwise (the --bbox path, which has
    no sort). A square bounding box over-selects its corners by up to sqrt(2) x
    the radius, so bbox results are re-filtered on the true distance here.
    """
    rows = []
    for h in ((data or {}).get("hits") or {}).get("hits") or []:
        src = h.get("_source") or {}
        if h.get("sort") and _num(h["sort"][0]) is not None:
            d = int(round(_num(h["sort"][0])))
        else:
            clat, clon = centroid_of(src)
            d = (int(round(_haversine_m(lat, lng, clat, clon)))
                 if clat is not None and clon is not None else None)
        if bbox and radius is not None and d is not None and d > radius:
            continue
        rows.append(shape(src, d))
    rows.sort(key=lambda r: (r["distance_m"] is None, r["distance_m"]))
    return rows


def shape(src, distance_m=None):
    desc = _str(src.get("description")) or None
    storeys, units = _storeys(src), _units(src)
    hint, reasons = tall_building_hint(desc, storeys, units,
                                       extra_text=_str(src.get("site_name")))
    portal, portal_note = portal_for(src.get("lpa_name"))
    return {
        "reference": _str(src.get("lpa_app_no")) or None,
        "lpa_name": _str(src.get("lpa_name")) or None,
        "address": _address(src),
        "postcode": _str(src.get("postcode")) or None,
        "description": _trim(desc),
        "application_type": src.get("application_type"),
        "application_type_full": src.get("application_type_full"),
        "development_type": src.get("development_type"),
        "status": src.get("status") or None,
        "decision": src.get("decision"),
        "decision_date": src.get("decision_date"),
        "valid_date": src.get("valid_date"),
        "distance_m": distance_m,
        "tall_building_hint": hint,
        "tall_building_reasons": reasons,
        "storeys": storeys,
        "residential_units_proposed": units,
        "lat": centroid_of(src)[0],
        "lng": centroid_of(src)[1],
        "portal_url": portal,
        "portal_note": portal_note,
        "datahub_id": src.get("id"),
    }


# ------------------------------------------------------------ transport -----
def es_search(body, verbose=False, cache_ttl=3600):
    res = post_json(ES_URL, body, cache_ttl=cache_ttl, verbose=verbose,
                    expect=lambda b: '"hits"' in b and '"took"' in b)
    data = {}
    if res["body"]:
        try:
            data = json.loads(res["body"])
        except ValueError:
            res["ok"] = False
            res["note"] = res["note"] or "response was not JSON"
    if "error" in data:
        res["ok"] = False
        rc = (data.get("error") or {}).get("root_cause") or [{}]
        res["note"] = "elasticsearch: " + str(rc[0].get("reason"))[:200]
    return res, data


def _envelope(res, query, extra=None):
    out = {
        "source_url": ES_URL, "http_status": res["status"], "ok": res["ok"],
        "note": res["note"], "retrieved_at": res["retrieved_at"], "evidence_class": "G",
        "query_used": query, "caveat": DATAHUB_CAVEAT,
    }
    out.update(extra or {})
    return out


# --------------------------------------------------------------- near -------
def near(lat, lng, radius=250, since=2018, limit=200, bbox=False, verbose=False):
    filters = [geo_filter(lat, lng, radius, bbox=bbox)]
    sf = since_filter(since)
    if sf:
        filters.append(sf)
    body = {"size": int(limit), "track_total_hits": True, "_source": SOURCE_FIELDS,
            "query": {"bool": {"filter": filters}}}
    if not bbox:
        body["sort"] = [{"_geo_distance": {"centroid": {"lat": lat, "lon": lng},
                                           "order": "asc", "unit": "m", "distance_type": "arc"}}]
    res, data = es_search(body, verbose=verbose)
    rows, total = [], None
    if res["ok"]:
        total = ((data.get("hits") or {}).get("total") or {}).get("value")
        rows = rows_from_hits(data, lat, lng, radius=radius, bbox=bbox)
    out = _envelope(res, body, {
        "point": {"lat": lat, "lng": lng}, "radius_m": radius, "since_year": since,
        "geo_filter": "bbox on centroid_easting/centroid_northing (OSGB36, Helmert ~5 m)"
                      if bbox else "geo_distance on centroid (geo_point)",
        "count": len(rows), "total_matching": total, "results": rows,
        "tall_building_rule": "storeys >= %d, or >= %d residential units, or the words "
                              "'tall building'/'tower' in the description"
                              % (STOREY_THRESHOLD, UNITS_THRESHOLD),
    })
    if res["ok"] and not rows:
        out["not_found"] = {"what": "planning applications within %d m of %s,%s%s"
                                    % (radius, lat, lng, " since %s" % since if since else ""),
                            "query": body, "meaning": DATAHUB_CAVEAT}
    return out


# ------------------------------------------------------------- search -------
def search(text, lpa=None, since=None, limit=50, verbose=False):
    must = [{"multi_match": {
        "query": text, "type": "best_fields", "operator": "and",
        "fields": ["site_name^3", "application_details.scheme_name^3",
                   "street_name^2", "secondary_street_name", "locality",
                   "description", "postcode^2"]}}]
    filters = []
    if lpa:
        filters.append({"match_phrase": {"lpa_name": lpa}})
    sf = since_filter(since)
    if sf:
        filters.append(sf)
    body = {"size": int(limit), "track_total_hits": True, "_source": SOURCE_FIELDS,
            "query": {"bool": {"must": must, "filter": filters}}}
    res, data = es_search(body, verbose=verbose)
    rows, total = [], None
    if res["ok"]:
        total = ((data.get("hits") or {}).get("total") or {}).get("value")
        rows = [shape(h.get("_source") or {}) for h in (data.get("hits") or {}).get("hits") or []]
    out = _envelope(res, body, {
        "text": text, "lpa": lpa, "since_year": since,
        "count": len(rows), "total_matching": total, "results": rows,
    })
    if res["ok"] and not rows:
        out["not_found"] = {
            "what": "applications matching %r%s" % (text, " in %s" % lpa if lpa else ""),
            "query": body,
            "meaning": DATAHUB_CAVEAT + "; also note the free-text fields are site_name, "
                       "street_name and description — a marketing name a developer never "
                       "put on the application will not match. Try the street name.",
        }
    return out


# ------------------------------------------------------------- stages -------
STATUS_PLAIN = {
    "approved": "application recorded as approved",
    "refused": "refused",
    "withdrawn": "record marked withdrawn; decision history needs checking",
    "superseded": "record marked superseded; check the replacement record",
    "lapsed": "record marked lapsed; current permission validity needs checking",
    "completed": "record marked completed; this alone does not establish physical completion",
    "application received": "just submitted, not yet assessed",
    "application under consideration": "being assessed; no decision timing established",
    "closed": "record marked closed; decision history needs checking",
    "not required": "the council decided no permission was needed",
    "dismissed": "an appeal against refusal failed",
    "unknown": "the borough did not report a status",
}
COND_RE = re.compile(r"approval of details|reserved by condition|discharge of condition|"
                     r"\bAOD\b|condition[s]? \d", re.I)
DETAILS_RE = re.compile(r"\b(?:approval of details|discharge of conditions?|condition discharge|AOD)\b", re.I)
DETAILS_OPEN_RE = re.compile(r"^(?:(?:application|submission|request) for )?"
                             r"(?:approval of details|discharge of conditions?|condition discharge|AOD)\b", re.I)
VARIATION_RE = re.compile(r"\b(?:variation|removal|vary|remove)\b[^.;]{0,60}\bconditions?\b", re.I)
STATUS_ALIASES = {
    "under consideration": "application under consideration",
    "pending": "application under consideration",
    "pending decision": "application under consideration",
    "received": "application received",
    "approve": "approved",
    "approved with conditions": "approved",
    "granted": "approved",
    "refuse": "refused",
    "refused permission": "refused",
}
PRECOMMENCE_RE = re.compile(r"pre[- ]?commencement|prior to (?:the )?commencement|"
                            r"before (?:any )?(?:works|development) (?:begin|commence)|"
                            r"demolition|site set[- ]?up|construction (?:management|logistics)|"
                            r"piling|hoarding", re.I)
PREOCCUPY_RE = re.compile(r"pre[- ]?occupation|prior to (?:first )?occupation|"
                          r"before (?:the )?(?:first )?occupation|landscaping|"
                          r"external lighting|travel plan|refuse (?:store|storage)", re.I)


def _year_of(d):
    m = re.search(r"(\d{4})", d or "")
    return int(m.group(1)) if m else None


def _as_date(d):
    """dd/MM/yyyy -> datetime.date, or None. The Datahub uses no other format."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", d or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def explain(rec, src):
    """Plain-English 'what does this mean for someone about to sign a tenancy'."""
    lines = []
    status_raw, decision_raw = _str(rec.get("status")), _str(rec.get("decision"))
    status = STATUS_ALIASES.get(status_raw.lower(), status_raw.lower())
    dec = STATUS_ALIASES.get(decision_raw.lower(), decision_raw.lower())
    # Unknown labels remain unknown; do not turn every string beginning "approv" into a grant.
    display_status = status or dec
    plain = STATUS_PLAIN.get(display_status)
    if plain:
        lines.append("Status %s = %s." % (rec.get("status") or rec.get("decision"), plain))
    description = _str(src.get("description") or rec.get("description"))
    types = " ".join(_str(rec.get(key)) for key in
                     ("application_type", "application_type_full", "development_type"))
    blob = " ".join((description, types))
    details = bool(DETAILS_RE.search(types) or DETAILS_OPEN_RE.search(description))
    # Varying/removing a condition or merely mentioning one does not identify an AOD case.
    details = details and not bool(VARIATION_RE.search(blob))
    condition = details or bool(COND_RE.search(blob) or VARIATION_RE.search(blob))
    states = {status, dec}
    approved = "approved" in states
    pending = {"application received", "application under consideration"}
    conflicting = (states == {"approved", "refused"} or
                   bool(states & pending and states & {"approved", "refused"}))
    started = _str(src.get("actual_commencement_date")) or None
    finished = _str(src.get("actual_completion_date")) or None
    lapse = _str(src.get("lapsed_date")) or None
    if conflicting:
        lines.append("The register's status and decision fields conflict; approval and current works "
                     "are not established. Check the original decision record.")
    elif approved and details:
        lines.append("Approval relates to submitted condition details, not a new general planning "
                     "permission or proof of work starting.")
    elif approved:
        lines.append("Approval is recorded; permission alone does not establish when works start "
                     "or whether construction is happening now.")
    if started:
        lines.append("The register records commencement on %s; current on-site activity is not verified." % started)
    elif approved and not conflicting:
        lines.append("No commencement date is recorded; the actual start date remains unknown.")
    if finished:
        lines.append("The register records completion on %s; this does not rule out other or later works." % finished)
    if lapse:
        lines.append("The register lists a lapse date of %s; verify the original permission and "
                     "its conditions before interpreting validity or a construction deadline." % lapse)
    # Never manufacture an expiry from decision-year + 3, including condition-only records.
    if src.get("appeal_status") or src.get("appeal_decision"):
        lines.append("An appeal is recorded (status %s, decision %s); inspect its actual outcome "
                     "before interpreting permission." % (src.get("appeal_status"), src.get("appeal_decision")))
    if details:
        pre, post = bool(PRECOMMENCE_RE.search(blob)), bool(PREOCCUPY_RE.search(blob))
        lines.append("This concerns condition details. A pre-commencement or pre-occupation condition "
                     "describes a required stage, not evidence that work is starting or finishing now." +
                     (" The text concerns pre-commencement matters." if pre and not post else
                      " The text concerns pre-occupation matters." if post and not pre else
                      " Its precise stage needs checking in the original condition."))
    elif condition:
        lines.append("The record mentions planning conditions; this alone does not identify a "
                     "condition-discharge application or establish permission scope or current works. "
                     "Check the application type and original decision.")
    if rec.get("tall_building_hint"):
        lines.append("Screened as a big scheme (%s) — investigate construction duration and possible changes "
                     "to daylight and views." % "; ".join(rec.get("tall_building_reasons") or []))
    return lines


def stages(reference, lpa=None, verbose=False):
    filters = [{"match_phrase": {"lpa_app_no": reference}}]
    if lpa:
        filters.append({"match_phrase": {"lpa_name": lpa}})
    body = {"size": 5, "track_total_hits": True, "query": {"bool": {"filter": filters}}}
    res, data = es_search(body, verbose=verbose)
    hits = (data.get("hits") or {}).get("hits") or [] if res["ok"] else []
    out = _envelope(res, body, {"reference": reference, "lpa": lpa, "count": len(hits)})
    if not hits:
        out["record"] = None
        out["not_found"] = {"what": "application %r%s" % (reference, " at %s" % lpa if lpa else ""),
                            "query": body, "meaning": DATAHUB_CAVEAT}
        return out
    src = hits[0].get("_source") or {}
    rec = shape(src)
    out["record"] = rec
    out["what_this_means"] = explain(rec, src)
    conds = src.get("decision_conditions")
    portal = rec.get("portal_url")
    out["conditions"] = {
        "in_api": bool(conds),
        "count": len(conds) if isinstance(conds, list) else None,
        "text": conds if isinstance(conds, list) else None,
        "how_to_read_the_rest": (
            "The Datahub carries the conditions attached at decision for about half of all "
            "records, but never the discharge status of each one, the officer report, the "
            "objections or the drawings. Those are read case by case on the borough's own "
            "planning portal: " + (portal or "(no portal URL for this LPA in boroughs.yaml)") +
            " — search there for " + str(reference) + "."),
        "portal_url": portal,
    }
    if len(hits) > 1:
        out["other_matches"] = [shape(h.get("_source") or {}) for h in hits[1:]]
    return out


# -------------------------------------------------------------- planit ------
def planit(postcode, km=0.3, limit=20, verbose=False):
    """Fallback: PlanIt's aggregation of UK planning registers.

    robots: disallowed for /api/applics/; use sparingly, single lookups only.
    Only the `pcode` + `krad` (and `auth` + date-range) query forms work — the
    `search=` parameter matches the description text only, never a site name.
    """
    pc = re.sub(r"\s+", "%20", postcode.strip().upper())
    url = "%s?pcode=%s&krad=%s&pg_sz=%d" % (PLANIT_URL, pc, km, int(limit))
    res = fetch(url, cache_ttl=3600, verbose=verbose,
                expect=lambda b: '"records"' in b)
    rows, total = [], None
    if res["ok"]:
        try:
            j = json.loads(res["body"])
        except ValueError:
            res["ok"], res["note"] = False, "response was not JSON"
            j = {}
        total = j.get("total")
        for r in j.get("records") or []:
            rows.append({
                "reference": r.get("uid") or r.get("reference"),
                "lpa_name": r.get("area_name"),
                "address": r.get("address"),
                "postcode": r.get("postcode"),
                "description": _trim(r.get("description")),
                "application_type": r.get("app_type"),
                "status": r.get("app_state"),
                "decision": r.get("decision") or r.get("app_state"),
                "decision_date": r.get("decided_date"),
                "valid_date": r.get("start_date") or r.get("date_received"),
                "distance_m": (int(round(float(r["distance"]) * 1000))
                               if r.get("distance") not in (None, "") else None),
                "tall_building_hint": tall_building_hint(r.get("description"))[0],
                "case_url": r.get("url") or r.get("link"),
            })
        rows.sort(key=lambda x: (x["distance_m"] is None, x["distance_m"]))
    out = {"source_url": url, "http_status": res["status"], "ok": res["ok"], "note": res["note"],
           "retrieved_at": res["retrieved_at"], "evidence_class": "C",
           "robots": "disallowed for /api/applics/; use sparingly, single lookups only",
           "postcode": postcode, "radius_km": km, "count": len(rows), "total_matching": total,
           "results": rows,
           "caveat": "PlanIt is a third-party mirror of council registers, not the register "
                     "itself; a missing or stale record proves nothing. Use it only when the "
                     "GLA Datahub returns nothing."}
    if res["ok"] and not rows:
        out["not_found"] = {"what": "applications within %s km of %s" % (km, postcode),
                            "query": url}
    return out


# ---------------------------------------------------------------- cli -------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("near", help="applications within a radius of a point")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=250, help="metres (default 250)")
    p.add_argument("--since", type=int, default=2018, help="year; 0 disables the date filter")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--brief", action="store_true",
                   help="the nearest 40 only, ten fields each: what a model needs to read, not the whole record")
    p.add_argument("--bbox", action="store_true",
                   help="use the OSGB36 easting/northing bounding box instead of geo_distance")

    p = sub.add_parser("search", help="full-text search over site, street and description")
    p.add_argument("--text", required=True)
    p.add_argument("--lpa")
    p.add_argument("--since", type=int, default=None)
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("stages", help="one application, plus what its status means for a tenant")
    p.add_argument("--reference", required=True, help="the LPA's own number, e.g. 26/AP/0812")
    p.add_argument("--lpa")

    p = sub.add_parser("planit", help="fallback lookup via PlanIt (robots-disallowed API path)")
    p.add_argument("--postcode", required=True)
    p.add_argument("--km", type=float, default=0.3)
    p.add_argument("--limit", type=int, default=20)

    a = ap.parse_args()
    if a.cmd == "near":
        out = near(a.lat, a.lng, a.radius, a.since, a.limit, bbox=a.bbox, verbose=a.verbose)
        if getattr(a, "brief", False) and isinstance(out.get("results"), list):
            keep = ("reference", "address", "description", "status", "decision", "decision_date", "distance_m",
                    "storeys", "residential_units_proposed", "tall_building_hint", "portal_url")
            rows = sorted(out["results"], key=lambda r: (r.get("distance_m") is None, r.get("distance_m") or 0))[:40]
            out["results"] = [{k: ((r.get(k) or "")[:90] if k in ("description", "address") else r.get(k)) for k in keep} for r in rows]
            out["brief"] = "nearest 40 of %d, ten fields each; drop --brief for the full records" % out.get("count", len(rows))
    elif a.cmd == "search":
        out = search(a.text, a.lpa, a.since, a.limit, verbose=a.verbose)
    elif a.cmd == "stages":
        out = stages(a.reference, a.lpa, verbose=a.verbose)
    else:
        out = planit(a.postcode, a.km, a.limit, verbose=a.verbose)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not out.get("ok"):
        sys.stderr.write("fetch failed: %s\n" % out.get("note"))
        sys.exit(1)


if __name__ == "__main__":
    main()
