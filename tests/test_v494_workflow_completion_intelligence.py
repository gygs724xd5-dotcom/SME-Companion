import unittest

from brain.conversation_manager import (
    active_workflow_state,
    complete_workflow,
    continue_workflow,
    developer_diagnostics as os_diagnostics,
    planner_locked,
    route_quick_action,
)
from brain.conversation_priority_engine import classify_message_priority
from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_lifecycle import (
    classify_completed_workflow_followup,
)
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import prepare_content_collection_state
from brain.workflow_state_machine import update_workflow_state


class V494WorkflowCompletionIntelligenceTest(unittest.TestCase):
    def test_completion_gate_generates_content_after_target_customer_without_promotion(self):
        state, _ = update_workflow_state({}, "Create Post", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)

        state, _ = update_workflow_state(
            state,
            "\u0e0a\u0e32\u0e44\u0e17\u0e22",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        state = prepare_content_collection_state(state)
        self.assertIn("target_customer", state["missing_fields"])

        state, _ = update_workflow_state(
            state,
            "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        state = prepare_content_collection_state(state)

        self.assertTrue(state["is_ready"])
        self.assertEqual(state["missing_fields"], [])
        self.assertEqual(state["next_action"], "generate")
        self.assertEqual(state["readiness_decision"]["reason"], "execute_before_collecting")

    def test_completed_cost_workflow_is_diagnostics_only_for_pricing_followup(self):
        app_state = {
            "store": {
                "last_completed_workflow": {
                    "workflow_id": WORKFLOW_COST_CALCULATION,
                    "workflow_name": "cost_calculation",
                    "collected_fields": {"unit_cost": 35, "total_units": 100},
                }
            }
        }
        decision = classify_completed_workflow_followup(
            app_state,
            "\u0e04\u0e27\u0e23\u0e02\u0e32\u0e22\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23\u0e14\u0e35",
        )
        self.assertFalse(decision["reuse_completed_workflow"])
        self.assertIsNone(decision["workflow_followup_mode"])
        self.assertEqual(decision["completed_workflow"]["collected_fields"]["unit_cost"], 35)
        self.assertIsNone(active_workflow_state(app_state))
        self.assertFalse(planner_locked(app_state))

    def test_variant_request_does_not_use_completed_content_workflow(self):
        app_state = {
            "store": {
                "last_completed_workflow": {
                    "workflow_id": WORKFLOW_CONTENT_PLAN,
                    "workflow_name": "content_creation",
                    "collected_fields": {
                        "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22",
                        "target_customer": "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19",
                    },
                }
            }
        }

        decision = classify_completed_workflow_followup(app_state, "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a")

        self.assertFalse(decision["reuse_completed_workflow"])
        self.assertIsNone(decision["workflow_followup_mode"])
        self.assertIsNone(decision["workflow_variant_mode"])

    def test_completed_workflow_is_released_but_diagnostics_keep_completion(self):
        app_state = {}
        route_quick_action(app_state, "cost_calculator")
        continue_workflow(
            app_state,
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 40 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 50 \u0e0a\u0e34\u0e49\u0e19",
        )
        complete_workflow(app_state)
        diagnostics = os_diagnostics(app_state)

        self.assertIsNone(active_workflow_state(app_state))
        self.assertFalse(planner_locked(app_state))
        self.assertTrue(diagnostics["Workflow Released?"])
        self.assertEqual(app_state["store"]["last_completed_workflow"]["workflow_status"], "RELEASED")

    def test_completed_workflow_intent_switch_does_not_collect_old_fields(self):
        workflow_state, _ = update_workflow_state(
            {},
            "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        workflow_state["step"] = "completed"
        workflow_state["missing_fields"] = []
        app_state = {"workflow": {"workflow_state_v2": workflow_state}}

        priority = classify_message_priority(
            "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19",
            app_state,
        )

        self.assertFalse(priority["allow_field_extraction"])
        self.assertIn(priority["classification"], {"new_intent", "workflow_switch"})

    def test_developer_diagnostics_include_completion_fields(self):
        route = build_task_route(
            {},
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19",
        )
        diagnostics = developer_diagnostics(route)

        self.assertIn("workflow_status", diagnostics)
        self.assertIn("workflow_completion_reason", diagnostics)
        self.assertIn("workflow_release_reason", diagnostics)
        self.assertIn("workflow_followup_mode", diagnostics)
        self.assertIn("workflow_variant_mode", diagnostics)
        self.assertIn("Readiness Decision", diagnostics)
        self.assertIn("Completion Decision", diagnostics)
        self.assertIn("Transition Decision", diagnostics)


if __name__ == "__main__":
    unittest.main()
