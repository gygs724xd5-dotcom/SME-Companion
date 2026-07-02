import unittest

from brain.conversation_manager import route_quick_action
from brain.task_router import build_task_route
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION


class V522WorkflowDomainIsolationTest(unittest.TestCase):
    def test_marketing_request_releases_active_cost_workflow_state(self):
        state = {
            "business_memory": {"customer_segments": ["office workers"]},
            "store": {"store_id": "store-1", "name": "Demo Store"},
            "product_catalog": {"items": [{"name": "Thai tea"}]},
            "conversation": {
                "workflow_cache": {"next_question": "stale"},
                "pending_workflow": WORKFLOW_COST_CALCULATION,
                "missing_entities": ["cost", "quantity"],
                "next_question": "ต้นทุนต่อชิ้นกี่บาทครับ",
            },
        }
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, "marketing content for Thai tea")
        workflow = route["business_workflow"]
        os_state = state["conversation"]["conversation_os"]

        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_CONTENT_PLAN)
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), WORKFLOW_CONTENT_PLAN)
        self.assertTrue(workflow.get("workflow_domain_boundary_applied"))
        self.assertEqual(workflow.get("previous_workflow_id"), WORKFLOW_COST_CALCULATION)
        self.assertEqual(workflow.get("next_workflow_id"), WORKFLOW_CONTENT_PLAN)
        self.assertNotIn("cost", workflow.get("missing_entities") or [])
        self.assertNotIn("quantity", workflow.get("missing_entities") or [])
        self.assertNotEqual(workflow.get("next_question"), "ต้นทุนต่อชิ้นกี่บาทครับ")

        self.assertIsNone(os_state.get("active_workflow_id"))
        self.assertEqual(os_state.get("workflow_states"), {})
        self.assertEqual(os_state.get("conversation_stack"), [])
        self.assertIsNone(state["conversation"].get("pending_workflow"))
        self.assertNotIn("next_question", state["conversation"])
        self.assertEqual(state["business_memory"], {"customer_segments": ["office workers"]})
        self.assertEqual(state["store"], {"store_id": "store-1", "name": "Demo Store"})
        self.assertEqual(state["product_catalog"], {"items": [{"name": "Thai tea"}]})

    def test_completed_workflow_context_does_not_skip_planner_or_rebuild_workflow(self):
        state = {
            "business_memory": {
                "completed_workflows": [
                    {
                        "workflow_id": WORKFLOW_CONTENT_PLAN,
                        "collected_fields": {"product": "Thai tea"},
                    }
                ]
            },
            "conversation": {
                "missing_entities": ["product_or_business_type"],
                "next_question": "stale content question",
            },
        }

        route = build_task_route(state, "ต้นทุนรวม 200 ทำได้ 100 ชิ้น")
        workflow = route["business_workflow"]

        self.assertFalse((route.get("planner_output") or {}).get("planner_skipped"))
        self.assertEqual(route["planner_output"]["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), WORKFLOW_COST_CALCULATION)
        self.assertNotEqual(workflow.get("next_question"), "stale content question")


if __name__ == "__main__":
    unittest.main()
