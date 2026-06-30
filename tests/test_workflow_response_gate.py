import unittest

from brain.task_router import build_task_route, workflow_response_gate


class WorkflowResponseGateTest(unittest.TestCase):
    def test_sme_companion_question_never_allows_workflow_response(self):
        route = build_task_route({}, "SME Companion \u0e04\u0e37\u0e2d\u0e2d\u0e30\u0e44\u0e23")
        gate = workflow_response_gate(route)

        self.assertFalse(gate["workflow_response_allowed"])
        self.assertNotEqual(gate["final_response_gate"], "workflow_missing_entities")
        self.assertNotEqual(route.get("last_response_source"), "workflow_response")

    def test_customer_says_expensive_never_allows_workflow_response(self):
        route = build_task_route({}, "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32\u0e41\u0e1e\u0e07")
        gate = workflow_response_gate(route)

        self.assertFalse(gate["workflow_response_allowed"])
        self.assertIn(
            gate["workflow_response_blocked_reason"],
            {"intent_customer_reply", "workflow_action_interrupt"},
        )

    def test_complete_profit_entities_never_ask_for_quantity_again(self):
        route = build_task_route(
            {},
            "profit product choux cream price 50 cost 20 quantity 10 units",
        )
        workflow = route["business_workflow"]
        gate = workflow_response_gate(route)

        self.assertTrue(workflow["workflow_complete"])
        self.assertEqual(workflow["missing_entities"], [])
        self.assertFalse(gate["workflow_response_allowed"])
        self.assertEqual(gate["workflow_response_blocked_reason"], "workflow_action_complete")
        self.assertNotEqual(workflow.get("next_question"), "\u0e02\u0e32\u0e22\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19\u0e04\u0e23\u0e31\u0e1a")

    def test_workflow_response_only_allowed_for_collection_actions_with_missing_entities(self):
        allowed_route = build_task_route({}, "profit product choux cream price 50")
        allowed_gate = workflow_response_gate(allowed_route)

        self.assertIn(allowed_route["business_workflow"]["workflow_action"], {"continue", "start_new"})
        self.assertTrue(allowed_route["business_workflow"]["missing_entities"])
        self.assertTrue(allowed_gate["workflow_response_allowed"])

        blocked_gate = workflow_response_gate(
            {
                "business_workflow": {
                    "workflow_action": "resume",
                    "detected_intent": "profit_calculation",
                    "missing_entities": ["cost"],
                    "entity_completeness": {"completed": 1, "required": 2, "percent": 0.5},
                }
            }
        )

        self.assertFalse(blocked_gate["workflow_response_allowed"])
        self.assertEqual(blocked_gate["workflow_response_blocked_reason"], "workflow_action_resume")


if __name__ == "__main__":
    unittest.main()
