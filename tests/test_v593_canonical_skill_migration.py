import unittest

from brain.canonical_skill_migration import decide_legacy_skill_migration, migration_coverage
from brain.skill_migration_assessment import assess_legacy_skill, map_legacy_intent, map_legacy_metric
from brain.skill_migration_registry import load_skill_migration_registry
from brain.task_router import build_task_route


class V593CanonicalSkillMigrationTest(unittest.TestCase):
    def test_phase_1_assessment_and_rollout_modes(self):
        registry = load_skill_migration_registry()
        modes = registry["rollout_modes"]
        self.assertEqual(modes["cost_calculation"], "CANONICAL_PREFERRED")
        self.assertEqual(modes["sales_planning"], "SHADOW_CANONICAL")
        self.assertEqual(modes["dashboard_builder"], "SHADOW_CANONICAL")
        self.assertTrue(registry["legacy_deprecation_blocked"])

    def test_metric_and_intent_mapping_are_explicit(self):
        self.assertEqual(map_legacy_metric("price")["canonical_id"], "selling_price")
        self.assertEqual(map_legacy_metric("profit")["status"], "MAPPING_REQUIRES_REVIEW")
        self.assertEqual(map_legacy_metric("unknown")["status"], "UNKNOWN_METRIC")
        self.assertIn("analyze_sales_decline", map_legacy_intent("plan_sales"))

    def test_multi_authority_skill_splits_and_deprecation_blocked(self):
        assessment = assess_legacy_skill("skills/sales_planning.md")
        decision = decide_legacy_skill_migration("skills/sales_planning.md")
        coverage = migration_coverage("skills/sales_planning.md")
        self.assertEqual(assessment["authority_purity"], "MULTI_AUTHORITY")
        self.assertEqual(decision["strategy"], "SPLIT")
        self.assertFalse(coverage["replacement_complete"])

    def test_developer_feedback_deferred(self):
        decision = decide_legacy_skill_migration("skills/developer_feedback.md")
        self.assertEqual(decision["rollout_mode"], "LEGACY_UNCHANGED")

    def test_profit_workflow_still_owns_calculation(self):
        route = build_task_route({}, "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท")
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(route["business_workflow"]["extracted_entities"]["price"] - route["business_workflow"]["extracted_entities"]["cost"], 45)
        self.assertTrue(bridge["workflow_coordination"]["workflow_admitted"])
        self.assertFalse(bridge["constitutional_invariants"]["workflow_started_by_bridge"])

    def test_sales_and_dashboard_targets_are_non_executing(self):
        sales = build_task_route({}, "sales decline this month")
        sales_bridge = sales["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        self.assertIn(sales_bridge["primary_skill_candidate"]["skill_id"], {"analyze_sales_decline", "evaluate_sales_funnel"})
        self.assertFalse(sales_bridge["constitutional_invariants"]["planner_invoked"])
        dashboard = build_task_route({}, "dashboard metrics")
        dash_bridge = dashboard["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        self.assertEqual(dash_bridge["primary_skill_candidate"]["skill_id"], "identify_dashboard_metrics")
        self.assertFalse(dash_bridge["constitutional_invariants"]["tool_called_by_bridge"])


if __name__ == "__main__":
    unittest.main()
