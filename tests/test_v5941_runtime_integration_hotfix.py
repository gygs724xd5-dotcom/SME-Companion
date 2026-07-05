import unittest

from brain.knowledge_skill_outcome_hardening import resolve_v5941_runtime_response
from brain.response_commit_boundary import commit_response_boundary
from brain.task_router import build_task_route


CAPACITY = "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
PER_DAY = "\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19"
INVENTORY_3 = "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e02\u0e2d\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d 3 \u0e0a\u0e34\u0e49\u0e19"
STARTUP = "\u0e2d\u0e22\u0e32\u0e01\u0e23\u0e39\u0e49\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19"
INVENTORY_RETURN_2 = "\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e2a\u0e15\u0e4a\u0e2d\u0e01 \u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e02\u0e2d\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d 2 \u0e0a\u0e34\u0e49\u0e19"
SALES_BAD = "\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22\u0e44\u0e21\u0e48\u0e14\u0e35"
SALES_DROP = "\u0e0a\u0e48\u0e27\u0e07\u0e19\u0e35\u0e49\u0e22\u0e2d\u0e14\u0e15\u0e01"
AMBIGUOUS = "\u0e41\u0e25\u0e49\u0e27\u0e41\u0e15\u0e48\u0e27\u0e31\u0e19"
PROFIT = "\u0e02\u0e32\u0e22 80 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"


class V5941RuntimeIntegrationHotfixTest(unittest.TestCase):
    def setUp(self):
        self.context = {}

    def _route(self, message):
        return build_task_route(
            {"conversation": {"conversation_cognitive_context": self.context, "chat_history": []}},
            message,
        )

    def _turn(self, message):
        route = self._route(message)
        result = resolve_v5941_runtime_response(route, message, self.context)
        patch = (result.get("conversation_state_patch") or {}).get("conversation_cognitive_context") or {}
        self.context.update(patch)
        return route, result

    def test_capacity_timeframe_clarification(self):
        route, result = self._turn(CAPACITY)
        self.assertTrue(result["handled"])
        self.assertEqual(result["selected_response_owner"], "clarification_authority")
        self.assertIn("\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19", result["reply"])
        self.assertIn("\u0e15\u0e48\u0e2d\u0e23\u0e2d\u0e1a", result["reply"])
        self.assertEqual(self.context["pending_clarification_metric_id"], "output_time_period")
        self.assertTrue(result["diagnostics"]["generic_fallback_suppressed"])

    def test_follow_up_resolution_for_per_day(self):
        self._turn(CAPACITY)
        _, result = self._turn(PER_DAY)
        self.assertTrue(result["handled"])
        self.assertEqual(result["selected_response_owner"], "follow_up_resolution")
        self.assertNotIn("100 \u0e0a\u0e34\u0e49\u0e19\u0e19\u0e35\u0e49", result["reply"])
        self.assertEqual(result["diagnostics"]["follow_up_resolution_status"], "ANSWERED")

    def test_inventory_evidence_gap_and_no_premature_reorder(self):
        _, result = self._turn(INVENTORY_3)
        self.assertTrue(result["handled"])
        self.assertEqual(self.context["active_topic_id"], "INVENTORY_HEALTH")
        self.assertEqual(self.context["current_inventory"], 3)
        self.assertIn("\u0e40\u0e09\u0e25\u0e35\u0e48\u0e22", result["reply"])
        self.assertNotIn("\u0e2a\u0e31\u0e48\u0e07\u0e40\u0e1e\u0e34\u0e48\u0e21", result["reply"])
        self.assertNotIn("\u0e42\u0e1b\u0e23", result["reply"])

    def test_topic_switch_to_startup_cost_and_no_unit_cost_stale_clarification(self):
        self._turn(INVENTORY_3)
        route, result = self._turn(STARTUP)
        bridge = route["business_situation"]["diagnostics"]["knowledge_skill_bridge"]
        self.assertEqual(self.context["active_topic_id"], "STARTUP_COST_STRUCTURE")
        self.assertEqual((bridge["primary_skill_candidate"] or {})["skill_id"], "evaluate_startup_cost")
        self.assertNotIn("\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a", result["reply"])
        self.assertNotIn("\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19", result["reply"])

    def test_repeated_startup_request_recovers_without_unit_cost_loop(self):
        self._turn(STARTUP)
        _, result = self._turn(STARTUP)
        self.assertTrue(result["handled"])
        self.assertIn("\u0e40\u0e23\u0e34\u0e48\u0e21\u0e23\u0e49\u0e32\u0e19", result["reply"])
        self.assertNotIn("\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a", result["reply"])

    def test_topic_return_latest_inventory_supersedes_old_value(self):
        self._turn(INVENTORY_3)
        self._turn(STARTUP)
        _, result = self._turn(INVENTORY_RETURN_2)
        self.assertEqual(self.context["active_topic_id"], "INVENTORY_HEALTH")
        self.assertTrue(result["diagnostics"]["topic_return_detected"])
        self.assertEqual(result["diagnostics"]["freshest_value"], 2)
        self.assertEqual(result["diagnostics"]["superseded_values"], [3])
        self.assertIn("\u0e40\u0e09\u0e25\u0e35\u0e48\u0e22", result["reply"])

    def test_sales_ambiguity_asks_discriminating_question(self):
        for message in (SALES_BAD, SALES_DROP):
            self.context = {}
            route, result = self._turn(message)
            self.assertTrue(result["handled"])
            self.assertEqual(result["selected_response_owner"], "skill_ambiguity")
            self.assertNotEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
            self.assertFalse(route["workflow_admission_gate"]["admitted"])
            self.assertNotEqual(route["business_workflow"]["workflow_action"], "start_new")
            self.assertIsNone(route["business_workflow"]["workflow_state"])
            self.assertIn("\u0e04\u0e19\u0e40\u0e2b\u0e47\u0e19", result["reply"])
            self.assertIn("\u0e44\u0e21\u0e48\u0e0b\u0e37\u0e49\u0e2d", result["reply"])
            self.assertNotIn("\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19", result["reply"])

    def test_clarification_retry_cap_and_safe_partial_outcome(self):
        self._turn(CAPACITY)
        _, retry = self._turn(AMBIGUOUS)
        self.assertEqual(retry["diagnostics"]["clarification_retry_count"], 1)
        self.assertIn("\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19", retry["reply"])
        _, exhausted = self._turn(AMBIGUOUS)
        self.assertEqual(exhausted["diagnostics"]["clarification_stop_reason"], "RETRY_CAP_EXHAUSTED")
        self.assertIn("\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e23\u0e39\u0e49\u0e0a\u0e48\u0e27\u0e07\u0e40\u0e27\u0e25\u0e32", exhausted["reply"])

    def test_profit_workflow_still_owns_calculation(self):
        route = self._route(PROFIT)
        result = resolve_v5941_runtime_response(route, PROFIT, self.context)
        self.assertFalse(result["handled"])
        self.assertEqual(result["selected_response_owner"], "active_workflow")
        entities = route["business_workflow"]["extracted_entities"]
        self.assertEqual(entities["price"] - entities["cost"], 45)
        intelligence = route["business_intelligence"]
        self.assertFalse(intelligence["bridge_used"])
        self.assertTrue(intelligence["skill_matching_bypassed"])
        self.assertIsNone(intelligence["matched_skill"])
        self.assertIn("executable workflow owns", intelligence["skill_matching_bypass_reason"])

    def test_generic_fallback_only_after_structured_exhaustion(self):
        route = self._route("hello unrelated")
        result = resolve_v5941_runtime_response(route, "hello unrelated", self.context)
        self.assertFalse(result["handled"])
        self.assertEqual(result["selected_response_owner"], "safe_generic_fallback")
        self.assertFalse(result["diagnostics"]["generic_fallback_suppressed"])

    def test_response_guard_blocks_inventory_recommendation_leakage(self):
        _, result = self._turn(INVENTORY_3)
        self.assertEqual(result["diagnostics"]["response_guard_mode"], "pass")
        self.assertEqual(result["diagnostics"]["response_guard_violations"], [])
        self.assertNotIn("reorder", result["reply"].lower())

    def test_commit_boundary_remains_sole_final_chat_commit_owner(self):
        session_state = {"chat_history": [], "last_user_message": CAPACITY, "conversation_state": {}}
        application_state = {"conversation": {"conversation_memory": {}}}
        commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply="reply",
            response_metadata={"user_message": CAPACITY},
        )
        self.assertEqual(len(session_state["chat_history"]), 1)
        self.assertEqual(application_state["conversation"]["chat_history"][0]["content"], "reply")

    def test_route_stages_user_memory_once_and_commit_does_not_duplicate_it(self):
        route = build_task_route(
            {
                "conversation": {
                    "conversation_cognitive_context": self.context,
                    "chat_history": [{"role": "user", "content": CAPACITY}],
                }
            },
            CAPACITY,
        )
        staged_memory = route["conversation_memory"]
        self.assertEqual(staged_memory["recent_user_messages"], [CAPACITY])
        self.assertEqual(staged_memory["turn_count"], 1)

        session_state = {
            "chat_history": [{"role": "user", "content": CAPACITY}],
            "last_user_message": CAPACITY,
            "conversation_state": {},
        }
        application_state = {"conversation": {"conversation_memory": staged_memory}}
        result = commit_response_boundary(
            session_state=session_state,
            application_state=application_state,
            final_reply="reply",
            response_metadata={"user_message": CAPACITY},
        )

        memory = result["conversation_memory"]
        self.assertEqual(memory["recent_user_messages"], [CAPACITY])
        self.assertEqual(memory["turn_count"], 1)
        self.assertEqual(len(result["chat_history"]), 2)


if __name__ == "__main__":
    unittest.main()
