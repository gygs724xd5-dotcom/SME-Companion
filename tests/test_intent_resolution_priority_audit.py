import unittest

from brain.task_router import build_task_route, developer_diagnostics


class IntentResolutionPriorityAuditTest(unittest.TestCase):
    def test_cost_calculation_with_price_phrase_does_not_become_sales_plan(self):
        message = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 \u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19 \u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"

        route = build_task_route({}, message)
        diagnostics = developer_diagnostics(route)
        audit = diagnostics["intent_priority_audit"]

        self.assertEqual(route["business_context"]["current_message_intent"], "cost_calculation")
        self.assertEqual(route["business_workflow"]["workflow_state"]["workflow_id"], "COST_CALCULATION")
        self.assertEqual(route["intent_resolution"]["resolved_intent"], "cost_calculation")
        self.assertEqual(route["intent_resolution"]["resolved_workflow"], "COST_CALCULATION")
        self.assertEqual(route["planner_output"]["task_type"], "Cost Calculation")
        self.assertEqual(route["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertNotEqual(route["planner_output"]["task_type"], "Sales Plan")

        matched_skill = route["business_intelligence"].get("matched_skill") or {}
        self.assertNotEqual(matched_skill.get("skill_id"), "01.001.customer_asks_price")
        self.assertEqual(
            (route["business_intelligence"].get("suppressed_top_skill") or {}).get("skill_id"),
            "01.001.customer_asks_price",
        )

        self.assertEqual(audit["current_message_text"], message)
        self.assertEqual(audit["detected_intent"], "cost_calculation")
        self.assertEqual(audit["current_message_intent"], "cost_calculation")
        self.assertEqual(audit["intent_resolution"]["resolved_intent"], "cost_calculation")
        self.assertEqual(audit["intent_resolution"]["resolved_workflow"], "COST_CALCULATION")
        self.assertEqual(audit["planner_output"]["task_type"], "Cost Calculation")
        self.assertEqual(audit["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertEqual(audit["business_workflow"]["workflow_state"]["workflow_id"], "COST_CALCULATION")
        self.assertNotEqual(audit["matched_skill"]["skill_id"], "01.001.customer_asks_price")
        self.assertFalse(audit["intent_changed_between_layers"])

    def test_cost_calculation_unit_cost_phrase_completes_cost_mapping(self):
        message = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 \u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19 \u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"

        route = build_task_route({}, message)
        workflow = route["business_workflow"]
        entities = workflow["extracted_entities"]
        diagnostics = developer_diagnostics(route)

        self.assertEqual(workflow["workflow_state"]["workflow_id"], "COST_CALCULATION")
        self.assertEqual(entities["cost"], 35)
        self.assertEqual(entities["unit_cost"], 35)
        self.assertEqual(entities["quantity"], 100)
        self.assertEqual(entities["total_units"], 100)
        self.assertNotIn("cost", workflow["missing_entities"])
        self.assertNotIn("cost", diagnostics["missing_entities"])
        self.assertNotEqual(workflow["next_question"], "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17\u0e04\u0e23\u0e31\u0e1a")
        self.assertTrue(diagnostics["entity_mapping_trace"])
        self.assertEqual(
            diagnostics["workflow_readiness_decision"]["reason_by_field"]["cost"]["matched_aliases"][0],
            "cost",
        )


if __name__ == "__main__":
    unittest.main()
