#!/usr/bin/env python3
"""Offline, bounded adapter from human instructions and saved plain text to checks.

No external service, official-source claim, login, key, fee or network interaction.
Inputs are JSON and UTF-8 plain-text snapshots supplied by a trusted host, never
HTML selectors or portal endpoints. The plain-text grammar accepts a single
singular property description, complete labelled facts, and nearby standalone
listing facts. It stops before generic related-content/transport sections.
Unsupported wording, scope, conflicting values and missing facts stay unresolved.
This is deliberately not a general natural-language or source-truth verifier.

Usage: live_eligibility.py accept --input request.json
       live_eligibility.py validate --input request.json --artifact result.json
request.json: {proposal, user_inputs, revision, sources}; see accept() below.
"""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

try:
    import eligibility
except ImportError:
    import importlib.util
    _SPEC = importlib.util.spec_from_file_location(
        "_live_recorded_eligibility", Path(__file__).with_name("eligibility.py"))
    eligibility = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(eligibility)


SCHEMA = "vet-flat/live-eligibility/1"
PARSER_VERSION = "bounded-text/1"
FIELDS = {
    "rent_pcm": ("number", "GBP/month", "房租"),
    "monthly_total": ("number", "GBP/month", "每月總花費"),
    "bedrooms": ("number", "count", "房數"),
    "floor": ("number", "UK_floor", "英式樓層"),
    "area_m2": ("number", "m2", "廣告面積"),
    "epc_internal_area_m2": ("number", "m2", "EPC 室內面積"),
    "quiet": ("boolean", None, "屋內安靜程度"),
    "bedroom_faces_main_road": ("boolean", None, "臥室窗戶是否正對大馬路"),
    "heating_included": ("boolean", None, "租金是否包含暖氣費"),
    "availability": ("boolean", None, "指定入住日期的可租性"),
}
FOCUS_FIELDS = tuple(FIELDS)
_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_SMALL = r"(?:\d{1,2}|[零一二兩三四五六七八九十]+)"
_URL = re.compile(r"https?://[^\s<>「」“”\"'，。；！？()（）]+", re.I)
_CN = {"零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
       "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_EN = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
       "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
       "ten": 10, "ground": 0, "first": 1, "second": 2, "third": 3,
       "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
       "ninth": 9, "tenth": 10}


class LiveEligibilityError(ValueError):
    """Invalid host or proposal input; nothing may be published."""


def _require(ok, message):
    if not ok:
        raise LiveEligibilityError(message)


def _object(value, required, optional=(), where="object"):
    _require(type(value) is dict, where + " must be an object")
    _require(set(required) <= set(value) <= set(required) | set(optional),
             where + " has missing or unsupported fields")


def _hash(value):
    return eligibility.canonical_hash(value)


def _number(value):
    number = Decimal(value.replace(",", ""))
    return int(number) if number == number.to_integral_value() else float(number)


def _small(value):
    value = value.lower()
    if value.isdigit():
        return int(value)
    if value in _EN:
        return _EN[value]
    if value in _CN:
        return _CN[value]
    if "十" in value:
        left, right = value.split("十", 1)
        return (10 * (_CN[left] if left else 1)) + (_CN[right] if right else 0)
    raise LiveEligibilityError("unsupported number word")


def _requirement(key, field, operator, value, mandatory=True):
    kind, unit, _ = FIELDS.get(field, ("boolean", None, "待確認條件"))
    return dict(id=key, field=field, type=kind, operator=operator, value=value,
                unit=unit, mandatory=mandatory,
                basis=["observed", "reported"] if field in FIELDS else ["observed"])


def _categories(text):
    categories = set()
    for category, pattern in (
            ("budget", r"房租|租金|月租|預算|總花費|全部開銷|\brent\b|\bbudget\b|monthly total"),
            ("bedrooms", r"[一二兩三四五六七八九十\d]房|房型|\b(?:\d|one|two|three)[ -]bed(?:room)?s?\b|studio"),
            ("floor", r"樓|地面層|\bfloor\b|\bstorey\b"),
            ("area", r"面積|平方|\bsq\b|\bsqm\b|m²|m2|\barea\b|\bsize\b"),
            ("quiet", r"安靜|怕吵|噪音|\bquiet\b|\bnoise\b|\bnoisy\b"),
            ("road", r"大馬路|主幹道|main road|road.facing"),
            ("availability", r"入住|起租|搬到|\bmove.in\b|\bavailable\b")):
        if re.search(pattern, text, re.I):
            categories.add(category)
    return categories


def _clauses(text):
    # Keep URL dots out of sentence splitting; original spans are restored for
    # exact user provenance. URLs are discovery leads, never condition text.
    protected = {}
    def protect(match):
        index = len(protected)
        token = "__PEA_URL_%d__" % index
        while token in text or token in protected:
            index += 1
            token = "__PEA_URL_%d__" % index
        protected[token] = match.group()
        return token
    text = _URL.sub(protect, text)
    clauses = [part.strip() for part in re.split(
        r"[。！？!?；;\n]+|[，]|(?<!\d),(?!\d)|(?<!\d)\.(?!\d)", text) if part.strip()]
    for index, clause in enumerate(clauses):
        for token, url in protected.items():
            clause = clause.replace(token, url)
        clauses[index] = clause
    return clauses


def _routing_clause(clause):
    comparison_field = r"(?:房租|租金|房數|面積|樓層|暖氣費|暖氣|臥室朝向|噪音|安靜程度)"
    comparison_request = re.fullmatch(r"(?:請)?(?:先看|先比較|比較)" + comparison_field +
                                     r"(?:(?:、|與|和|及)" + comparison_field + r")*", clause)
    heating_question = (
        re.fullmatch(r"(?:暖氣|供暖)(?:費|費用)?(?:有)?(?:包含|包|含)(?:在)?(?:房租|租金)(?:裡|內|中)?嗎", clause) or
        re.fullmatch(r"(?:房租|租金)(?:是否|有沒有)(?:包含|包|含)(?:暖氣|供暖)(?:費|費用)?(?:嗎)?", clause) or
        re.fullmatch(r"is heating(?: cost)? included in (?:the )?rent", clause, re.I) or
        re.fullmatch(r"does (?:the )?rent include heating(?: costs?)?", clause, re.I))
    return bool(comparison_request or heating_question or re.fullmatch(r"(?:如果沒有符合的就(?:說明是哪裡卡住|直接說沒有)|保留原要求|先比較已知條件|我會補充確切條件)", clause) or
                re.fullmatch(r"if (?:none|no (?:candidate|listing)s?) (?:match|matches|meet(?:s)? (?:the )?(?:requirements|conditions)),? (?:say so|explain why)", clause, re.I))


def _budget_ambiguity(clause):
    """Only whole, simple ambiguous budget clauses get a resolvable signature."""
    currency = r"(?:£\s*|GBP\s*)(?P<n>" + _NUM + r")"
    ending = r"(?:\s*(?:每月|pcm|per month|a month))?"
    generic = re.fullmatch(r"(?:我(?:的)?\s*)?(?:每月)?預算(?:上限|最多|最高)(?:為|是)?\s*" + currency + ending, clause, re.I)
    if generic:
        return {"kind": "generic-scope", "amount": _number(generic.group("n"))}
    approximate = re.fullmatch(r"(?:房租|租金|月租)(?:上限|最多|最高)(?:為|是)?(?:大概|約莫|約)\s*" + currency + ending, clause, re.I)
    if approximate:
        return {"kind": "approx-rent", "amount": _number(approximate.group("n"))}
    return None


def _parse_clause(clause):
    """Return proposed fixed predicates, covered semantic categories and scope flag."""
    rows, covered, spans = [], set(), []
    # This explicit exclusion has conditional grammar but is itself a hard rule.
    road = ((re.search(r"臥室(?:的)?(?:窗戶|窗|窗口)?(?:\s|\w)*?(?:正對|朝向|面向|朝|對著)(?:大馬路|主幹道)", clause)
             and re.search(r"排除|不要|不接受|不可以|不能", clause)) or
            (re.search(r"bedroom(?: windows?)?.{0,35}(?:fac(?:e|es|ing)|overlook).{0,15}(?:main road|major road)", clause, re.I)
             and re.search(r"exclude|must not|cannot|can't|no |not accept|reject", clause, re.I)))
    if road:
        exact_road = (re.fullmatch(r"(?:只要|如果)?臥室(?:的)?(?:窗戶|窗|窗口)?(?:正對|朝向|面向|朝|對著)(?:大馬路|主幹道)(?:就)?(?:排除|不要|不接受|不可以|不能)", clause) or
                      re.fullmatch(r"(?:exclude|reject) (?:any |a |the )?bedroom(?: windows?)? (?:facing|overlooking) (?:a |the )?(?:main|major) road", clause, re.I) or
                      re.fullmatch(r"(?:the )?bedroom(?: windows?)? must not face (?:a |the )?(?:main|major) road", clause, re.I))
        if not exact_road:
            return [], set(), True
        rows.append(("bedroom-road", "bedroom_faces_main_road", "eq", False))
        covered.add("road")
        spans.append((0, len(clause)))
    scoped = bool(re.search(r"如果|除非|除外|例外|只針對|這(?:一)?[間戶]|那(?:一)?[間戶]|僅限|(?:^|\s)(?:if|unless|except|provided|only for|for this|for that|as long as)\b", clause, re.I))
    # Do not interpret an instruction about questions or a conditional as a waiver.
    if (scoped and (not road or (_categories(clause) - {"road"}))) or re.search(r"不要再問|別再問|不必再問|stop asking|don't ask|do not ask", clause, re.I):
        return [], set(), True
    if re.search(r"兩千多|大概|約莫|左右|差不多|可能|\babout\b|\baround\b|\broughly\b|\bmaybe\b", clause, re.I):
        return [], set(), True
    total = bool(re.search(r"總花費|全部預算|全部開銷|含(?:所有)?帳單|包括帳單|monthly total|total monthly|including bills|all.in", clause, re.I))
    budget_word = r"(?:房租|租金|月租|房租上限|預算|每月總花費|全部預算|monthly rent|rent|rental budget|budget|monthly total|total monthly (?:cost|spend))"
    limiter = r"(?:每月|一個月|每個月|上限|預算|最多|最高|不能超過|不超過|不高於|不得超過|改成|改為|調整為|降到|提高到|放寬到|收緊到|是|為|至|在|以內|的|英鎊|：|:|\s|ceiling|cap|maximum|max|at most|no more than|up to|under|within|is|of|to|change(?:d)?|limit|per month|a month)*"
    amounts = list(re.finditer(budget_word + limiter + r"(?:£\s*|GBP\s*)(?P<n>" + _NUM + r")", clause, re.I))
    # Currency first form is accepted only with an explicit ceiling operator.
    amounts += list(re.finditer(r"(?:最多|不超過|上限(?:改成|為)?|at most|no more than|up to)\s*£\s*(?P<n>" + _NUM + r")\s*(?:每月|pcm|per month|a month)?\s*(?:的)?(?:房租|租金|rent)", clause, re.I))
    if amounts:
        if not all(re.search(r"上限|最多|最高|不能超過|不超過|不高於|不得超過|預算|ceiling|cap|maximum|\bmax\b|at most|no more than|up to|under|within|budget|limit", m.group(), re.I) for m in amounts):
            return [], set(), True
        if not total and not re.search(r"房租|租金|月租|\brent\b|\brental\b", clause, re.I):
            return [], set(), True
        values = {_number(m.group("n")) for m in amounts}
        if len(values) != 1:
            return [], set(), True
        field = "monthly_total" if total else "rent_pcm"
        value = values.pop()
        if value <= 0:
            return [], set(), True
        rows.append(("monthly-total-ceiling" if total else "rent-ceiling", field, "lte", value))
        covered.add("budget")
        spans.extend((m.start(), m.end()) for m in amounts)
    bed_matches = list(re.finditer(r"(" + _SMALL + r")\s*房(?!東|租)", clause))
    bed_matches += list(re.finditer(r"\b(\d|one|two|three|four)\s*[- ]\s*bed(?:room)?(?:s)?\b", clause, re.I))
    if bed_matches:
        vals = {_small(m.group(1)) for m in bed_matches}
        if len(vals) != 1 or re.search(r"不是|不要[一二兩三\d]房|不只|或|\bor\b|\bnot\b|don't want", clause, re.I):
            return [], set(), True
        minimum_beds = all(re.search(r"(?:至少|不少於|最低|at least|minimum(?: of)?)\s*$", clause[:m.start()], re.I) for m in bed_matches)
        rows.append(("bedrooms", "bedrooms", "gte" if minimum_beds else "eq", vals.pop()))
        covered.add("bedrooms")
        spans.extend((m.start(), m.end()) for m in bed_matches)
    floors = re.search(r"(" + _SMALL + r")\s*(?:樓)?\s*(?:到|至|[-–~])\s*(" + _SMALL + r")\s*樓", clause)
    if not floors:
        floors = re.search(r"\bfloors?\s*(?:between\s*)?(\d{1,2}|one|two|three|four|five)\s*(?:to|through|and|[-–])\s*(\d{1,2}|five|six|seven|eight|nine|ten)\b", clause, re.I)
    if floors:
        lower, upper = _small(floors.group(1)), _small(floors.group(2))
        if lower > upper:
            return [], set(), True
        rows.extend([("floor-min", "floor", "gte", lower), ("floor-max", "floor", "lte", upper)])
        covered.add("floor")
        spans.append(floors.span())
    area = re.search(r"(?:至少|不低於|不少於|最低|>=|at least|minimum(?: of)?|min(?:imum)?\s*[:=]?)\s*(" + _NUM + r")\s*(?:平方公尺|平方米|m²|m2|sqm|sq\.?\s*m(?:etres?)?)", clause, re.I)
    if area:
        field = "epc_internal_area_m2" if re.search(r"\bEPC\b", clause, re.I) else "area_m2"
        if _number(area.group(1)) <= 0:
            return [], set(), True
        rows.append(("epc-area-min" if field.startswith("epc") else "area-min", field, "gte", _number(area.group(1))))
        covered.add("area")
        spans.append(area.span())
    if re.search(r"安靜|怕吵|\bquiet\b", clause, re.I) and not re.search(r"不需要安靜|不用安靜|不在意|不介意|don't (?:need|care)|do not (?:need|care)", clause, re.I):
        rows.append(("quiet", "quiet", "eq", True))
        covered.add("quiet")
        spans.extend(m.span() for m in re.finditer(r"安靜|怕吵|\bquiet\b", clause, re.I))
    # Full supported clauses may contain these ordinary desire/change wrappers.
    # Unconsumed content is an explicit coverage gap, even when it has no keyword
    # known to this parser (for example an unfamiliar additional hard condition).
    remainder = list(clause)
    for start, end in spans:
        remainder[start:end] = " " * (end - start)
    remainder = "".join(remainder)
    wrappers = ("只接受", "我只要", "只要", "我要", "我想要", "想要", "我想租", "我想找", "想租", "想找", "一間", "一個", "希望", "偏好", "最好", "需要", "樓層", "室內面積", "面積", "不過", "而且", "還是", "第一優先", "最優先", "優先", "改成", "改為", "租一間", "我比較", "英式", "英國", "至少", "不少於", "最低", "必須", "一定要", "可以把", "請把", "能把", "嗎", "而", "的", "我", "要", "找", "租")
    remainder = re.sub("|".join(re.escape(v) for v in sorted(wrappers, key=len, reverse=True)), " ", remainder)
    remainder = re.sub(r"\b(?:per month|a month|pcm)\b", " ", remainder, flags=re.I)
    remainder = re.sub(r"\b(?:i|we|want|need|only|a|an|the|please|flat|apartment|property|bedrooms?|area|size|internal|advertised|epc|and|with|must|be|prefer|change|changed|to|now|still|priority|first|is|my|at least|minimum|per month|a month|pcm)\b", " ", remainder, flags=re.I)
    remainder = re.sub(r"[\s：:、\-–()（）]+", "", remainder)
    return rows, covered, bool(rows and remainder)


def normalize(user_inputs, revision):
    """Compile a small explicit zh/en grammar from ordered, host-authored requests.

    Return {constraints, unresolved_intent: [exact clauses], provenance}. Every
    unresolved clause has a mandatory unknown predicate. Conditions are never
    accepted from actor output, and ambiguous updates never retire earlier ones.
    """
    _require(type(revision) is int and revision >= 0, "revision must be a nonnegative integer")
    _require(type(user_inputs) is list and all(type(v) is str and v.strip() for v in user_inputs),
             "user_inputs must be an array of nonempty strings")
    _require(sum(len(v) for v in user_inputs) <= 96000, "user instruction packet exceeds supported bound")
    active, origins, unresolved = {}, {}, {}
    for index, text in enumerate(user_inputs):
        pending_rows, pending_origins, covered_message, conflicts = {}, {}, set(), set()
        clarification_answer = "我會補充確切條件" in _clauses(text)
        clauses = [(clause, _URL.sub("", clause).strip()) for clause in _clauses(text)]
        clauses = [(original, parsed) for original, parsed in clauses if parsed and not _routing_clause(parsed)]
        conditional_message = any(
            re.search(r"如果|除非|除外|例外|若|只要.+就|\b(?:if|unless|except|provided)\b|as long as", clause, re.I)
            and not any(row[0] == "bedroom-road" for row in _parse_clause(clause)[0])
            for _, clause in clauses)
        for clause, parsed_clause in clauses:
            rows, covered, ambiguous = _parse_clause(parsed_clause)
            # A condition can precede or follow its proposed numeric amendment
            # across punctuation. Never apply just the convenient half.
            ambiguous = ambiguous or conditional_message
            categories = _categories(parsed_clause)
            for key, field, operator, value in ([] if ambiguous else rows):
                preference = bool(re.search(r"偏好|希望|最好|\bprefer\b", parsed_clause, re.I))
                hard = bool(re.search(r"必須|一定要|只接受|\bmust\b|required", parsed_clause, re.I))
                mandatory = hard or (field != "quiet" and not preference)
                existing = pending_rows.get(key, active.get(key))
                if not mandatory and existing and existing["mandatory"]:
                    if preference:
                        key = "preference-" + key
                    else:
                        mandatory = True
                row = _requirement(key, field, operator, value, mandatory)
                if key in pending_rows and pending_rows[key] != row:
                    conflicts.add(key)
                pending_rows[key] = row
                pending_origins[key] = {"request_id": "input-%d" % (index + 1), "quote": clause}
            if not ambiguous:
                covered_message |= covered
            missing = categories - covered
            # Housing constraints outside the grammar remain visible instead of
            # disappearing merely because another constraint was recognized.
            other_constraint = re.search(r"必須|只接受|不能|不可|一定要|不要|至少|最多|條件|要求|我要|想要|想租|想找|需要|希望|喜歡|\bmust\b|\brequire\b|\bonly\b|\bexclude\b|\bmaximum\b|\bminimum\b|\bwant\b|\bneed\b|\bprefer\b|\bcannot\b|\bcan't\b|\bcan not\b", parsed_clause, re.I)
            if ambiguous or missing or (other_constraint and not rows):
                key = "intent-" + hashlib.sha256(clause.encode("utf-8")).hexdigest()[:16]
                unresolved[key] = {"text": clause, "categories": sorted(categories), "index": index,
                                   "budget_ambiguity": _budget_ambiguity(parsed_clause)}
        for key in conflicts:
            origin = pending_origins[key]
            unresolved["conflict-" + key] = {"text": origin["quote"], "categories": [],
                                           "index": index, "budget_ambiguity": None}
            pending_rows.pop(key, None)
            pending_origins.pop(key, None)
        # Resolve only a complete, pure budget ambiguity. Heating, lifts, mixed
        # conditions and scoped exceptions never receive this narrow signature.
        generic_keys = [key for key, item in unresolved.items()
                        if (item.get("budget_ambiguity") or {}).get("kind") == "generic-scope"]
        first_unresolved = next(iter(unresolved), None)
        # The renderer asks about the first unresolved clause. Its literal reply
        # option cannot choose a different target or batch-clear several budgets.
        marker_target = (generic_keys[0] if clarification_answer and len(generic_keys) == 1
                         and generic_keys[0] == first_unresolved else None)
        for key, item in list(unresolved.items()):
            signature = item.get("budget_ambiguity")
            if not signature or item["index"] >= index:
                continue
            budget = pending_rows.get("rent-ceiling")
            total_budget = pending_rows.get("monthly-total-ceiling")
            resolved = (signature["kind"] == "approx-rent" and budget is not None)
            resolved = resolved or (signature["kind"] == "generic-scope" and
                any(row is not None and (row["value"] == signature["amount"] or key == marker_target)
                    for row in (budget, total_budget)))
            if resolved:
                del unresolved[key]
        active.update(pending_rows)
        origins.update(pending_origins)
    for key, item in unresolved.items():
        active[key] = _requirement(key, key, "eq", True)
        origins[key] = {"request_id": "input-%d" % (item["index"] + 1), "quote": item["text"]}
    if not active:
        active["intent-not-specified"] = _requirement("intent-not-specified", "intent-not-specified", "eq", True)
    # A verified single-listing identity is a host precondition, not a new human
    # preference. Its meaning is only that the retained page describes one unit.
    active["listing-identity"] = _requirement("listing-identity", "listing_identity", "eq", True)
    constraints = dict(schema_version=eligibility.CONSTRAINTS_SCHEMA, revision=revision,
                       requirements=[active[k] for k in sorted(active)],
                       user_requests={"input-%d" % (i + 1): text for i, text in enumerate(user_inputs)},
                       exceptions=[])
    return dict(constraints=constraints, unresolved_intent=[v["text"] for v in unresolved.values()],
                provenance={"parser_version": PARSER_VERSION, "user_inputs_sha256": _hash(user_inputs),
                            "requirements": origins, "complete_natural_language_understanding": False})


def _unknown(field, reason):
    return dict(value=None, unit=FIELDS.get(field, (None, None, None))[1], qualifier="unknown",
                source_id=None, quote=None, reason=reason)


def _known(field, value, source_id, quote, qualifier="reported"):
    return dict(value=value, unit=FIELDS.get(field, (None, None, None))[1], qualifier=qualifier,
                source_id=source_id, quote=quote)


_SECTION_END = re.compile(r"(?:nearest stations|nearby (?:stations|properties)|similar properties|related properties|you (?:might|may) also (?:be interested|like).*|local life|local intelligence|popular searches.*|market (?:overview|statistics|review))", re.I)
_UNSAFE = re.compile(r"\b(?:not|isn't|wasn't|example|previous|previously|former|formerly|deposit|fees?|neighbour|neighbor|nearby|hypothetical)\b|不是|並非|例如|押金|舊租金", re.I)
_PROPERTY = re.compile(r"\b(?P<n>\d{1,2})[ -]bedroom\b.{0,45}?\b(?:apartment|flat|property|house|maisonette)\b", re.I)
_RENT = re.compile(r"(?:(?:advertised\s+)?(?:monthly\s+)?rent(?:\s+(?:pcm|per month))?\s*[:=]?\s*)?£\s*(?P<n>" + _NUM + r")\s*(?:pcm|per calendar month|per month|/\s*month)\.?", re.I)
_WEEKLY = re.compile(r"£\s*" + _NUM + r"\s*(?:pw|per week)\.?", re.I)
_AREA_UNIT = r"(?:m²|m2|sqm|sq\.?\s*m(?:etres?)?|square metres?)"
_FT_UNIT = r"(?:sq\.?\s*ft|sqft|square feet)"


def _source_facts(url, source):
    source_id = "source-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    fields = {field: _unknown(field, "來源未提供可核對的單戶資料") for field in FIELDS}
    fields["listing_identity"] = _unknown("listing_identity", "尚未辨明來源是否為單一房源")
    metadata = dict(source_url=url, retrieved_at=None, sha256=None, ok=False,
                    identity="unknown", retention_verified=False, unit_identity_supported=False)
    if source is None:
        metadata["note"] = "沒有保存這個來源"
        return source_id, "Unavailable source: " + url, fields, metadata
    _object(source, {"text", "retrieved_at", "sha256", "ok", "identity"}, {"note"}, where="source")
    _require(type(source["text"]) is str and type(source["ok"]) is bool, "invalid source text/ok types")
    _require(source["identity"] in ("unit", "unknown"), "invalid source identity")
    _require(source["retrieved_at"] is None or type(source["retrieved_at"]) is str, "invalid source retrieval time")
    _require(source["sha256"] is None or type(source["sha256"]) is str, "invalid source hash")
    metadata.update({k: source[k] for k in ("retrieved_at", "sha256", "ok", "identity")})
    if "note" in source:
        _require(source["note"] is None or type(source["note"]) is str, "invalid source note")
        metadata["host_note"] = source["note"]
    text = source["text"]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    metadata["retention_verified"] = source["sha256"] == digest
    metadata["actual_text_sha256"] = digest
    if not source["ok"] or not metadata["retention_verified"] or len(text) > 400000:
        metadata["note"] = "保存的來源不可用、內容不符或超出解析範圍"
        return source_id, text or "Empty source: " + url, fields, metadata
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if _SECTION_END.fullmatch(line):
            break
        if line:
            lines.append(line)
    descriptions = [(line, match) for line in lines if not _UNSAFE.search(line) for match in _PROPERTY.finditer(line)]
    counts = {int(match.group("n")) for _, match in descriptions}
    starting = any(re.search(r"\b(?:from|starting(?: at| from)?)\s+£", line, re.I) for line in lines)
    multiunit = any(re.search(r"\b(?:available (?:apartments|flats|units)|(?:apartments|flats|units) available|choose (?:an? |your )?(?:apartment|flat|unit)|(?:apartment|flat|unit)\s+[a-z0-9]+\s*(?:&|and|,)\s*(?:(?:apartment|flat|unit)\s+)?[a-z0-9]+)\b", line, re.I) for line in lines)
    unit_labels = {m.group().lower() for line in lines for m in re.finditer(r"\b(?:apartment|flat|unit)\s+(?:[A-Z](?![a-z])|\d+[A-Z]?)\b", line, re.I)}
    multiunit = multiunit or len(unit_labels) > 1 or any(len(list(_PROPERTY.finditer(line))) > 1 for line in lines)
    if source["identity"] != "unit" or len(counts) != 1 or starting or multiunit:
        metadata["note"] = "來源不能保守辨識為有明確房型的單戶；大樓起价與多戶資料不套用"
        return source_id, text or "Empty source: " + url, fields, metadata
    metadata["unit_identity_supported"] = True
    fields["listing_identity"] = _known("listing_identity", True, source_id, descriptions[0][0], "observed")
    observations = {field: [] for field in FIELDS}
    observations["bedrooms"] = [(next(iter(counts)), line) for line, _ in descriptions]
    for index, line in enumerate(lines):
        previous = lines[index - 1] if index else ""
        recent = lines[max(0, index - 5):index]
        if _UNSAFE.search(line):
            # An explicit negative heating/road statement is handled separately.
            pass
        else:
            bed = re.fullmatch(r"(\d{1,2})\s+Beds?", line, re.I)
            if bed:
                observations["bedrooms"].append((int(bed.group(1)), line))
            rent = _RENT.fullmatch(line)
            if rent:
                labelled = bool(re.match(r"(?:advertised\s+)?(?:monthly\s+)?rent\b", line, re.I))
                nearby_type = any(_PROPERTY.search(s) or re.fullmatch(r"\d{1,2}\s+Beds?", s, re.I) for s in recent)
                safe_context = labelled or (not any(_UNSAFE.search(s) for s in recent) and
                                (_WEEKLY.fullmatch(previous) or nearby_type or
                                 re.fullmatch(r"(?:monthly\s+)?rent", previous, re.I)))
                if safe_context:
                    observations["rent_pcm"].append((_number(rent.group("n")), line))
            total = re.fullmatch(r"(?:monthly total|total monthly (?:cost|spend))\s*[:=]\s*£\s*(" + _NUM + r")\s*(?:pcm|per month|/month)", line, re.I)
            if total:
                observations["monthly_total"].append((_number(total.group(1)), line))
            floor = re.fullmatch(r"(?:floor\s*[:=]\s*)?(\d{1,2})(?:st|nd|rd|th)?\s*(?:floor)?", line, re.I)
            if floor and (re.search(r"floor", line, re.I) or previous.lower() == "floor"):
                observations["floor"].append((int(floor.group(1)), line))
            word_floor = re.fullmatch(r"(ground|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) floor", line, re.I)
            if word_floor:
                observations["floor"].append((_small(word_floor.group(1)), line))
            # Only a floor adjective attached directly to the unit description.
            embedded_floor = re.search(r"\b(\d{1,2})(?:st|nd|rd|th) floor\s+(?:property|flat|apartment|\d{1,2} bedroom (?:flat|apartment))\b", line, re.I)
            if embedded_floor and _PROPERTY.search(line):
                observations["floor"].append((int(embedded_floor.group(1)), line))
            epc = re.fullmatch(r"EPC (?:internal |total floor )?area\s*[:=]\s*(" + _NUM + r")\s*" + _AREA_UNIT + r"\.?", line, re.I)
            if epc:
                observations["epc_internal_area_m2"].append((_number(epc.group(1)), line))
            metric = re.fullmatch(r"(?:(?:advertised |internal |total )?(?:area|floor area)\s*[:=]\s*)?(" + _NUM + r")\s*" + _AREA_UNIT + r"(?:\s*approx\.?)?\.?", line, re.I)
            combined = re.fullmatch(r"(" + _NUM + r")\s*\(\s*(" + _NUM + r")\s*" + _AREA_UNIT + r"\s*\)\s*(?:approx\.?)?", line, re.I)
            feet = re.fullmatch(r"(?:(?:advertised |internal |total )?(?:area|floor area)\s*[:=]\s*)?(" + _NUM + r")\s*" + _FT_UNIT + r"(?:\s*approx\.?)?\.?", line, re.I)
            area_label = re.fullmatch(r"(?:total\s+)?(?:sq\.?\s*ft|area|floor area|size)", previous, re.I)
            span_context = (any(_PROPERTY.fullmatch(s) for s in recent) and
                            not re.search(r"bedroom|kitchen|bathroom|living room|balcony|terrace", previous, re.I))
            labelled_area = re.match(r"(?:advertised |internal |total )?(?:area|floor area)\s*[:=]", line, re.I)
            if combined and area_label:
                observations["area_m2"].append((_number(combined.group(2)), line))
            elif metric and (area_label or labelled_area or span_context):
                observations["area_m2"].append((_number(metric.group(1)), line))
            elif feet and (area_label or labelled_area or span_context):
                value = float(Decimal(feet.group(1).replace(",", "")) * Decimal("0.09290304"))
                observations["area_m2"].append((value, line))
        road = re.fullmatch(r"(?:the )?bedroom(?: windows?)? (faces?|overlooks?|does not face|do not face) (?:a |the )?(?:main|major) road\.?", line, re.I)
        if road:
            observations["bedroom_faces_main_road"].append(("not" not in road.group(1).lower(), line))
        heating = re.fullmatch(r"(?:the )?heating(?: (?:costs?|bills?))? (?:is |are )?(not )?included(?: in (?:the )?rent)?\.?", line, re.I)
        if heating:
            observations["heating_included"].append((heating.group(1) is None, line))
        noise = re.fullmatch(r"(?:bedroom|indoor) noise\s*:\s*(quiet|noisy)\.?", line, re.I)
        if noise:
            observations["quiet"].append((noise.group(1).lower() == "quiet", line))
    for field, values in observations.items():
        distinct = {value for value, _ in values}
        if len(distinct) == 1:
            value, quote = values[0]
            fields[field] = _known(field, value, source_id, quote)
        elif len(distinct) > 1:
            fields[field] = _unknown(field, "同一來源有互相衝突的數值，需先確認適用哪一筆")
    fields["availability"] = _unknown("availability", "廣告或保存時間不能確認使用者指定日期、單戶與租約條件的可租性")
    metadata["note"] = "保存的單戶廣告；列出的數值屬來源自述，並非實地或房東確認"
    return source_id, text, fields, metadata


def _proposal(value):
    _object(value, {"candidates", "focus_fields"}, where="proposal")
    _require(type(value["candidates"]) is list and len(value["candidates"]) <= 3,
             "proposal supports at most three candidates")
    _require(type(value["focus_fields"]) is list and all(type(v) is str and v in FIELDS for v in value["focus_fields"]),
             "unsupported focus field")
    _require(len(set(value["focus_fields"])) == len(value["focus_fields"]), "duplicate focus field")
    seen, candidates = set(), []
    for row in value["candidates"]:
        _object(row, {"source_url", "label"}, where="candidate proposal")
        _require(type(row["source_url"]) is str and type(row["label"]) is str and len(row["label"]) <= 160,
                 "invalid candidate URL/label")
        url = row["source_url"]
        try:
            parsed = urlsplit(url)
            valid_url = (parsed.scheme in ("http", "https") and parsed.hostname and
                         not parsed.username and not parsed.password and not parsed.fragment and
                         not re.search(r"[\s<>\\\x00-\x1f]", url))
        except ValueError:
            valid_url = False
        _require(valid_url, "candidate requires an ordinary http(s) source URL")
        _require(url not in seen, "duplicate candidate URL")
        seen.add(url)
        candidates.append({"source_url": url, "label": row["label"]})
    return {"candidates": candidates, "focus_fields": sorted(value["focus_fields"])}


def _format_number(value):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return format(value, ",.6f").rstrip("0").rstrip(".")
    return "未確認"


def _formatted(field, value):
    if value is None:
        return "未確認"
    if field in ("rent_pcm", "monthly_total"):
        return "£" + _format_number(value) + "／月"
    if field in ("area_m2", "epc_internal_area_m2"):
        return _format_number(value) + " m²"
    if field == "floor":
        return "地面層" if value == 0 else "英式 " + _format_number(value) + " 樓"
    if field == "bedrooms":
        return _format_number(value) + " 房"
    return "是" if value else "否"


def _requirement_label(row):
    field, value = row["field"], row["value"]
    if field not in FIELDS:
        return "房源身分" if field == "listing_identity" else "尚未完整釐清的條件"
    if field == "bedroom_faces_main_road":
        return "臥室窗戶不正對大馬路"
    if field == "quiet":
        return "屋內安靜" if row["mandatory"] else "偏好屋內安靜"
    suffix = {"lte": "不超過", "gte": "至少", "eq": "為"}[row["operator"]]
    return FIELDS[field][2] + suffix + _formatted(field, value)


def _presentation(constraints, evidence, recommendation):
    rows = {row["id"]: row for row in constraints["requirements"]}
    labels = {row["id"]: "房源 " + chr(65 + index) for index, row in enumerate(evidence["candidates"])}
    todos = []
    for todo in recommendation["todos"]:
        labels_to_check = list(dict.fromkeys(_requirement_label(rows[key]) for key in todo["requirement_ids"]))
        todos.append(labels[todo["candidate_id"]] + "：查證" + "、".join(labels_to_check))
    conditions = [("必要條件：" if row["mandatory"] else "偏好：") +
                  _requirement_label(row).removeprefix("偏好")
                  for row in constraints["requirements"] if row["field"] in FIELDS]
    return {"todos": todos, "conditions": conditions}


def _failure_text(label, row, check):
    field, value = row["field"], check["value"]
    if field in ("rent_pcm", "monthly_total"):
        return label + "廣告列" + _formatted(field, value) + "，超過" + _formatted(field, row["value"]) + "上限"
    if field in ("area_m2", "epc_internal_area_m2"):
        return label + "來源列" + _formatted(field, value) + "，低於" + _formatted(field, row["value"]) + "的面積要求"
    return label + "廣告列" + _formatted(field, value) + "，不符合「" + _requirement_label(row) + "」"


def _opening(rows, candidates, checks, recommendation, labels):
    ranked, blocked = recommendation["ranking"], recommendation["blocked"]
    failures = []
    for item in blocked:
        key = item["candidate_id"]
        requirement_id = item["failed_requirement_ids"][0]
        failures.append(_failure_text(labels[key], rows[requirement_id], checks["candidates"][key]["checks"][requirement_id]))
    if failures:
        opening = "；".join(failures) + "，依目前條件排除"
        if ranked:
            opening += "；先查證" + "、".join(labels[item["candidate_id"]] for item in ranked) + "尚未確認的條件。"
        else:
            opening += "；這批房源目前沒有可繼續推薦的選項。"
        return opening
    rents = sorted((Decimal(str(candidates[item["candidate_id"]]["fields"]["rent_pcm"]["value"])), item["candidate_id"])
                   for item in ranked if candidates[item["candidate_id"]]["fields"]["rent_pcm"]["value"] is not None)
    if len(rents) >= 2:
        low, high = rents[0], rents[-1]
        if low[0] == high[0]:
            opening = labels[low[1]] + "與" + labels[high[1]] + "的廣告房租同為" + _formatted("rent_pcm", float(low[0]))
            return opening + "；再比較其他條件，仍待核實。"
        else:
            opening = labels[low[1]] + "的廣告房租比" + labels[high[1]] + "每月低 £" + _format_number(float(high[0] - low[0]))
        return opening + "；可從價格差異繼續比較，其他條件仍待核實。"
    if rents:
        return labels[rents[0][1]] + "廣告房租為" + _formatted("rent_pcm", float(rents[0][0])) + "，可先核對它與目前條件的差距；目前沒有一間已核實全部條件。"
    if ranked:
        return "、".join(labels[item["candidate_id"]] for item in ranked) + "有可追溯的單戶廣告，但租金與其他未確認條件仍需先查證。"
    return "目前的來源不足以確認單戶房源，還不能作符合條件的候選比較。"


def _render(constraints, evidence, checks, recommendation, proposal, metadata, unresolved, presentation):
    rows = {row["id"]: row for row in constraints["requirements"]}
    candidates = {row["id"]: row for row in evidence["candidates"]}
    labels = {row["id"]: "房源 " + chr(65 + index) for index, row in enumerate(evidence["candidates"])}
    questions = []
    if unresolved:
        excerpt = unresolved[0] if len(unresolved[0]) <= 130 else unresolved[0][:129] + "…"
        questions = [{"question": "這項要求還需要釐清：「" + excerpt + "」。你想先補充，還是保留它並先比較已知條件？",
                      "options": ["保留原要求，先比較已知條件", "我會補充確切條件"]}]
        budget = _budget_ambiguity(unresolved[0])
        if budget and budget["kind"] == "generic-scope":
            amount = "£" + format(budget["amount"], ",")
            questions = [{"question": "你說的預算 " + amount + "，是每月只算房租，還是包含帳單的全部花費？",
                          "options": ["房租上限 " + amount, "每月總花費上限 " + amount]}]
    if not candidates:
        return {"message": "目前還沒有可核對的單戶房源。提供具體房源連結後，可以依目前條件比較；尚未辨明的條件會保留待確認。", "questions": questions}
    opening = _opening(rows, candidates, checks, recommendation, labels)
    paragraphs = [opening]
    for index, proposal_row in enumerate(proposal["candidates"]):
        candidate_id = evidence["candidates"][index]["id"]
        candidate, result = candidates[candidate_id], checks["candidates"][candidate_id]
        fields = candidate["fields"]
        parts = []
        for field in ("rent_pcm", "bedrooms", "floor", "area_m2"):
            fact = fields[field]
            if fact["value"] is not None:
                parts.append(FIELDS[field][2] + " " + _formatted(field, fact["value"]))
        detail = "；".join(parts) if parts else "尚無足夠的單戶數值可比較"
        if result["failed_requirement_ids"]:
            failures = []
            for key in result["failed_requirement_ids"]:
                check, row = result["checks"][key], rows[key]
                failures.append(_requirement_label(row) + "，來源列為" + _formatted(row["field"], check["value"]))
            conclusion = "排除：" + "；".join(failures) + "。"
        else:
            conclusions = []
            for key in result["open_requirement_ids"]:
                row, check = rows[key], result["checks"][key]
                if row["field"] == "listing_identity":
                    continue
                label = _requirement_label(row)
                conclusions.append(label + ("：來源說法符合此項，仍待核實" if check["comparison"] is True else "：待確認"))
            conclusion = "；".join(dict.fromkeys(conclusions)) + "。" if conclusions else "目前記錄的條件已核對；仍須確認實際租賃條件。"
        if result["advisory_failed_requirement_ids"]:
            advisory = ["「" + _requirement_label(rows[key]) + "」" for key in result["advisory_failed_requirement_ids"]]
            conclusion += "來源記載不符偏好：" + "、".join(advisory) + "；這項偏好未作為排除條件。"
        # Actor labels are private proposal metadata. They can contain verdicts.
        retrieved = metadata[proposal_row["source_url"]]["retrieved_at"]
        dated = re.match(r"\d{4}-\d{2}-\d{2}", retrieved or "")
        date_text = "保存於 " + dated.group() if dated else "保存日期未提供"
        paragraphs.append("**" + labels[candidate_id] + "**（[房源廣告](" + proposal_row["source_url"].replace("(", "%28").replace(")", "%29") + ")，" + date_text + "）：" + detail + "。" + conclusion)
        focus = []
        for field in proposal["focus_fields"]:
            if field in ("rent_pcm", "bedrooms", "floor", "area_m2"):
                continue
            fact = fields[field]
            focus.append(FIELDS[field][2] + "：" + ("來源列為" + _formatted(field, fact["value"]) + "，仍待核實" if fact["value"] is not None else "未確認"))
        if focus:
            paragraphs.append("；".join(focus) + "。")
    if presentation["todos"]:
        paragraphs.append("下一步：" + "；".join(presentation["todos"]) + "。")
    if unresolved:
        excerpts = [quote if len(quote) <= 200 else quote[:199] + "…" for quote in unresolved[:3]]
        remainder = "，另有 " + str(len(unresolved) - 3) + " 項" if len(unresolved) > 3 else ""
        paragraphs.append("仍待釐清的原要求共 " + str(len(unresolved)) + " 項" + remainder + "：\n" +
                          "\n".join("- 「" + quote + "」" for quote in excerpts) +
                          ("\n此處為節錄，完整原文保留在條件清單。" if len(unresolved) > 3 or any(len(q) > 200 for q in unresolved[:3]) else ""))
    return {"message": "\n\n".join(paragraphs), "questions": questions}


def accept(proposal, user_inputs, revision, sources):
    """Produce the only publishable reply/ranking/TODO from current host inputs.

    proposal = {candidates:[{source_url,label}], focus_fields:[FOCUS_FIELDS...]};
    label is retained privately and never used in the formal reply. sources maps
    exact URL to {text,retrieved_at,sha256,ok,identity:'unit'|'unknown'}.
    The trusted host supplies source identity and pins text independently. The
    parser also requires a supported single-property description in that text.
    """
    proposal = _proposal(proposal)
    _require(type(sources) is dict and all(type(key) is str for key in sources), "sources must be a URL map")
    normalized = normalize(user_inputs, revision)
    constraints = deepcopy(normalized["constraints"])
    evidence = dict(schema_version=eligibility.EVIDENCE_SCHEMA, sources={}, candidates=[])
    metadata = {}
    for row in proposal["candidates"]:
        url = row["source_url"]
        source_id, text, fields, source_meta = _source_facts(url, sources.get(url))
        metadata[url] = source_meta
        evidence["sources"][source_id] = text
        evidence["candidates"].append({"id": "candidate-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20], "fields": fields})
    # Source receipts are part of the independent eligibility evidence pin, too.
    evidence["sources"]["host-source-metadata"] = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")) or "{}"
    pins = dict(revision=revision, constraints_sha256=_hash(constraints), evidence_sha256=_hash(evidence))
    checks = eligibility.evaluate(constraints, evidence, **pins)
    indexed = {row["id"]: row for row in evidence["candidates"]}
    eligible = [key for key, row in checks["candidates"].items()
                if row["status"] != "blocked" and indexed[key]["fields"]["listing_identity"]["value"] is True]
    eligible.sort(key=lambda key: (len(checks["candidates"][key]["advisory_failed_requirement_ids"]),
                                  len(checks["candidates"][key]["open_requirement_ids"]),
                                  indexed[key]["fields"]["rent_pcm"]["value"] if indexed[key]["fields"]["rent_pcm"]["value"] is not None else float("inf"), key))
    recommendation = dict(schema_version=eligibility.RECOMMENDATION_SCHEMA, binding=deepcopy(pins),
                          first_choice=eligible[0] if eligible else None, ranking=[], backups=[],
                          blocked=[], not_selected=[], todos=[])
    for key, row in checks["candidates"].items():
        if row["status"] == "blocked":
            recommendation["blocked"].append({"candidate_id": key, "failed_requirement_ids": row["failed_requirement_ids"]})
        elif key not in eligible:
            recommendation["not_selected"].append(key)
    for key in eligible:
        row = checks["candidates"][key]
        recommendation["ranking"].append({"candidate_id": key, "status": row["status"],
                                           "open_requirement_ids": row["open_requirement_ids"], "exception_ids": row["exception_ids"]})
        if row["open_requirement_ids"]:
            recommendation["todos"].append({"id": "investigate-" + key, "candidate_id": key,
                "action": "investigate", "requirement_ids": row["open_requirement_ids"], "binding": deepcopy(pins)})
    validation = eligibility.validate_recommendation(constraints, evidence, recommendation, **pins)
    _require(validation["valid"] is True, "internal recommendation validation failed")
    presentation = _presentation(constraints, evidence, recommendation)
    reply = _render(constraints, evidence, checks, recommendation, proposal, metadata, normalized["unresolved_intent"], presentation)
    return dict(schema_version=SCHEMA, proposal=proposal, normalization=normalized,
                constraints=constraints, evidence=evidence, pins=pins, checks=checks,
                recommendation=recommendation, reply=reply, presentation=presentation, source_metadata=metadata,
                notes={"parser_version": PARSER_VERSION, "source_truth_verified": False,
                       "complete_natural_language_understanding": False,
                       "ranking_basis": "Advisory failures, open-check count, recorded monthly rent, stable URL identifier; no claim of best housing quality",
                       "payment_authorized": False})


def validate_artifact(artifact, user_inputs, revision, sources):
    """Recompute every official field; edits, stale receipts or revisions fail."""
    try:
        _require(type(artifact) is dict and "proposal" in artifact, "artifact lacks proposal")
        expected = accept(artifact["proposal"], user_inputs, revision, sources)
        _require(_hash(artifact) == _hash(expected), "artifact differs from the current recomputed result")
        return {"valid": True, "errors": []}
    except (LiveEligibilityError, eligibility.EligibilityError, TypeError, ValueError, OverflowError) as exc:
        return {"valid": False, "errors": [str(exc)]}


def _load(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise LiveEligibilityError("duplicate JSON key: " + key)
            out[key] = value
        return out
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(LiveEligibilityError("nonfinite JSON number")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("accept", "validate"):
        command = sub.add_parser(name)
        command.add_argument("--input", required=True)
        if name == "validate":
            command.add_argument("--artifact", required=True)
    args = parser.parse_args(argv)
    try:
        request = _load(args.input)
        _object(request, {"proposal", "user_inputs", "revision", "sources"}, where="input")
        if args.command == "accept":
            result = accept(**request)
        else:
            artifact = _load(args.artifact)
            # The CLI also binds the independently supplied original proposal.
            _require(type(artifact) is dict and artifact.get("proposal") == _proposal(request["proposal"]), "artifact proposal differs from input")
            result = validate_artifact(artifact, request["user_inputs"], request["revision"], request["sources"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 1 if result.get("valid") is False else 0
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
