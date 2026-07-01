import unittest

from brain.conversation_runtime_reset import (
    RESET_RUNTIME_STATE_VERSION,
    reset_transient_conversation_state,
)
from brain.response_transformation_engine import transform_response
from brain.task_router import build_task_route
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION


MSG_CREATE_THAI_TEA_POST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
MSG_COST_35_100_PROFIT_30 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19 \u0e01\u0e33\u0e44\u0e23 30%"
MSG_COST_20_50 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 20 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 50 \u0e0a\u0e34\u0e49\u0e19"
MSG_VARIANT = "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a"


def _completed_cost_workflow():
    return {
        "workflow_id": WORKFLOW_COST_CALCULATION,
        "workflow_name": "cost_calculation",
        "collected_fields": {
            "unit_cost": 35,
            "total_units": 100,
            "profit_percent": 30,
        },
        "generated_response": (
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 35 \u0e1a\u0e32\u0e17 "
            "\u0e41\u0e19\u0e30\u0e19\u0e33\u0e15\u0e31\u0e49\u0e07\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22 45.50 \u0e1a\u0e32\u0e17"
        ),
    }


def _completed_content_workflow():
    return {
        "workflow_id": WORKFLOW_CONTENT_PLAN,
        "workflow_name": "content_creation",
        "collected_fields": {"product": "\u0e0a\u0e32\u0e44\u0e17\u0e22"},
        "generated_response": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22",
    }


def _dirty_state(completed_workflow):
    response_memory = {
        "last_generated_response": completed_workflow["generated_response"],
        "last_response_type": completed_workflow["workflow_id"],
        "last_generation_context": {"workflow": completed_workflow["workflow_id"]},
        "last_variant_history": ["old variant"],
        "last_transformation_chain": ["SHORTEN", "SEO"],
        "transformation_history": [{"transformation_type": "SHORTEN"}],
    }
    return {
        "auth_session": {"session_id": "session-1"},
        "auth_owner_id": "owner-1",
        "current_owner_id": "owner-1",
        "current_store_id": "store-1",
        "current_store_name": "Thai Tea Shop",
        "store": {
            "store_profile": {"store_name": "Thai Tea Shop", "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22"},
            "last_completed_workflow": completed_workflow,
        },
        "business_memory": {"identity": {"owner_id": "owner-1"}, "completed_workflows": [completed_workflow]},
        "ui": {"theme": "light"},
        "conversation": {
            "chat_history": [
                {"role": "user", "content": MSG_COST_35_100_PROFIT_30},
                {"role": "assistant", "content": completed_workflow["generated_response"]},
            ],
            "current_workflow": completed_workflow["workflow_id"],
            "workflow_state_v2": {"workflow": completed_workflow["workflow_id"], "step": "completed"},
            "conversation_memory": {"completed_workflows": [completed_workflow], "last_intent": "profit_calculation"},
            "business_context": {"current_discussion_topic": "old cost/profit"},
            "response_memory": response_memory,
            **response_memory,
            "last_intent": "profit_calculation",
            "previous_intent": "cost_calculation",
            "followup_chain": ["completed_workflow", "pricing_followup"],
            "continuation_mode": "completed_workflow_followup",
        },
        "workflow": {
            "current_workflow": completed_workflow["workflow_id"],
            "workflow_state_v2": {"workflow": completed_workflow["workflow_id"], "step": "completed"},
        },
        "business_context": {"current_discussion_topic": "old cost/profit"},
        "conversation_understanding": {"detected_intent": "continue_previous_workflow"},
        "conversation_memory": {"last_intent": "profit_calculation"},
        "knowledge_context": {"selected_skill": "old_skill"},
        "reasoning_context": {"business_goal": "old_goal"},
        "planner_context": {"business_goal": "old_plan"},
        "developer": {
            "developer_mode": True,
            "task_route": {"llm_decision": {"response_mode": "old"}},
            "llm_decision": {"response_mode": "old"},
            "future_hooks": {"ocr_engine": None},
        },
    }


class V5201ConversationResetIsolationTest(unittest.TestCase):
    def test_reset_after_completed_cost_does_not_leak_pricing_into_content_request(self):
        reset_state, diagnostics = reset_transient_conversation_state(
            _dirty_state(_completed_cost_workflow()),
            conversation_id="conversation-new",
        )

        followup = classify_completed_workflow_followup(reset_state, MSG_CREATE_THAI_TEA_POST)
        transformation = transform_response(MSG_CREATE_THAI_TEA_POST, reset_state)
        route = build_task_route(reset_state, MSG_CREATE_THAI_TEA_POST)
        route_text = str(route)

        self.assertTrue(diagnostics["conversation_reset_applied"])
        self.assertEqual(diagnostics["reset_runtime_state_version"], RESET_RUNTIME_STATE_VERSION)
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertFalse(transformation["handled"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        self.assertNotEqual((route.get("business_context") or {}).get("current_discussion_topic"), "old cost/profit")
        self.assertNotIn("45.50", route_text)
        self.assertNotIn("pricing_followup", route_text)

    def test_reset_after_completed_content_allows_fresh_cost_calculation(self):
        reset_state, _ = reset_transient_conversation_state(_dirty_state(_completed_content_workflow()))

        route = build_task_route(reset_state, MSG_COST_20_50)
        route_text = str(route)

        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_COST_CALCULATION)
        self.assertIn("20", route_text)
        self.assertIn("50", route_text)
        self.assertNotIn("\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22", route_text)

    def test_reset_preserves_store_profile_and_business_memory_identity(self):
        dirty = _dirty_state(_completed_cost_workflow())
        reset_state, diagnostics = reset_transient_conversation_state(dirty)

        self.assertEqual(reset_state["auth_owner_id"], "owner-1")
        self.assertEqual(reset_state["current_store_id"], "store-1")
        self.assertEqual(reset_state["store"]["store_profile"]["store_name"], "Thai Tea Shop")
        self.assertEqual(reset_state["business_memory"]["identity"]["owner_id"], "owner-1")
        self.assertEqual(reset_state["ui"]["theme"], "light")
        self.assertNotIn("last_completed_workflow", reset_state["store"])
        self.assertIn("store", diagnostics["reset_preserved_keys"])
        self.assertIn("business_memory", diagnostics["reset_preserved_keys"])

    def test_reset_clears_previous_response_and_transformation_history(self):
        reset_state, diagnostics = reset_transient_conversation_state(_dirty_state(_completed_content_workflow()))
        conversation = reset_state["conversation"]

        self.assertIsNone(conversation["last_generated_response"])
        self.assertIsNone(conversation["last_response_type"])
        self.assertEqual(conversation["last_generation_context"], {})
        self.assertEqual(conversation["last_variant_history"], [])
        self.assertEqual(conversation["last_transformation_chain"], [])
        self.assertEqual(conversation["transformation_history"], [])
        self.assertEqual(conversation["response_memory"], {})
        self.assertFalse(transform_response(MSG_VARIANT, reset_state)["handled"])
        self.assertIn("last_generated_response", diagnostics["reset_cleared_keys"])
        self.assertIn("response_memory", diagnostics["reset_cleared_keys"])


if __name__ == "__main__":
    unittest.main()
