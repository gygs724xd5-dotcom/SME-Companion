import ast
import dataclasses
import inspect
import unittest

import brain.business_skill_lifecycle_manifest as manifest_module
from brain.business_skill import CONTRACTED, SHADOW_AVAILABLE, UNIT_TESTED
from brain.business_skill_lifecycle_manifest import (
    APPROVED_LIFECYCLE_PROMOTIONS,
    APPROVED_PROMOTION_SKILL_IDS,
    BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION,
    UNIT_TEST_QUALIFICATION,
    BusinessSkillLifecyclePromotion,
    apply_approved_lifecycle_promotion,
    apply_approved_lifecycle_promotions,
    build_lifecycle_promotion_diagnostics,
    get_lifecycle_promotion,
    validate_lifecycle_promotion,
    validate_lifecycle_promotion_manifest,
)
from brain.business_skill_registry import get_business_skill_registry, validate_business_skill_registry
from brain.business_skill_shadow_selector import LIFECYCLE_INELIGIBLE, select_shadow_business_skill


class V5157BusinessSkillLifecyclePromotionTests(unittest.TestCase):
    def setUp(self):
        self.current = get_business_skill_registry()
        self.baseline = tuple(dataclasses.replace(
            skill,
            active_status=CONTRACTED,
            tests_required=tuple(test for test in skill.tests_required if "test_v5156_" not in test and "test_v5157_" not in test),
        ) for skill in self.current)

    def promotion(self, **changes):
        return dataclasses.replace(APPROVED_LIFECYCLE_PROMOTIONS[0], **changes)

    def test_manifest_is_exact_immutable_and_lookup_is_exact(self):
        self.assertEqual(BUSINESS_SKILL_LIFECYCLE_MANIFEST_VERSION, "5.15.7")
        self.assertEqual(tuple(item.skill_id for item in APPROVED_LIFECYCLE_PROMOTIONS), APPROVED_PROMOTION_SKILL_IDS)
        self.assertEqual(len(APPROVED_LIFECYCLE_PROMOTIONS), 2)
        for item in APPROVED_LIFECYCLE_PROMOTIONS:
            self.assertEqual((item.from_status, item.to_status), (CONTRACTED, UNIT_TESTED))
            self.assertEqual(item.qualification_version, "5.15.6")
            self.assertEqual(item.qualification_type, UNIT_TEST_QUALIFICATION)
            self.assertIn("tests/test_v5156_business_skill_lifecycle_qualification.py", item.qualification_test_files)
            with self.assertRaises(dataclasses.FrozenInstanceError):
                item.to_status = SHADOW_AVAILABLE
        self.assertIsNotNone(get_lifecycle_promotion(APPROVED_PROMOTION_SKILL_IDS[0]))
        self.assertIsNone(get_lifecycle_promotion(" " + APPROVED_PROMOTION_SKILL_IDS[0]))
        self.assertIsNone(get_lifecycle_promotion("unknown.v1"))

    def test_manifest_validation_rejects_duplicates_and_unknown_ids(self):
        duplicate = (APPROVED_LIFECYCLE_PROMOTIONS[0], APPROVED_LIFECYCLE_PROMOTIONS[0])
        self.assertFalse(validate_lifecycle_promotion_manifest(duplicate)["valid"])
        unknown = (self.promotion(skill_id="cost.unknown.v1"),)
        self.assertFalse(validate_lifecycle_promotion_manifest(unknown)["valid"])
        with self.assertRaises(ValueError):
            apply_approved_lifecycle_promotions(self.baseline, unknown)

    def test_transition_policy_rejects_invalid_transitions(self):
        cases = (
            {"from_status": "UNKNOWN"},
            {"to_status": "UNKNOWN"},
            {"to_status": CONTRACTED},
            {"from_status": UNIT_TESTED, "to_status": CONTRACTED},
            {"from_status": CONTRACTED, "to_status": SHADOW_AVAILABLE},
            {"from_status": UNIT_TESTED, "to_status": SHADOW_AVAILABLE},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertFalse(validate_lifecycle_promotion(self.promotion(**changes))["valid"])
        wrong = dataclasses.replace(self.baseline[0], active_status=UNIT_TESTED)
        with self.assertRaises(ValueError):
            apply_approved_lifecycle_promotion(wrong)

    def test_apply_is_copy_based_and_changes_only_status_and_tests(self):
        original = self.baseline[0]
        promoted = apply_approved_lifecycle_promotion(original)
        self.assertIsNot(promoted, original)
        self.assertEqual(original.active_status, CONTRACTED)
        changed = [field.name for field in dataclasses.fields(original) if getattr(original, field.name) != getattr(promoted, field.name)]
        self.assertEqual(changed, ["tests_required", "active_status"])
        self.assertTrue(set(original.tests_required).issubset(promoted.tests_required))
        self.assertEqual(promoted.tests_required.count("tests/test_v5156_business_skill_lifecycle_qualification.py"), 1)
        self.assertEqual(promoted.tests_required.count("tests/test_v5157_business_skill_lifecycle_promotion.py"), 1)
        with self.assertRaises(ValueError):
            apply_approved_lifecycle_promotion(promoted)

    def test_registry_has_exact_mixed_statuses_and_validates(self):
        self.assertEqual(len(self.current), 10)
        unit_tested = [skill.skill_id for skill in self.current if skill.active_status == UNIT_TESTED]
        self.assertEqual(tuple(unit_tested), APPROVED_PROMOTION_SKILL_IDS)
        self.assertEqual(sum(skill.active_status == CONTRACTED for skill in self.current), 8)
        self.assertFalse(any(skill.active_status == SHADOW_AVAILABLE for skill in self.current))
        self.assertTrue(validate_business_skill_registry()["valid"])

    def test_unit_tested_cost_skills_remain_shadow_ineligible(self):
        for skill in self.current[:2]:
            candidate = {"skill_id": skill.skill_id, "candidate_confidence": 1.0, "candidate_valid": True,
                         "candidate_shadow_only": True, "candidate_selected": False, "candidate_authorized": False}
            evidence = {"skill_id": skill.skill_id, "evidence_ready": True, "evidence_valid": True,
                        "evidence_shadow_only": True, "evidence_selected": False, "evidence_authorized": False,
                        "evidence_executed": False, "evidence_confidence": 1.0}
            result = select_shadow_business_skill([candidate], [evidence], self.current)
            self.assertEqual(result["selection_status"], LIFECYCLE_INELIGIBLE)
            self.assertIsNone(result["shadow_selected_skill_id"])

    def test_diagnostics_report_two_copy_mutations_and_safe_boundaries(self):
        diagnostics = build_lifecycle_promotion_diagnostics(self.baseline)
        self.assertEqual(diagnostics["lifecycle_mutation_count"], 2)
        self.assertEqual(diagnostics["status_counts_before"], {CONTRACTED: 10})
        self.assertEqual(diagnostics["status_counts_after"], {UNIT_TESTED: 2, CONTRACTED: 8})
        self.assertEqual(diagnostics["shadow_available_ids"], [])
        for key in ("shadow_available", "shadow_selected", "authorized", "executed", "reasoning_executed", "response_generated"):
            self.assertFalse(diagnostics[key])
        self.assertNotIn("BusinessSkill(", repr(diagnostics))

    def test_module_imports_only_pure_contract_layers(self):
        tree = ast.parse(inspect.getsource(manifest_module))
        imports = {alias.name.casefold() for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports.update(node.module.casefold() for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
        forbidden = ("streamlit", "app", "memory", "workflow", "planner", "router", "response", "llm", "subprocess", "pathlib", "os", "brain.business_skill_matcher")
        self.assertFalse(any(name == token or name.startswith(token + ".") for name in imports for token in forbidden))


if __name__ == "__main__":
    unittest.main()
