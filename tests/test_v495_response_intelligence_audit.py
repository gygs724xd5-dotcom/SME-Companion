import unittest

from brain.task_router import developer_diagnostics
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import completed_workflow_followup_reply, prepare_content_collection_state
from brain.workflow_state_machine import update_workflow_state


class V495ResponseIntelligenceAuditTest(unittest.TestCase):
    def test_completed_workflow_followup_builder_is_disabled(self):
        completed = {
            "workflow_id": WORKFLOW_CONTENT_PLAN,
            "workflow_name": "content_creation",
            "collected_fields": {"product": "Thai tea"},
        }

        self.assertIsNone(completed_workflow_followup_reply(completed, "another version"))

    def test_completed_workflow_followup_detection_is_diagnostics_only(self):
        app_state = {
            "store": {
                "last_completed_workflow": {
                    "workflow_id": WORKFLOW_COST_CALCULATION,
                    "collected_fields": {"unit_cost": 35, "total_units": 100},
                }
            }
        }

        decision = classify_completed_workflow_followup(app_state, "profit 30%")

        self.assertFalse(decision["reuse_completed_workflow"])
        self.assertIsNone(decision["workflow_followup_mode"])
        self.assertEqual(decision["followup_chain"], [])
        self.assertEqual(decision["completed_workflow"]["workflow_id"], WORKFLOW_COST_CALCULATION)

    def test_promotion_is_optional_for_content_generation(self):
        state, _ = update_workflow_state({}, "Create Post", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)
        state, _ = update_workflow_state(state, "Thai tea", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)
        state, _ = update_workflow_state(state, "office workers", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)

        self.assertTrue(state["is_ready"])
        self.assertEqual(state["missing_fields"], [])

    def test_response_diagnostics_do_not_mark_completed_workflow_reuse_by_default(self):
        diagnostics = developer_diagnostics(
            {
                "response_type": "content_variant",
                "response_source": "planner_first_response",
                "reuse_completed_workflow": False,
            }
        )

        self.assertEqual(diagnostics["response_source"], "planner_first_response")
        self.assertFalse(diagnostics["reuse_completed_workflow"])


if __name__ == "__main__":
    unittest.main()
