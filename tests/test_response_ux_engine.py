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


FORBIDDEN_HEADINGS = ["สิ่งที่ผมเข้าใจ", "วิเคราะห์", "คำแนะนำ", "ขั้นตอนถัดไป"]


class ResponseUxEngineTest(unittest.TestCase):
    def assert_no_analysis_blocks(self, reply: str):
        for heading in FORBIDDEN_HEADINGS:
            self.assertNotIn(heading, reply)

    def test_create_post_collects_one_field_at_a_time_then_generates(self):
        workflow_state, _ = update_workflow_state({}, "Create Post", detected_workflow=WORKFLOW_CONTENT_PLAN)
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], ASK_NEXT_FIELD)
        self.assertEqual(reply["reply"], "อยากโปรโมตสินค้าอะไรครับ")
        self.assert_no_analysis_blocks(reply["reply"])

        workflow_state, _ = update_workflow_state(workflow_state, "ชูครีม", detected_workflow=WORKFLOW_CONTENT_PLAN)
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], ASK_NEXT_FIELD)
        self.assertEqual(reply["reply"], "ลูกค้าหลักเป็นใครครับ")
        self.assert_no_analysis_blocks(reply["reply"])

        workflow_state, _ = update_workflow_state(workflow_state, "วัยรุ่น", detected_workflow=WORKFLOW_CONTENT_PLAN)
        workflow_state = prepare_content_collection_state(workflow_state)
        reply = build_workflow_reply(workflow_state)

        self.assertEqual(reply["response_mode"], ASK_NEXT_FIELD)
        self.assertEqual(reply["reply"], "มีโปรโมชั่นอะไรอยู่ไหมครับ")
        self.assert_no_analysis_blocks(reply["reply"])

        workflow_state, _ = update_workflow_state(workflow_state, "ลด10%", detected_workflow=WORKFLOW_CONTENT_PLAN)
        workflow_state = prepare_content_collection_state(workflow_state)
        generated = "โพสต์สำหรับชูครีม\n\nวัยรุ่นสายหวานห้ามพลาด ชูครีมลด 10% วันนี้"
        reply = build_workflow_reply(workflow_state, generated_reply=generated)

        self.assertEqual(reply["response_mode"], GENERATE_OUTPUT)
        self.assertIn("โพสต์สำหรับชูครีม", reply["reply"])
        self.assert_no_analysis_blocks(reply["reply"])

    def test_cost_calculation_response_mode_changes(self):
        missing_state = new_workflow_state(WORKFLOW_COST_CALCULATION)
        ready_state = {
            **missing_state,
            "collected_fields": {"ingredients_costs": [{"name": "แป้ง", "cost": 40}], "total_units": 10},
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
                "product": "ชูครีม",
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
