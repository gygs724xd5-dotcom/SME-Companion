import unittest

from brain.entity_runtime import (
    DateEntity,
    EntityPayload,
    MoneyEntity,
    ProductEntity,
    QuantityEntity,
    extract_canonical_entities,
)


class V530EntityRuntimeTest(unittest.TestCase):
    def test_entity_structures_create_canonical_dicts(self):
        entities = [
            MoneyEntity(role="cost", amount=85, normalized_field="cost"),
            QuantityEntity(amount=2, unit="\u0e01\u0e25\u0e48\u0e2d\u0e07"),
            ProductEntity(name="\u0e01\u0e32\u0e41\u0e1f"),
            DateEntity(value="\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49"),
        ]

        for entity in entities:
            with self.subTest(entity=entity.__class__.__name__):
                data = entity.to_dict()
                self.assertIn("entity_id", data)
                self.assertIn("entity_type", data)
                self.assertEqual(data["version"], "5.3.0")
                self.assertEqual(data["source"], "entity_runtime")

        payload = EntityPayload(entities=[entity.to_dict() for entity in entities])
        self.assertEqual(payload.version, "5.3.0")
        self.assertEqual(payload.source, "entity_runtime")

    def test_profit_message_extracts_cost_and_selling_price(self):
        payload = extract_canonical_entities(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 \u0e02\u0e32\u0e22 120 \u0e01\u0e33\u0e44\u0e23\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
        )

        self.assertEqual(payload["slots"]["cost"], 85)
        self.assertEqual(payload["slots"]["selling_price"], 120)
        money_roles = {item["role"] for item in payload["grouped_entities"]["money"]}
        self.assertIn("cost", money_roles)
        self.assertIn("selling_price", money_roles)

    def test_total_cost_and_output_quantity_are_extracted(self):
        payload = extract_canonical_entities(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 200 \u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
        )

        self.assertEqual(payload["slots"]["cost"], 200)
        self.assertEqual(payload["slots"]["quantity"], 100)
        self.assertEqual(payload["slots"]["quantity_unit"], "\u0e0a\u0e34\u0e49\u0e19")
        self.assertEqual(payload["grouped_entities"]["quantity"][0]["role"], "production_output")

    def test_sell_product_unit_price_extracts_product_and_price(self):
        payload = extract_canonical_entities(
            "\u0e02\u0e32\u0e22\u0e01\u0e32\u0e41\u0e1f\u0e41\u0e01\u0e49\u0e27\u0e25\u0e30 50 \u0e1a\u0e32\u0e17"
        )

        self.assertEqual(payload["slots"]["product"], "\u0e01\u0e32\u0e41\u0e1f")
        self.assertEqual(payload["slots"]["price"], 50)
        self.assertEqual(payload["grouped_entities"]["product"][0]["name"], "\u0e01\u0e32\u0e41\u0e1f")
        self.assertEqual(payload["grouped_entities"]["money"][0]["metadata"]["unit"], "\u0e41\u0e01\u0e49\u0e27")

    def test_customer_order_extracts_quantity_and_unit(self):
        payload = extract_canonical_entities(
            "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2a\u0e31\u0e48\u0e07 2 \u0e01\u0e25\u0e48\u0e2d\u0e07"
        )

        self.assertEqual(payload["slots"]["quantity"], 2)
        self.assertEqual(payload["slots"]["quantity_unit"], "\u0e01\u0e25\u0e48\u0e2d\u0e07")
        self.assertEqual(payload["grouped_entities"]["quantity"][0]["amount"], 2)
        self.assertEqual(payload["grouped_entities"]["quantity"][0]["unit"], "\u0e01\u0e25\u0e48\u0e2d\u0e07")

    def test_runtime_foundation_does_not_claim_planner_workflow_or_memory_changes(self):
        payload = extract_canonical_entities("\u0e23\u0e32\u0e04\u0e32 150")

        self.assertEqual(payload["slots"]["price"], 150)
        self.assertFalse(payload["diagnostics"]["planner_routing_changed"])
        self.assertFalse(payload["diagnostics"]["workflow_logic_changed"])
        self.assertFalse(payload["diagnostics"]["business_memory_write"])


if __name__ == "__main__":
    unittest.main()
