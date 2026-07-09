import ast
import copy
import inspect
import unittest
from unittest.mock import patch

import app
from brain.business_situation import COST_CHANGE
from brain.evidence_gap import MISSING_REQUIRED_FIELD, NO_GAP
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, DIRECT_SEMANTIC_ANSWER, LLM_ASSISTED_RESPONSE, START_WORKFLOW
from brain.response_commit_boundary import commit_response_boundary
from brain.runtime_context_reset import reset_runtime_contexts
from brain.conversation_runtime_reset import reset_transient_conversation_state
from brain.task_router import build_task_route
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_output_renderer import generate_deterministic_workflow_reply
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import build_workflow_reply, completed_workflow_output_stop_condition
from brain.workflow_state_machine import update_workflow_state


ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION_COST = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"

STABLE_RESPONSE_AUTHORITY_KEYS = (
    "response_authority_decision",
    "response_authority_mode",
    "response_authority_reason",
    "response_authority_workflow_allowed",
    "response_authority_shadow_mode",
)
STABLE_EVIDENCE_GAP_KEYS = (
    "evidence_gap_profile",
    "evidence_gap_detected",
    "evidence_gap_type",
    "evidence_missing_fields",
    "evidence_conflicting_fields",
    "evidence_smallest_next_question",
    "evidence_sufficient",
    "evidence_can_answer_with_assumptions",
    "evidence_gap_reason",
    "evidence_gap_confidence",
    "evidence_gap_shadow_mode",
)
STABLE_BUSINESS_SITUATION_KEYS = (
    "business_situation_profile",
    "business_situation_detected",
    "business_situation_type",
    "business_domain",
    "perspective_stance",
    "business_risk_level",
    "business_opportunity_level",
    "business_urgency_level",
    "owner_attention",
    "recommended_response_posture",
    "business_reasoning_summary",
    "business_situation_confidence",
    "business_situation_shadow_mode",
)


def _session_state():
    return {
        "conversation_reset_diagnostics": {},
        "last_response_authority_diagnostics": {
            "response_authority_decision": {"diagnostics": {"source": "test"}},
            "response_authority_mode": DIRECT_BUSINESS_ANALYSIS,
            "response_authority_reason": "analytical_statement_detected",
            "response_authority_workflow_allowed": False,
            "response_authority_shadow_mode": True,
        },
        "last_evidence_gap_diagnostics": {
            "evidence_gap_profile": {"gap_type": MISSING_REQUIRED_FIELD},
            "evidence_gap_detected": True,
            "evidence_gap_type": MISSING_REQUIRED_FIELD,
            "evidence_missing_fields": ["customer_segment"],
            "evidence_conflicting_fields": [],
            "evidence_smallest_next_question": "What is the customer segment?",
            "evidence_sufficient": False,
            "evidence_can_answer_with_assumptions": False,
            "evidence_gap_reason": "missing_required_field",
            "evidence_gap_confidence": 0.9,
            "evidence_gap_shadow_mode": True,
        },
        "last_business_situation_diagnostics": {
            "business_situation_profile": {"situation_type": COST_CHANGE},
            "business_situation_detected": True,
            "business_situation_type": COST_CHANGE,
            "business_domain": "COST",
            "perspective_stance": "ANALYTICAL",
            "business_risk_level": "LOW",
            "business_opportunity_level": "NONE",
            "business_urgency_level": "LOW",
            "owner_attention": "Cost changed.",
            "recommended_response_posture": "ANALYTICAL",
            "business_reasoning_summary": "cost_change_statement",
            "business_situation_confidence": 0.86,
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


def _record_all_shadow_diagnostics(message, *, route=None, session_state=None, **kwargs):
    session_state = session_state or {"conversation_reset_diagnostics": {}}
    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value={}), \
        patch.object(app, "_update_application_section"):
        evidence = app._record_evidence_gap_shadow_diagnostics(message, task_route=route, **kwargs)
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


def _commit_component_reply(route):
    return commit_response_boundary(
        session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
        application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
        final_reply=EXPECTED_COMPONENT,
        intent="cost_calculation",
        workflow="COST_CALCULATION",
        response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
        assistant_message={"role": "assistant", "show_business_insights": False},
    )


class V5143DiagnosticsDashboardAcceptanceTest(unittest.TestCase):
    def assertResponseAuthorityIntact(self, diagnostics):
        for key in STABLE_RESPONSE_AUTHORITY_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["response_authority_shadow_mode"])

    def assertEvidenceGapIntact(self, diagnostics):
        for key in STABLE_EVIDENCE_GAP_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["evidence_gap_shadow_mode"])

    def assertBusinessSituationIntact(self, diagnostics):
        for key in STABLE_BUSINESS_SITUATION_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["business_situation_shadow_mode"])

    def assertNoCostWorkflowAdmission(self, route):
        gate = route.get("workflow_admission_gate") or {}
        workflow = route.get("business_workflow") or {}
        self.assertNotEqual(gate.get("decision"), "ADMIT")
        self.assertNotEqual(workflow.get("workflow_action"), "start_new")
        self.assertIsNone(workflow.get("workflow_state"))
        self.assertIsNone(workflow.get("next_question"))

    def test_dashboard_snapshot_is_observable_but_non_authoritative(self):
        session_state = _session_state()
        session_state["last_response_authority_diagnostics"]["response_authority_mode"] = START_WORKFLOW
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "build_brain_diagnostics_snapshot") as build_snapshot:
            snapshot, _, session_state = _record_snapshot(session_state)

        build_snapshot.assert_not_called()
        self.assertIs(session_state["brain_diagnostics_snapshot"], snapshot)
        self.assertNotIn("brain_diagnostics_dashboard_snapshot", session_state)
        self.assertIs(session_state["last_brain_diagnostics_snapshot"], snapshot)
        self.assertTrue(session_state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)
        self.assertNotIn("START_WORKFLOW", expected_reply)
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])
        self.assertEqual(
            snapshot["diagnostics"]["brain_diagnostics_snapshot_skipped_reason"],
            "dashboard_snapshot_runtime_disabled_by_default",
        )

    def test_dashboard_snapshot_does_not_activate_gates(self):
        snapshot, _, session_state = _record_snapshot()
        layer_map = snapshot["active_vs_shadow_layer_map"]

        self.assertEqual(set(layer_map), {"Dashboard Snapshot"})
        self.assertEqual(layer_map["Dashboard Snapshot"]["mode"], "shadow")
        self.assertEqual(layer_map["Dashboard Snapshot"]["active_gate_status"], "shadow_only")
        self.assertTrue(session_state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertNotIn("active_gate_violation", snapshot["mismatch_flags"])
        self.assertFalse(snapshot["diagnostics"]["active_gate_changed"])
        self.assertFalse(snapshot["diagnostics"]["brain_diagnostics_snapshot_runtime_enabled"])

    def test_dashboard_snapshot_does_not_override_response_authority_diagnostics(self):
        session_state = _session_state()
        before = copy.deepcopy(session_state["last_response_authority_diagnostics"])

        snapshot, _, session_state = _record_snapshot(session_state)

        self.assertEqual(session_state["last_response_authority_diagnostics"], before)
        self.assertEqual(snapshot["shadow_diagnostics"]["response_authority"], before)
        self.assertEqual(before["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertTrue(before["response_authority_shadow_mode"])

    def test_dashboard_snapshot_does_not_override_evidence_gap_diagnostics(self):
        session_state = _session_state()
        before = copy.deepcopy(session_state["last_evidence_gap_diagnostics"])

        snapshot, _, session_state = _record_snapshot(session_state)

        self.assertEqual(session_state["last_evidence_gap_diagnostics"], before)
        self.assertEqual(snapshot["shadow_diagnostics"]["evidence_gap"], before)
        self.assertEqual(before["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertFalse(before["evidence_sufficient"])
        self.assertTrue(before["evidence_gap_shadow_mode"])

    def test_dashboard_snapshot_does_not_override_business_situation_diagnostics(self):
        session_state = _session_state()
        before = copy.deepcopy(session_state["last_business_situation_diagnostics"])

        snapshot, _, session_state = _record_snapshot(session_state)

        self.assertEqual(session_state["last_business_situation_diagnostics"], before)
        self.assertEqual(snapshot["shadow_diagnostics"]["business_situation"], before)
        self.assertEqual(before["business_situation_type"], COST_CHANGE)
        self.assertEqual(before["perspective_stance"], "ANALYTICAL")
        self.assertTrue(before["business_situation_shadow_mode"])

    def test_dashboard_snapshot_does_not_render_ui(self):
        source = inspect.getsource(app._record_brain_diagnostics_snapshot_shadow)
        tree = ast.parse(source)
        streamlit_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "st":
                    streamlit_calls.append(node.func.attr)

        self.assertEqual(streamlit_calls, [])
        self.assertFalse(hasattr(app, "render_brain_diagnostics_dashboard"))
        self.assertFalse(hasattr(app, "render_dashboard_snapshot"))
        self.assertFalse(hasattr(app, "_show_brain_diagnostics_dashboard"))

    def test_analytical_cost_statement_remains_direct_business_analysis(self):
        route = build_task_route({}, ANALYTICAL_COST)
        expected_reply = build_general_direct_response(ANALYTICAL_COST)
        authority, evidence, business, snapshot, _ = _record_all_shadow_diagnostics(ANALYTICAL_COST, route=route)

        self.assertNoCostWorkflowAdmission(route)
        self.assertResponseAuthorityIntact(authority)
        self.assertEvidenceGapIntact(evidence)
        self.assertBusinessSituationIntact(business)
        self.assertEqual(authority["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertIn("30", expected_reply)
        self.assertIn("40", expected_reply)
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])

    def test_semantic_correction_remains_direct_semantic_answer(self):
        route = build_task_route({}, CORRECTION_COST)
        expected_reply = build_general_direct_response(CORRECTION_COST)
        session_state = {"conversation_reset_diagnostics": {}}
        with patch.object(app.st, "session_state", session_state), \
            patch.object(app, "_sync_session_to_application_state", return_value={}), \
            patch.object(app, "_update_application_section"):
            authority = app._record_response_authority_shadow_decision(
                CORRECTION_COST,
                task_route=route,
                semantic_correction_detected=True,
            )
            evidence = app._record_evidence_gap_shadow_diagnostics(
                CORRECTION_COST,
                task_route=route,
                required_fields=["total_units"],
            )
            business = app._record_business_situation_shadow_diagnostics(
                CORRECTION_COST,
                task_route=route,
                evidence_gap_profile={"evidence_sufficient": True, "gap_type": NO_GAP},
            )
            snapshot = app._record_brain_diagnostics_snapshot_shadow(
                current_turn_trace={"final_response_route": "direct"}
            )

        self.assertNoCostWorkflowAdmission(route)
        self.assertResponseAuthorityIntact(authority)
        self.assertEvidenceGapIntact(evidence)
        self.assertBusinessSituationIntact(business)
        self.assertEqual(authority["response_authority_mode"], DIRECT_SEMANTIC_ANSWER)
        self.assertIn("30", expected_reply)
        self.assertEqual(build_general_direct_response(CORRECTION_COST), expected_reply)
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])

    def test_completed_workflow_context_after_reset_is_not_reused_by_snapshot_state(self):
        reset_state, reset_diagnostics = reset_transient_conversation_state(
            _dirty_completed_cost_state(),
            conversation_id="conversation-new",
        )
        reset_state, runtime_diagnostics = reset_runtime_contexts(reset_state)
        route = build_task_route(reset_state, CONTENT_REQUEST)
        followup = classify_completed_workflow_followup(reset_state, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {**reset_diagnostics, **runtime_diagnostics}}

        _, evidence, _, snapshot, _ = _record_all_shadow_diagnostics(CONTENT_REQUEST, route=route, session_state=session_state)

        self.assertTrue(reset_diagnostics["conversation_reset_applied"])
        self.assertTrue(runtime_diagnostics["runtime_context_reset_applied"])
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        self.assertNotIn("45.50", str(route))
        self.assertEvidenceGapIntact(evidence)
        self.assertIs(session_state["brain_diagnostics_snapshot"], snapshot)
        self.assertNotIn("45.50", str(snapshot))

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
        _, _, _, snapshot, _ = _record_all_shadow_diagnostics(
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
        self.assertNotIn("?", reply.get("reply") or "")
        self.assertNotIn("brain_diagnostics_snapshot", reply.get("reply") or "")
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])

    def test_dashboard_snapshot_fail_closed_diagnostics_do_not_crash_final_response_flow(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)
        with patch.object(app, "build_brain_diagnostics_snapshot", side_effect=RuntimeError("boom")) as build_snapshot:
            snapshot, _, session_state = _record_snapshot({"conversation_reset_diagnostics": {}})

        build_snapshot.assert_not_called()
        self.assertTrue(session_state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertEqual(
            snapshot["diagnostics"]["brain_diagnostics_snapshot_reason"],
            "dashboard_snapshot_runtime_disabled_by_default",
        )
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_commit_boundary_output_is_unchanged_by_dashboard_snapshot_diagnostics(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        baseline = _commit_component_reply(route)
        _, _, _, snapshot, _ = _record_all_shadow_diagnostics(COMPONENT_TOTAL, route=route)
        result = _commit_component_reply(route)
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]

        self.assertEqual(set(result.keys()), set(baseline.keys()))
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("brain_diagnostics_snapshot", assistant_messages[0]["content"])
        self.assertNotIn("brain_diagnostics_snapshot", str(result.get("response_metadata") or {}))
        self.assertTrue(snapshot["diagnostics"]["brain_diagnostics_snapshot_shadow_mode"])


if __name__ == "__main__":
    unittest.main()
