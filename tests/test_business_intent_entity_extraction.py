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

    def test_customer_expensive_reply_intent_and_entities_override_pricing_context(self):
        message = f"\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32{CHOUX_CREAM}\u0e41\u0e1e\u0e07\u0e44\u0e1b \u0e04\u0e27\u0e23\u0e15\u0e2d\u0e1a\u0e22\u0e31\u0e07\u0e44\u0e07"
        intent = detect_business_intent(message)
        entities = extract_business_entities(message, intent["detected_intent"])
        extracted = entities["extracted_entities"]

        self.assertIn(intent["detected_intent"], {"customer_reply", "customer_says_expensive"})
        self.assertEqual(intent["detected_intent"], "customer_says_expensive")
        self.assertEqual(extracted["product_or_service"], CHOUX_CREAM)
        self.assertIn(CHOUX_CREAM, extracted["product_or_service_names"])
        self.assertEqual(extracted["customer_phrase"], "\u0e41\u0e1e\u0e07\u0e44\u0e1b")
        self.assertIn("\u0e41\u0e1e\u0e07\u0e44\u0e1b", extracted["customer_phrases"])

    def test_pricing_unclear_explanation_is_not_pricing_question(self):
        intent = detect_business_intent("pricing_unclear \u0e04\u0e37\u0e2d\u0e2d\u0e30\u0e44\u0e23")

        self.assertIn(intent["detected_intent"], {"label_explanation", "general_question"})
        self.assertNotEqual(intent["detected_intent"], "pricing_question")

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

    def test_task_route_isolates_previous_pricing_context_for_expensive_reply(self):
        message = f"\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e1a\u0e2d\u0e01\u0e27\u0e48\u0e32{CHOUX_CREAM}\u0e41\u0e1e\u0e07\u0e44\u0e1b \u0e04\u0e27\u0e23\u0e15\u0e2d\u0e1a\u0e22\u0e31\u0e07\u0e44\u0e07"
        state = {
            "conversation_memory": {"last_intent": "pricing_question"},
            "business_context": {
                "detected_intent": "pricing_question",
                "business_domain": "01 Sales",
                "business_stage": "Interest",
                "memory_tags": ["pricing_strategy"],
            },
        }

        route = build_task_route(state, message)
        diagnostics = developer_diagnostics(route)

        self.assertEqual(route["detected_intent"]["detected_intent"], "customer_says_expensive")
        self.assertEqual(route["business_intelligence"]["top_skill"], "01.002.customer_says_expensive")
        self.assertEqual(route["business_context"]["previous_context_intent"], "pricing_question")
        self.assertTrue(route["business_context"]["intent_changed"])
        self.assertTrue(route["business_context"]["context_isolation_applied"])
        self.assertTrue(diagnostics["context_isolation_applied"])

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
