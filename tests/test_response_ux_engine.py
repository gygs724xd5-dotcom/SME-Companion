import unittest

from brain.response_mode_engine import (
    ASK_NEXT_FIELD,
    BUSINESS_CONSULTING,
    GENERATE_OUTPUT,
    determine_response_mode,
)
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.workflow_reply_builder import build_workflow_reply, prepare_content_collection_state
from brain.workflow_state_machine import new_workflow_state, update_workflow_state


FORBIDDEN_HEADINGS = [
    "\u0e2a\u0e34\u0e48\u0e07\u0e17\u0e35\u0e48\u0e1c\u0e21\u0e40\u0e02\u0e49\u0e32\u0e43\u0e08",
    "\u0e27\u0e34\u0e40\u0e04\u0e23\u0e32\u0e30\u0e2b\u0e4c",
    "\u0e04\u0e33\u0e41\u0e19\u0e30\u0e19\u0e33",
    "\u0e02\u0e31\u0e49\u0e19\u0e15\u0e2d\u0e19\u0e16\u0e31\u0e14\u0e44\u0e1b",
]


class ResponseUxEngineTest(unittest.TestCase):
    def assert_no_analysis_blocks(self, reply: str):
        for heading in FORBIDDEN_HEADINGS:
            self.assertNotIn(heading, reply)

    def test_create_post_collects_until_executable_then_generates(self):
        workflow_state, _ = update_workflow_state({}, "Create Post", detected_workflow=WORKFLOW_CONTENT_PLAN)
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], ASK_NEXT_FIELD)
        self.assert_no_analysis_blocks(reply["reply"])

        workflow_state, _ = update_workflow_state(
            workflow_state,
            "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], ASK_NEXT_FIELD)
        self.assert_no_analysis_blocks(reply["reply"])

        workflow_state, _ = update_workflow_state(
            workflow_state,
            "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], GENERATE_OUTPUT)
        self.assertFalse(workflow_state["missing_fields"])
        self.assert_no_analysis_blocks(reply["reply"])

    def test_cost_calculation_response_mode_changes(self):
        missing_state = new_workflow_state(WORKFLOW_COST_CALCULATION)
        ready_state = {
            **missing_state,
            "collected_fields": {"ingredients_costs": [{"name": "\u0e41\u0e1b\u0e49\u0e07", "cost": 40}], "total_units": 10},
            "missing_fields": [],
            "is_ready": True,
            "next_action": "generate",
        }

        self.assertEqual(determine_response_mode(workflow_state=missing_state).mode, ASK_NEXT_FIELD)
        self.assertEqual(determine_response_mode(workflow_state=ready_state).mode, GENERATE_OUTPUT)

    def test_business_analysis_uses_consulting_mode(self):
        decision = determine_response_mode(planner={"task_type": "Business Analysis", "workflow": WORKFLOW_DASHBOARD_REQUEST})

        self.assertEqual(decision.mode, BUSINESS_CONSULTING)

    def test_sales_planning_collects_then_generates(self):
        missing_state = new_workflow_state(WORKFLOW_SALES_PLAN_7_DAY)
        ready_state = {
            **missing_state,
            "collected_fields": {
                "product": "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21",
                "daily_capacity": 30,
                "sales_channel": "Facebook",
            },
            "missing_fields": [],
            "is_ready": True,
            "next_action": "generate",
        }

        self.assertEqual(determine_response_mode(workflow_state=missing_state).mode, ASK_NEXT_FIELD)
        self.assertEqual(determine_response_mode(workflow_state=ready_state).mode, GENERATE_OUTPUT)

    def test_receipt_ocr_routes_to_output_mode(self):
        receipt_state = {
            "workflow": WORKFLOW_RECEIPT_CAPTURE,
            "step": "waiting_for_upload",
            "missing_fields": [],
            "is_ready": True,
            "next_action": "route",
        }

        self.assertEqual(determine_response_mode(workflow_state=receipt_state).mode, GENERATE_OUTPUT)


if __name__ == "__main__":
    unittest.main()
