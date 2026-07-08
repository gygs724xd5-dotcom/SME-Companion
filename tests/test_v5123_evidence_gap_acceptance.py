import unittest
from unittest.mock import patch

import app
from brain.evidence_gap import (
    CALCULATION_INPUT_GAP,
    MISSING_REQUIRED_FIELD,
    NO_GAP,
    STALE_CONTEXT,
    USER_CONFIRMATION_GAP,
    WORKFLOW_REQUIREMENT_GAP,
)
from brain.general_response_router import build_general_direct_response
from brain.response_authority import (
    CLARIFICATION_QUESTION,
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


ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION_COST = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
INCOMPLETE_COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"

STABLE_EVIDENCE_KEYS = (
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


def _record_evidence(message, *, route=None, app_state=None, session_state=None, **kwargs):
    session_state = session_state or {"conversation_reset_diagnostics": {}}
    developer_updates = {}

    def update_section(section, values):
        if section == "developer":
            developer_updates.update(values or {})
        return {}

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value=app_state or {}), \
        patch.object(app, "_update_application_section", side_effect=update_section):
        diagnostics = app._record_evidence_gap_shadow_diagnostics(
            message,
            task_route=route,
            **kwargs,
        )

    return diagnostics, developer_updates, session_state


def _record_authority(message, *, route=None, app_state=None, session_state=None, **kwargs):
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


class V5123EvidenceGapAcceptanceTest(unittest.TestCase):
    def assertStableEvidenceDiagnostics(self, diagnostics):
        for key in STABLE_EVIDENCE_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["evidence_gap_shadow_mode"])

    def assertShadowAuthorityDiagnostics(self, diagnostics):
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

    def test_evidence_gap_diagnostics_are_observable_but_non_authoritative(self):
        route = build_task_route({}, ANALYTICAL_COST)
        forced_profile = {
            "evidence_sufficient": False,
            "gap_detected": True,
            "gap_type": WORKFLOW_REQUIREMENT_GAP,
            "missing_fields": ["customer_segment"],
            "conflicting_fields": [],
            "smallest_next_question": "What is the customer segment?",
            "can_answer_with_assumptions": False,
            "assumption_notes": [],
            "confidence": 0.91,
            "reason": "forced_acceptance_gap",
            "diagnostics": {"evidence_gap_profile_version": "test"},
        }

        with patch.object(app, "evaluate_evidence_gap", return_value=forced_profile):
            diagnostics, developer_updates, session_state = _record_evidence(ANALYTICAL_COST, route=route)

        final_reply = build_general_direct_response(ANALYTICAL_COST)
        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertEqual(diagnostics["evidence_gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertEqual(session_state["last_evidence_gap_profile"], forced_profile)
        self.assertTrue(developer_updates["evidence_gap_shadow_mode"])
        self.assertNotEqual(final_reply, diagnostics["evidence_gap_type"])
        self.assertNotIn("evidence_gap_type", final_reply)
        self.assertNotIn("customer_segment", final_reply)

    def test_evidence_gap_does_not_force_clarification_or_smallest_next_question(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)
        diagnostics, _, _ = _record_evidence(
            ANALYTICAL_COST,
            route=build_task_route({}, ANALYTICAL_COST),
            required_fields=["customer_segment"],
        )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertFalse(diagnostics["evidence_sufficient"])
        self.assertEqual(diagnostics["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(diagnostics["evidence_smallest_next_question"], "What is the customer segment?")
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)
        self.assertNotIn(diagnostics["evidence_smallest_next_question"], expected_reply)

    def test_evidence_gap_does_not_override_response_authority_shadow_mode(self):
        route = build_task_route({}, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {}}
        evidence, _, _ = _record_evidence(
            CONTENT_REQUEST,
            route=route,
            session_state=session_state,
            required_fields=["missing_test_field"],
        )
        authority, _, _ = _record_authority(
            CONTENT_REQUEST,
            route=route,
            session_state=session_state,
        )

        self.assertStableEvidenceDiagnostics(evidence)
        self.assertTrue(session_state["last_evidence_gap_diagnostics"]["evidence_gap_shadow_mode"])
        self.assertShadowAuthorityDiagnostics(authority)
        self.assertIn(authority["response_authority_mode"], {LLM_ASSISTED_RESPONSE, START_WORKFLOW})
        self.assertNotEqual(authority["response_authority_mode"], evidence["evidence_gap_type"])
        self.assertNotEqual(authority["response_authority_mode"], CLARIFICATION_QUESTION)
        self.assertTrue(authority["response_authority_decision"]["diagnostics"]["evidence_sufficient"])

    def test_analytical_cost_statement_remains_direct_business_analysis(self):
        route = build_task_route({}, ANALYTICAL_COST)
        direct_reply = build_general_direct_response(ANALYTICAL_COST)
        evidence, _, _ = _record_evidence(
            ANALYTICAL_COST,
            route=route,
            required_fields=["total_units"],
        )
        authority, _, _ = _record_authority(ANALYTICAL_COST, route=route)

        self.assertNoCostWorkflowAdmission(route)
        self.assertTrue(_entities(route).get("analytical_statement_detected"))
        self.assertIn("30", direct_reply)
        self.assertIn("40", direct_reply)
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertFalse(evidence["evidence_sufficient"])
        self.assertEqual(authority["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(authority["response_authority_workflow_allowed"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), direct_reply)

    def test_semantic_correction_remains_direct_semantic_answer(self):
        route = build_task_route({}, CORRECTION_COST)
        direct_reply = build_general_direct_response(CORRECTION_COST)
        evidence, _, _ = _record_evidence(
            CORRECTION_COST,
            route=route,
            required_fields=["total_units"],
        )
        authority, _, _ = _record_authority(
            CORRECTION_COST,
            route=route,
            semantic_correction_detected=True,
        )

        self.assertNoCostWorkflowAdmission(route)
        self.assertTrue(_entities(route).get("correction_detected"))
        self.assertIn("30", direct_reply)
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertFalse(evidence["evidence_sufficient"])
        self.assertEqual(authority["response_authority_mode"], DIRECT_SEMANTIC_ANSWER)
        self.assertFalse(authority["response_authority_workflow_allowed"])
        self.assertEqual(build_general_direct_response(CORRECTION_COST), direct_reply)

    def test_completed_workflow_after_reset_is_not_reused_as_evidence(self):
        reset_state, reset_diagnostics = reset_transient_conversation_state(
            _dirty_completed_cost_state(),
            conversation_id="conversation-new",
        )
        reset_state, runtime_diagnostics = reset_runtime_contexts(reset_state)
        route = build_task_route(reset_state, CONTENT_REQUEST)
        followup = classify_completed_workflow_followup(reset_state, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {**reset_diagnostics, **runtime_diagnostics}}
        evidence, _, _ = _record_evidence(
            CONTENT_REQUEST,
            route=route,
            app_state=reset_state,
            session_state=session_state,
            required_fields=["unit_cost"],
            completed_context=_completed_cost_workflow().get("collected_fields"),
        )

        self.assertTrue(reset_diagnostics["conversation_reset_applied"])
        self.assertTrue(runtime_diagnostics["runtime_context_reset_applied"])
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], CALCULATION_INPUT_GAP)
        self.assertEqual(evidence["evidence_gap_profile"]["diagnostics"]["stale_completed_fields_blocked"], ["unit_cost"])
        self.assertFalse(evidence["evidence_gap_profile"]["diagnostics"]["completed_workflow_context_counted"])

    def test_stale_context_diagnostic_does_not_force_workflow_continuation(self):
        route = build_task_route({}, CONTENT_REQUEST)
        forced_profile = {
            "evidence_sufficient": False,
            "gap_detected": True,
            "gap_type": STALE_CONTEXT,
            "missing_fields": [],
            "conflicting_fields": [],
            "smallest_next_question": "What should we work on now?",
            "can_answer_with_assumptions": False,
            "assumption_notes": [],
            "confidence": 0.75,
            "reason": "stale_completed_context",
            "diagnostics": {"evidence_gap_profile_version": "test"},
        }

        with patch.object(app, "evaluate_evidence_gap", return_value=forced_profile):
            evidence, _, _ = _record_evidence(CONTENT_REQUEST, route=route)

        followup = classify_completed_workflow_followup(_dirty_completed_cost_state(), CONTENT_REQUEST)
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], STALE_CONTEXT)
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertNotIn("45.50", str(route))

    def test_deterministic_workflow_completion_boundary_remains_result_only(self):
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
        evidence, _, _ = _record_evidence(
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
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], NO_GAP)
        self.assertIsNone(evidence["evidence_smallest_next_question"])
        self.assertNotIn("?", reply.get("reply") or "")

    def test_evidence_gap_diagnostics_do_not_replace_existing_workflow_question(self):
        state, _ = update_workflow_state({}, INCOMPLETE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)
        evidence, _, _ = _record_evidence(
            INCOMPLETE_COST_PER_UNIT,
            active_workflow={**state, "workflow_status": "collecting"},
        )

        self.assertFalse(state.get("workflow_complete"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertFalse(evidence["evidence_sufficient"])
        self.assertNotEqual(reply.get("response_mode"), evidence["evidence_gap_type"])
        self.assertNotEqual(reply.get("reply"), evidence["evidence_smallest_next_question"])

    def test_evidence_gap_fail_closed_diagnostics_do_not_crash_final_response_flow(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "evaluate_evidence_gap", side_effect=RuntimeError("boom")):
            evidence, _, _ = _record_evidence(
                ANALYTICAL_COST,
                route={"business_workflow": object()},
                app_state={"developer": object()},
            )

        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], USER_CONFIRMATION_GAP)
        self.assertEqual(evidence["evidence_gap_reason"], "evidence_gap_shadow_error")
        self.assertIn("evidence_gap_error", evidence["evidence_gap_profile"]["diagnostics"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_commit_boundary_output_shape_is_unchanged_by_evidence_gap_diagnostics(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        baseline = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )
        evidence, _, _ = _record_evidence(COMPONENT_TOTAL, route=route)
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
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(set(result.keys()), set(baseline.keys()))
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("evidence_gap_type", assistant_messages[0]["content"])
        self.assertNotIn("evidence_gap_profile", str(result.get("response_metadata") or {}))


if __name__ == "__main__":
    unittest.main()
