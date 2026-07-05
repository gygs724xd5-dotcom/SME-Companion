import unittest

from brain.judgment_candidate_registry import (
    JudgmentCandidateRegistry,
    retrieve_judgment_candidates,
    validate_judgment_candidate_registry,
)


class V5101JudgmentCandidateRegistryTest(unittest.TestCase):
    def test_registry_contract_validation_and_claim_caps(self):
        registry = JudgmentCandidateRegistry()
        validation = validate_judgment_candidate_registry(registry)
        ids = [item.candidate_id for item in registry.list()]

        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("JUDGMENT::PROFITABILITY::AVERAGE_ORDER_VALUE_DECLINE", ids)
        self.assertIn("JUDGMENT::INVENTORY::STOCKOUT_EXPOSURE", ids)
        for candidate in registry.list():
            self.assertNotIn(candidate.maximum_claim_level, {"PRIMARY_DRIVER", "CONFIRMED_CAUSE"})
            self.assertTrue(candidate.required_knowledge_ids)
            self.assertTrue(candidate.forbidden_outputs)
            self.assertTrue(candidate.misuse_constraints)
            self.assertTrue(candidate.provenance)

    def test_approved_candidates_load_and_drafts_remain_diagnostic(self):
        result = retrieve_judgment_candidates(
            selected_frame="PROFIT_COMPRESSION",
            selected_knowledge_ids=["PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"],
            evidence_package={"average_order_value": {"value": 80}},
        )

        self.assertIn("JUDGMENT::PROFITABILITY::AVERAGE_ORDER_VALUE_DECLINE", result["available_candidate_ids"])
        self.assertIn("JUDGMENT::PROFITABILITY::DISCOUNT_PRESSURE", result["deferred_candidate_ids"])
        self.assertLessEqual(len(result["available_candidate_ids"]), 5)

    def test_conflict_matrix_is_deterministic(self):
        conflicts = [item.to_dict() for item in JudgmentCandidateRegistry().conflicts()]
        self.assertIn(
            {
                "candidate_a": "JUDGMENT::PROFITABILITY::AVERAGE_ORDER_VALUE_DECLINE",
                "candidate_b": "JUDGMENT::PROFITABILITY::UNIT_COST_INCREASE",
                "conflict_type": "COEXISTING",
                "coexistence_allowed": True,
                "resolution_metrics": ["average_order_value", "unit_cost"],
            },
            conflicts,
        )


if __name__ == "__main__":
    unittest.main()
