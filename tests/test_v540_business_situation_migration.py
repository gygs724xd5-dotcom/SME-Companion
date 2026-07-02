import unittest

from brain.business_situation import BUSINESS_SITUATION_SOURCE, BUSINESS_SITUATION_VERSION
from brain.planner_engine import build_execution_plan
from brain.task_router import build_task_route, developer_diagnostics


class BusinessSituationMigrationTest(unittest.TestCase):
    def test_task_route_exposes_business_situation_without_changing_stable_planner_fields(self):
        baseline = build_task_route({}, "price?")
        route = build_task_route({}, "price?")

        situation = route.get("business_situation") or {}
        planner_situation = (route.get("planner_output") or {}).get("business_situation") or {}

        self.assertEqual(baseline["planner_output"]["task_type"], route["planner_output"]["task_type"])
        self.assertEqual(baseline["planner_output"]["workflow"], route["planner_output"]["workflow"])
        self.assertTrue(situation)
        self.assertEqual(situation, planner_situation)
        self.assertEqual(situation["version"], BUSINESS_SITUATION_VERSION)
        self.assertEqual(situation["diagnostics"]["business_situation_source"], BUSINESS_SITUATION_SOURCE)
        self.assertEqual(situation["diagnostics"]["runtime_mode"], "compatibility_context_only")

    def test_business_situation_uses_business_language_not_procedural_state(self):
        route = build_task_route({}, "customer says price is expensive")
        situation = route.get("business_situation") or {}

        self.assertIn("objective", situation)
        self.assertIn("business_context", situation)
        self.assertIn("known_evidence", situation)
        self.assertIn("material_uncertainty", situation)
        self.assertIn("conversation_purpose", situation)
        self.assertIn("potential_business_risks", situation)

        forbidden_keys = {"workflow", "workflow_state", "step", "steps", "transition", "transitions", "missing_fields"}
        self.assertFalse(forbidden_keys.intersection(situation.keys()))

    def test_planner_builds_business_situation_as_compatible_context(self):
        plan = build_execution_plan({}, "create a promotion for my bakery")
        situation = plan.get("business_situation") or {}

        self.assertTrue(situation)
        self.assertEqual(situation["diagnostics"]["routes_changed"], False)
        self.assertEqual(situation["diagnostics"]["responses_changed"], False)
        self.assertEqual(situation["diagnostics"]["commit_boundary_changed"], False)

    def test_developer_diagnostics_include_business_situation_group(self):
        route = build_task_route({}, "calculate profit")
        diagnostics = developer_diagnostics(route)

        self.assertTrue(diagnostics["business_situation_created"])
        self.assertIn("Business Situation", diagnostics["diagnostic_groups"])
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Business Situation"]["business_situation_version"],
            BUSINESS_SITUATION_VERSION,
        )


if __name__ == "__main__":
    unittest.main()
