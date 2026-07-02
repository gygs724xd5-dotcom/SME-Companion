import unittest

from brain.conversation_manager import sync_legacy_workflow_state
from brain.conversation_runtime_reset import clear_conversation_runtime_state
from brain.task_router import build_task_route, developer_diagnostics


CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e01\u0e32\u0e41\u0e1f"
CUSTOMER_PRICE_COFFEE = "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e16\u0e32\u0e21\u0e23\u0e32\u0e04\u0e32\u0e01\u0e32\u0e41\u0e1f\u0e40\u0e22\u0e47\u0e19"
CUSTOMER_PRICE_AMERICANO = "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e16\u0e32\u0e21\u0e23\u0e32\u0e04\u0e32\u0e2d\u0e40\u0e21\u0e23\u0e34\u0e01\u0e32\u0e42\u0e19\u0e48"
COST_500 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 500"
QUANTITY_100 = "100 \u0e0a\u0e34\u0e49\u0e19"
PROMOTION_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e34\u0e14\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e48\u0e19\u0e23\u0e49\u0e32\u0e19"


def _carry_route_state(state: dict, route: dict) -> dict:
    next_state = dict(state or {})
    next_state["conversation_memory"] = route.get("conversation_memory") or {}
    next_state["business_context"] = route.get("business_context") or {}
    next_state["conversation_intelligence"] = route.get("conversation_intelligence") or {}

    conversation = dict(next_state.get("conversation") or {})
    conversation.update(
        {
            "conversation_memory": route.get("conversation_memory") or {},
            "business_context": route.get("business_context") or {},
            "intent_resolution": route.get("intent_resolution") or {},
            "understanding": route.get("conversation_understanding") or {},
        }
    )

    workflow_state = (route.get("business_workflow") or {}).get("workflow_state")
    if workflow_state:
        conversation_os = conversation.setdefault("conversation_os", {})
        conversation_os.setdefault("workflow_states", {})
        workflow_id = workflow_state.get("workflow_id")
        conversation_os["active_workflow_id"] = workflow_id
        conversation_os["workflow_states"][workflow_id] = workflow_state
        sync_legacy_workflow_state(next_state, workflow_state)

    next_state["conversation"] = conversation
    return next_state


class V535PlannerCurrentIntentAuthorityTest(unittest.TestCase):
    def test_customer_reply_beats_stale_content_plan_context(self):
        state = _carry_route_state({}, build_task_route({}, CONTENT_REQUEST))

        route = build_task_route(state, CUSTOMER_PRICE_COFFEE)
        skill = route["business_intelligence"].get("matched_skill") or {}
        reasoning = route["business_intelligence"].get("business_reasoning") or {}

        self.assertEqual(route["business_context"]["current_message_intent"], "customer_reply")
        self.assertIn(route["intent_resolution"]["resolved_intent"], {"customer_reply", "customer_price_reply"})
        self.assertNotEqual(route["intent_resolution"]["resolved_workflow"], "CONTENT_PLAN")
        self.assertNotEqual(route["planner_output"]["workflow"], "CONTENT_PLAN")
        self.assertEqual(skill.get("skill_id"), "01.001.customer_asks_price")
        self.assertTrue(skill.get("matched_from_current_message"))
        self.assertEqual(reasoning.get("skill_id"), "01.001.customer_asks_price")

    def test_customer_reply_with_product_name_is_not_content_plan(self):
        route = build_task_route({}, CUSTOMER_PRICE_AMERICANO)
        skill = route["business_intelligence"].get("matched_skill") or {}

        self.assertIn(route["intent_resolution"]["resolved_intent"], {"customer_reply", "customer_price_reply"})
        self.assertNotEqual(route["intent_resolution"]["resolved_workflow"], "CONTENT_PLAN")
        self.assertNotEqual(route["planner_output"]["workflow"], "CONTENT_PLAN")
        self.assertEqual(skill.get("skill_id"), "01.001.customer_asks_price")

    def test_promotion_after_reset_does_not_reuse_cost_workflow(self):
        state = _carry_route_state({}, build_task_route({}, COST_500))
        state, _ = clear_conversation_runtime_state(state, reason="new_conversation")

        route = build_task_route(state, PROMOTION_REQUEST)
        skill = route["business_intelligence"].get("matched_skill") or {}

        self.assertEqual(route["intent_resolution"]["resolved_intent"], "marketing_strategy")
        self.assertEqual(route["planner_output"]["task_type"], "Marketing")
        self.assertNotEqual(route["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertNotEqual((route["business_workflow"].get("workflow_state") or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertNotIn("quantity", route["business_workflow"].get("missing_entities") or [])
        self.assertEqual(skill.get("skill_id"), "02.002.create_promotion")

    def test_valid_cost_followup_still_computes_unit_cost(self):
        state = _carry_route_state({}, build_task_route({}, COST_500))

        route = build_task_route(state, QUANTITY_100)
        workflow = route["business_workflow"]

        self.assertEqual(route["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(workflow.get("input_cost"), 500)
        self.assertEqual(workflow.get("input_quantity"), 100)
        self.assertEqual(workflow.get("computed_cost_per_unit"), 5)

    def test_domain_switch_from_cost_to_content_plan(self):
        state = _carry_route_state({}, build_task_route({}, COST_500))

        route = build_task_route(state, CONTENT_REQUEST)

        self.assertEqual(route["intent_resolution"]["resolved_intent"], "content_planning")
        self.assertEqual(route["planner_output"]["workflow"], "CONTENT_PLAN")
        self.assertNotEqual(route["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertNotIn("quantity", route["business_workflow"].get("missing_entities") or [])

    def test_planner_message_guard_excludes_stale_content_plan_context(self):
        state = _carry_route_state({}, build_task_route({}, CONTENT_REQUEST))

        route = build_task_route(state, CUSTOMER_PRICE_COFFEE)
        planner_message = route["intent_resolution"].get("planner_message") or ""

        self.assertNotIn("content plan", planner_message)
        self.assertNotIn(CONTENT_REQUEST, planner_message)
        self.assertIn("customer reply", planner_message)

    def test_canonical_entities_remain_available_in_diagnostics(self):
        route = build_task_route({}, CUSTOMER_PRICE_COFFEE)
        diagnostics = developer_diagnostics(route)

        self.assertTrue(route.get("canonical_entities"))
        self.assertEqual(diagnostics["canonical_entities"], route["canonical_entities"])


if __name__ == "__main__":
    unittest.main()
