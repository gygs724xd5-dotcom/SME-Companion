import unittest

from brain.conversation_manager import start_workflow
from brain.general_response_router import (
    build_general_direct_response,
    select_general_response_route,
)
from brain.task_router import build_task_route, workflow_response_gate
from brain.workflow_authorization_gate import update_workflow_state_if_authorized
from brain.workflow_reply_builder import build_workflow_reply
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION


class V5310GeneralResponseRouterTest(unittest.TestCase):
    def test_workflow_request_bypasses_general_router_for_workflow_runtime(self):
        message = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e49\u0e32\u0e19\u0e01\u0e32\u0e41\u0e1f"
        route = build_task_route({}, message)
        gate = workflow_response_gate(route)
        selected = select_general_response_route(route, "OTHER")

        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual((route["business_workflow"].get("workflow_state") or {}).get("workflow_id"), WORKFLOW_COST_CALCULATION)
        self.assertTrue(gate["workflow_response_allowed"])
        self.assertFalse(selected["handled"])
        self.assertEqual(selected["reason"], "planner_authorized_workflow")

    def test_planner_authorized_cost_workflow_start_returns_missing_field_prompt(self):
        message = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e49\u0e32\u0e19\u0e01\u0e32\u0e41\u0e1f"
        route = build_task_route({}, message)
        workflow = route["planner_output"]["workflow"]

        workflow_state, extracted, authorization = update_workflow_state_if_authorized(
            {},
            message,
            authorized_workflow=workflow,
            detected_workflow=workflow,
        )
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(workflow, WORKFLOW_COST_CALCULATION)
        self.assertTrue(authorization["workflow_mutation_authorized"])
        self.assertEqual(workflow_state["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual(workflow_state["step"], "collecting_cost_inputs")
        self.assertIn("ingredients_costs", workflow_state["missing_fields"])
        self.assertEqual(reply["response_mode"], "ASK_NEXT_FIELD")
        self.assertIn("\u0e02\u0e2d\u0e23\u0e32\u0e04\u0e32\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a", reply["reply"])
        self.assertEqual(extracted, {})

    def test_general_question_selects_executable_general_route(self):
        route = build_task_route({}, "\u0e1b\u0e23\u0e30\u0e40\u0e17\u0e28\u0e44\u0e17\u0e22\u0e21\u0e35\u0e01\u0e35\u0e48\u0e08\u0e31\u0e07\u0e2b\u0e27\u0e31\u0e14")
        selected = select_general_response_route(route, "OTHER")

        self.assertTrue(selected["handled"])
        self.assertEqual(selected["response_route"], "general_response")
        self.assertFalse(workflow_response_gate(route)["workflow_response_allowed"])
        self.assertEqual(
            build_general_direct_response("\u0e1b\u0e23\u0e30\u0e40\u0e17\u0e28\u0e44\u0e17\u0e22\u0e21\u0e35\u0e01\u0e35\u0e48\u0e08\u0e31\u0e07\u0e2b\u0e27\u0e31\u0e14"),
            "\u0e1b\u0e23\u0e30\u0e40\u0e17\u0e28\u0e44\u0e17\u0e22\u0e21\u0e35 77 \u0e08\u0e31\u0e07\u0e2b\u0e27\u0e31\u0e14\u0e04\u0e23\u0e31\u0e1a",
        )

    def test_general_story_request_gets_direct_general_response(self):
        message = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e25\u0e48\u0e32\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e41\u0e21\u0e27 2 \u0e1b\u0e23\u0e30\u0e42\u0e22\u0e04"
        route = build_task_route({}, message)
        selected = select_general_response_route(route, "GENERAL_CHAT")
        reply = build_general_direct_response(message)

        self.assertTrue(selected["handled"])
        self.assertIsNotNone(reply)
        self.assertIn("\u0e41\u0e21\u0e27\u0e15\u0e31\u0e27\u0e2b\u0e19\u0e36\u0e48\u0e07", reply)
        self.assertIn("\u0e17\u0e38\u0e01\u0e04\u0e23\u0e31\u0e49\u0e07", reply)
        self.assertNotIn("\u0e04\u0e37\u0e19\u0e2b\u0e19\u0e36\u0e48\u0e07", reply)

    def test_active_workflow_unrelated_question_bypasses_workflow_to_general_route(self):
        state = {}
        start_workflow(state, WORKFLOW_COST_CALCULATION, initial_message="\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e49\u0e32\u0e19\u0e01\u0e32\u0e41\u0e1f")

        route = build_task_route(state, "\u0e1b\u0e23\u0e30\u0e40\u0e17\u0e28\u0e44\u0e17\u0e22\u0e21\u0e35\u0e01\u0e35\u0e48\u0e08\u0e31\u0e07\u0e2b\u0e27\u0e31\u0e14")
        gate = workflow_response_gate(route)
        selected = select_general_response_route(route, "OTHER")

        self.assertFalse(gate["workflow_response_allowed"])
        self.assertNotEqual(gate["final_response_gate"], "workflow_missing_entities")
        self.assertTrue(selected["handled"])
        self.assertEqual(selected["response_route"], "general_response")


if __name__ == "__main__":
    unittest.main()
