import unittest
from unittest.mock import patch

import app
from brain.general_response_router import build_general_direct_response
from brain.response_authority import (
    CONTINUE_WORKFLOW,
    DIRECT_BUSINESS_ANALYSIS,
    DIRECT_SEMANTIC_ANSWER,
    LLM_ASSISTED_RESPONSE,
    START_WORKFLOW,
)
from brain.response_commit_boundary import commit_response_boundary
from brain.response_mode_engine import ASK_NEXT_FIELD
from brain.runtime_context_reset import reset_runtime_contexts
from brain.conversation_runtime_reset import reset_transient_conversation_state
from brain.task_router import build_task_route
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_output_renderer import generate_deterministic_workflow_reply
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import build_workflow_reply, completed_workflow_output_stop_condition
from brain.workflow_state_machine import update_workflow_state


COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"
ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION_COST = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
INCOMPLETE_COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"


def _workflow(route):
    return route.get("business_workflow") or {}


def _entities(route):
    return (route.get("extracted_entities") or {}).get("extracted_entities") or {}


def _completed_cost_workflow():
    return {
        "workflow_id": WORKFLOW_COST_CALCULATION,
        "workflow_name": "cost_calculation",
        "collected_fields": {"unit_cost": 35, "total_units": 100, "profit_percent": 30},
        "generated_response": (
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 35 \u0e1a\u0e32\u0e17 "
            "\u0e41\u0e19\u0e30\u0e19\u0e33\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22 45.50 \u0e1a\u0e32\u0e17"
        ),
    }


def _dirty_completed_cost_state():
    completed = _completed_cost_workflow()
    return {
        "store": {"last_completed_workflow": completed},
        "business_memory": {"completed_workflows": [completed]},
        "conversation": {
            "conversation_memory": {"completed_workflows": [completed]},
            "business_context": {"current_discussion_topic": "old cost/profit"},
            "last_generated_response": completed["generated_response"],
            "response_memory": {"last_generated_response": completed["generated_response"]},
        },
        "developer": {"developer_mode": True},
    }


def _record_shadow(message, *, route=None, app_state=None, session_state=None, **kwargs):
    session_state = session_state or {"conversation_reset_diagnostics": {}}
    developer_updates = {}

    def update_section(section, values):
        if section == "developer":
            developer_updates.update(values or {})
        return {}

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value=app_state or {}), \
        patch.object(app, "_update_application_section", side_effect=update_section):
        diagnostics = app._record_response_authority_shadow_decision(
            message,
            task_route=route,
            **kwargs,
        )

    return diagnostics, developer_updates, session_state


class V5113ResponseAuthorityAcceptanceTest(unittest.TestCase):
    def assertShadowDiagnostics(self, diagnostics):
        for key in (
            "response_authority_decision",
            "response_authority_mode",
            "response_authority_reason",
            "response_authority_workflow_allowed",
            "response_authority_shadow_mode",
        ):
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["response_authority_shadow_mode"])

    def assertNoCostWorkflowAdmission(self, route):
        gate = route.get("workflow_admission_gate") or {}
        workflow = _workflow(route)
        self.assertNotEqual(gate.get("decision"), "ADMIT")
        self.assertNotEqual(workflow.get("workflow_action"), "start_new")
        self.assertIsNone(workflow.get("workflow_state"))
        self.assertIsNone(workflow.get("next_question"))

    def test_deterministic_cost_completion_remains_result_only_with_shadow_diagnostics(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        workflow = _workflow(route)
        state, _ = update_workflow_state({}, COMPONENT_TOTAL, detected_workflow="COST_CALCULATION")
        visible = generate_deterministic_workflow_reply(state)
        reply = build_workflow_reply(state, generated_reply=visible)
        stop = completed_workflow_output_stop_condition(
            workflow_state={**state, "workflow_complete": True, "workflow_action": "complete"},
            workflow_decision=workflow,
            response_mode=reply.get("response_mode"),
        )
        diagnostics, _, _ = _record_shadow(
            COMPONENT_TOTAL,
            route=route,
            active_workflow={**state, "workflow_status": "completed"},
        )

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(visible, EXPECTED_COMPONENT)
        self.assertEqual(reply.get("reply"), EXPECTED_COMPONENT)
        self.assertTrue(stop["render_result_only"])
        self.assertFalse(stop["append_question_allowed"])
        self.assertShadowDiagnostics(diagnostics)
        self.assertNotEqual(diagnostics["response_authority_mode"], CONTINUE_WORKFLOW)
        self.assertNotIn("?", reply.get("reply") or "")

    def test_completed_workflow_after_reset_is_not_reused_or_authoritatively_continued(self):
        reset_state, reset_diagnostics = reset_transient_conversation_state(
            _dirty_completed_cost_state(),
            conversation_id="conversation-new",
        )
        reset_state, runtime_diagnostics = reset_runtime_contexts(reset_state)
        route = build_task_route(reset_state, CONTENT_REQUEST)
        followup = classify_completed_workflow_followup(reset_state, CONTENT_REQUEST)
        diagnostics, _, _ = _record_shadow(
            CONTENT_REQUEST,
            route=route,
            app_state=reset_state,
            session_state={"conversation_reset_diagnostics": {**reset_diagnostics, **runtime_diagnostics}},
        )

        self.assertTrue(reset_diagnostics["conversation_reset_applied"])
        self.assertTrue(runtime_diagnostics["runtime_context_reset_applied"])
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        self.assertNotIn("45.50", str(route))
        self.assertShadowDiagnostics(diagnostics)
        self.assertNotEqual(diagnostics["response_authority_mode"], CONTINUE_WORKFLOW)

    def test_analytical_cost_statement_remains_direct_analysis_and_shadow_only(self):
        route = build_task_route({}, ANALYTICAL_COST)
        direct_reply = build_general_direct_response(ANALYTICAL_COST)
        diagnostics, _, _ = _record_shadow(ANALYTICAL_COST, route=route)

        self.assertNoCostWorkflowAdmission(route)
        self.assertTrue(_entities(route).get("analytical_statement_detected"))
        self.assertIn("30", direct_reply)
        self.assertIn("40", direct_reply)
        self.assertEqual(diagnostics["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(diagnostics["response_authority_workflow_allowed"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), direct_reply)

    def test_semantic_correction_remains_direct_answer_and_shadow_only(self):
        route = build_task_route({}, CORRECTION_COST)
        direct_reply = build_general_direct_response(CORRECTION_COST)
        diagnostics, _, _ = _record_shadow(
            CORRECTION_COST,
            route=route,
            semantic_correction_detected=True,
        )

        self.assertNoCostWorkflowAdmission(route)
        self.assertTrue(_entities(route).get("correction_detected"))
        self.assertIn("30", direct_reply)
        self.assertEqual(diagnostics["response_authority_mode"], DIRECT_SEMANTIC_ANSWER)
        self.assertFalse(diagnostics["response_authority_workflow_allowed"])
        self.assertEqual(build_general_direct_response(CORRECTION_COST), direct_reply)

    def test_shadow_diagnostics_fail_closed_without_changing_final_response_path(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "decide_response_authority", side_effect=RuntimeError("boom")):
            diagnostics, _, _ = _record_shadow(
                ANALYTICAL_COST,
                route={"malformed": object()},
                app_state={"developer": object()},
            )

        self.assertShadowDiagnostics(diagnostics)
        self.assertEqual(diagnostics["response_authority_mode"], LLM_ASSISTED_RESPONSE)
        self.assertEqual(diagnostics["response_authority_reason"], "authority_shadow_error")
        self.assertIn("response_authority_error", diagnostics["response_authority_decision"]["diagnostics"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_shadow_mode_diagnostics_are_observable_but_not_an_active_response_gate(self):
        state, _ = update_workflow_state({}, INCOMPLETE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)

        with patch.object(
            app,
            "decide_response_authority",
            return_value={
                "response_mode": START_WORKFLOW,
                "workflow_allowed": True,
                "commit_required": False,
                "reason": "forced_conflicting_shadow_decision",
                "diagnostics": {"response_authority_version": "test"},
            },
        ):
            diagnostics, developer_updates, _ = _record_shadow(INCOMPLETE_COST_PER_UNIT)

        self.assertFalse(state.get("workflow_complete"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertIn("\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19", reply.get("reply") or "")
        self.assertEqual(diagnostics["response_authority_mode"], START_WORKFLOW)
        self.assertTrue(developer_updates["response_authority_shadow_mode"])
        self.assertNotEqual(reply.get("response_mode"), diagnostics["response_authority_mode"])

    def test_response_authority_diagnostics_do_not_change_commit_boundary_output(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        diagnostics, _, _ = _record_shadow(COMPONENT_TOTAL, route=route)
        result = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertShadowDiagnostics(diagnostics)
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("response_authority_mode", assistant_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
