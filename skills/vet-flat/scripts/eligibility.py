#!/usr/bin/env python3
"""Compare trusted, normalized conditions with retained local evidence.

Offline, standard-library only; no official external source, login, key, fee,
network access or robots/ToS interaction. Source quotes establish retention,
not truth. The trusted caller supplies current revision and canonical SHA pins.

Usage: eligibility.py evaluate --constraints conditions.json --evidence facts.json
       --revision 3 --constraints-sha256 <sha256> --evidence-sha256 <sha256>
       eligibility.py validate <same options> --recommendation recommendation.json
"""
import argparse
from datetime import date
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys

CONSTRAINTS_SCHEMA = "vet-flat/eligibility-constraints/1"
EVIDENCE_SCHEMA = "vet-flat/eligibility-evidence/1"
RECOMMENDATION_SCHEMA = "vet-flat/eligibility-recommendation/1"
QUALIFIERS = {"observed", "estimate", "reported", "unknown"}
PIN_KEYS = {"revision", "constraints_sha256", "evidence_sha256"}


class EligibilityError(ValueError):
    """Malformed or stale inputs; no eligibility decision can be accepted."""


def _require(condition, message):
    if not condition:
        raise EligibilityError(message)


def _object(value, required, optional=(), at="object"):
    _require(type(value) is dict, at + " must be an object")
    _require(set(value) >= set(required), at + " missing required fields")
    _require(set(value) <= set(required) | set(optional), at + " has unknown fields")


def _text(value, at):
    _require(type(value) is str and bool(value.strip()), at + " must be a nonempty string")


def _strings(value, at, nonempty=False):
    _require(type(value) is list, at + " must be an array")
    for item in value:
        _text(item, at + " item")
    _require(len(set(value)) == len(value), at + " contains duplicates")
    _require(not nonempty or bool(value), at + " must not be empty")


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _typed(value, kind, at):
    valid = ((kind == "number" and _number(value)) or
             (kind == "boolean" and type(value) is bool) or
             (kind == "string" and type(value) is str))
    _require(valid, at + " does not match type " + kind)


def _unit(value, kind, at):
    if kind == "number":
        _text(value, at)
    else:
        _require(value is None, at + " must be null for nonnumeric fields")


def _scope(value, at):
    _object(value, {"date", "rooms"}, at=at)
    _require(type(value["date"]) is str and
             re.fullmatch(r"\d{4}-\d{2}-\d{2}", value["date"]) is not None,
             at + ".date must be ISO YYYY-MM-DD")
    try:
        date.fromisoformat(value["date"])
    except ValueError as exc:
        raise EligibilityError(at + ".date is invalid") from exc
    _strings(value["rooms"], at + ".rooms", nonempty=True)


def _predicate(row, at, fields, requirement=False):
    required = {"field", "type", "operator", "value", "unit", "basis"}
    if requirement:
        required |= {"id", "mandatory"}
    _object(row, required, {"scope"}, at)
    _text(row["field"], at + ".field")
    _require(type(row["type"]) is str and row["type"] in {"number", "boolean", "string"},
             at + ".type is unsupported")
    _require(type(row["operator"]) is str and row["operator"] in {"lte", "gte", "eq"},
             at + ".operator is unsupported")
    _require(row["type"] == "number" or row["operator"] == "eq",
             at + " ordering requires a number")
    _typed(row["value"], row["type"], at + ".value")
    _unit(row["unit"], row["type"], at + ".unit")
    _strings(row["basis"], at + ".basis", nonempty=True)
    _require(set(row["basis"]) <= QUALIFIERS - {"unknown"}, at + ".basis is unsupported")
    if "scope" in row:
        _scope(row["scope"], at + ".scope")
    spec = (row["type"], row["unit"])
    _require(row["field"] not in fields or fields[row["field"]] == spec,
             at + " conflicts with the field type/unit")
    fields[row["field"]] = spec
    if requirement:
        _text(row["id"], at + ".id")
        _require(type(row["mandatory"]) is bool, at + ".mandatory must be boolean")


def canonical_hash(value):
    """SHA-256 of sorted, compact, UTF-8 JSON; JSON numbers retain their form."""
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EligibilityError("input must be finite UTF-8 JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _binding(revision, constraints_sha256, evidence_sha256):
    _require(type(revision) is int and revision >= 0, "revision must be a nonnegative integer")
    for value in (constraints_sha256, evidence_sha256):
        _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
                 "SHA pins must be lowercase SHA-256 hex")
    return dict(revision=revision, constraints_sha256=constraints_sha256,
                evidence_sha256=evidence_sha256)


def _validate_inputs(constraints, evidence, binding):
    _require(canonical_hash(constraints) == binding["constraints_sha256"], "constraints SHA mismatch")
    _require(canonical_hash(evidence) == binding["evidence_sha256"], "evidence SHA mismatch")
    _object(constraints, {"schema_version", "revision", "requirements", "user_requests", "exceptions"},
            at="constraints")
    _require(constraints["schema_version"] == CONSTRAINTS_SCHEMA, "unsupported constraints schema")
    _require(type(constraints["revision"]) is int and constraints["revision"] == binding["revision"],
             "constraints revision mismatch")
    rows = constraints["requirements"]
    _require(type(rows) is list and bool(rows), "requirements must be a nonempty array")
    fields, requirements = {}, {}
    for row in rows:
        _predicate(row, "requirement", fields, requirement=True)
        _require(row["id"] not in requirements, "duplicate requirement id")
        requirements[row["id"]] = row
    requests = constraints["user_requests"]
    _require(type(requests) is dict, "user_requests must be an object")
    for key, value in requests.items():
        _text(key, "request id")
        _text(value, "request text")
    exceptions = constraints["exceptions"]
    _require(type(exceptions) is list, "exceptions must be an array")
    seen_ids, seen_scopes = set(), set()
    for row in exceptions:
        _object(row, {"id", "requirement_id", "candidate_id", "request_id", "quote", "when"},
                at="exception")
        for key in ("id", "requirement_id", "candidate_id", "request_id", "quote"):
            _text(row[key], "exception." + key)
        _require(row["id"] not in seen_ids, "duplicate exception id")
        seen_ids.add(row["id"])
        pair = (row["candidate_id"], row["requirement_id"])
        _require(pair not in seen_scopes, "duplicate candidate/requirement exception")
        seen_scopes.add(pair)
        _require(row["requirement_id"] in requirements, "exception refers to unknown requirement")
        _require(row["request_id"] in requests and row["quote"] in requests[row["request_id"]],
                 "exception lacks a retained exact user quote")
        _require(type(row["when"]) is list, "exception.when must be an array")
        for predicate in row["when"]:
            _predicate(predicate, "exception predicate", fields)
    _object(evidence, {"schema_version", "sources", "candidates"}, at="evidence")
    _require(evidence["schema_version"] == EVIDENCE_SCHEMA, "unsupported evidence schema")
    sources = evidence["sources"]
    _require(type(sources) is dict, "sources must be an object")
    for key, value in sources.items():
        _text(key, "source id")
        _text(value, "source text")
    _require(type(evidence["candidates"]) is list, "candidates must be an array")
    candidates = {}
    for candidate in evidence["candidates"]:
        _object(candidate, {"id", "fields"}, at="candidate")
        _text(candidate["id"], "candidate id")
        _require(candidate["id"] not in candidates, "duplicate candidate id")
        candidates[candidate["id"]] = candidate
        _require(type(candidate["fields"]) is dict, "candidate.fields must be an object")
        for field, item in candidate["fields"].items():
            _text(field, "evidence field")
            _object(item, {"value", "unit", "qualifier", "source_id", "quote"},
                    {"scope", "reason"}, "evidence field " + field)
            _require(type(item["qualifier"]) is str and item["qualifier"] in QUALIFIERS,
                     "unsupported evidence qualifier")
            if "scope" in item:
                _scope(item["scope"], "evidence.scope")
            if field in fields:
                kind, unit = fields[field]
                _require(item["unit"] == unit, "evidence unit mismatch: " + field)
            else:
                kind = ("boolean" if type(item["value"]) is bool else
                        "string" if type(item["value"]) is str else "number")
                _require(item["unit"] is None or type(item["unit"]) is str,
                         "evidence unit must be a string or null")
            if item["qualifier"] == "unknown":
                _require(item["value"] is None and item["source_id"] is None and item["quote"] is None,
                         "unknown evidence must have null value/source_id/quote")
                _text(item.get("reason"), "unknown evidence reason")
            else:
                _require("reason" not in item, "known evidence cannot have an unknown reason")
                _typed(item["value"], kind, "evidence value: " + field)
                _text(item["source_id"], "evidence.source_id")
                _text(item["quote"], "evidence.quote")
                _require(item["source_id"] in sources and item["quote"] in sources[item["source_id"]],
                         "evidence quote not found in retained source")
    for row in exceptions:
        _require(row["candidate_id"] in candidates, "exception refers to unknown candidate")
    return requirements, candidates


def _check(predicate, fields):
    item = fields.get(predicate["field"])
    if item is None or item["qualifier"] == "unknown":
        return {"status": "unresolved", "comparison": None, "qualifier": "unknown",
                "reason": item["reason"] if item else "No recorded evidence for field",
                "value": None, "unit": predicate["unit"]}
    result = {"qualifier": item["qualifier"], "value": item["value"], "unit": item["unit"],
              "source_id": item["source_id"], "quote": item["quote"], "comparison": None}
    if "scope" in item:
        result["scope"] = item["scope"]
    scope = predicate.get("scope")
    if scope and ("scope" not in item or scope["date"] != item["scope"]["date"] or
                  not set(scope["rooms"]) <= set(item["scope"]["rooms"])):
        return dict(result, status="unresolved", reason="Evidence does not cover the required date/rooms")
    left, right = item["value"], predicate["value"]
    if predicate["type"] == "number":
        left, right = Decimal(str(left)), Decimal(str(right))
    comparison = {"lte": lambda: left <= right, "gte": lambda: left >= right,
                  "eq": lambda: left == right}[predicate["operator"]]()
    result["comparison"] = comparison
    if item["qualifier"] not in predicate["basis"]:
        return dict(result, status="unresolved", reason="Evidence qualifier is not an allowed basis")
    if not comparison:
        return dict(result, status="failed", reason="Recorded value fails the condition")
    if item["qualifier"] != "observed":
        return dict(result, status="unresolved", reason="Planning comparison met; actual condition is unconfirmed")
    return dict(result, status="met", reason="Recorded observation meets the condition")


def evaluate(constraints, evidence, *, revision, constraints_sha256, evidence_sha256):
    """Recompute checks from caller-pinned inputs; never issue an overall PASS."""
    binding = _binding(revision, constraints_sha256, evidence_sha256)
    requirements, candidates = _validate_inputs(constraints, evidence, binding)
    exceptions = {(row["candidate_id"], row["requirement_id"]): row
                  for row in constraints["exceptions"]}
    results = {}
    for candidate_id, candidate in candidates.items():
        checks, effective, exception_checks = {}, [], {}
        for requirement_id, requirement in requirements.items():
            check = _check(requirement, candidate["fields"])
            exception = exceptions.get((candidate_id, requirement_id))
            if exception:
                predicates = [_check(p, candidate["fields"]) for p in exception["when"]]
                satisfied = all(p["status"] == "met" for p in predicates)
                exception_checks[exception["id"]] = {"satisfied": satisfied, "checks": predicates}
                if satisfied and check["status"] != "met":
                    check = dict(check, status="met", original_status=check["status"],
                                 reason="Explicit candidate-scoped exception applies",
                                 exception_id=exception["id"])
                    effective.append(exception["id"])
            checks[requirement_id] = check
        failed = sorted(key for key, check in checks.items()
                        if check["status"] == "failed" and requirements[key]["mandatory"])
        advisory = sorted(key for key, check in checks.items()
                          if check["status"] == "failed" and not requirements[key]["mandatory"])
        unresolved = sorted(key for key, check in checks.items() if check["status"] == "unresolved")
        status = "blocked" if failed else "needs_evidence" if unresolved else "meets_recorded_checks"
        results[candidate_id] = dict(status=status, checks=checks, failed_requirement_ids=failed,
                                     open_requirement_ids=unresolved, exception_ids=sorted(effective),
                                     advisory_failed_requirement_ids=advisory, exceptions=exception_checks)
    return {"schema_version": "vet-flat/eligibility-result/1", "binding": binding,
            "candidates": results, "payment_authorized": False,
            "limit": "Recorded checks only; source truth, prose and overall due diligence are not certified."}


def _recommendation_errors(recommendation, evaluation):
    _object(recommendation, {"schema_version", "binding", "first_choice", "ranking", "backups",
                             "blocked", "not_selected", "todos"}, at="recommendation")
    _require(recommendation["schema_version"] == RECOMMENDATION_SCHEMA, "unsupported recommendation schema")
    binding, candidates = evaluation["binding"], evaluation["candidates"]
    _object(recommendation["binding"], PIN_KEYS, at="recommendation.binding")
    _require(type(recommendation["binding"]["revision"]) is int and
             recommendation["binding"] == binding, "stale recommendation binding")
    errors, pools, selected = [], {}, set()
    for pool in ("ranking", "backups", "blocked", "not_selected"):
        _require(type(recommendation[pool]) is list, pool + " must be an array")
        for row in recommendation[pool]:
            if pool == "not_selected":
                candidate_id = row
                _text(candidate_id, "not_selected candidate")
            else:
                keys = ({"candidate_id", "failed_requirement_ids"} if pool == "blocked" else
                        {"candidate_id", "status", "open_requirement_ids", "exception_ids"})
                _object(row, keys, at=pool + " entry")
                candidate_id = row["candidate_id"]
                _text(candidate_id, pool + " candidate")
            _require(candidate_id in candidates, "unknown candidate: " + candidate_id)
            if candidate_id in pools:
                errors.append("candidate appears in multiple pools: " + candidate_id)
            pools[candidate_id] = pool
            actual = candidates[candidate_id]
            if (actual["status"] == "blocked") != (pool == "blocked"):
                errors.append("blocked membership disagrees with mandatory checks: " + candidate_id)
            if pool == "blocked":
                _strings(row["failed_requirement_ids"], "failed_requirement_ids")
                if sorted(row["failed_requirement_ids"]) != actual["failed_requirement_ids"]:
                    errors.append("failed requirement IDs disagree: " + candidate_id)
            elif pool in ("ranking", "backups"):
                selected.add(candidate_id)
                if row["status"] != actual["status"]:
                    errors.append("candidate status disagrees: " + candidate_id)
                for key in ("open_requirement_ids", "exception_ids"):
                    _strings(row[key], key)
                    if sorted(row[key]) != actual[key]:
                        errors.append(key + " disagree: " + candidate_id)
    if set(pools) != set(candidates):
        errors.append("every candidate must appear in exactly one pool")
    first = recommendation["first_choice"]
    _require(first is None or type(first) is str, "first_choice must be a string or null")
    expected_first = recommendation["ranking"][0]["candidate_id"] if recommendation["ranking"] else None
    if first != expected_first:
        errors.append("first_choice must equal the first ranked candidate")
    if recommendation["backups"] and not recommendation["ranking"]:
        errors.append("backups require a first-ranked candidate")
    _require(type(recommendation["todos"]) is list, "todos must be an array")
    covered, todo_ids = {key: set() for key in selected}, set()
    for todo in recommendation["todos"]:
        _object(todo, {"id", "candidate_id", "action", "requirement_ids", "binding"}, at="TODO")
        _text(todo["id"], "TODO id")
        _require(todo["id"] not in todo_ids, "duplicate TODO id")
        todo_ids.add(todo["id"])
        _object(todo["binding"], PIN_KEYS, at="TODO.binding")
        if type(todo["binding"]["revision"]) is not int or todo["binding"] != binding:
            errors.append("stale TODO binding: " + todo["id"])
        candidate_id = todo["candidate_id"]
        _text(candidate_id, "TODO candidate")
        _require(candidate_id in candidates, "TODO refers to unknown candidate")
        _strings(todo["requirement_ids"], "TODO requirement_ids")
        _require(type(todo["action"]) is str and todo["action"] in {"investigate", "view", "reconsider"},
                 "unsupported TODO action")
        actual = candidates[candidate_id]
        if actual["status"] == "blocked":
            if (todo["action"] != "reconsider" or
                    sorted(todo["requirement_ids"]) != actual["failed_requirement_ids"]):
                errors.append("blocked candidate TODO must reconsider its failed conditions: " + candidate_id)
        elif candidate_id not in selected or todo["action"] not in {"investigate", "view"}:
            errors.append("active TODO must name a selected nonblocked candidate: " + candidate_id)
        elif not set(todo["requirement_ids"]) <= set(actual["open_requirement_ids"]):
            errors.append("TODO must use currently open requirement IDs: " + candidate_id)
        else:
            if todo["action"] == "investigate" and not todo["requirement_ids"]:
                errors.append("investigation TODO must name an open condition: " + candidate_id)
            covered[candidate_id].update(todo["requirement_ids"])
    for candidate_id in sorted(selected):
        if not set(candidates[candidate_id]["open_requirement_ids"]) <= covered[candidate_id]:
            errors.append("TODOs do not cover every open condition: " + candidate_id)
    return errors


def validate_recommendation(constraints, evidence, recommendation, *, revision,
                            constraints_sha256, evidence_sha256):
    """Return valid:false on recommendation violations; raise for invalid pinned inputs."""
    evaluation = evaluate(constraints, evidence, revision=revision,
                          constraints_sha256=constraints_sha256, evidence_sha256=evidence_sha256)
    try:
        errors = _recommendation_errors(recommendation, evaluation)
    except EligibilityError as exc:
        errors = [str(exc)]
    return {"valid": not errors, "errors": errors, "binding": evaluation["binding"],
            "payment_authorized": False}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def _read(path):
    def bad_constant(value):
        raise EligibilityError("nonfinite JSON constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=bad_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("evaluate", "validate"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--constraints", required=True)
        sub.add_argument("--evidence", required=True)
        sub.add_argument("--revision", required=True, type=int)
        sub.add_argument("--constraints-sha256", required=True)
        sub.add_argument("--evidence-sha256", required=True)
        if command == "validate":
            sub.add_argument("--recommendation", required=True)
    args = parser.parse_args(argv)
    try:
        constraints, evidence = _read(args.constraints), _read(args.evidence)
        pins = {key: getattr(args, key) for key in PIN_KEYS}
        if args.command == "evaluate":
            result = evaluate(constraints, evidence, **pins)
        else:
            result = validate_recommendation(constraints, evidence, _read(args.recommendation), **pins)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0 if result.get("valid", True) else 1
    except (EligibilityError, OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
