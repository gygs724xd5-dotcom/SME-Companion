import unittest

from brain.knowledge_runtime import build_knowledge_runtime
from brain.knowledge_skill_bridge import build_knowledge_skill_bridge


class V591SkillCandidateSelectionTest(unittest.TestCase):
    def test_capacity_relevance_beats_ready_or_metric_only_candidates(self):
        knowledge = build_knowledge_runtime(user_message="ตอนนี้ทำได้ 100 ชิ้น", business_situation={"known_evidence": [{"summary": "ขายชูครีม ทำตามออเดอร์"}]}, perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"})
        bridge = build_knowledge_skill_bridge({"knowledge_runtime_result": knowledge, "business_context": {"business_model": "made_to_order"}})
        self.assertEqual(bridge["primary_skill_candidate"]["skill_id"], "analyze_operating_capacity")
        self.assertEqual(bridge["primary_skill_candidate"]["evidence_readiness_result"]["status"], "BLOCKED_BY_REQUIRED_EVIDENCE")
        self.assertEqual(bridge["next_shared_gap"]["metric_id"], "output_time_period")

    def test_planning_stage_is_deferred(self):
        knowledge = build_knowledge_runtime(user_message="ตอนนี้ทำได้ 100 ชิ้น", business_situation={"known_evidence": [{"summary": "ทำตามออเดอร์"}]}, perspective_runtime={"selected_frame": "CAPACITY_CONSTRAINT"})
        bridge = build_knowledge_skill_bridge({"knowledge_runtime_result": knowledge, "business_context": {"business_model": "made_to_order"}, "selected_frame": "CAPACITY_CONSTRAINT"})
        deferred = {item["skill_id"] for item in bridge["deferred_skill_candidates"]}
        self.assertIn("plan_order_fulfillment", deferred)
        self.assertFalse(bridge["planner_handoff"]["planning_allowed"])


if __name__ == "__main__":
    unittest.main()
