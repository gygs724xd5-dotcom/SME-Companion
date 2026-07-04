import unittest

from brain.knowledge_runtime import build_knowledge_runtime
from brain.knowledge_skill_bridge import build_knowledge_skill_bridge
from brain.task_router import build_task_route


class V591OutcomesTest(unittest.TestCase):
    def _bridge(self, route):
        return route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]

    def test_operating_capacity_visible_outcome(self):
        route = build_task_route({"conversation_memory": {"business_topic": "ขายชูครีม ทำตามออเดอร์"}}, "ตอนนี้ทำได้ 100 ชิ้น")
        bridge = self._bridge(route)
        self.assertEqual(bridge["primary_skill_candidate"]["skill_id"], "analyze_operating_capacity")
        self.assertEqual(bridge["primary_skill_candidate"]["applicability_result"]["status"], "APPLICABLE")
        self.assertEqual(bridge["primary_skill_candidate"]["evidence_readiness_result"]["status"], "BLOCKED_BY_REQUIRED_EVIDENCE")
        self.assertEqual(bridge["next_shared_gap"]["metric_id"], "output_time_period")
        self.assertIn("ต่อวัน", route["final_response_text"])
        self.assertIn("ต่อรอบ", route["final_response_text"])
        self.assertFalse(bridge["constitutional_invariants"]["skill_executed"])
        self.assertFalse(bridge["constitutional_invariants"]["planner_invoked"])

    def test_complete_capacity_advances_gap(self):
        route = build_task_route({"conversation_memory": {"business_topic": "ขายชูครีม ทำตามออเดอร์"}}, "ตอนนี้ทำได้ 100 ชิ้นต่อวัน")
        bridge = self._bridge(route)
        self.assertEqual(bridge["primary_skill_candidate"]["skill_id"], "analyze_operating_capacity")
        self.assertIn(bridge["primary_skill_candidate"]["evidence_readiness_result"]["status"], {"READY_WITH_LIMITATIONS", "PARTIALLY_READY"})
        self.assertNotEqual(bridge["next_shared_gap"].get("metric_id"), "output_time_period")

    def test_profit_startup_inventory_cash_outcomes(self):
        cases = [
            ("ลูกค้าเพิ่มแต่กำไรลด", "analyze_profit_compression", "analysis_timeframe"),
            ("อยากเปิดร้านขายชูครีมแต่ไม่รู้ต้องใช้ทุนเท่าไร", "evaluate_startup_cost", "business_model"),
            ("ของเหลือแค่ 3 ชิ้น", "analyze_inventory_risk", "average_daily_sales"),
            ("ขายได้แต่ไม่มีเงินสด", "analyze_cash_flow_stress", "receivable_days"),
        ]
        for message, skill_id, gap in cases:
            route = build_task_route({}, message)
            bridge = self._bridge(route)
            self.assertEqual(bridge["primary_skill_candidate"]["skill_id"], skill_id)
            self.assertEqual(bridge["next_shared_gap"].get("metric_id"), gap)

    def test_inventory_conflict_blocks(self):
        knowledge = build_knowledge_runtime(user_message="เหลือ 3 ชิ้น", perspective_runtime={"selected_frame": "INVENTORY_RISK"}, structured_business_data={"current_stock": {"value": 12, "unit": "pieces"}})
        bridge = build_knowledge_skill_bridge({"knowledge_runtime_result": knowledge, "selected_frame": "INVENTORY_RISK"})
        self.assertEqual(bridge["primary_skill_candidate"]["evidence_readiness_result"]["status"], "BLOCKED_BY_CONFLICT")

    def test_no_safe_skill_and_ready_skill_no_judgment(self):
        bridge = build_knowledge_skill_bridge({"knowledge_runtime_result": {"knowledge_available": False}})
        self.assertEqual(bridge["bridge_status"], "INSUFFICIENT_KNOWLEDGE_CONTEXT")
        route = build_task_route({}, "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท")
        self.assertEqual(route["business_workflow"]["extracted_entities"]["price"] - route["business_workflow"]["extracted_entities"]["cost"], 45)
        self.assertFalse(self._bridge(route)["constitutional_invariants"]["business_judgment_produced"])


if __name__ == "__main__":
    unittest.main()
