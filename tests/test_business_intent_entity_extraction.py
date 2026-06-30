import unittest

from brain.business_entity_extractor import extract_business_entities
from brain.business_intent_engine import detect_business_intent
from brain.task_router import build_task_route, developer_diagnostics
from llm.prompt_context_builder import build_prompt_context


CHOUX_CREAM = "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"


class BusinessIntentEntityExtractionTest(unittest.TestCase):
    def test_pricing_question_intent_and_product(self):
        intent = detect_business_intent(f"{CHOUX_CREAM}\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23")
        entities = extract_business_entities(
            f"{CHOUX_CREAM}\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23",
            intent["detected_intent"],
        )

        self.assertEqual(intent["detected_intent"], "pricing_question")
        self.assertIn("\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", intent["matched_intent_keywords"])
        self.assertIn(CHOUX_CREAM, entities["extracted_entities"]["product_or_service_names"])
        self.assertEqual(entities["missing_entities"], [])

    def test_profit_calculation_extracts_product_price_cost_quantity(self):
        message = f"\u0e04\u0e33\u0e19\u0e27\u0e13\u0e01\u0e33\u0e44\u0e23 {CHOUX_CREAM} \u0e02\u0e32\u0e22 50 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 20 \u0e1a\u0e32\u0e17 \u0e08\u0e33\u0e19\u0e27\u0e19 10 \u0e0a\u0e34\u0e49\u0e19"
        intent = detect_business_intent(message)
        entities = extract_business_entities(message, intent["detected_intent"])
        extracted = entities["extracted_entities"]

        self.assertEqual(intent["detected_intent"], "profit_calculation")
        self.assertIn(CHOUX_CREAM, extracted["product_or_service_names"])
        self.assertEqual(extracted["prices"][0]["amount"], 50)
        self.assertEqual(extracted["costs"][0]["amount"], 20)
        self.assertEqual(extracted["quantities"][0]["amount"], 10)
        self.assertEqual(entities["missing_entities"], [])

    def test_sales_summary_extracts_date(self):
        message = "\u0e2a\u0e23\u0e38\u0e1b\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49"
        intent = detect_business_intent(message)
        entities = extract_business_entities(message, intent["detected_intent"])

        self.assertEqual(intent["detected_intent"], "sales_summary")
        self.assertIn("\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49", entities["extracted_entities"]["dates"])
        self.assertEqual(entities["missing_entities"], [])

    def test_choux_cream_is_not_cosmetic_store_entity_hint(self):
        result = extract_business_entities(CHOUX_CREAM, "pricing_question")

        self.assertIn(CHOUX_CREAM, result["extracted_entities"]["product_or_service_names"])
        self.assertNotIn("cosmetic_store", result["extracted_entities"].get("business_type_hints", []))

    def test_missing_required_entities_are_detected(self):
        intent = detect_business_intent("\u0e04\u0e33\u0e19\u0e27\u0e13\u0e01\u0e33\u0e44\u0e23\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22")
        entities = extract_business_entities("\u0e04\u0e33\u0e19\u0e27\u0e13\u0e01\u0e33\u0e44\u0e23\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22", intent["detected_intent"])

        self.assertEqual(intent["detected_intent"], "profit_calculation")
        self.assertEqual(
            entities["missing_entities"],
            ["product_or_service", "price", "cost", "quantity"],
        )

    def test_task_route_diagnostics_include_intent_and_entities(self):
        route = build_task_route({}, f"{CHOUX_CREAM}\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23")
        diagnostics = developer_diagnostics(route)

        self.assertEqual(diagnostics["detected_intent"]["detected_intent"], "pricing_question")
        self.assertIn(CHOUX_CREAM, diagnostics["extracted_entities"]["extracted_entities"]["product_or_service_names"])
        self.assertEqual(route["business_context"]["detected_intent"], "pricing_question")
        self.assertEqual(route["llm_reasoning_context"]["detected_intent"]["detected_intent"], "pricing_question")

    def test_normal_prompt_context_omits_internal_diagnostics(self):
        context = build_prompt_context(
            {},
            planner={"goal": f"{CHOUX_CREAM}\u0e23\u0e32\u0e04\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23", "task_type": "General Business Help"},
            business_context={
                "detected_intent": "pricing_question",
                "intent_confidence": 0.9,
                "extracted_entities": {"product_or_service_names": [CHOUX_CREAM]},
                "missing_entities": [],
                "entity_confidence": 0.8,
            },
            developer_mode=False,
        )

        self.assertNotIn("diagnostics", context)
        self.assertIn("business_intent_entities", context)
        self.assertEqual(context["business_intent_entities"]["detected_intent"], "pricing_question")


if __name__ == "__main__":
    unittest.main()
