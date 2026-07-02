import unittest

from brain.entity_runtime import extract_canonical_entities, inspect_canonical_entities


class V531EntityInspectorGuardTest(unittest.TestCase):
    def test_inspector_returns_debug_summary_sections(self):
        summary = inspect_canonical_entities(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 \u0e1a\u0e32\u0e17 "
            "\u0e02\u0e32\u0e22 120 \u0e1a\u0e32\u0e17"
        )

        self.assertEqual(summary["version"], "5.3.1")
        self.assertEqual(summary["slots"]["cost"], 85)
        self.assertEqual(summary["slots"]["selling_price"], 120)
        self.assertEqual(summary["money_entities_by_role"]["cost"][0]["amount"], 85)
        self.assertEqual(
            summary["money_entities_by_role"]["selling_price"][0]["amount"],
            120,
        )
        self.assertIn("quantity_entities", summary)
        self.assertIn("product_entities", summary)
        self.assertIn("date_entities", summary)
        self.assertIn("grouped_entities", summary)
        self.assertIn("diagnostics", summary)

    def test_inspector_accepts_existing_payload(self):
        payload = extract_canonical_entities(
            "\u0e02\u0e32\u0e22\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"
            "\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 35 \u0e1a\u0e32\u0e17"
        )

        summary = inspect_canonical_entities(payload)

        self.assertEqual(summary["slots"]["product"], "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21")
        self.assertEqual(summary["slots"]["price"], 35)
        self.assertEqual(summary["product_entities"][0]["name"], "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21")

    def test_cost_and_selling_price_guard(self):
        payload = extract_canonical_entities(
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 85 \u0e1a\u0e32\u0e17 "
            "\u0e02\u0e32\u0e22 120 \u0e1a\u0e32\u0e17"
        )

        self.assertEqual(payload["slots"]["cost"], 85)
        self.assertEqual(payload["slots"]["selling_price"], 120)

    def test_sell_choux_creme_unit_price_guard(self):
        payload = extract_canonical_entities(
            "\u0e02\u0e32\u0e22\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21"
            "\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 35 \u0e1a\u0e32\u0e17"
        )

        self.assertEqual(payload["slots"]["product"], "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21")
        self.assertEqual(payload["slots"]["price"], 35)

    def test_total_production_quantity_guard(self):
        payload = extract_canonical_entities(
            "\u0e17\u0e33\u0e44\u0e14\u0e49\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14 "
            "50 \u0e0a\u0e34\u0e49\u0e19"
        )

        self.assertEqual(payload["slots"]["quantity"], 50)
        self.assertEqual(payload["slots"]["quantity_unit"], "\u0e0a\u0e34\u0e49\u0e19")
        self.assertEqual(payload["grouped_entities"]["quantity"][0]["role"], "production_output")

    def test_customer_order_quantity_guard(self):
        payload = extract_canonical_entities(
            "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2a\u0e31\u0e48\u0e07 2 "
            "\u0e01\u0e25\u0e48\u0e2d\u0e07"
        )

        self.assertEqual(payload["slots"]["quantity"], 2)
        self.assertEqual(payload["slots"]["quantity_unit"], "\u0e01\u0e25\u0e48\u0e2d\u0e07")

    def test_raw_material_cost_and_quantity_guard(self):
        payload = extract_canonical_entities(
            "\u0e0b\u0e37\u0e49\u0e2d\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a "
            "300 \u0e1a\u0e32\u0e17 "
            "\u0e17\u0e33\u0e44\u0e14\u0e49 60 \u0e0a\u0e34\u0e49\u0e19"
        )

        self.assertEqual(payload["slots"]["cost"], 300)
        self.assertEqual(payload["slots"]["quantity"], 60)

    def test_entity_runtime_does_not_claim_cross_layer_changes(self):
        summary = inspect_canonical_entities("\u0e23\u0e32\u0e04\u0e32 150")

        self.assertFalse(summary["diagnostics"]["planner_routing_changed"])
        self.assertFalse(summary["diagnostics"]["workflow_logic_changed"])
        self.assertFalse(summary["diagnostics"]["business_memory_write"])


if __name__ == "__main__":
    unittest.main()
