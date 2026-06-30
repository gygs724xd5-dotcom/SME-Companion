import unittest
from unittest.mock import patch

from brain import pipeline_debugger
from brain.business_intelligence_bridge import run_business_intelligence_bridge
from brain.task_router import build_task_route
from memory.application_state import application_state


class BusinessIntelligenceBridgeTest(unittest.TestCase):
    def setUp(self):
        application_state.clear()
        pipeline_debugger._fallback_trace = None

    def test_bridge_matches_customer_says_expensive(self):
        result = run_business_intelligence_bridge("\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32\u0e41\u0e1e\u0e07", {}, {})

        self.assertTrue(result["bridge_used"])
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["matched_skill"]["skill_id"], "01.002.customer_says_expensive")
        self.assertEqual(result["business_reasoning"]["skill_id"], "01.002.customer_says_expensive")
        self.assertGreaterEqual(result["confidence"], 0.6)

    def test_bridge_matches_customer_asks_price(self):
        result = run_business_intelligence_bridge("\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", {}, {})

        self.assertTrue(result["bridge_used"])
        self.assertEqual(result["matched_skill"]["skill_id"], "01.001.customer_asks_price")
        self.assertEqual(result["business_reasoning"]["skill_id"], "01.001.customer_asks_price")

    def test_bridge_skill_match_audit_flags_context_pricing(self):
        context = {
            "business_context": {
                "business_domain": "01 Sales",
                "business_stage": "Interest",
                "memory_tags": ["pricing_strategy"],
                "detected_intent": "customer_says_expensive",
                "matched_intent_keywords": ["ลูกค้าบอกว่า", "แพงไป", "ควรตอบยังไง"],
            },
            "business_intent": {
                "detected_intent": "customer_says_expensive",
                "intent_confidence": 0.97,
                "matched_intent_keywords": ["ลูกค้าบอกว่า", "แพงไป", "ควรตอบยังไง"],
            },
        }

        result = run_business_intelligence_bridge("ลูกค้าบอกว่าชูครีมแพงไป ควรตอบยังไง", context, {})

        audit = result["skill_match_audit"]
        self.assertEqual(audit["current_message"], "ลูกค้าบอกว่าชูครีมแพงไป ควรตอบยังไง")
        self.assertEqual(audit["detected_intent"], "customer_says_expensive")
        pricing_matches = [
            item for item in audit["suspicious_matches"] if item["token"] == "pricing"
        ]
        self.assertTrue(pricing_matches)
        self.assertTrue(any(item["source_field"] == "business_context.memory_tags" for item in pricing_matches))

    def test_task_router_injects_business_reasoning(self):
        route = build_task_route({}, "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32\u0e41\u0e1e\u0e07")

        business = route["business_intelligence"]
        planner = route["planner_output"]
        reasoning = route["reasoning"]

        self.assertTrue(business["bridge_used"])
        self.assertEqual(business["matched_skill"]["skill_id"], "01.002.customer_says_expensive")
        self.assertEqual(reasoning["action"], "business_reasoning")
        self.assertEqual(reasoning["business_skill_id"], "01.002.customer_says_expensive")
        self.assertEqual(planner["business_reasoning"]["skill_id"], "01.002.customer_says_expensive")
        self.assertTrue(planner["business_principle"])
        self.assertTrue(planner["thinking_pattern"])
        self.assertTrue(planner["decision_tree"])
        self.assertTrue(planner["questions_to_ask"])

    def test_broad_business_message_routes_to_business_consulting(self):
        route = build_task_route({}, "\u0e2d\u0e22\u0e32\u0e01\u0e02\u0e32\u0e22\u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e1c\u0e49\u0e32")

        self.assertTrue(route["business_intelligence"]["bridge_used"])
        self.assertEqual(route["planner_output"]["task_type"], "Business Consulting")
        self.assertEqual(route["reasoning"]["action"], "business_reasoning")
        self.assertEqual(route["planner_output"]["estimated_response_mode"], "BUSINESS_CONSULTING")

    def test_unknown_sentence_uses_legacy_fallback(self):
        route = build_task_route({}, "xyzzy unrelated sentence")

        self.assertFalse(route["business_intelligence"]["bridge_used"])
        self.assertTrue(route["business_intelligence"]["fallback_used"])
        self.assertEqual(route["reasoning"]["action"], "default_chat")
        self.assertEqual(route["planner_output"]["task_type"], "General Business Help")

    def test_bridge_failure_is_backward_compatible(self):
        with patch("brain.business_intelligence_bridge.search_business_skills", side_effect=RuntimeError("boom")):
            result = run_business_intelligence_bridge("price?", {}, {"task_type": "General Business Help"})

        self.assertFalse(result["bridge_used"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["planner_output"]["task_type"], "General Business Help")
        self.assertIn("bridge_error", result)

    def test_trace_events_include_business_bridge_state(self):
        route = build_task_route({}, "\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23")
        application_state.setdefault("developer", {})["task_route"] = route

        with patch.object(pipeline_debugger, "st", None):
            pipeline_debugger.start_pipeline_trace("\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23")
            trace = pipeline_debugger.add_pipeline_event(
                "business_intelligence",
                "Business Reasoning",
                "Business Reasoning",
            )

        key_state = trace["events"][-1]["key_state"]
        self.assertTrue(key_state["business_skill_search"])
        self.assertTrue(key_state["bridge_used"])
        self.assertFalse(key_state["fallback_used"])
        self.assertEqual(key_state["matched_skill"], "01.001.customer_asks_price")
        self.assertTrue(key_state["business_principle"])
        self.assertTrue(key_state["thinking_pattern"])
        self.assertTrue(key_state["decision_tree"])
        self.assertTrue(key_state["business_reasoning"])
        self.assertGreaterEqual(key_state["reasoning_confidence"], 0.6)
        self.assertTrue(key_state["business_response_mode"])
        self.assertEqual(key_state["detected_intent"]["detected_intent"], "pricing_question")
        self.assertIn("extracted_entities", key_state["extracted_entities"])


if __name__ == "__main__":
    unittest.main()
