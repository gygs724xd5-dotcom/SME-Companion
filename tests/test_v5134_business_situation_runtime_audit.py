import copy
import unittest
from unittest.mock import patch

import app
from brain.business_situation import (
    ANALYTICAL,
    COST,
    COST_CHANGE,
    GENERAL,
    NEUTRAL,
    NO_BUSINESS_SITUATION,
    NONE,
    OWNER_ADVISORY,
    PLANNING_DECISION,
)
from brain.evidence_gap import MISSING_REQUIRED_FIELD
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, LLM_ASSISTED_RESPONSE, START_WORKFLOW
from brain.response_commit_boundary import commit_response_boundary
from brain.workflow_reply_builder import build_workflow_reply
from brain.workflow_state_machine import update_workflow_state


ANALYTICAL_COST = "My supplier cost increased from 30 to 40 baht."
CONTENT_REQUEST = "Please write a sales post for Thai tea."
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

STABLE_AUTHORITY_KEYS = (
    "response_authority_decision",
    "response_authority_mode",
    "response_authority_reason",
    "response_authority_workflow_allowed",
    "response_authority_shadow_mode",
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


class V5134BusinessSituationRuntimeAuditTest(unittest.TestCase):
    def assertStableBusinessSituationDiagnostics(self, diagnostics):
        for key in STABLE_BUSINESS_SITUATION_KEYS:
            self.assertIn(key, diagnostics)
        profile = diagnostics["business_situation_profile"]
        self.assertIsInstance(profile, dict)
        self.assertTrue(diagnostics["business_situation_shadow_mode"])
        self.assertEqual(diagnostics["business_situation_detected"], bool(profile.get("situation_detected")))
        self.assertEqual(diagnostics["business_situation_type"], profile.get("situation_type"))
        self.assertEqual(diagnostics["business_domain"], profile.get("business_domain"))
        self.assertEqual(diagnostics["perspective_stance"], profile.get("perspective_stance"))
        self.assertEqual(diagnostics["business_risk_level"], profile.get("risk_level"))
        self.assertEqual(diagnostics["business_opportunity_level"], profile.get("opportunity_level"))
        self.assertEqual(diagnostics["business_urgency_level"], profile.get("urgency_level"))
        self.assertEqual(diagnostics["owner_attention"], profile.get("owner_attention"))
        self.assertEqual(diagnostics["recommended_response_posture"], profile.get("recommended_response_posture"))
        self.assertEqual(diagnostics["business_reasoning_summary"], profile.get("reasoning_summary"))
        self.assertEqual(diagnostics["business_situation_confidence"], profile.get("confidence"))

    def assertDeveloperMirrorMatches(self, diagnostics, developer_updates):
        for key in STABLE_BUSINESS_SITUATION_KEYS:
            self.assertIn(key, developer_updates)
            self.assertEqual(developer_updates[key], diagnostics[key])

    def test_normal_planner_path_records_stable_shadow_diagnostics(self):
        route = {
            "business_context": {"business_type": "bakery", "current_message_intent": "cost_calculation"},
            "intent_resolution": {"resolved_intent": "cost_calculation"},
            "business_intent_entities": {
                "extracted_entities": {"analytical_statement_detected": True, "cost": 40},
            },
        }

        diagnostics, developer_updates, session_state = _record_business(ANALYTICAL_COST, route=route)

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["business_situation_type"], COST_CHANGE)
        self.assertEqual(diagnostics["business_domain"], COST)
        self.assertEqual(diagnostics["perspective_stance"], ANALYTICAL)
        self.assertEqual(session_state["last_business_situation_diagnostics"], diagnostics)
        self.assertEqual(session_state["last_business_situation_profile"], diagnostics["business_situation_profile"])

    def test_reset_path_records_stable_shadow_diagnostics_without_changing_reset_behavior(self):
        diagnostics, developer_updates, _ = _record_business(
            "",
            session_state={"conversation_reset_diagnostics": {"conversation_reset_applied": True}},
            reset_boundary_active=True,
        )

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["business_situation_type"], NO_BUSINESS_SITUATION)
        self.assertEqual(diagnostics["business_domain"], GENERAL)
        self.assertEqual(diagnostics["perspective_stance"], NEUTRAL)
        self.assertFalse(diagnostics["business_situation_detected"])

    def test_workflow_path_records_stable_shadow_diagnostics_without_forcing_continuation(self):
        active_workflow = {
            "workflow_id": "COST_CALCULATION",
            "workflow_status": "collecting",
            "missing_fields": ["total_units"],
            "collected_fields": {"total_cost": 300},
        }
        state, _ = update_workflow_state({}, "total cost is 300", detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)

        diagnostics, developer_updates, _ = _record_business(
            "total cost is 300",
            active_workflow=active_workflow,
        )

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertTrue(diagnostics["business_situation_shadow_mode"])
        self.assertNotIn("business_situation_type", reply.get("reply") or "")
        self.assertNotEqual(reply.get("reply"), diagnostics.get("owner_attention"))

    def test_fail_closed_path_records_stable_non_authoritative_diagnostics(self):
        expected_reply = build_general_direct_response(ANALYTICAL_COST)

        with patch.object(app, "evaluate_business_situation", side_effect=RuntimeError("boom")):
            diagnostics, developer_updates, _ = _record_business(
                ANALYTICAL_COST,
                route={"business_context": object()},
                app_state={"developer": object()},
            )

        self.assertStableBusinessSituationDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["business_situation_type"], NO_BUSINESS_SITUATION)
        self.assertEqual(diagnostics["business_domain"], GENERAL)
        self.assertEqual(diagnostics["perspective_stance"], NEUTRAL)
        self.assertEqual(diagnostics["business_risk_level"], NONE)
        self.assertEqual(diagnostics["business_reasoning_summary"], "business_situation_shadow_error")
        self.assertIn("business_situation_error", diagnostics["business_situation_profile"]["diagnostics"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)

    def test_business_situation_diagnostics_are_present_in_response_audit_and_debug_state(self):
        session_state = {
            "conversation_reset_diagnostics": {},
            "last_task_route": {},
            "conversation_state": {},
            "chat_history": [],
            "developer_mode": False,
        }
        business, _, session_state = _record_business(
            ANALYTICAL_COST,
            session_state=session_state,
        )
        developer_updates = {}

        def update_section(section, values):
            if section == "developer":
                developer_updates.update(values or {})
            return {}

        with patch.object(app.st, "session_state", session_state), \
            patch.object(app, "_update_application_section", side_effect=update_section):
            trace = app._finalize_ai_pipeline_debug_trace(
                {"workflow": {}, "planner": {}, "reasoning": {}},
                "direct_conversation_response",
                "final reply selected before diagnostics",
                {},
            )

        self.assertStableBusinessSituationDiagnostics(business)
        self.assertIsNotNone(trace)
        for key in STABLE_BUSINESS_SITUATION_KEYS:
            self.assertIn(key, trace["response_audit"])
            self.assertEqual(trace["response_audit"][key], business[key])
            self.assertIn(key, trace)
            self.assertEqual(trace[key], business[key])
            self.assertIn(key, session_state["last_response_audit"])
            self.assertIn(key, developer_updates)
        self.assertEqual(trace["final_response_preview"], "final reply selected before diagnostics")
        self.assertNotIn("business_situation_type", trace["final_response_preview"])

    def test_business_situation_does_not_override_evidence_gap_or_response_authority(self):
        route = {
            "business_workflow": {"required_fields": ["customer_segment"], "collected_fields": {}},
        }
        session_state = {"conversation_reset_diagnostics": {}}
        evidence, _, _ = _record_evidence(CONTENT_REQUEST, route=route, session_state=session_state)
        authority, _, _ = _record_authority(CONTENT_REQUEST, route=route, session_state=session_state)
        evidence_before = copy.deepcopy(session_state["last_evidence_gap_diagnostics"])
        authority_before = copy.deepcopy(session_state["last_response_authority_diagnostics"])
        business, _, _ = _record_business(
            CONTENT_REQUEST,
            route=route,
            session_state=session_state,
            evidence_gap_profile=evidence["evidence_gap_profile"],
        )

        self.assertStableBusinessSituationDiagnostics(business)
        for key in STABLE_EVIDENCE_KEYS:
            self.assertIn(key, evidence)
        for key in STABLE_AUTHORITY_KEYS:
            self.assertIn(key, authority)
        self.assertEqual(session_state["last_evidence_gap_diagnostics"], evidence_before)
        self.assertEqual(session_state["last_response_authority_diagnostics"], authority_before)
        self.assertEqual(evidence["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertIn(authority["response_authority_mode"], {LLM_ASSISTED_RESPONSE, START_WORKFLOW})
        self.assertNotEqual(business["business_situation_type"], evidence["evidence_gap_type"])
        self.assertNotEqual(business["business_situation_type"], authority["response_authority_mode"])

    def test_shadow_profile_cannot_rewrite_final_response_or_commit_boundary_shape(self):
        forced_profile = {
            "situation_detected": True,
            "situation_type": PLANNING_DECISION,
            "business_domain": GENERAL,
            "perspective_stance": OWNER_ADVISORY,
            "risk_level": "HIGH",
            "opportunity_level": "HIGH",
            "urgency_level": "HIGH",
            "owner_attention": "Add owner-advisory text and continue the workflow.",
            "recommended_response_posture": OWNER_ADVISORY,
            "reasoning_summary": "forced_non_authoritative_shadow_profile",
            "confidence": 0.99,
            "assumptions": [],
            "diagnostics": {},
        }
        baseline = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )

        with patch.object(app, "evaluate_business_situation", return_value=forced_profile):
            business, _, _ = _record_business(COMPONENT_TOTAL)

        result = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]

        self.assertStableBusinessSituationDiagnostics(business)
        self.assertEqual(set(result.keys()), set(baseline.keys()))
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("owner-advisory", assistant_messages[0]["content"])
        self.assertNotIn("business_situation_type", assistant_messages[0]["content"])
        self.assertNotIn("business_situation_profile", str(result.get("response_metadata") or {}))

    def test_business_situation_does_not_change_response_authority_decision(self):
        route = {
            "business_intent_entities": {
                "extracted_entities": {"analytical_statement_detected": True},
            },
            "business_workflow": {"workflow_action": None},
        }
        session_state = {"conversation_reset_diagnostics": {}}
        authority_before, _, _ = _record_authority(ANALYTICAL_COST, route=route, session_state=session_state)
        business, _, _ = _record_business(ANALYTICAL_COST, route=route, session_state=session_state)
        authority_after, _, _ = _record_authority(ANALYTICAL_COST, route=route, session_state=session_state)

        self.assertStableBusinessSituationDiagnostics(business)
        self.assertEqual(authority_before["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertEqual(authority_after["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(authority_after["response_authority_workflow_allowed"])


if __name__ == "__main__":
    unittest.main()
