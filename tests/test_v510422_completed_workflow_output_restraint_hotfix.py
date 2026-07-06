import unittest

from brain.response_commit_boundary import commit_response_boundary
from brain.response_mode_engine import ASK_NEXT_FIELD
from brain.task_router import build_task_route
from brain.workflow_output_renderer import generate_deterministic_workflow_reply
from brain.workflow_reply_builder import build_workflow_reply, completed_workflow_output_stop_condition
from brain.workflow_state_machine import update_workflow_state


COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
UNIT_COST_TOTAL = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 15 \u0e1a\u0e32\u0e17 \u0e17\u0e33 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
PROFIT = "\u0e02\u0e32\u0e22 80 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
INCOMPLETE_COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
ZERO_QUANTITY = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 0 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
ANALYTICAL = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"

FORBIDDEN_FOLLOWUPS = (
    "\u0e2d\u0e22\u0e32\u0e01\u0e43\u0e2b\u0e49\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19\u0e14\u0e35\u0e04\u0e23\u0e31\u0e1a",
    "\u0e16\u0e49\u0e32\u0e04\u0e38\u0e13\u0e2d\u0e22\u0e32\u0e01\u0e23\u0e39\u0e49",
    "\u0e16\u0e49\u0e32\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23",
    "\u0e41\u0e08\u0e49\u0e07\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a",
    "\u0e2d\u0e22\u0e32\u0e01\u0e43\u0e2b\u0e49\u0e0a\u0e48\u0e27\u0e22\u0e15\u0e48\u0e2d\u0e44\u0e2b\u0e21\u0e04\u0e23\u0e31\u0e1a",
)


def _workflow(route):
    return route.get("business_workflow") or {}


def _completed_reply(message, workflow="COST_CALCULATION"):
    state, _ = update_workflow_state({}, message, detected_workflow=workflow)
    visible = generate_deterministic_workflow_reply(state)
    reply = build_workflow_reply(state, generated_reply=visible)
    return state, visible, reply


class V510422CompletedWorkflowOutputRestraintHotfixTest(unittest.TestCase):
    def assertNoFollowup(self, text):
        for phrase in FORBIDDEN_FOLLOWUPS:
            self.assertNotIn(phrase, text or "")

    def test_exact_component_cost_live_input_returns_90_without_followup(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        workflow = _workflow(route)
        state, visible, reply = _completed_reply(COMPONENT_TOTAL)
        stop = completed_workflow_output_stop_condition(
            workflow_state={**state, "workflow_complete": True, "workflow_action": "complete"},
            workflow_decision=workflow,
            response_mode=reply.get("response_mode"),
        )

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(workflow.get("missing_entities"), [])
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(reply.get("response_mode"), "GENERATE_OUTPUT")
        self.assertEqual(workflow.get("computed_total_cost"), 90)
        self.assertIn("90", visible)
        self.assertEqual(visible, "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17")
        self.assertTrue(stop["render_result_only"])
        self.assertFalse(stop["clarification_allowed"])
        self.assertFalse(stop["ask_next_field_allowed"])
        self.assertFalse(stop["proactive_followup_allowed"])
        self.assertNoFollowup(reply.get("reply"))

    def test_cost_per_unit_returns_15_without_followup(self):
        route = build_task_route({}, COST_PER_UNIT)
        state, visible, reply = _completed_reply(COST_PER_UNIT)
        self.assertEqual(_workflow(route).get("workflow_action"), "complete")
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 = 15 \u0e1a\u0e32\u0e17")
        self.assertNoFollowup(reply.get("reply"))

    def test_unit_cost_times_quantity_returns_300_without_followup(self):
        route = build_task_route({}, UNIT_COST_TOTAL)
        state, visible, reply = _completed_reply(UNIT_COST_TOTAL)
        self.assertEqual(_workflow(route).get("workflow_action"), "complete")
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 300 \u0e1a\u0e32\u0e17")
        self.assertNoFollowup(reply.get("reply"))

    def test_profit_returns_45_without_followup(self):
        route = build_task_route({}, PROFIT)
        state, visible, reply = _completed_reply(PROFIT, workflow="PROFIT_CALCULATION")
        self.assertEqual(_workflow(route).get("workflow_action"), "complete")
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, "\u0e01\u0e33\u0e44\u0e23 = 45 \u0e1a\u0e32\u0e17")
        self.assertNoFollowup(reply.get("reply"))

    def test_incomplete_cost_per_unit_still_asks_for_quantity(self):
        state, _ = update_workflow_state({}, INCOMPLETE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)
        self.assertFalse(state.get("workflow_complete"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertIsNone(generate_deterministic_workflow_reply(state))

    def test_division_by_zero_still_returns_validation_guidance(self):
        state, _ = update_workflow_state({}, ZERO_QUANTITY, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}
        validation = generate_deterministic_workflow_reply(state)
        self.assertFalse(state.get("is_ready"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(trace.get("validation_error"), "quantity_must_be_greater_than_zero")
        self.assertIn("0", validation)

    def test_v51041_analytical_statement_remains_suppressed(self):
        route = build_task_route({}, ANALYTICAL)
        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))

    def test_v51041_correction_remains_suppressed(self):
        route = build_task_route({}, CORRECTION)
        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))

    def test_full_router_path_and_commit_boundary_commit_once(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        workflow = _workflow(route)
        _, visible, _ = _completed_reply(COMPONENT_TOTAL)
        session_state = {"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}], "last_user_message": COMPONENT_TOTAL}
        application_state = {"conversation": {"conversation_memory": route.get("conversation_memory") or {}}}

        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply=visible,
            intent="cost_calculation",
            workflow=(workflow.get("workflow_state") or {}).get("workflow_id"),
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], visible)
        self.assertIn("90", result["conversation_memory"]["last_assistant_reply"])
        self.assertNoFollowup(result["conversation_memory"]["last_assistant_reply"])


if __name__ == "__main__":
    unittest.main()
