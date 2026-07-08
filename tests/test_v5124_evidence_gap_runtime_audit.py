import unittest
from unittest.mock import patch

import app
from brain.evidence_gap import MISSING_REQUIRED_FIELD, NO_GAP, USER_CONFIRMATION_GAP, WORKFLOW_REQUIREMENT_GAP
from brain.general_response_router import build_general_direct_response
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS
from brain.response_commit_boundary import commit_response_boundary
from brain.workflow_reply_builder import build_workflow_reply
from brain.workflow_state_machine import update_workflow_state


ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
INCOMPLETE_COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"

STABLE_EVIDENCE_DIAGNOSTIC_KEYS = (
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


class V5124EvidenceGapRuntimeAuditTest(unittest.TestCase):
    def assertStableEvidenceDiagnostics(self, diagnostics):
        for key in STABLE_EVIDENCE_DIAGNOSTIC_KEYS:
            self.assertIn(key, diagnostics)
        profile = diagnostics["evidence_gap_profile"]
        self.assertIsInstance(profile, dict)
        self.assertTrue(diagnostics["evidence_gap_shadow_mode"])
        self.assertEqual(diagnostics["evidence_gap_detected"], bool(profile.get("gap_detected")))
        self.assertEqual(diagnostics["evidence_gap_type"], profile.get("gap_type"))
        self.assertEqual(diagnostics["evidence_missing_fields"], list(profile.get("missing_fields") or []))
        self.assertEqual(diagnostics["evidence_conflicting_fields"], list(profile.get("conflicting_fields") or []))
        self.assertEqual(diagnostics["evidence_smallest_next_question"], profile.get("smallest_next_question"))
        self.assertEqual(diagnostics["evidence_sufficient"], bool(profile.get("evidence_sufficient")))
        self.assertEqual(
            diagnostics["evidence_can_answer_with_assumptions"],
            bool(profile.get("can_answer_with_assumptions")),
        )
        self.assertEqual(diagnostics["evidence_gap_reason"], profile.get("reason"))
        self.assertEqual(diagnostics["evidence_gap_confidence"], profile.get("confidence"))

    def assertDeveloperMirrorMatches(self, diagnostics, developer_updates):
        for key in STABLE_EVIDENCE_DIAGNOSTIC_KEYS:
            self.assertIn(key, developer_updates)
            self.assertEqual(developer_updates[key], diagnostics[key])

    def test_normal_planner_path_records_stable_shadow_diagnostics(self):
        route = {
            "business_workflow": {
                "required_fields": ["customer_segment"],
                "collected_fields": {},
            }
        }

        diagnostics, developer_updates, session_state = _record_evidence("Draft a post.", route=route)

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(session_state["last_evidence_gap_diagnostics"], diagnostics)
        self.assertEqual(session_state["last_evidence_gap_profile"], diagnostics["evidence_gap_profile"])

    def test_reset_path_records_stable_shadow_diagnostics(self):
        diagnostics, developer_updates, _ = _record_evidence(
            "",
            session_state={"conversation_reset_diagnostics": {"conversation_reset_applied": True}},
            reset_boundary_active=True,
            intent_ambiguous=False,
        )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["evidence_gap_type"], NO_GAP)
        self.assertTrue(diagnostics["evidence_sufficient"])

    def test_workflow_path_records_stable_shadow_diagnostics(self):
        active_workflow = {
            "workflow_id": "COST_CALCULATION",
            "workflow_status": "collecting",
            "missing_fields": ["total_units"],
            "collected_fields": {"total_cost": 300},
        }

        diagnostics, developer_updates, _ = _record_evidence(
            INCOMPLETE_COST_PER_UNIT,
            active_workflow=active_workflow,
        )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["evidence_gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertEqual(diagnostics["evidence_missing_fields"], ["total_units"])
        self.assertFalse(diagnostics["evidence_sufficient"])

    def test_fail_closed_path_records_stable_shadow_diagnostics(self):
        with patch.object(app, "evaluate_evidence_gap", side_effect=RuntimeError("boom")):
            diagnostics, developer_updates, _ = _record_evidence(
                ANALYTICAL_COST,
                route={"business_workflow": object()},
                app_state={"developer": object()},
            )

        self.assertStableEvidenceDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["evidence_gap_type"], USER_CONFIRMATION_GAP)
        self.assertEqual(diagnostics["evidence_gap_reason"], "evidence_gap_shadow_error")
        self.assertFalse(diagnostics["evidence_sufficient"])
        self.assertIn("evidence_gap_error", diagnostics["evidence_gap_profile"]["diagnostics"])

    def test_evidence_gap_diagnostics_are_present_in_response_audit_without_selecting_response(self):
        session_state = {"conversation_reset_diagnostics": {}}
        evidence, _, session_state = _record_evidence(
            ANALYTICAL_COST,
            session_state=session_state,
            required_fields=["customer_segment"],
        )
        response_audit = {"response_source": "direct_response"}
        response_audit.update(session_state["last_evidence_gap_diagnostics"])
        final_reply = build_general_direct_response(ANALYTICAL_COST)

        self.assertStableEvidenceDiagnostics(evidence)
        for key in STABLE_EVIDENCE_DIAGNOSTIC_KEYS:
            self.assertIn(key, response_audit)
        self.assertEqual(response_audit["evidence_gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), final_reply)
        self.assertNotIn("evidence_gap_type", final_reply)
        self.assertNotIn(response_audit["evidence_smallest_next_question"], final_reply)

    def test_evidence_gap_does_not_override_response_authority_shadow_diagnostics(self):
        route = {
            "business_intent_entities": {
                "extracted_entities": {"analytical_statement_detected": True},
            },
            "business_workflow": {"workflow_action": None},
        }
        session_state = {"conversation_reset_diagnostics": {}}
        evidence, _, _ = _record_evidence(
            ANALYTICAL_COST,
            route=route,
            session_state=session_state,
            required_fields=["customer_segment"],
        )
        authority, _, _ = _record_authority(
            ANALYTICAL_COST,
            route=route,
            session_state=session_state,
        )

        self.assertStableEvidenceDiagnostics(evidence)
        self.assertTrue(authority["response_authority_shadow_mode"])
        self.assertEqual(authority["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertNotEqual(authority["response_authority_mode"], evidence["evidence_gap_type"])
        self.assertEqual(session_state["last_response_authority_diagnostics"], authority)
        self.assertEqual(session_state["last_evidence_gap_diagnostics"], evidence)

    def test_evidence_gap_does_not_force_clarification_or_workflow_continuation(self):
        state, _ = update_workflow_state({}, INCOMPLETE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)
        evidence, _, _ = _record_evidence(
            INCOMPLETE_COST_PER_UNIT,
            active_workflow={**state, "workflow_status": "collecting"},
        )

        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(evidence["evidence_gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertNotEqual(reply.get("reply"), evidence["evidence_smallest_next_question"])
        self.assertNotIn("evidence_gap_type", reply.get("reply") or "")

    def test_commit_boundary_output_shape_is_unchanged_by_evidence_gap_diagnostics(self):
        baseline = commit_response_boundary(
            session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
            application_state={"conversation": {"conversation_memory": {}}},
            final_reply=EXPECTED_COMPONENT,
            intent="cost_calculation",
            workflow="COST_CALCULATION",
            response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
            assistant_message={"role": "assistant", "show_business_insights": False},
        )
        evidence, _, _ = _record_evidence(COMPONENT_TOTAL)
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
        self.assertStableEvidenceDiagnostics(evidence)
        self.assertEqual(set(result.keys()), set(baseline.keys()))
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("evidence_gap_type", assistant_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
