import copy
import unittest

import brain.business_skill as business_skill_module
from brain.business_skill import (
    BUSINESS_SKILL_DIAGNOSTIC_KEYS,
    CONTRACTED,
    LIMITED_ACTIVE,
    STABLE,
    BusinessSkill,
    RequiredEvidence,
    build_business_skill_diagnostics,
    create_cost_change_analysis_skill,
    determine_skill_evidence_readiness,
    normalize_business_skill,
    validate_business_skill,
    validate_required_evidence,
)


class V5151BusinessSkillTest(unittest.TestCase):
    def test_required_evidence_default_normalization(self):
        evidence = RequiredEvidence(field_name="unit_cost", field_type="number")

        normalized = validate_required_evidence(evidence)["normalized"]

        self.assertEqual(normalized["field_name"], "unit_cost")
        self.assertEqual(normalized["field_type"], "number")
        self.assertTrue(normalized["required"])
        self.assertEqual(normalized["source"], "current_turn_or_business_memory")
        self.assertEqual(normalized["freshness"], "current_or_recent")
        self.assertEqual(normalized["confidence_required"], 0.7)
        self.assertEqual(normalized["example_values"], [])
        self.assertFalse(normalized["can_assume"])

    def test_required_evidence_validation_catches_empty_field_name(self):
        result = validate_required_evidence(RequiredEvidence(field_name="", field_type="number"))

        self.assertFalse(result["valid"])
        self.assertIn("field_name is required", result["errors"])

    def test_required_evidence_confidence_range_validation(self):
        high = validate_required_evidence(
            RequiredEvidence(field_name="unit_cost", field_type="number", confidence_required=1.5)
        )
        low = validate_required_evidence(
            RequiredEvidence(field_name="unit_cost", field_type="number", confidence_required=-0.1)
        )

        self.assertFalse(high["valid"])
        self.assertFalse(low["valid"])
        self.assertIn("confidence_required must be between 0 and 1", high["errors"])
        self.assertIn("confidence_required must be between 0 and 1", low["errors"])

    def test_required_evidence_warns_without_missing_question(self):
        result = validate_required_evidence(RequiredEvidence(field_name="unit_cost", field_type="number"))

        self.assertTrue(result["valid"])
        self.assertIn("required evidence should define missing_question", result["warnings"])

    def test_required_evidence_warns_for_assumable_without_confirmation(self):
        result = validate_required_evidence(
            RequiredEvidence(field_name="customer_segment", field_type="text", can_assume=True)
        )

        self.assertTrue(result["valid"])
        self.assertIn("assumable evidence without user confirmation should be reviewed", result["warnings"])

    def test_business_skill_default_active_status_is_contracted(self):
        skill = BusinessSkill(
            skill_id="cost.test.v1",
            skill_version="1.0.0",
            skill_name="Cost Test",
            business_domain="COST",
        )

        self.assertEqual(skill.active_status, CONTRACTED)
        self.assertEqual(normalize_business_skill(skill)["active_status"], CONTRACTED)

    def test_business_skill_validation_accepts_seed_cost_change_analysis_skill(self):
        result = validate_business_skill(create_cost_change_analysis_skill())

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["normalized"]["skill_id"], "cost.change_analysis.v1")

    def test_business_skill_validation_rejects_unknown_business_domain(self):
        skill = create_cost_change_analysis_skill()
        payload = normalize_business_skill(skill)
        payload["business_domain"] = "UNKNOWN"

        result = validate_business_skill(payload)

        self.assertFalse(result["valid"])
        self.assertIn("business_domain must be canonical", result["errors"])

    def test_business_skill_validation_rejects_unknown_skill_category(self):
        payload = normalize_business_skill(create_cost_change_analysis_skill())
        payload["skill_category"] = "UNKNOWN"

        result = validate_business_skill(payload)

        self.assertFalse(result["valid"])
        self.assertIn("skill_category must be canonical", result["errors"])

    def test_business_skill_validation_rejects_unknown_lifecycle_status(self):
        payload = normalize_business_skill(create_cost_change_analysis_skill())
        payload["active_status"] = "ACTIVE"

        result = validate_business_skill(payload)

        self.assertFalse(result["valid"])
        self.assertIn("active_status must be canonical", result["errors"])

    def test_normalize_business_skill_does_not_mutate_input(self):
        payload = normalize_business_skill(create_cost_change_analysis_skill())
        original = copy.deepcopy(payload)

        normalized = normalize_business_skill(payload)
        normalized["required_evidence"][0]["field_name"] = "mutated"

        self.assertEqual(payload, original)

    def test_determine_skill_evidence_readiness_ready_when_required_evidence_present(self):
        readiness = determine_skill_evidence_readiness(
            create_cost_change_analysis_skill(),
            {"previous_cost": 30, "current_cost": 40},
        )

        self.assertTrue(readiness["reasoning_ready"])
        self.assertEqual(readiness["missing_evidence"], [])
        self.assertEqual(readiness["present_evidence"], ["previous_cost", "current_cost"])
        self.assertEqual(readiness["blocked_reason"], "")
        self.assertEqual(readiness["confidence_floor"], 0.8)

    def test_determine_skill_evidence_readiness_blocks_when_required_evidence_missing(self):
        readiness = determine_skill_evidence_readiness(
            create_cost_change_analysis_skill(),
            {"previous_cost": 30},
        )

        self.assertFalse(readiness["reasoning_ready"])
        self.assertEqual(readiness["missing_evidence"], ["current_cost"])
        self.assertEqual(readiness["blocked_reason"], "missing_required_evidence")

    def test_determine_skill_evidence_readiness_treats_can_assume_missing_evidence_separately(self):
        skill = BusinessSkill(
            skill_id="customer.assumption.v1",
            skill_version="1.0.0",
            skill_name="Customer Assumption",
            business_domain="CUSTOMER",
            intent_patterns=("customer",),
            required_evidence=(
                RequiredEvidence(
                    field_name="customer_segment",
                    field_type="text",
                    can_assume=True,
                    missing_question="Which customer segment?",
                ),
            ),
        )

        readiness = determine_skill_evidence_readiness(skill, {})

        self.assertTrue(readiness["reasoning_ready"])
        self.assertEqual(readiness["missing_evidence"], [])
        self.assertEqual(readiness["present_evidence"], [])
        self.assertEqual(readiness["assumable_evidence"], ["customer_segment"])

    def test_diagnostics_returns_stable_v515_contract_keys(self):
        diagnostics = build_business_skill_diagnostics(
            create_cost_change_analysis_skill(),
            {"previous_cost": 30, "current_cost": 40},
        )

        self.assertEqual(tuple(diagnostics.keys()), BUSINESS_SKILL_DIAGNOSTIC_KEYS)

    def test_diagnostics_confidence_is_one_when_valid_and_ready(self):
        diagnostics = build_business_skill_diagnostics(
            create_cost_change_analysis_skill(),
            {"previous_cost": 30, "current_cost": 40},
        )

        self.assertEqual(diagnostics["business_skill_confidence"], 1.0)
        self.assertTrue(diagnostics["business_skill_reasoning_ready"])

    def test_diagnostics_confidence_is_point_six_when_valid_but_missing_evidence(self):
        diagnostics = build_business_skill_diagnostics(create_cost_change_analysis_skill(), {"previous_cost": 30})

        self.assertEqual(diagnostics["business_skill_confidence"], 0.6)
        self.assertFalse(diagnostics["business_skill_reasoning_ready"])

    def test_diagnostics_follow_up_question_uses_first_missing_evidence_missing_question(self):
        diagnostics = build_business_skill_diagnostics(create_cost_change_analysis_skill(), {})

        self.assertEqual(diagnostics["business_skill_follow_up_question"], "What was the previous cost?")

    def test_diagnostics_shadow_mode_defaults_true(self):
        diagnostics = build_business_skill_diagnostics(create_cost_change_analysis_skill())

        self.assertTrue(diagnostics["business_skill_shadow_mode"])

    def test_seed_skill_does_not_have_limited_active_or_stable_status(self):
        skill = create_cost_change_analysis_skill()

        self.assertNotIn(skill.active_status, {LIMITED_ACTIVE, STABLE})
        self.assertEqual(skill.active_status, CONTRACTED)

    def test_module_imports_do_not_require_streamlit_or_app_runtime(self):
        self.assertIs(business_skill_module.BusinessSkill, BusinessSkill)
        self.assertNotIn("streamlit", business_skill_module.__dict__)
        self.assertNotIn("app", business_skill_module.__dict__)


if __name__ == "__main__":
    unittest.main()
