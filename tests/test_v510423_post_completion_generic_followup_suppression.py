import unittest
from unittest.mock import patch

import app
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
INCOMPLETE = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"

EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"
EXPECTED_CPU = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 = 15 \u0e1a\u0e32\u0e17"
EXPECTED_TOTAL = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 300 \u0e1a\u0e32\u0e17"
EXPECTED_PROFIT = "\u0e01\u0e33\u0e44\u0e23 = 45 \u0e1a\u0e32\u0e17"

FORBIDDEN = (
    "\u0e2d\u0e22\u0e32\u0e01\u0e17\u0e23\u0e32\u0e1a\u0e27\u0e48\u0e32\u0e04\u0e38\u0e13\u0e17\u0e33\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e2d\u0e30\u0e44\u0e23",
    "\u0e2d\u0e22\u0e32\u0e01\u0e43\u0e2b\u0e49\u0e0a\u0e48\u0e27\u0e22\u0e15\u0e48\u0e2d\u0e44\u0e2b\u0e21",
    "\u0e16\u0e49\u0e32\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23",
    "\u0e41\u0e19\u0e30\u0e19\u0e33\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22",
    "\u0e27\u0e34\u0e18\u0e35\u0e04\u0e33\u0e19\u0e27\u0e13\u0e01\u0e33\u0e44\u0e23",
    "\u0e41\u0e08\u0e49\u0e07\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a",
)


def _workflow(route):
    return route.get("business_workflow") or {}


def _completed(message, workflow="COST_CALCULATION"):
    route = build_task_route({}, message)
    state, _ = update_workflow_state({}, message, detected_workflow=workflow)
    visible = generate_deterministic_workflow_reply(state)
    reply = build_workflow_reply(state, generated_reply=visible)
    stop = completed_workflow_output_stop_condition(
        workflow_state={**state, "workflow_complete": True, "workflow_action": "complete"},
        workflow_decision=_workflow(route),
        response_mode=reply.get("response_mode"),
    )
    return route, state, visible, reply, stop


class V510423PostCompletionGenericFollowupSuppressionTest(unittest.TestCase):
    def assertNoFollowup(self, text):
        self.assertNotIn("?", text or "")
        self.assertNotIn("\u0e44\u0e2b\u0e21", text or "")
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, text or "")

    def test_component_cost_live_path_returns_90_result_only(self):
        route, state, visible, reply, stop = _completed(COMPONENT_TOTAL)

        self.assertEqual(_workflow(route).get("workflow_action"), "complete")
        self.assertTrue(_workflow(route).get("workflow_complete"))
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(_workflow(route).get("computed_total_cost"), 90)
        self.assertEqual(visible, EXPECTED_COMPONENT)
        self.assertEqual(reply.get("reply"), EXPECTED_COMPONENT)
        self.assertTrue(stop["render_result_only"])
        self.assertFalse(stop["generic_followup_allowed"])
        self.assertFalse(stop["proactive_recommendation_allowed"])
        self.assertFalse(stop["llm_rewrite_allowed"])
        self.assertFalse(stop["append_question_allowed"])
        self.assertNoFollowup(reply.get("reply"))

    def test_cost_per_unit_returns_15_with_no_followup(self):
        _, state, visible, reply, stop = _completed(COST_PER_UNIT)

        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, EXPECTED_CPU)
        self.assertTrue(stop["render_result_only"])
        self.assertNoFollowup(reply.get("reply"))

    def test_unit_cost_times_quantity_returns_300_with_no_followup(self):
        _, state, visible, reply, stop = _completed(UNIT_COST_TOTAL)

        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, EXPECTED_TOTAL)
        self.assertTrue(stop["render_result_only"])
        self.assertNoFollowup(reply.get("reply"))

    def test_profit_returns_45_with_no_followup(self):
        _, state, visible, reply, stop = _completed(PROFIT, workflow="PROFIT_CALCULATION")

        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(visible, EXPECTED_PROFIT)
        self.assertTrue(stop["render_result_only"])
        self.assertNoFollowup(reply.get("reply"))

    def test_incomplete_workflow_still_asks_only_for_quantity(self):
        state, _ = update_workflow_state({}, INCOMPLETE, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)

        self.assertFalse(state.get("workflow_complete"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertIn("\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19", reply.get("reply") or "")
        self.assertIsNone(generate_deterministic_workflow_reply(state))

    def test_app_completed_workflow_handler_bypasses_llm_rewrite_and_followup(self):
        state = {"workflow_state_v2": {}}
        with patch.object(app, "_ensure_conversation_state", return_value=state), \
            patch.object(app, "add_pipeline_event"), \
            patch.object(app, "_sync_session_to_application_state", return_value={}), \
            patch.object(app, "_sync_workflow_state_v2"), \
            patch.object(app, "classify_message_priority", return_value={"allow_field_extraction": True}), \
            patch.object(app, "_maybe_improve_workflow_reply_with_llm", side_effect=AssertionError("LLM rewrite must be bypassed")):
            result = app._handle_state_machine_workflow(
                COMPONENT_TOTAL,
                app.V2_WORKFLOW_COST_CALCULATION,
                {},
            )

        self.assertTrue(result["done"])
        self.assertFalse(result["llm_attempted"])
        self.assertEqual(result["reply"], EXPECTED_COMPONENT)
        self.assertEqual(result["response_mode"], "GENERATE_OUTPUT")
        self.assertTrue(result["completed_workflow_output_stop_condition"]["render_result_only"])
        self.assertFalse(result["completed_workflow_output_stop_condition"]["llm_rewrite_allowed"])
        self.assertNoFollowup(result["reply"])

    def test_response_commit_boundary_commits_result_once(self):
        route, _, visible, _, _ = _completed(COMPONENT_TOTAL)
        session_state = {"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}], "last_user_message": COMPONENT_TOTAL}
        application_state = {"conversation": {"conversation_memory": route.get("conversation_memory") or {}}}

        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply=visible,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNoFollowup(assistant_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
