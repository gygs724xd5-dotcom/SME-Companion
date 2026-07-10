import ast
import copy
import dataclasses
import unittest
from pathlib import Path

from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE, UNIT_TESTED
from brain.business_skill_registry import BUSINESS_SKILL_REGISTRY_VERSION, get_business_skill_registry
from brain.business_skill_shadow_observation import (
    AMBIGUITY_BLOCKED,
    BUSINESS_SKILL_SHADOW_OBSERVATION_VERSION,
    CANDIDATE_REJECTED,
    CONFIDENCE_BLOCKED,
    DIAGNOSTIC_ONLY,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_INVALID,
    EVIDENCE_STALE,
    LIFECYCLE_BLOCKED,
    NO_CANDIDATE,
    NO_RUNTIME_AUTHORITY,
    SHADOW_SELECTED,
    ShadowEvidenceInput,
    ShadowObservation,
    ShadowObservationRequest,
    observe_business_skill_shadow,
    observe_business_skill_shadows,
)


CHANGE = "เดือนก่อนต้นทุน 20,000 บาท เดือนนี้ 24,000 บาท ต้นทุนเปลี่ยนไปเท่าไร"
UNIT = "ต้นทุนรวม 1,000 บาท ผลิตได้ 100 ชิ้น ต้นทุนต่อชิ้นเท่าไร"
NOW = "2026-07-10T12:00:00+07:00"


def rich(value, **changes):
    item = {"value": value, "confidence": 1.0, "source": "current_turn",
            "freshness": "current", "user_confirmed": True}
    item.update(changes)
    return item


CHANGE_EVIDENCE = {"previous_cost": rich(20000), "current_cost": rich(24000)}
UNIT_EVIDENCE = {"total_cost": rich(1000), "unit_quantity": rich(100)}


def request(message=CHANGE, evidence=CHANGE_EVIDENCE):
    return ShadowObservationRequest.from_mapping(message, evidence, reference_time=NOW)


class V51510BusinessSkillShadowObservationTests(unittest.TestCase):
    def test_versions_immutable_contracts_and_registry_counts(self):
        self.assertEqual(BUSINESS_SKILL_SHADOW_OBSERVATION_VERSION, "5.15.10")
        self.assertEqual(BUSINESS_SKILL_REGISTRY_VERSION, "5.15.9.1")
        for contract in (ShadowEvidenceInput, ShadowObservationRequest, ShadowObservation):
            self.assertTrue(contract.__dataclass_params__.frozen)
        registry = get_business_skill_registry()
        self.assertEqual(sum(x.active_status == SHADOW_AVAILABLE for x in registry), 2)
        self.assertEqual(sum(x.active_status == CONTRACTED for x in registry), 8)
        self.assertEqual(sum(x.active_status == UNIT_TESTED for x in registry), 0)
        self.assertEqual(sum(x.active_status == LIMITED_ACTIVE for x in registry), 0)
        self.assertEqual(sum(x.active_status == STABLE for x in registry), 0)

    def assert_positive(self, message, evidence, skill_id):
        result = observe_business_skill_shadow(request(message, evidence))
        self.assertEqual(result.outcome, SHADOW_SELECTED)
        self.assertEqual(result.top_candidate_id, skill_id)
        self.assertEqual(result.selected_shadow_skill_id, skill_id)
        self.assertEqual(result.candidate_confidence, .5833)
        self.assertEqual(result.selector_confidence, .5833)
        self.assertEqual(result.candidates[0].score, 70)
        self.assertTrue(result.evidence_ready)
        self.assertEqual(result.evidence_confidence, 1.0)
        self.assertEqual(result.canonical_lifecycle_status, SHADOW_AVAILABLE)
        self.assertTrue(result.lifecycle_gate_passed)
        self.assertTrue(result.confidence_gate_passed)
        self.assertTrue(result.ambiguity_gate_passed)
        self.assertEqual(result.diagnostic_status, DIAGNOSTIC_ONLY)
        self.assertEqual(result.authority_boundary_status, NO_RUNTIME_AUTHORITY)
        return result

    def test_exact_thai_change_analysis_uses_canonical_shadow_skill(self):
        result = self.assert_positive(CHANGE, CHANGE_EVIDENCE, "cost.change_analysis.v1")
        canonical = next(x for x in get_business_skill_registry() if x.skill_id == result.selected_shadow_skill_id)
        self.assertEqual(result.candidates[0].lifecycle_status, canonical.active_status)

    def test_exact_thai_per_unit_uses_canonical_shadow_skill(self):
        self.assert_positive(UNIT, UNIT_EVIDENCE, "cost.per_unit_calculation.v1")

    def test_no_lifecycle_copy_calculation_reasoning_or_response_contract(self):
        source = (Path(__file__).parents[1] / "brain/business_skill_shadow_observation.py").read_text("utf-8")
        tree = ast.parse(source)
        calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertNotIn("replace", calls)
        forbidden_fields = {"answer", "calculated_result", "reasoning", "response", "follow_up_question"}
        self.assertTrue(forbidden_fields.isdisjoint(field.name for field in dataclasses.fields(ShadowObservation)))

    def test_empty_whitespace_unrelated_and_historical_context_only_have_no_candidate(self):
        for message in ("", "   ", "วันนี้อากาศดี", "ทำต่อได้เลย"):
            with self.subTest(message=message):
                self.assertEqual(observe_business_skill_shadow(request(message, {})).outcome, NO_CANDIDATE)

    def test_missing_invalid_type_invalid_value_low_confidence_stale_and_assumption(self):
        cases = (
            ({"previous_cost": rich(20000)}, EVIDENCE_INCOMPLETE, "EVIDENCE_MISSING:current_cost"),
            ({"previous_cost": rich("wrong"), "current_cost": rich(2)}, EVIDENCE_INVALID, "EVIDENCE_INVALID:previous_cost"),
            ({"total_cost": rich(-1), "unit_quantity": rich(2)}, EVIDENCE_INVALID, "EVIDENCE_INVALID:total_cost"),
            ({"previous_cost": rich(1, confidence=.2), "current_cost": rich(2)}, CONFIDENCE_BLOCKED, "EVIDENCE_LOW_CONFIDENCE:previous_cost"),
            ({"previous_cost": rich(1, freshness="stale"), "current_cost": rich(2)}, EVIDENCE_STALE, "EVIDENCE_STALE:previous_cost"),
            ({"previous_cost": rich(1, assumed=True), "current_cost": rich(2)}, EVIDENCE_INVALID, "EVIDENCE_INVALID:previous_cost"),
        )
        for evidence, outcome, reason in cases:
            message = UNIT if "total_cost" in evidence else CHANGE
            with self.subTest(outcome=outcome):
                result = observe_business_skill_shadow(request(message, evidence))
                self.assertEqual(result.outcome, outcome)
                self.assertIn(reason, result.reason_codes)

    def test_missing_confirmation_is_reported_according_to_canonical_contract(self):
        evidence = copy.deepcopy(CHANGE_EVIDENCE)
        evidence["previous_cost"]["user_confirmed"] = False
        result = observe_business_skill_shadow(request(CHANGE, evidence))
        # These canonical fields do not require confirmation; the harness does
        # not invent a stricter confirmation gate.
        self.assertEqual(result.outcome, SHADOW_SELECTED)
        self.assertEqual(result.confirmation_status, "SATISFIED_OR_NOT_REQUIRED")
        self.assertFalse(result.evidence[0].user_confirmed)

    def test_low_candidate_confidence_and_lifecycle_blocked_contracted_skill(self):
        low = observe_business_skill_shadow(request("Cost Change Analysis", CHANGE_EVIDENCE))
        self.assertEqual(low.outcome, CONFIDENCE_BLOCKED)
        contracted = observe_business_skill_shadow(request("please check promotion margin", {}))
        self.assertEqual(contracted.outcome, LIFECYCLE_BLOCKED)
        self.assertEqual(contracted.canonical_lifecycle_status, CONTRACTED)

    def test_competing_candidates_and_unresolved_ambiguity(self):
        evidence = {**CHANGE_EVIDENCE, **UNIT_EVIDENCE}
        result = observe_business_skill_shadow(request(f"{CHANGE} {UNIT}", evidence))
        self.assertEqual(result.outcome, AMBIGUITY_BLOCKED)
        self.assertEqual(result.competing_candidate_ids, ("cost.per_unit_calculation.v1",))
        self.assertIsNone(result.selected_shadow_skill_id)

    def test_malformed_and_conflicting_evidence(self):
        self.assertEqual(observe_business_skill_shadow(123).outcome, CANDIDATE_REJECTED)
        no_time = ShadowObservationRequest.from_mapping(CHANGE, CHANGE_EVIDENCE)
        self.assertEqual(observe_business_skill_shadow(no_time).reason_codes, ("REFERENCE_TIME_REQUIRED",))
        evidence = copy.deepcopy(CHANGE_EVIDENCE)
        evidence["previous_cost"]["validation_errors"] = ["conflicting sources"]
        self.assertEqual(observe_business_skill_shadow(request(CHANGE, evidence)).outcome, EVIDENCE_INVALID)

    def test_unknown_evidence_does_not_leak_into_canonical_mapping(self):
        evidence = {**CHANGE_EVIDENCE, "unknown_field": rich(999)}
        result = observe_business_skill_shadow(request(CHANGE, evidence))
        self.assertEqual(result.outcome, SHADOW_SELECTED)
        self.assertNotIn("unknown_field", tuple(item.field_name for item in result.evidence))

    def test_determinism_ordering_no_mutation_and_previous_result_stability(self):
        evidence = copy.deepcopy(CHANGE_EVIDENCE)
        req = request(CHANGE, evidence)
        before = copy.deepcopy(evidence)
        first = observe_business_skill_shadow(req)
        second = observe_business_skill_shadow(req)
        self.assertEqual(first, second)
        self.assertEqual(evidence, before)
        evidence["previous_cost"]["value"] = 1
        self.assertEqual(first, second)
        self.assertEqual(tuple(x.rank for x in first.candidates), tuple(range(1, len(first.candidates) + 1)))

    def test_batch_is_ordered_independent_and_has_no_cross_case_leakage(self):
        requests = (request(CHANGE, CHANGE_EVIDENCE), request(UNIT, UNIT_EVIDENCE), request(CHANGE, {}))
        first = observe_business_skill_shadows(requests)
        second = observe_business_skill_shadows(requests)
        self.assertEqual(first, second)
        self.assertEqual(tuple(x.top_candidate_id for x in first.observations),
                         ("cost.change_analysis.v1", "cost.per_unit_calculation.v1", "cost.change_analysis.v1"))
        self.assertEqual(first.observations[2].outcome, EVIDENCE_INCOMPLETE)
        self.assertNotIn("total_cost", tuple(x.field_name for x in first.observations[0].evidence))

    def test_authority_no_persistence_and_no_runtime_imports(self):
        result = observe_business_skill_shadow(request())
        for name in ("authorized", "executed", "reasoning_executed", "response_generated",
                     "follow_up_generated", "persisted"):
            self.assertFalse(getattr(result, name))
        path = Path(__file__).parents[1] / "brain/business_skill_shadow_observation.py"
        imports = []
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        forbidden = ("app", "brain.task_router", "brain.planner_engine", "brain.business_workflow_engine",
                     "brain.response_authority", "brain.business_memory_engine", "streamlit", "logging")
        self.assertFalse(any(name == word or name.startswith(f"{word}.") for name in imports for word in forbidden))


if __name__ == "__main__":
    unittest.main()
