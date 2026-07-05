import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_judgment_runtime import build_business_judgment_runtime
from brain.judgment_contracts import CausalClaimLevel
from brain.task_router import build_task_route


BASE = {
    "active_topic": "profit",
    "active_topic_id": "profit_case",
    "selected_frame": "PROFIT_COMPRESSION",
    "primary_knowledge_ids": ["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
    "primary_skill_id": "analyze_profit_compression",
    "judgment_policy": {"analysis_procedure": True},
}


class V5100BusinessJudgmentFoundationTest(unittest.TestCase):
    def test_profit_compression_aov_tentative_contributing_factor(self):
        result = build_business_judgment_runtime({
            **BASE,
            "evidence_package": {
                "previous": {"total_revenue": 100000, "order_count": 1000, "net_profit": 20000},
                "current": {"total_revenue": 105000, "order_count": 1300, "net_profit": 12000},
            },
        })

        self.assertEqual(result["judgment_status"], "JUDGMENT_TENTATIVE")
        selected = result["selected_judgment"]["selected_explanation"]
        self.assertEqual(selected["candidate_id"], "JUDGMENT::PROFITABILITY::AVERAGE_ORDER_VALUE_DECLINE")
        self.assertEqual(selected["causal_claim_level"], CausalClaimLevel.CONTRIBUTING_FACTOR.value)
        self.assertAlmostEqual(result["evidence_summary"]["metrics"]["average_order_value__previous"]["value"], 100.0)
        self.assertAlmostEqual(result["evidence_summary"]["metrics"]["average_order_value"]["value"], 80.769, places=2)
        alternatives = [item["explanation_id"] for item in result["alternative_explanations"]]
        self.assertIn("JUDGMENT::PROFITABILITY::UNIT_COST_INCREASE", alternatives)
        invariants = result["constitutional_invariants"]
        self.assertFalse(invariants["recommendation_generated"])
        self.assertFalse(invariants["decision_made"])
        self.assertFalse(invariants["planner_invoked"])
        self.assertFalse(invariants["workflow_started_by_judgment"])
        self.assertFalse(invariants["business_memory_mutated_by_judgment"])

    def test_judgment_blocks_ineligible_authority_and_critical_conflict(self):
        no_authority = build_business_judgment_runtime({
            **BASE,
            "judgment_policy": {"authority_available": False},
            "evidence_package": {"current": {"total_revenue": 1}},
        })
        self.assertEqual(no_authority["eligibility"]["status"], "BLOCKED_BY_AUTHORITY")
        self.assertFalse(no_authority["judgment_available"])

        conflict = build_business_judgment_runtime({
            **BASE,
            "evidence_package": {
                "unit_cost": [
                    {"value": 35, "source": "dashboard"},
                    {"value": 55, "source": "invoice"},
                ]
            },
        })
        self.assertEqual(conflict["judgment_status"], "CONFLICT_BLOCKED")
        self.assertIsNone(conflict["selected_judgment"])

    def test_route_audit_and_observatory_include_diagnostic_judgment_only(self):
        route = build_task_route({}, "customers increased but profit down")
        audit = route["cognitive_authority_audit"]
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}

        self.assertTrue(audit["judgment_runtime_consulted"])
        self.assertTrue(audit["judgment_eligibility_checked"])
        self.assertIn("Business Judgment", layers)
        self.assertIn("decision_boundary", layers["Business Judgment"]["runtime_state"])
        self.assertFalse(audit["decision_made"])
        self.assertFalse(audit["planner_invoked"])
        self.assertFalse(audit["workflow_started_by_judgment"])
        self.assertFalse(audit["business_memory_mutated_by_judgment"])


if __name__ == "__main__":
    unittest.main()
