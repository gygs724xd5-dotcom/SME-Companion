import unittest

from brain.business_judgment_runtime import build_business_judgment_runtime
from brain.judgment_revision_runtime import revise_business_judgment


BASE = {
    "selected_frame": "PROFIT_COMPRESSION",
    "primary_knowledge_ids": ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
    "primary_skill_id": "analyze_profit_compression",
    "judgment_policy": {"analysis_procedure": True},
}


class V5103JudgmentRevisionRuntimeTest(unittest.TestCase):
    def test_new_evidence_expands_to_multiple_contributing_factors(self):
        previous = build_business_judgment_runtime({
            **BASE,
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000},
            },
        })
        revision = revise_business_judgment(previous, {
            **BASE,
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000, "unit_cost": 35},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000, "unit_cost": 45},
            },
        }, revision_trigger="NEW_SUPPORTING_EVIDENCE")

        self.assertEqual(revision["revision_status"], "EXPANDED")
        self.assertIn("JUDGMENT::PROFITABILITY::UNIT_COST_INCREASE", revision["current_selected_candidates"])
        self.assertTrue(revision["user_visible_revision_required"])
        self.assertIn("previous", revision["provenance"])

    def test_correction_withdraws_claim_under_conflict(self):
        previous = build_business_judgment_runtime({
            **BASE,
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000},
            },
        })
        revision = revise_business_judgment(previous, {
            **BASE,
            "evidence_package": {
                "average_order_value": [
                    {"value": 80.8, "source": "dashboard"},
                    {"value": 100.0, "source": "corrected_source"},
                ]
            },
        }, revision_trigger="USER_CORRECTION")

        self.assertEqual(revision["revision_status"], "WITHDRAWN")
        self.assertTrue(revision["withdrawn_claims"])
        self.assertTrue(revision["user_visible_revision_required"])


if __name__ == "__main__":
    unittest.main()
