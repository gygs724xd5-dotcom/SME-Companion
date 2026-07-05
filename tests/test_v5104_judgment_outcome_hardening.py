import unittest

from brain.business_judgment_runtime import build_business_judgment_runtime
from brain.judgment_outcome import build_judgment_outcome


class V5104JudgmentOutcomeHardeningTest(unittest.TestCase):
    def test_multiple_contributing_factors_no_forced_sole_cause_or_recommendation(self):
        result = build_business_judgment_runtime({
            "selected_frame": "PROFIT_COMPRESSION",
            "primary_knowledge_ids": ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
            "primary_skill_id": "analyze_profit_compression",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000, "unit_cost": 35},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000, "unit_cost": 45},
            },
        })
        outcome = build_judgment_outcome(result)

        self.assertEqual(outcome["judgment_status"], "MULTIPLE_CONTRIBUTING_FACTORS")
        self.assertEqual(len(outcome["selected_explanations"]), 2)
        self.assertFalse(outcome["decision_boundary"]["recommendation_allowed"])
        self.assertFalse(outcome["decision_boundary"]["planner_allowed"])
        self.assertFalse(outcome["decision_boundary"]["workflow_allowed"])
        self.assertFalse(outcome["decision_boundary"]["tool_allowed"])
        self.assertTrue(all(claim["claim_level"] == "CONTRIBUTING_FACTOR" for claim in outcome["safe_claims"]))

    def test_inventory_stockout_exposure_safe_risk_statement(self):
        result = build_business_judgment_runtime({
            "selected_frame": "INVENTORY_RISK",
            "primary_knowledge_ids": ["INVENTORY_HEALTH", "SUPPLY_RELIABILITY"],
            "primary_skill_id": "analyze_inventory_risk",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {"current_stock": 3, "average_daily_sales": 5, "supplier_lead_time": 3},
        })
        outcome = build_judgment_outcome(result)

        self.assertEqual(outcome["selected_explanations"][0]["candidate_id"], "JUDGMENT::INVENTORY::STOCKOUT_EXPOSURE")
        self.assertTrue(outcome["safe_claims"])
        self.assertNotIn("\u0e2a\u0e31\u0e48\u0e07\u0e40\u0e1e\u0e34\u0e48\u0e21", outcome["response_handoff"]["safe_summary"])

    def test_decision_leak_suppressed_and_recorded(self):
        result = build_business_judgment_runtime({
            "selected_frame": "INVENTORY_RISK",
            "primary_knowledge_ids": ["INVENTORY_HEALTH", "SUPPLY_RELIABILITY"],
            "primary_skill_id": "analyze_inventory_risk",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {"current_stock": 3, "average_daily_sales": 5, "supplier_lead_time": 3},
        })
        outcome = build_judgment_outcome(result, unsafe_output="\u0e14\u0e31\u0e07\u0e19\u0e31\u0e49\u0e19\u0e04\u0e27\u0e23\u0e25\u0e14\u0e23\u0e32\u0e04\u0e32")

        self.assertIn("RECOMMENDATION_LEAK", outcome["validation"]["violations"])
        self.assertTrue(outcome["diagnostics"]["judgment_recommendation_leak_prevented"])
        self.assertFalse(outcome["decision_boundary"]["decision_made"])

    def test_outcome_checksum_deterministic(self):
        payload = {
            "selected_frame": "CAPACITY_CONSTRAINT",
            "primary_knowledge_ids": ["OPERATING_CAPACITY"],
            "primary_skill_id": "analyze_operating_capacity",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {"maximum_capacity": 100, "current_order_volume": 95, "output_time_period": "day"},
        }
        first = build_judgment_outcome(build_business_judgment_runtime(payload))
        second = build_judgment_outcome(build_business_judgment_runtime(payload))
        self.assertEqual(first["snapshot"]["checksum"], second["snapshot"]["checksum"])
        self.assertEqual(first["selected_explanations"][0]["candidate_id"], "JUDGMENT::CAPACITY::DEMAND_NEAR_CAPACITY")


if __name__ == "__main__":
    unittest.main()
