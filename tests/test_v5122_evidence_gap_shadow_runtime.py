import copy
import unittest
from unittest.mock import patch

import app
from brain.evidence_gap import MISSING_REQUIRED_FIELD, NO_GAP, USER_CONFIRMATION_GAP, WORKFLOW_REQUIREMENT_GAP
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, LLM_ASSISTED_RESPONSE, START_WORKFLOW
from brain.response_commit_boundary import commit_response_boundary
from brain.response_mode_engine import ASK_NEXT_FIELD
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.conversation_runtime_reset import reset_transient_conversation_state
from brain.runtime_context_reset import reset_runtime_contexts
from brain.task_router import build_task_route
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN
from brain.workflow_reply_builder import build_workflow_reply
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

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value=app_state or {}), \
        patch.object(app, "_update_application_section"):
        return app._record_response_authority_shadow_decision(
            message,
            task_route=route,
            **kwargs,
        )


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


class V5122EvidenceGapShadowRuntimeTest(unittest.TestCase):
    def assertStableEvidenceDiagnostics(self, diagnostics):
        for key in STABLE_EVIDENCE_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["evidence_gap_shadow_mode"])

    def test_app_records_evidence_gap_shadow_diagnostics_without_mutating_inputs(self):
        route = {
            "business_workflow": {
                "required_fields": ["customer_segment"],
                "collected_fields": {},
            }
        }
        original_route = copy.deepcopy(route)

        diagnostics, developer_updates, session_state = _record_evidence(
            "Draft a post.",
            route=route,
        )

        self.assertEqual(route, original_route)
        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertEqual(diagnostics["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(diagnostics["evidence_missing_fields"], ["customer_segment"])
        self.assertEqual(developer_updates["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(session_state["last_evidence_gap_profile"], diagnostics["evidence_gap_profile"])

    def test_diagnostics_include_stable_keys_for_no_gap_profile(self):
        diagnostics, _, _ = _record_evidence(
            "The customer segment is retail.",
            route={"business_workflow": {"required_fields": ["customer_segment"], "collected_fields": {"customer_segment": "retail"}}},
        )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertEqual(diagnostics["evidence_gap_type"], NO_GAP)
        self.assertFalse(diagnostics["evidence_gap_detected"])

    def test_fail_closed_path_does_not_crash_final_response_flow(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "evaluate_evidence_gap", side_effect=RuntimeError("boom")):
            diagnostics, _, _ = _record_evidence(ANALYTICAL_COST)

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertEqual(diagnostics["evidence_gap_type"], USER_CONFIRMATION_GAP)
        self.assertEqual(diagnostics["evidence_gap_reason"], "evidence_gap_shadow_error")
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_evidence_gap_is_observable_but_non_authoritative(self):
        state, _ = update_workflow_state({}, INCOMPLETE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)
        diagnostics, _, _ = _record_evidence(
            INCOMPLETE_COST_PER_UNIT,
            active_workflow={**state, "workflow_status": "collecting"},
        )

        self.assertEqual(diagnostics["evidence_gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertFalse(diagnostics["evidence_sufficient"])
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertNotEqual(reply.get("response_mode"), diagnostics["evidence_gap_type"])

    def test_existing_direct_analysis_and_semantic_correction_remain_direct(self):
        analytical_route = build_task_route({}, ANALYTICAL_COST)
        analytical_reply = build_general_direct_response(ANALYTICAL_COST)
        _record_evidence(ANALYTICAL_COST, route=analytical_route)
        authority = _record_authority(ANALYTICAL_COST, route=analytical_route)

        correction_route = build_task_route({}, CORRECTION_COST)
        correction_reply = build_general_direct_response(CORRECTION_COST)
        _record_evidence(CORRECTION_COST, route=correction_route)

        self.assertIn("30", analytical_reply)
        self.assertIn("40", analytical_reply)
        self.assertEqual(authority["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), analytical_reply)
        self.assertIn("30", correction_reply)
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
        diagnostics, _, _ = _record_evidence(
            CONTENT_REQUEST,
            route=route,
            app_state=reset_state,
            session_state=session_state,
        )
        result = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("evidence_gap_type", assistant_messages[0]["content"])

    def test_response_authority_shadow_mode_is_not_overridden_by_evidence_gap(self):
        route = build_task_route({}, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {}}
        _record_evidence(
            CONTENT_REQUEST,
            route=route,
            session_state=session_state,
            required_fields=["missing_test_field"],
        )
        authority = _record_authority(
            CONTENT_REQUEST,
            route=route,
            session_state=session_state,
        )

        self.assertTrue(session_state["last_evidence_gap_diagnostics"]["evidence_gap_shadow_mode"])
        self.assertTrue(authority["response_authority_shadow_mode"])
        self.assertIn(authority["response_authority_mode"], {LLM_ASSISTED_RESPONSE, START_WORKFLOW})


if __name__ == "__main__":
    unittest.main()
