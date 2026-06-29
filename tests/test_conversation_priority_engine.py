import unittest

from brain.business_context_engine import build_business_context
from brain.conversation_priority_engine import (
    NEW_INTENT,
    TEMPORARY_INTERRUPT,
    WORKFLOW_ANSWER,
    WORKFLOW_SWITCH,
    classify_message_priority,
)
from brain.workflow_readiness import (
    WORKFLOW_CONTENT_PLAN,
    WORKFLOW_COST_CALCULATION,
    WORKFLOW_RECEIPT_CAPTURE,
    WORKFLOW_SALES_PLAN_7_DAY,
)
from brain.workflow_state_machine import new_workflow_state, update_workflow_state


CHOUX_CREAM = "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"
TEEN = "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19"
DISCOUNT = "\u0e25\u0e14 10%"
SALES_REQUEST = "\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e01\u0e32\u0e23\u0e02\u0e32\u0e22\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
COST_REQUEST = "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19"
RECEIPT_REQUEST = "\u0e2d\u0e48\u0e32\u0e19\u0e1a\u0e34\u0e25"
TIME_REQUEST = "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e01\u0e35\u0e48\u0e42\u0e21\u0e07"
CREAM = "\u0e04\u0e23\u0e35\u0e21"


def _state(workflow_state: dict) -> dict:
    return {
        "workflow": {
            "current_workflow": workflow_state.get("workflow"),
            "workflow_state_v2": workflow_state,
        },
        "conversation": {"workflow_state_v2": workflow_state},
    }


def _content_plan_waiting_for(field: str) -> dict:
    workflow_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
    workflow_state["required_fields"] = [field]
    workflow_state["missing_fields"] = [field]
    workflow_state["is_ready"] = False
    return workflow_state


class ConversationPriorityEngineTest(unittest.TestCase):
    def test_completed_content_plan_sales_request_routes_as_new_intent_not_field_answer(self):
        workflow_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
        workflow_state["step"] = "completed"
        workflow_state["missing_fields"] = []
        workflow_state["collected_fields"] = {"product": CHOUX_CREAM}

        decision = classify_message_priority(SALES_REQUEST, _state(workflow_state))

        self.assertIn(decision["classification"], {NEW_INTENT, WORKFLOW_SWITCH})
        self.assertEqual(decision["detected_new_intent"], WORKFLOW_SALES_PLAN_7_DAY)
        self.assertFalse(decision["allow_field_extraction"])

    def test_active_content_plan_product_answer_allows_field_extraction(self):
        decision = classify_message_priority(CHOUX_CREAM, _state(new_workflow_state(WORKFLOW_CONTENT_PLAN)))

        self.assertEqual(decision["classification"], WORKFLOW_ANSWER)
        self.assertTrue(decision["allow_field_extraction"])

        workflow_state, extracted = update_workflow_state(
            new_workflow_state(WORKFLOW_CONTENT_PLAN),
            CHOUX_CREAM,
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )
        self.assertEqual(extracted["product"], CHOUX_CREAM)
        self.assertFalse(workflow_state["missing_fields"])

    def test_target_customer_answer_allows_field_extraction(self):
        decision = classify_message_priority(TEEN, _state(_content_plan_waiting_for("target_customer")))

        self.assertEqual(decision["classification"], WORKFLOW_ANSWER)
        self.assertTrue(decision["allow_field_extraction"])

    def test_promotion_answer_allows_field_extraction(self):
        decision = classify_message_priority(DISCOUNT, _state(_content_plan_waiting_for("promotion")))

        self.assertEqual(decision["classification"], WORKFLOW_ANSWER)
        self.assertTrue(decision["allow_field_extraction"])

    def test_active_content_plan_cost_request_is_workflow_switch(self):
        decision = classify_message_priority(COST_REQUEST, _state(new_workflow_state(WORKFLOW_CONTENT_PLAN)))

        self.assertEqual(decision["classification"], WORKFLOW_SWITCH)
        self.assertEqual(decision["detected_new_intent"], WORKFLOW_COST_CALCULATION)
        self.assertFalse(decision["allow_field_extraction"])

    def test_active_content_plan_receipt_request_is_workflow_switch(self):
        decision = classify_message_priority(RECEIPT_REQUEST, _state(new_workflow_state(WORKFLOW_CONTENT_PLAN)))

        self.assertEqual(decision["classification"], WORKFLOW_SWITCH)
        self.assertEqual(decision["detected_new_intent"], WORKFLOW_RECEIPT_CAPTURE)
        self.assertFalse(decision["allow_field_extraction"])

    def test_active_content_plan_time_question_is_temporary_interrupt(self):
        decision = classify_message_priority(TIME_REQUEST, _state(new_workflow_state(WORKFLOW_CONTENT_PLAN)))

        self.assertEqual(decision["classification"], TEMPORARY_INTERRUPT)
        self.assertFalse(decision["allow_field_extraction"])

    def test_completed_workflow_business_request_does_not_allow_field_extraction(self):
        workflow_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
        workflow_state["step"] = "completed"
        workflow_state["missing_fields"] = []

        decision = classify_message_priority(COST_REQUEST, _state(workflow_state))

        self.assertEqual(decision["classification"], WORKFLOW_SWITCH)
        self.assertEqual(decision["detected_new_intent"], WORKFLOW_COST_CALCULATION)
        self.assertFalse(decision["allow_field_extraction"])

    def test_business_context_does_not_learn_workflow_answer_when_extraction_allowed(self):
        context = build_business_context(
            {"conversation": {"conversation_priority": {"allow_field_extraction": True}}},
            CREAM,
        )

        self.assertNotEqual(context.get("current_product"), "cream")


if __name__ == "__main__":
    unittest.main()
