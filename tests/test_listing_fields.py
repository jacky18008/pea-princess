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


class TestPropertyPostcode(unittest.TestCase):
    def assert_unknown(self, raw, kind='text'):
        rec = LF.extract(raw, kind)
        self.assertNotIn('postcode', rec['fields'])
        self.assertIn('postcode', rec['unknown'])
        self.assertTrue(rec['postcode_candidates'])
        self.assertTrue(rec['postcode_note'])
        return rec

    def test_pdf_style_office_footer_is_not_the_property_outcode(self):
        rec = self.assert_unknown('1 bedroom flat for rent, Example Road, N4\n£1,800 pcm\n'
                                  'Our local office\nExample Agency\n12 Demo Street\nLondon\nN8 1AA\nCall 020 0000 0000')
        self.assertEqual(1800, rec['fields']['rent']['value'])
        self.assertEqual('office', rec['postcode_candidates'][0]['role'])
        self.assertIn('Our local office', rec['postcode_candidates'][0]['quote'])
        self.assertNotIn('address', rec['fields'])

    def test_office_first_does_not_hide_explicit_property_address(self):
        rec = LF.extract('Our local office\nN8 1AA\nProperty address: 4 Sample Road, N4 2BB', 'text')
        self.assertEqual('N4 2BB', rec['fields']['postcode']['value'])
        self.assertIn('excluded', rec['postcode_note'])

    def test_property_first_survives_office_footer(self):
        rec = LF.extract('Property address: 4 Sample Road, N4 2BB\n£1,800 pcm\nOur local office\nN8 1AA', 'text')
        self.assertEqual('N4 2BB', rec['fields']['postcode']['value'])

    def test_unassigned_different_postcodes_remain_ambiguous(self):
        rec = self.assert_unknown('4 Sample Road, N4 2BB\n12 Demo Street, N8 1AA')
        self.assertIn('Conflicting', rec['postcode_note'])
        self.assertEqual(2, len(rec['postcode_candidates']))

    def test_jsonld_agent_address_does_not_win_before_dwelling(self):
        obj = {'@type': 'RealEstateListing', 'agent': {'@type': 'RealEstateAgent', 'address':
               {'streetAddress': '12 Demo Street', 'postalCode': 'N8 1AA'}},
               'about': {'@type': 'Apartment', 'address': {'streetAddress': '4 Sample Road', 'postalCode': 'N4 2BB'}}}
        rec = LF.extract('<script type="application/ld+json">'+json.dumps(obj)+'</script>', 'html')
        self.assertEqual('N4 2BB', rec['fields']['postcode']['value'])
        self.assertEqual('4 Sample Road', rec['fields']['address']['value'])
        self.assertIn('/agent/address/postalCode', rec['postcode_candidates'][0]['quote'])

    def test_jsonld_organization_only_is_not_a_property(self):
        rec = self.assert_unknown('<script type="application/ld+json">'+json.dumps(
            {'@type':'Organization', 'address': {'streetAddress':'12 Demo Street', 'postalCode':'N8 1AA'}})+'</script>', 'html')
        self.assertNotIn('address', rec['fields'])

    def test_embedded_children_do_not_lose_agent_scope(self):
        raw = '<script>window.data = '+json.dumps({'agentData': {'address':
            {'streetAddress':'12 Demonstration Street, London', 'postalCode':'N8 1AA'}}})+';</script>'
        rec = self.assert_unknown(raw, 'html')
        self.assertTrue(all(c['role']=='office' for c in rec['postcode_candidates']))
        self.assertNotIn('address', rec['fields'])

    def test_microdata_office_scope_and_whitespace_normalization(self):
        for tag in ('<span itemprop="postalCode">n81aa</span>', '<meta itemprop="postalCode" content="N8 1AA">'):
            with self.subTest(tag=tag):
                rec = self.assert_unknown('<div itemscope itemtype="https://schema.org/RealEstateAgent">'+tag+'</div>', 'html')
                self.assertTrue(any(c['role']=='office' and c['value']=='N8 1AA' for c in rec['postcode_candidates']))

    def test_microdata_property_sibling_is_not_inherited_office_scope(self):
        raw = ('<div itemscope itemtype="https://schema.org/RealEstateAgent"><span itemprop="postalCode">N8 1AA</span></div>'
               '<div itemscope itemtype="https://schema.org/Apartment"><span itemprop="postalCode">N4 2BB</span></div>')
        self.assertEqual('N4 2BB', LF.extract(raw, 'html')['fields']['postcode']['value'])

    def test_void_agent_link_does_not_leak_scope_into_property_microdata(self):
        raw = ('<div itemscope itemtype="https://schema.org/Apartment">'
               '<link itemprop="agent" href="https://example.invalid/agent">'
               '<span itemprop="postalCode">N4 2BB</span></div>')
        self.assertEqual('N4 2BB', LF.extract(raw, 'html')['fields']['postcode']['value'])

    def test_contact_metadata_is_not_a_property_postcode(self):
        self.assert_unknown('<meta property="business:contact_data:postal_code" content="N8 1AA">', 'html')

    def test_structured_and_visible_property_conflict_is_retained(self):
        raw = '<script type="application/ld+json">'+json.dumps({'@type':'Apartment','address':{'postalCode':'N4 2BB'}})+'</script><p>Property postcode: N8 1AA</p>'
        self.assertIn('Conflicting', self.assert_unknown(raw,'html')['postcode_note'])

    def test_partial_structured_postcode_is_not_a_full_property_location(self):
        self.assert_unknown('<script type="application/ld+json">'+json.dumps({'@type':'Apartment','address':{'postalCode':'N4'}})+'</script>', 'html')


class TestBinaryInput(unittest.TestCase):
    def run_file(self, body, suffix='.txt', flags=()):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'saved'+suffix)
            with open(path, 'wb') as handle:
                handle.write(body)
            return subprocess.run([sys.executable, os.path.join(SCRIPTS, 'listing_fields.py'), *flags, path], capture_output=True)

    def assert_format_error(self, result):
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        rec = json.loads(result.stdout)
        self.assertEqual({'error'}, set(rec))
        self.assertIn('pdftotext -layout', rec['error'])
        self.assertIn('UTF-8', rec['error'])
        self.assertNotIn('postcode_candidates', rec)
        self.assertEqual(b'', result.stderr)

    def test_raw_pdf_is_refused_even_when_its_stream_looks_like_listing_text(self):
        self.assert_format_error(self.run_file(b'%PDF-1.7\n1 0 obj <</Text (N8 1AA 2 bedrooms)>>\n%%EOF', '.pdf'))

    def test_pdf_magic_is_refused_under_text_name_and_text_flag(self):
        self.assert_format_error(self.run_file(b'%PDF-1.7\nN8 1AA 2 bedrooms', '.txt', ('--text',)))

    def test_pdf_stdin_is_rejected_before_any_fields_are_returned(self):
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'listing_fields.py'), '--text', '-'],
                                input=b'%PDF-1.7\nN8 1AA 2 bedrooms', capture_output=True)
        self.assert_format_error(result)

    def test_common_binary_magics_are_rejected_regardless_of_extension(self):
        for magic in (b'\x89PNG\r\n\x1a\n', b'GIF89a', b'PK\x03\x04', b'RIFF', b'\xff\xd8\xff'):
            with self.subTest(magic=magic):
                self.assert_format_error(self.run_file(magic+b'N8 1AA 2 bedrooms', '.txt'))

    def test_invalid_utf8_and_binary_controls_are_not_replaced_with_text(self):
        for raw in (b'N8 1AA\xff2 bedrooms', b'N8 1AA\x002 bedrooms'):
            with self.subTest(raw=raw):
                self.assert_format_error(self.run_file(raw))

    def test_utf8_plain_text_stdin_still_parses_rent_and_postcode(self):
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'listing_fields.py'), '--text', '-'],
                                input='£1,800 pcm\nProperty postcode: N4 2BB\f'.encode('utf-8'), capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        rec = json.loads(result.stdout)
        self.assertEqual(1800, rec['fields']['rent']['value'])
        self.assertEqual('N4 2BB', rec['fields']['postcode']['value'])


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
