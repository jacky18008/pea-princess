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
Nothing here is written for one website: no site names, no page selectors.

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

URL_LIKE = re.compile(r"^\s*(?:https?://|www\.)\S+\s*$", re.I)
POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b")
OUTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\b")
MONEY = r"£\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?"
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

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.title, self.canonical = "", None
        self.meta = collections.OrderedDict()
        self.scripts = []                       # (type, text)
        self.microdata = collections.OrderedDict()
        self.text_parts = []
        self._stack = []
        self._script_type = None
        self._itemprop = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._stack.append(tag)
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
        elif a.get("itemprop"):
            prop = a["itemprop"].strip()
            value = a.get("content") or a.get("datetime") or a.get("href")
            if value:
                self.microdata.setdefault(prop, value.strip())
            else:
                self._itemprop = prop
        if tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article", "dd", "dt"):
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._script_type = None
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        elif tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
        if tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "section", "article", "dd"):
            self.text_parts.append("\n")

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
                self.microdata.setdefault(self._itemprop, text)
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
        for start in [m.start() for m in re.finditer(r"\{", text)][:200]:
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


def walk(obj, found, path=""):
    """Collect standard keys anywhere in a nested object; first hit per field wins."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).replace("_", "").replace("-", "").lower()
            for field, names in STANDARD_KEYS.items():
                if lowered in names and field not in found:
                    if isinstance(value, dict):
                        scalar = value.get("value") if "value" in value else (value.get("price") or value.get("name"))
                        unit = value.get("unitCode") or value.get("unitText") or value.get("priceCurrency")
                        if scalar not in (None, ""):
                            found[field] = (scalar, unit, path + "/" + str(key))
                    elif isinstance(value, (str, int, float)) and str(value).strip():
                        found[field] = (value, None, path + "/" + str(key))
            walk(value, found, path + "/" + str(key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:50]):
            walk(item, found, path + "[%d]" % i)


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


def text_facts(text):
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
    m = POSTCODE.search(text)
    if m:
        put("postcode", (m.group(1) + " " + m.group(2)).upper(), None, m)
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
def structured_facts(objects, how):
    found = collections.OrderedDict()
    for obj in objects:
        walk(obj, found)
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
    return facts


def extract(raw, kind):
    """(record) for one saved page (kind 'html') or pasted text (kind 'text')."""
    facts = collections.OrderedDict()
    source = collections.OrderedDict([("kind", "saved_page" if kind == "html" else "pasted_text")])
    if kind == "html":
        parser = Collector()
        parser.feed(raw)
        source["title"] = re.sub(r"\s+", " ", parser.title).strip() or None
        source["canonical"] = parser.canonical or parser.meta.get("og:url")
        for field, fact in structured_facts(jsonld_objects(parser.scripts), "jsonld").items():
            facts.setdefault(field, fact)
        micro = collections.OrderedDict((k, v) for k, v in parser.microdata.items())
        for field, fact in structured_facts([micro], "microdata").items():
            facts.setdefault(field, fact)
        meta_obj = {k.split(":")[-1]: v for k, v in parser.meta.items()}
        for field, fact in structured_facts([meta_obj], "meta").items():
            facts.setdefault(field, fact)
        for field, fact in structured_facts(embedded_json_objects(parser.scripts), "embedded_json").items():
            facts.setdefault(field, fact)
        text = visible_text(parser.text_parts)
    else:
        source["title"] = None
        source["canonical"] = None
        text = raw
    for field, fact in text_facts(text).items():
        facts.setdefault(field, fact)
    known = list(STANDARD_KEYS.keys())
    return collections.OrderedDict([
        ("schema", "vet-flat/listing-fields/1"),
        ("source", source),
        ("fields", facts),
        ("unknown", [f for f in known if f not in facts]),
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
    if args.source == "-":
        raw = sys.stdin.read()
    else:
        if not os.path.exists(args.source):
            print(json.dumps({"error": "no such file: %s" % args.source}, ensure_ascii=False))
            return 2
        with io.open(args.source, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    if looks_like_url(raw):
        print(json.dumps({"error": REFUSAL}, ensure_ascii=False))
        return 2
    kind = "text" if args.text or "<" not in raw[:2000] else "html"
    print(json.dumps(extract(raw, kind), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
