import unittest

from brain.brain_observatory import build_brain_observatory
from brain.task_router import build_task_route


class V591BridgeIntegrationTest(unittest.TestCase):
    def test_bridge_attaches_to_route_audit_and_observatory(self):
        route = build_task_route({"conversation_memory": {"business_topic": "ขายชูครีม ทำตามออเดอร์"}}, "ตอนนี้ทำได้ 100 ชิ้น")
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        audit = route["cognitive_authority_audit"]
        observatory = build_brain_observatory(route)
        layers = {item["layer"]: item for item in observatory["layers"]}
        self.assertTrue(bridge["bridge_consulted"])
        self.assertEqual(audit["primary_skill_candidate"], "analyze_operating_capacity")
        self.assertTrue(audit["skill_to_clarification_handoff_created"])
        self.assertIn("Knowledge-Skill Bridge", layers)
        self.assertFalse(audit["skill_execution_triggered"])
        self.assertFalse(audit["planner_invoked"])

    def test_workflow_owner_preserved(self):
        route = build_task_route({}, "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท")
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(route["business_workflow"]["extracted_entities"]["price"] - route["business_workflow"]["extracted_entities"]["cost"], 45)
        self.assertTrue(bridge["workflow_coordination"]["workflow_admitted"])
        self.assertFalse(bridge["workflow_coordination"]["bridge_execution_allowed"])


if __name__ == "__main__":
    unittest.main()
