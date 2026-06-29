import unittest

from brain.conversation_manager import (
    active_workflow_state,
    complete_workflow,
    continue_workflow,
    planner_locked,
    route_quick_action,
)
from brain.task_router import build_task_route
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_DASHBOARD_REQUEST,
    WORKFLOW_RECEIPT_CAPTURE,
)


class ConversationOSTest(unittest.TestCase):
    def test_create_post_continues_and_completes(self):
        state = {}

        started = route_quick_action(state, "create_post")
        self.assertTrue(started["handled"])
        self.assertTrue(planner_locked(state))
        self.assertEqual(active_workflow_state(state)["workflow_id"], WORKFLOW_CONTENT_PLAN)

        continued = continue_workflow(state, "ขายกาแฟเย็น")
        self.assertTrue(continued["handled"])
        self.assertFalse(continued["workflow_state"]["missing_fields"])

        complete_workflow(state)
        self.assertFalse(planner_locked(state))
        self.assertIsNone(active_workflow_state(state))
        self.assertEqual(state["store"]["last_completed_workflow"]["workflow_id"], WORKFLOW_CONTENT_PLAN)
        self.assertEqual(state["business_memory"]["completed_workflows"][-1]["workflow_id"], WORKFLOW_CONTENT_PLAN)

    def test_create_post_accepts_bare_product_answer_once(self):
        state = {}

        route_quick_action(state, "create_post")
        continued = continue_workflow(state, "Choux Cream")

        self.assertTrue(continued["handled"])
        self.assertEqual(continued["workflow_state"]["collected_fields"]["product"], "Choux Cream")
        self.assertNotIn("product_or_business_type", continued["workflow_state"]["missing_fields"])
        self.assertFalse(continued["workflow_state"]["missing_fields"])
        self.assertEqual(continued["workflow_state"]["current_step"], "ready_to_generate")

    def test_cost_calculator_collects_multiple_turns_and_completes(self):
        state = {}

        route_quick_action(state, "cost_calculator")
        first_turn = continue_workflow(state, "แป้ง 40 ไข่ 30 น้ำตาล 20")
        self.assertIn("total_units", first_turn["workflow_state"]["missing_fields"])
        self.assertTrue(planner_locked(state))

        second_turn = continue_workflow(state, "ทำได้ 10 ชิ้น")
        self.assertFalse(second_turn["workflow_state"]["missing_fields"])

        complete_workflow(state)
        self.assertFalse(planner_locked(state))

    def test_receipt_ocr_upload_flow_can_continue_to_summary(self):
        state = {}

        started = route_quick_action(state, "receipt_ocr")
        self.assertEqual(started["workflow_state"]["workflow_id"], WORKFLOW_RECEIPT_CAPTURE)
        self.assertTrue(planner_locked(state))

        continued = continue_workflow(state, "อัปโหลดบิลแล้ว")
        self.assertTrue(continued["handled"])
        complete_workflow(state)
        self.assertFalse(planner_locked(state))

    def test_business_analysis_completes_without_planner_state(self):
        state = {}

        started = route_quick_action(state, "business_analysis")
        self.assertEqual(started["workflow_state"]["workflow_id"], WORKFLOW_DASHBOARD_REQUEST)
        self.assertTrue(planner_locked(state))

        complete_workflow(state)
        self.assertFalse(planner_locked(state))

    def test_interrupt_answers_temporarily_and_resumes_workflow(self):
        state = {}

        route_quick_action(state, "cost_calculator")
        interrupted = continue_workflow(state, "ตอนนี้กี่โมง")
        self.assertFalse(interrupted["handled"])
        self.assertTrue(interrupted["resume_after_reply"])
        self.assertEqual(active_workflow_state(state)["workflow_id"], WORKFLOW_COST_CALCULATION)
        self.assertTrue(planner_locked(state))

        continued = continue_workflow(state, "แป้ง 40, ไข่ 30, ทำได้ 10 ชิ้น")
        self.assertTrue(continued["handled"])
        self.assertFalse(continued["workflow_state"]["missing_fields"])

    def test_pause_unlocks_planner_and_resume_restores_workflow(self):
        state = {}

        route_quick_action(state, "cost_calculator")
        paused = continue_workflow(state, "pause")

        self.assertTrue(paused["handled"])
        self.assertEqual(paused["event"], "paused")
        self.assertFalse(planner_locked(state))
        self.assertIsNone(active_workflow_state(state))

        resumed = continue_workflow(state, "resume")
        self.assertTrue(resumed["handled"])
        self.assertEqual(resumed["event"], "resumed")
        self.assertEqual(resumed["workflow_state"]["workflow_id"], WORKFLOW_COST_CALCULATION)
        self.assertTrue(planner_locked(state))

    def test_higher_priority_workflow_switches_from_create_post_to_receipt_ocr(self):
        state = {}

        route_quick_action(state, "create_post")
        switched = continue_workflow(state, "upload receipt")

        self.assertTrue(switched["handled"])
        self.assertEqual(switched["event"], "workflow_switched")
        self.assertEqual(switched["workflow_state"]["workflow_id"], WORKFLOW_RECEIPT_CAPTURE)
        self.assertEqual(active_workflow_state(state)["workflow_id"], WORKFLOW_RECEIPT_CAPTURE)
        self.assertTrue(planner_locked(state))

    def test_task_router_does_not_run_planner_when_workflow_active(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, "แป้ง 40")
        self.assertTrue(route["planner_locked"])
        self.assertEqual(route["planner_output"]["next_step"], "continue_active_workflow")

    def test_task_router_planner_first_still_routes_without_active_workflow(self):
        route = build_task_route({}, "สวัสดี")

        self.assertFalse(route.get("planner_locked", False))
        self.assertIn("planner_output", route)


if __name__ == "__main__":
    unittest.main()
