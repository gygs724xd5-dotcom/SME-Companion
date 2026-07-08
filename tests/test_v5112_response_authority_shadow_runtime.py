import copy
import unittest
from unittest.mock import patch

import app
from brain.response_authority import DIRECT_BUSINESS_ANALYSIS, LLM_ASSISTED_RESPONSE


class V5112ResponseAuthorityShadowRuntimeTest(unittest.TestCase):
    def test_app_records_shadow_diagnostics_without_mutating_workflow(self):
        session_state = {"conversation_reset_diagnostics": {}}
        developer_updates = {}
        active_workflow = {
            "workflow_id": "COST_CALCULATION",
            "current_step": "collecting",
            "collected_fields": {"cost": 40},
        }
        original_workflow = copy.deepcopy(active_workflow)
        route = {
            "business_intent_entities": {
                "extracted_entities": {
                    "analytical_statement_detected": True,
                },
            },
        }

        def update_section(section, values):
            if section == "developer":
                developer_updates.update(values or {})
            return {}

        with patch.object(app.st, "session_state", session_state), \
            patch.object(app, "_sync_session_to_application_state", return_value={}), \
            patch.object(app, "_update_application_section", side_effect=update_section):
            diagnostics = app._record_response_authority_shadow_decision(
                "Is this cost too high?",
                task_route=route,
                active_workflow=active_workflow,
            )

        self.assertEqual(active_workflow, original_workflow)
        self.assertTrue(diagnostics["response_authority_shadow_mode"])
        self.assertEqual(diagnostics["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertEqual(developer_updates["response_authority_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(developer_updates["response_authority_workflow_allowed"])

    def test_app_shadow_diagnostics_fail_closed_on_authority_error(self):
        session_state = {"conversation_reset_diagnostics": {}}

        with patch.object(app.st, "session_state", session_state), \
            patch.object(app, "_sync_session_to_application_state", side_effect=RuntimeError("boom")), \
            patch.object(app, "_update_application_section"):
            diagnostics = app._record_response_authority_shadow_decision("hello")

        self.assertTrue(diagnostics["response_authority_shadow_mode"])
        self.assertEqual(diagnostics["response_authority_mode"], LLM_ASSISTED_RESPONSE)
        self.assertEqual(diagnostics["response_authority_reason"], "authority_shadow_error")


if __name__ == "__main__":
    unittest.main()
