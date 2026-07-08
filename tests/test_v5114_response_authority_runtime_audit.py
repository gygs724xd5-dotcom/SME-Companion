import unittest
from unittest.mock import patch

import app
from brain.response_authority import (
    CONTINUE_WORKFLOW,
    DIRECT_BUSINESS_ANALYSIS,
    LLM_ASSISTED_RESPONSE,
    RESET_ACKNOWLEDGEMENT,
)


STABLE_AUTHORITY_DIAGNOSTIC_KEYS = (
    "response_authority_decision",
    "response_authority_mode",
    "response_authority_reason",
    "response_authority_workflow_allowed",
    "response_authority_shadow_mode",
)


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


class V5114ResponseAuthorityRuntimeAuditTest(unittest.TestCase):
    def assertStableAuthorityDiagnostics(self, diagnostics):
        for key in STABLE_AUTHORITY_DIAGNOSTIC_KEYS:
            self.assertIn(key, diagnostics)
        self.assertTrue(diagnostics["response_authority_shadow_mode"])
        self.assertIsInstance(diagnostics["response_authority_decision"], dict)
        self.assertEqual(
            diagnostics["response_authority_mode"],
            diagnostics["response_authority_decision"].get("response_mode"),
        )
        self.assertEqual(
            diagnostics["response_authority_reason"],
            diagnostics["response_authority_decision"].get("reason"),
        )
        self.assertEqual(
            diagnostics["response_authority_workflow_allowed"],
            bool(diagnostics["response_authority_decision"].get("workflow_allowed")),
        )

    def assertDeveloperMirrorMatches(self, diagnostics, developer_updates):
        for key in STABLE_AUTHORITY_DIAGNOSTIC_KEYS:
            self.assertIn(key, developer_updates)
            self.assertEqual(developer_updates[key], diagnostics[key])

    def test_reset_path_records_stable_shadow_diagnostics(self):
        diagnostics, developer_updates, session_state = _record_shadow(
            "",
            session_state={"conversation_reset_diagnostics": {"conversation_reset_applied": True}},
            reset_boundary_active=True,
            explicit_workflow_intent=False,
        )

        self.assertStableAuthorityDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["response_authority_mode"], RESET_ACKNOWLEDGEMENT)
        self.assertFalse(diagnostics["response_authority_workflow_allowed"])
        self.assertEqual(session_state["last_response_authority_diagnostics"], diagnostics)

    def test_locked_workflow_path_records_stable_shadow_diagnostics(self):
        active_workflow = {
            "workflow_id": "COST_CALCULATION",
            "workflow_status": "collecting",
            "collected_fields": {"unit_cost": 35},
        }

        diagnostics, developer_updates, _ = _record_shadow(
            "100 pieces",
            active_workflow=active_workflow,
            explicit_workflow_intent=True,
        )

        self.assertStableAuthorityDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["response_authority_mode"], CONTINUE_WORKFLOW)
        self.assertTrue(diagnostics["response_authority_workflow_allowed"])

    def test_normal_planner_path_records_stable_shadow_diagnostics(self):
        route = {
            "business_intent_entities": {
                "extracted_entities": {"analytical_statement_detected": True},
            },
            "business_workflow": {"workflow_action": None},
        }

        diagnostics, developer_updates, _ = _record_shadow(
            "My cost increased from 30 to 40 baht.",
            route=route,
        )

        self.assertStableAuthorityDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(diagnostics["response_authority_workflow_allowed"])

    def test_fail_closed_path_records_stable_non_authoritative_diagnostics(self):
        expected_reply = "direct reply is selected outside response authority"

        with patch.object(app, "decide_response_authority", side_effect=RuntimeError("boom")):
            diagnostics, developer_updates, _ = _record_shadow(
                "hello",
                route={"malformed": object()},
            )

        self.assertStableAuthorityDiagnostics(diagnostics)
        self.assertDeveloperMirrorMatches(diagnostics, developer_updates)
        self.assertEqual(diagnostics["response_authority_mode"], LLM_ASSISTED_RESPONSE)
        self.assertEqual(diagnostics["response_authority_reason"], "authority_shadow_error")
        self.assertFalse(diagnostics["response_authority_workflow_allowed"])
        self.assertEqual(expected_reply, "direct reply is selected outside response authority")


if __name__ == "__main__":
    unittest.main()
