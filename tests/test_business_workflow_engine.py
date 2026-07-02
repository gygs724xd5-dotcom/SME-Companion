import unittest

from brain.business_entity_extractor import extract_business_entities
from brain.business_intent_engine import detect_business_intent
from brain.business_workflow_engine import decide_business_workflow
from brain.conversation_manager import continue_workflow, route_quick_action
from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_readiness import WORKFLOW_COST_CALCULATION


CHOUX_CREAM = "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"


def _decision(message, state=None, intent=None):
    business_intent = detect_business_intent(message)
    if intent:
        business_intent = {**business_intent, "detected_intent": intent, "intent_confidence": 0.9}
    entities = extract_business_entities(message, business_intent["detected_intent"])
    return decide_business_workflow(message, business_intent, entities, state or {})


def _active_profit_state(missing=None, collected=None):
    return {
        "conversation": {
            "conversation_os": {
                "active_workflow_id": "PROFIT_CALCULATION",
                "planner_locked": True,
                "conversation_stack": [],
                "workflow_states": {
                    "PROFIT_CALCULATION": {
                        "workflow_id": "PROFIT_CALCULATION",
                        "workflow_name": "Profit Calculation",
                        "workflow_status": "COLLECT",
                        "current_step": "collecting_entities",
                        "required_entities": ["product", "price", "cost", "quantity"],
                        "collected_fields": collected or {"product": CHOUX_CREAM, "price": 50, "cost": 20},
                        "missing_fields": missing or ["quantity"],
                    }
                },
            }
        }
    }


class BusinessWorkflowEngineTest(unittest.TestCase):
    def test_continue_workflow_with_missing_quantity_answer(self):
        decision = _decision("20", _active_profit_state(), intent="unknown")

        self.assertEqual(decision["workflow_action"], "continue")
        self.assertEqual(decision["missing_entities"], [])
        self.assertTrue(decision["workflow_complete"])

    def test_interrupt_workflow_for_customer_reply(self):
        decision = _decision("customer says it is too expensive", _active_profit_state(), intent="unknown")

        self.assertEqual(decision["workflow_action"], "interrupt")
        self.assertIn("customer_reply", decision["workflow_reason"])

    def test_label_explanation_overrides_workflow(self):
        decision = _decision("pricing_unclear คืออะไร", _active_profit_state(), intent="unknown")

        self.assertEqual(decision["workflow_action"], "interrupt")
        self.assertEqual(decision["workflow_reason"], "label_explanation")

    def test_resume_workflow_from_paused_state(self):
        state = {}
        route_quick_action(state, "cost_calculator")
        continue_workflow(state, "pause")

        decision = _decision("กลับมาคำนวณต่อ", state, intent="unknown")

        self.assertEqual(decision["workflow_action"], "resume")
        self.assertTrue(decision["workflow_resume_available"])

    def test_complete_workflow_when_entities_are_complete(self):
        message = f"profit product {CHOUX_CREAM} price 50 cost 20 quantity 10 units"
        decision = _decision(message, intent="profit_calculation")

        self.assertEqual(decision["workflow_action"], "complete")
        self.assertTrue(decision["workflow_complete"])
        self.assertEqual(decision["missing_entities"], [])

    def test_cancel_workflow(self):
        decision = _decision("cancel", _active_profit_state(), intent="unknown")

        self.assertEqual(decision["workflow_action"], "cancel")

    def test_start_new_workflow(self):
        decision = _decision(f"profit product {CHOUX_CREAM} price 50", intent="profit_calculation")

        self.assertEqual(decision["workflow_action"], "start_new")
        self.assertIn("cost", decision["missing_entities"])
        self.assertNotIn("quantity", decision["missing_entities"])

    def test_entity_completeness_and_missing_detection(self):
        decision = _decision(f"profit product {CHOUX_CREAM} price 50 cost 20", intent="profit_calculation")

        self.assertEqual(decision["required_entities"], ["price", "cost"])
        self.assertNotIn("quantity", decision["missing_entities"])
        self.assertEqual(decision["entity_completeness"]["completed"], 2)

    def test_smart_question_generation_does_not_ask_quantity_for_unit_profit(self):
        decision = _decision(f"profit product {CHOUX_CREAM} price 50 cost 20", intent="profit_calculation")

        self.assertIsNone(decision["next_question"])

    def test_task_router_customer_reply_overrides_active_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, "customer says it is too expensive")

        self.assertEqual(route["business_workflow"]["workflow_action"], "release")
        self.assertTrue(route["business_workflow"]["workflow_released"])
        self.assertFalse(route.get("planner_locked", False))

    def test_task_router_label_explanation_overrides_active_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, "pricing_unclear คืออะไร")

        self.assertEqual(route["business_workflow"]["workflow_action"], "release")
        self.assertTrue(route["business_workflow"]["workflow_released"])
        self.assertFalse(route.get("planner_locked", False))

    def test_general_question_overrides_active_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, "what time is it?")

        self.assertEqual(route["business_workflow"]["workflow_action"], "release")
        self.assertTrue(route["business_workflow"]["workflow_released"])
        self.assertFalse(route.get("planner_locked", False))

    def test_returning_to_previous_workflow_is_diagnosed(self):
        state = {}
        route_quick_action(state, "cost_calculator")
        continue_workflow(state, "pause")

        route = build_task_route(state, "กลับมาคำนวณต่อ")
        diagnostics = developer_diagnostics(route)

        self.assertEqual(route["business_workflow"]["workflow_action"], "resume")
        self.assertEqual((route["business_workflow"]["workflow_state"] or {}).get("workflow_id"), WORKFLOW_COST_CALCULATION)
        self.assertTrue(diagnostics["workflow_resume_available"])
        self.assertIn("required_entities", diagnostics)


if __name__ == "__main__":
    unittest.main()
