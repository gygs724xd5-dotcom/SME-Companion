import copy
import unittest

from brain.business_situation import (
    ANALYTICAL,
    CASHFLOW,
    CASHFLOW_CONCERN,
    CAUTIOUS,
    COST,
    COST_CHANGE,
    COST_CORRECTION,
    CORRECTIVE,
    CUSTOMER,
    CUSTOMER_ISSUE,
    GENERAL,
    HIGH,
    INVENTORY,
    INVENTORY_RISK,
    MEDIUM,
    NEUTRAL,
    NO_BUSINESS_SITUATION,
    OWNER_ADVISORY,
    PLANNING_DECISION,
    PRICING,
    PRICING_DECISION,
    PROFIT_MARGIN_RISK,
    WORKFLOW_STATUS,
    evaluate_business_situation,
)


class V5131BusinessSituationTest(unittest.TestCase):
    def test_analytical_cost_statement_returns_cost_change(self):
        profile = evaluate_business_situation("Supplier cost went up from 40 to 55 baht.")

        self.assertTrue(profile["situation_detected"])
        self.assertEqual(profile["situation_type"], COST_CHANGE)
        self.assertEqual(profile["business_domain"], COST)
        self.assertEqual(profile["perspective_stance"], ANALYTICAL)

    def test_cost_correction_returns_corrective_cost_profile(self):
        profile = evaluate_business_situation("Correction: I meant the unit cost is 45 baht, not 40.")

        self.assertEqual(profile["situation_type"], COST_CORRECTION)
        self.assertEqual(profile["business_domain"], COST)
        self.assertEqual(profile["perspective_stance"], CORRECTIVE)

    def test_pricing_decision_question_returns_pricing_decision(self):
        profile = evaluate_business_situation("What price should I charge for this product?")

        self.assertEqual(profile["situation_type"], PRICING_DECISION)
        self.assertEqual(profile["business_domain"], PRICING)
        self.assertEqual(profile["perspective_stance"], OWNER_ADVISORY)

    def test_margin_profit_concern_returns_margin_risk(self):
        profile = evaluate_business_situation("My margin is too low and this product may not be profitable.")

        self.assertEqual(profile["situation_type"], PROFIT_MARGIN_RISK)
        self.assertIn(profile["risk_level"], {MEDIUM, HIGH})
        self.assertEqual(profile["perspective_stance"], ANALYTICAL)

    def test_inventory_shortage_returns_inventory_risk(self):
        profile = evaluate_business_situation("We have a stock shortage and may run out tomorrow.")

        self.assertEqual(profile["situation_type"], INVENTORY_RISK)
        self.assertEqual(profile["business_domain"], INVENTORY)
        self.assertEqual(profile["risk_level"], HIGH)

    def test_customer_complaint_returns_customer_issue(self):
        profile = evaluate_business_situation("A customer complained about the delivery and wants a refund.")

        self.assertEqual(profile["situation_type"], CUSTOMER_ISSUE)
        self.assertEqual(profile["business_domain"], CUSTOMER)

    def test_cashflow_shortage_returns_cashflow_concern(self):
        profile = evaluate_business_situation("We are short on cash and cannot pay suppliers this week.")

        self.assertEqual(profile["situation_type"], CASHFLOW_CONCERN)
        self.assertEqual(profile["business_domain"], CASHFLOW)
        self.assertEqual(profile["risk_level"], HIGH)

    def test_planning_next_step_returns_owner_advisory_posture(self):
        profile = evaluate_business_situation("What should I do next to improve the shop?")

        self.assertEqual(profile["situation_type"], PLANNING_DECISION)
        self.assertEqual(profile["recommended_response_posture"], OWNER_ADVISORY)

    def test_workflow_status_does_not_become_direct_business_advice(self):
        profile = evaluate_business_situation(
            "What is the workflow status?",
            active_workflow={"workflow_id": "pricing", "workflow_status": "collecting"},
        )

        self.assertEqual(profile["situation_type"], WORKFLOW_STATUS)
        self.assertEqual(profile["business_domain"], GENERAL)
        self.assertEqual(profile["recommended_response_posture"], "OPERATIONAL")
        self.assertIn("workflow", profile["reasoning_summary"])

    def test_casual_non_business_message_returns_no_business_situation(self):
        profile = evaluate_business_situation("Hi, thanks.")

        self.assertFalse(profile["situation_detected"])
        self.assertEqual(profile["situation_type"], NO_BUSINESS_SITUATION)
        self.assertEqual(profile["business_domain"], GENERAL)
        self.assertEqual(profile["perspective_stance"], NEUTRAL)

    def test_insufficient_evidence_profile_lowers_confidence_and_uses_cautious_stance(self):
        baseline = evaluate_business_situation("What price should I charge for this product?")
        profile = evaluate_business_situation(
            "What price should I charge for this product?",
            evidence_gap_profile={"evidence_sufficient": False, "gap_type": "MISSING_BUSINESS_CONTEXT"},
        )

        self.assertEqual(profile["situation_type"], PRICING_DECISION)
        self.assertEqual(profile["perspective_stance"], CAUTIOUS)
        self.assertLess(profile["confidence"], baseline["confidence"])

    def test_contradictory_evidence_profile_fails_cautious(self):
        profile = evaluate_business_situation(
            "My cost went up from 40 to 55 baht.",
            evidence_gap_profile={
                "evidence_sufficient": False,
                "gap_type": "CONTRADICTORY_EVIDENCE",
                "conflicting_fields": ["cost"],
            },
        )

        self.assertEqual(profile["situation_type"], COST_CHANGE)
        self.assertEqual(profile["perspective_stance"], CAUTIOUS)
        self.assertTrue(profile["diagnostics"]["evidence_contradictory"])
        self.assertLessEqual(profile["confidence"], 0.45)

    def test_reset_boundary_prevents_completed_workflow_context_from_dominating(self):
        profile = evaluate_business_situation(
            "What should I do next?",
            completed_workflow_context={"business_domain": "pricing", "workflow_id": "old_pricing"},
            reset_boundary_active=True,
        )

        self.assertEqual(profile["situation_type"], PLANNING_DECISION)
        self.assertEqual(profile["business_domain"], GENERAL)
        self.assertFalse(profile["diagnostics"]["completed_workflow_context_counted"])

    def test_business_context_can_inform_generic_business_related_message(self):
        profile = evaluate_business_situation(
            "How should I improve this?",
            business_context={"business_domain": "inventory", "current_problem": "low stock"},
        )

        self.assertTrue(profile["situation_detected"])
        self.assertEqual(profile["business_domain"], INVENTORY)
        self.assertIn("Business context", profile["assumptions"][0])

    def test_helper_does_not_mutate_input_dictionaries_or_lists(self):
        extracted_entities = {"product": "tea", "numbers": [40, 55]}
        evidence_gap_profile = {"evidence_sufficient": False, "gap_type": "MISSING_BUSINESS_CONTEXT"}
        business_context = {"business_domain": "pricing", "nested": {"current_product": "tea"}}
        active_workflow = {"workflow_id": "pricing", "workflow_status": "collecting"}
        completed_workflow_context = {"business_domain": "cost"}
        calculation_result = {"margin": 0.2}
        recent_context = [{"message": "old"}]
        originals = copy.deepcopy(
            (
                extracted_entities,
                evidence_gap_profile,
                business_context,
                active_workflow,
                completed_workflow_context,
                calculation_result,
                recent_context,
            )
        )

        evaluate_business_situation(
            "Should I raise the price?",
            extracted_entities=extracted_entities,
            evidence_gap_profile=evidence_gap_profile,
            business_context=business_context,
            active_workflow=active_workflow,
            completed_workflow_context=completed_workflow_context,
            calculation_result=calculation_result,
            recent_context=recent_context,
        )

        self.assertEqual(
            (
                extracted_entities,
                evidence_gap_profile,
                business_context,
                active_workflow,
                completed_workflow_context,
                calculation_result,
                recent_context,
            ),
            originals,
        )

    def test_malformed_inputs_do_not_crash_and_return_stable_diagnostics(self):
        profile = evaluate_business_situation(
            None,
            extracted_entities=["bad"],
            evidence_gap_profile=["bad"],
            business_context=["bad"],
            active_workflow=["bad"],
            completed_workflow_context=["bad"],
            calculation_result=["bad"],
            recent_context={"bad": "shape"},
            truth_confidence="bad",
        )

        self.assertEqual(profile["situation_type"], NO_BUSINESS_SITUATION)
        self.assertIsInstance(profile["diagnostics"], dict)
        self.assertIn("business_situation_profile_version", profile["diagnostics"])
        self.assertIn("business_context", profile["diagnostics"]["malformed_inputs"])
        self.assertEqual(profile["confidence"], 0.0)

    def test_confidence_is_clamped_between_zero_and_one(self):
        high = evaluate_business_situation("What price should I charge?", truth_confidence=3.5)
        low = evaluate_business_situation("What price should I charge?", truth_confidence=-2)

        self.assertEqual(high["confidence"], 0.86)
        self.assertEqual(low["confidence"], 0.0)

    def test_owner_goal_increases_owner_attention_usefulness_without_final_answer_text(self):
        profile = evaluate_business_situation(
            "What should I do next?",
            owner_goal="increase profit this month",
        )

        self.assertEqual(profile["situation_type"], PLANNING_DECISION)
        self.assertIn("increase profit this month", profile["owner_attention"])
        self.assertNotIn("final_answer", profile)


if __name__ == "__main__":
    unittest.main()
