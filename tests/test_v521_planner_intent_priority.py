import unittest

from brain.conversation_manager import route_quick_action
from brain.conversation_priority_engine import WORKFLOW_ANSWER, WORKFLOW_SWITCH, classify_message_priority
from brain.task_router import build_task_route
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION


WORKFLOW_PROFIT_CALCULATION = "PROFIT_CALCULATION"


class V521PlannerIntentPriorityTest(unittest.TestCase):
    def assert_routes_to_profit(self, message: str):
        route = build_task_route({}, message)
        workflow = route["business_workflow"]

        self.assertEqual(route["detected_intent"]["detected_intent"], "profit_calculation")
        self.assertEqual(route["intent_resolution"]["resolved_intent"], "profit_calculation")
        self.assertEqual(route["intent_resolution"]["resolved_workflow"], WORKFLOW_PROFIT_CALCULATION)
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_PROFIT_CALCULATION)
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), WORKFLOW_PROFIT_CALCULATION)
        self.assertNotEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertNotIn("quantity", workflow.get("missing_entities") or [])
        return route

    def assert_routes_to_cost_per_unit(self, message: str):
        route = build_task_route({}, message)
        workflow = route["business_workflow"]

        self.assertEqual(route["detected_intent"]["detected_intent"], "cost_calculation")
        self.assertEqual(route["intent_resolution"]["resolved_intent"], "cost_calculation")
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), WORKFLOW_COST_CALCULATION)
        self.assertNotEqual(route["planner_output"]["workflow"], WORKFLOW_PROFIT_CALCULATION)
        return route

    def test_profit_intent_wins_over_cost_per_unit_phrasing(self):
        cases = [
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 100 \u0e1a\u0e32\u0e17 \u0e02\u0e32\u0e22 150 \u0e1a\u0e32\u0e17 \u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 \u0e02\u0e32\u0e22 120 \u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
            "\u0e17\u0e38\u0e19 100 \u0e02\u0e32\u0e22 150",
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 100 \u0e1a\u0e32\u0e17 \u0e02\u0e32\u0e22 150 \u0e1a\u0e32\u0e17",
            "\u0e02\u0e32\u0e22 150 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 100 \u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
        ]

        for message in cases:
            with self.subTest(message=message):
                route = self.assert_routes_to_profit(message)
                self.assertTrue(route["business_workflow"]["workflow_complete"])

    def test_clear_cost_per_unit_intent_is_preserved(self):
        cases = [
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 \u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19",
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23 \u0e16\u0e49\u0e32\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 \u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19",
        ]

        for message in cases:
            with self.subTest(message=message):
                route = self.assert_routes_to_cost_per_unit(message)
                self.assertTrue(route["business_workflow"]["workflow_complete"])

    def test_profit_question_interrupts_active_cost_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        message = "\u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
        priority = classify_message_priority(message, state)
        route = build_task_route(state, message)

        self.assertEqual(priority["classification"], WORKFLOW_SWITCH)
        self.assertEqual(priority["detected_new_intent"], WORKFLOW_PROFIT_CALCULATION)
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_PROFIT_CALCULATION)
        self.assertEqual((route["business_workflow"].get("workflow_state") or {}).get("workflow_id"), WORKFLOW_PROFIT_CALCULATION)

    def test_quantity_answer_continues_active_cost_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        message = "100 \u0e0a\u0e34\u0e49\u0e19"
        priority = classify_message_priority(message, state)
        route = build_task_route(state, message)

        self.assertEqual(priority["classification"], WORKFLOW_ANSWER)
        self.assertTrue(priority["allow_field_extraction"])
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual((route["business_workflow"].get("workflow_state") or {}).get("workflow_id"), WORKFLOW_COST_CALCULATION)


if __name__ == "__main__":
    unittest.main()
