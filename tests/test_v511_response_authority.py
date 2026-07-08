import copy
import unittest

from brain.response_authority import (
    CLARIFICATION_QUESTION,
    CONTINUE_WORKFLOW,
    DIRECT_BUSINESS_ANALYSIS,
    DIRECT_SEMANTIC_ANSWER,
    LLM_ASSISTED_RESPONSE,
    START_WORKFLOW,
    decide_response_authority,
)


class V511ResponseAuthorityTest(unittest.TestCase):
    def test_analytical_cost_statement_authorizes_business_analysis(self):
        decision = decide_response_authority(
            "Is 100 baht too expensive for this product?",
            analytical_statement_detected=True,
        )

        self.assertEqual(decision["response_mode"], DIRECT_BUSINESS_ANALYSIS)
        self.assertFalse(decision["workflow_allowed"])
        self.assertEqual(decision["reason"], "analytical_statement_detected")

    def test_semantic_correction_authorizes_direct_semantic_answer(self):
        decision = decide_response_authority(
            "I meant wholesale customer, not retail customer.",
            semantic_correction_detected=True,
        )

        self.assertEqual(decision["response_mode"], DIRECT_SEMANTIC_ANSWER)
        self.assertFalse(decision["workflow_allowed"])
        self.assertEqual(decision["reason"], "semantic_correction_detected")

    def test_explicit_workflow_intent_without_active_workflow_starts_workflow(self):
        decision = decide_response_authority(
            "Help me build a pricing plan.",
            explicit_workflow_intent=True,
        )

        self.assertEqual(decision["response_mode"], START_WORKFLOW)
        self.assertTrue(decision["workflow_allowed"])

    def test_explicit_workflow_intent_with_active_workflow_continues_workflow(self):
        decision = decide_response_authority(
            "The cost is 40 baht.",
            explicit_workflow_intent=True,
            active_workflow={"workflow_id": "pricing", "workflow_status": "collecting"},
        )

        self.assertEqual(decision["response_mode"], CONTINUE_WORKFLOW)
        self.assertTrue(decision["workflow_allowed"])

    def test_reset_boundary_and_completed_context_do_not_continue_workflow(self):
        decision = decide_response_authority(
            "What should I post today?",
            completed_workflow_context={"workflow_id": "pricing"},
            reset_boundary_active=True,
        )

        self.assertNotEqual(decision["response_mode"], CONTINUE_WORKFLOW)
        self.assertFalse(decision["workflow_allowed"])
        self.assertTrue(decision["diagnostics"]["completed_workflow_reuse_blocked"])
        self.assertTrue(decision["diagnostics"]["reset_boundary_respected"])

    def test_completed_workflow_context_alone_does_not_continue_workflow(self):
        decision = decide_response_authority(
            "What should I post today?",
            completed_workflow_context={"workflow_id": "pricing"},
        )

        self.assertEqual(decision["response_mode"], LLM_ASSISTED_RESPONSE)
        self.assertFalse(decision["workflow_allowed"])
        self.assertTrue(decision["diagnostics"]["completed_workflow_reuse_blocked"])

    def test_insufficient_evidence_authorizes_clarification_question(self):
        decision = decide_response_authority(
            "Should I buy more stock?",
            evidence_sufficient=False,
        )

        self.assertEqual(decision["response_mode"], CLARIFICATION_QUESTION)
        self.assertFalse(decision["workflow_allowed"])
        self.assertEqual(decision["reason"], "insufficient_evidence")

    def test_fallback_normal_message_authorizes_llm_assisted_response(self):
        decision = decide_response_authority("Give me some ideas for my shop.")

        self.assertEqual(decision["response_mode"], LLM_ASSISTED_RESPONSE)
        self.assertFalse(decision["workflow_allowed"])
        self.assertTrue(decision["diagnostics"]["llm_assistance_allowed"])

    def test_helper_does_not_mutate_input_dictionaries(self):
        active_workflow = {
            "workflow_id": "pricing",
            "workflow_status": "collecting",
            "collected_fields": {"cost": 40},
        }
        completed_context = {
            "workflow_id": "old_pricing",
            "collected_fields": {"price": 100},
        }
        original_active = copy.deepcopy(active_workflow)
        original_completed = copy.deepcopy(completed_context)

        decide_response_authority(
            "Continue this workflow.",
            explicit_workflow_intent=True,
            active_workflow=active_workflow,
            completed_workflow_context=completed_context,
        )

        self.assertEqual(active_workflow, original_active)
        self.assertEqual(completed_context, original_completed)

    def test_malformed_workflow_dict_does_not_crash(self):
        decision = decide_response_authority(
            "Continue this workflow.",
            explicit_workflow_intent=True,
            active_workflow={"workflow_status": {"unexpected": "dict"}},
        )

        self.assertEqual(decision["response_mode"], START_WORKFLOW)
        self.assertTrue(decision["workflow_allowed"])


if __name__ == "__main__":
    unittest.main()
