import unittest

from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION


WORKFLOW_PROFIT_CALCULATION = "PROFIT_CALCULATION"


class V532PlannerEntityAdapterTest(unittest.TestCase):
    def _diagnostics_for(self, message: str) -> tuple[dict, dict]:
        route = build_task_route({}, message)
        return route, developer_diagnostics(route)

    def test_profit_planner_diagnostics_include_canonical_entities(self):
        route, diagnostics = self._diagnostics_for(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 "
            "\u0e02\u0e32\u0e22 120 "
            "\u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
        )

        self.assertEqual(route["detected_intent"]["detected_intent"], "profit_calculation")
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_PROFIT_CALCULATION)

        canonical_entities = diagnostics["canonical_entities"]
        self.assertEqual(canonical_entities["slots"]["cost"], 85)
        self.assertEqual(canonical_entities["slots"]["selling_price"], 120)
        self.assertEqual(
            diagnostics["planner_context"]["planner_inputs"]["canonical_entities"],
            canonical_entities,
        )
        self.assertEqual(
            diagnostics["planner_context"]["planner_hints"]["canonical_entity_slots"]["cost"],
            85,
        )
        self.assertTrue(
            diagnostics["planner_context"]["diagnostics"]["canonical_entities_present"]
        )
        self.assertIn(
            "canonical_entities",
            diagnostics["diagnostic_groups"]["Planner Context"],
        )

    def test_cost_planner_diagnostics_include_canonical_entities(self):
        route, diagnostics = self._diagnostics_for(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 "
            "\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
        )

        self.assertEqual(route["detected_intent"]["detected_intent"], "cost_calculation")
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)

        canonical_entities = diagnostics["canonical_entities"]
        self.assertEqual(canonical_entities["slots"]["cost"], 200)
        self.assertEqual(canonical_entities["slots"]["quantity"], 100)
        self.assertEqual(
            diagnostics["planner_context"]["planner_inputs"]["canonical_entities"],
            canonical_entities,
        )


if __name__ == "__main__":
    unittest.main()
