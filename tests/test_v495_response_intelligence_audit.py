import unittest

from brain.task_router import developer_diagnostics
from brain.workflow_lifecycle import (
    FOLLOWUP_MODE_REUSE_COMPLETED,
    VARIANT_MODE_GENERATE_VARIANT,
    classify_completed_workflow_followup,
)
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_reply_builder import (
    completed_workflow_followup_reply,
    prepare_content_collection_state,
)
from brain.workflow_state_machine import update_workflow_state


class V495ResponseIntelligenceAuditTest(unittest.TestCase):
    def _completed_content(self):
        return {
            "workflow_id": WORKFLOW_CONTENT_PLAN,
            "workflow_name": "content_creation",
            "collected_fields": {
                "product": "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21",
                "target_customer": "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19",
            },
        }

    def test_content_variant_generates_from_completed_workflow(self):
        reply = completed_workflow_followup_reply(
            self._completed_content(),
            "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a",
            workflow_variant_mode=VARIANT_MODE_GENERATE_VARIANT,
        )

        self.assertEqual(reply["response_type"], "content_variant")
        self.assertEqual(reply["variant_source"], "previous_completed_content")
        self.assertIn("\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21", reply["reply"])
        self.assertNotIn("\u0e21\u0e35\u0e42\u0e1b\u0e23", reply["reply"])

    def test_short_version_summarizes_previous_generated_content(self):
        reply = completed_workflow_followup_reply(
            self._completed_content(),
            "\u0e40\u0e2d\u0e32\u0e41\u0e1a\u0e1a\u0e2a\u0e31\u0e49\u0e19",
            workflow_variant_mode=VARIANT_MODE_GENERATE_VARIANT,
        )

        self.assertEqual(reply["response_type"], "content_short_version")
        self.assertEqual(reply["response_reason"], "summarized_previous_generated_content")
        self.assertLessEqual(len([line for line in reply["reply"].splitlines() if line.strip()]), 2)

    def test_pricing_reuse_applies_requested_profit_markup(self):
        completed = {
            "workflow_id": WORKFLOW_COST_CALCULATION,
            "workflow_name": "cost_calculation",
            "collected_fields": {"unit_cost": 35, "total_units": 100},
        }

        reply = completed_workflow_followup_reply(completed, "\u0e01\u0e33\u0e44\u0e23 30%")

        self.assertEqual(reply["response_type"], "pricing_followup")
        self.assertEqual(reply["calculation_trace"]["computed_selling_price"], 45.5)
        self.assertIn("45.5", reply["reply"])

    def test_completed_workflow_followup_detection_reuses_cost_workflow(self):
        app_state = {"store": {"last_completed_workflow": {
            "workflow_id": WORKFLOW_COST_CALCULATION,
            "collected_fields": {"unit_cost": 35, "total_units": 100},
        }}}

        decision = classify_completed_workflow_followup(app_state, "\u0e01\u0e33\u0e44\u0e23 30%")

        self.assertTrue(decision["reuse_completed_workflow"])
        self.assertEqual(decision["workflow_followup_mode"], FOLLOWUP_MODE_REUSE_COMPLETED)
        self.assertEqual(decision["followup_chain"], ["completed_workflow", "pricing_followup"])

    def test_promotion_is_optional_for_content_generation(self):
        state, _ = update_workflow_state({}, "Create Post", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)
        state, _ = update_workflow_state(state, "\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)
        state, _ = update_workflow_state(state, "\u0e27\u0e31\u0e22\u0e23\u0e38\u0e48\u0e19", detected_workflow=WORKFLOW_CONTENT_PLAN)
        state = prepare_content_collection_state(state)

        self.assertTrue(state["is_ready"])
        self.assertEqual(state["missing_fields"], [])

    def test_response_diagnostics_include_v495_fields(self):
        diagnostics = developer_diagnostics({
            "response_type": "content_variant",
            "response_source": "completed_workflow",
            "response_reason": "generated_variant_from_completed_content_workflow",
            "reuse_completed_workflow": True,
            "variant_source": "previous_completed_content",
            "composer_trace": ["completed_workflow", "content_fields", "variant"],
            "followup_chain": ["completed_workflow", "variant_request"],
        })

        self.assertEqual(diagnostics["response_type"], "content_variant")
        self.assertEqual(diagnostics["response_source"], "completed_workflow")
        self.assertEqual(diagnostics["response_reason"], "generated_variant_from_completed_content_workflow")
        self.assertTrue(diagnostics["reuse_completed_workflow"])
        self.assertEqual(diagnostics["variant_source"], "previous_completed_content")
        self.assertEqual(diagnostics["composer_trace"], ["completed_workflow", "content_fields", "variant"])
        self.assertEqual(diagnostics["followup_chain"], ["completed_workflow", "variant_request"])


if __name__ == "__main__":
    unittest.main()
