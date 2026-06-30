import unittest

from brain.task_router import developer_diagnostics
from brain.workflow_lifecycle import (
    FOLLOWUP_MODE_REUSE_COMPLETED,
    VARIANT_MODE_GENERATE_VARIANT,
    classify_completed_workflow_followup,
)
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import completed_workflow_followup_reply


class V496ConversationIntelligenceTest(unittest.TestCase):
    def _content_completed(self):
        return {
            "workflow_id": WORKFLOW_CONTENT_PLAN,
            "workflow_name": "content_creation",
            "collected_fields": {
                "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22",
                "target_customer": "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e2d\u0e2d\u0e1f\u0e1f\u0e34\u0e28",
            },
        }

    def _cost_completed(self):
        return {
            "workflow_id": WORKFLOW_COST_CALCULATION,
            "workflow_name": "cost_calculation",
            "collected_fields": {"unit_cost": 35, "total_units": 100},
        }

    def test_content_variant_generates_directly(self):
        app_state = {"store": {"last_completed_workflow": self._content_completed()}}
        decision = classify_completed_workflow_followup(app_state, "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a")
        reply = completed_workflow_followup_reply(
            decision["completed_workflow"],
            "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a",
            workflow_variant_mode=decision["workflow_variant_mode"],
        )

        self.assertTrue(decision["reuse_completed_workflow"])
        self.assertEqual(decision["workflow_variant_mode"], VARIANT_MODE_GENERATE_VARIANT)
        self.assertTrue(reply["reply"].startswith("\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a"))
        self.assertNotIn("\u0e2d\u0e22\u0e32\u0e01\u0e44\u0e14\u0e49", reply["reply"])

    def test_multiple_variant_chain_reuses_completed_context(self):
        app_state = {"store": {"last_completed_workflow": self._content_completed()}}
        for message in [
            "\u0e2d\u0e35\u0e01\u0e2d\u0e31\u0e19",
            "\u0e2d\u0e35\u0e01\u0e42\u0e1e\u0e2a\u0e15\u0e4c",
            "\u0e41\u0e1a\u0e1a\u0e43\u0e2b\u0e21\u0e48",
        ]:
            decision = classify_completed_workflow_followup(app_state, message)
            self.assertTrue(decision["reuse_completed_workflow"])
            self.assertEqual(decision["workflow_followup_mode"], FOLLOWUP_MODE_REUSE_COMPLETED)

    def test_short_version_uses_completed_content(self):
        reply = completed_workflow_followup_reply(
            self._content_completed(),
            "\u0e41\u0e1a\u0e1a\u0e2a\u0e31\u0e49\u0e19",
            workflow_variant_mode=VARIANT_MODE_GENERATE_VARIANT,
        )

        self.assertEqual(reply["response_type"], "content_short_version")
        self.assertLessEqual(len([line for line in reply["reply"].splitlines() if line.strip()]), 2)

    def test_long_version_uses_completed_content(self):
        reply = completed_workflow_followup_reply(
            self._content_completed(),
            "\u0e41\u0e1a\u0e1a\u0e22\u0e32\u0e27",
            workflow_variant_mode=VARIANT_MODE_GENERATE_VARIANT,
        )

        self.assertEqual(reply["response_type"], "content_long_version")
        self.assertIn("\u0e0a\u0e32\u0e44\u0e17\u0e22", reply["reply"])

    def test_pricing_followup_reuses_cost_result(self):
        app_state = {"store": {"last_completed_workflow": self._cost_completed()}}
        decision = classify_completed_workflow_followup(app_state, "\u0e02\u0e32\u0e2245\u0e14\u0e35\u0e44\u0e2b\u0e21")

        self.assertTrue(decision["reuse_completed_workflow"])
        self.assertEqual(decision["followup_chain"], ["completed_workflow", "pricing_followup"])

    def test_pricing_percentage(self):
        reply = completed_workflow_followup_reply(self._cost_completed(), "\u0e01\u0e33\u0e44\u0e2340")

        self.assertEqual(reply["calculation_trace"]["requested_profit_percent"], 40)
        self.assertEqual(reply["calculation_trace"]["computed_selling_price"], 49)

    def test_pricing_fixed_profit(self):
        reply = completed_workflow_followup_reply(self._cost_completed(), "\u0e16\u0e49\u0e32\u0e40\u0e2d\u0e32\u0e01\u0e33\u0e44\u0e2315\u0e1a\u0e32\u0e17")

        self.assertEqual(reply["response_reason"], "fixed_profit_from_completed_cost")
        self.assertEqual(reply["calculation_trace"]["computed_selling_price"], 50)

    def test_pricing_fixed_price(self):
        reply = completed_workflow_followup_reply(self._cost_completed(), "\u0e16\u0e49\u0e32\u0e02\u0e32\u0e2250")

        self.assertEqual(reply["response_reason"], "fixed_price_evaluation_from_completed_cost")
        self.assertEqual(reply["calculation_trace"]["computed_profit_per_unit"], 15)

    def test_no_planner_question_when_completed_context_exists(self):
        app_state = {"store": {"last_completed_workflow": self._content_completed()}}
        decision = classify_completed_workflow_followup(
            app_state,
            "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a",
        )
        completed_reply = completed_workflow_followup_reply(
            decision["completed_workflow"],
            "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a",
            workflow_variant_mode=decision["workflow_variant_mode"],
        )

        self.assertTrue(decision["reuse_completed_workflow"])
        self.assertNotIn("\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e2d\u0e30\u0e44\u0e23", completed_reply["reply"])

    def test_completed_workflow_reuse_diagnostics(self):
        diagnostics = developer_diagnostics(
            {
                "response_type": "content_variant",
                "response_source": "completed_workflow",
                "reuse_completed_workflow": True,
                "conversation_style": "chatgpt_continuation",
                "continuation_mode": "completed_workflow_followup",
                "direct_answer_mode": True,
                "planner_skipped": True,
                "reuse_reason": "completed_content_result_available",
                "response_generation_mode": "variant_generation",
            }
        )

        self.assertEqual(diagnostics["conversation_style"], "chatgpt_continuation")
        self.assertEqual(diagnostics["continuation_mode"], "completed_workflow_followup")
        self.assertTrue(diagnostics["direct_answer_mode"])
        self.assertTrue(diagnostics["planner_skipped"])
        self.assertEqual(diagnostics["reuse_reason"], "completed_content_result_available")
        self.assertEqual(diagnostics["response_generation_mode"], "variant_generation")

    def test_conversation_continuation_has_no_assistant_followup_question(self):
        reply = completed_workflow_followup_reply(
            self._content_completed(),
            "\u0e02\u0e32\u0e22\u0e40\u0e01\u0e48\u0e07\u0e01\u0e27\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21",
            workflow_variant_mode=VARIANT_MODE_GENERATE_VARIANT,
        )

        self.assertTrue(reply["reply"].startswith("\u0e44\u0e14\u0e49\u0e40\u0e25\u0e22\u0e04\u0e23\u0e31\u0e1a"))
        self.assertFalse(reply["reply"].rstrip().endswith("\u0e44\u0e2b\u0e21\u0e04\u0e23\u0e31\u0e1a"))


if __name__ == "__main__":
    unittest.main()
