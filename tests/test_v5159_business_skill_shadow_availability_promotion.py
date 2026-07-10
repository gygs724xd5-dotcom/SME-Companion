import ast
import copy
import dataclasses
import inspect
import unittest

import brain.business_skill_shadow_availability_manifest as manifest_module
from brain.business_skill import CONTRACTED, LIMITED_ACTIVE, SHADOW_AVAILABLE, STABLE, UNIT_TESTED
from brain.business_skill_candidate_matcher import score_business_skill_candidate
from brain.business_skill_evidence_mapper import map_candidate_skill_evidence
from brain.business_skill_lifecycle_manifest import (
    APPROVED_LIFECYCLE_PROMOTIONS,
    apply_approved_lifecycle_promotions,
)
from brain.business_skill_registry import (
    BUSINESS_SKILL_REGISTRY_VERSION,
    get_business_skill_registry,
    validate_business_skill_registry,
)
from brain.business_skill_shadow_availability_manifest import (
    APPROVED_SHADOW_AVAILABILITY_PROMOTIONS,
    APPROVED_SHADOW_AVAILABILITY_SKILL_IDS,
    BUSINESS_SKILL_SHADOW_AVAILABILITY_MANIFEST_VERSION,
    SHADOW_AVAILABILITY_QUALIFICATION,
    BusinessSkillShadowAvailabilityPromotion,
    apply_approved_shadow_availability_promotion,
    apply_approved_shadow_availability_promotions,
    build_shadow_availability_promotion_diagnostics,
    get_shadow_availability_promotion,
    validate_shadow_availability_manifest,
    validate_shadow_availability_promotion,
)
from brain.business_skill_shadow_selector import (
    AMBIGUOUS_CANDIDATES,
    BELOW_CONFIDENCE_THRESHOLD,
    EVIDENCE_NOT_READY,
    LIFECYCLE_INELIGIBLE,
    SHADOW_SELECTED,
    select_shadow_business_skill,
)


CASES = {
    "cost.change_analysis.v1": ("my cost increased from 30 to 40", {"previous_cost": 30, "current_cost": 40}),
    "cost.per_unit_calculation.v1": ("please calculate cost per unit", {"total_cost": 100, "unit_quantity": 10}),
}


class V5159BusinessSkillShadowAvailabilityPromotionTests(unittest.TestCase):
    def setUp(self):
        self.baseline = tuple(dataclasses.replace(
            skill,
            active_status=UNIT_TESTED if skill.skill_id in APPROVED_SHADOW_AVAILABILITY_SKILL_IDS else skill.active_status,
            tests_required=tuple(test for test in skill.tests_required if "test_v5158_" not in test and "test_v5159_" not in test),
        ) for skill in get_business_skill_registry())

    def test_manifest_is_exact_immutable_and_cites_v5158(self):
        self.assertEqual(BUSINESS_SKILL_SHADOW_AVAILABILITY_MANIFEST_VERSION, "5.15.9")
        self.assertEqual(tuple(item.skill_id for item in APPROVED_SHADOW_AVAILABILITY_PROMOTIONS), APPROVED_SHADOW_AVAILABILITY_SKILL_IDS)
        self.assertEqual(len(APPROVED_SHADOW_AVAILABILITY_PROMOTIONS), 2)
        for item in APPROVED_SHADOW_AVAILABILITY_PROMOTIONS:
            self.assertEqual((item.from_status, item.to_status), (UNIT_TESTED, SHADOW_AVAILABLE))
            self.assertEqual(item.qualification_version, "5.15.8")
            self.assertEqual(item.qualification_type, SHADOW_AVAILABILITY_QUALIFICATION)
            self.assertIn("tests/test_v5158_business_skill_shadow_availability_qualification.py", item.qualification_test_files)
            with self.assertRaises(dataclasses.FrozenInstanceError):
                item.to_status = CONTRACTED
        self.assertIsNotNone(get_shadow_availability_promotion(APPROVED_SHADOW_AVAILABILITY_SKILL_IDS[0]))
        self.assertIsNone(get_shadow_availability_promotion(" " + APPROVED_SHADOW_AVAILABILITY_SKILL_IDS[0]))

    def test_manifest_rejects_duplicates_scope_and_invalid_transition(self):
        first, second = APPROVED_SHADOW_AVAILABILITY_PROMOTIONS
        cases = (
            (first, first),
            (first, dataclasses.replace(first, approval_reason="conflicting duplicate")),
            (dataclasses.replace(first, skill_id="cost.unknown.v1"), second),
            (dataclasses.replace(first, skill_id="pricing.basic_price_suggestion.v1"), second),
            (dataclasses.replace(first, from_status=CONTRACTED), second),
            (dataclasses.replace(first, qualification_version="5.15.7"), second),
            (dataclasses.replace(first, qualification_type="UNIT_TEST_QUALIFICATION"), second),
            (dataclasses.replace(first, qualification_test_files=()), second),
            (dataclasses.replace(first, qualification_test_files=(first.qualification_test_files[0],) * 2), second),
            (dataclasses.replace(first, qualification_test_files=("malformed",)), second),
        )
        for manifest in cases:
            with self.subTest(manifest=manifest):
                self.assertFalse(validate_shadow_availability_manifest(manifest)["valid"])

    def test_transition_policy_rejects_same_backward_skips_and_other_forward_steps(self):
        first = APPROVED_SHADOW_AVAILABILITY_PROMOTIONS[0]
        cases = (
            {"from_status": UNIT_TESTED, "to_status": UNIT_TESTED},
            {"from_status": SHADOW_AVAILABLE, "to_status": UNIT_TESTED},
            {"from_status": CONTRACTED, "to_status": SHADOW_AVAILABLE},
            {"from_status": UNIT_TESTED, "to_status": LIMITED_ACTIVE},
            {"from_status": SHADOW_AVAILABLE, "to_status": LIMITED_ACTIVE},
            {"from_status": LIMITED_ACTIVE, "to_status": STABLE},
            {"from_status": "UNKNOWN", "to_status": SHADOW_AVAILABLE},
            {"from_status": UNIT_TESTED, "to_status": "UNKNOWN"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertFalse(validate_shadow_availability_promotion(dataclasses.replace(first, **changes))["valid"])

    def test_copy_promotion_changes_only_status_and_test_provenance(self):
        original = self.baseline[0]
        promoted = apply_approved_shadow_availability_promotion(original)
        changed = [field.name for field in dataclasses.fields(original) if getattr(original, field.name) != getattr(promoted, field.name)]
        self.assertEqual(changed, ["tests_required", "active_status"])
        self.assertEqual(original.active_status, UNIT_TESTED)
        self.assertEqual(promoted.active_status, SHADOW_AVAILABLE)
        self.assertIn("tests/test_v5158_business_skill_shadow_availability_qualification.py", promoted.tests_required)
        self.assertIn("tests/test_v5159_business_skill_shadow_availability_promotion.py", promoted.tests_required)
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(promoted)

    def test_application_rejects_unknown_duplicate_mismatch_and_bad_audit_sources(self):
        source = self.baseline[0]
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(dataclasses.replace(source, skill_id="unknown.v1"))
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(dataclasses.replace(source, active_status=CONTRACTED))
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(dataclasses.replace(source, active_status=SHADOW_AVAILABLE))
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(dataclasses.replace(source, tests_required=source.tests_required * 2))
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotion(dataclasses.replace(source, tests_required=("bad-reference",)))
        with self.assertRaises(ValueError):
            apply_approved_shadow_availability_promotions((*self.baseline, self.baseline[0]))

    def test_registry_has_exact_v5159_state(self):
        registry = get_business_skill_registry()
        self.assertEqual(BUSINESS_SKILL_REGISTRY_VERSION, "5.15.9.1")
        self.assertEqual(tuple(skill.skill_id for skill in registry if skill.active_status == SHADOW_AVAILABLE), APPROVED_SHADOW_AVAILABILITY_SKILL_IDS)
        self.assertEqual(sum(skill.active_status == CONTRACTED for skill in registry), 8)
        self.assertEqual(sum(skill.active_status == UNIT_TESTED for skill in registry), 0)
        self.assertEqual(sum(skill.active_status == LIMITED_ACTIVE for skill in registry), 0)
        self.assertEqual(sum(skill.active_status == STABLE for skill in registry), 0)
        self.assertTrue(validate_business_skill_registry()["valid"])

    def test_v5157_then_v5159_order_preserves_history_and_non_lifecycle_contract(self):
        contracted = tuple(dataclasses.replace(
            skill,
            active_status=CONTRACTED,
            tests_required=tuple(test for test in skill.tests_required if "test_v5156_" not in test and
                                 "test_v5157_" not in test and "test_v5158_" not in test and "test_v5159_" not in test),
        ) for skill in get_business_skill_registry())
        intermediate = apply_approved_lifecycle_promotions(contracted)
        final = apply_approved_shadow_availability_promotions(intermediate)
        self.assertEqual(final, get_business_skill_registry())
        self.assertEqual(tuple(item.qualification_version for item in APPROVED_LIFECYCLE_PROMOTIONS), ("5.15.6", "5.15.6"))
        for before, after in zip(contracted, final):
            changed = {field.name for field in dataclasses.fields(before) if getattr(before, field.name) != getattr(after, field.name)}
            self.assertLessEqual(changed, {"tests_required", "active_status"})
        for skill in final[:2]:
            self.assertEqual(skill.tests_required.count("tests/test_v5156_business_skill_lifecycle_qualification.py"), 1)
            self.assertEqual(skill.tests_required.count("tests/test_v5157_business_skill_lifecycle_promotion.py"), 1)
            self.assertEqual(skill.tests_required.count("tests/test_v5158_business_skill_shadow_availability_qualification.py"), 1)
            self.assertEqual(skill.tests_required.count("tests/test_v5159_business_skill_shadow_availability_promotion.py"), 1)

    def test_repeated_construction_is_deterministic_and_does_not_mutate_inputs(self):
        source = copy.deepcopy(self.baseline)
        before = copy.deepcopy(source)
        first = apply_approved_shadow_availability_promotions(source)
        second = apply_approved_shadow_availability_promotions(source)
        self.assertEqual(first, second)
        self.assertEqual(source, before)
        self.assertEqual(get_business_skill_registry(), get_business_skill_registry())
        self.assertIsInstance(APPROVED_SHADOW_AVAILABILITY_PROMOTIONS, tuple)

    def test_canonical_matcher_mapper_selector_selects_both_cost_skills(self):
        registry = get_business_skill_registry()
        for skill_id, (message, evidence) in CASES.items():
            with self.subTest(skill_id=skill_id):
                skill = next(item for item in registry if item.skill_id == skill_id)
                candidate = score_business_skill_candidate(message, skill)
                mapping = map_candidate_skill_evidence(candidate, evidence, registry)
                decision = select_shadow_business_skill([candidate], [mapping], registry)
                self.assertEqual(decision["selection_status"], SHADOW_SELECTED)
                self.assertEqual(decision["shadow_selected_skill_id"], skill_id)
                for key in ("authorized", "executed", "reasoning_executed", "response_generated", "follow_up_generated"):
                    self.assertFalse(decision[key])

    def test_selector_keeps_lifecycle_evidence_confidence_and_ambiguity_gates(self):
        registry = get_business_skill_registry()
        cost = registry[0]
        candidate = score_business_skill_candidate(CASES[cost.skill_id][0], cost)
        good = map_candidate_skill_evidence(candidate, CASES[cost.skill_id][1], registry)
        contracted = registry[2]
        contracted_candidate = score_business_skill_candidate("check the promotion margin", contracted)
        contracted_evidence = map_candidate_skill_evidence(contracted_candidate, {"selling_price": 100, "promotion_price": 90, "unit_cost": 50}, registry)
        self.assertEqual(select_shadow_business_skill([contracted_candidate], [contracted_evidence], registry)["selection_status"], LIFECYCLE_INELIGIBLE)
        missing = map_candidate_skill_evidence(candidate, {}, registry)
        self.assertEqual(select_shadow_business_skill([candidate], [missing], registry)["selection_status"], EVIDENCE_NOT_READY)
        self.assertEqual(select_shadow_business_skill([candidate], [good], registry, minimum_candidate_confidence=.99)["selection_status"], BELOW_CONFIDENCE_THRESHOLD)
        tied = dict(candidate, candidate_confidence=.8)
        other_skill = registry[1]
        other = dict(score_business_skill_candidate(CASES[other_skill.skill_id][0], other_skill), candidate_confidence=.8)
        other_mapping = map_candidate_skill_evidence(other, CASES[other_skill.skill_id][1], registry)
        self.assertEqual(select_shadow_business_skill([tied, other], [good, other_mapping], registry)["selection_status"], AMBIGUOUS_CANDIDATES)

    def test_diagnostics_keep_shadow_availability_diagnostic_only(self):
        result = build_shadow_availability_promotion_diagnostics(self.baseline)
        self.assertEqual(result["status_counts_before"], {UNIT_TESTED: 2, CONTRACTED: 8})
        self.assertEqual(result["status_counts_after"], {SHADOW_AVAILABLE: 2, CONTRACTED: 8})
        self.assertEqual(result["lifecycle_mutation_count"], 2)
        for key in ("authorized", "executed", "reasoning_executed", "tools_invoked", "follow_up_generated", "workflow_altered", "response_generated", "runtime_activated"):
            self.assertFalse(result[key])

    def test_module_imports_only_pure_contract_layers(self):
        tree = ast.parse(inspect.getsource(manifest_module))
        imports = {node.module.casefold() for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        forbidden = ("streamlit", "app", "memory", "workflow", "planner", "router", "response", "llm")
        self.assertFalse(any(name == token or name.startswith(token + ".") for name in imports for token in forbidden))


if __name__ == "__main__":
    unittest.main()
