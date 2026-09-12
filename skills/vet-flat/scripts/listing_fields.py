#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fields out of a listing page the user already saved or pasted. This tool never fetches.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

Give it a file the person saved from their own browser (HTML or plain text) or paste
the page text on stdin, and it prints the facts a listing states - rent and period,
bedrooms, bathrooms, floor, floor area, postcode, address, availability, furnishing,
deposit, EPC and council tax band - each with the sentence it was read in, so every
value can be checked against the page.

How it reads, in order of trust:
  1. schema.org JSON-LD blocks (``<script type="application/ld+json">``)
  2. microdata (``itemprop=...``) and Open Graph / meta tags
  3. any JSON object embedded in a script block that happens to carry the same
     standard keys (price, numberOfRooms, floorSize, postalCode ...)
  4. the visible text, with plain-language patterns ("£1,800 pcm", "2 bedrooms",
     "3rd floor", "540 sq ft", a UK postcode)
Postcodes retain candidates and office/entity context across these layers; conflicting
possible property postcodes stay unknown rather than taking the first hit. These
context clues do not establish a verified property address.
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
OFFICE_WORDS = re.compile(r"\b(?:office|branch|agency|registered address|contact details|contact us|(?:estate|letting|lettings) agents?)\b", re.I)
PROPERTY_LABEL = re.compile(r"\b(?:property|listing|flat|apartment|house)\s+(?:address|postcode|location)\b", re.I)
OFFICE_KEYS = frozenset(('agent', 'agents', 'agency', 'agentdetails', 'estateagent', 'realestateagent',
                         'office', 'branch', 'broker', 'seller', 'provider', 'publisher', 'author',
                         'contact', 'contactdetails', 'contactdata', 'agentoffice', 'agentdata', 'agentaddress', 'officeaddress', 'branchaddress', 'organization', 'organisation'))
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
STANDARD_KEYS = {
    "rent": ("price", "rent", "rentpcm", "rent_pcm", "monthlyrent", "pricepcm", "amount"),
    "bedrooms": ("numberofbedrooms", "numberofrooms", "bedrooms", "beds"),
    "bathrooms": ("numberofbathroomstotal", "numberofbathrooms", "bathrooms"),
    "floor_area": ("floorsize", "floorarea", "area", "size"),
    "postcode": ("postalcode", "postcode"),
    "address": ("streetaddress", "displayaddress", "address"),
    "floor": ("floorlevel", "floor"),
    "available_from": ("availablefrom", "availabilitystarts", "availabledate", "letavailabledate"),
    "furnished": ("furnishtype", "furnished", "furnishing"),
    "deposit": ("deposit", "securitydeposit"),
    "epc": ("epcrating", "energyrating", "epc"),
    "council_tax_band": ("counciltaxband",),
}


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

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        role = entity_role({'@type': (a.get('itemtype') or '').split()}, self._roles[-1] if self._roles else 'unassigned')
        if key_name(a.get('itemprop', '')) in OFFICE_KEYS:
            role = 'office'
        if tag not in self.VOID:
            self._stack.append(tag)
            self._roles.append(role)
        if tag == "title":
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
        if tag == "title":
            self._in_title = False
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
                                out.append(obj)
                        break
            if len(out) >= limit:
                return out
    return out


def walk(obj, found, path="", postcode_candidates=None, role="unassigned"):
    """Collect standard fields, retaining postcode candidates with their entity scope."""
    if isinstance(obj, dict):
        role = entity_role(obj, role)
        for key, value in obj.items():
            lowered = str(key).replace("_", "").replace("-", "").lower()
            for field, names in STANDARD_KEYS.items():
                if lowered in names and field == 'postcode' and postcode_candidates is not None:
                    if isinstance(value, (str, int, float)):
                        postcode_candidates.append({'value': str(value).strip().upper(), 'role': role,
                            'quote': '%s at %s/%s' % (json.dumps(value, ensure_ascii=False), path, key)})
                    continue
                if lowered in names and field not in found and not (role == 'office' and field in ('address', 'postcode')):
                    if isinstance(value, dict):
                        scalar = value.get("value") if "value" in value else (value.get("price") or value.get("name"))
                        unit = value.get("unitCode") or value.get("unitText") or value.get("priceCurrency")
                        if scalar not in (None, ""):
                            found[field] = (scalar, unit, path + "/" + str(key))
                    elif isinstance(value, (str, int, float)) and str(value).strip():
                        found[field] = (value, None, path + "/" + str(key))
            walk(value, found, path + "/" + str(key), postcode_candidates, "office" if lowered in OFFICE_KEYS else role)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:50]):
            walk(item, found, path + "[%d]" % i, postcode_candidates, role)


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


def resolve_postcode(candidates):
    """An office is not the dwelling; conflicting plausible postcodes stay unknown."""
    for candidate in candidates:
        match = POSTCODE.fullmatch(candidate['value'])
        if match:
            candidate['value'] = (match.group(1) + ' ' + match.group(2)).upper()
    office_values = {c['value'] for c in candidates if c['role'] == 'office'}
    usable = []
    for candidate in candidates:
        match = POSTCODE.fullmatch(candidate['value'])
        if not match or candidate['role'] == 'office':
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
    m = re.search(r"\b(\d+|one|two|three|four|five|six|studio)\s*[- ]?(?:bed(?:room)?s?)\b", text, re.I)
    if m:
        raw = m.group(1).lower()
        put("bedrooms", float(WORD_NUM[raw]) if raw in WORD_NUM else number(raw), "count", m)
    m = re.search(r"\b(\d+|one|two|three)\s*[- ]?(?:bath(?:room)?s?)\b", text, re.I)
    if m:
        raw = m.group(1).lower()
        put("bathrooms", float(WORD_NUM[raw]) if raw in WORD_NUM else number(raw), "count", m)
    m = re.search(r"\b(lower ground|ground|basement|top|penthouse)\s+floor\b|\b(\d{1,2})(?:st|nd|rd|th)\s+floor\b", text, re.I)
    if m:
        if m.group(2):
            put("floor", number(m.group(2)), "UK_floor", m)
        else:
            word = m.group(1).lower()
            put("floor", {"ground": 0.0, "lower ground": -1.0, "basement": -1.0}.get(word, word), "UK_floor", m)
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(sq\.?\s*ft|square\s*feet|sqft|ft²)\b", text, re.I)
    if m:
        put("floor_area", number(m.group(1)), "sq_ft", m)
    else:
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(m²|sq\.?\s*m\b|sqm|square\s*met(?:re|er)s?)", text, re.I)
        if m:
            put("floor_area", number(m.group(1)), "m2", m)
    candidates = text_postcodes(text)
    if postcode_candidates is not None:
        postcode_candidates.extend(candidates)
    selected, _ = resolve_postcode(candidates)
    if selected:
        facts['postcode'] = selected
    m = re.search(r"available\s+(?:from\s+)?(now|immediately|\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", text, re.I)
    if m:
        put("available_from", m.group(1), None, m)
    m = re.search(r"\b(part[- ]furnished|unfurnished|furnished)\b", text, re.I)
    if m:
        put("furnished", m.group(1).lower(), None, m)
    m = re.search(r"deposit[^£\n]{0,40}" + MONEY, text, re.I)
    if m:
        put("deposit", number(m.group(1)), "GBP", m)
    m = re.search(r"\bEPC(?:\s*rating)?[^A-G\n]{0,12}\b([A-G])\b", text)
    if m:
        put("epc", m.group(1), "band", m)
    m = re.search(r"council\s*tax(?:\s*band)?[^A-H\n]{0,12}\b([A-H])\b", text, re.I)
    if m:
        put("council_tax_band", m.group(1).upper(), "band", m)
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
        # "4th floor", "540 sq ft", "£1,595 pcm": a string with its unit inside is read
        # with the same plain-language patterns as the visible text.
        if isinstance(value, str) and field in ("rent", "bedrooms", "bathrooms", "floor", "floor_area", "deposit"):
            sub = text_facts(value)
            if field in sub:
                value, unit = sub[field]["value"], sub[field]["unit"]
        if field == "rent":
            value = number(value)
            unit = unit or "GBP/month"
        elif field in ("bedrooms", "bathrooms", "floor", "deposit"):
            value = number(value) if number(value) is not None else value
            unit = unit or {"bedrooms": "count", "bathrooms": "count", "floor": "UK_floor", "deposit": "GBP"}[field]
        elif field == "floor_area":
            value = number(value) if number(value) is not None else value
            unit = {"MTK": "m2", "FTK": "sq_ft"}.get(str(unit), unit) or "m2"
        elif field == "postcode":
            value = str(value).strip().upper()
        if value is None:
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
    source = collections.OrderedDict([("kind", "saved_page" if kind == "html" else "pasted_text")])
    if kind == "html":
        parser = Collector()
        parser.feed(raw)
        source["title"] = re.sub(r"\s+", " ", parser.title).strip() or None
        source["canonical"] = parser.canonical or parser.meta.get("og:url")
        for field, fact in structured_facts(jsonld_objects(parser.scripts), "jsonld", postcode_candidates).items():
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
        for field, fact in structured_facts(embedded_json_objects(parser.scripts), "embedded_json", postcode_candidates).items():
            facts.setdefault(field, fact)
        text = visible_text(parser.text_parts)
    else:
        source["title"] = None
        source["canonical"] = None
        text = raw
    for field, fact in text_facts(text, postcode_candidates).items():
        facts.setdefault(field, fact)
    facts.pop('postcode', None)
    selected, postcode_note = resolve_postcode(postcode_candidates)
    if selected:
        facts['postcode'] = selected
    known = list(STANDARD_KEYS.keys())
    return collections.OrderedDict([
        ("schema", "vet-flat/listing-fields/1"),
        ("source", source),
        ("fields", facts),
        ("unknown", [f for f in known if f not in facts]),
        ("postcode_candidates", postcode_candidates),
        ("postcode_note", postcode_note),
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
