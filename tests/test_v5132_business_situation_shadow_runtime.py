import copy
import unittest
from unittest.mock import patch

import app
from brain.business_situation import COST, COST_CHANGE, NO_BUSINESS_SITUATION
from brain.evidence_gap import MISSING_REQUIRED_FIELD
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, DIRECT_SEMANTIC_ANSWER, LLM_ASSISTED_RESPONSE, START_WORKFLOW
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


def _record_business(message, *, route=None, app_state=None, session_state=None, **kwargs):
    session_state = session_state or {"conversation_reset_diagnostics": {}}
    developer_updates = {}

    def update_section(section, values):
        if section == "developer":
            developer_updates.update(values or {})
        return {}

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value=app_state or {}), \
        patch.object(app, "_update_application_section", side_effect=update_section):
        diagnostics = app._record_business_situation_shadow_diagnostics(
            message,
            task_route=route,
            **kwargs,
        )

    return diagnostics, developer_updates, session_state


def _record_evidence(message, *, route=None, app_state=None, session_state=None, **kwargs):
    session_state = session_state or {"conversation_reset_diagnostics": {}}

    with patch.object(app.st, "session_state", session_state), \
        patch.object(app, "_sync_session_to_application_state", return_value=app_state or {}), \
        patch.object(app, "_update_application_section"):
        return app._record_evidence_gap_shadow_diagnostics(
            message,
            task_route=route,
            **kwargs,
        )


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


class V5132BusinessSituationShadowRuntimeTest(unittest.TestCase):
    def assertStableBusinessSituationDiagnostics(self, diagnostics):
        for key in STABLE_BUSINESS_SITUATION_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["business_situation_shadow_mode"])

    def test_app_records_business_situation_shadow_diagnostics_without_mutating_inputs(self):
        route = {
            "business_context": {"business_type": "bakery"},
            "intent_resolution": {"resolved_intent": "cost_calculation"},
            "extracted_entities": {"extracted_entities": {"cost": 55}},
        }
        active_workflow = {"workflow_id": "COST_CALCULATION", "collected_fields": {"cost": 55}}
        original_route = copy.deepcopy(route)
        original_workflow = copy.deepcopy(active_workflow)

        diagnostics, developer_updates, session_state = _record_business(
            "Supplier cost went up from 40 to 55 baht.",
            route=route,
            active_workflow=active_workflow,
        )

        self.assertEqual(route, original_route)
        self.assertEqual(active_workflow, original_workflow)
        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertEqual(diagnostics["business_situation_type"], COST_CHANGE)
        self.assertEqual(diagnostics["business_domain"], COST)
        self.assertEqual(developer_updates["business_situation_type"], COST_CHANGE)
        self.assertEqual(session_state["last_business_situation_profile"], diagnostics["business_situation_profile"])

    def test_diagnostics_include_stable_keys_for_no_business_situation_profile(self):
        diagnostics, _, _ = _record_business("Hi, thanks.")

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertEqual(diagnostics["business_situation_type"], NO_BUSINESS_SITUATION)
        self.assertFalse(diagnostics["business_situation_detected"])

    def test_fail_closed_path_does_not_crash_final_response_flow(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "evaluate_business_situation", side_effect=RuntimeError("boom")):
            diagnostics, _, _ = _record_business(ANALYTICAL_COST)

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertEqual(diagnostics["business_situation_type"], NO_BUSINESS_SITUATION)
        self.assertEqual(diagnostics["business_reasoning_summary"], "business_situation_shadow_error")
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_business_situation_is_observable_but_non_authoritative(self):
        route = build_task_route({}, CONTENT_REQUEST)
        forced_profile = {
            "situation_detected": True,
            "situation_type": "PRICING_DECISION",
            "business_domain": "PRICING",
            "perspective_stance": "OWNER_ADVISORY",
            "risk_level": "HIGH",
            "opportunity_level": "HIGH",
            "urgency_level": "HIGH",
            "owner_attention": "Raise price now.",
            "recommended_response_posture": "OWNER_ADVISORY",
            "reasoning_summary": "forced_shadow_profile",
            "confidence": 0.99,
            "assumptions": [],
            "diagnostics": {},
        }

        with patch.object(app, "evaluate_business_situation", return_value=forced_profile):
            diagnostics, _, _ = _record_business(CONTENT_REQUEST, route=route)

        final_reply = build_general_direct_response(ANALYTICAL_COST)
        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertEqual(diagnostics["business_reasoning_summary"], "forced_shadow_profile")
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), final_reply)
        self.assertNotIn("Raise price now.", final_reply)

    def test_business_situation_does_not_override_evidence_gap_diagnostics(self):
        session_state = {"conversation_reset_diagnostics": {}}
        evidence = _record_evidence(
            "Draft a post.",
            route={"business_workflow": {"required_fields": ["customer_segment"], "collected_fields": {}}},
            session_state=session_state,
        )
        before = copy.deepcopy(session_state["last_evidence_gap_diagnostics"])
        business, _, _ = _record_business(
            "Draft a post.",
            route={},
            session_state=session_state,
            evidence_gap_profile=evidence["evidence_gap_profile"],
        )

        self.assertStableBusinessSituationDiagnostics(business)
        self.assertEqual(session_state["last_evidence_gap_diagnostics"], before)
        self.assertEqual(session_state["last_evidence_gap_diagnostics"]["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertTrue(session_state["last_evidence_gap_diagnostics"]["evidence_gap_shadow_mode"])

    def test_business_situation_does_not_override_response_authority_diagnostics(self):
        route = build_task_route({}, CONTENT_REQUEST)
        session_state = {"conversation_reset_diagnostics": {}}
        authority = _record_authority(CONTENT_REQUEST, route=route, session_state=session_state)
        before = copy.deepcopy(session_state["last_response_authority_diagnostics"])
        business, _, _ = _record_business(CONTENT_REQUEST, route=route, session_state=session_state)

        self.assertStableBusinessSituationDiagnostics(business)
        self.assertEqual(session_state["last_response_authority_diagnostics"], before)
        self.assertTrue(authority["response_authority_shadow_mode"])
        self.assertIn(authority["response_authority_mode"], {LLM_ASSISTED_RESPONSE, START_WORKFLOW})

    def test_direct_analysis_and_semantic_correction_remain_direct(self):
        analytical_route = build_task_route({}, ANALYTICAL_COST)
        analytical_reply = build_general_direct_response(ANALYTICAL_COST)
        business, _, _ = _record_business(ANALYTICAL_COST, route=analytical_route)
        authority = _record_authority(ANALYTICAL_COST, route=analytical_route)

        correction_route = build_task_route({}, CORRECTION_COST)
        correction_reply = build_general_direct_response(CORRECTION_COST)
        correction_authority = _record_authority(
            CORRECTION_COST,
            route=correction_route,
            semantic_correction_detected=True,
        )

        self.assertStableBusinessSituationDiagnostics(business)
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
        diagnostics, _, _ = _record_business(
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

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("business_situation_type", assistant_messages[0]["content"])

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
        diagnostics, _, _ = _record_business(
            COMPONENT_TOTAL,
            route=route,
            active_workflow={**state, "workflow_status": "completed"},
        )

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(visible, EXPECTED_COMPONENT)
        self.assertEqual(reply.get("reply"), EXPECTED_COMPONENT)
        self.assertTrue(stop["render_result_only"])
        self.assertFalse(stop["append_question_allowed"])
        self.assertNotIn("business_situation_type", reply.get("reply") or "")


if __name__ == "__main__":
    unittest.main()
