#!/usr/bin/env python3
"""Street-level imagery — the closest thing to a viewing before the viewing.

Three routes, in this order. Rule 1 is: use the USER'S OWN key, never one of ours.

  1. Google Street View Static API, with `GOOGLE_MAPS_KEY` in a plain `.env` next
     to this script (or in the environment). Best coverage in London; the
     coverage/date check is free, the images are not.
  2. Mapillary Graph API v4, with the user's own free `MAPILLARY_TOKEN`.
     Crowd-sourced, CC BY-SA 4.0, free, patchy.
  3. No key at all: `streetview.py brief` prints the checklist so the agent can
     ask the user to open Street View themselves and paste screenshots back.

SOURCES, all opened and checked 2026-09-05
  Google Street View Static API (official Google product; needs a key AND a
  Google Cloud project with a billing account):
    image     https://maps.googleapis.com/maps/api/streetview
              size (required, max 640x640), location=lat,lng OR pano=<id>,
              heading 0-360, fov default 90 max 120, pitch -90..90,
              radius default 50 m, source=default|outdoor, return_error_code,
              key (required).
    metadata  https://maps.googleapis.com/maps/api/streetview/metadata
              same location/pano/key; returns copyright, date, location, pano_id,
              status (OK | ZERO_RESULTS | NOT_FOUND | OVER_QUERY_LIMIT |
              REQUEST_DENIED | INVALID_REQUEST | UNKNOWN_ERROR).
              Google: "Street View Static API metadata requests are available at
              no charge. No quota is consumed when you request metadata."
    price     After the 2025-03-01 Maps Platform change the old $200 credit is
              gone and each SKU has its own free monthly allowance:
                "Static Street View"    SKU 9BD0-A2EE-44C3 — 10,000 free/month,
                  then $7.00 / 1,000 (0-100k), $5.60 / 1,000 (100k-500k),
                  $4.20 / 1,000 (500k+).
                "Street View Metadata"  SKU 3168-48A9-5C8C — free, unlimited.
              Four images per flat is 4 calls: free until the 2,500th flat of the
              month, and about $0.028 after that.
    terms     Maps Platform ToS 3.2.3(a) "No Scraping": do not export, extract or
              scrape Google Maps Content for use outside the Services — the
              examples name bulk-downloading Street View images.
              3.2.3(b) "No Caching": do not cache Google Maps Content except
              where the Service Specific Terms allow. The Street View policies
              page allows exactly one exception, "the panorama ID ... is exempt
              from the caching restriction. Therefore, you can store panorama ID
              values indefinitely." So keep the pano_id and the date; do not
              keep the JPEG. This script never caches an image, writes them where
              the caller asks, and tells the caller to delete them at the end of
              the session unless the user chose to keep them.
              And never lift images off the maps.google.com website instead of
              calling the API — that is the scraping the same clause forbids.
              Attribution: "You must follow Google Maps attribution requirements
              when displaying Content from Google Maps Platform APIs."
              https://developers.google.com/maps/documentation/streetview/policies

  Mapillary Graph API v4 (not official; free token from
  https://www.mapillary.com/dashboard/developers):
    https://graph.mapillary.com/images?bbox=...&fields=...
    Sent as `Authorization: OAuth <token>` so the token never enters a URL.
    Documented limits: bbox "must be smaller than 0.01 degrees square", limit max
    2000 (the separate radius search caps at 50 m, which is why this script uses
    a bbox). Imagery is CC BY-SA 4.0; Mapillary's terms require the Mapillary
    logo and a link back when images are shown.

  KartaView / OpenStreetCam (https://api.openstreetcam.org/api/doc.html) is a
  third open, CC BY-SA option with a nearby-photos endpoint. Not wired up here.

EVIDENCE CLASS is C for everything this script returns. Street imagery is a
third party's observation of one street on ONE day, and that day is often years
ago. Quote the capture date beside every finding, and never write a present-tense
claim from a dated photograph.

Usage:
  streetview.py check     --lat 51.5045 --lng -0.0865 [--radius 50] [--outdoor]
  streetview.py fetch     --lat 51.5045 --lng -0.0865 --out ./sv \\
                          [--toward-lat 51.5047 --toward-lng -0.0862] \\
                          [--headings 0,90,180,270] [--fov 90] [--pitch 0] \\
                          [--size 640x640] [--used-this-month 0]
  streetview.py mapillary --lat 51.5045 --lng -0.0865 [--radius 60] [--limit 10]
  streetview.py brief
Every command prints ONE JSON object on stdout carrying source_url,
retrieved_at and evidence_class. Exit 0 on success, 2 on usage error (asking
`fetch` to run with no key is one), 1 on fetch failure.
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, fetch_binary, now_iso  # noqa: E402
from roads import bearing_deg, compass, haversine_m  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------- endpoints ----
STATIC_BASE = "https://maps.googleapis.com/maps/api/streetview"
META_BASE = "https://maps.googleapis.com/maps/api/streetview/metadata"
MAPILLARY_BASE = "https://graph.mapillary.com/images"

# --------------------------------------------- documented parameter limits --
MAX_SIZE_PX = 640          # Street View Static API standard maximum, per dimension
MIN_SIZE_PX = 16
MAX_FOV_DEG = 120          # documented maximum; default 90
MIN_FOV_DEG = 10
MAX_IMAGES = 4             # this tool's own cap: four views is a facade, not a survey
MAPILLARY_MAX_RADIUS_M = 300   # keeps the bbox under the documented 0.01 degrees square
MAPILLARY_MAX_LIMIT = 2000

# ---------------------------------------------- pricing, verified 2026-09-05 -
PRICING_CHECKED = "2026-09-05"
PRICING_SOURCE = "https://developers.google.com/maps/billing-and-pricing/pricing"
IMAGE_SKU = "Static Street View (SKU 9BD0-A2EE-44C3)"
METADATA_SKU = "Street View Metadata (SKU 3168-48A9-5C8C)"
FREE_IMAGE_CALLS_PER_MONTH = 10000
# (first call index in the band, USD per 1,000 calls) — monthly volume bands
PRICE_BANDS_USD_PER_1000 = [(0, 7.00), (100000, 5.60), (500000, 4.20)]
METADATA_IS_FREE = True

GOOGLE_ATTRIBUTION = (
    "Imagery © Google, Street View Static API. The returned image carries the Google "
    "wordmark; keep it visible and do not crop it out. Any image reproduced in a report "
    "must follow the Google Maps attribution requirements: "
    "https://developers.google.com/maps/documentation/streetview/policies")
MAPILLARY_ATTRIBUTION = (
    "Imagery © the Mapillary contributor shown in `creator`, licensed CC BY-SA 4.0. "
    "Display the Mapillary logo and link back to the image page when you show it: "
    "https://www.mapillary.com/terms")
STORAGE_NOTE = (
    "Google Maps Platform terms 3.2.3(b) forbid caching Google Maps Content; the Street "
    "View policies exempt only the panorama ID, which may be stored indefinitely. Keep "
    "pano_id, the capture date and your written finding. Delete the image files when the "
    "session ends unless the user has asked to keep their own copy.")
DATE_NOTE = (
    "`date` is when Google's car drove past, not today. London panoramas are commonly one "
    "to five years old and some side streets are older still. Write every finding as "
    "'as of <capture date>' and treat anything that can change in a year — hoardings, "
    "shop fronts, bins, scaffolding — as a lead to confirm, not a fact.")

GET_A_KEY = [
    "Open https://console.cloud.google.com/ and create (or pick) a project.",
    "Attach a billing account to it — the Street View Static API will not serve without "
    "one, even inside the free monthly allowance.",
    "APIs & Services -> Library -> enable 'Street View Static API'.",
    "APIs & Services -> Credentials -> Create credentials -> API key.",
    "Restrict the key: Application restrictions = IP addresses (your machine), API "
    "restrictions = Street View Static API only. An unrestricted key is a billing risk.",
    "Optional but sensible: Billing -> Budgets & alerts -> a budget of a few pounds.",
    "Put it in a file named `.env` next to this script as GOOGLE_MAPS_KEY=... "
    "(one KEY=VALUE per line, no quotes needed, never commit it).",
]
DO_IT_BY_HAND = [
    "Open https://www.google.com/maps and search the address, then drop the yellow "
    "pegman on the street outside the building.",
    "Take screenshots looking at the building, along the street both ways, and at "
    "whatever stands across the road.",
    "Note the capture date Google prints in the corner of the Street View window — it is "
    "the single most important thing on the screen.",
    "Paste the screenshots into the chat. Screenshots you take yourself are yours to "
    "keep; do not ask an agent to scrape them off the website.",
]
GET_A_MAPILLARY_TOKEN = [
    "Sign in at https://www.mapillary.com/ (free account).",
    "Open https://www.mapillary.com/dashboard/developers and register an application.",
    "Copy the client token it issues.",
    "Put it in `.env` next to this script as MAPILLARY_TOKEN=...",
]


# ------------------------------------------------------------ env / keys ----
def load_env(path=None):
    """Parse a plain KEY=VALUE .env next to this script. No package, no export."""
    path = path or os.path.join(HERE, ".env")
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                if k.lower().startswith("export "):
                    k = k[7:].strip()
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                if k:
                    out[k] = v
    except Exception:
        return out
    return out


def google_key(env=None):
    env = load_env() if env is None else env
    return os.environ.get("GOOGLE_MAPS_KEY") or env.get("GOOGLE_MAPS_KEY") or None


def mapillary_token(env=None):
    env = load_env() if env is None else env
    return os.environ.get("MAPILLARY_TOKEN") or env.get("MAPILLARY_TOKEN") or None


# ----------------------------------------------------------- URL building ---
KEY_PARAM_RE = re.compile(r"([?&](?:key|access_token|signature)=)[^&]*", re.I)


def redact_key(url):
    """Replace the value of key= / access_token= / signature= with REDACTED.

    Every URL that leaves this script — in a manifest, in stdout, in an error —
    goes through here first. A manifest is a file the user may well paste into a
    chat, and a Maps key in the open is somebody else's bill.
    """
    return KEY_PARAM_RE.sub(lambda m: m.group(1) + "REDACTED", url or "")


def _url(base, params):
    """Build a URL with the parameters in a stable order (so tests can assert)."""
    return base + "?" + urllib.parse.urlencode(params)


def metadata_url(lat, lng, key, radius=None, source=None, pano=None):
    p = []
    if pano:
        p.append(("pano", pano))
    else:
        p.append(("location", "%s,%s" % (lat, lng)))
        if radius is not None:
            p.append(("radius", int(radius)))
    if source:
        p.append(("source", source))
    p.append(("key", key))
    return _url(META_BASE, p)


def image_url(key, lat=None, lng=None, pano=None, heading=0.0, fov=90, pitch=0,
              size="640x640", source=None, return_error_code=True):
    """One Street View Static API image URL. `pano` wins over lat/lng when given.

    Pinning to a pano_id keeps all four headings on the SAME panorama, so the
    four views really are four sides of one standing position. It is also the one
    identifier the terms let you store.
    """
    p = [("size", size)]
    if pano:
        p.append(("pano", pano))
    else:
        p.append(("location", "%s,%s" % (lat, lng)))
    p.append(("heading", round(float(heading) % 360.0, 2)))
    p.append(("fov", int(fov)))
    p.append(("pitch", int(pitch)))
    if source:
        p.append(("source", source))
    if return_error_code:
        p.append(("return_error_code", "true"))
    p.append(("key", key))
    return _url(STATIC_BASE, p)


# --------------------------------------------------------------- geometry ---
def heading_toward(from_lat, from_lng, to_lat, to_lng):
    """Compass heading, degrees clockwise from north, camera point -> target.

    The camera point is where Street View stands (the road); the target is the
    building. Getting these the wrong way round photographs the far pavement.
    """
    return round(bearing_deg(from_lat, from_lng, to_lat, to_lng), 1)


def headings_around(base, n=MAX_IMAGES):
    """`n` evenly spaced headings starting at `base` (4 -> the building, the two
    ways along the street, and whatever faces the building across the road)."""
    n = max(1, min(int(n), MAX_IMAGES))
    step = 360.0 / n
    return [round((float(base) + i * step) % 360.0, 1) for i in range(n)]


def plan_headings(headings_arg=None, toward_heading=None):
    """Explicit --headings wins; then --toward; then the four cardinals."""
    if headings_arg:
        vals = [round(float(h) % 360.0, 1) for h in str(headings_arg).split(",") if h.strip()]
    elif toward_heading is not None:
        vals = headings_around(toward_heading)
    else:
        vals = [0.0, 90.0, 180.0, 270.0]
    out = []
    for v in vals:                                   # dedupe, keep order, cap at 4
        if v not in out:
            out.append(v)
    return out[:MAX_IMAGES]


def parse_size(text):
    """'640x640' -> (640, 640), clamped to the documented maximum."""
    m = re.match(r"^\s*(\d{1,5})\s*[xX]\s*(\d{1,5})\s*$", str(text or ""))
    if not m:
        raise ValueError("size must look like 640x640")
    w = max(MIN_SIZE_PX, min(MAX_SIZE_PX, int(m.group(1))))
    h = max(MIN_SIZE_PX, min(MAX_SIZE_PX, int(m.group(2))))
    return w, h


def clamp_fov(fov):
    return max(MIN_FOV_DEG, min(MAX_FOV_DEG, int(fov)))


def clamp_pitch(pitch):
    return max(-90, min(90, int(pitch)))


# ------------------------------------------------------------ cost model ----
def _band_price_per_1000(call_index):
    """USD per 1,000 for the call sitting at 0-based position `call_index` in the
    month. Bands are by monthly volume, so a heavy month prices later calls
    lower, never higher."""
    price = PRICE_BANDS_USD_PER_1000[0][1]
    for start, per_1000 in PRICE_BANDS_USD_PER_1000:
        if call_index >= start:
            price = per_1000
    return price


def estimate_cost_usd(n_images, used_this_month=0):
    """List-price USD for `n_images` more Static Street View calls this month.

    Two rules, both from Google's pricing page:
      * the first FREE_IMAGE_CALLS_PER_MONTH calls of the calendar month cost
        nothing (the per-SKU free allowance that replaced the $200 credit);
      * everything after that is priced in the volume band its position falls in.
    Metadata calls are not counted: that SKU is free and consumes no quota.
    """
    n_images = max(0, int(n_images))
    used = max(0, int(used_this_month))
    total = 0.0
    for i in range(n_images):
        pos = used + i
        if pos < FREE_IMAGE_CALLS_PER_MONTH:
            continue
        total += _band_price_per_1000(pos) / 1000.0
    return round(total, 6)


def cost_block(n_images, used_this_month=0, metadata_calls=1):
    free_left = max(0, FREE_IMAGE_CALLS_PER_MONTH - max(0, int(used_this_month)))
    billable = max(0, int(n_images) - free_left)
    return {
        "image_sku": IMAGE_SKU,
        "metadata_sku": METADATA_SKU,
        "image_calls": int(n_images),
        "metadata_calls": int(metadata_calls),
        "metadata_usd": 0.0 if METADATA_IS_FREE else None,
        "free_image_calls_per_month": FREE_IMAGE_CALLS_PER_MONTH,
        "assumed_image_calls_already_used_this_month": int(used_this_month),
        "free_image_calls_left_before_this_run": free_left,
        "billable_image_calls": billable,
        "estimated_usd": estimate_cost_usd(n_images, used_this_month),
        "price_bands_usd_per_1000": [{"from_call": s, "usd_per_1000": p}
                                     for s, p in PRICE_BANDS_USD_PER_1000],
        "pricing_source": PRICING_SOURCE,
        "pricing_checked": PRICING_CHECKED,
        "note": ("Estimate only, at list price, and it cannot see the rest of your Google "
                 "Cloud bill. Pass --used-this-month with your real month-to-date Static "
                 "Street View count for a truthful figure. Metadata is free and consumes "
                 "no quota, so the coverage check costs nothing."),
    }


# ------------------------------------------------------------- envelopes ----
def _no_key_block(what):
    return {
        "access": "manual",
        "ok": False,
        "evidence_class": "U",
        "retrieved_at": now_iso(),
        "note": ("no GOOGLE_MAPS_KEY in the environment or in a .env next to this script, "
                 "so %s did not run. This is normal and not an error: use your own key, or "
                 "take the screenshots yourself." % what),
        "how_to_get_a_key": GET_A_KEY,
        "or_do_it_by_hand": DO_IT_BY_HAND,
        "cost_if_you_do_get_a_key": cost_block(MAX_IMAGES, 0),
        "brief": "run `streetview.py brief` for the list of what to look at",
    }


# ------------------------------------------------------------------ check ---
def check(lat, lng, radius=50, source=None, verbose=False, key=None):
    """Is there a panorama here, and how old is it? Free — metadata is not billed."""
    key = key if key is not None else google_key()
    out = {
        "point": {"lat": lat, "lng": lng},
        "source_url": redact_key(metadata_url(lat, lng, "REDACTED", radius, source)),
        "retrieved_at": now_iso(),
        "evidence_class": "C",
        "attribution": GOOGLE_ATTRIBUTION,
        "capture_date_note": DATE_NOTE,
        "billing": {"free": True, "sku": METADATA_SKU,
                    "quote": ("Street View Static API metadata requests are available at no "
                              "charge. No quota is consumed when you request metadata.")},
    }
    if not key:
        out.update(_no_key_block("the coverage check"))
        out["http_status"] = None
        out["status"] = None
        out["pano_id"] = None
        out["date"] = None
        out["location"] = None
        return out
    url = metadata_url(lat, lng, key, radius, source)
    res = fetch(url, expect=lambda b: '"status"' in b, verbose=verbose, cache_ttl=86400)
    out["http_status"] = res["status"]
    out["ok"] = res["ok"]
    out["note"] = res["note"]
    out["retrieved_at"] = res["retrieved_at"]
    out["from_cache"] = res.get("from_cache", False)
    out["status"] = None
    out["pano_id"] = None
    out["date"] = None
    out["location"] = None
    if not res["ok"]:
        out["not_found"] = {"what": "Street View coverage", "query": out["source_url"],
                            "meaning": "the metadata endpoint did not answer; this is a fetch "
                                       "failure, not an absence of coverage"}
        return out
    try:
        data = json.loads(res["body"])
    except ValueError:
        out["ok"] = False
        out["note"] = "metadata response was not JSON"
        return out
    out["status"] = data.get("status")
    out["pano_id"] = data.get("pano_id")
    out["date"] = data.get("date")
    out["location"] = data.get("location")
    out["copyright"] = data.get("copyright")
    if out["copyright"]:
        out["attribution"] = out["copyright"] + " — " + GOOGLE_ATTRIBUTION
    loc = out["location"] or {}
    if loc.get("lat") is not None:
        d = haversine_m(lat, lng, loc["lat"], loc["lng"])
        out["camera_distance_m"] = int(round(d))
        b = bearing_deg(lat, lng, loc["lat"], loc["lng"])
        out["camera_bearing_deg"] = int(round(b))
        out["camera_direction"] = compass(b)
        out["heading_from_camera_to_point_deg"] = heading_toward(loc["lat"], loc["lng"], lat, lng)
        out["heading_hint"] = ("point the camera at the building with "
                               "--toward-lat %s --toward-lng %s, or pass "
                               "--headings %s" % (lat, lng,
                                                  out["heading_from_camera_to_point_deg"]))
    if out["status"] != "OK":
        out["not_found"] = {
            "what": "a panorama within %s m of the point" % radius,
            "query": out["source_url"],
            "status": out["status"],
            "meaning": {
                "ZERO_RESULTS": "no panorama near this point (or the pano id is wrong). "
                                "Widen --radius, try the street rather than the courtyard, "
                                "or fall back to Mapillary.",
                "NOT_FOUND": "the location string could not be resolved.",
                "OVER_QUERY_LIMIT": "the key is over its quota or has no billing account.",
                "REQUEST_DENIED": "the key is wrong, restricted away from this API, or the "
                                  "Street View Static API is not enabled on the project.",
                "INVALID_REQUEST": "a required parameter is missing.",
                "UNKNOWN_ERROR": "server-side, usually temporary; retry once.",
            }.get(out["status"], "unrecognised status"),
        }
    return out


# ------------------------------------------------------------------ fetch ---
def fetch_images(lat, lng, out_dir, headings=None, toward_lat=None, toward_lng=None,
                 fov=90, pitch=0, size="640x640", source=None, radius=50,
                 used_this_month=0, verbose=False, key=None):
    """Download up to four views into out_dir and write manifest.json beside them."""
    key = key if key is not None else google_key()
    w, h = parse_size(size)
    size = "%dx%d" % (w, h)
    fov, pitch = clamp_fov(fov), clamp_pitch(pitch)

    toward = None
    toward_heading = None
    if toward_lat is not None and toward_lng is not None:
        toward = {"lat": toward_lat, "lng": toward_lng}
        toward_heading = heading_toward(lat, lng, toward_lat, toward_lng)
    plan = plan_headings(headings, toward_heading)

    man = {
        "source_url": STATIC_BASE,
        "metadata_url": redact_key(metadata_url(lat, lng, "REDACTED", radius, source)),
        "retrieved_at": now_iso(),
        "evidence_class": "C",
        "evidence_class_note": ("C — a third party's photograph of the street on one day. "
                                "Not a register, not a measurement, and not today."),
        "attribution": GOOGLE_ATTRIBUTION,
        "capture_date_note": DATE_NOTE,
        "privacy_and_storage": STORAGE_NOTE,
        "point": {"lat": lat, "lng": lng},
        "toward": toward,
        "toward_heading_deg": toward_heading,
        "toward_direction": compass(toward_heading) if toward_heading is not None else None,
        "headings_deg": plan,
        "fov_deg": fov, "pitch_deg": pitch, "size": size,
        "out_dir": os.path.abspath(out_dir) if out_dir else None,
        "images": [],
    }
    if toward_heading is not None:
        man["headings_note"] = ("heading %.1f (%s) is the camera point looking at the target; "
                                "the rest are 90 degrees apart from it, so you get the "
                                "building, the street both ways, and what faces it across "
                                "the road." % (toward_heading, compass(toward_heading)))

    if not key:
        man.update(_no_key_block("the image download"))
        man["cost_estimate"] = cost_block(len(plan), used_this_month)
        return man, 2

    meta = check(lat, lng, radius=radius, source=source, verbose=verbose, key=key)
    man["coverage"] = {k: meta.get(k) for k in
                       ("status", "pano_id", "date", "location", "copyright", "http_status",
                        "ok", "note", "camera_distance_m", "camera_bearing_deg",
                        "camera_direction")}
    man["pano_id"] = meta.get("pano_id")
    man["capture_date"] = meta.get("date")
    if meta.get("copyright"):
        man["attribution"] = meta["copyright"] + " — " + GOOGLE_ATTRIBUTION
    if meta.get("status") != "OK":
        man["ok"] = False
        man["note"] = ("no panorama to download: metadata status %s. Nothing was requested, "
                       "so nothing was billed." % meta.get("status"))
        man["not_found"] = meta.get("not_found")
        man["cost_estimate"] = cost_block(0, used_this_month)
        return man, 0

    os.makedirs(out_dir, exist_ok=True)
    ok_count = 0
    for hd in plan:
        url = image_url(key, lat=lat, lng=lng, pano=man["pano_id"], heading=hd, fov=fov,
                        pitch=pitch, size=size, source=source)
        name = "streetview-h%03d.jpg" % int(round(hd))
        path = os.path.join(out_dir, name)
        res = fetch_binary(url, path, expect_content_type="image/", verbose=verbose)
        rec = {"file": name, "path": path, "heading_deg": hd, "direction": compass(hd),
               "fov_deg": fov, "pitch_deg": pitch, "size": size,
               "url": redact_key(url), "http_status": res["status"], "ok": res["ok"],
               "note": res["note"], "bytes": res["bytes"],
               "content_type": res["content_type"], "retrieved_at": res["retrieved_at"],
               "pano_id": man["pano_id"], "capture_date": man["capture_date"],
               "evidence_class": "C", "attribution": man["attribution"]}
        if hd == toward_heading:
            rec["shows"] = "the target (the building), from the camera point"
        man["images"].append(rec)
        ok_count += 1 if res["ok"] else 0

    man["ok"] = ok_count > 0
    man["images_downloaded"] = ok_count
    man["note"] = ("" if ok_count == len(plan) else
                   "%d of %d image requests failed; see each image's note"
                   % (len(plan) - ok_count, len(plan)))
    man["cost_estimate"] = cost_block(len(plan), used_this_month)
    man["what_to_look_for"] = [b["heading"] for b in CHECKLIST]
    man["brief"] = "run `streetview.py brief` for the full checklist"

    if out_dir:
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        man["manifest"] = os.path.join(os.path.abspath(out_dir), "manifest.json")
    return man, (0 if man["ok"] else 1)


# -------------------------------------------------------------- mapillary ---
def _bbox(lat, lng, radius_m):
    """Square bbox `radius_m` either side of the point, in degrees.

    Mapillary requires the bbox to be smaller than 0.01 degrees square, so the
    radius is capped rather than silently truncated by the server.
    """
    r = max(1.0, min(float(radius_m), MAPILLARY_MAX_RADIUS_M))
    dlat = r / 111320.0
    dlng = r / (111320.0 * max(0.05, math.cos(math.radians(lat))))
    return (round(lng - dlng, 6), round(lat - dlat, 6),
            round(lng + dlng, 6), round(lat + dlat, 6)), r


MAPILLARY_FIELDS = ("id,captured_at,compass_angle,computed_compass_angle,geometry,"
                    "is_pano,creator,thumb_1024_url,thumb_256_url")


def _epoch_ms_to_iso(ms):
    if ms in (None, ""):
        return None
    try:
        from datetime import datetime, timezone as _tz
        return (datetime.fromtimestamp(float(ms) / 1000.0, _tz.utc)
                .replace(microsecond=0).isoformat())
    except Exception:
        return None


def mapillary(lat, lng, radius=60, limit=10, verbose=False, token=None):
    """Nearest Mapillary images to the point: id, capture date, compass angle, thumb."""
    token = token if token is not None else mapillary_token()
    (west, south, east, north), r = _bbox(lat, lng, radius)
    limit = max(1, min(int(limit), MAPILLARY_MAX_LIMIT))
    url = _url(MAPILLARY_BASE, [("bbox", "%s,%s,%s,%s" % (west, south, east, north)),
                                ("fields", MAPILLARY_FIELDS),
                                ("limit", limit)])
    out = {
        "source_url": url,                 # the token rides in a header, not the URL
        "retrieved_at": now_iso(),
        "evidence_class": "C",
        "attribution": MAPILLARY_ATTRIBUTION,
        "licence": "CC BY-SA 4.0",
        "capture_date_note": DATE_NOTE,
        "point": {"lat": lat, "lng": lng},
        "radius_m_requested": radius,
        "radius_m_used": int(r),
        "bbox": {"west": west, "south": south, "east": east, "north": north},
        "bbox_note": ("Mapillary requires a bbox smaller than 0.01 degrees square, and its "
                      "radius search caps at 50 m, so this uses a bbox and caps the radius "
                      "at %d m." % MAPILLARY_MAX_RADIUS_M),
        "images": [],
    }
    if not token:
        out.update({
            "access": "manual", "ok": False, "evidence_class": "U",
            "http_status": None,
            "note": ("no MAPILLARY_TOKEN in the environment or in a .env next to this "
                     "script. Mapillary is free; a token takes about two minutes."),
            "how_to_get_a_token": GET_A_MAPILLARY_TOKEN,
            "or_do_it_by_hand": [
                "Open https://www.mapillary.com/app/ and search the address.",
                "Green lines are covered streets; click one to open the photo.",
                "Note the capture date and the contributor, and screenshot what you need.",
            ],
        })
        return out
    res = fetch(url, headers={"Authorization": "OAuth " + token,
                              "Accept": "application/json"},
                expect=lambda b: '"data"' in b, verbose=verbose, cache_ttl=3600)
    out["http_status"] = res["status"]
    out["ok"] = res["ok"]
    out["note"] = res["note"]
    out["retrieved_at"] = res["retrieved_at"]
    out["from_cache"] = res.get("from_cache", False)
    if not res["ok"]:
        out["not_found"] = {"what": "Mapillary imagery", "query": url,
                            "meaning": "the API did not answer; a fetch failure, not an "
                                       "absence of coverage"}
        return out
    try:
        data = json.loads(res["body"]).get("data") or []
    except ValueError:
        out["ok"] = False
        out["note"] = "response was not JSON"
        return out
    rows = []
    for im in data:
        coords = ((im.get("geometry") or {}).get("coordinates") or [None, None])
        ilng, ilat = coords[0], coords[1]
        d = None if ilat is None else haversine_m(lat, lng, ilat, ilng)
        ang = im.get("compass_angle")
        if ang is None:
            ang = im.get("computed_compass_angle")
        rows.append({
            "id": im.get("id"),
            "captured_at": _epoch_ms_to_iso(im.get("captured_at")),
            "captured_at_raw_ms": im.get("captured_at"),
            "compass_angle_deg": None if ang is None else round(float(ang), 1),
            "facing": compass(ang) if ang is not None else None,
            "is_pano": im.get("is_pano"),
            "creator": (im.get("creator") or {}).get("username"),
            "lat": ilat, "lng": ilng,
            "distance_m": None if d is None else int(round(d)),
            "bearing_from_point_deg": (None if ilat is None else
                                       int(round(bearing_deg(lat, lng, ilat, ilng)))),
            "thumb_1024_url": im.get("thumb_1024_url"),
            "thumb_256_url": im.get("thumb_256_url"),
            "page_url": "https://www.mapillary.com/app/?pKey=%s&focus=photo" % im.get("id"),
            "evidence_class": "C",
            "attribution": MAPILLARY_ATTRIBUTION,
        })
    rows.sort(key=lambda r: (r["distance_m"] is None, r["distance_m"] or 0))
    out["images"] = rows[:limit]
    out["count"] = len(rows)
    if not rows:
        out["not_found"] = {
            "what": "any Mapillary image inside the bbox", "query": url,
            "meaning": "Mapillary is crowd-sourced. No image here means nobody has driven "
                       "or walked this street with the app, not that the street is "
                       "unremarkable. Try Street View, or ask the user for screenshots."}
    out["thumb_note"] = ("thumb URLs are signed and expire; open them now or ask the user "
                         "to. Reproducing one in a report needs the CC BY-SA 4.0 credit in "
                         "`attribution`.")
    return out


# ------------------------------------------------------------------ brief ---
CHECKLIST = [
    {"heading": "1. Which facade the flat is on, and what it faces",
     "items": [
         "Find the building, then work out which elevation the flat's windows are on: "
         "street, courtyard, or side return. Ask the agent in those words.",
         "Road class and width, how many lanes, whether there is a bus lane, and how far "
         "the kerb is from the wall. A bedroom 6 m from a bus lane is a different flat "
         "from the same bedroom over a courtyard.",
         "Bus stop, taxi rank, loading bay or coach drop directly outside.",
         "Pub, bar, late food, off-licence, vape shop, shisha, launderette, gym extract: "
         "note what is at ground level under and beside the windows.",
         "Where the bins live, and whether the refuse store opens onto the pavement the "
         "flat looks at.",
     ]},
    {"heading": "2. Ground and lower-ground exposure",
     "items": [
         "Window sill height against the pavement: can a person on the pavement see in?",
         "Light well, area, basement stair or railings, and whether the well is deep, "
         "narrow, or full of leaves.",
         "Grilles, security bars, frosted glass or permanently closed blinds — all of them "
         "say something about how exposed the room is.",
         "Steps down to the door, and where surface water would go.",
     ]},
    {"heading": "3. Construction and works",
     "items": [
         "Hoarding, scaffolding, a crane, a site cabin, a wheel wash, a gantry — anywhere "
         "in the frame, on either side of the street.",
         "A hoarding with a developer's name and a planning reference on it is a free lead: "
         "take the reference to roads.py / planning.py.",
         "Road works, a utility trench, a temporary traffic light.",
         "Remember the imagery is dated: a hoarding in the picture may be a finished "
         "building now, and an empty site may be a tower now.",
     ]},
    {"heading": "4. Vacant and shuttered units",
     "items": [
         "Count the shuttered, whitewashed, to-let or boarded shop fronts on the street.",
         "A parade with three empty units and a betting shop reads differently from one "
         "with a butcher and a bakery — but say it as a count and a date, never as a "
         "judgement about who lives there.",
     ]},
    {"heading": "5. What blocks the sky",
     "items": [
         "Count the storeys of the building directly opposite, and of anything that rises "
         "behind it.",
         "Take the distance from roads.py `obstruction_candidates` and check that the "
         "picture agrees with the tagged height.",
         "Estimate the angle: atan(height / distance). Over 45 degrees from a low floor "
         "means very little sky. Compare with the tagged figure and say which you used.",
         "Look for a blank flank wall, a light well, or a deep recess opposite.",
     ]},
    {"heading": "6. Signs of how the block is managed",
     "items": [
         "Bins: stored, or standing on the pavement between collections?",
         "Graffiti and fly-posting on the entrance, and whether it looks recent or painted "
         "over.",
         "The entry phone and door: taped, broken, propped, replaced?",
         "Communal windows, planting, lighting, the state of the front path.",
         "A managing agent's board or a Neighbourhood Watch sign gives you a name to "
         "search on Companies House.",
     ]},
    {"heading": "7. The capture date against the building's age",
     "items": [
         "Read the capture date first, before anything else in the frame.",
         "Compare it with the build year from the EPC or Land Registry. A new build whose "
         "imagery predates completion will show a hoarding or a car park — that is the "
         "camera being old, not the flat not existing.",
         "Where several panoramas exist, step back through the older ones: the change "
         "between two dates is often more useful than either alone.",
         "If the newest imagery is more than about three years old, say so and downgrade "
         "everything you read from it to a lead.",
     ]},
    {"heading": "8. What NOT to infer",
     "items": [
         "Never describe, count, or draw any conclusion from the people in the frame — not "
         "their appearance, ethnicity, nationality, age or apparent circumstances. Faces "
         "are blurred for a reason and this is out of bounds, full stop.",
         "Street imagery is not evidence about crime. Crime goes to crime.py and "
         "data.police.uk; a photograph of a street on one afternoon says nothing about it.",
         "Do not infer who lives there, how well off they are, or what the neighbours are "
         "like. That is not a housing judgement.",
         "Do not read noise, smell or damp from a photograph. Note the source (a pub, an "
         "extract, a main road) as something to check on the day.",
         "Do not read a vehicle, a parked van or a shop's customers as anything at all.",
         "A photograph is class C evidence and dated. It can raise a question or replace "
         "an assumption. It cannot grant a pass.",
     ]},
]


def brief_text():
    lines = ["Street imagery — what to look at (class C evidence, always dated)", ""]
    for block in CHECKLIST:
        lines.append(block["heading"])
        for item in block["items"]:
            lines.append("   - " + item)
        lines.append("")
    lines.append("Ask the user for these four screenshots if you have no key:")
    lines.append("   - looking AT the building from the pavement opposite")
    lines.append("   - looking along the street, one way")
    lines.append("   - looking along the street, the other way")
    lines.append("   - looking at whatever stands across the road from the flat")
    lines.append("   - plus the capture date shown in the corner of the window")
    return "\n".join(lines)


def brief():
    return {
        "source_url": None,
        "retrieved_at": now_iso(),
        "evidence_class": "C",
        "what": "the checklist for reading street-level imagery, before or instead of an API call",
        "routes": [
            {"route": 1, "name": "Google Street View Static API",
             "when": "the user has GOOGLE_MAPS_KEY and wants the best London coverage",
             "cost": "coverage check free; images %s free a month, then $%.2f / 1,000"
                     % (FREE_IMAGE_CALLS_PER_MONTH, PRICE_BANDS_USD_PER_1000[0][1]),
             "command": "streetview.py check ... then streetview.py fetch ... --out <dir>"},
            {"route": 2, "name": "Mapillary",
             "when": "no Google key, or you want a free second date on the same street",
             "cost": "free with a free token; imagery is CC BY-SA 4.0",
             "command": "streetview.py mapillary --lat <lat> --lng <lng>"},
            {"route": 3, "name": "the user's own screenshots",
             "when": "no keys at all, or the runtime has no network",
             "cost": "free",
             "command": "ask for the four views below and the capture date"},
        ],
        "screenshots_to_ask_for": [
            "looking at the building from the pavement opposite",
            "looking along the street one way",
            "looking along the street the other way",
            "looking at whatever stands across the road from the flat",
            "the capture date shown in the corner of the Street View window",
        ],
        "checklist": CHECKLIST,
        "text": brief_text(),
        "capture_date_note": DATE_NOTE,
        "privacy_and_storage": STORAGE_NOTE,
        "attribution_google": GOOGLE_ATTRIBUTION,
        "attribution_mapillary": MAPILLARY_ATTRIBUTION,
        "ok": True,
        "note": "",
    }


# ------------------------------------------------------------------- CLI ----
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="is there a panorama here, and how old is it (free)")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=50, help="search radius in metres (default 50)")
    p.add_argument("--outdoor", action="store_true",
                   help="source=outdoor: skip indoor/business panoramas")

    p = sub.add_parser("fetch", help="download up to four views (needs your own key; billed)")
    p.add_argument("--lat", type=float, required=True, help="the camera point, e.g. the road")
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--out", required=True, help="directory for the images and manifest.json")
    p.add_argument("--headings", default=None,
                   help="comma-separated degrees, e.g. 0,90,180,270 (max 4)")
    p.add_argument("--toward-lat", type=float, default=None,
                   help="target latitude — the building. Heading is computed from --lat/--lng "
                        "toward it, and the other three views are 90 degrees apart.")
    p.add_argument("--toward-lng", type=float, default=None)
    p.add_argument("--fov", type=int, default=90, help="10-120, default 90")
    p.add_argument("--pitch", type=int, default=0, help="-90 to 90, default 0")
    p.add_argument("--size", default="640x640", help="WxH, each capped at 640")
    p.add_argument("--radius", type=int, default=50, help="panorama search radius, metres")
    p.add_argument("--outdoor", action="store_true", help="source=outdoor")
    p.add_argument("--used-this-month", type=int, default=0,
                   help="your month-to-date Static Street View call count, for a truthful "
                        "cost estimate (default 0)")

    p = sub.add_parser("mapillary", help="nearest free CC BY-SA street images")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=60,
                   help="metres, capped at %d (default 60)" % MAPILLARY_MAX_RADIUS_M)
    p.add_argument("--limit", type=int, default=10)

    sub.add_parser("brief", help="print the what-to-look-for checklist and stop")

    a = ap.parse_args()
    code = 0
    if a.cmd == "check":
        out = check(a.lat, a.lng, radius=a.radius,
                    source="outdoor" if a.outdoor else None, verbose=a.verbose)
        code = 0 if out.get("ok") or out.get("access") == "manual" else 1
    elif a.cmd == "fetch":
        if (a.toward_lat is None) != (a.toward_lng is None):
            ap.error("--toward-lat and --toward-lng must be given together")
        try:
            parse_size(a.size)
        except ValueError as exc:
            ap.error(str(exc))
        out, code = fetch_images(a.lat, a.lng, a.out, headings=a.headings,
                                 toward_lat=a.toward_lat, toward_lng=a.toward_lng,
                                 fov=a.fov, pitch=a.pitch, size=a.size,
                                 source="outdoor" if a.outdoor else None, radius=a.radius,
                                 used_this_month=a.used_this_month, verbose=a.verbose)
    elif a.cmd == "mapillary":
        out = mapillary(a.lat, a.lng, radius=a.radius, limit=a.limit, verbose=a.verbose)
        code = 0 if out.get("ok") or out.get("access") == "manual" else 1
    else:
        out = brief()

    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if code == 2:
        sys.stderr.write("refusing to run: %s\n" % out.get("note"))
    elif code:
        sys.stderr.write("fetch failed: %s\n" % out.get("note"))
    sys.exit(code)


if __name__ == "__main__":
    main()
