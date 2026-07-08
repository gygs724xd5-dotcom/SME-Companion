import copy
import unittest

from brain.evidence_gap import (
    AMBIGUOUS_INTENT,
    CALCULATION_INPUT_GAP,
    CONTRADICTORY_EVIDENCE,
    MISSING_REQUIRED_FIELD,
    NO_GAP,
    WORKFLOW_REQUIREMENT_GAP,
    evaluate_evidence_gap,
)


class V5121EvidenceGapTest(unittest.TestCase):
    def test_all_required_fields_present_returns_no_gap(self):
        profile = evaluate_evidence_gap(
            "Use 40 baht cost and 100 baht price.",
            required_fields=["cost", "price"],
            provided_fields={"cost": 40, "price": 100},
        )

        self.assertEqual(profile["gap_type"], NO_GAP)
        self.assertTrue(profile["evidence_sufficient"])
        self.assertFalse(profile["gap_detected"])

    def test_one_required_field_missing_asks_only_that_field(self):
        profile = evaluate_evidence_gap(
            "The price is 100 baht.",
            required_fields=["price", "customer_segment"],
            provided_fields={"price": 100},
        )

        self.assertEqual(profile["gap_type"], MISSING_REQUIRED_FIELD)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["missing_fields"], ["customer_segment"])
        self.assertEqual(profile["smallest_next_question"], "What is the customer segment?")
        self.assertNotIn("price", profile["smallest_next_question"])

    def test_multiple_required_fields_missing_asks_first_missing_field_only(self):
        profile = evaluate_evidence_gap(
            "Help me decide.",
            required_fields=["customer_segment", "product", "channel"],
            provided_fields={},
        )

        self.assertEqual(profile["gap_type"], MISSING_REQUIRED_FIELD)
        self.assertEqual(profile["missing_fields"], ["customer_segment", "product", "channel"])
        self.assertEqual(profile["smallest_next_question"], "What is the customer segment?")
        self.assertNotIn("product", profile["smallest_next_question"])
        self.assertNotIn("channel", profile["smallest_next_question"])

    def test_conflicting_evidence_fails_closed(self):
        profile = evaluate_evidence_gap(
            "The price is both 80 and 100 baht.",
            conflicting_fields=["price"],
            required_fields=["price"],
            provided_fields={"price": 100},
        )

        self.assertEqual(profile["gap_type"], CONTRADICTORY_EVIDENCE)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["conflicting_fields"], ["price"])

    def test_reset_boundary_prevents_completed_context_from_satisfying_evidence(self):
        profile = evaluate_evidence_gap(
            "Should we continue?",
            required_fields=["customer_segment"],
            completed_workflow_context={"customer_segment": "restaurants"},
            reset_boundary_active=True,
        )

        self.assertEqual(profile["gap_type"], MISSING_REQUIRED_FIELD)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["missing_fields"], ["customer_segment"])
        self.assertEqual(profile["diagnostics"]["stale_completed_fields_blocked"], ["customer_segment"])

    def test_completed_workflow_context_alone_does_not_satisfy_workflow_requirement_after_reset(self):
        profile = evaluate_evidence_gap(
            "Continue pricing.",
            active_workflow_requirements=["unit_cost"],
            completed_workflow_context={"unit_cost": 40},
            reset_boundary_active=True,
        )

        self.assertEqual(profile["gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["missing_fields"], ["unit_cost"])

    def test_ambiguous_intent_returns_ambiguous_intent_gap(self):
        profile = evaluate_evidence_gap("This one.", intent_ambiguous=True)

        self.assertEqual(profile["gap_type"], AMBIGUOUS_INTENT)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["smallest_next_question"], "What do you want to do?")

    def test_missing_workflow_requirement_returns_workflow_gap(self):
        profile = evaluate_evidence_gap(
            "Run the calculation.",
            active_workflow_requirements=["unit_cost", "sale_price"],
            provided_fields={"unit_cost": 40},
        )

        self.assertEqual(profile["gap_type"], WORKFLOW_REQUIREMENT_GAP)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["missing_fields"], ["sale_price"])
        self.assertEqual(profile["smallest_next_question"], "What is the sale price?")

    def test_can_answer_with_assumptions_keeps_gap_detected_but_sufficient(self):
        notes = ["Assume the customer segment is retail."]

        profile = evaluate_evidence_gap(
            "Draft a simple post.",
            required_fields=["customer_segment"],
            can_answer_with_assumptions=True,
            assumption_notes=notes,
        )

        self.assertEqual(profile["gap_type"], MISSING_REQUIRED_FIELD)
        self.assertTrue(profile["gap_detected"])
        self.assertTrue(profile["evidence_sufficient"])
        self.assertTrue(profile["can_answer_with_assumptions"])
        self.assertEqual(profile["assumption_notes"], notes)
        self.assertIsNone(profile["smallest_next_question"])

    def test_helper_does_not_mutate_input_dictionaries_or_lists(self):
        required_fields = ["customer_segment", "price"]
        provided_fields = {"price": 100, "nested": {"cost": 40}}
        known_context = {"business": {"customer_segment": "retail"}}
        conflicting_fields = ["inventory"]
        workflow_requirements = ["price"]
        completed_context = {"customer_segment": "old retail"}
        assumption_notes = ["Assume current campaign."]
        originals = copy.deepcopy(
            (
                required_fields,
                provided_fields,
                known_context,
                conflicting_fields,
                workflow_requirements,
                completed_context,
                assumption_notes,
            )
        )

        evaluate_evidence_gap(
            "Check this.",
            required_fields=required_fields,
            provided_fields=provided_fields,
            known_context=known_context,
            conflicting_fields=conflicting_fields,
            active_workflow_requirements=workflow_requirements,
            completed_workflow_context=completed_context,
            assumption_notes=assumption_notes,
        )

        self.assertEqual(
            (
                required_fields,
                provided_fields,
                known_context,
                conflicting_fields,
                workflow_requirements,
                completed_context,
                assumption_notes,
            ),
            originals,
        )

    def test_malformed_inputs_do_not_crash_and_return_stable_diagnostics(self):
        profile = evaluate_evidence_gap(
            None,
            required_fields={"unexpected": "dict"},
            provided_fields=["not", "dict"],
            known_context="bad context",
            completed_workflow_context=["not", "dict"],
            active_workflow_requirements={"bad": "shape"},
            conflicting_fields={"field": "price"},
            assumption_notes="bad notes",
        )

        self.assertEqual(profile["gap_type"], CONTRADICTORY_EVIDENCE)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertIsInstance(profile["diagnostics"], dict)
        self.assertIn("provided_fields", profile["diagnostics"]["malformed_inputs"])
        self.assertIn("known_context", profile["diagnostics"]["malformed_inputs"])
        self.assertIn("evidence_gap_type", profile["diagnostics"])

    def test_confidence_is_clamped_between_zero_and_one(self):
        high = evaluate_evidence_gap("High confidence.", confidence=3.5)
        low = evaluate_evidence_gap("Low confidence.", confidence=-2)
        malformed = evaluate_evidence_gap("Bad confidence.", confidence="not-a-number")

        self.assertEqual(high["confidence"], 1.0)
        self.assertEqual(low["confidence"], 0.0)
        self.assertEqual(malformed["confidence"], 0.0)

    def test_no_unnecessary_question_when_evidence_is_sufficient(self):
        profile = evaluate_evidence_gap(
            "The customer segment is retail.",
            required_fields=["customer_segment"],
            provided_fields={"customer_segment": "retail"},
        )

        self.assertEqual(profile["gap_type"], NO_GAP)
        self.assertIsNone(profile["smallest_next_question"])

    def test_known_context_can_satisfy_required_fields_when_not_reset(self):
        profile = evaluate_evidence_gap(
            "Use our usual audience.",
            required_fields=["customer_segment"],
            known_context={"customer_segment": "local cafe owners"},
        )

        self.assertEqual(profile["gap_type"], NO_GAP)
        self.assertTrue(profile["evidence_sufficient"])

    def test_fallback_empty_message_behavior_is_deterministic(self):
        first = evaluate_evidence_gap("")
        second = evaluate_evidence_gap(None)

        self.assertEqual(first["gap_type"], NO_GAP)
        self.assertTrue(first["evidence_sufficient"])
        self.assertEqual(first["reason"], "empty_message_no_required_evidence")
        self.assertEqual(first, second)

    def test_missing_calculation_field_returns_calculation_input_gap(self):
        profile = evaluate_evidence_gap(
            "Calculate margin.",
            required_fields=["unit_cost", "sale_price"],
            provided_fields={"sale_price": 100},
        )

        self.assertEqual(profile["gap_type"], CALCULATION_INPUT_GAP)
        self.assertFalse(profile["evidence_sufficient"])
        self.assertEqual(profile["smallest_next_question"], "What is the unit cost?")


if __name__ == "__main__":
    unittest.main()
