import unittest

from brain.canonical_skill_registry import CanonicalSkillRegistry
from brain.skill_applicability import evaluate_skill_applicability
from brain.skill_evidence_readiness import evaluate_skill_evidence_readiness


class V591SkillEvidenceReadinessTest(unittest.TestCase):
    def setUp(self):
        self.registry = CanonicalSkillRegistry()

    def test_complete_required_evidence_is_ready_with_optional_limitations(self):
        skill = self.registry.get_skill("analyze_operating_capacity")
        result = evaluate_skill_evidence_readiness(
            skill,
            available_metrics={
                "output_quantity": {"value": 100, "timeframe": "day", "completeness_status": "AVAILABLE_COMPLETE"},
                "output_time_period": {"value": "day", "completeness_status": "AVAILABLE_COMPLETE"},
            },
        )
        self.assertEqual(result.status, "READY_WITH_LIMITATIONS")

    def test_missing_required_conflict_and_workflow_owned_precedence(self):
        skill = self.registry.get_skill("evaluate_unit_economics")
        missing = evaluate_skill_evidence_readiness(skill, available_metrics={"selling_price": {"value": 80, "completeness_status": "AVAILABLE_COMPLETE"}})
        conflict = evaluate_skill_evidence_readiness(skill, incomplete_metrics={"selling_price": {"completeness_status": "CONFLICTING"}, "unit_cost": {"completeness_status": "AVAILABLE_COMPLETE"}})
        owned = evaluate_skill_evidence_readiness(skill, workflow_owned_fields=["selling_price"], available_metrics={"selling_price": {"completeness_status": "AVAILABLE_COMPLETE"}, "unit_cost": {"completeness_status": "AVAILABLE_COMPLETE"}})
        self.assertEqual(missing.status, "BLOCKED_BY_REQUIRED_EVIDENCE")
        self.assertEqual(conflict.status, "BLOCKED_BY_CONFLICT")
        self.assertEqual(owned.status, "BLOCKED_BY_WORKFLOW_OWNERSHIP")

    def test_applicability_operators_and_missing_context(self):
        skill = self.registry.get_skill("plan_order_fulfillment")
        self.assertEqual(evaluate_skill_applicability(skill, {"current_turn": {"business_model": "made_to_order"}}).status, "APPLICABLE")
        self.assertEqual(evaluate_skill_applicability(skill, {"current_turn": {}}).status, "APPLICABILITY_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
