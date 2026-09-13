#!/usr/bin/env python3
"""Compile and check a bounded host-owned user-intent frame.

Part of Pea Princess by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Source: the trusted host's ordered text conversation, not an external source.
No key, login, fee, network, execution or persistence; robots/ToS do not apply.
Python 3.9 standard library. This is a finite grammar, not a semantic verifier.

    python3 intent_guard.py compile transcript.json
    python3 intent_guard.py check transcript.json reply.json

Transcript: {"messages": [{"id": "u1", "role": "user", "text": "..."}]}.
Reply: {"intent_claims": {"revision": "...", "conditions": [...]}, "text": "..."}.
Success/check results are one JSON object. Invalid input exits 2; a failed
check exits 1. See references/intent-guard.md for the host trust boundary.
"""

import argparse
import hashlib
import json
import re
import sys

import intent_context


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_REPLY_BYTES = 128 * 1024
SCHEMA_VERSION = 1
GRAMMAR_VERSION = "quiet-light-v2"
FIELDS = ("quiet", "morning_direct_sun", "daylight")
STRENGTHS = ("mandatory", "preference", "bonus")


class IntentGuardError(ValueError):
    """A host frame/input is invalid or exceeds its declared bounds."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _source(message, start, end):
    return {"message_id": message["id"], "quote": message["text"][start:end],
            "start": start, "end": end}


def _matches(pattern, text):
    return bool(re.search(pattern, text, flags=re.I))


QUIET = r"安靜|寧靜|quiet(?:ness)?"
DIRECT = r"直射|direct\s+(?:morning\s+)?(?:sun(?:light)?|light)"
LIGHT = r"採光|采光|自然光|(?:早上|早晨|上午).{0,8}(?:有光|陽光)|daylight|natural\s+light|morning\s+(?:sun(?:light)?|light)"
TARGET = "(?:%s|%s|%s)" % (QUIET, DIRECT, LIGHT)
HARD = r"硬條件|必要條件|必須|一定要|一定得|非得|不可妥協|mandatory|must(?:\s+have)?|required|non[- ]negotiable|hard\s+(?:condition|requirement|filter)"
PREF = r"偏好|希望|喜歡|想要|想找|想住|prefer(?:ence)?|would\s+like|ideally|nice\s+to\s+have"
BONUS = r"(?:當|作為|改成|改為|列為|是|只算|算|作)\s*(?:為)?加分|加分項|(?:only\s+a\s+)?bonus|nice[- ]to[- ]have"
SCOPED = r"如果|假如|若是|若.{0,24}(?:則|就)|除非|前提是|條件是|只有.{0,60}才|只限|僅限|這(?:一)?(?:間|戶)|房源\s*[A-Za-zＡ-Ｚ0-9]|候選\s*[A-Za-z0-9]|\b(?:if|unless|provided|assuming|as\s+long\s+as|except|only\s+for|this\s+(?:flat|unit|candidate)|candidate\s+[A-Z0-9])\b"
ADVICE_ONLY = r"不要替我(?:做)?決定|還不要.{0,8}決定|先.{0,12}(?:給我|提供).{0,8}建議|先別改|你怎麼看|你覺得呢|\b(?:what\s+do\s+you\s+think|should\s+we|do\s+you\s+recommend|advice\s+only|do\s+not\s+decide|don't\s+decide)\b"
NO_CHANGE = r"(?:不要|別|勿|先不|不允許|不准|不可|不得|不可以|不能|不應該?|不該|沒有|未曾|尚未|還沒|並未)(?:把|將)?.{0,32}(?:改成|改為|變成|升為|設為|列為|定為|視為|當作|當加分|當成)|(?:不想|不希望).{0,30}(?:安靜|直射|採光)|(?:沒(?:有)?|未曾|尚未|並未)(?:說|要求|同意|確認|決定|設定).{0,30}(?:安靜|直射|採光)|\b(?:do\s+not|don't)\s+(?:change|make|turn|promote|treat|list|set|consider|prefer|want)\b"
NOT_HARD = r"(?:不是|並非|不再是|不是說|非|未必是?).{0,6}(?:硬|必要)|(?:不能|不應|不該).{0,8}(?:硬條件|必要條件|必須)|不(?:必|用|需|強求|要求|再要求|一定要)|沒有.{0,6}(?:硬|必要)|\bno\s+(?:need|requirement)\b|\bno\s+longer\s+(?:a\s+)?(?:hard\s+(?:requirement|condition|filter)|mandatory|required|a\s+must)\b|\bnot\s+(?:be\s+)?(?:a\s+)?(?:hard\s+(?:requirement|condition|filter)|must|required|mandatory|necessary)\b|\b(?:do\s+not|don't)\s+(?:need|require)\b"
WORKFLOW_NEGATION = r"(?:不要|不用|不需要|不必|別|先不).{0,12}(?:問|詢問|追問|討論|解釋|查|查證|研究|判斷|確認)|\b(?:do\s+not|don't|no\s+need\s+to)\s+(?:ask|discuss|check|research|explain|verify)\b"
REPORTED = r"(?:仲介|房東|網站|文件|附件|文章|廣告|他|她).{0,4}(?:說|寫|提到|表示)|\b(?:the\s+(?:agent|landlord|document|website|listing)|he|she)\s+(?:says|said|states|requires)\b"


def _mask_data(text, inline_quotes=True):
    """Preserve offsets while excluding explicitly delimited copied data.

    This does not authenticate unmarked prose pasted into a user message.
    The host must keep attachment/source bodies out of the user-authority lane.
    """
    spans = []
    patterns = [r"```[\s\S]*?(?:```|\Z)", r"~~~[\s\S]*?(?:~~~|\Z)",
                r"(?m)^\s*>[^\n]*(?:\n|\Z)",
                r"<(?:untrusted_text|document|attachment|source)(?:\s[^>]*)?>[\s\S]*?(?:</(?:untrusted_text|document|attachment|source)>|\Z)",
                r"(?:以下(?:是|為)(?:文件|附件|網頁|引用|房源廣告)|文件內容|附件內容|quoted\s+(?:document|source)\s*:)[\s\S]*\Z"]
    if inline_quotes:
        patterns += [r"「[^」]*」", r"『[^』]*』", r'"[^"\n]*"', r"“[^”]*”", r"`[^`\n]+`"]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            # Explicitly assigning a quoted short *condition label* is a user
            # action, unlike quoting a document or a complete instruction.
            # Keep the original quote characters and offsets in that case.
            label = match.group()[1:-1]
            quoted_label = (inline_quotes and match.group()[:1] in ('「', '『', '"', '“')
                            and len(label) <= 48 and _matches(TARGET, label)
                            and not _matches(HARD + r"|[。！？!?;；]|忽略|指令|ignore|instruction|role", label)
                            and _matches(r"(?:我(?:目前|現在)?(?:把|將)|請(?:把|將))\s*\Z", text[max(0, match.start() - 20):match.start()])
                            and _matches(r"\A\s*(?:列為|當作|設為|改成|改為).{0,8}(?:" + HARD + "|" + PREF + "|加分)", text[match.end():match.end() + 36]))
            if not quoted_label:
                spans.append((match.start(), match.end()))
    # Merge overlapping spans before retaining exclusions; no source is lost.
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    chars = list(text)
    for start, end in merged:
        for i in range(start, end):
            if chars[i] not in "\r\n":
                chars[i] = " "
    return "".join(chars), merged


def _sentences(text):
    cursor = 0
    spans = []
    for match in re.finditer(r"[。！？!?\n;；]|[.](?=\s|\Z)", text):
        spans.append((cursor, match.end()))
        cursor = match.end()
    if cursor < len(text):
        spans.append((cursor, len(text)))
    for start, end in spans:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            yield start, end


def _clauses(text, start, end):
    # Split differing strengths before interpreting their target fields.
    segment = text[start:end]
    cursor = 0
    for separator in re.finditer(r"[,，]|但(?:是)?|而且|\bbut\b|\band\b(?=\s+(?:I\b|quiet\b|daylight\b|morning\b|direct\b|natural\b))", segment, flags=re.I):
        if separator.start() > cursor:
            yield start + cursor, start + separator.start()
        cursor = separator.end()
    if cursor < len(segment):
        yield start + cursor, end


def _transition(frame, active, field, strength, source):
    previous = active.get(field)
    if strength is None:
        if previous is None:
            return
        del active[field]
    else:
        predicates = {
            "quiet": {"kind": "quietness", "value": True},
            "morning_direct_sun": {"kind": "direct_sunlight", "time": "morning"},
            "daylight": {"kind": "natural_light", "minimum": None},
        }
        active[field] = {"id": field, "field": field, "strength": strength,
                         "scope": {"kind": "global"}, "predicate": predicates[field],
                         "source": source}
    frame["transitions"].append({"field": field,
                                 "from": previous["strength"] if previous else None,
                                 "to": strength, "source": source})


def build_frame(messages):
    """Compile an exact role index plus conservative quiet/daylight conditions.

    Roles/IDs and complete original messages must come from the trusted host.
    Assistant text is never parsed as authorization. The host must remove its
    own question prefix from submitted form answers before assigning user role.
    Unsupported, scoped, quoted or ambiguous text is retained, not made hard.
    """
    try:
        index = intent_context.build_frame(messages)
    except intent_context.IntentContextError as exc:
        raise IntentGuardError(str(exc)) from None
    frame = {"schema_version": SCHEMA_VERSION, "grammar_version": GRAMMAR_VERSION,
             "transcript_sha256": index["transcript_sha256"],
             "message_order": index["message_order"],
             "user_statements": index["user_statements"],
             "assistant_context": index["assistant_context"],
             "conditions": [], "transitions": [], "unresolved": [],
             "capabilities": {"fields": list(FIELDS), "scope": "global",
                              "natural_language_complete": False}}
    active = {}
    for message in messages:
        if message["role"] != "user":
            continue
        text = message["text"]
        masked, excluded = _mask_data(text)
        for start, end in excluded:
            frame["unresolved"].append({"reason": "quoted_or_source_data", "source": _source(message, start, end)})
        advice_only = _matches(ADVICE_ONLY, masked)
        detached_predicate = _matches(r"[。;；.]\s*(?:前提是|條件是|provided\s+that|as\s+long\s+as)", masked)
        for start, end in _sentences(masked):
            sentence = masked[start:end]
            if not _matches(TARGET, sentence):
                frame["unresolved"].append({"reason": "outside_supported_grammar", "source": _source(message, start, end)})
                continue
            if _matches(SCOPED, sentence) or detached_predicate:
                frame["unresolved"].append({"reason": "scoped_or_conditional", "source": _source(message, start, end)})
                continue
            if _matches(REPORTED, sentence):
                frame["unresolved"].append({"reason": "reported_source_not_authority", "source": _source(message, start, end)})
                continue
            if advice_only:
                frame["unresolved"].append({"reason": "advice_or_proposal_not_adopted", "source": _source(message, start, end)})
                continue
            # An explicit polite imperative remains a direct change even if it
            # ends in a courtesy question. An ordinary question is not one.
            imperative = _matches(r"(?:請|幫我)(?:把|將)?.{0,30}(?:改成|改為|當|取消)|\bplease\b.{0,40}(?:make|change|remove|drop|treat)", sentence)
            if _matches(r"[?？]|(?:嗎|是否)|\b(?:could\s+we|can\s+we|would\s+you)\b", sentence) and not imperative:
                frame["unresolved"].append({"reason": "question_not_adopted", "source": _source(message, start, end)})
                continue
            for lo, hi in _clauses(masked, start, end):
                clause = masked[lo:hi].strip()
                if not clause:
                    continue
                source = _source(message, lo, hi)
                if _matches(NO_CHANGE, clause):
                    frame["unresolved"].append({"reason": "negated_change", "source": source})
                    continue
                if _matches(WORKFLOW_NEGATION, clause):
                    frame["unresolved"].append({"reason": "workflow_not_condition_change", "source": source})
                    continue
                quiet = _matches(QUIET, clause)
                direct = _matches(DIRECT, clause)
                daylight = _matches(LIGHT, clause)
                if quiet and (direct or daylight):
                    frame["unresolved"].append({"reason": "mixed_targets_require_scope", "source": source})
                    continue
                applied = False
                not_hard = _matches(NOT_HARD, clause)
                if quiet:
                    if _matches(r"(?:取消|移除|刪除).{0,12}(?:安靜|quiet)|(?:安靜|quiet).{0,12}(?:不用考慮|不再考慮)|(?:remove|drop).{0,12}quiet", clause):
                        _transition(frame, active, "quiet", None, source)
                        applied = True
                    elif _matches(PREF, clause):
                        _transition(frame, active, "quiet", "preference", source)
                        applied = True
                    elif not_hard:
                        # A refusal is not evidence for a new preference. Retire
                        # a known hard requirement; preserve an existing softer
                        # preference without fabricating an additional choice.
                        if active.get("quiet", {}).get("strength") == "mandatory":
                            _transition(frame, active, "quiet", None, source)
                        frame["unresolved"].append({"reason": "no_hard_requirement_declared", "source": source})
                        applied = True
                    elif _matches(HARD, clause):
                        _transition(frame, active, "quiet", "mandatory", source)
                        applied = True
                elif direct:
                    relaxed = not_hard or _matches(r"不是直射也(?:沒關係|可以)|非直射也(?:沒關係|可以)|(?:取消|移除|刪除).{0,20}直射|(?:直射).{0,15}(?:取消|不重要)|(?:remove|drop).{0,30}direct", clause)
                    if relaxed:
                        _transition(frame, active, "morning_direct_sun", None, source)
                        applied = True
                    elif _matches(r"早上|早晨|上午|morning", clause):
                        if _matches(HARD, clause):
                            _transition(frame, active, "morning_direct_sun", "mandatory", source)
                            applied = True
                        elif _matches(PREF, clause):
                            _transition(frame, active, "morning_direct_sun", "preference", source)
                            applied = True
                elif daylight:
                    if _matches(BONUS, clause):
                        _transition(frame, active, "morning_direct_sun", None, source)
                        _transition(frame, active, "daylight", "bonus", source)
                        applied = True
                    elif _matches(r"(?:取消|移除|刪除).{0,10}(?:採光|自然光)|(?:採光|自然光).{0,10}(?:不用考慮|不再考慮)|(?:remove|drop).{0,15}(?:daylight|natural\s+light)", clause):
                        _transition(frame, active, "morning_direct_sun", None, source)
                        _transition(frame, active, "daylight", None, source)
                        applied = True
                    elif _matches(PREF, clause) or _matches(r"(?:早上|早晨|上午).{0,10}有光就好", clause):
                        _transition(frame, active, "daylight", "preference", source)
                        applied = True
                    elif not_hard:
                        for field in ("daylight", "morning_direct_sun"):
                            if active.get(field, {}).get("strength") == "mandatory":
                                _transition(frame, active, field, None, source)
                        frame["unresolved"].append({"reason": "no_hard_requirement_declared", "source": source})
                        applied = True
                    elif _matches(HARD, clause):
                        _transition(frame, active, "daylight", "mandatory", source)
                        applied = True
                if not applied:
                    frame["unresolved"].append({"reason": "outside_supported_grammar", "source": source})
    frame["conditions"] = [active[field] for field in FIELDS if field in active]
    frame["revision"] = _digest(frame)
    return frame


def _check_frame(frame):
    if type(frame) is not dict or frame.get("schema_version") != SCHEMA_VERSION:
        raise IntentGuardError("frame must be an unmodified build_frame result")
    candidate = dict(frame)
    revision = candidate.pop("revision", None)
    try:
        valid = type(revision) is str and revision == _digest(candidate)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        valid = False
    if not valid or candidate.get("grammar_version") != GRAMMAR_VERSION:
        raise IntentGuardError("frame integrity or grammar version mismatch; rebuild from host messages")


def expected_claims(frame):
    """The exact echo required from an actor; it grants no mutation authority."""
    _check_frame(frame)
    return {"revision": frame["revision"], "conditions": [
        {"id": row["id"], "strength": row["strength"]} for row in frame["conditions"]]}


def validate_claims(frame, claims):
    """Return findings for malformed, stale, missing, invented or altered claims."""
    expected = expected_claims(frame)
    findings = []
    if type(claims) is not dict or set(claims) != {"revision", "conditions"}:
        return {"ok": False, "findings": [{"code": "invalid_claims_schema"}]}
    if type(claims["revision"]) is not str or claims["revision"] != expected["revision"]:
        findings.append({"code": "stale_revision"})
    rows = claims["conditions"]
    if type(rows) is not list or len(rows) > len(FIELDS):
        return {"ok": False, "findings": findings + [{"code": "invalid_conditions_schema"}]}
    wanted = {row["id"]: row["strength"] for row in expected["conditions"]}
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {"id", "strength"}
                or type(row["id"]) is not str or type(row["strength"]) is not str):
            findings.append({"code": "invalid_condition_schema"})
            continue
        key, strength = row["id"], row["strength"]
        if key in seen:
            findings.append({"code": "duplicate_condition", "id": key})
        seen.add(key)
        if key not in wanted:
            findings.append({"code": "unknown_condition", "id": key})
        elif strength != wanted[key]:
            findings.append({"code": "condition_strength_mismatch", "id": key,
                             "expected": wanted[key], "actual": strength})
    for key in sorted(set(wanted) - seen):
        findings.append({"code": "missing_condition", "id": key})
    return {"ok": not findings, "findings": findings}


_DECLARED_LABELS = {
    "mandatory": r"硬條件|必要條件|mandatory|required|(?:a\s+)?must|(?:a\s+)?hard\s+(?:condition|requirement|filter)",
    "preference": r"偏好(?:條件)?|(?:a\s+)?preference|preferred\s+(?:condition|requirement)",
    "bonus": r"加分(?:項(?:目)?)?|(?:a\s+)?bonus",
}
_DECLARED_LABEL = "(?:%s)" % "|".join(_DECLARED_LABELS.values())
_LABEL_SPACE = r"[\s*_`「」『』\"“”]{0,12}"
_CHANGE_VERB = r"(?:改為|改成|變為|變成|調整為|調整成|降為|降成|升為|升成|列為|設為|保留為|當作)"
_EXPLICIT_USER = r"你(?:的|目前的|現在的|已確認的|已(?:經)?(?:決定|確認|指定|設定|要求)|要求|指定|設定|決定|確認)|依你|按照你|根據你|\b(?:your\s+(?:current\s+)?(?:hard\s+)?(?:condition|requirement|filter)|you\s+(?:have\s+)?(?:require|required|confirmed|specified|decided))"


def _historical_clause(clause):
    """An explicitly past condition is not an assertion about the current frame."""
    return (_matches(r"原本|原先|以前|之前|先前|曾經|當時|過去|起初|一度|\b(?:previously|formerly|earlier|used\s+to)\b", clause)
            and not _matches(r"現在|目前|如今|現階段|\b(?:now|currently|today)\b", clause))


def _context_intro(prefix):
    """Carry a standalone reporting/history intro, not an unrelated past clause."""
    history_intro = re.fullmatch(r"\s*(?:以前|過去|之前|曾經|原本|previously|formerly|earlier)\s*[,，:：]\s*", prefix, flags=re.I)
    return bool(history_intro or (_matches(REPORTED, prefix) and not _matches(TARGET, prefix)))


def _denied_assertion(clause):
    return _matches(r"(?:這個|此|上述)?(?:說法|描述|陳述|主張).{0,8}(?:不成立|不正確|不對|不是真的|錯誤)|\b(?:this|that)\s+(?:claim|statement)\s+is\s+(?:false|incorrect|wrong)\b", clause)


def _current_strengths(field, clause, context=None, prefix=""):
    """Recognize explicit current labels/changes, not implicit semantic preferences.

    A transition's destination is asserted now; its former mandatory label is
    history. Deliberate advice, reported/negated statements and marked history
    remain outside this small grammar. Bare option labels are not assertions.
    """
    personal_advice = (_matches(r"我(?:會|認為|覺得|傾向)|\b(?:I\s+would|I\s+think|in\s+my\s+(?:view|assessment))\b", clause)
                       and not _matches(_EXPLICIT_USER, clause))
    if (_historical_clause(clause) or _context_intro(prefix) or _denied_assertion(clause) or _matches(REPORTED, clause) or _matches(NO_CHANGE, clause)
            or _matches(SCOPED, context or clause) or _matches(r"[?？]|嗎|是否", clause) or personal_advice
            or _matches(r"我(?:會)?(?:建議|推薦)|我的建議|可以考慮|是否要|要不要|你可以選|\b(?:I\s+(?:would\s+)?recommend|I\s+suggest|my\s+advice|consider|should\s+we)\b", clause)
            or _matches(r"(?:錯誤|不實|並非事實|不是說)|\b(?:false\s+that|not\s+true\s+that|incorrect\s+to\s+say)\b", clause)):
        return []
    target = {"quiet": QUIET, "morning_direct_sun": r"直射(?:陽光|光線|日照)?|direct\s+(?:morning\s+)?(?:sun(?:light)?|light)",
              "daylight": LIGHT}[field]
    # The direct-sun dimension must not be reinterpreted as generic daylight.
    if field == "daylight" and _matches(DIRECT, clause):
        return []
    transition = (r"(?:(?:已經|已|現在|目前)?(?:由|從)" + _LABEL_SPACE + _DECLARED_LABEL + _LABEL_SPACE + _CHANGE_VERB
                  + r"|\s*(?:(?:has|have|was|is)\s+)?(?:now\s+)?(?:changed|moved|reclassified|downgraded|softened|relaxed|promoted)\s+from\s+"
                  + _DECLARED_LABEL + r"\s+(?:to|into)\s+)")
    current = (r"(?:(?:現在|目前|已經|已|仍然|仍|現階段)?(?:是|為|算是|算作|算|屬於|成為|" + _CHANGE_VERB + r")"
               + r"|\s*(?:(?:is|are|remains?)\s+(?:now\s+|still\s+|currently\s+)?|(?:has|have)\s+(?:now\s+)?(?:become|been\s+(?:set|changed|reclassified|downgraded|promoted)\s+to)\s+))")
    prefix = "(?:%s)%s(?:條件|要求|condition|requirement)?%s" % (target, _LABEL_SPACE, _LABEL_SPACE)
    suffix = _LABEL_SPACE + r"(?:你的|你目前的|你設定的|your\s+|only\s+)?" + _LABEL_SPACE
    found = []
    for strength, label in _DECLARED_LABELS.items():
        # Chinese labels can be followed immediately by explanatory prose.
        pattern = prefix + "(?:" + transition + "|" + current + ")" + suffix + "(?:" + label + r")(?=[^A-Za-z]|\Z)"
        for match in re.finditer(pattern, clause, flags=re.I):
            found.append({"strength": strength, "start": match.start(), "end": match.end()})
    return found


def validate_reply(frame, text, *, proposal=False):
    """Check a small set of explicit prose contradictions, not overall quality.

    Checks visible answer prose and independently supplied question/option text
    can use this function. Unselected proposals and analyst advice are allowed.
    Findings include original spans, permitting a reviewer to inspect context.
    """
    _check_frame(frame)
    if type(proposal) is not bool:
        raise IntentGuardError("proposal context must be a host-supplied boolean")
    if type(text) is not str:
        raise IntentGuardError("reply text must be a string")
    try:
        size = len(text.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        raise IntentGuardError("reply text contains an unpaired Unicode surrogate") from None
    if size > MAX_REPLY_BYTES:
        raise IntentGuardError("reply text exceeds %d UTF-8 bytes" % MAX_REPLY_BYTES)
    active = {row["field"]: row["strength"] for row in frame["conditions"]}
    retired = {row["field"] for row in frame["transitions"] if row["to"] is None} - set(active)
    user_text = "\n".join(row["text"] for row in frame["user_statements"])
    masked, _ = _mask_data(text, inline_quotes=False)
    findings = []
    for start, end in _sentences(masked):
        sentence = masked[start:end]
        # Teaching examples, counterexamples and explicit advice cannot prove
        # the speaker attributed a condition to the user. Prefer false negatives
        # to vetoing ordinary analysis merely because it uses the word 'must'.
        counterexample = _matches(r"錯誤(?:說法|示範)|不要(?:說|寫)|不能(?:說|寫)|例如.{0,12}[「\"]|\b(?:incorrect\s+example|do\s+not\s+say|don't\s+say|for\s+example)\b", sentence)
        advice = _matches(r"我(?:會)?(?:建議|推薦)|我的建議|可以考慮|是否要|要不要|你可以選|\b(?:I\s+(?:would\s+)?recommend|I\s+suggest|my\s+advice|consider|would\s+you\s+like|should\s+we)\b", sentence)
        if counterexample:
            continue
        explicit_user = _matches(_EXPLICIT_USER, sentence)
        if proposal and not explicit_user:
            continue
        offered_action = _matches(r"\A\s*(?:請)?(?:把|將)|\A\s*(?:make|treat|change|set)\b", sentence)
        offered_question = (_matches(r"[?？]|嗎", sentence)
                            and _matches(r"你(?:要|想|希望|願意)|要不要|\A\s*(?:要|是否)|\b(?:would\s+you\s+like|do\s+you\s+want)\b", sentence))
        if (offered_action or offered_question) and not explicit_user:
            continue
        for field, target in (("quiet", QUIET), ("morning_direct_sun", DIRECT), ("daylight", LIGHT)):
            if not _matches(target, sentence):
                continue
            target_clauses = []
            explicit_mismatch = False
            for lo, hi in _clauses(masked, start, end):
                clause = masked[lo:hi]
                prefix = masked[start:lo]
                # A direct-sun clause belongs to that exact dimension. A later
                # generic-daylight clause in the same sentence still needs checking.
                if field == "daylight" and _matches(DIRECT, clause):
                    continue
                if (not _matches(target, clause) or _historical_clause(clause)
                        or _context_intro(prefix) or _denied_assertion(clause)):
                    continue
                assertions = _current_strengths(field, clause, sentence, prefix)
                for assertion in assertions:
                    if assertion["strength"] != active.get(field):
                        left, right = lo, hi
                        findings.append({"code": "retired_condition_reintroduced" if field in retired else "condition_strength_mismatch",
                                         "field": field, "expected_strength": active.get(field),
                                         "actual_strength": assertion["strength"], "quote": text[left:right],
                                         "start": left, "end": right})
                        explicit_mismatch = True
                if not assertions:
                    target_clauses.append(clause)
            if explicit_mismatch or active.get(field) == "mandatory":
                continue
            hard = any(_matches(HARD, clause) for clause in target_clauses)
            negated = any(_matches(r"(?:不是|並非|不再是|非|不應(?:是|變成)?|不能(?:當成|變成)|不要.{0,8}(?:當|改)).{0,8}(?:硬條件|必要條件|必須)|\b(?:not|isn't|is\s+not|not\s+a)\s+(?:a\s+)?(?:hard|mandatory|required|must)\b", clause)
                          for clause in target_clauses)
            user_gate = explicit_user and _matches(r"(?:不符合|不滿足|違反).{0,22}你.{0,12}(?:核心|必要|硬).{0,6}條件", sentence)
            compound_hard = _matches(r"(?:兩|二|two)\s*個?\s*(?:硬條件|必要條件|hard\s+(?:conditions|requirements))", sentence)
            direct_hard = any(_matches(r"(?:%s).{0,12}(?:是|仍是|屬於|為|：|:)\s*(?:你的)?\s*(?:硬條件|必要條件|mandatory|a\s+must)" % target, clause)
                              for clause in target_clauses)
            if (hard and not negated and (explicit_user or compound_hard or direct_hard)
                    and not (advice and not explicit_user)) or user_gate:
                findings.append({"code": "unsupported_hard_requirement", "field": field,
                                 "expected_strength": active.get(field), "quote": text[start:end],
                                 "start": start, "end": end})
        if (not _matches(r"通風|ventilat", user_text) and _matches(r"通風|ventilat", sentence)
                and explicit_user and _matches(HARD, sentence) and not advice):
            findings.append({"code": "invented_ventilation_requirement", "field": "ventilation",
                             "quote": text[start:end], "start": start, "end": end})
    # The historical error spans a semicolon: a conditional acceptance gate
    # followed by 'otherwise this violates your core conditions'. Preserve that
    # whole paragraph rather than applying the assertion to an isolated quote.
    for match in re.finditer(r"[^\n]{1,1200}", masked):
        paragraph = match.group()
        if (active.get("quiet") != "mandatory" and _matches(QUIET, paragraph)
                and _matches(r"只有.{0,240}才.{0,240}否則.{0,100}不符合你.{0,16}(?:核心|必要|硬)條件", paragraph)
                and not _matches(r"錯誤(?:說法|示範)|不要(?:說|寫)|例如", paragraph)):
            if not any(f["field"] == "quiet" and f["start"] >= match.start()
                       and f["end"] <= match.end() for f in findings):
                findings.append({"code": "unsupported_hard_requirement", "field": "quiet",
                                 "expected_strength": active.get("quiet"), "quote": text[match.start():match.end()],
                                 "start": match.start(), "end": match.end()})
    return {"ok": not findings, "findings": findings,
            "semantic_coverage": "finite quiet/daylight authority contradictions only"}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise IntentGuardError("JSON contains a duplicate object key")
        value[key] = item
    return value


def _reject_constant(_value):
    raise IntentGuardError("JSON non-finite numbers are not allowed")


def _load(path):
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with open(path, "rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise IntentGuardError("input exceeds %d bytes" % MAX_INPUT_BYTES)
    try:
        return json.loads(raw.decode("utf-8", errors="strict"),
                          object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise IntentGuardError("input must be bounded valid UTF-8 JSON") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("transcript", nargs="?", default="-")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("transcript")
    check_parser.add_argument("reply")
    args = parser.parse_args(argv)
    try:
        document = _load(args.transcript)
        if type(document) is not dict or set(document) != {"messages"}:
            raise IntentGuardError("transcript must contain exactly messages")
        frame = build_frame(document["messages"])
        result = frame
        exit_code = 0
        if args.command == "check":
            if args.transcript == "-" and args.reply == "-":
                raise IntentGuardError("only one input may use stdin")
            reply = _load(args.reply)
            if type(reply) is not dict or set(reply) != {"intent_claims", "text"}:
                raise IntentGuardError("reply must contain exactly intent_claims and text")
            claims = validate_claims(frame, reply["intent_claims"])
            prose = validate_reply(frame, reply["text"])
            result = {"ok": claims["ok"] and prose["ok"], "revision": frame["revision"],
                      "claims": claims, "reply": prose}
            exit_code = 0 if result["ok"] else 1
    except (IntentGuardError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
