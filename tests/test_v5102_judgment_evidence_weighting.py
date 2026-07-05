import unittest

from brain.business_judgment_runtime import build_business_judgment_runtime
from brain.judgment_candidate_registry import JudgmentCandidateRegistry
from brain.judgment_evidence_weighting import weigh_evidence_for_candidates


class V5102JudgmentEvidenceWeightingTest(unittest.TestCase):
    def test_weighting_orders_truth_freshness_completeness_and_scope(self):
        registry = JudgmentCandidateRegistry()
        candidate = registry.get("JUDGMENT::INVENTORY::STOCKOUT_EXPOSURE").to_dict()
        weighted = weigh_evidence_for_candidates(
            {
                "current_stock": {"value": 3, "truth_classification": "OBSERVED", "freshness": "CURRENT", "entity_scope": "store"},
                "average_daily_sales": {"value": 5, "truth_classification": "UNVERIFIED", "freshness": "CURRENT", "entity_scope": "store"},
                "supplier_lead_time": {"value": 3, "truth_classification": "OBSERVED", "freshness": "STALE", "entity_scope": "store"},
                "wrong_scope_metric": {"value": 9, "wrong_scope": True},
            },
            [candidate],
        )
        weights = {item["metric_id"]: item for item in weighted["weights"]}

        self.assertGreater(weights["current_stock"]["effective_weight"], weights["average_daily_sales"]["effective_weight"])
        self.assertEqual(weights["supplier_lead_time"]["weight_class"], "NOT_USABLE")
        self.assertEqual(weights["current_stock"]["evidence_role"], "CORE_SUPPORT")
        self.assertFalse(any("%" in str(item.get("effective_weight")) for item in weighted["weights"]))

    def test_non_comparable_periods_excluded_and_missing_not_zero(self):
        result = build_business_judgment_runtime({
            "selected_frame": "PROFIT_COMPRESSION",
            "primary_knowledge_ids": ["PROFITABILITY_STRUCTURE"],
            "primary_skill_id": "analyze_profit_compression",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {
                "total_revenue": {"metric_id": "total_revenue", "value": 100000, "timeframe": "month"},
                "previous_total_revenue": {"metric_id": "total_revenue", "value": 30000, "timeframe": "week"},
                "order_count": {"value": 1000},
            },
        })
        excluded = result["evidence_summary"]["weighted_evidence"]["excluded_evidence"]
        self.assertTrue(any(item["metric_id"] == "total_revenue" and "not_comparable" in item["limiting_factors"] for item in excluded))
        self.assertNotEqual(result["judgment_status"], "JUDGMENT_SUPPORTED")

    def test_derived_evidence_dependency_group_prevents_double_counting(self):
        result = build_business_judgment_runtime({
            "selected_frame": "PROFIT_COMPRESSION",
            "primary_knowledge_ids": ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
            "primary_skill_id": "analyze_profit_compression",
            "judgment_policy": {"analysis_procedure": True},
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000},
            },
        })
        groups = result["evidence_summary"]["weighted_evidence"]["dependency_groups"]
        self.assertTrue(any(group["dependency_type"] == "DERIVED" for group in groups))
        self.assertTrue(result["diagnostics"]["evidence_double_count_prevented"])


if __name__ == "__main__":
    unittest.main()
