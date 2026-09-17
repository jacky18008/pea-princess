#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fields out of a listing page the user already saved or pasted. This tool never fetches.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

Give it a file the person saved from their own browser (HTML or plain text) or paste
the page text on stdin, and it prints the facts a listing states - rent and period,
bedrooms, bathrooms, floor, floor area, postcode and postcode district, address,
availability, furnishing, deposit, let type, minimum term, property type, EPC and
council tax band - each with the sentence it was read in, so every value can be
checked against the page.

How it reads, in order of trust:
  1. schema.org JSON-LD blocks (``<script type="application/ld+json">``)
  2. microdata (``itemprop=...``) and Open Graph / meta tags
  3. any JSON object embedded in a script block that happens to carry the same
     standard keys (price, numberOfRooms, floorSize, postalCode ...). A page's own
     data block is often one JSON document carried inside another as a string, and
     often written as an index-referenced array (each object's values are positions
     in one flat list); both forms are opened in place, with no site-specific code.
  4. the visible text, with plain-language patterns ("£1,800 pcm", "2 bedrooms",
     "Bedrooms: 2", "3rd floor", "540 sq ft", a UK postcode)
Postcodes retain candidates and office/entity context across these layers; conflicting
possible property postcodes stay unknown rather than taking the first hit, and a
candidate from another postcode district than the address states is never the
property's (typically the agent's office, printed without an office label). These
context clues do not establish a verified property address.
Beside the fields, ``page`` lists what the data block says about photos, floor plans,
EPC images, virtual tours, coordinates, nearest stations, key features, the
description, the listing date and the marketing agent. Its links are for the person
to open in their own browser; this tool and the skill never fetch them.
Nothing here is written for one website: no site names, no page selectors.

PDF and other binary inputs are refused before decoding, even if renamed to .txt.
For a PDF, first convert it locally with ``pdftotext -layout input.pdf output.txt``,
then pass ``--text output.txt``. Only UTF-8 HTML/plain text is accepted.

What it refuses: a web address. It prints an error asking the person to open the
page in their browser and save or copy it. There is no network code in this file and
none may be added (tests check the imports).

Usage:
  python3 scripts/listing_fields.py saved-page.html
  python3 scripts/listing_fields.py --text pasted.txt
  pbpaste | python3 scripts/listing_fields.py -
"""
from __future__ import unicode_literals

import argparse
import collections
import html
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

REFUSAL = ("This tool does not open web pages. Open the listing in your browser, save "
           "the page (or copy the text), and pass the file.")

FORMAT_REFUSAL = ("Unsupported PDF/binary or non-UTF-8 input. This tool accepts saved HTML or UTF-8 plain text, "
                  "not raw PDF files. For a PDF, first run locally: pdftotext -layout INPUT.pdf OUTPUT.txt; "
                  "then run listing_fields.py --text OUTPUT.txt. No listing fields were extracted.")
BINARY_SUFFIXES = frozenset(('.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.tif', '.tiff',
                             '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.gz',
                             '.mp3', '.mp4', '.mov', '.woff', '.woff2'))
BINARY_SIGNATURES = (b'%PDF-', b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a',
                     b'PK\x03\x04', b'PK\x05\x06', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
                     b'\x1f\x8b', b'RIFF', b'II*\x00', b'MM\x00*')


def decode_saved_text(raw, name='-'):
    """Reject binary bytes rather than replacing them and extracting invented text."""
    if isinstance(raw, str):
        raw = raw.encode('utf-8')  # Supports an explicitly supplied StringIO stdin.
    head = raw[:1024].lstrip(b'\xef\xbb\xbf \t\r\n')
    if (os.path.splitext(name)[1].lower() in BINARY_SUFFIXES or
            head.startswith(BINARY_SIGNATURES) or b'%PDF-' in raw[:1024] or
            any(byte < 32 and byte not in (9, 10, 12, 13) for byte in raw) or b'\x7f' in raw):
        raise ValueError(FORMAT_REFUSAL)
    try:
        return raw.decode('utf-8-sig')
    except UnicodeError as error:
        raise ValueError(FORMAT_REFUSAL) from error


URL_LIKE = re.compile(r"^\s*(?:https?://|www\.)\S+\s*$", re.I)
POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.I)
OUTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\b")
MONEY = r"£\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?"
OFFICE_WORDS = re.compile(r"\b(?:office|branch|agency|registered address|contact details|contact us|marketed by|listed by|"
                          r"advertised by|contact (?:the )?agent|call (?:the )?agent|request details|(?:estate|letting|lettings) agents?)\b", re.I)
PROPERTY_LABEL = re.compile(r"\b(?:property|listing|flat|apartment|house)\s+(?:address|postcode|location)\b", re.I)
OFFICE_KEYS = frozenset(('agent', 'agents', 'agency', 'agentdetails', 'estateagent', 'realestateagent',
                         'office', 'branch', 'broker', 'seller', 'provider', 'publisher', 'author',
                         'contact', 'contactdetails', 'contactdata', 'contactinfo', 'contactinformation',
                         'agentoffice', 'agentdata', 'agentaddress', 'officeaddress', 'branchaddress',
                         'organization', 'organisation', 'customer', 'lister', 'advertiser', 'marketedby',
                         'listedby', 'landlord'))
OFFICE_TYPES = frozenset(('realestateagent', 'organization', 'organisation', 'localbusiness', 'person'))
PROPERTY_TYPES = frozenset(('apartment', 'house', 'residence', 'accommodation', 'singlefamilyresidence', 'realestatelisting'))


def key_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def entity_role(obj, inherited='unassigned'):
    if inherited == 'office':
        return inherited
    types = obj.get('@type', [])
    if not isinstance(types, list):
        types = [types]
    names = {key_name(str(t).rsplit('/', 1)[-1]) for t in types}
    if names & OFFICE_TYPES:
        return 'office'
    return 'property' if names & PROPERTY_TYPES else inherited


WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "studio": 0}

# Standard keys that carry the same meaning wherever a page embeds them.
STANDARD_KEYS = collections.OrderedDict([
    ("rent", ("price", "rent", "rentpcm", "rent_pcm", "monthlyrent", "pricepcm", "amount", "primaryprice",
              "displayprice", "rentamount", "pricepermonth")),
    ("bedrooms", ("numberofbedrooms", "numberofrooms", "bedrooms", "beds", "numberofbeds", "bedroomcount")),
    ("bathrooms", ("numberofbathroomstotal", "numberofbathrooms", "bathrooms", "bathroomcount")),
    ("floor_area", ("floorsize", "floorarea", "area", "size", "sizings", "internalarea", "totalfloorarea")),
    ("postcode", ("postalcode", "postcode", "fullpostcode")),
    ("outcode", ("outcode", "outwardcode", "postcodeoutward", "postcodedistrict")),
    ("address", ("streetaddress", "displayaddress", "address", "fulladdress")),
    ("floor", ("floorlevel", "floor", "entrancefloor", "floornumber")),
    ("available_from", ("availablefrom", "availabilitystarts", "availabledate", "letavailabledate",
                        "availablefromdate", "dateavailable", "availableon")),
    ("furnished", ("furnishtype", "furnished", "furnishing", "furnishedtype", "furnishingtype")),
    ("deposit", ("deposit", "securitydeposit", "depositamount", "tenancydeposit")),
    ("let_type", ("lettype", "tenancytype", "letduration")),
    ("minimum_term_months", ("minimumterminmonths", "minimumterm", "minimumtenancy", "mintenancy", "minimumtermmonths")),
    ("property_type", ("propertysubtype", "propertytype", "dwellingtype")),
    ("epc", ("epcrating", "energyrating", "epc", "epcband", "energyefficiencyrating")),
    ("council_tax_band", ("counciltaxband", "taxband")),
])
UNIT_NAMES = {"mtk": "m2", "ftk": "sq_ft", "sqm": "m2", "m2": "m2", "sq m": "m2", "sqft": "sq_ft", "ft2": "sq_ft", "sq ft": "sq_ft"}

# What the page's own data says beyond the fields. Links are listed, never opened.
PAGE_NOTE = ("Links under page are what the page lists, for the person to open in their own browser; "
             "this tool and the skill never fetch them.")
PAGE_LISTS = collections.OrderedDict([
    ("photos", ("images", "photos", "propertyimages", "propertyphotos", "gallery", "imageurls", "pictures")),
    ("floorplans", ("floorplans", "floorplan", "floorplanimages", "floorplanurls")),
    ("epc_images", ("epcgraphs", "epcimages", "epcs", "energycertificates", "epcdocuments", "epccharts")),
    ("virtual_tours", ("virtualtours", "virtualtour", "tours", "videotours")),
    ("nearest_stations", ("neareststations", "nearbystations", "stations", "transportlinks")),
    ("key_features", ("keyfeatures", "bulletpoints", "highlights", "keypoints", "features")),
])
PAGE_SCALARS = collections.OrderedDict([
    ("description", ("description", "fulldescription", "propertydescription", "longdescription")),
    ("listed_on", ("listingupdatereason", "firstvisibledate", "addedon", "datelisted", "listedon", "dateposted",
                   "datepublished", "addeddate", "listingdate", "firstlisted")),
])
AGENT_NAME_KEYS = ("companyname", "companytradingname", "tradingname", "brandname", "branchdisplayname",
                   "agentname", "displayname", "name")
AGENT_PHONE_KEYS = ("localnumber", "telephonenumber", "telephone", "phonenumber", "phone", "tel")
LINK_KEYS = ("url", "src", "href", "imageurl", "link", "uri", "contenturl")
LAT_KEYS, LNG_KEYS = ("latitude", "lat"), ("longitude", "lng", "lon", "long")


# ------------------------------------------------------------------ html --
class Collector(HTMLParser):
    """Titles, meta tags, canonical link, script blocks, microdata and visible text."""

    SKIP = ("script", "style", "noscript", "template", "svg", "head")
    VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"))

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.title, self.canonical = "", None
        self.meta = collections.OrderedDict()
        self.scripts = []                       # (type, text)
        self.microdata = collections.OrderedDict()
        self.micro_locations = []
        self._roles = []
        self.text_parts = []
        self._stack = []
        self._script_type = None
        self._itemprop = None
        self._in_title = False
        self._title_done = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        role = entity_role({'@type': (a.get('itemtype') or '').split()}, self._roles[-1] if self._roles else 'unassigned')
        if key_name(a.get('itemprop', '')) in OFFICE_KEYS:
            role = 'office'
        if tag not in self.VOID:
            self._stack.append(tag)
            self._roles.append(role)
        if tag == "title":
            # The page's own title only: not an icon's <title> inside an <svg>, not a later one.
            if not self._title_done and "svg" not in self._stack[:-1]:
                self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").strip().lower()
            if key and a.get("content") is not None:
                self.meta.setdefault(key, a["content"].strip())
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = a["href"].strip()
        elif tag == "script":
            self._script_type = (a.get("type") or "").lower()
        if a.get("itemprop"):
            prop = a["itemprop"].strip()
            value = a.get("content") or a.get("datetime") or a.get("href")
            if value:
                self._micro(prop, value.strip(), role)
            else:
                self._itemprop = (prop, role)
        if tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article", "dd", "dt"):
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True
        if tag == "script":
            self._script_type = None
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
            self._roles.pop()
        elif tag in self._stack:
            while self._stack:
                popped = self._stack.pop()
                self._roles.pop()
                if popped == tag:
                    break
        if tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article", "dd"):
            self.text_parts.append("\n")

    def _micro(self, prop, value, role):
        if key_name(prop) in STANDARD_KEYS['postcode'] + STANDARD_KEYS['address']:
            node = {prop: value}
            if role == 'office':
                node = {'agent': node}
            elif role == 'property':
                node['@type'] = 'Accommodation'
            self.micro_locations.append(node)
        else:
            self.microdata.setdefault(prop, value)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if "script" in self._stack:
            self.scripts.append((self._script_type or "", data))
            return
        if any(t in self._stack for t in self.SKIP):
            return
        if self._itemprop:
            text = data.strip()
            if text:
                self._micro(self._itemprop[0], text, self._itemprop[1])
                self._itemprop = None
        self.text_parts.append(data)


def visible_text(parts):
    text = html.unescape("".join(parts))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


# ------------------------------------------------------------------ json --
def jsonld_objects(scripts):
    out = []
    for kind, text in scripts:
        if "ld+json" not in kind:
            continue
        try:
            doc = json.loads(text.strip())
        except ValueError:
            continue
        stack = [doc]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                out.append(node)
                if isinstance(node.get("@graph"), list):
                    stack.extend(node["@graph"])
    return out


INDEXED_TAGS = ("Date", "Set", "Map", "RegExp", "Object", "BigInt", "null")


def looks_indexed(doc):
    """An index-referenced array: a list whose first item is an object (or list) whose
    values are all positions in that same list."""
    if not isinstance(doc, list) or len(doc) < 2 or not isinstance(doc[0], (dict, list)):
        return False
    refs = list(doc[0].values()) if isinstance(doc[0], dict) else doc[0]
    return bool(refs) and all(isinstance(r, int) and not isinstance(r, bool) and -6 <= r < len(doc) for r in refs)


def unflatten_indexed(values, limit=200000):
    """Rebuild the tree an index-referenced array encodes: positions become values,
    negative positions are the encoder's names for undefined and the like, tagged lists
    such as ["Date", ...] keep their payload. Shared and cyclic references are safe."""
    memo = {}
    budget = [limit]

    def build(ref, depth):
        if isinstance(ref, bool) or not isinstance(ref, int):
            return ref
        if ref < 0 or ref >= len(values) or depth > 60 or budget[0] <= 0:
            return None
        if ref in memo:
            return memo[ref]
        budget[0] -= 1
        value = values[ref]
        if isinstance(value, dict):
            out = collections.OrderedDict()
            memo[ref] = out
            for key, child in value.items():
                out[key] = build(child, depth + 1)
            return out
        if isinstance(value, list):
            if value and isinstance(value[0], str) and value[0] in INDEXED_TAGS:
                tag = value[0]
                if tag in ("Date", "RegExp", "BigInt", "Object"):
                    memo[ref] = value[1] if len(value) > 1 else None
                    return memo[ref]
                out = collections.OrderedDict() if tag in ("Map", "null") else []
                memo[ref] = out
                if tag == "Set":
                    out.extend(build(child, depth + 1) for child in value[1:])
                elif tag == "Map":
                    for key, child in zip(value[1::2], value[2::2]):
                        out[str(build(key, depth + 1))] = build(child, depth + 1)
                else:  # "null": an object without a prototype, its keys given in place
                    for key, child in zip(value[1::2], value[2::2]):
                        out[str(key)] = build(child, depth + 1)
                return out
            out = []
            memo[ref] = out
            out.extend(build(child, depth + 1) for child in value)
            return out
        memo[ref] = value
        return value

    return build(0, 0)


def nested_json(obj, depth=0):
    """A JSON document carried inside a string value (a page's own data block) is opened
    in place; an index-referenced array is rebuilt into the tree it encodes."""
    if depth > 4:
        return obj
    if isinstance(obj, dict):
        return collections.OrderedDict((k, nested_json(v, depth + 1)) for k, v in obj.items())
    if isinstance(obj, list):
        return [nested_json(v, depth + 1) for v in obj[:400]]
    if isinstance(obj, str) and len(obj) > 80 and obj.lstrip()[:1] in "[{":
        try:
            inner = json.loads(obj)
        except ValueError:
            return obj
        if looks_indexed(inner):
            inner = unflatten_indexed(inner)
        return nested_json(inner, depth + 1)
    return obj


def embedded_json_objects(scripts, limit=40):
    """JSON objects that a page embeds in plain script blocks (`var x = {...};`)."""
    out = []
    for kind, text in scripts:
        if "ld+json" in kind or len(text) < 40:
            continue
        covered_end = -1
        for start in [m.start() for m in re.finditer(r"\{", text)][:200]:
            if start <= covered_end:
                continue
            depth, in_str, esc = 0, False, False
            for i in range(start, min(len(text), start + 400000)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        covered_end = i
                        chunk = text[start:i + 1]
                        if len(chunk) > 60:
                            try:
                                obj = json.loads(chunk)
                            except ValueError:
                                break
                            if isinstance(obj, dict):
                                out.append(nested_json(obj))
                        break
            if len(out) >= limit:
                return out
    return out


def walk(obj, found, path="", postcode_candidates=None, role="unassigned", depth=0):
    """Collect standard fields, retaining postcode candidates with their entity scope."""
    if depth > 40:
        return
    if isinstance(obj, dict):
        role = entity_role(obj, role)
        named = {}
        for key in obj:
            named.setdefault(key_name(key), key)
        # A postcode split into its two halves (outward and inward) is one candidate.
        outward = next((named[n] for n in ("outcode", "outwardcode", "postcodeoutward") if n in named), None)
        inward = next((named[n] for n in ("incode", "inwardcode", "postcodeinward") if n in named), None)
        if outward and inward and postcode_candidates is not None and isinstance(obj[outward], str) and isinstance(obj[inward], str):
            value = (obj[outward].strip() + " " + obj[inward].strip()).upper()
            postcode_candidates.append({'value': value, 'role': role,
                                        'quote': '%s at %s/%s+%s' % (json.dumps(value), path, outward, inward)})
        for key, value in obj.items():
            lowered = str(key).replace("_", "").replace("-", "").lower()
            for field, names in STANDARD_KEYS.items():
                if lowered in names and field == 'postcode' and postcode_candidates is not None:
                    if isinstance(value, (str, int, float)):
                        postcode_candidates.append({'value': str(value).strip().upper(), 'role': role,
                            'quote': '%s at %s/%s' % (json.dumps(value, ensure_ascii=False), path, key)})
                    continue
                if lowered in names and field not in found and not (role == 'office' and field in ('address', 'postcode', 'outcode')):
                    if isinstance(value, dict):
                        scalar = value.get("value") if "value" in value else (value.get("price") or value.get("name"))
                        unit = value.get("unitCode") or value.get("unitText") or value.get("priceCurrency")
                        if scalar not in (None, ""):
                            found[field] = (scalar, unit, path + "/" + str(key))
                    elif isinstance(value, list) and field == 'floor_area' and value and isinstance(value[0], dict):
                        # sizes given as a list of {unit, minimumSize | value}: the first entry
                        first = {key_name(k): v for k, v in value[0].items()}
                        scalar = first.get("minimumsize", first.get("value", first.get("size")))
                        if scalar not in (None, ""):
                            found[field] = (scalar, first.get("unit") or first.get("unitcode"), path + "/" + str(key) + "[0]")
                    elif isinstance(value, bool):
                        if field == 'furnished':
                            found[field] = ("furnished" if value else "unfurnished", None, path + "/" + str(key))
                    elif isinstance(value, (str, int, float)) and str(value).strip():
                        found[field] = (value, None, path + "/" + str(key))
            walk(value, found, path + "/" + str(key), postcode_candidates, "office" if lowered in OFFICE_KEYS else role, depth + 1)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:50]):
            walk(item, found, path + "[%d]" % i, postcode_candidates, role, depth + 1)


def strip_tags(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value)))).strip()


def links_in(value):
    """Web addresses a list names: strings, or objects with url/src/href (and a caption)."""
    out = []
    for item in (value if isinstance(value, list) else [value])[:60]:
        if isinstance(item, str) and item.startswith(("http://", "https://", "//")):
            out.append(collections.OrderedDict([("url", item)]))
        elif isinstance(item, dict):
            named = {key_name(k): v for k, v in item.items()}
            link = next((named[k] for k in LINK_KEYS if isinstance(named.get(k), str) and named[k].strip()), None)
            if link:
                entry = collections.OrderedDict([("url", link.strip())])
                caption = next((named[k] for k in ("caption", "title", "label", "alt", "name")
                                if isinstance(named.get(k), str) and named[k].strip()), None)
                if caption:
                    entry["caption"] = strip_tags(caption)
                out.append(entry)
    return out


def stations_in(value):
    out = []
    for item in (value if isinstance(value, list) else [])[:20]:
        if isinstance(item, str) and item.strip():
            out.append(collections.OrderedDict([("name", item.strip())]))
            continue
        if not isinstance(item, dict):
            continue
        named = {key_name(k): v for k, v in item.items()}
        name = next((named[k] for k in ("name", "stationname", "station", "title") if isinstance(named.get(k), str)), None)
        if not name or not name.strip():
            continue
        entry = collections.OrderedDict([("name", name.strip())])
        for key, implied in (("distance", None), ("distancemiles", "miles"), ("distancekm", "km"), ("distancem", "m")):
            if number(named.get(key)) is not None:
                entry["distance"] = round(number(named[key]), 2)
                unit = next((named[k] for k in ("unit", "distanceunit", "units") if isinstance(named.get(k), str)), None) or implied
                if unit:
                    entry["unit"] = unit
                break
        modes = next((named[k] for k in ("types", "type", "modes", "mode", "transporttype") if named.get(k)), None)
        if isinstance(modes, str):
            modes = [modes]
        if isinstance(modes, list):
            entry["modes"] = [strip_tags(m).lower().replace("_", " ") for m in modes[:4] if isinstance(m, str)]
        out.append(entry)
    return out


def feature_strings(value, depth=0):
    out = []
    items = value if isinstance(value, list) else (list(value.values()) if isinstance(value, dict) else [value])
    for item in items[:60]:
        if isinstance(item, str) and item.strip():
            out.append(strip_tags(item))
        elif isinstance(item, dict):
            named = {key_name(k): v for k, v in item.items()}
            text = next((named[k] for k in ("displaytext", "text", "label", "name", "title", "value")
                         if isinstance(named.get(k), str) and named[k].strip()), None)
            if text:
                out.append(strip_tags(text))
            elif depth < 2:
                out.extend(feature_strings(item, depth + 1))
        elif isinstance(item, list) and depth < 2:
            out.extend(feature_strings(item, depth + 1))
    return out[:30]


def page_extras(objects, how):
    """What the page's own data says beyond the fields: media links, coordinates, nearest
    stations, key features, the description, the listing date, the marketing agent.
    Links are listed for the person, never opened here."""
    page = collections.OrderedDict()
    agent = collections.OrderedDict()
    names = {}

    def put(name, value, path):
        if name in page or value in (None, "", [], {}):
            return
        entry = collections.OrderedDict()
        if isinstance(value, list):
            entry["count"] = len(value)
            entry["items"] = value[:40]
        else:
            entry["value"] = value
        entry["how"], entry["quote"] = how, path
        page[name] = entry

    def visit(obj, path, role, depth):
        if depth > 40:
            return
        if isinstance(obj, dict):
            role = entity_role(obj, role)
            named = {}
            for key in obj:
                named.setdefault(key_name(key), key)
            if role == "office":
                for key in AGENT_NAME_KEYS:
                    if key in named and isinstance(obj[named[key]], str) and obj[named[key]].strip():
                        names.setdefault(key, (strip_tags(obj[named[key]]), path + "/" + str(named[key])))
                for key in AGENT_PHONE_KEYS:
                    if key in named and isinstance(obj[named[key]], str) and obj[named[key]].strip():
                        agent.setdefault("phone", strip_tags(obj[named[key]]))
                for key in STANDARD_KEYS["address"]:
                    if key in named and isinstance(obj[named[key]], str) and obj[named[key]].strip():
                        agent.setdefault("address", strip_tags(obj[named[key]]))
            else:
                lat = next((obj[named[k]] for k in LAT_KEYS if k in named), None)
                lng = next((obj[named[k]] for k in LNG_KEYS if k in named), None)
                if number(lat) is not None and number(lng) is not None and "coordinates" not in page:
                    entry = collections.OrderedDict([("lat", number(lat)), ("lng", number(lng))])
                    if re.search(r"approx", " ".join(str(v) for v in obj.values() if isinstance(v, str)), re.I):
                        entry["precision"] = "approximate, as the page places it"
                    put("coordinates", entry, path)
            for key, value in obj.items():
                lowered = key_name(key)
                child_path = path + "/" + str(key)
                if role != "office":
                    for name, keys in PAGE_LISTS.items():
                        if lowered in keys and name not in page:
                            if name == "nearest_stations":
                                put(name, stations_in(value), child_path)
                            elif name == "key_features":
                                put(name, feature_strings(value), child_path)
                            else:
                                put(name, links_in(value), child_path)
                    for name, keys in PAGE_SCALARS.items():
                        if lowered in keys and isinstance(value, str) and name not in page:
                            text = strip_tags(value)
                            if name != "description" or len(text) >= 80:
                                put(name, text[:4000], child_path)
                visit(value, child_path, "office" if lowered in OFFICE_KEYS else role, depth + 1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:50]):
                visit(item, path + "[%d]" % i, role, depth + 1)

    for obj in objects:
        visit(obj, "", "unassigned", 0)
    name_path = ""
    for key in AGENT_NAME_KEYS:
        if key in names:
            agent["name"], name_path = names[key]
            agent.move_to_end("name", last=False)
            break
    if agent:
        entry = collections.OrderedDict(agent)
        entry["how"], entry["quote"] = how, name_path
        page["agent"] = entry
    return page


def text_postcodes(text):
    candidates = []
    for match in POSTCODE.finditer(text):
        # PDF text may put an office heading several short lines before its postcode.
        before = text[max(0, match.start() - 500):match.start()]
        lines = [line.strip() for line in before.splitlines() if line.strip()][-6:]
        context = '\n'.join(lines)
        offices = list(OFFICE_WORDS.finditer(context))
        properties = list(PROPERTY_LABEL.finditer(context))
        role = 'unassigned'
        if offices and (not properties or offices[-1].start() > properties[-1].start()):
            role = 'office'
        elif properties:
            role = 'property'
        candidates.append({'value': (match.group(1) + ' ' + match.group(2)).upper(),
                           'how': 'text', 'role': role,
                           'quote': re.sub(r'\s+', ' ', (context + ' ' + text[match.start():match.end()])).strip()[-500:]})
    return candidates


def resolve_postcode(candidates, expected_outcodes=None):
    """An office is not the dwelling; conflicting plausible postcodes stay unknown.

    expected_outcodes: the postcode districts the address or title states ({'SE13'}). A
    candidate from another district cannot be the property's - typically the agent's
    office, printed without an office label."""
    for candidate in candidates:
        match = POSTCODE.fullmatch(candidate['value'])
        if match:
            candidate['value'] = (match.group(1) + ' ' + match.group(2)).upper()
            if expected_outcodes and candidate['role'] == 'unassigned' and match.group(1).upper() not in expected_outcodes:
                candidate['role'] = 'other_district'
                candidate['note'] = 'postcode district differs from the address (%s)' % ', '.join(sorted(expected_outcodes))
    office_values = {c['value'] for c in candidates if c['role'] in ('office', 'other_district')}
    usable = []
    for candidate in candidates:
        match = POSTCODE.fullmatch(candidate['value'])
        if not match or candidate['role'] in ('office', 'other_district'):
            continue
        if candidate['role'] != 'property' and candidate['value'] in office_values:
            continue
        usable.append(candidate)
    values = {c['value'] for c in usable}
    if len(values) == 1:
        chosen = usable[0]
        return collections.OrderedDict([('value', chosen['value']), ('unit', None),
                                       ('how', chosen['how']), ('quote', chosen['quote'])]), (
            'Office/contact postcodes were excluded.' if office_values else None)
    if len(values) > 1:
        return None, 'Conflicting possible property postcodes; confirm the property address.'
    if candidates:
        return None, 'No unambiguous full property postcode; office/contact or incomplete location values are retained as candidates only.'
    return None, None


def bare_outcode_lines(text):
    """Districts that address-like lines end with ('Pargeter Yard, London, XE2'): how a
    listing names where the home is without giving the full postcode."""
    found = set()
    for line in str(text or "").split("\n"):
        if "," in line:
            part = line.rsplit(",", 1)[-1].strip().rstrip(".")
            if re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?", part, re.I):
                found.add(part.upper())
    return found


def address_outcodes(*texts):
    """Postcode districts an address or title ends with ('..., London, SE13' -> {'SE13'})."""
    found = set()
    for text in texts:
        for line in str(text or "").replace("\r", "\n").split("\n"):
            for part in line.split(","):
                m = re.fullmatch(r"([A-Z]{1,2}\d[A-Z\d]?)(?:\s+\d[A-Z]{2})?\.?", part.strip(), re.I)
                if m:
                    found.add(m.group(1).upper())
    return found


# ------------------------------------------------------------------ text --
def number(token):
    try:
        return float(str(token).replace(",", ""))
    except ValueError:
        return None


def sentence_around(text, start, end, width=110):
    left = max(0, text.rfind("\n", 0, start), text.rfind(". ", 0, start) + 1)
    right = min(len(text), start + width)
    span = text[max(left, start - width):right].strip()
    return re.sub(r"\s+", " ", span)[:220]


COUNT_LABELS = {"bedrooms": r"bedrooms|beds|no\.?\s*of\s*bed(?:room)?s|bedroom\s*:",
                "bathrooms": r"bathrooms|baths|no\.?\s*of\s*bath(?:room)?s|bathroom\s*:"}
COUNT_WORDS = {"bedrooms": r"bed(?:room)?s?", "bathrooms": r"bath(?:room)?s?"}
LABEL_BEFORE = re.compile(r"(?:bed(?:room)?s?|bath(?:room)?s?|receptions?|size|floors?|type)\s*[:\-\u2013]?\s*$", re.I)
LABEL_WITH_VALUE = re.compile(r"\d\s*[- ]?\s*(?:bed(?:room)?s?|bath(?:room)?s?|receptions?)\s*[:\-\u2013]?\s*$", re.I)
FLOOR_WORDS = {"lower ground": -1.0, "basement": -1.0, "ground": 0.0, "first": 1.0, "second": 2.0, "third": 3.0,
               "fourth": 4.0, "fifth": 5.0, "sixth": 6.0, "seventh": 7.0, "eighth": 8.0, "ninth": 9.0, "tenth": 10.0}
DATE = r"now|immediately|\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}"


def count_in_text(text, field):
    """'Bedrooms: 2' (label first) wins; '2 bedrooms' (value first) is read unless the
    number is the value of the label just before it ('BEDROOMS 2 BATHROOMS 1')."""
    m = re.search(r"\b(?:%s)\s*[:\-\u2013]?\s*(\d{1,2}|studio)\b" % COUNT_LABELS[field], text, re.I)
    if m:
        return m
    for m in re.finditer(r"\b(\d{1,2}|one|two|three|four|five|six|studio)\s*[- ]?(?:%s)\b" % COUNT_WORDS[field], text, re.I):
        before = text[max(0, m.start() - 24):m.start()]
        if LABEL_BEFORE.search(before) and not LABEL_WITH_VALUE.search(before):
            continue
        return m
    return None


def text_facts(text, postcode_candidates=None):
    facts = collections.OrderedDict()

    def put(field, value, unit, m, how="text"):
        if field not in facts and value is not None:
            facts[field] = collections.OrderedDict([("value", value), ("unit", unit), ("how", how),
                                                    ("quote", sentence_around(text, m.start(), m.end()))])

    m = re.search(MONEY + r"\s*(pcm|per calendar month|per month|a month|/\s*month|monthly)", text, re.I)
    if m:
        put("rent", number(m.group(1)), "GBP/month", m)
    else:
        m = re.search(MONEY + r"\s*(pw|per week|a week|/\s*week|weekly)", text, re.I)
        if m:
            put("rent", number(m.group(1)), "GBP/week", m)
    for field in ("bedrooms", "bathrooms"):
        m = count_in_text(text, field)
        if m:
            raw = m.group(1).lower()
            value = float(WORD_NUM[raw]) if raw in WORD_NUM else number(raw)
            if value is not None and value <= 12:
                put(field, value, "count", m)
    m = re.search(r"\b(lower ground|ground|basement|top|penthouse|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)[- ]floor\b"
                  r"|\b(\d{1,2})(?:st|nd|rd|th)[- ]floor\b|\bfloor\s*[:\-\u2013]\s*(\d{1,2})\b", text, re.I)
    if m:
        if m.group(2) or m.group(3):
            put("floor", number(m.group(2) or m.group(3)), "UK_floor", m)
        else:
            word = m.group(1).lower()
            put("floor", FLOOR_WORDS.get(word, word), "UK_floor", m)
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(sq\.?\s*ft|square\s*feet|sqft|ft\u00b2)\b", text, re.I)
    if m:
        put("floor_area", number(m.group(1)), "sq_ft", m)
    else:
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(m\u00b2|sq\.?\s*m\b|sqm|square\s*met(?:re|er)s?)", text, re.I)
        if m:
            put("floor_area", number(m.group(1)), "m2", m)
    candidates = text_postcodes(text)
    if postcode_candidates is not None:
        postcode_candidates.extend(candidates)
    selected, _ = resolve_postcode(candidates)
    if selected:
        facts['postcode'] = selected
    m = re.search(r"\b(?:available|availability|let available date|available date|move[- ]in(?: date)?)\s*(?:date)?\s*[:\-\u2013]?\s*(?:from\s+)?("
                  + DATE + r")\b", text, re.I)
    if m:
        value = m.group(1)
        put("available_from", value.lower() if value.lower() in ("now", "immediately") else value, None, m)
    m = re.search(r"\b(part[- ]furnished|unfurnished|furnished)\b", text, re.I)
    if m:
        put("furnished", m.group(1).lower().replace(" ", "-"), None, m)
    m = (re.search(r"(?<!holding )\bdeposit\s*[:\-\u2013]?\s*" + MONEY, text, re.I)
         or re.search(r"(?<!holding )\bdeposit[^\u00a3\n]{0,40}" + MONEY, text, re.I))
    if m:
        put("deposit", number(m.group(1)), "GBP", m)
    else:
        m = re.search(r"(?<!holding )\bdeposit[^\u00a3\n]{0,30}?\b(\d{1,2}|one|two|three|four|five|six)\s+weeks?'?(?:\s*(?:of\s+)?rent)?\b", text, re.I)
        if m:
            raw = m.group(1).lower()
            put("deposit", float(WORD_NUM[raw]) if raw in WORD_NUM else number(raw), "weeks_rent", m)
    m = re.search(r"\b(?i:EPC|energy rating|energy performance(?: certificate)?)(?:\s*(?i:rating|band|grade))?\s*(?i:of|is|=)?\s*[:\-\u2013]?\s*([A-G])\b(?![ \t]+[a-z])", text)
    if m:
        put("epc", m.group(1), "band", m)
    m = re.search(r"\b(?i:council\s*tax)(?:\s*(?i:band))?\s*[:\-\u2013]?\s*(?i:band)?\s*(?i:of|is|=)?\s*[:\-\u2013]?\s*([A-H])\b(?![ \t]+[a-z])", text)
    if m:
        put("council_tax_band", m.group(1), "band", m)
    m = re.search(r"\b(?:let type|tenancy type|let)\s*[:\-\u2013]\s*((?:short|long)[- ]term|(?:short|long)\s*let)\b", text, re.I)
    if m:
        put("let_type", re.sub(r"[- ]+", " ", m.group(1).lower()), None, m)
    m = re.search(r"\bmin(?:imum|\.)?\s*(?:term|tenancy|let)(?:\s*length)?\s*[:\-\u2013]?\s*(\d{1,2})\s*months?\b", text, re.I)
    if m:
        put("minimum_term_months", number(m.group(1)), "months", m)
    m = re.search(r"\bproperty\s*type\s*[:\-\u2013]?\s*(flat|apartment|studio|maisonette|penthouse|duplex|terraced house|"
                  r"semi-detached house|detached house|house|bungalow|room)\b", text, re.I)
    if m:
        put("property_type", m.group(1).lower(), None, m)
    return facts


# --------------------------------------------------------------- assemble --
def structured_facts(objects, how, postcode_candidates=None):
    found = collections.OrderedDict()
    candidates = []
    for obj in objects:
        walk(obj, found, postcode_candidates=candidates)
    for candidate in candidates:
        candidate['how'] = how
    if postcode_candidates is not None:
        postcode_candidates.extend(candidates)
    facts = collections.OrderedDict()
    for field, (value, unit, path) in found.items():
        # "4th floor", "540 sq ft", "£1,595 pcm", "6 weeks": a string with its unit inside is
        # read with the same plain-language patterns as the visible text.
        if isinstance(value, str) and field in ("rent", "bedrooms", "bathrooms", "floor", "floor_area", "deposit", "minimum_term_months"):
            sub = text_facts(("deposit " if field == "deposit" else "") + value)
            if field in sub:
                value, unit = sub[field]["value"], sub[field]["unit"]
        if field == "rent":
            value = number(value)
            unit = unit or "GBP/month"
        elif field in ("bedrooms", "bathrooms", "floor", "deposit", "minimum_term_months"):
            value = number(value) if number(value) is not None else value
            unit = unit or {"bedrooms": "count", "bathrooms": "count", "floor": "UK_floor", "deposit": "GBP",
                            "minimum_term_months": "months"}[field]
        elif field == "floor_area":
            value = number(value) if number(value) is not None else value
            unit = UNIT_NAMES.get(str(unit).strip().lower(), unit) if unit else "m2"
        elif field in ("postcode", "outcode"):
            value = str(value).strip().upper()
        elif field in ("furnished", "let_type", "property_type"):
            value = re.sub(r"[\s_]+", "-" if field == "furnished" else " ", strip_tags(value).lower()).strip()
        elif field == "available_from":
            value = strip_tags(value)
            value = value.lower() if value.lower() in ("now", "immediately") else value
        elif field in ("epc", "council_tax_band"):
            text = strip_tags(value).upper()
            letters = re.findall(r"\b([A-H])\b" if field == "council_tax_band" else r"\b([A-G])\b", text)
            value = letters[0] if letters and len(text) <= 12 else None
            unit = "band"
        if value is None or value == "":
            continue
        facts[field] = collections.OrderedDict([("value", value), ("unit", unit), ("how", how),
                                                ("quote", "%s at %s" % (json.dumps(value, ensure_ascii=False), path))])
    selected, _ = resolve_postcode(candidates)
    if selected:
        facts['postcode'] = selected
    return facts


def extract(raw, kind):
    """(record) for one saved page (kind 'html') or pasted text (kind 'text')."""
    facts = collections.OrderedDict()
    postcode_candidates = []
    page = collections.OrderedDict()
    source = collections.OrderedDict([("kind", "saved_page" if kind == "html" else "pasted_text")])
    if kind == "html":
        parser = Collector()
        parser.feed(raw)
        source["title"] = re.sub(r"\s+", " ", parser.title).strip() or None
        source["canonical"] = parser.canonical or parser.meta.get("og:url")
        jsonld = jsonld_objects(parser.scripts)
        for field, fact in structured_facts(jsonld, "jsonld", postcode_candidates).items():
            facts.setdefault(field, fact)
        micro = collections.OrderedDict((k, v) for k, v in parser.microdata.items())
        for field, fact in structured_facts([micro] + parser.micro_locations, "microdata", postcode_candidates).items():
            facts.setdefault(field, fact)
        meta_objects = []
        for key, value in parser.meta.items():
            node = {key.split(':')[-1]: value}
            if any(key_name(part) in OFFICE_KEYS or part == 'business' for part in key.split(':')[:-1]):
                node = {'contact': node}
            meta_objects.append(node)
        for field, fact in structured_facts(meta_objects, "meta", postcode_candidates).items():
            facts.setdefault(field, fact)
        embedded = embedded_json_objects(parser.scripts)
        for field, fact in structured_facts(embedded, "embedded_json", postcode_candidates).items():
            facts.setdefault(field, fact)
        for how, objects in (("jsonld", jsonld), ("embedded_json", embedded)):
            for name, entry in page_extras(objects, how).items():
                page.setdefault(name, entry)
        text = visible_text(parser.text_parts)
    else:
        source["title"] = None
        source["canonical"] = None
        text = raw
    for field, fact in text_facts(text, postcode_candidates).items():
        facts.setdefault(field, fact)
    facts.pop('postcode', None)
    expected = address_outcodes(source.get("title"), facts["address"]["value"] if "address" in facts else None,
                                facts["outcode"]["value"] if "outcode" in facts else None) | bare_outcode_lines(text)
    selected, postcode_note = resolve_postcode(postcode_candidates, expected)
    if selected:
        facts['postcode'] = selected
        facts.setdefault('outcode', collections.OrderedDict([("value", selected['value'].split()[0]), ("unit", None),
                                                             ("how", selected['how']), ("quote", selected['quote'])]))
    elif 'outcode' not in facts and len(expected) == 1:
        facts['outcode'] = collections.OrderedDict([("value", next(iter(expected))), ("unit", None), ("how", "text"),
                                                    ("quote", "the district the address or title ends with; the full postcode is not stated")])
    known = list(STANDARD_KEYS.keys())
    return collections.OrderedDict([
        ("schema", "vet-flat/listing-fields/2"),
        ("source", source),
        ("fields", facts),
        ("unknown", [f for f in known if f not in facts]),
        ("postcode_candidates", postcode_candidates),
        ("postcode_note", postcode_note),
        ("page", page),
        ("page_note", PAGE_NOTE if page else None),
        ("note", "Values are what the page states; nothing here is verified against a register."),
    ])


def looks_like_url(text):
    return bool(URL_LIKE.match(text or ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="a saved page (.html) or text file, or - for stdin")
    ap.add_argument("--text", action="store_true", help="treat the input as pasted plain text, not HTML")
    args = ap.parse_args(argv)
    if looks_like_url(args.source):
        print(json.dumps({"error": REFUSAL}, ensure_ascii=False))
        return 2
    try:
        if args.source == "-":
            raw = getattr(sys.stdin, 'buffer', sys.stdin).read()
        else:
            with open(args.source, 'rb') as fh:
                raw = fh.read()
        raw = decode_saved_text(raw, args.source)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    if looks_like_url(raw):
        print(json.dumps({"error": REFUSAL}, ensure_ascii=False))
        return 2
    kind = "text" if args.text or "<" not in raw[:2000] else "html"
    print(json.dumps(extract(raw, kind), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
