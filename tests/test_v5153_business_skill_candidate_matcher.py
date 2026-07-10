import inspect
import unittest
from dataclasses import replace

import brain.business_skill_candidate_matcher as matcher_module
from brain.business_skill import CONTRACTED, COST, PRICING, BusinessSkill
from brain.business_skill_candidate_matcher import (
    build_business_skill_candidate_diagnostics,
    match_business_skill_candidates,
    normalize_candidate_message,
    score_business_skill_candidate,
    top_business_skill_candidate,
)
from brain.business_skill_registry import get_business_skill_registry


class V5153BusinessSkillCandidateMatcherTest(unittest.TestCase):
    def assert_top(self, message, skill_id):
        candidate = top_business_skill_candidate(message)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["skill_id"], skill_id)

    def test_blank_and_unrelated_messages_return_no_candidates(self):
        for message in (None, "", "   ", "hello", "สวัสดี"):
            self.assertEqual(match_business_skill_candidates(message), [])

    def test_seed_skill_messages_rank_expected_skill_first(self):
        cases = (
            ("my cost increased this month", "cost.change_analysis.v1"),
            ("please calculate cost per unit", "cost.per_unit_calculation.v1"),
            ("check the promotion margin", "pricing.promotion_margin_check.v1"),
            ("suggest price for this product", "pricing.basic_price_suggestion.v1"),
            ("explain gross margin", "profitability.gross_margin_explanation.v1"),
            ("we have low stock", "inventory.low_stock_explanation.v1"),
            ("prepare a daily sales summary", "sales.daily_sales_summary.v1"),
            ("explain this cashflow warning", "cashflow.warning_explanation.v1"),
            ("triage this customer complaint", "customer.complaint_triage.v1"),
            ("make a daily task checklist", "operations.daily_task_checklist.v1"),
        )
        for message, expected in cases:
            with self.subTest(message=message):
                self.assert_top(message, expected)

    def test_every_thai_example_question_matches_deterministically(self):
        for skill in get_business_skill_registry():
            for question in skill.example_questions:
                with self.subTest(skill=skill.skill_id, question=question):
                    first = match_business_skill_candidates(question)
                    second = match_business_skill_candidates(question)
                    self.assertEqual(first, second)
                    self.assertEqual(first[0]["skill_id"], skill.skill_id)
                    self.assertIn(question, first[0]["matched_example_questions"])

    def test_normalization_preserves_thai_without_tokenizer(self):
        self.assertEqual(normalize_candidate_message("  ของใกล้หมด!  "), "ของใกล้หมด")

    def test_exact_intent_outranks_loose_metadata_overlap(self):
        exact = BusinessSkill("exact.v1", "1", "Exact", COST, intent_patterns=("unit cost",))
        loose = BusinessSkill("unit.cost.v1", "1", "Unit Cost", COST)
        candidates = match_business_skill_candidates("unit cost", (loose, exact), limit=None)
        self.assertEqual(candidates[0]["skill_id"], "exact.v1")
        self.assertGreater(candidates[0]["candidate_score"], candidates[1]["candidate_score"])

    def test_domain_hint_strengthens_but_does_not_create_candidate(self):
        without_hint = score_business_skill_candidate("suggest price", get_business_skill_registry()[3])
        with_hint = score_business_skill_candidate("suggest price", get_business_skill_registry()[3], PRICING)
        self.assertGreater(with_hint["candidate_score"], without_hint["candidate_score"])
        self.assertEqual(match_business_skill_candidates("hello", business_domain=PRICING), [])

    def test_unknown_domain_hint_is_safe(self):
        self.assert_top("low stock", "inventory.low_stock_explanation.v1")
        self.assert_top("low stock", "inventory.low_stock_explanation.v1")
        result = match_business_skill_candidates("low stock", business_domain="UNKNOWN")
        self.assertFalse(result[0]["domain_hint_matched"])

    def test_minimum_score_and_limit_behavior(self):
        self.assertEqual(match_business_skill_candidates("cost", minimum_score=9), [])
        all_matches = match_business_skill_candidates("cost unit", limit=None, minimum_score=8)
        self.assertGreaterEqual(len(all_matches), 2)
        self.assertEqual(match_business_skill_candidates("cost unit", limit=0), [])
        self.assertEqual(len(match_business_skill_candidates("cost unit", limit=1, minimum_score=8)), 1)
        top_score = all_matches[0]["candidate_score"]
        self.assertTrue(all(c["candidate_score"] >= top_score for c in
                            match_business_skill_candidates("cost unit", limit=None, minimum_score=top_score)))

    def test_ties_preserve_registry_order(self):
        one = BusinessSkill("one.v1", "1", "Alpha Beta", COST)
        two = BusinessSkill("two.v1", "1", "Alpha Beta", COST)
        result = match_business_skill_candidates("alpha beta", (two, one), limit=None)
        self.assertEqual([item["skill_id"] for item in result], ["two.v1", "one.v1"])

    def test_invalid_registry_entries_are_ignored_and_reported(self):
        valid = get_business_skill_registry()[0]
        diagnostics = build_business_skill_candidate_diagnostics(
            "cost increased", (None, {}, replace(valid, skill_id=""), valid)
        )
        self.assertEqual(diagnostics["total_registry_skills_considered"], 1)
        self.assertEqual(diagnostics["invalid_registry_entries"], 3)

    def test_returned_data_cannot_mutate_registry_state(self):
        registry = get_business_skill_registry()
        original_patterns = registry[0].intent_patterns
        candidate = top_business_skill_candidate("cost increased", registry)
        candidate["matched_intent_patterns"].append("changed")
        candidate["candidate_reasons"].clear()
        self.assertEqual(registry[0].intent_patterns, original_patterns)
        self.assertNotIn("changed", registry[0].intent_patterns)

    def test_candidates_are_shadow_only_and_have_no_authority_or_readiness(self):
        candidates = match_business_skill_candidates("cost increased", limit=None)
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertTrue(candidate["candidate_shadow_mode"])
            self.assertFalse(candidate["candidate_selected"])
            self.assertFalse(candidate["candidate_authorized"])
            self.assertIsNone(candidate["candidate_reasoning_ready"])

    def test_diagnostics_preserve_matching_boundary(self):
        result = build_business_skill_candidate_diagnostics("cost increased", business_domain=COST)
        self.assertEqual(result["top_candidate_id"], "cost.change_analysis.v1")
        self.assertIsNone(result["selected_skill_id"])
        self.assertIsNone(result["authorized_skill_id"])
        self.assertTrue(result["shadow_mode"])
        self.assertIn("Current-message-only", result["matching_boundary"])

    def test_current_lifecycle_progression_does_not_change_candidate_boundary(self):
        registry = get_business_skill_registry()
        self.assertEqual(len(registry), 10)
        self.assertEqual(sum(skill.active_status == CONTRACTED for skill in registry), 8)
        self.assertEqual(sum(skill.active_status == "SHADOW_AVAILABLE" for skill in registry), 2)

    def test_module_has_no_legacy_runtime_or_readiness_imports(self):
        source = inspect.getsource(matcher_module)
        forbidden = (
            "brain.business_skill_matcher", "determine_skill_evidence_readiness",
            "import app", "streamlit", "memory", "workflow", "planner", "router",
            "response_authority", "llm",
        )
        # The legacy name is allowed only in the required explanatory docstring.
        code_after_docstring = source[source.find('"""', 3) + 3:]
        self.assertNotIn("brain.business_skill_matcher", code_after_docstring)
        for token in forbidden[1:]:
            self.assertNotIn(token, source.casefold())


if __name__ == "__main__":
    unittest.main()
