"""Offline behavior tests for pinned conditions, scoped waivers and current TODOs."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/vet-flat/scripts/eligibility.py"
SPEC = importlib.util.spec_from_file_location("eligibility", SCRIPT)
eligibility = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eligibility)


def requirement(key, field, kind, operator, value, unit, basis=None, mandatory=True):
    return dict(id=key, field=field, type=kind, operator=operator, value=value,
                unit=unit, mandatory=mandatory, basis=basis or ["observed"])


def fixture():
    conditions = {
        "schema_version": eligibility.CONSTRAINTS_SCHEMA, "revision": 7,
        "requirements": [
            requirement("budget", "monthly_total", "number", "lte", 1500, "GBP/month",
                        ["observed", "estimate"]),
            requirement("area", "internal_area_m2", "number", "gte", 45, "m2"),
            requirement("floor", "ground_floor", "boolean", "eq", False, None),
            requirement("quiet", "quiet", "boolean", "eq", True, None)],
        "user_requests": {"u1": "For C only, ground floor is acceptable if the dated inspection confirms both rooms are dry."},
        "exceptions": [{"id": "floor-c", "requirement_id": "floor", "candidate_id": "C",
                        "request_id": "u1", "quote": "For C only, ground floor is acceptable",
                        "when": [{"field": "dry_inspection", "type": "boolean", "operator": "eq",
                                  "value": True, "unit": None, "basis": ["observed"],
                                  "scope": {"date": "2026-01-12", "rooms": ["bedroom", "living_room"]}}]}]}
    evidence = {"schema_version": eligibility.EVIDENCE_SCHEMA, "sources": {}, "candidates": []}
    for key, cost, area, floor in (("A", 1610, 46, False), ("B", 1400, 43, False), ("C", 1400, 46, True)):
        fields = {}
        for field, value, unit, qualifier in (
                ("monthly_total", cost, "GBP/month", "estimate"),
                ("internal_area_m2", area, "m2", "observed"),
                ("ground_floor", floor, None, "observed"),
                ("dry_inspection", True, None, "observed")):
            source = key + "-" + field
            quote = "%s: %s %s (%s)" % (field, value, unit, qualifier)
            evidence["sources"][source] = quote
            fields[field] = dict(value=value, unit=unit, qualifier=qualifier,
                                 source_id=source, quote=quote)
        fields["dry_inspection"]["scope"] = {"date": "2026-01-12", "rooms": ["bedroom", "living_room"]}
        fields["quiet"] = dict(value=None, unit=None, qualifier="unknown", source_id=None,
                               quote=None, reason="No representative observation")
        evidence["candidates"].append(dict(id=key, fields=fields))
    return conditions, evidence


def pins(conditions, evidence):
    return dict(revision=conditions["revision"], constraints_sha256=eligibility.canonical_hash(conditions),
                evidence_sha256=eligibility.canonical_hash(evidence))


def proposal(conditions, evidence):
    binding = pins(conditions, evidence)
    return dict(schema_version=eligibility.RECOMMENDATION_SCHEMA, binding=deepcopy(binding),
                first_choice="C", ranking=[dict(candidate_id="C", status="needs_evidence",
                open_requirement_ids=["budget", "quiet"], exception_ids=["floor-c"])], backups=[],
                blocked=[dict(candidate_id="A", failed_requirement_ids=["budget"]),
                         dict(candidate_id="B", failed_requirement_ids=["area"])], not_selected=[],
                todos=[dict(id="check-c", candidate_id="C", action="investigate",
                            requirement_ids=["budget", "quiet"], binding=deepcopy(binding))])


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.c, self.e = fixture()

    def evaluate(self):
        return eligibility.evaluate(self.c, self.e, **pins(self.c, self.e))

    def validate(self, value=None):
        return eligibility.validate_recommendation(self.c, self.e,
                value if value is not None else proposal(self.c, self.e), **pins(self.c, self.e))

    def test_known_failures_block_and_supported_estimate_remains_open(self):
        actual = self.evaluate()
        a, b, c = (actual["candidates"][key] for key in "ABC")
        self.assertEqual((a["status"], a["failed_requirement_ids"]), ("blocked", ["budget"]))
        self.assertEqual((b["status"], b["failed_requirement_ids"]), ("blocked", ["area"]))
        self.assertEqual((c["status"], c["open_requirement_ids"]), ("needs_evidence", ["budget", "quiet"]))
        self.assertTrue(c["checks"]["budget"]["comparison"])
        self.assertEqual(c["checks"]["budget"]["qualifier"], "estimate")
        self.assertEqual(c["checks"]["floor"]["original_status"], "failed")
        self.assertEqual(c["exception_ids"], ["floor-c"])
        self.assertFalse(actual["payment_authorized"])
        self.assertTrue(self.validate()["valid"])

    def test_numeric_threshold_is_inclusive_and_decimal_comparison_preserves_boundary(self):
        self.c["requirements"][0]["value"] = 1400.1
        field = self.e["candidates"][2]["fields"]["monthly_total"]
        field.update(value=1400.1, qualifier="observed")
        self.assertEqual(self.evaluate()["candidates"]["C"]["checks"]["budget"]["status"], "met")
        field["value"] = 1400.100001
        self.assertEqual(self.evaluate()["candidates"]["C"]["status"], "blocked")

    def test_missing_evidence_and_unknown_never_become_false_or_observed(self):
        del self.e["candidates"][2]["fields"]["internal_area_m2"]
        c = self.evaluate()["candidates"]["C"]
        self.assertEqual(c["open_requirement_ids"], ["area", "budget", "quiet"])
        self.assertIsNone(c["checks"]["area"]["comparison"])
        self.assertEqual(c["checks"]["area"]["reason"], "No recorded evidence for field")

    def test_observed_false_is_blocked_instead_of_unresolved(self):
        self.e["candidates"][2]["fields"]["quiet"] = dict(value=False, unit=None,
                qualifier="observed", source_id="noise", quote="Quiet: false")
        self.e["sources"]["noise"] = "Quiet: false"
        self.assertEqual(self.evaluate()["candidates"]["C"]["failed_requirement_ids"], ["quiet"])

    def test_reported_or_disallowed_basis_never_guarantees_satisfaction(self):
        field = self.e["candidates"][2]["fields"]["internal_area_m2"]
        field["qualifier"] = "reported"
        self.assertEqual(self.evaluate()["candidates"]["C"]["checks"]["area"]["status"], "unresolved")
        self.c["requirements"][1]["basis"].append("reported")
        self.assertEqual(self.evaluate()["candidates"]["C"]["checks"]["area"]["status"], "unresolved")

    def add_commute(self, minutes=32):
        condition = requirement("commute", "commute_minutes", "number", "lte", 35, "minutes")
        condition["scope"] = {"kind": "journey", "destination_id": "demo-library-entrance",
                              "time_window": "weekday-arrival-08:30-09:00"}
        self.c["requirements"].append(condition)
        quote = "One weekday journey took %s minutes." % minutes
        self.e["sources"]["journey"] = quote
        item = dict(value=minutes, unit="minutes", qualifier="observed", source_id="journey",
                    quote=quote, scope=deepcopy(condition["scope"]))
        self.e["candidates"][2]["fields"]["commute_minutes"] = item
        return condition, item

    def test_commute_unknown_target_stays_unresolved_below_or_above_limit(self):
        for minutes in (32, 38):
            for omitted in (True, False):
                with self.subTest(minutes=minutes, omitted=omitted):
                    self.c, self.e = fixture()
                    condition, item = self.add_commute(minutes)
                    if omitted:
                        del condition["scope"]
                    else:
                        condition["scope"] = None
                    check = self.evaluate()["candidates"]["C"]["checks"]["commute"]
                    self.assertEqual(check["status"], "unresolved")
                    self.assertIsNone(check["comparison"])
                    self.assertEqual(check["value"], minutes)
                    self.assertEqual(check["qualifier"], "observed")
                    self.assertIn("commute", self.evaluate()["candidates"]["C"]["open_requirement_ids"])

    def test_commute_requires_matching_evidence_context_before_scalar_comparison(self):
        for minutes in (32, 38):
            for scope in (None, {}, {"date": "2026-01-12", "rooms": ["bedroom"]},
                          {"kind": "journey", "destination_id": "another-entrance",
                           "time_window": "weekday-arrival-08:30-09:00"},
                          {"kind": "journey", "destination_id": "demo-library-entrance",
                           "time_window": "weekend-arrival-14:00-15:00"}):
                with self.subTest(minutes=minutes, scope=scope):
                    self.c, self.e = fixture()
                    condition, item = self.add_commute(minutes)
                    if scope == {}:
                        del item["scope"]
                    else:
                        item["scope"] = scope
                    result = self.evaluate()["candidates"]["C"]
                    self.assertEqual(result["checks"]["commute"]["status"], "unresolved")
                    self.assertIsNone(result["checks"]["commute"]["comparison"])
                    self.assertNotIn("commute", result["failed_requirement_ids"])

    def test_matching_observed_commute_passes_or_fails_at_inclusive_threshold(self):
        for minutes, status in ((32, "met"), (35, "met"), (38, "failed")):
            with self.subTest(minutes=minutes):
                self.c, self.e = fixture()
                self.add_commute(minutes)
                result = self.evaluate()["candidates"]["C"]
                self.assertEqual(result["checks"]["commute"]["status"], status)
                self.assertEqual(result["checks"]["commute"]["comparison"], minutes <= 35)
                if status == "failed":
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual(result["failed_requirement_ids"], ["commute"])

    def test_changed_commute_target_invalidates_pins_and_keeps_open_id_in_todos(self):
        condition, item = self.add_commute()
        old_pins = pins(self.c, self.e)
        r = proposal(self.c, self.e)
        self.assertTrue(self.validate(r)["valid"])
        condition["scope"]["destination_id"] = "new-user-destination"
        self.c["revision"] += 1
        with self.assertRaisesRegex(eligibility.EligibilityError, "constraints SHA mismatch"):
            eligibility.evaluate(self.c, self.e, **old_pins)
        self.assertFalse(self.validate(r)["valid"])
        r["binding"] = pins(self.c, self.e)
        r["todos"][0]["binding"] = pins(self.c, self.e)
        self.assertFalse(self.validate(r)["valid"])
        r["ranking"][0]["open_requirement_ids"].append("commute")
        self.assertFalse(self.validate(r)["valid"])
        r["todos"][0]["requirement_ids"].append("commute")
        self.assertTrue(self.validate(r)["valid"])
        self.assertIsNone(self.evaluate()["candidates"]["C"]["checks"]["commute"]["comparison"])
        before_evidence_update = pins(self.c, self.e)
        item["scope"] = deepcopy(condition["scope"])
        with self.assertRaisesRegex(eligibility.EligibilityError, "evidence SHA mismatch"):
            eligibility.evaluate(self.c, self.e, **before_evidence_update)
        self.assertEqual(self.evaluate()["candidates"]["C"]["checks"]["commute"]["status"], "met")

    def test_journey_scope_is_typed_without_placeholder_defaults(self):
        invalid_scopes = [False, "weekday", {"kind": "journey", "destination_id": ""},
            {"kind": "journey", "destination_id": "entrance", "time_window": " "},
            {"kind": "journey", "destination_id": False, "time_window": "weekday-morning"},
            {"kind": "route", "destination_id": "entrance", "time_window": "weekday-morning"},
            {"kind": "journey", "destination_id": "entrance", "time_window": "weekday-morning", "rooms": []},
            {"date": "2026-01-12", "rooms": ["bedroom"]}]
        for scope in invalid_scopes:
            with self.subTest(scope=scope):
                self.c, self.e = fixture()
                condition, item = self.add_commute()
                condition["scope"] = scope
                with self.assertRaises(eligibility.EligibilityError):
                    self.evaluate()

    def test_scope_unknown_never_satisfies_an_and_exception_predicate(self):
        condition, item = self.add_commute()
        predicate = {key: value for key, value in condition.items() if key not in ("id", "mandatory")}
        self.c["exceptions"][0]["when"].append(predicate)
        item["scope"] = None
        result = self.evaluate()["candidates"]["C"]
        self.assertEqual(result["failed_requirement_ids"], ["floor"])
        self.assertEqual(result["exception_ids"], [])
        self.assertEqual(result["open_requirement_ids"], ["budget", "commute", "quiet"])
        item["scope"] = deepcopy(condition["scope"])
        self.assertEqual(self.evaluate()["candidates"]["C"]["exception_ids"], ["floor-c"])
        self.e["candidates"][2]["fields"]["dry_inspection"]["scope"] = None
        self.assertEqual(self.evaluate()["candidates"]["C"]["failed_requirement_ids"], ["floor"])

    def test_explicit_unknown_scope_is_not_an_unscoped_numeric_check(self):
        self.c["requirements"][1]["scope"] = None
        result = self.evaluate()["candidates"]["C"]
        self.assertEqual(result["checks"]["area"]["status"], "unresolved")
        self.assertIsNone(result["checks"]["area"]["comparison"])
        del self.c["requirements"][1]["scope"]
        self.assertEqual(self.evaluate()["candidates"]["C"]["checks"]["area"]["status"], "met")

    def test_exception_never_leaks_to_another_candidate(self):
        self.e["candidates"][0]["fields"]["ground_floor"]["value"] = True
        a = self.evaluate()["candidates"]["A"]
        self.assertEqual(a["failed_requirement_ids"], ["budget", "floor"])
        self.assertEqual(a["exception_ids"], [])

    def test_exception_requires_all_observed_predicates_with_exact_date_and_rooms(self):
        original = deepcopy(self.e)
        changes = [dict(value=False), dict(qualifier="estimate"),
                   dict(scope={"date": "2026-01-11", "rooms": ["bedroom", "living_room"]}),
                   dict(scope={"date": "2026-01-12", "rooms": ["bedroom"]})]
        for change in changes:
            with self.subTest(change=change):
                self.e = deepcopy(original)
                self.e["candidates"][2]["fields"]["dry_inspection"].update(change)
                c = self.evaluate()["candidates"]["C"]
                self.assertEqual(c["failed_requirement_ids"], ["floor"])
                self.assertEqual(c["exception_ids"], [])
        self.e = original
        self.e["candidates"][2]["fields"]["dry_inspection"]["scope"]["rooms"].append("kitchen")
        self.assertEqual(self.evaluate()["candidates"]["C"]["exception_ids"], ["floor-c"])

    def test_explicit_unconditional_exception_is_confined_to_trusted_scope(self):
        self.c["exceptions"][0]["when"] = []
        self.c["user_requests"]["u1"] = "For C only, ground floor is acceptable without an inspection."
        del self.e["candidates"][2]["fields"]["dry_inspection"]
        self.assertEqual(self.evaluate()["candidates"]["C"]["exception_ids"], ["floor-c"])

    def test_exception_requires_retained_user_quote_and_known_refs(self):
        for key, value in (("quote", "Invented waiver"), ("request_id", "source"),
                           ("candidate_id", "Z"), ("requirement_id", "invented")):
            with self.subTest(key=key):
                c = deepcopy(self.c)
                c["exceptions"][0][key] = value
                with self.assertRaises(eligibility.EligibilityError):
                    eligibility.evaluate(c, self.e, **pins(c, self.e))

    def test_strict_types_units_fields_duplicates_and_nonfinite_values(self):
        bad_changes = [lambda c, e: c["requirements"][0].update(value=True),
            lambda c, e: c["requirements"][0].update(value=float("nan")),
            lambda c, e: c["requirements"][0].update(mandatory="true"),
            lambda c, e: c["requirements"][0].update(operator="less"),
            lambda c, e: c["requirements"][2].update(operator="lte"),
            lambda c, e: c["requirements"].append(deepcopy(c["requirements"][0])),
            lambda c, e: c["exceptions"].append(deepcopy(c["exceptions"][0])),
            lambda c, e: e["candidates"].append(deepcopy(e["candidates"][0])),
            lambda c, e: e["candidates"][0]["fields"]["monthly_total"].update(value="1610"),
            lambda c, e: e["candidates"][0]["fields"]["monthly_total"].update(unit="GBP/week"),
            lambda c, e: e["candidates"][0]["fields"]["monthly_total"].update(quote="wrong quote"),
            lambda c, e: e["candidates"][0]["fields"]["quiet"].update(value=False),
            lambda c, e: e["candidates"][0]["fields"]["quiet"].pop("reason"),
            lambda c, e: c.update(payment_authorized=True),
            lambda c, e: c.update(requirements=[]),
            lambda c, e: c["exceptions"][0]["when"][0]["scope"].update(date="2026-02-30")]
        for index, change in enumerate(bad_changes):
            with self.subTest(index=index):
                c, e = deepcopy(self.c), deepcopy(self.e)
                change(c, e)
                with self.assertRaises(eligibility.EligibilityError):
                    eligibility.evaluate(c, e, **pins(c, e))

    def test_generic_string_field_and_advisory_failure_remain_visible(self):
        self.c["requirements"].append(requirement("finish", "finish", "string", "eq", "wood", None,
                                                     mandatory=False))
        self.e["candidates"][2]["fields"]["finish"] = dict(value="tile", unit=None,
            qualifier="observed", source_id="finish", quote="tile")
        self.e["sources"]["finish"] = "Floor finish is tile"
        c = self.evaluate()["candidates"]["C"]
        self.assertEqual(c["advisory_failed_requirement_ids"], ["finish"])
        self.assertEqual(c["status"], "needs_evidence")

    def test_external_pins_detect_changed_budget_evidence_and_revision(self):
        previous = pins(self.c, self.e)
        self.c["requirements"][0]["value"] = 1800
        with self.assertRaisesRegex(eligibility.EligibilityError, "constraints SHA mismatch"):
            eligibility.evaluate(self.c, self.e, **previous)
        previous = pins(self.c, self.e)
        self.e["sources"]["new"] = "A new source version"
        with self.assertRaisesRegex(eligibility.EligibilityError, "evidence SHA mismatch"):
            eligibility.evaluate(self.c, self.e, **previous)
        previous = pins(self.c, self.e)
        previous["revision"] += 1
        with self.assertRaisesRegex(eligibility.EligibilityError, "revision mismatch"):
            eligibility.evaluate(self.c, self.e, **previous)

    def test_tightening_and_relaxing_budget_recomputes_without_reusing_old_export(self):
        old = self.evaluate()
        old_proposal = proposal(self.c, self.e)
        self.c["revision"] += 1
        self.c["requirements"][0]["value"] = 1350
        self.assertEqual(self.evaluate()["candidates"]["C"]["status"], "blocked")
        self.assertFalse(self.validate(old_proposal)["valid"])
        self.c["revision"] += 1
        self.c["requirements"][0]["value"] = 1800
        self.assertEqual(old["candidates"]["A"]["status"], "blocked")
        self.assertEqual(self.evaluate()["candidates"]["A"]["status"], "needs_evidence")
        self.assertFalse(self.validate(old_proposal)["valid"])

    def test_failed_candidate_cannot_be_first_ranked_backup_or_hidden(self):
        for pool in ("ranking", "backups", "not_selected"):
            with self.subTest(pool=pool):
                r = proposal(self.c, self.e)
                r["blocked"].pop(1)
                r[pool].append("B" if pool == "not_selected" else dict(candidate_id="B",
                    status="needs_evidence", open_requirement_ids=["budget", "quiet"], exception_ids=[]))
                self.assertFalse(self.validate(r)["valid"])
        r = proposal(self.c, self.e)
        r["first_choice"] = "A"
        self.assertFalse(self.validate(r)["valid"])

    def test_first_choice_exactly_matches_ranking_and_all_candidates_have_one_pool(self):
        for change in (lambda r: r.update(first_choice=None), lambda r: r["blocked"].pop(),
                       lambda r: r["not_selected"].append("C"),
                       lambda r: r["ranking"].append(deepcopy(r["ranking"][0]))):
            r = proposal(self.c, self.e)
            change(r)
            self.assertFalse(self.validate(r)["valid"])

    def test_unknowns_cannot_be_erased_or_relabelled_as_guaranteed(self):
        for change in (lambda r: r["ranking"][0].update(status="meets_recorded_checks"),
                       lambda r: r["ranking"][0].update(open_requirement_ids=[]),
                       lambda r: r["ranking"][0].update(exception_ids=["invented"]),
                       lambda r: r.update(verdict="PASS"),
                       lambda r: r.update(payment_authorized=True)):
            r = proposal(self.c, self.e)
            change(r)
            self.assertFalse(self.validate(r)["valid"])

    def test_stale_todo_rejected_even_when_top_level_binding_is_current(self):
        r = proposal(self.c, self.e)
        self.c["revision"] += 1
        r["binding"] = pins(self.c, self.e)
        result = self.validate(r)
        self.assertFalse(result["valid"])
        self.assertTrue(any("stale TODO" in error for error in result["errors"]))

    def test_todos_cover_every_selected_open_condition_without_invented_work(self):
        for change in (lambda r: r.update(todos=[]),
                       lambda r: r["todos"][0].update(requirement_ids=["quiet"]),
                       lambda r: r["todos"][0].update(requirement_ids=["budget", "quiet", "area"]),
                       lambda r: r["todos"][0].update(action="pay")):
            r = proposal(self.c, self.e)
            change(r)
            self.assertFalse(self.validate(r)["valid"])

    def test_blocked_reconsideration_does_not_promote_or_authorize_viewing(self):
        r = proposal(self.c, self.e)
        todo = dict(id="reconsider-b", candidate_id="B", action="reconsider", requirement_ids=["area"],
                    binding=pins(self.c, self.e))
        r["todos"].append(todo)
        self.assertTrue(self.validate(r)["valid"])
        todo["action"] = "view"
        self.assertFalse(self.validate(r)["valid"])
        todo.update(action="reconsider", requirement_ids=[])
        self.assertFalse(self.validate(r)["valid"])

    def test_empty_ranking_can_leave_nonblocked_candidates_unselected(self):
        r = proposal(self.c, self.e)
        r.update(first_choice=None, ranking=[], not_selected=["C"], todos=[])
        self.assertTrue(self.validate(r)["valid"])

    def test_calls_do_not_mutate_inputs(self):
        c, e = deepcopy(self.c), deepcopy(self.e)
        r = proposal(c, e)
        before = deepcopy((c, e, r))
        eligibility.validate_recommendation(c, e, r, **pins(c, e))
        self.assertEqual((c, e, r), before)

    def test_cli_success_rejection_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            paths = {name: base / (name + ".json") for name in ("constraints", "evidence", "recommendation")}
            for key, value in (("constraints", self.c), ("evidence", self.e),
                               ("recommendation", proposal(self.c, self.e))):
                paths[key].write_text(json.dumps(value))
            args = [sys.executable, str(SCRIPT), "validate"]
            for key, path in paths.items():
                args += ["--" + key, str(path)]
            for key, value in pins(self.c, self.e).items():
                args += ["--" + key.replace("_", "-"), str(value)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])
            bad = proposal(self.c, self.e)
            bad["first_choice"] = "A"
            paths["recommendation"].write_text(json.dumps(bad))
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["valid"])
            paths["constraints"].write_text('{"revision":7,"revision":8}')
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("duplicate JSON key", json.loads(result.stderr)["error"])

    def test_reference_example_runs_from_detached_skill(self):
        doc = ROOT / "skills/vet-flat/references/eligibility-api.md"
        blocks = re.findall(r"^```python\n(.*?)^```", doc.read_text(), re.M | re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "detached skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "scripts/eligibility.py").write_bytes(SCRIPT.read_bytes())
            result = subprocess.run([sys.executable, "-c", blocks[0]], cwd=temp,
                env=dict(os.environ, PEA_SKILL=str(skill)), capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
