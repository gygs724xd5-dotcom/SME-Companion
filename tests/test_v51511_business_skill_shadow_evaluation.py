import copy
import dataclasses
import unittest
from dataclasses import replace
from unittest.mock import patch

from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_evaluation import *
from brain.business_skill_shadow_observation import (
    AMBIGUITY_BLOCKED, CONFIDENCE_BLOCKED, EVIDENCE_INCOMPLETE, LIFECYCLE_BLOCKED,
    NO_CANDIDATE, SHADOW_SELECTED, ShadowObservationRequest, observe_business_skill_shadow,
)

NOW = "2026-07-10T12:00:00+07:00"
CHANGE = "เดือนก่อนต้นทุน 20,000 บาท เดือนนี้ 24,000 บาท ต้นทุนเปลี่ยนไปเท่าไร"
UNIT = "ต้นทุนรวม 1,000 บาท ผลิตได้ 100 ชิ้น ต้นทุนต่อชิ้น"


def rich(value, **changes):
    result = {"value": value, "confidence": 1.0, "source": "current_turn",
              "freshness": "current", "user_confirmed": True}
    result.update(changes)
    return result


CE = {"previous_cost": rich(20000), "current_cost": rich(24000)}
UE = {"total_cost": rich(1000), "unit_quantity": rich(100)}


def case(case_id, message, evidence, label, skill=None):
    request = ShadowObservationRequest.from_mapping(message, evidence, reference_time=NOW if evidence else None)
    return ShadowEvaluationCase(case_id, request, ExpectedShadowOutcome(label, skill))


class V51511ShadowEvaluationTests(unittest.TestCase):
    def test_versions_frozen_contracts_registry_and_positive_fixtures(self):
        self.assertEqual(BUSINESS_SKILL_SHADOW_EVALUATION_VERSION, "5.15.11")
        self.assertEqual(BUSINESS_SKILL_REGISTRY_VERSION, "5.15.9.1")
        for contract in (ExpectedShadowOutcome, ShadowEvaluationCase, ShadowDriftFinding,
                         ShadowEvaluationResult, ShadowSkillTotal, ShadowEvaluationSummary):
            self.assertTrue(contract.__dataclass_params__.frozen)
        fixtures = (
            case("en-change", "my cost increased this month", CE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]),
            case("en-unit", "cost per unit", UE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[1]),
            case("th-change", CHANGE, CE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]),
            case("th-unit", UNIT, UE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[1]),
        )
        summary = evaluate_business_skill_shadows(fixtures)
        self.assertEqual((summary.total_cases, summary.passed_cases, summary.selected_count), (4, 4, 4))
        self.assertEqual(summary.true_positive_count, 4)
        self.assertEqual(tuple(x.expected_count for x in summary.per_skill_totals), (2, 2))

    def test_abstentions_and_evidence_blocks(self):
        fixtures = [case(f"none-{i}", msg, {}, TRUE_NEGATIVE) for i, msg in enumerate(
            ("", "   ", "วันนี้อากาศดี", "ทำต่อได้เลย"))]
        fixtures += [
            case("missing", CHANGE, {"previous_cost": rich(1)}, EXPECTED_EVIDENCE_BLOCK),
            case("invalid-type", CHANGE, {"previous_cost": rich("x"), "current_cost": rich(2)}, EXPECTED_EVIDENCE_BLOCK),
            case("invalid-value", UNIT, {"total_cost": rich(-1), "unit_quantity": rich(2)}, EXPECTED_EVIDENCE_BLOCK),
            case("stale", CHANGE, {"previous_cost": rich(1, freshness="stale"), "current_cost": rich(2)}, EXPECTED_EVIDENCE_BLOCK),
            case("assumed", CHANGE, {"previous_cost": rich(1, assumed=True), "current_cost": rich(2)}, EXPECTED_EVIDENCE_BLOCK),
            case("conflict", CHANGE, {"previous_cost": rich(1, validation_errors=["conflicting sources"]), "current_cost": rich(2)}, EXPECTED_EVIDENCE_BLOCK),
            case("low-evidence", CHANGE, {"previous_cost": rich(1, confidence=.2), "current_cost": rich(2)}, EXPECTED_LOW_CONFIDENCE_BLOCK),
        ]
        summary = evaluate_business_skill_shadows(reversed(fixtures))
        self.assertEqual(summary.total_cases, 11)
        self.assertEqual(summary.true_negative_count, 4)
        self.assertEqual(summary.evidence_block_count, 6)
        self.assertEqual(summary.low_confidence_block_count, 1)
        self.assertEqual(tuple(x.case_id for x in summary.results), tuple(sorted(x.case_id for x in fixtures)))

    def test_competing_candidates_and_unresolved_ambiguity(self):
        evidence = {**CE, **UE}
        combined = f"{CHANGE} {UNIT}"
        summary = evaluate_business_skill_shadows((case("ambiguous", combined, evidence, EXPECTED_AMBIGUITY_BLOCK),))
        self.assertEqual(summary.ambiguity_block_count, 1)
        self.assertEqual(summary.results[0].observation.competing_candidate_ids,
                         ("cost.per_unit_calculation.v1",))

    def test_false_positive_false_negative_and_misclassification_drift(self):
        fixtures = (
            case("fp", CHANGE, CE, TRUE_NEGATIVE),
            case("fn", "วันนี้อากาศดี", {}, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]),
            case("mis", UNIT, UE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]),
        )
        summary = evaluate_business_skill_shadows(fixtures)
        self.assertEqual((summary.false_positive_count, summary.false_negative_count,
                          summary.misclassification_count), (1, 1, 1))
        self.assertEqual(summary.failed_cases, 3)
        self.assertEqual(tuple(x.case_id for x in summary.drift_findings), ("fn", "fp", "mis"))
        self.assertFalse(any(hasattr(x, "answer") for x in summary.drift_findings))

    def test_isolated_ambiguity_lifecycle_and_low_candidate_boundary(self):
        base = observe_business_skill_shadow(ShadowObservationRequest.from_mapping(CHANGE, CE, reference_time=NOW))
        scenarios = (
            ("ambiguity", AMBIGUITY_BLOCKED, EXPECTED_AMBIGUITY_BLOCK),
            ("lifecycle", LIFECYCLE_BLOCKED, EXPECTED_LIFECYCLE_BLOCK),
            ("low", CONFIDENCE_BLOCKED, EXPECTED_LOW_CONFIDENCE_BLOCK),
        )
        for case_id, outcome, label in scenarios:
            isolated = replace(base, outcome=outcome, selected_shadow_skill_id=None)
            with patch("brain.business_skill_shadow_evaluation.observe_business_skill_shadow", return_value=isolated):
                result = evaluate_business_skill_shadows((case(case_id, "x", {}, label),))
            self.assertEqual(result.passed_cases, 1)
        self.assertEqual(get_business_skill_registry(), get_business_skill_registry())

    def test_validation_determinism_independence_and_mutation_safety(self):
        with self.assertRaises(ValueError):
            ShadowEvaluationCase(" ", ShadowObservationRequest("x"), ExpectedShadowOutcome(TRUE_NEGATIVE))
        with self.assertRaises(ValueError):
            ExpectedShadowOutcome("BROKEN")
        with self.assertRaises(ValueError):
            ExpectedShadowOutcome(TRUE_NEGATIVE, EVALUATED_SKILL_IDS[0])
        with self.assertRaises(ValueError):
            ShadowEvaluationCase("e", ShadowObservationRequest.from_mapping(CHANGE, CE),
                                 ExpectedShadowOutcome(TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]))
        duplicate = case("same", "", {}, TRUE_NEGATIVE)
        with self.assertRaises(ValueError):
            evaluate_business_skill_shadows((duplicate, duplicate))

        evidence = copy.deepcopy(CE)
        original = copy.deepcopy(evidence)
        fixture = case("stable", CHANGE, evidence, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0])
        evidence["previous_cost"]["value"] = 999
        registry_before = copy.deepcopy(get_business_skill_registry())
        first = evaluate_business_skill_shadows((fixture,))
        second = evaluate_business_skill_shadows((fixture,))
        self.assertEqual(first, second)
        self.assertNotEqual(evidence, original)
        self.assertEqual(first.results[0].observation.current_message, CHANGE)
        self.assertEqual(get_business_skill_registry(), registry_before)
        other = evaluate_business_skill_shadows((case("other", "", {}, TRUE_NEGATIVE),))
        self.assertEqual(evaluate_business_skill_shadows((fixture,)), first)
        self.assertEqual(other.true_negative_count, 1)

    def test_authority_boundary(self):
        summary = evaluate_business_skill_shadows((case("x", CHANGE, CE, TRUE_POSITIVE, EVALUATED_SKILL_IDS[0]),))
        forbidden = {"answer", "calculation", "business_reasoning", "follow_up", "action",
                     "response", "response_content", "application_state"}
        for contract in (ShadowEvaluationResult, ShadowEvaluationSummary, ShadowDriftFinding):
            self.assertTrue(forbidden.isdisjoint(field.name for field in dataclasses.fields(contract)))
        self.assertFalse(summary.authorized or summary.executed or summary.reasoning_executed or
                         summary.response_generated or summary.follow_up_generated or summary.persisted)
        observation = summary.results[0].observation
        self.assertFalse(observation.authorized or observation.executed or observation.response_generated or observation.persisted)


if __name__ == "__main__":
    unittest.main()
