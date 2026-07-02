import unittest

from brain.business_workflow_engine import decide_business_workflow
from brain.entity_runtime import extract_canonical_entities
from brain.workflow_state_machine import update_workflow_state


WORKFLOW_COST_CALCULATION = "COST_CALCULATION"
WORKFLOW_PROFIT_CALCULATION = "PROFIT_CALCULATION"


class V534CanonicalEntityMigrationTest(unittest.TestCase):
    def test_profit_workflow_uses_canonical_cost_and_selling_price(self):
        message = (
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 "
            "\u0e02\u0e32\u0e22 120 "
            "\u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
        )
        canonical_entities = extract_canonical_entities(message)

        decision = decide_business_workflow(
            message,
            business_intent={
                "detected_intent": "profit_calculation",
                "intent_confidence": 0.9,
            },
            entity_result={"extracted_entities": {}},
            application_state={},
            planner_decision={
                "workflow": WORKFLOW_PROFIT_CALCULATION,
                "intent_resolution": {"resolved_intent": "profit_calculation"},
            },
            canonical_entities=canonical_entities,
        )

        entities = decision["extracted_entities"]
        self.assertTrue(decision["workflow_complete"])
        self.assertEqual(entities["cost"], 85)
        self.assertEqual(entities["price"], 120)
        self.assertEqual(entities["selling_price"], 120)
        self.assertIn("canonical_entity_runtime", entities["entity_source"])
        self.assertIn("cost", decision["completed_entities"])
        self.assertIn("price", decision["completed_entities"])

    def test_cost_workflow_uses_canonical_cost_and_quantity(self):
        message = (
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 "
            "\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
        )
        canonical_entities = extract_canonical_entities(message)

        decision = decide_business_workflow(
            message,
            business_intent={
                "detected_intent": "cost_calculation",
                "intent_confidence": 0.9,
            },
            entity_result={"extracted_entities": {}},
            application_state={},
            planner_decision={
                "workflow": WORKFLOW_COST_CALCULATION,
                "intent_resolution": {"resolved_intent": "cost_calculation"},
            },
            canonical_entities=canonical_entities,
        )

        entities = decision["extracted_entities"]
        self.assertTrue(decision["workflow_complete"])
        self.assertEqual(entities["cost"], 200)
        self.assertEqual(entities["quantity"], 100)
        self.assertEqual(entities["total_units"], 100)
        self.assertEqual(decision["calculation_trace"]["computed_cost_per_unit"], 2)
        self.assertIn("cost", decision["completed_entities"])
        self.assertIn("quantity", decision["completed_entities"])

    def test_state_machine_uses_canonical_slots_before_legacy_fields(self):
        message = (
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 "
            "\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
        )
        canonical_entities = extract_canonical_entities(message)

        state, extracted = update_workflow_state(
            {},
            message,
            detected_workflow=WORKFLOW_COST_CALCULATION,
            canonical_entities=canonical_entities,
        )

        self.assertTrue(state["is_ready"])
        self.assertEqual(extracted["cost"], 200)
        self.assertEqual(extracted["quantity"], 100)
        self.assertEqual(extracted["total_units"], 100)
        self.assertEqual(extracted["entity_source"], "canonical_entity_runtime")


if __name__ == "__main__":
    unittest.main()
