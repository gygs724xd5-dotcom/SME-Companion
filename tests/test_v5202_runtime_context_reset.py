import unittest

from brain.runtime_context_reset import (
    RUNTIME_CONTEXT_KEYS,
    RUNTIME_CONTEXT_VERSION,
    PRESERVED_RUNTIME_ROOTS,
    reset_runtime_contexts,
)
from brain.conversation_runtime_reset import reset_transient_conversation_state
from brain.response_transformation_engine import transform_response
from brain.task_router import build_task_route
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION


MSG_CREATE_THAI_TEA_POST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
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
        "previous_generated_response": completed_workflow["generated_response"],
        "last_response_type": completed_workflow["workflow_id"],
        "last_generation_context": {"workflow": completed_workflow["workflow_id"]},
        "last_variant_history": ["old variant"],
        "last_transformation_chain": ["SHORTEN", "SEO"],
        "transformation_history": [{"transformation_type": "SHORTEN"}],
    }
    runtime_payload = {key: {"old": key} for key in RUNTIME_CONTEXT_KEYS}
    return {
        "auth_session": {"session_id": "session-1"},
        "auth_owner_id": "owner-1",
        "current_owner_id": "owner-1",
        "current_store_id": "store-1",
        "selected_store": "store-1",
        "user_profile": {"name": "owner"},
        "settings": {"tone": "friendly"},
        "product_catalog": [{"name": "\u0e0a\u0e32\u0e44\u0e17\u0e22"}],
        "inventory": {"tea": 10},
        "business_config": {"currency": "THB"},
        "store": {
            "store_profile": {"store_name": "Thai Tea Shop", "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22"},
            "last_completed_workflow": completed_workflow,
        },
        "store_profile": {"store_name": "Thai Tea Shop", "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22"},
        "business_memory": {
            "identity": {"owner_id": "owner-1"},
            "completed_workflows": [completed_workflow],
        },
        "conversation": {
            "chat_history": [
                {"role": "user", "content": "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19"},
                {"role": "user", "content": "\u0e01\u0e33\u0e44\u0e23 30%"},
                {"role": "assistant", "content": completed_workflow["generated_response"]},
            ],
            "conversation_memory": {"completed_workflows": [completed_workflow], "last_intent": "profit_calculation"},
            "business_context": {"current_discussion_topic": "old cost/profit"},
            "response_memory": response_memory,
            **response_memory,
            **runtime_payload,
        },
        "workflow": {
            "current_workflow": completed_workflow["workflow_id"],
            "workflow_runtime": {"workflow_id": completed_workflow["workflow_id"]},
        },
        "business_context": {"current_discussion_topic": "old cost/profit"},
        "developer": {
            "developer_mode": True,
            "future_hooks": {"ocr_engine": None},
            "task_route": {"llm_decision": {"response_mode": "old"}},
            **runtime_payload,
        },
        **runtime_payload,
    }


def _new_conversation_reset(state):
    reset_state, _ = reset_transient_conversation_state(state, conversation_id="conversation-new")
    return reset_runtime_contexts(reset_state)


class V5202RuntimeContextResetTest(unittest.TestCase):
    def test_cost_profit_reset_marketing_request_does_not_use_old_cost_context(self):
        reset_state, diagnostics = _new_conversation_reset(_dirty_state(_completed_cost_workflow()))

        followup = classify_completed_workflow_followup(reset_state, MSG_CREATE_THAI_TEA_POST)
        route = build_task_route(reset_state, MSG_CREATE_THAI_TEA_POST)
        route_text = str(route)

        self.assertTrue(diagnostics["runtime_context_reset_applied"])
        self.assertEqual(diagnostics["runtime_context_version"], RUNTIME_CONTEXT_VERSION)
        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)
        self.assertNotIn("45.50", route_text)
        self.assertNotIn("pricing_followup", route_text)

    def test_marketing_reset_cost_request_calculates_cost_normally(self):
        reset_state, _ = _new_conversation_reset(_dirty_state(_completed_content_workflow()))

        route = build_task_route(reset_state, MSG_COST_20_50)
        route_text = str(route)

        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_COST_CALCULATION)
        self.assertIn("20", route_text)
        self.assertIn("50", route_text)
        self.assertNotIn("\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22", route_text)

    def test_reset_clears_v5_runtime_context_objects(self):
        reset_state, diagnostics = reset_runtime_contexts(_dirty_state(_completed_cost_workflow()))

        for key in RUNTIME_CONTEXT_KEYS:
            self.assertNotIn(key, reset_state)
            self.assertNotIn(key, reset_state["conversation"])
            self.assertNotIn(key, reset_state["developer"])
        self.assertIn("knowledge_context", diagnostics["runtime_contexts_cleared"])
        self.assertIn("response_envelope", diagnostics["runtime_contexts_cleared"])
        self.assertIn("active_cost_context", diagnostics["runtime_contexts_found"])

    def test_reset_preserves_store_profile_and_durable_business_memory(self):
        dirty = _dirty_state(_completed_cost_workflow())
        reset_state, diagnostics = reset_runtime_contexts(dirty)

        self.assertEqual(reset_state["auth_session"]["session_id"], "session-1")
        self.assertEqual(reset_state["store_profile"]["store_name"], "Thai Tea Shop")
        self.assertEqual(reset_state["store"]["store_profile"]["product"], "\u0e0a\u0e32\u0e44\u0e17\u0e22")
        self.assertEqual(reset_state["business_memory"]["identity"]["owner_id"], "owner-1")
        self.assertEqual(reset_state["product_catalog"][0]["name"], "\u0e0a\u0e32\u0e44\u0e17\u0e22")
        self.assertEqual(reset_state["inventory"]["tea"], 10)
        for key in ("business_memory", "store_profile", "selected_store", "settings", "inventory"):
            self.assertIn(key, diagnostics["runtime_contexts_preserved"])
        self.assertEqual(diagnostics["runtime_contexts_preserved"], list(PRESERVED_RUNTIME_ROOTS))

    def test_reset_clears_previous_response_and_transformation_history(self):
        reset_state, diagnostics = _new_conversation_reset(_dirty_state(_completed_content_workflow()))
        conversation = reset_state["conversation"]

        self.assertNotIn("previous_generated_response", conversation)
        self.assertNotIn("last_transformation_chain", conversation)
        self.assertNotIn("transformation_history", conversation)
        self.assertFalse(transform_response(MSG_VARIANT, reset_state)["handled"])
        self.assertIn("previous_generated_response", diagnostics["runtime_contexts_cleared"])
        self.assertIn("transformation_history", diagnostics["runtime_contexts_cleared"])


if __name__ == "__main__":
    unittest.main()
