# -*- coding: utf-8 -*-
"""scripts/listing_fields.py: fields out of a page the person saved or pasted; never a fetch.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

The fixtures are synthetic pages with standard markup (schema.org JSON-LD, microdata,
Open Graph, an embedded JSON blob, plain text). No real listing page is stored here.
"""
from __future__ import unicode_literals

import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import listing_fields as LF  # noqa: E402

JSONLD_PAGE = """<!doctype html><html><head><title>1 bedroom flat to rent, Example Road</title>
<link rel="canonical" href="https://example.invalid/listing/12345">
<meta property="og:url" content="https://example.invalid/listing/12345">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"RealEstateListing","name":"1 bedroom flat",
 "offers":{"@type":"Offer","price":"1850","priceCurrency":"GBP"},
 "about":{"@type":"Apartment","numberOfBedrooms":1,"numberOfBathroomsTotal":1,
          "floorSize":{"@type":"QuantitativeValue","value":48.5,"unitCode":"MTK"},
          "floorLevel":"3",
          "address":{"@type":"PostalAddress","streetAddress":"12 Example Road","postalCode":"SE1 8BW","addressLocality":"London"}}}
</script></head><body><h1>1 bedroom flat to rent</h1><p>£1,850 pcm. Available from 1st October 2026. Furnished.</p>
<p>Deposit: £2,134. EPC rating C. Council tax band D.</p></body></html>"""

MICRODATA_PAGE = """<html><head><title>Studio to rent</title></head><body>
<div itemscope itemtype="https://schema.org/Accommodation">
 <span itemprop="numberOfRooms">2</span> bedrooms
 <span itemprop="floorSize">540 sq ft</span>
 <span itemprop="postalCode">E1 2FX</span>
 <meta itemprop="price" content="2300">
</div><p>Second floor flat, unfurnished, £2,300 per month.</p></body></html>"""

EMBEDDED_PAGE = """<html><head><title>Flat</title>
<script>window.pageModel = {"propertyData":{"prices":{"primaryPrice":"£1,595 pcm"},"bedrooms":2,"bathrooms":1,
 "address":{"displayAddress":"Flat 4, 9 Sample Street, London","postcode":"N4 2ZB"},
 "sizings":[{"unit":"sqft","minimumSize":610}],"floorLevel":"4th floor"}};</script></head>
<body><div>2 bedroom apartment</div><div>£1,595 pcm</div><div>4th floor · 610 sq ft</div></body></html>"""

PASTED_TEXT = """2 bedroom flat to rent
£2,150 pcm
Ground floor, 62 m², part-furnished. Available 15 November 2026.
Deposit £2,480. EPC B. Council tax band E. Postcode SW9 8HP."""


class TestReading(unittest.TestCase):
    def test_jsonld_wins_and_carries_where_it_was_read(self):
        rec = LF.extract(JSONLD_PAGE, "html")
        f = rec["fields"]
        self.assertEqual(1850.0, f["rent"]["value"]); self.assertEqual("jsonld", f["rent"]["how"])
        self.assertEqual(1.0, f["bedrooms"]["value"])
        self.assertEqual(48.5, f["floor_area"]["value"]); self.assertEqual("m2", f["floor_area"]["unit"])
        self.assertEqual("SE1 8BW", f["postcode"]["value"])
        self.assertEqual(3.0, f["floor"]["value"])
        self.assertEqual("https://example.invalid/listing/12345", rec["source"]["canonical"])
        self.assertEqual("1 bedroom flat to rent, Example Road", rec["source"]["title"])
        # things only the visible text carried
        self.assertEqual("1st October 2026", f["available_from"]["value"])
        self.assertEqual("furnished", f["furnished"]["value"])
        self.assertEqual(2134.0, f["deposit"]["value"])
        self.assertEqual("C", f["epc"]["value"]); self.assertEqual("D", f["council_tax_band"]["value"])
        self.assertIn("EPC rating C", f["epc"]["quote"])

    def test_microdata_and_visible_text(self):
        f = LF.extract(MICRODATA_PAGE, "html")["fields"]
        self.assertEqual(2.0, f["bedrooms"]["value"]); self.assertEqual("microdata", f["bedrooms"]["how"])
        self.assertEqual("E1 2FX", f["postcode"]["value"])
        self.assertEqual(2300.0, f["rent"]["value"])
        self.assertEqual(540.0, f["floor_area"]["value"]); self.assertEqual("sq_ft", f["floor_area"]["unit"])
        self.assertEqual("unfurnished", f["furnished"]["value"])

    def test_an_embedded_json_blob_is_read_by_its_standard_keys(self):
        f = LF.extract(EMBEDDED_PAGE, "html")["fields"]
        self.assertEqual(2.0, f["bedrooms"]["value"]); self.assertEqual("embedded_json", f["bedrooms"]["how"])
        self.assertEqual("N4 2ZB", f["postcode"]["value"])
        self.assertEqual(1595.0, f["rent"]["value"])          # from the visible text
        self.assertEqual(4.0, f["floor"]["value"])
        self.assertEqual(610.0, f["floor_area"]["value"])

    def test_pasted_text_alone(self):
        rec = LF.extract(PASTED_TEXT, "text")
        f = rec["fields"]
        self.assertEqual("pasted_text", rec["source"]["kind"])
        self.assertEqual(2150.0, f["rent"]["value"]); self.assertEqual("GBP/month", f["rent"]["unit"])
        self.assertEqual(0.0, f["floor"]["value"])
        self.assertEqual(62.0, f["floor_area"]["value"]); self.assertEqual("m2", f["floor_area"]["unit"])
        self.assertEqual("part-furnished", f["furnished"]["value"])
        self.assertEqual("SW9 8HP", f["postcode"]["value"])
        self.assertEqual("B", f["epc"]["value"]); self.assertEqual("E", f["council_tax_band"]["value"])
        self.assertEqual([], [u for u in rec["unknown"] if u in ("rent", "bedrooms", "postcode")])

    def test_weekly_rent_keeps_its_period(self):
        f = LF.extract("Lovely room, £320 pw, bills included. Available now.", "text")["fields"]
        self.assertEqual(320.0, f["rent"]["value"]); self.assertEqual("GBP/week", f["rent"]["unit"])
        self.assertEqual("now", f["available_from"]["value"])

    def test_missing_things_are_listed_as_unknown_not_guessed(self):
        rec = LF.extract("A flat. Call to arrange a viewing.", "text")
        self.assertEqual({}, dict(rec["fields"]))
        self.assertIn("rent", rec["unknown"])


class TestItNeverFetches(unittest.TestCase):
    """The rule that keeps this tool on the Amstrad side of the line: no network code, and
    a web address is refused with an instruction to save the page instead."""

    def test_no_network_module_is_imported(self):
        with io.open(os.path.join(SCRIPTS, "listing_fields.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        banned = {"urllib", "http", "socket", "ssl", "requests", "httpx", "aiohttp", "subprocess",
                  "selenium", "playwright", "webbrowser", "ftplib", "smtplib", "xmlrpc"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(set(), imported & banned, imported & banned)
        self.assertNotIn("_fetch", imported)

    def test_a_url_argument_is_refused_with_the_save_instruction(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "listing_fields.py"),
                               "https://example.invalid/listing/1"], capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)
        self.assertIn("does not open web pages", proc.stdout)
        self.assertIn("save the page", proc.stdout)

    def test_a_pasted_bare_url_is_refused_too(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "listing_fields.py"), "-"],
                              input="www.example.invalid/listing/1\n", capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)
        self.assertIn("does not open web pages", proc.stdout)

    def test_a_saved_file_is_read_and_printed_as_json(self):
        folder = tempfile.mkdtemp(prefix="vetflat-listing-")
        path = os.path.join(folder, "page.html")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(JSONLD_PAGE)
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "listing_fields.py"), path],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        rec = json.loads(proc.stdout)
        self.assertEqual("vet-flat/listing-fields/1", rec["schema"])
        self.assertEqual(1850.0, rec["fields"]["rent"]["value"])

    def test_no_site_is_named_in_the_module(self):
        with io.open(os.path.join(SCRIPTS, "listing_fields.py"), encoding="utf-8") as fh:
            source = fh.read().lower()
        for name in ("rightmove", "zoopla", "onthemarket", "openrent", "spareroom", "airbnb", "booking.com"):
            self.assertNotIn(name, source, name)


if __name__ == "__main__":
    unittest.main()
