import unittest

from brain.business_workflow_engine import decide_business_workflow
from brain.business_entity_extractor import extract_business_entities
from brain.business_intent_engine import detect_business_intent
from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_state_machine import cost_calculation_trace, update_workflow_state


MSG_COST_35_100 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 \u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19 \u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
MSG_COST_40_50 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 40 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 50 \u0e0a\u0e34\u0e49\u0e19"
MSG_SALES_7_DAY = "\u0e0a\u0e48\u0e27\u0e22\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22 7 \u0e27\u0e31\u0e19"


def _workflow_decision(message):
    intent = detect_business_intent(message)
    entities = extract_business_entities(message, intent["detected_intent"])
    return decide_business_workflow(message, intent, entities, {})


class V493WorkflowReadinessCalculationAuditTest(unittest.TestCase):
    def test_unit_cost_and_quantity_compute_total_for_price_question(self):
        state, extracted = update_workflow_state({}, MSG_COST_35_100, detected_workflow="COST_CALCULATION")
        trace = state["calculation_trace"]

        self.assertEqual(state["workflow"], "COST_CALCULATION")
        self.assertEqual(extracted["unit_cost"], 35)
        self.assertEqual(extracted["total_units"], 100)
        self.assertTrue(state["is_ready"])
        self.assertEqual(state["missing_fields"], [])
        self.assertEqual(trace["computed_total_cost"], 3500)
        self.assertEqual(trace["computed_cost_per_unit"], 35)
        self.assertEqual(trace["selected_formula"], "unit_cost_times_quantity")

        route = build_task_route({}, MSG_COST_35_100)
        diagnostics = developer_diagnostics(route)
        self.assertEqual((route["business_workflow"]["workflow_state"] or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertEqual(diagnostics["computed_total_cost"], 3500)
        self.assertEqual(diagnostics["computed_cost_per_unit"], 35)

    def test_cost_calculation_quantity_does_not_request_daily_capacity(self):
        state, extracted = update_workflow_state({}, MSG_COST_40_50, detected_workflow="COST_CALCULATION")
        decision = _workflow_decision(MSG_COST_40_50)

        self.assertEqual(extracted["unit_cost"], 40)
        self.assertEqual(extracted["total_units"], 50)
        self.assertEqual(state["calculation_trace"]["computed_total_cost"], 2000)
        self.assertEqual(state["calculation_trace"]["computed_cost_per_unit"], 40)
        self.assertNotIn("quantity", decision["missing_entities"])
        self.assertNotIn("total_units", decision["missing_entities"])
        self.assertNotIn("daily_capacity", decision["missing_entities"])
        self.assertNotIn("daily_capacity_or_available_quantity", decision["missing_entities"])
        self.assertIsNone(decision["next_question"])

    def test_total_cost_and_quantity_compute_cost_per_unit(self):
        trace = cost_calculation_trace({"total_cost": 3500, "quantity": 100})

        self.assertEqual(trace["selected_formula"], "total_cost_div_quantity")
        self.assertEqual(trace["computed_total_cost"], 3500)
        self.assertEqual(trace["computed_cost_per_unit"], 35)

    def test_sales_planning_still_routes_to_sales_plan(self):
        route = build_task_route({}, MSG_SALES_7_DAY)

        self.assertEqual(route["planner_output"]["workflow"], "SALES_PLAN_7_DAY")


if __name__ == "__main__":
    unittest.main()
