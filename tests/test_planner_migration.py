import unittest

from brain.canonical_objects import PlannerContext
from brain.planner_migration import (
    PLANNER_MIGRATION_SOURCE,
    PLANNER_MIGRATION_VERSION,
    normalize_planner_inputs,
)
from brain.task_router import build_task_route, developer_diagnostics


STABLE_PLANNER_FIELDS = [
    "goal",
    "task_type",
    "workflow",
    "required_skills",
    "required_information",
    "known_information",
    "missing_information",
    "can_execute",
    "next_step",
    "priority",
    "estimated_response_mode",
]


def _stable_planner_output(route):
    planner_output = route.get("planner_output") or {}
    return {field: planner_output.get(field) for field in STABLE_PLANNER_FIELDS}


class PlannerMigrationTest(unittest.TestCase):
    def test_planner_prefers_v5_context_when_available(self):
        state = {
            "planner_context": PlannerContext(
                selected_domain="Operations",
                selected_skill="cost_calculation",
                business_goal="calculate unit cost",
                decision_type="Cost Calculation",
                confidence=0.91,
            ).to_dict()
        }

        route = build_task_route(state, "help")
        diagnostics = developer_diagnostics(route)

        self.assertEqual(route["planner_output"]["task_type"], "Cost Calculation")
        self.assertTrue(diagnostics["planner_used_v5_context"])
        self.assertFalse(diagnostics["planner_used_legacy_fallback"])
        self.assertEqual(diagnostics["planner_runtime_source"], PLANNER_MIGRATION_SOURCE)
        self.assertEqual(diagnostics["planner_runtime_version"], PLANNER_MIGRATION_VERSION)
        self.assertEqual(diagnostics["planner_selected_domain"], "Operations")
        self.assertEqual(diagnostics["planner_selected_skill"], "cost_calculation")
        self.assertEqual(diagnostics["planner_business_goal"], "calculate unit cost")
        self.assertEqual(diagnostics["planner_decision_type"], "Cost Calculation")
        self.assertEqual(diagnostics["planner_confidence"], 0.91)
        self.assertIn("Planner Migration", diagnostics["diagnostic_groups"])

    def test_planner_falls_back_to_v4_when_v5_context_is_incomplete(self):
        baseline = build_task_route({}, "help")
        state = {
            "planner_context": PlannerContext(
                selected_domain="Unmapped Domain",
                selected_skill="unmapped.skill",
                business_goal="not enough routing context",
                decision_type="unknown",
                confidence=0.4,
            ).to_dict()
        }

        route = build_task_route(state, "help")
        diagnostics = developer_diagnostics(route)

        self.assertEqual(_stable_planner_output(route), _stable_planner_output(baseline))
        self.assertFalse(diagnostics["planner_used_v5_context"])
        self.assertTrue(diagnostics["planner_used_legacy_fallback"])
        self.assertEqual(diagnostics["planner_reason"], "v5_context_incomplete_or_unmapped_using_v4_fallback")

    def test_normalization_uses_knowledge_reasoning_planner_priority(self):
        normalized = normalize_planner_inputs(
            knowledge_context={
                "selected_domain": "Knowledge Domain",
                "selected_skill": "knowledge_cost_skill",
                "response_guidance": {"decision_type": "Cost Calculation"},
                "confidence": 0.7,
            },
            reasoning_context={
                "selected_domain": "Reasoning Domain",
                "selected_skill": "reasoning_skill",
                "business_goal": "reasoning goal",
                "decision_type": "Content Plan",
                "confidence": 0.8,
            },
            planner_context={
                "selected_domain": "Planner Domain",
                "selected_skill": "planner_skill",
                "business_goal": "planner goal",
                "decision_type": "Sales Plan",
                "confidence": 0.6,
            },
        )

        self.assertEqual(normalized["selected_domain"], "Knowledge Domain")
        self.assertEqual(normalized["selected_skill"], "knowledge_cost_skill")
        self.assertEqual(normalized["business_goal"], "reasoning goal")
        self.assertEqual(normalized["decision_type"], "Cost Calculation")
        self.assertEqual(normalized["confidence"], 0.8)
        self.assertTrue(normalized["used_v5_context"])

    def test_legacy_routing_output_remains_identical_without_v5_context(self):
        first = build_task_route({}, "price?")
        second = build_task_route({}, "price?")

        self.assertEqual(_stable_planner_output(first), _stable_planner_output(second))
        self.assertEqual(first["task_type"], second["task_type"])


if __name__ == "__main__":
    unittest.main()
