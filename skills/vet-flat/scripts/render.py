#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn a vet-flat report.json into the fixed report layout.

The standard is `references/report-schema.json`, not the HTML: models emit JSON,
this script decides the layout. `viewer/viewer.html` renders the same sections in
the same order in a browser, from the same JSON and the same glossary.

Not a network tool. Standard library only, Python 3.9.

Usage:
  render.py report.json                  > report.html
  render.py report.json --lang zh-TW     > report.zh-TW.html
  render.py report.json --md             > report.md
  render.py report.json --validate-only            # check, print nothing

Exit codes: 0 ok, 1 the report failed validation, 2 wrong arguments.
Errors and warnings go to stderr; the report goes to stdout.
"""
from __future__ import unicode_literals

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")
DEFAULT_SCHEMA = os.path.join(REFS, "report-schema.json")
DEFAULT_GLOSSARY = os.path.join(REFS, "glossary.yaml")

FOOTER_TEMPLATE = "Generated with vet-flat {version} \u2014 {url}"
DEFAULT_SOURCE_URL = "https://github.com/jacky18008/pea-princess"

# The ten sections, in order. (glossary id, html anchor)
SECTIONS = [
    ("section.verdict", "verdict"),
    ("section.hard_filters", "hard-filters"),
    ("section.comparison", "comparison"),
    ("section.worst_reviews", "worst-reviews"),
    ("section.landmines", "landmines"),
    ("section.axes", "axes"),
    ("section.questions", "questions"),
    ("section.gaps", "gaps"),
    ("section.sources", "sources"),
    ("section.about", "about"),
]

METRIC_KEYS = [
    ("price_per_sqft_epc", "ui.price_per_sqft"),
    ("crime_6mo_count", "ui.crime_6mo"),
    ("commute_min", "ui.commute"),
    ("commute_redundancy_grade", "ui.redundancy"),
    ("management_organic_score", "ui.organic_score"),
    ("management_incentivised_share", "ui.incentivised_share"),
    ("nearest_works_m", "ui.nearest_works"),
    ("landlord_type", "ui.landlord_type"),
]

COST_KEYS = [
    ("rent_pcm", "ui.rent_pcm"),
    ("bills_low", "ui.bills_low"),
    ("bills_planning", "ui.bills_planning"),
    ("bills_stress", "ui.bills_stress"),
    ("council_tax", "ui.council_tax"),
    ("all_in_planning", "ui.all_in_planning"),
]

PROFILE_KEYS = [
    "min_floor_area_sqft", "max_building_age_years", "rent_pcm_target", "all_in_pcm_ceiling",
    "move_in_earliest", "move_in_latest", "commute_destination", "commute_max_min",
    "reject_ground_floor", "must_haves", "guarantor_route", "notes",
]


# --------------------------------------------------------------- glossary ---
class GlossaryError(Exception):
    pass


def parse_mini_yaml(text):
    """Parse the deliberately tiny subset of YAML used by glossary.yaml.

    Rules: two-space indent, three levels, every scalar is a double-quoted JSON
    string on one line, a line whose first non-space character is # is a comment.
    """
    root = {}
    stack = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise GlossaryError("line %d: indent must be a multiple of 2" % lineno)
        line = raw.strip()
        if ":" not in line:
            raise GlossaryError("line %d: expected 'key:' or 'key: \"value\"'" % lineno)
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise GlossaryError("line %d: indentation does not close" % lineno)
        parent = stack[-1][1]
        if rest == "":
            node = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            if not rest.startswith('"'):
                raise GlossaryError("line %d: values must be double-quoted" % lineno)
            try:
                value, _ = json.JSONDecoder().raw_decode(rest)
            except ValueError:
                raise GlossaryError("line %d: value is not a valid quoted string" % lineno)
            parent[key] = value
    return root


def load_glossary(path):
    with io.open(path, encoding="utf-8") as fh:
        doc = parse_mini_yaml(fh.read())
    terms = doc.get("terms")
    if not isinstance(terms, dict):
        raise GlossaryError("%s has no 'terms' map" % path)
    return terms


class Labels(object):
    """Look a label or a plain-language gloss up in the reader's language."""

    def __init__(self, terms, lang):
        self.terms = terms
        self.lang = lang or "en"
        self.chain = self._chain(self.lang)

    @staticmethod
    def _chain(lang):
        out = [lang]
        if "-" in lang:
            out.append(lang.split("-")[0])
        # zh-HK / zh-MO readers get traditional; bare zh gets simplified.
        if lang.lower().startswith("zh") and "zh-TW" not in out:
            out.append("zh-TW" if lang.lower() in ("zh-hk", "zh-mo", "zh-hant") else "zh-CN")
        out.append("en")
        return out

    def label(self, term_id, default=None):
        entry = self.terms.get(term_id)
        if not entry:
            return default if default is not None else term_id
        for lang in self.chain:
            if entry.get(lang):
                return entry[lang]
        return default if default is not None else term_id

    def plain(self, term_id, default=""):
        entry = self.terms.get(term_id)
        if not entry:
            return default
        for lang in self.chain:
            got = entry.get("plain-" + lang)
            if got:
                return got
        return entry.get("plain", default)

    def tip(self, term_id):
        """What to show on hover: the original jargon plus the plain sentence."""
        entry = self.terms.get(term_id) or {}
        bits = [b for b in (entry.get("term"), self.plain(term_id)) if b]
        return " \u2014 ".join(bits)


# -------------------------------------------------------------- validation ---
TYPE_MAP = {
    "object": dict, "array": list, "string": str,
    "boolean": bool, "null": type(None),
}


def _is_type(value, name):
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    py = TYPE_MAP.get(name)
    if py is None:
        return True
    if py is str:
        return isinstance(value, str)
    return isinstance(value, py) and not isinstance(value, bool) if py is not bool else isinstance(value, bool)


class Validator(object):
    """A small JSON Schema draft-07 checker: enough for this one schema.

    Understands $ref, type, enum, const, required, properties,
    additionalProperties (false becomes a warning), items, minItems, maxItems,
    minLength, maxLength, minimum, maximum and pattern.
    """

    def __init__(self, schema):
        self.schema = schema
        self.errors = []
        self.warnings = []

    def _resolve(self, node):
        seen = 0
        while isinstance(node, dict) and "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/"):
                return node
            target = self.schema
            for part in ref[2:].split("/"):
                target = target.get(part, {})
            node = target
            seen += 1
            if seen > 20:
                break
        return node

    def err(self, path, message):
        self.errors.append("%s: %s" % (path or "(root)", message))

    def warn(self, path, message):
        self.warnings.append("%s: %s" % (path or "(root)", message))

    def check(self, value, schema, path=""):
        schema = self._resolve(schema)
        if not isinstance(schema, dict):
            return
        if "type" in schema:
            names = schema["type"]
            if isinstance(names, str):
                names = [names]
            if not any(_is_type(value, n) for n in names):
                self.err(path, "must be %s, got %s" % (" or ".join(names), type(value).__name__))
                return
        if "enum" in schema and value not in schema["enum"]:
            self.err(path, "must be one of %s, got %r" % (json.dumps(schema["enum"], ensure_ascii=False), value))
        if "const" in schema and value != schema["const"]:
            self.err(path, "must be %r, got %r" % (schema["const"], value))
        if isinstance(value, str):
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                self.err(path, "is %d characters, the limit is %d" % (len(value), schema["maxLength"]))
            if "minLength" in schema and len(value) < schema["minLength"]:
                self.err(path, "is empty or too short (minimum %d characters)" % schema["minLength"])
            if "pattern" in schema and not re.search(schema["pattern"], value):
                self.err(path, "does not match the required format %s (got %r)" % (schema["pattern"], value))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                self.err(path, "must be at least %s, got %s" % (schema["minimum"], value))
            if "maximum" in schema and value > schema["maximum"]:
                self.err(path, "must be at most %s, got %s" % (schema["maximum"], value))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                self.err(path, "needs at least %d entries, got %d" % (schema["minItems"], len(value)))
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                self.err(path, "allows at most %d entries, got %d" % (schema["maxItems"], len(value)))
            if "items" in schema:
                for i, item in enumerate(value):
                    self.check(item, schema["items"], "%s[%d]" % (path, i))
        if isinstance(value, dict):
            props = schema.get("properties") or {}
            for name in schema.get("required", []):
                if name not in value:
                    self.err(path, "is missing the required key '%s'" % name)
            for name, sub in value.items():
                if name in props:
                    self.check(sub, props[name], "%s.%s" % (path, name) if path else name)
                elif schema.get("additionalProperties") is False:
                    self.warn(path, "has an unexpected key '%s'; the renderers ignore it" % name)


def semantic_checks(data, v):
    """The rules that a schema cannot state, in the words the model needs."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return
    ids = []
    for i, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue
        path = "candidates[%d]" % i
        cid = cand.get("id")
        if cid in ids:
            v.err(path, "reuses the id %r; every candidate needs its own id" % cid)
        ids.append(cid)
        axes = cand.get("axes")
        if isinstance(axes, list):
            axis_ids = [a.get("id") for a in axes if isinstance(a, dict)]
            if sorted([a for a in axis_ids if isinstance(a, int)]) != list(range(1, 13)):
                v.err(path + ".axes",
                      "must be exactly 12 entries with ids 1 to 12, each once. Got ids %s" % (axis_ids,))
        kq = cand.get("killer_questions")
        if isinstance(kq, list) and len(kq) > 2:
            v.err(path + ".killer_questions",
                  "has %d questions; at most 2 are allowed. Keep the two that would change the verdict." % len(kq))
        verdict = cand.get("verdict") or {}
        status = verdict.get("status")
        if status == "CONDITIONAL" and not verdict.get("conditions"):
            v.err(path + ".verdict", "status CONDITIONAL needs at least one entry in conditions")
        if status == "EDGE" and verdict.get("break_even_rent_pcm") in (None, ""):
            v.err(path + ".verdict", "status EDGE needs break_even_rent_pcm, the rent at which this becomes worth taking")
        if status == "KILL" and not verdict.get("fatal_axis"):
            v.err(path + ".verdict", "status KILL needs fatal_axis, the number of the axis that killed it")
        codes = set(verdict.get("reason_codes") or [])
        found = set(l.get("code") for l in (cand.get("landmines") or []) if isinstance(l, dict))
        for code in sorted(codes - found):
            v.warn(path + ".verdict.reason_codes",
                   "%s is given as a reason but there is no landmine entry with that code" % code)
        if len(candidates) > 1 and not cand.get("metrics"):
            v.warn(path, "has no metrics, so it will be blank in the side-by-side table")

    comparison = data.get("comparison")
    if len(candidates) > 1:
        if not comparison:
            v.err("comparison", "is required when there is more than one candidate")
        else:
            ranked = [r.get("candidate_id") for r in (comparison.get("ranking") or []) if isinstance(r, dict)]
            for cid in ids:
                if cid not in ranked:
                    v.err("comparison.ranking", "does not rank candidate %r" % cid)
            for cid in ranked:
                if cid not in ids:
                    v.err("comparison.ranking", "ranks %r, which is not a candidate id" % cid)
    elif comparison:
        v.warn("comparison", "is present but there is only one candidate; it will not be shown")

    known = set()
    for i, src in enumerate(data.get("sources") or []):
        if not isinstance(src, dict):
            continue
        sid = src.get("id")
        if sid in known:
            v.err("sources[%d]" % i, "reuses the id %r" % sid)
        known.add(sid)

    def walk(node, path):
        if isinstance(node, dict):
            for key, sub in node.items():
                if key == "sources" and isinstance(sub, list) and all(isinstance(x, str) for x in sub):
                    for sid in sub:
                        if sid not in known:
                            v.warn(path, "cites source %r, which is not in the top-level sources list" % sid)
                else:
                    walk(sub, "%s.%s" % (path, key) if path else key)
        elif isinstance(node, list):
            for i, sub in enumerate(node):
                walk(sub, "%s[%d]" % (path, i))

    walk(data.get("candidates"), "candidates")
    walk(data.get("comparison"), "comparison")


def validate(data, schema):
    v = Validator(schema)
    v.check(data, schema, "")
    semantic_checks(data, v)
    return v.errors, v.warnings


# ------------------------------------------------------------------ helpers ---
def esc(text):
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt_value(value, unit=None):
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = ("%.2f" % value).rstrip("0").rstrip(".")
    elif isinstance(value, int):
        text = "{:,}".format(value)
    else:
        text = str(value)
    if unit:
        text = "%s %s" % (text, unit)
    return text


def money(value):
    if value is None:
        return None
    return "\u00a3{:,.0f}".format(value) if isinstance(value, (int, float)) else str(value)


def footer_text(data):
    gb = data.get("generated_by") or {}
    return FOOTER_TEMPLATE.format(version=gb.get("version") or "unknown",
                                  url=gb.get("source_url") or DEFAULT_SOURCE_URL)


def candidate_name(cand):
    return ((cand.get("identity") or {}).get("display_name")
            or cand.get("id") or "?")


def profile_rows(snapshot, L):
    rows = []
    seen = set()
    for key in PROFILE_KEYS:
        if key in snapshot:
            seen.add(key)
            rows.append((key, snapshot[key]))
    for key in sorted(snapshot):
        if key not in seen:
            rows.append((key, snapshot[key]))
    out = []
    for key, value in rows:
        if value is None or value == [] or value == "":
            continue
        if isinstance(value, list):
            text = "; ".join(str(x) for x in value)
        elif isinstance(value, bool):
            text = L.label("ui.yes") if value else L.label("ui.no")
        else:
            text = str(value)
        out.append((key.replace("_", " "), text))
    return out


# --------------------------------------------------------------------- CSS ---
CSS = """
:root{
  --bg:#f6f6f4; --panel:#ffffff; --ink:#17181a; --muted:#5b6068; --line:#e0e0dc;
  --chip:#eceef0; --chip-ink:#3c4148; --accent:#245a86; --thead:#f0f1f2;
  --pass:#1c6b45; --pass-bg:#e6f2eb; --edge:#7a5600; --edge-bg:#faf1dd;
  --cond:#1d5581; --cond-bg:#e6eff7; --kill:#9c1f1f; --kill-bg:#fbe9e9;
  --ok:#1c6b45; --bad:#9c1f1f; --unk:#6b6b6b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#15171a; --panel:#1d2024; --ink:#e9eaec; --muted:#a3a9b2; --line:#31353b;
    --chip:#282d33; --chip-ink:#c4cad2; --accent:#7cb2dd; --thead:#242930;
    --pass:#6cc294; --pass-bg:#16301f; --edge:#dcb85f; --edge-bg:#332a12;
    --cond:#7cb2dd; --cond-bg:#152735; --kill:#e88b8b; --kill-bg:#331818;
    --ok:#6cc294; --bad:#e88b8b; --unk:#9aa0a8;
  }
}
:root[data-theme="dark"]{
  --bg:#15171a; --panel:#1d2024; --ink:#e9eaec; --muted:#a3a9b2; --line:#31353b;
  --chip:#282d33; --chip-ink:#c4cad2; --accent:#7cb2dd; --thead:#242930;
  --pass:#6cc294; --pass-bg:#16301f; --edge:#dcb85f; --edge-bg:#332a12;
  --cond:#7cb2dd; --cond-bg:#152735; --kill:#e88b8b; --kill-bg:#331818;
  --ok:#6cc294; --bad:#e88b8b; --unk:#9aa0a8;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",
  "Noto Sans TC","Noto Sans SC","PingFang TC","Microsoft JhengHei",Arial,sans-serif;}
.wrap{max-width:1100px;margin:0 auto;padding:24px 18px 64px}
h1{font-size:26px;line-height:1.25;margin:0 0 4px}
h2{font-size:20px;margin:38px 0 6px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:17px;margin:22px 0 6px}
h4{font-size:15px;margin:14px 0 4px}
p{margin:8px 0}
small,.sub{color:var(--muted);font-size:13px;line-height:1.45}
.lede{color:var(--muted);font-size:14px;margin:0 0 2px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:14px 16px;margin:12px 0}
.vcard{border-left:6px solid var(--line)}
.vcard.PASS{border-left-color:var(--pass);background:var(--pass-bg)}
.vcard.EDGE{border-left-color:var(--edge);background:var(--edge-bg)}
.vcard.CONDITIONAL{border-left-color:var(--cond);background:var(--cond-bg)}
.vcard.KILL{border-left-color:var(--kill);background:var(--kill-bg)}
.status{display:inline-block;font-weight:700;letter-spacing:.02em;padding:3px 10px;
  border-radius:999px;font-size:13px;border:1px solid currentColor}
.status.PASS{color:var(--pass)} .status.EDGE{color:var(--edge)}
.status.CONDITIONAL{color:var(--cond)} .status.KILL{color:var(--kill)}
.headline{font-size:18px;font-weight:600;margin:10px 0 6px}
.chips{margin:6px 0 0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-block;background:var(--chip);color:var(--chip-ink);border-radius:6px;
  padding:2px 8px;font-size:12.5px;border:1px solid var(--line);cursor:help}
.chip.ev-G{border-color:var(--ok)} .chip.ev-U{border-color:var(--unk)}
.chip.ev-S,.chip.ev-I{border-color:var(--edge)} .chip.ev-C{border-color:var(--accent)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);
  border-radius:10px;background:var(--panel);margin:10px 0}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--line)}
th{background:var(--thead);font-weight:600;white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
td.num{white-space:nowrap}
.meaning{border-bottom:1px dotted var(--muted);cursor:help}
.ok{color:var(--ok);font-weight:600} .bad{color:var(--bad);font-weight:600}
.unk{color:var(--unk);font-weight:600}
ul,ol{margin:8px 0;padding-left:22px} li{margin:4px 0}
.q{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:8px;padding:10px 12px;margin:8px 0}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;
  background:var(--chip);padding:1px 5px;border-radius:4px;word-break:break-all}
a{color:var(--accent)}
.foot{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px}
.rev{border-left:3px solid var(--line);padding-left:10px;margin:6px 0;font-style:italic}
.axis{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
.axis:first-of-type{border-top:none}
@media (max-width:640px){
  body{font-size:15px} .wrap{padding:16px 12px 48px} h1{font-size:22px} h2{font-size:18px}
}
@media print{
  body{background:#fff;color:#000;font-size:11pt}
  .wrap{max-width:none;padding:0}
  .card,.tw,.q{break-inside:avoid;page-break-inside:avoid}
  .tw{overflow:visible} table{min-width:0}
  h2{page-break-after:avoid} a{color:#000;text-decoration:none}
  a[href^="http"]::after{content:" (" attr(href) ")";font-size:9pt;color:#444}
}
"""


# -------------------------------------------------------------------- HTML ---
class HtmlRenderer(object):
    def __init__(self, data, L):
        self.d = data
        self.L = L
        self.out = []

    def w(self, text=""):
        self.out.append(text)

    # -- small pieces --------------------------------------------------------
    def chip_evidence(self, ec):
        if not ec:
            return ""
        tid = "evidence." + ec
        return '<span class="chip ev-%s" title="%s">%s</span>' % (
            esc(ec), esc(self.L.tip(tid)), esc(self.L.label(tid, ec)))

    def measure_cell(self, mea):
        if not isinstance(mea, dict):
            return '<td>%s</td>' % esc(self.L.label("ui.no_data"))
        value = fmt_value(mea.get("value"), mea.get("unit"))
        if value is None:
            value = self.L.label("ui.no_data")
        bits = ['<span class="meaning" title="%s">%s</span>' % (esc(mea.get("meaning") or ""), esc(value))]
        if mea.get("compared_to"):
            bits.append('<br><small>%s</small>' % esc(mea["compared_to"]))
        if mea.get("evidence_class"):
            bits.append('<br>%s' % self.chip_evidence(mea["evidence_class"]))
        return "<td>%s</td>" % "".join(bits)

    def section(self, index, term_id, anchor):
        L = self.L
        self.w('<h2 id="%s">%d. %s</h2>' % (anchor, index, esc(L.label(term_id))))
        gloss = L.plain(term_id)
        if gloss:
            self.w('<p class="lede">%s</p>' % esc(gloss))

    def table(self, headers, rows):
        self.w('<div class="tw"><table><thead><tr>')
        for head in headers:
            if isinstance(head, tuple):
                self.w('<th title="%s">%s</th>' % (esc(head[1]), esc(head[0])))
            else:
                self.w("<th>%s</th>" % esc(head))
        self.w("</tr></thead><tbody>")
        for row in rows:
            self.w("<tr>%s</tr>" % "".join(row))
        self.w("</tbody></table></div>")

    # -- sections ------------------------------------------------------------
    def s1_verdict(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            verdict = cand.get("verdict") or {}
            status = verdict.get("status", "")
            self.w('<div class="card vcard %s">' % esc(status))
            self.w('<h3>%s</h3>' % esc(candidate_name(cand)))
            identity = cand.get("identity") or {}
            line = " \u00b7 ".join([x for x in (identity.get("address"), identity.get("postcode"),
                                                identity.get("floor")) if x])
            if line:
                self.w('<p class="sub">%s</p>' % esc(line))
            self.w('<p><span class="status %s" title="%s">%s</span></p>' % (
                esc(status), esc(L.tip("verdict." + status)), esc(L.label("verdict." + status, status))))
            self.w('<p class="headline">%s</p>' % esc(verdict.get("headline", "")))
            codes = verdict.get("reason_codes") or []
            if codes:
                self.w('<p class="sub">%s</p><ul class="chips">' % esc(L.label("ui.reason_codes")))
                for code in codes:
                    self.w('<li class="chip" title="%s">%s</li>' % (
                        esc(L.plain("landmine." + code)), esc(L.label("landmine." + code, code))))
                self.w("</ul>")
            if verdict.get("break_even_rent_pcm") is not None:
                self.w('<p><strong>%s:</strong> %s <small>%s</small></p>' % (
                    esc(L.label("ui.break_even_rent")), esc(money(verdict["break_even_rent_pcm"])),
                    esc(L.plain("ui.break_even_rent"))))
            if verdict.get("fatal_axis"):
                axis_id = verdict["fatal_axis"]
                self.w('<p><strong>%s:</strong> %s</p>' % (
                    esc(L.label("ui.fatal_axis")),
                    esc("%d. %s" % (axis_id, L.label("axis.%d" % axis_id)))))
            if verdict.get("conditions"):
                self.w("<p><strong>%s</strong></p><ol>" % esc(L.label("ui.conditions")))
                for cond in verdict["conditions"]:
                    self.w("<li>%s</li>" % esc(cond))
                self.w("</ol>")
            self.w("</div>")

    def s2_hard_filters(self):
        L = self.L
        marks = {True: ('ok', "ui.pass"), False: ('bad', "ui.fail"), "unknown": ('unk', "ui.unknown")}
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            rows = []
            for hf in cand.get("hard_filters") or []:
                css, tid = marks.get(hf.get("pass"), ('unk', "ui.unknown"))
                rows.append([
                    "<td><strong>%s</strong></td>" % esc(hf.get("name", "")),
                    "<td>%s</td>" % esc(hf.get("requirement", "")),
                    "<td>%s</td>" % esc(hf.get("observed", "")),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        css, esc(L.plain(tid)), esc(L.label(tid))),
                    "<td>%s</td>" % self.chip_evidence(hf.get("evidence_class")),
                ])
            if not rows:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            self.table(["", L.label("ui.requirement"), L.label("ui.observed"),
                        L.label("ui.result"), L.label("ui.evidence")], rows)

    def s3_comparison(self):
        L = self.L
        comparison = self.d.get("comparison") or {}
        candidates = self.d.get("candidates", [])
        if len(candidates) < 2:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
            return
        by_id = dict((c.get("id"), c) for c in candidates)
        ranking = comparison.get("ranking") or []
        order = [r.get("candidate_id") for r in ranking] or [c.get("id") for c in candidates]

        rows = []
        for i, entry in enumerate(ranking, 1):
            cand = by_id.get(entry.get("candidate_id")) or {}
            rows.append([
                '<td class="num">%d</td>' % i,
                "<td><strong>%s</strong></td>" % esc(candidate_name(cand)),
                '<td class="num">%s</td>' % esc(fmt_value(entry.get("quality_score"))),
                '<td class="num">%s</td>' % esc("%d%%" % round((entry.get("closing_probability") or 0) * 100)),
                '<td class="num">%s</td>' % esc(fmt_value(entry.get("expected_value"))),
                "<td>%s</td>" % esc(entry.get("reason", "")),
            ])
        if rows:
            self.table([L.label("ui.rank"), L.label("ui.candidate"),
                        (L.label("ui.quality_score"), L.plain("ui.quality_score")),
                        (L.label("ui.closing_probability"), L.plain("ui.closing_probability")),
                        (L.label("ui.expected_value"), L.plain("ui.expected_value")),
                        L.label("ui.reason")], rows)

        headers = [L.label("ui.candidate")]
        for _, tid in METRIC_KEYS:
            headers.append((L.label(tid), L.plain(tid)))
        headers.append((L.label("ui.all_in_pcm"), L.plain("ui.all_in_pcm")))
        rows = []
        for cid in order:
            cand = by_id.get(cid)
            if not cand:
                continue
            metrics = cand.get("metrics") or {}
            cells = ["<td><strong>%s</strong></td>" % esc(candidate_name(cand))]
            for key, _tid in METRIC_KEYS:
                cells.append(self.measure_cell(metrics.get(key)))
            costs = cand.get("costs") or {}
            cells.append('<td class="num"><span class="meaning" title="%s">%s</span><br><small>%s</small></td>' % (
                esc(costs.get("basis_note") or ""), esc(money(costs.get("all_in_planning")) or L.label("ui.no_data")),
                esc(L.plain("ui.all_in_pcm"))))
            rows.append(cells)
        self.table(headers, rows)

        for key, tid in (("structural_findings", "ui.structural_findings"),
                         ("single_building_findings", "ui.single_building_findings")):
            findings = comparison.get(key) or []
            if not findings:
                continue
            self.w("<h3>%s</h3>" % esc(self.L.label(tid)))
            self.w('<p class="lede">%s</p>' % esc(self.L.plain(tid)))
            for finding in findings:
                self.w('<div class="card"><h4>%s</h4><p>%s</p>' % (
                    esc(finding.get("theme", "")), esc(finding.get("detail", ""))))
                if key == "structural_findings":
                    self.w('<p class="sub">%s &middot; %s</p>' % (
                        esc("%s: %s" % (self.L.label("ui.building"), finding.get("buildings_count"))),
                        esc(", ".join(str(y) for y in finding.get("years") or []))))
                else:
                    self.w('<p class="sub">%s: %s</p>' % (
                        esc(self.L.label("ui.building")), esc(finding.get("building", ""))))
                self.w("</div>")

    def s4_worst_reviews(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            reviews = cand.get("worst_reviews") or []
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            if not reviews:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            rows = []
            for rev in reviews:
                organic = rev.get("organic")
                rows.append([
                    "<td>%s</td>" % esc(rev.get("building") or ""),
                    "<td>%s</td>" % esc(rev.get("source_name") or ""),
                    '<td class="num">%s</td>' % esc(rev.get("date") or ""),
                    '<td class="num">%s</td>' % esc(fmt_value(rev.get("score")) or ""),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        "ok" if organic else "bad", esc(L.plain("ui.organic")),
                        esc(L.label("ui.yes") if organic else L.label("ui.no"))),
                    '<td><div class="rev">%s</div></td>' % esc(rev.get("excerpt") or ""),
                    "<td>%s</td>" % esc(rev.get("why_it_matters") or ""),
                ])
            self.table([L.label("ui.building"), L.label("ui.source_name"), L.label("ui.date"),
                        L.label("ui.score"), (L.label("ui.organic"), L.plain("ui.organic")),
                        L.label("ui.excerpt"), L.label("ui.why_it_matters")], rows)

    def s5_landmines(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            mines = cand.get("landmines") or []
            if not mines:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
                continue
            rows = []
            for mine in mines:
                code = mine.get("code", "")
                rows.append([
                    '<td class="num"><span class="chip" title="%s">%s</span></td>' % (
                        esc(L.plain("landmine." + code)), esc(code)),
                    "<td><strong>%s</strong><br><small>%s</small></td>" % (
                        esc(mine.get("label", "")), esc(L.label("landmine." + code, ""))),
                    "<td>%s</td>" % esc(mine.get("detail", "")),
                    '<td class="num"><span class="%s" title="%s">%s</span></td>' % (
                        "ok" if mine.get("reversible") else "bad", esc(L.plain("ui.reversible")),
                        esc(L.label("ui.yes") if mine.get("reversible") else L.label("ui.no"))),
                    "<td>%s</td>" % self.chip_evidence(mine.get("evidence_class")),
                ])
            self.table(["", L.label("section.landmines"),
                        L.label("ui.detail"),
                        (L.label("ui.reversible"), L.plain("ui.reversible")),
                        L.label("ui.evidence")], rows)

    def s6_axes(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w('<div class="card"><h3>%s</h3>' % esc(candidate_name(cand)))
            for axis in sorted(cand.get("axes") or [], key=lambda a: a.get("id") or 0):
                aid = axis.get("id")
                self.w('<div class="axis"><h4>%s. %s %s</h4>' % (
                    esc(aid), esc(L.label("axis.%s" % aid, axis.get("name", ""))),
                    self.chip_evidence(axis.get("evidence_class"))))
                self.w("<p>%s</p>" % esc(axis.get("finding", "")))
                numbers = axis.get("numbers") or []
                if numbers:
                    rows = []
                    for n in numbers:
                        rows.append([
                            "<td><strong>%s</strong></td>" % esc(n.get("label", "")),
                            '<td class="num"><span class="meaning" title="%s">%s</span></td>' % (
                                esc(n.get("meaning") or ""), esc(fmt_value(n.get("value"), n.get("unit"))
                                                                 or L.label("ui.no_data"))),
                            "<td><small>%s</small></td>" % esc(n.get("meaning", "")),
                            "<td><small>%s</small></td>" % esc(n.get("compared_to", "")),
                            "<td>%s</td>" % self.chip_evidence(n.get("evidence_class")),
                        ])
                    self.table([L.label("ui.numbers"), "", L.label("ui.why_it_matters"),
                                L.label("ui.compared_to"), L.label("ui.evidence")], rows)
                if axis.get("unknowns"):
                    self.w("<p class=\"sub\"><strong>%s</strong></p><ul>" % esc(L.label("ui.unknowns")))
                    for unk in axis["unknowns"]:
                        self.w("<li>%s</li>" % esc(unk))
                    self.w("</ul>")
                if axis.get("sources"):
                    self.w('<p class="sub">%s: %s</p>' % (
                        esc(L.label("ui.sources")), esc(", ".join(axis["sources"]))))
                self.w("</div>")
            costs = cand.get("costs") or {}
            if costs:
                self.w("<h4>%s</h4>" % esc(L.label("ui.costs")))
                rows = []
                for key, tid in COST_KEYS:
                    if costs.get(key) is None:
                        continue
                    rows.append(['<td title="%s">%s</td>' % (esc(L.plain(tid)), esc(L.label(tid))),
                                 '<td class="num">%s</td>' % esc(money(costs.get(key)))])
                if rows:
                    self.table([L.label("ui.costs"), ""], rows)
                if costs.get("basis_note"):
                    self.w('<p class="sub"><strong>%s:</strong> %s</p>' % (
                        esc(L.label("ui.basis_note")), esc(costs["basis_note"])))
            if cand.get("photos_vs_reality_notes"):
                self.w("<h4>%s</h4><p>%s</p>" % (esc(L.label("ui.photos_vs_reality")),
                                                 esc(cand["photos_vs_reality_notes"])))
            if cand.get("provenance_notes"):
                self.w("<h4>%s</h4><ul>" % esc(L.label("ui.provenance")))
                for note in cand["provenance_notes"]:
                    self.w("<li><small>%s</small></li>" % esc(note))
                self.w("</ul>")
            self.w("</div>")

    def s7_questions(self):
        L = self.L
        for cand in self.d.get("candidates", []):
            self.w("<h3>%s</h3>" % esc(candidate_name(cand)))
            self.w("<h4>%s</h4>" % esc(L.label("ui.killer_questions")))
            self.w('<p class="lede">%s</p>' % esc(L.plain("ui.killer_questions")))
            questions = cand.get("killer_questions") or []
            if questions:
                for question in questions:
                    self.w('<div class="q">%s</div>' % esc(question))
            else:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
            self.w("<h4>%s</h4>" % esc(L.label("ui.viewing_checks")))
            checks = cand.get("viewing_day_checks") or []
            if checks:
                self.w("<ol>")
                for check in checks:
                    self.w("<li>%s</li>" % esc(check))
                self.w("</ol>")
            else:
                self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))

    def s8_gaps(self):
        L = self.L
        rows = []
        for entry in self.d.get("not_found") or []:
            queries = "".join("<li><code>%s</code></li>" % esc(q) for q in entry.get("queries_used") or [])
            rows.append([
                "<td><strong>%s</strong></td>" % esc(entry.get("what", "")),
                "<td><ul>%s</ul></td>" % queries,
                "<td><small>%s</small></td>" % esc(entry.get("where_looked") or ""),
                "<td><small>%s</small></td>" % esc(entry.get("next_step") or ""),
            ])
        if rows:
            self.table([L.label("ui.not_found_what"), (L.label("ui.queries_used"), L.plain("ui.queries_used")),
                        L.label("ui.sources"), L.label("ui.next_step")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))
        rows = []
        for entry in self.d.get("blocked_sources") or []:
            rows.append([
                "<td><strong>%s</strong></td>" % esc(entry.get("source", "")),
                '<td class="num">%s</td>' % esc(entry.get("http_status") if entry.get("http_status") is not None else ""),
                "<td>%s</td>" % esc(entry.get("reason", "")),
                "<td><small>%s</small></td>" % esc(entry.get("workaround") or ""),
            ])
        self.w("<h3>%s</h3>" % esc(L.label("ui.blocked_source")))
        if rows:
            self.table([L.label("ui.blocked_source"), L.label("ui.http_status"),
                        L.label("ui.blocked_reason"), L.label("ui.workaround")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))

    def s9_sources(self):
        L = self.L
        rows = []
        for src in self.d.get("sources") or []:
            url = src.get("url") or ""
            link = ('<a href="%s">%s</a>' % (esc(url), esc(url))) if url.startswith("http") else esc(url)
            note = " ".join(x for x in (src.get("provenance"), src.get("note")) if x)
            rows.append([
                '<td class="num"><code>%s</code></td>' % esc(src.get("id", "")),
                "<td>%s</td>" % esc(src.get("name") or ""),
                "<td><small>%s</small></td>" % link,
                '<td class="num"><small>%s</small></td>' % esc(src.get("retrieved_at", "")),
                "<td>%s</td>" % self.chip_evidence(src.get("evidence_class")),
                "<td><small>%s</small></td>" % esc(note),
            ])
        if rows:
            self.table(["", L.label("ui.source_name"), L.label("ui.url"),
                        (L.label("ui.retrieved_at"), L.plain("ui.retrieved_at")),
                        L.label("ui.evidence"), L.label("ui.provenance")], rows)
        else:
            self.w("<p>%s</p>" % esc(L.label("ui.nothing_listed")))

    def s10_about(self):
        L = self.L
        gb = self.d.get("generated_by") or {}
        rows = [
            ("ui.tool", gb.get("tool")),
            ("ui.version", gb.get("version")),
            ("ui.runtime", gb.get("runtime")),
            ("ui.mode", gb.get("mode")),
            ("ui.model", gb.get("model_name")),
            ("ui.language", self.d.get("language")),
            ("ui.generated_at", self.d.get("generated_at")),
        ]
        cells = []
        for tid, value in rows:
            if value in (None, ""):
                continue
            cells.append(['<td title="%s">%s</td>' % (esc(L.plain(tid)), esc(L.label(tid))),
                          "<td>%s</td>" % esc(value)])
        self.table(["", ""], cells)
        snapshot = self.d.get("profile_snapshot") or {}
        prows = profile_rows(snapshot, L)
        if prows:
            self.w("<h3>%s</h3>" % esc(L.label("ui.profile_snapshot")))
            self.w('<p class="lede">%s</p>' % esc(L.plain("ui.profile_snapshot")))
            self.table(["", ""], [["<td>%s</td>" % esc(k), "<td>%s</td>" % esc(v)] for k, v in prows])
        self.w("<h3>%s</h3>" % esc(L.label("ui.evidence")))
        rows = []
        for code in ("G", "S", "C", "I", "U"):
            rows.append(["<td>%s</td>" % self.chip_evidence(code),
                         "<td>%s</td>" % esc(L.plain("evidence." + code))])
        self.table(["", ""], rows)

    # -- document ------------------------------------------------------------
    def render(self):
        L = self.L
        names = ", ".join(candidate_name(c) for c in self.d.get("candidates", []))
        title = "%s \u2014 %s" % (L.label("ui.report_title"), names) if names else L.label("ui.report_title")
        self.w("<!doctype html>")
        self.w('<html lang="%s"><head><meta charset="utf-8">' % esc(L.lang))
        self.w('<meta name="viewport" content="width=device-width,initial-scale=1">')
        self.w("<title>%s</title>" % esc(title))
        self.w("<style>%s</style></head><body><div class=\"wrap\">" % CSS)
        self.w("<h1>%s</h1>" % esc(L.label("ui.report_title")))
        self.w('<p class="sub">%s &middot; %s</p>' % (esc(names), esc(self.d.get("generated_at", ""))))
        renderers = [self.s1_verdict, self.s2_hard_filters, self.s3_comparison, self.s4_worst_reviews,
                     self.s5_landmines, self.s6_axes, self.s7_questions, self.s8_gaps,
                     self.s9_sources, self.s10_about]
        for i, ((term_id, anchor), fn) in enumerate(zip(SECTIONS, renderers), 1):
            self.section(i, term_id, anchor)
            fn()
        self.w('<p class="foot">%s</p>' % esc(footer_text(self.d)))
        self.w("</div></body></html>")
        return "\n".join(self.out)


# ---------------------------------------------------------------- Markdown ---
def md_escape(text):
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def md_table(headers, rows):
    out = ["", "| " + " | ".join(md_escape(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md_escape(c) for c in row) + " |")
    out.append("")
    return out


def render_markdown(data, L):
    o = []
    names = ", ".join(candidate_name(c) for c in data.get("candidates", []))
    o.append("# %s \u2014 %s" % (L.label("ui.report_title"), names))
    o.append("")
    o.append("_%s_" % data.get("generated_at", ""))

    def head(i, term_id):
        o.append("")
        o.append("## %d. %s" % (i, L.label(term_id)))
        gloss = L.plain(term_id)
        if gloss:
            o.append("")
            o.append("_%s_" % gloss)

    candidates = data.get("candidates", [])

    head(1, "section.verdict")
    for cand in candidates:
        verdict = cand.get("verdict") or {}
        status = verdict.get("status", "")
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append("**%s** \u2014 %s" % (L.label("verdict." + status, status), verdict.get("headline", "")))
        codes = verdict.get("reason_codes") or []
        if codes:
            o.append("")
            o.append("%s: %s" % (L.label("ui.reason_codes"),
                                 ", ".join("%s (%s)" % (L.label("landmine." + c, c), c) for c in codes)))
        if verdict.get("break_even_rent_pcm") is not None:
            o.append("")
            o.append("%s: %s" % (L.label("ui.break_even_rent"), money(verdict["break_even_rent_pcm"])))
        if verdict.get("fatal_axis"):
            o.append("")
            o.append("%s: %s. %s" % (L.label("ui.fatal_axis"), verdict["fatal_axis"],
                                     L.label("axis.%s" % verdict["fatal_axis"])))
        for cond in verdict.get("conditions") or []:
            o.append("- %s" % cond)

    head(2, "section.hard_filters")
    marks = {True: "ui.pass", False: "ui.fail", "unknown": "ui.unknown"}
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        rows = [[hf.get("name", ""), hf.get("requirement", ""), hf.get("observed", ""),
                 L.label(marks.get(hf.get("pass"), "ui.unknown")),
                 L.label("evidence." + (hf.get("evidence_class") or "U"))]
                for hf in cand.get("hard_filters") or []]
        o += md_table(["", L.label("ui.requirement"), L.label("ui.observed"),
                       L.label("ui.result"), L.label("ui.evidence")], rows)

    head(3, "section.comparison")
    comparison = data.get("comparison") or {}
    if len(candidates) > 1 and comparison:
        by_id = dict((c.get("id"), c) for c in candidates)
        rows = []
        for i, entry in enumerate(comparison.get("ranking") or [], 1):
            cand = by_id.get(entry.get("candidate_id")) or {}
            rows.append([i, candidate_name(cand), fmt_value(entry.get("quality_score")),
                         "%d%%" % round((entry.get("closing_probability") or 0) * 100),
                         fmt_value(entry.get("expected_value")), entry.get("reason", "")])
        o += md_table([L.label("ui.rank"), L.label("ui.candidate"), L.label("ui.quality_score"),
                       L.label("ui.closing_probability"), L.label("ui.expected_value"),
                       L.label("ui.reason")], rows)
        headers = [L.label("ui.candidate")] + [L.label(t) for _, t in METRIC_KEYS] + [L.label("ui.all_in_pcm")]
        rows = []
        for entry in comparison.get("ranking") or []:
            cand = by_id.get(entry.get("candidate_id"))
            if not cand:
                continue
            metrics = cand.get("metrics") or {}
            row = [candidate_name(cand)]
            for key, _t in METRIC_KEYS:
                mea = metrics.get(key) or {}
                text = fmt_value(mea.get("value"), mea.get("unit")) or L.label("ui.no_data")
                if mea.get("compared_to"):
                    text = "%s (%s)" % (text, mea["compared_to"])
                row.append(text)
            row.append(money((cand.get("costs") or {}).get("all_in_planning")) or L.label("ui.no_data"))
            rows.append(row)
        o += md_table(headers, rows)
        for key, tid in (("structural_findings", "ui.structural_findings"),
                         ("single_building_findings", "ui.single_building_findings")):
            findings = comparison.get(key) or []
            if not findings:
                continue
            o.append("")
            o.append("### %s" % L.label(tid))
            o.append("")
            o.append("_%s_" % L.plain(tid))
            for finding in findings:
                o.append("")
                o.append("- **%s** \u2014 %s" % (finding.get("theme", ""), finding.get("detail", "")))
    else:
        o.append("")
        o.append("_%s_" % L.label("ui.nothing_listed"))

    head(4, "section.worst_reviews")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        rows = [[r.get("building") or "", r.get("source_name") or "", r.get("date") or "",
                 fmt_value(r.get("score")) or "",
                 L.label("ui.yes") if r.get("organic") else L.label("ui.no"),
                 r.get("excerpt") or "", r.get("why_it_matters") or ""]
                for r in cand.get("worst_reviews") or []]
        if rows:
            o += md_table([L.label("ui.building"), L.label("ui.source_name"), L.label("ui.date"),
                           L.label("ui.score"), L.label("ui.organic"), L.label("ui.excerpt"),
                           L.label("ui.why_it_matters")], rows)
        else:
            o.append("")
            o.append("_%s_" % L.label("ui.nothing_listed"))

    head(5, "section.landmines")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        rows = [[m.get("code", ""), "%s (%s)" % (m.get("label", ""), L.label("landmine." + m.get("code", ""), "")),
                 m.get("detail", ""),
                 L.label("ui.yes") if m.get("reversible") else L.label("ui.no"),
                 L.label("evidence." + (m.get("evidence_class") or "U"))]
                for m in cand.get("landmines") or []]
        if rows:
            o += md_table(["", L.label("section.landmines"), L.label("ui.detail"),
                           L.label("ui.reversible"), L.label("ui.evidence")], rows)
        else:
            o.append("")
            o.append("_%s_" % L.label("ui.nothing_listed"))

    head(6, "section.axes")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        for axis in sorted(cand.get("axes") or [], key=lambda a: a.get("id") or 0):
            aid = axis.get("id")
            o.append("")
            o.append("#### %s. %s [%s]" % (aid, L.label("axis.%s" % aid, axis.get("name", "")),
                                           L.label("evidence." + (axis.get("evidence_class") or "U"))))
            o.append("")
            o.append(axis.get("finding", ""))
            for n in axis.get("numbers") or []:
                o.append("- **%s**: %s \u2014 %s %s" % (
                    n.get("label", ""), fmt_value(n.get("value"), n.get("unit")) or L.label("ui.no_data"),
                    n.get("meaning", ""), n.get("compared_to", "")))
            for unk in axis.get("unknowns") or []:
                o.append("- %s: %s" % (L.label("ui.unknowns"), unk))
        costs = cand.get("costs") or {}
        if costs:
            o.append("")
            o.append("**%s**" % L.label("ui.costs"))
            rows = [[L.label(t), money(costs.get(k))] for k, t in COST_KEYS if costs.get(k) is not None]
            o += md_table([L.label("ui.costs"), ""], rows)
            if costs.get("basis_note"):
                o.append("%s: %s" % (L.label("ui.basis_note"), costs["basis_note"]))
        if cand.get("photos_vs_reality_notes"):
            o.append("")
            o.append("**%s**: %s" % (L.label("ui.photos_vs_reality"), cand["photos_vs_reality_notes"]))
        for note in cand.get("provenance_notes") or []:
            o.append("- %s: %s" % (L.label("ui.provenance"), note))

    head(7, "section.questions")
    for cand in candidates:
        o.append("")
        o.append("### %s" % candidate_name(cand))
        o.append("")
        o.append("**%s**" % L.label("ui.killer_questions"))
        for question in cand.get("killer_questions") or []:
            o.append("1. %s" % question)
        o.append("")
        o.append("**%s**" % L.label("ui.viewing_checks"))
        for check in cand.get("viewing_day_checks") or []:
            o.append("- [ ] %s" % check)

    head(8, "section.gaps")
    rows = [[e.get("what", ""), "; ".join("`%s`" % q for q in e.get("queries_used") or []),
             e.get("where_looked") or "", e.get("next_step") or ""]
            for e in data.get("not_found") or []]
    if rows:
        o += md_table([L.label("ui.not_found_what"), L.label("ui.queries_used"),
                       L.label("ui.sources"), L.label("ui.next_step")], rows)
    o.append("")
    o.append("### %s" % L.label("ui.blocked_source"))
    rows = [[e.get("source", ""), e.get("http_status") if e.get("http_status") is not None else "",
             e.get("reason", ""), e.get("workaround") or ""]
            for e in data.get("blocked_sources") or []]
    if rows:
        o += md_table([L.label("ui.blocked_source"), L.label("ui.http_status"),
                       L.label("ui.blocked_reason"), L.label("ui.workaround")], rows)

    head(9, "section.sources")
    rows = [[s.get("id", ""), s.get("name") or "", s.get("url") or "", s.get("retrieved_at", ""),
             L.label("evidence." + (s.get("evidence_class") or "U")),
             " ".join(x for x in (s.get("provenance"), s.get("note")) if x)]
            for s in data.get("sources") or []]
    o += md_table(["", L.label("ui.source_name"), L.label("ui.url"), L.label("ui.retrieved_at"),
                   L.label("ui.evidence"), L.label("ui.provenance")], rows)

    head(10, "section.about")
    gb = data.get("generated_by") or {}
    rows = [[L.label("ui.tool"), gb.get("tool")], [L.label("ui.version"), gb.get("version")],
            [L.label("ui.runtime"), gb.get("runtime")], [L.label("ui.mode"), gb.get("mode")],
            [L.label("ui.model"), gb.get("model_name")], [L.label("ui.language"), data.get("language")],
            [L.label("ui.generated_at"), data.get("generated_at")]]
    o += md_table(["", ""], [r for r in rows if r[1]])
    prows = profile_rows(data.get("profile_snapshot") or {}, L)
    if prows:
        o.append("### %s" % L.label("ui.profile_snapshot"))
        o += md_table(["", ""], [[k, v] for k, v in prows])
    o += md_table(["", ""], [[L.label("evidence." + c), L.plain("evidence." + c)] for c in "GSCIU"])
    o.append("")
    o.append("---")
    o.append("")
    o.append(footer_text(data))
    o.append("")
    return "\n".join(o)


# -------------------------------------------------------------------- main ---
def build_parser():
    p = argparse.ArgumentParser(
        description="Render a vet-flat report.json as one self-contained HTML page, or as Markdown.")
    p.add_argument("report", help="path to report.json")
    p.add_argument("--lang", default=None,
                   help="BCP-47 language for labels (en, zh-TW, zh-CN...). Default: the report's own language.")
    p.add_argument("--md", action="store_true", help="write Markdown instead of HTML")
    p.add_argument("--validate-only", action="store_true", help="check the report and write nothing")
    p.add_argument("--schema", default=DEFAULT_SCHEMA, help="path to report-schema.json")
    p.add_argument("--glossary", default=DEFAULT_GLOSSARY, help="path to glossary.yaml")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with io.open(args.report, encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError) as exc:
        sys.stderr.write("Cannot read the report: %s\n" % exc)
        return 2
    except ValueError as exc:
        sys.stderr.write("The report is not valid JSON: %s\n" % exc)
        return 1
    try:
        with io.open(args.schema, encoding="utf-8") as fh:
            schema = json.load(fh)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("Cannot read the schema at %s: %s\n" % (args.schema, exc))
        return 2

    errors, warnings = validate(data, schema)
    for warning in warnings:
        sys.stderr.write("warning  %s\n" % warning)
    if errors:
        sys.stderr.write("\nThis report does not match report-schema.json. %d problem%s:\n"
                         % (len(errors), "" if len(errors) == 1 else "s"))
        for error in errors:
            sys.stderr.write("  error  %s\n" % error)
        sys.stderr.write("\nFix the JSON and run again. The schema explains every field:\n  %s\n" % args.schema)
        return 1
    if warnings and args.strict:
        sys.stderr.write("\n--strict: %d warning(s) treated as errors.\n" % len(warnings))
        return 1
    if args.validate_only:
        sys.stderr.write("OK: the report matches report-schema.json.\n")
        return 0

    try:
        terms = load_glossary(args.glossary)
    except (IOError, OSError, GlossaryError) as exc:
        sys.stderr.write("Cannot read the glossary at %s: %s\n" % (args.glossary, exc))
        return 2
    lang = args.lang or data.get("language") or "en"
    labels = Labels(terms, lang)
    text = render_markdown(data, labels) if args.md else HtmlRenderer(data, labels).render()
    out = getattr(sys.stdout, "buffer", sys.stdout)
    out.write(text.encode("utf-8"))
    out.write(b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
