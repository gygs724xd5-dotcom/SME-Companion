import unittest

from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import completed_workflow_followup_reply


class V496ConversationIntelligenceTest(unittest.TestCase):
    def _content_completed(self):
        return {
            "workflow_id": WORKFLOW_CONTENT_PLAN,
            "workflow_name": "content_creation",
            "collected_fields": {"product": "Thai tea", "target_customer": "office workers"},
        }

    def _cost_completed(self):
        return {
            "workflow_id": WORKFLOW_COST_CALCULATION,
            "workflow_name": "cost_calculation",
            "collected_fields": {"unit_cost": 35, "total_units": 100},
        }

    def test_variant_request_does_not_reuse_completed_content(self):
        app_state = {"store": {"last_completed_workflow": self._content_completed()}}

        decision = classify_completed_workflow_followup(app_state, "another version")

        self.assertFalse(decision["reuse_completed_workflow"])
        self.assertIsNone(decision["workflow_variant_mode"])
        self.assertIsNone(completed_workflow_followup_reply(decision["completed_workflow"], "another version"))

    def test_pricing_followup_does_not_reuse_completed_cost(self):
        app_state = {"store": {"last_completed_workflow": self._cost_completed()}}

        decision = classify_completed_workflow_followup(app_state, "sell 45?")

        self.assertFalse(decision["reuse_completed_workflow"])
        self.assertEqual(decision["followup_chain"], [])
        self.assertIsNone(completed_workflow_followup_reply(decision["completed_workflow"], "sell 45?"))

    def test_completed_context_does_not_skip_planner(self):
        app_state = {"store": {"last_completed_workflow": self._content_completed()}}

        route = build_task_route(app_state, "cost is 35 for 100 pieces")

        self.assertFalse(route.get("planner_skipped", False))
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_COST_CALCULATION)

    def test_completed_workflow_reuse_diagnostics_are_false(self):
        diagnostics = developer_diagnostics(
            {
                "response_type": "assistant_response",
                "response_source": "planner_first_response",
            }
        )

        self.assertFalse(diagnostics["reuse_completed_workflow"])
        self.assertFalse(diagnostics["planner_skipped"])
        self.assertIsNone(diagnostics["continuation_mode"])


if __name__ == "__main__":
    unittest.main()
