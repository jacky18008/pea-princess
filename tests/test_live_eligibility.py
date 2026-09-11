"""Offline behavior regressions for the host-owned live eligibility adapter."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/vet-flat/scripts/live_eligibility.py"
SPEC = importlib.util.spec_from_file_location("live_eligibility_tests", SCRIPT)
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)
URL_A = "https://example.org/listings/unit-a"
URL_B = "https://example.org/listings/unit-b"


def source(text, identity="unit", **changes):
    item = dict(text=text, retrieved_at="2026-01-12T12:00:00Z", ok=True, identity=identity,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
    item.update(changes)
    return item


def listing(rent=2100, bedrooms=1, floor=3, area=46):
    return "%d bedroom apartment\nRent: £%s pcm\n%dth floor\nAdvertised area: %s m²" % (bedrooms, rent, floor, area)


def proposal(urls=(URL_A,), focus=()):
    return {"candidates": [{"source_url": url, "label": "Actor label"} for url in urls],
            "focus_fields": list(focus)}


def requirements(normalized):
    return {row["id"]: row for row in normalized["constraints"]["requirements"]}


def fields(artifact, index=0):
    return artifact["evidence"]["candidates"][index]["fields"]


def check(artifact, index=0):
    key = artifact["evidence"]["candidates"][index]["id"]
    return artifact["checks"]["candidates"][key]


class NormalizeTests(unittest.TestCase):
    def test_zh_clear_rent_bedroom_floor_and_area_compile(self):
        n = live.normalize(["我只要一房，房租最多 £2,200，而且只接受二到十樓；面積至少45平方公尺。"], 7)
        rows = requirements(n)
        self.assertEqual(rows["rent-ceiling"]["value"], 2200)
        self.assertEqual(rows["bedrooms"]["value"], 1)
        self.assertEqual((rows["floor-min"]["value"], rows["floor-max"]["value"]), (2, 10))
        self.assertEqual(rows["area-min"]["value"], 45)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertTrue(all(row["mandatory"] for row in rows.values()))

    def test_en_clear_constraints_compile(self):
        n = live.normalize(["I only want a one-bedroom flat; rent at most £2,200; floors 2 to 10; area at least 45 sqm."], 1)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["area-min"]["value"], 45)

    def test_budget_tightening_and_relaxation_preserve_other_conditions(self):
        inputs = ["我只要一房，房租每月最多 £2,300，樓層二到十樓。", "不過房租上限改成 £2,100。"]
        rows = requirements(live.normalize(inputs, 2))
        self.assertEqual(rows["rent-ceiling"]["value"], 2100)
        self.assertEqual(rows["floor-max"]["value"], 10)
        inputs.append("房租上限改成 £2,500。")
        n = live.normalize(inputs, 3)
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2500)
        self.assertEqual(n["provenance"]["requirements"]["rent-ceiling"]["request_id"], "input-3")

    def test_ambiguous_conditional_and_quoted_updates_do_not_relax(self):
        later = ["如果很安靜，這間房租上限改成 £3,000。", "房租上限大概 £3,000。",
                 "房租上限改成 £3,000 if the bedroom is quiet.",
                 "仲介說房租上限改成 £3,000。", "I do not want a rent cap £3,000.",
                 "房租上限改成 £3,000 並且需要一個尚未定義的特殊條件。",
                 "房租上限改成 £3,000，如果很安靜。", "如果很安靜，房租上限改成 £3,000。"]
        for amendment in later:
            with self.subTest(amendment=amendment):
                n = live.normalize(["房租最多 £2,100。", amendment], 2)
                self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)
                self.assertTrue(n["unresolved_intent"])
                self.assertEqual(n["constraints"]["exceptions"], [])

    def test_observed_price_in_a_user_question_is_not_a_new_ceiling(self):
        n = live.normalize(["房租最多 £2,100。", "仲介說房租 £3,000。"], 2)
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)
        self.assertTrue(n["unresolved_intent"])

    def test_two_different_ceiling_values_in_one_request_conflict(self):
        n = live.normalize(["房租最多 £2,100。", "房租最多 £2,200；房租最多 £2,400。"], 2)
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)
        self.assertTrue(n["unresolved_intent"])

    def test_total_spend_does_not_change_rent_cap(self):
        n = live.normalize(["房租最多 £2,100。", "每月總花費最多 £2,400。"], 2)
        rows = requirements(n)
        self.assertEqual(rows["rent-ceiling"]["value"], 2100)
        self.assertEqual(rows["monthly-total-ceiling"]["value"], 2400)

    def test_generic_budget_does_not_assume_rent_only(self):
        n = live.normalize(["預算上限 £2,000。"], 1)
        self.assertNotIn("rent-ceiling", requirements(n))
        self.assertNotIn("monthly-total-ceiling", requirements(n))
        self.assertTrue(n["unresolved_intent"])

    def test_pure_budget_ambiguity_resolves_after_precise_clarification(self):
        for initial, clarified, expected in (("預算上限 £2000", "房租上限 £2000", 2000),
                                             ("房租上限大概 £2000", "房租上限 £1900", 1900)):
            with self.subTest(initial=initial):
                n = live.normalize([initial, clarified], 2)
                self.assertEqual(n["unresolved_intent"], [])
                self.assertEqual(requirements(n)["rent-ceiling"]["value"], expected)

    def test_budget_choices_resolve_to_the_selected_scope(self):
        inputs = ["預算上限 £2000"]
        first = live.accept(proposal(), inputs, 1, {URL_A: source(listing())})
        options = first["reply"]["questions"][0]["options"]
        self.assertEqual(2, len(options))
        for option, field in zip(options, ("rent_pcm", "monthly_total")):
            followup = live.accept(proposal(), inputs + [option], 2, {URL_A: source(listing())})
            self.assertEqual([], followup["normalization"]["unresolved_intent"])
            self.assertEqual([], followup["reply"]["questions"])
            self.assertTrue(any(row["field"] == field and row["value"] == 2000
                                for row in followup["constraints"]["requirements"]))

    def test_native_clarification_answer_can_correct_scope_and_amount(self):
        n = live.normalize(["預算上限 £2000", "我會補充確切條件；房租上限 £1900"], 2)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 1900)

    def test_clarification_marker_does_not_clear_multiple_generic_budgets(self):
        n = live.normalize(["預算上限 £2000；預算最多 £2100", "我會補充確切條件；房租上限 £1900"], 2)
        self.assertEqual(n["unresolved_intent"], ["預算上限 £2000", "預算最多 £2100"])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 1900)

    def test_clarification_marker_cannot_skip_the_first_unresolved_question(self):
        n = live.normalize(["樓層須有電梯；預算上限 £2000", "我會補充確切條件；房租上限 £1900"], 2)
        self.assertEqual(n["unresolved_intent"], ["樓層須有電梯", "預算上限 £2000"])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 1900)

    def test_nonpure_budget_unknown_has_no_broad_category_resolution(self):
        for initial in ("預算上限 £2000，房租須含暖氣", "房租上限大概 £2000 而且必須有暖氣", "樓層須有電梯"):
            n = live.normalize([initial, "房租上限 £2000", "樓層二到十樓"], 3)
            self.assertTrue(n["unresolved_intent"])

    def test_gbp_monthly_ceiling_is_supported_without_pound_symbol(self):
        n = live.normalize(["Rent ceiling GBP 2000 per month."], 1)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2000)

    def test_bare_listing_urls_are_discovery_leads_not_condition_barriers(self):
        url = "https://example.org/properties-to-rent/n6/unit1?floor=13"
        initial = "房租最多 £2,100。"
        n = live.normalize([initial, url], 2)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)
        self.assertEqual(n["constraints"]["user_requests"]["input-2"], url)

    def test_url_inside_condition_retains_exact_original_provenance(self):
        raw = "我只要一房 https://example.org/properties-to-rent/unit1"
        n = live.normalize([raw], 1)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["bedrooms"]["value"], 1)
        self.assertEqual(n["provenance"]["requirements"]["bedrooms"]["quote"], raw)

    def test_heating_question_does_not_become_a_user_condition(self):
        for question in ("暖氣費包含在房租裡嗎？", "房租是否包含暖氣費？", "Is heating included in the rent?"):
            n = live.normalize(["房租最多 £2,100。", question], 2)
            self.assertEqual(n["unresolved_intent"], [])
            self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)

    def test_known_field_comparison_request_is_not_a_constraint(self):
        text = ("房租上限 £2300。我要一房，希望安靜。請比較下面兩間，先看房租、房數與面積，不用找新的房源。\n"
                "https://example.org/properties-to-rent/unit-a\nhttps://example.org/properties-to-rent/unit-b")
        n = live.normalize([text], 1)
        self.assertEqual(n["unresolved_intent"], [])
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2300)
        self.assertEqual(requirements(n)["bedrooms"]["value"], 1)
        self.assertFalse(live._routing_clause("先看房租最多 £2000"))

    def test_question_form_can_still_authorize_an_explicit_budget_change(self):
        n = live.normalize(["房租最多 £2,300", "可以把房租上限改成 £2,100嗎？"], 2)
        self.assertEqual(requirements(n)["rent-ceiling"]["value"], 2100)
        self.assertEqual(n["unresolved_intent"], [])

    def test_minimum_bedroom_count_is_ordered_condition(self):
        for text in ("至少兩房。", "I need at least two-bedroom apartment."):
            with self.subTest(text=text):
                n = live.normalize([text], 1)
                row = requirements(n)["bedrooms"]
                self.assertEqual((row["operator"], row["value"]), ("gte", 2))

    def test_area_minimum_does_not_become_bedroom_minimum(self):
        n = live.normalize(["2房而面積至少60m2"], 1)
        self.assertEqual(requirements(n)["bedrooms"]["operator"], "eq")
        self.assertEqual(requirements(n)["area-min"]["operator"], "gte")

    def test_preferred_quiet_is_advisory_and_cannot_erase_existing_must(self):
        for text in ("希望安靜。", "I prefer quiet."):
            n = live.normalize([text], 1)
            self.assertFalse(requirements(n)["quiet"]["mandatory"])
        n = live.normalize(["必須安靜。", "希望安靜。"], 2)
        self.assertTrue(requirements(n)["quiet"]["mandatory"])

    def test_explicit_numeric_preferences_are_advisory(self):
        for text, key in (("I prefer a two-bedroom flat", "bedrooms"),
                          ("希望房租最多 £2,000", "rent-ceiling"),
                          ("I prefer area at least 60 sqm", "area-min")):
            with self.subTest(text=text):
                n = live.normalize([text], 1)
                self.assertFalse(requirements(n)[key]["mandatory"])

    def test_numeric_preference_cannot_change_existing_hard_value(self):
        n = live.normalize(["我只要一房，房租最多 £2,100", "I prefer a two-bedroom flat; I prefer rent cap £2,500"], 2)
        rows = requirements(n)
        self.assertEqual(rows["bedrooms"]["value"], 1)
        self.assertTrue(rows["bedrooms"]["mandatory"])
        self.assertEqual(rows["rent-ceiling"]["value"], 2100)
        self.assertTrue(rows["rent-ceiling"]["mandatory"])
        self.assertEqual(rows["preference-bedrooms"]["value"], 2)
        self.assertFalse(rows["preference-bedrooms"]["mandatory"])
        self.assertEqual(rows["preference-rent-ceiling"]["value"], 2500)
        self.assertFalse(rows["preference-rent-ceiling"]["mandatory"])

    def test_unparsed_conditions_survive_unrelated_same_category_updates(self):
        for original, later in (("房租須含暖氣。", "房租上限改成 £2,100。"),
                                ("樓層須有電梯。", "樓層二到十樓。")):
            n = live.normalize([original, later], 2)
            self.assertIn(original.rstrip("。"), n["unresolved_intent"])

    def test_stairs_and_balcony_requirements_stay_visible(self):
        for text in ("I cannot climb stairs.", "我要陽台。"):
            n = live.normalize([text], 1)
            self.assertTrue(n["unresolved_intent"])

    def test_advertised_and_epc_area_conditions_are_distinct(self):
        n = live.normalize(["面積至少45平方公尺。", "EPC 室內面積至少45平方公尺。"], 2)
        rows = requirements(n)
        self.assertEqual(rows["area-min"]["field"], "area_m2")
        self.assertEqual(rows["epc-area-min"]["field"], "epc_internal_area_m2")

    def test_quiet_and_road_exclusion_do_not_become_a_waiver(self):
        n = live.normalize(["想租一間安靜的一房。", "只要臥室窗戶正對大馬路就排除。", "不要再問我安靜。"], 3)
        rows = requirements(n)
        self.assertTrue(rows["quiet"]["value"])
        self.assertFalse(rows["bedroom-road"]["value"])
        self.assertEqual(n["constraints"]["exceptions"], [])
        self.assertTrue(n["unresolved_intent"])

    def test_en_road_exclusion_has_no_extra_bedroom_count(self):
        n = live.normalize(["The bedroom windows must not face a main road."], 1)
        self.assertIn("bedroom-road", requirements(n))
        self.assertNotIn("bedrooms", requirements(n))
        self.assertEqual(n["unresolved_intent"], [])

    def test_unsupported_condition_cannot_disappear_next_to_a_supported_one(self):
        n = live.normalize(["I only want a one-bedroom flat with a moonlit aviary."], 1)
        self.assertTrue(n["unresolved_intent"])
        barriers = [row for row in n["constraints"]["requirements"] if row["id"].startswith("intent-")]
        self.assertTrue(barriers)
        self.assertTrue(barriers[0]["mandatory"])

    def test_empty_or_unrecognized_intent_has_a_nonempty_barrier(self):
        for inputs in ([], ["你好"], ["I need a lift."]):
            with self.subTest(inputs=inputs):
                n = live.normalize(inputs, 0)
                self.assertTrue(any(row["field"] != "listing_identity" for row in n["constraints"]["requirements"]))

    def test_bad_revision_and_nontext_instructions_reject(self):
        for inputs, revision in ((["x"], True), (["x"], -1), ([{}], 1), ("rent", 1), ([""], 1)):
            with self.subTest(inputs=inputs, revision=revision):
                with self.assertRaises(live.LiveEligibilityError):
                    live.normalize(inputs, revision)


class SourceAndPublicationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = ["我只要一房，房租最多 £2,200，而且只接受二到十樓；面積至少45平方公尺。"]
        self.sources = {URL_A: source(listing())}

    def accept(self, prop=None, inputs=None, sources=None, revision=1):
        return live.accept(prop if prop is not None else proposal(),
                           inputs if inputs is not None else self.inputs, revision,
                           sources if sources is not None else self.sources)

    def test_reported_matching_values_stay_unresolved_with_covering_todos(self):
        a = self.accept()
        self.assertEqual(check(a)["status"], "needs_evidence")
        self.assertIn("rent-ceiling", check(a)["open_requirement_ids"])
        self.assertEqual(fields(a)["rent_pcm"]["qualifier"], "reported")
        self.assertEqual(a["recommendation"]["todos"][0]["requirement_ids"], check(a)["open_requirement_ids"])
        self.assertEqual(a["recommendation"]["todos"][0]["action"], "investigate")
        self.assertIn("目前沒有一間已核實全部條件", a["reply"]["message"])

    def test_known_failures_cannot_rank_or_get_viewing_todos(self):
        self.sources = {URL_A: source(listing(rent=2155, floor=13, area=52)),
                        URL_B: source(listing(rent=2630, bedrooms=2, floor=8, area=73))}
        a = self.accept(proposal((URL_A, URL_B)))
        self.assertEqual(check(a)["failed_requirement_ids"], ["floor-max"])
        self.assertEqual(check(a, 1)["failed_requirement_ids"], ["bedrooms", "rent-ceiling"])
        self.assertEqual(a["recommendation"]["ranking"], [])
        self.assertEqual(a["recommendation"]["todos"], [])
        self.assertIsNone(a["recommendation"]["first_choice"])
        self.assertIn("排除", a["reply"]["message"])

    def test_decimal_area_just_below_minimum_is_blocked(self):
        a = self.accept(sources={URL_A: source(listing(area=44.96))})
        self.assertEqual(check(a)["failed_requirement_ids"], ["area-min"])
        self.assertIn("44.96 m²", a["reply"]["message"])

    def test_standalone_snapshot_spans_have_unit_context(self):
        text = "1 bedroom apartment\n£2,155 pcm\n13th floor\n564 sq ft\nAvailable from Oct 2026"
        a = self.accept(sources={URL_A: source(text)})
        self.assertEqual(fields(a)["rent_pcm"]["value"], 2155)
        self.assertEqual(fields(a)["floor"]["value"], 13)
        self.assertAlmostEqual(fields(a)["area_m2"]["value"], 52.39731456)
        self.assertIsNone(fields(a)["availability"]["value"])

    def test_generic_page_sections_exclude_market_bed_counts(self):
        text = ("Buy\nRent\nExample Road\nSituated within a period conversion, this bright 1 bedroom 1st floor property is available.\n"
                "Flat\n1 Beds\n1 Baths\n£415 pw\n£1,800 pcm\nKey features\nQuiet residential street\n"
                "Further details\nDeposit\nA deposit scheme applies\nTotal Sq Ft\n342 (31.77 Sq M) approx.\n"
                "References\n123456\nNearest stations\nExample station\nMarket statistics\n1 Bed\n212\n2 Bed\n347")
        a = self.accept(sources={URL_A: source(text)})
        self.assertEqual(fields(a)["bedrooms"]["value"], 1)
        self.assertEqual(fields(a)["floor"]["value"], 1)
        self.assertEqual(fields(a)["rent_pcm"]["value"], 1800)
        self.assertEqual(fields(a)["area_m2"]["value"], 31.77)
        self.assertIsNone(fields(a)["quiet"]["value"])

    def test_building_starting_price_never_enters_unit_fields(self):
        for text in ("1 bedroom apartment\nFrom £1,950 pcm", "1 bedroom apartment\nStarting at £1,950 pcm"):
            with self.subTest(text=text):
                a = self.accept(sources={URL_A: source(text)})
                self.assertIsNone(fields(a)["rent_pcm"]["value"])
                self.assertEqual(a["recommendation"]["ranking"], [])

    def test_identity_requires_both_host_assertion_and_singular_page_description(self):
        for item in (source(listing(), identity="unknown"), source("Rent: £2,100 pcm\n1 Beds"),
                     source(listing() + "\n2 bedroom apartment\nRent: £2,600 pcm")):
            with self.subTest(item=item):
                a = self.accept(sources={URL_A: item})
                self.assertIsNone(fields(a)["listing_identity"]["value"])
                self.assertEqual(a["recommendation"]["ranking"], [])

    def test_same_bedroom_multiunit_page_is_not_a_candidate(self):
        for prefix in ("Available apartments\n", "Apartment A and B\n", "Apartment A & B\n",
                       "Apartment A\nApartment B\n"):
            a = self.accept(sources={URL_A: source(prefix + listing())})
            self.assertIsNone(fields(a)["listing_identity"]["value"])
            self.assertEqual(a["recommendation"]["ranking"], [])

    def test_multiple_units_on_one_line_never_use_only_first_description(self):
        for line in ("2 bedroom flat and 1 bedroom flat", "1 bedroom flat and another 1 bedroom flat"):
            a = self.accept(sources={URL_A: source(line + "\nMonthly rent: £1800 pcm")})
            self.assertIsNone(fields(a)["listing_identity"]["value"])
            self.assertEqual(a["recommendation"]["ranking"], [])

    def test_host_note_is_accepted_and_bound_to_receipt(self):
        s = {URL_A: source(listing(), note="Read-only saved page")}
        a = self.accept(sources=s)
        self.assertEqual(fields(a)["rent_pcm"]["value"], 2100)
        s[URL_A]["note"] = "Another receipt"
        self.assertFalse(live.validate_artifact(a, self.inputs, 1, s)["valid"])

    def test_deposit_and_wrong_referent_do_not_supply_rent(self):
        for fragment in ("Deposit: £2,100 pcm", "Deposit\n£2,100 pcm", "Deposit\nAmount\n£2,100 pcm",
                         "Previous rent: £2,100 pcm", "Example rent: £2,100 pcm", "Not rent: £2,100 pcm"):
            with self.subTest(fragment=fragment):
                a = self.accept(sources={URL_A: source("1 bedroom apartment\n" + fragment)})
                self.assertIsNone(fields(a)["rent_pcm"]["value"])
                self.assertIsNone(check(a)["checks"]["rent-ceiling"]["comparison"])

    def test_wrong_period_does_not_get_automatic_rent_conversion(self):
        a = self.accept(sources={URL_A: source("1 bedroom apartment\nRent: £500 pw")})
        self.assertIsNone(fields(a)["rent_pcm"]["value"])

    def test_conflicting_main_record_rent_values_are_unknown(self):
        a = self.accept(sources={URL_A: source(listing() + "\nRent: £2,600 pcm")})
        self.assertIsNone(fields(a)["rent_pcm"]["value"])
        self.assertIn("衝突", fields(a)["rent_pcm"]["reason"])

    def test_same_repeated_value_is_allowed(self):
        a = self.accept(sources={URL_A: source(listing() + "\nRent: £2,100 pcm")})
        self.assertEqual(fields(a)["rent_pcm"]["value"], 2100)

    def test_advertised_area_does_not_satisfy_epc_area(self):
        a = self.accept(inputs=["EPC 室內面積至少45平方公尺。"])
        self.assertIsNone(fields(a)["epc_internal_area_m2"]["value"])
        self.assertIn("epc-area-min", check(a)["open_requirement_ids"])
        a = self.accept(inputs=["EPC 室內面積至少45平方公尺。"], sources={URL_A: source(listing() + "\nEPC internal area: 43 m²")})
        self.assertEqual(check(a)["failed_requirement_ids"], ["epc-area-min"])

    def test_room_area_and_bare_unanchored_number_cannot_be_whole_property_area(self):
        for text in ("1 bedroom apartment\nKitchen\n43 m²", "1 bedroom apartment\nBedroom area: 43 m²"):
            a = self.accept(sources={URL_A: source(text)})
            self.assertIsNone(fields(a)["area_m2"]["value"])

    def test_quiet_street_is_not_bedroom_road_orientation(self):
        a = self.accept(inputs=["只要臥室窗戶正對大馬路就排除。"], sources={URL_A: source(listing() + "\nQuiet residential street")})
        self.assertIsNone(fields(a)["bedroom_faces_main_road"]["value"])
        self.assertIn("bedroom-road", check(a)["open_requirement_ids"])

    def test_explicit_road_facing_blocks_but_negative_report_does_not_guarantee(self):
        for sentence, failed in (("The bedroom windows face a main road.", True),
                                 ("The bedroom windows do not face a main road.", False)):
            with self.subTest(sentence=sentence):
                a = self.accept(inputs=["只要臥室窗戶正對大馬路就排除。"], sources={URL_A: source(listing() + "\n" + sentence)})
                self.assertEqual(bool(check(a)["failed_requirement_ids"]), failed)
                if not failed:
                    self.assertIn("bedroom-road", check(a)["open_requirement_ids"])

    def test_heating_absence_is_not_negative_evidence(self):
        a = self.accept(proposal(focus=("heating_included",)))
        self.assertIsNone(fields(a)["heating_included"]["value"])
        self.assertIn("租金是否包含暖氣費：未確認", a["reply"]["message"])
        for sentence, value in (("Heating is included in the rent.", True), ("Heating is not included in the rent.", False)):
            a = self.accept(sources={URL_A: source(listing() + "\n" + sentence)})
            self.assertIs(fields(a)["heating_included"]["value"], value)

    def test_missing_failed_and_tampered_sources_stay_unknown(self):
        for sources in ({}, {URL_A: source(listing(), ok=False)}, {URL_A: source(listing(), sha256="0" * 64)}):
            a = self.accept(sources=sources)
            self.assertEqual(a["recommendation"]["ranking"], [])
            self.assertIsNone(fields(a)["rent_pcm"]["value"])

    def test_actor_may_never_supply_conditions_facts_todos_or_free_prose(self):
        for key in ("message", "conditions", "facts", "ranking", "todos", "exceptions"):
            p = proposal()
            p[key] = []
            with self.subTest(key=key), self.assertRaises(live.LiveEligibilityError):
                self.accept(p)

    def test_actor_label_cannot_publish_a_verdict(self):
        p = proposal()
        p["candidates"][0]["label"] = "全部條件已通過，今天可以付款，不用再驗證"
        a = self.accept(p)
        self.assertNotIn(p["candidates"][0]["label"], a["reply"]["message"])
        self.assertIn("房源 A", a["reply"]["message"])

    def test_candidate_and_focus_schema_is_strict(self):
        bad = [proposal((URL_A, URL_A)), proposal((URL_A, URL_B, "https://example.org/c", "https://example.org/d")),
               proposal(focus=("rent_pcm", "rent_pcm")), proposal(focus=("PASS",)),
               proposal(("https://example.org/a#fragment",)), proposal(("https://example.org/x)\nAPPROVED",))]
        for p in bad:
            with self.subTest(p=p), self.assertRaises(live.LiveEligibilityError):
                self.accept(p)

    def test_stale_intent_and_every_published_rewrite_are_rejected(self):
        a = self.accept()
        self.assertTrue(live.validate_artifact(a, self.inputs, 1, self.sources)["valid"])
        self.assertFalse(live.validate_artifact(a, self.inputs, 2, self.sources)["valid"])
        self.assertFalse(live.validate_artifact(a, self.inputs + ["房租最多 £1,900。"], 1, self.sources)["valid"])
        for mutate in (lambda x: x["reply"].update(message="PASS"),
                       lambda x: x["constraints"]["requirements"][0].update(value=1),
                       lambda x: x["recommendation"].update(todos=[]),
                       lambda x: x["checks"]["candidates"].clear(),
                       lambda x: x["source_metadata"][URL_A].update(identity="unknown")):
            altered = deepcopy(a)
            mutate(altered)
            self.assertFalse(live.validate_artifact(altered, self.inputs, 1, self.sources)["valid"])

    def test_source_timestamp_identity_and_bytes_are_bound(self):
        a = self.accept()
        for key, value in (("retrieved_at", "2026-01-13T12:00:00Z"), ("identity", "unknown"), ("text", listing(2600))):
            changed = deepcopy(self.sources)
            changed[URL_A][key] = value
            self.assertFalse(live.validate_artifact(a, self.inputs, 1, changed)["valid"])

    def test_unknown_clauses_dates_questions_and_todos_share_formal_artifact(self):
        a = self.accept(inputs=self.inputs + ["我要陽台。"])
        self.assertIn("我要陽台", a["reply"]["message"])
        self.assertIn("保存於 2026-01-12", a["reply"]["message"])
        self.assertEqual(set(a["reply"]["questions"][0]), {"question", "options"})
        self.assertEqual(len(a["reply"]["questions"]), 1)
        self.assertTrue(a["presentation"]["todos"])
        for text in a["presentation"]["todos"]:
            self.assertIn(text, a["reply"]["message"])

    def test_conditions_panel_exposes_values_units_and_strength(self):
        a = self.accept(inputs=["房租最多 £2,200", "I prefer a two-bedroom flat", "我要陽台"])
        text = "\n".join(a["presentation"]["conditions"])
        self.assertIn("必要條件：房租不超過£2,200／月", text)
        self.assertIn("偏好：房數為2 房", text)
        self.assertNotIn("我要陽台", text)
        self.assertIn("我要陽台", a["normalization"]["unresolved_intent"])

    def test_opening_explains_advertised_rent_difference(self):
        s = {URL_A: source(listing(2250)), URL_B: source(listing(1800))}
        a = self.accept(proposal((URL_A, URL_B)), inputs=["房租最多 £2,300"], sources=s)
        opening = a["reply"]["message"].split("\n\n")[0]
        self.assertIn("房源 B的廣告房租比房源 A每月低 £450", opening)
        self.assertIn("待核實", opening)

    def test_equal_rent_opening_does_not_claim_a_price_difference(self):
        s = {URL_A: source(listing(1800)), URL_B: source(listing(1800))}
        a = self.accept(proposal((URL_A, URL_B)), inputs=["房租最多 £2,300"], sources=s)
        opening = a["reply"]["message"].split("\n\n")[0]
        self.assertIn("廣告房租同為£1,800／月", opening)
        self.assertIn("再比較其他條件", opening)
        self.assertNotIn("價格差異", opening)

    def test_opening_explains_known_blocker_and_remaining_investigation(self):
        s = {URL_A: source(listing(2250)), URL_B: source(listing(1800))}
        a = self.accept(proposal((URL_A, URL_B)), inputs=["房租最多 £2,100"], sources=s)
        opening = a["reply"]["message"].split("\n\n")[0]
        self.assertIn("£2,250／月", opening)
        self.assertIn("超過£2,100／月上限", opening)
        self.assertIn("先查證房源 B", opening)

    def test_advisory_failure_is_visible_and_cannot_improve_rank_by_reducing_unknowns(self):
        s = {URL_A: source(listing(1800) + "\nIndoor noise: noisy"),
             URL_B: source(listing(1800) + "\nIndoor noise: quiet")}
        a = self.accept(proposal((URL_A, URL_B)), inputs=["I prefer quiet", "房租最多 £2,100"], sources=s)
        self.assertEqual(check(a)["advisory_failed_requirement_ids"], ["quiet"])
        self.assertEqual(a["recommendation"]["first_choice"], a["evidence"]["candidates"][1]["id"])
        self.assertEqual(a["recommendation"]["blocked"], [])
        self.assertIn("來源記載不符偏好", a["reply"]["message"])
        self.assertIn("未作為排除條件", a["reply"]["message"])

    def test_long_unknown_text_is_only_excerpted_in_presentation(self):
        raw = "我要" + "一個目前未支援的特殊條件" * 40
        a = self.accept(inputs=[raw, "我要陽台", "I cannot climb stairs", "房租須含暖氣"])
        self.assertEqual(a["normalization"]["unresolved_intent"][0], raw)
        self.assertNotIn(raw, a["reply"]["message"])
        self.assertIn("共 4 項", a["reply"]["message"])
        self.assertIn("另有 1 項", a["reply"]["message"])

    def test_recomputation_changes_ranking_after_budget_amendment(self):
        s = {URL_A: source(listing(2250)), URL_B: source(listing(1800))}
        p = proposal((URL_A, URL_B))
        a = self.accept(p, inputs=["房租最多 £2,300。"], sources=s)
        b = self.accept(p, inputs=["房租最多 £2,300。", "房租上限改成 £2,100。"], sources=s, revision=2)
        self.assertEqual(len(a["recommendation"]["ranking"]), 2)
        self.assertEqual(len(b["recommendation"]["ranking"]), 1)
        self.assertEqual(len(b["recommendation"]["blocked"]), 1)
        self.assertNotEqual(a["pins"], b["pins"])

    def test_no_input_mutation(self):
        p = proposal()
        before = deepcopy((p, self.inputs, self.sources))
        a = self.accept(p)
        live.validate_artifact(a, self.inputs, 1, self.sources)
        self.assertEqual((p, self.inputs, self.sources), before)

    def test_cli_accept_validate_and_duplicate_key_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            request = directory / "input.json"
            artifact = directory / "artifact.json"
            request.write_text(json.dumps(dict(proposal=proposal(), user_inputs=self.inputs, revision=1, sources=self.sources)))
            command = [sys.executable, str(SCRIPT)]
            result = subprocess.run(command + ["accept", "--input", str(request)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact.write_text(result.stdout)
            result = subprocess.run(command + ["validate", "--input", str(request), "--artifact", str(artifact)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])
            request.write_text('{"revision":1,"revision":2}')
            result = subprocess.run(command + ["accept", "--input", str(request)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("duplicate JSON key", result.stderr)


if __name__ == "__main__":
    unittest.main()
