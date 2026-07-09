import ast
import copy
import inspect
import unittest
from unittest.mock import patch

import app
from brain.business_situation import COST_CHANGE
from brain.evidence_gap import MISSING_REQUIRED_FIELD
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, DIRECT_SEMANTIC_ANSWER
from brain.response_commit_boundary import commit_response_boundary
from brain.runtime_context_reset import reset_runtime_contexts
from brain.conversation_runtime_reset import reset_transient_conversation_state
from brain.task_router import build_task_route
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_output_renderer import generate_deterministic_workflow_reply
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN
from brain.workflow_reply_builder import build_workflow_reply, completed_workflow_output_stop_condition
from brain.workflow_state_machine import update_workflow_state


ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION_COST = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"


STABLE_SNAPSHOT_KEYS = {
    "dashboard_version",
    "layer_progress",
    "shadow_diagnostics",
    "current_turn_trace",
    "regression_safety_status",
    "test_health",
    "protected_dirty_files",
    "active_vs_shadow_layer_map",
    "mismatch_flags",
    "next_recommended_step",
    "diagnostics",
}


def _session_state():
    return {
        "conversation_reset_diagnostics": {},
        "last_response_authority_diagnostics": {
            "response_authority_mode": DIRECT_BUSINESS_ANALYSIS,
            "response_authority_reason": "analytical_statement_detected",
            "response_authority_shadow_mode": True,
        },
        "last_evidence_gap_diagnostics": {
            "evidence_gap_type": MISSING_REQUIRED_FIELD,
            "evidence_sufficient": False,
            "evidence_gap_shadow_mode": True,
        },
        "last_business_situation_diagnostics": {
            "business_situation_detected": True,
            "business_situation_type": COST_CHANGE,
            "business_situation_shadow_mode": True,
        },
        "ai_pipeline_debug_trace": {},
    }


def _record_snapshot(session_state=None, *, update_section=None, **kwargs):
    session_state = session_state or _session_state()
    developer_updates = {}

    def capture_update(section, values):
        if section == "developer":
            developer_updates.update(values or {})
        return {}

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_update_application_section", side_effect=update_section or capture_update):
        snapshot = app._record_brain_diagnostics_snapshot_shadow(**kwargs)

    return snapshot, developer_updates, session_state


def _record_all_shadow_diagnostics(message, *, route=None, session_state=None):
    session_state = session_state or {"conversation_reset_diagnostics": {}}
    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value={}), \
        patch.object(app, "_update_application_section"):
        evidence = app._record_evidence_gap_shadow_diagnostics(message, task_route=route)
        business = app._record_business_situation_shadow_diagnostics(
            message,
            task_route=route,
            evidence_gap_profile=evidence.get("evidence_gap_profile"),
        )
        authority = app._record_response_authority_shadow_decision(message, task_route=route)
        snapshot = app._record_brain_diagnostics_snapshot_shadow(
            current_turn_trace={"final_response_route": "direct"}
        )
    return authority, evidence, business, snapshot, session_state


def _dirty_completed_cost_state():
    completed = {
        "workflow_id": "COST_CALCULATION",
        "workflow_name": "cost_calculation",
        "collected_fields": {"unit_cost": 35, "total_units": 100, "profit_percent": 30},
        "generated_response": "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 35 \u0e1a\u0e32\u0e17",
    }
    return {
        "store": {"last_completed_workflow": completed},
        "business_memory": {"completed_workflows": [completed]},
        "conversation": {
            "conversation_memory": {"completed_workflows": [completed]},
            "business_context": {"current_discussion_topic": "old cost/profit"},
        },
        "developer": {"developer_mode": True},
    }


class V5142DiagnosticsDashboardShadowRuntimeTest(unittest.TestCase):
    def test_runtime_helper_computes_and_stores_shadow_snapshot(self):
        snapshot, developer_updates, session_state = _record_snapshot(
            current_turn_trace={"final_response_route": "direct"}
        )

        self.assertEqual(set(snapshot), STABLE_SNAPSHOT_KEYS)
        self.assertIs(session_state["brain_diagnostics_snapshot"], snapshot)
        self.assertIs(session_state["brain_diagnostics_dashboard_snapshot"], snapshot)
        self.assertIs(session_state["last_brain_diagnostics_snapshot"], snapshot)
        self.assertTrue(session_state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertIs(developer_updates["brain_diagnostics_snapshot"], snapshot)

    def test_snapshot_includes_response_authority_evidence_gap_and_business_situation(self):
        snapshot, _, _ = _record_snapshot()

        self.assertEqual(
            snapshot["shadow_diagnostics"]["response_authority"]["response_authority_mode"],
            DIRECT_BUSINESS_ANALYSIS,
        )
        self.assertEqual(
            snapshot["shadow_diagnostics"]["evidence_gap"]["evidence_gap_type"],
            MISSING_REQUIRED_FIELD,
        )
        self.assertEqual(
            snapshot["shadow_diagnostics"]["business_situation"]["business_situation_type"],
            COST_CHANGE,
        )

    def test_snapshot_marks_active_gates_inactive_shadow_by_default(self):
        snapshot, _, _ = _record_snapshot()

        for status in snapshot["active_vs_shadow_layer_map"].values():
            self.assertEqual(status["mode"], "shadow")
            self.assertEqual(status["active_gate_status"], "shadow_only")

    def test_snapshot_fail_closed_path_does_not_crash_final_response_flow(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)
        with patch.object(app, "build_brain_diagnostics_snapshot", side_effect=RuntimeError("boom")):
            snapshot, _, session_state = _record_snapshot()

        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)
        self.assertTrue(session_state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertEqual(
            snapshot["diagnostics"]["brain_diagnostics_snapshot_reason"],
            "brain_diagnostics_snapshot_shadow_error",
        )
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])

    def test_snapshot_is_observable_but_non_authoritative(self):
        forced_session = _session_state()
        forced_session["last_response_authority_diagnostics"]["response_authority_mode"] = "START_WORKFLOW"
        reply = build_general_direct_response(ANALYTICAL_COST)
        snapshot, _, _ = _record_snapshot(forced_session)

        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), reply)
        self.assertEqual(snapshot["diagnostics"]["response_behavior_changed"], False)
        self.assertNotIn("START_WORKFLOW", reply)

    def test_runtime_shadow_records_feed_dashboard_snapshot_without_overriding_each_other(self):
        route = build_task_route({}, CONTENT_REQUEST)
        authority, evidence, business, snapshot, session_state = _record_all_shadow_diagnostics(
            CONTENT_REQUEST,
            route=route,
        )

        self.assertTrue(authority["response_authority_shadow_mode"])
        self.assertTrue(evidence["evidence_gap_shadow_mode"])
        self.assertTrue(business["business_situation_shadow_mode"])
        self.assertEqual(
            session_state["last_response_authority_diagnostics"],
            snapshot["shadow_diagnostics"]["response_authority"],
        )
        self.assertEqual(
            session_state["last_evidence_gap_diagnostics"],
            snapshot["shadow_diagnostics"]["evidence_gap"],
        )
        self.assertEqual(
            session_state["last_business_situation_diagnostics"],
            snapshot["shadow_diagnostics"]["business_situation"],
        )

    def test_snapshot_does_not_mutate_input_diagnostics(self):
        session_state = _session_state()
        before = copy.deepcopy(session_state)
        _record_snapshot(session_state)

        for key in (
            "last_response_authority_diagnostics",
            "last_evidence_gap_diagnostics",
            "last_business_situation_diagnostics",
        ):
            self.assertEqual(session_state[key], before[key])

    def test_existing_direct_analysis_and_semantic_correction_remain_direct(self):
        analytical_route = build_task_route({}, ANALYTICAL_COST)
        analytical_reply = build_general_direct_response(ANALYTICAL_COST)
        authority, _, _, _, _ = _record_all_shadow_diagnostics(ANALYTICAL_COST, route=analytical_route)

        correction_route = build_task_route({}, CORRECTION_COST)
        correction_reply = build_general_direct_response(CORRECTION_COST)
        correction_session = {"conversation_reset_diagnostics": {}}
        with patch.object(app.st, "session_state", correction_session), \
            patch.object(app, "_sync_session_to_application_state", return_value={}), \
            patch.object(app, "_update_application_section"):
            correction_authority = app._record_response_authority_shadow_decision(
                CORRECTION_COST,
                task_route=correction_route,
                semantic_correction_detected=True,
            )
            app._record_brain_diagnostics_snapshot_shadow()

        self.assertIn("30", analytical_reply)
        self.assertIn("40", analytical_reply)
        self.assertEqual(authority["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), analytical_reply)
        self.assertIn("30", correction_reply)
        self.assertEqual(correction_authority["response_authority_mode"], DIRECT_SEMANTIC_ANSWER)
        self.assertEqual(build_general_direct_response(CORRECTION_COST), correction_reply)

    def test_reset_isolation_and_completion_boundary_remain_intact(self):
        reset_state, reset_diagnostics = reset_transient_conversation_state(
            _dirty_completed_cost_state(),
            conversation_id="conversation-new",
        )
        reset_state, runtime_diagnostics = reset_runtime_contexts(reset_state)
        route = build_task_route(reset_state, CONTENT_REQUEST)
        followup = classify_completed_workflow_followup(reset_state, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {**reset_diagnostics, **runtime_diagnostics}}
        _record_all_shadow_diagnostics(CONTENT_REQUEST, route=route, session_state=session_state)
        result = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("brain_diagnostics_snapshot", assistant_messages[0]["content"])

    def test_deterministic_workflow_completion_boundary_remains_intact(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        workflow = route.get("business_workflow") or {}
        state, _ = update_workflow_state({}, COMPONENT_TOTAL, detected_workflow="COST_CALCULATION")
        visible = generate_deterministic_workflow_reply(state)
        reply = build_workflow_reply(state, generated_reply=visible)
        stop = completed_workflow_output_stop_condition(
            workflow_state={**state, "workflow_complete": True, "workflow_action": "complete"},
            workflow_decision=workflow,
            response_mode=reply.get("response_mode"),
        )
        _record_all_shadow_diagnostics(
            COMPONENT_TOTAL,
            route=route,
            session_state={"conversation_reset_diagnostics": {}},
        )

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(visible, EXPECTED_COMPONENT)
        self.assertEqual(reply.get("reply"), EXPECTED_COMPONENT)
        self.assertTrue(stop["render_result_only"])
        self.assertFalse(stop["append_question_allowed"])
        self.assertNotIn("brain_diagnostics_snapshot", reply.get("reply") or "")

    def test_no_ui_dashboard_rendering_is_introduced_by_snapshot_helper(self):
        source = inspect.getsource(app._record_brain_diagnostics_snapshot_shadow)
        tree = ast.parse(source)
        rendered_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "st":
                rendered_calls.append(node.func.attr)

        self.assertEqual(rendered_calls, [])


if __name__ == "__main__":
    unittest.main()
