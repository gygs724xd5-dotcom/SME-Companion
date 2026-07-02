import unittest

from brain.conversation_priority_engine import WORKFLOW_SWITCH, classify_message_priority
from brain.cost_intent_isolation import is_strong_cost_calculation_message
from brain.response_transformation_engine import transform_response
from brain.workflow_lifecycle import classify_completed_workflow_followup
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN, WORKFLOW_COST_CALCULATION
from brain.workflow_state_machine import (
    detect_workflow_intent,
    new_workflow_state,
    update_workflow_state,
)


MSG_CREATE_THAI_TEA_POST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22"
MSG_GENERAL_AUDIENCE = "\u0e04\u0e19\u0e17\u0e31\u0e48\u0e27\u0e44\u0e1b"
MSG_COST_35_100 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 100 \u0e0a\u0e34\u0e49\u0e19"
MSG_VARIANT = "\u0e02\u0e2d\u0e2d\u0e35\u0e01\u0e41\u0e1a\u0e1a"


def _completed_content_workflow():
    return {
        "workflow_id": WORKFLOW_CONTENT_PLAN,
        "workflow_name": "content_creation",
        "collected_fields": {
            "product": "\u0e0a\u0e32\u0e44\u0e17\u0e22",
            "target_customer": MSG_GENERAL_AUDIENCE,
        },
        "generated_response": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22",
    }


def _completed_cost_workflow():
    return {
        "workflow_id": WORKFLOW_COST_CALCULATION,
        "workflow_name": "cost_calculation",
        "collected_fields": {"unit_cost": 35, "total_units": 100},
        "generated_response": (
            "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\n\n"
            "35 \u0e1a\u0e32\u0e17\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 * 100 \u0e0a\u0e34\u0e49\u0e19 = 3,500 \u0e1a\u0e32\u0e17\n"
            "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19 = 35 \u0e1a\u0e32\u0e17"
        ),
    }


class V5151CostIntentIsolationTest(unittest.TestCase):
    def test_strong_cost_message_overrides_completed_content_context(self):
        app_state = {
            "store": {"last_completed_workflow": _completed_content_workflow()},
            "conversation": {
                "response_memory": {
                    "last_generated_response": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22",
                    "last_response_type": WORKFLOW_CONTENT_PLAN,
                    "last_generation_context": {"workflow": WORKFLOW_CONTENT_PLAN},
                }
            },
        }

        self.assertTrue(is_strong_cost_calculation_message(MSG_COST_35_100))
        self.assertEqual(detect_workflow_intent(MSG_COST_35_100), WORKFLOW_COST_CALCULATION)
        self.assertFalse(classify_completed_workflow_followup(app_state, MSG_COST_35_100)["reuse_completed_workflow"])
        self.assertFalse(transform_response(MSG_COST_35_100, app_state)["handled"])

        content_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
        workflow_state, extracted = update_workflow_state(
            content_state,
            MSG_COST_35_100,
            detected_workflow=WORKFLOW_COST_CALCULATION,
        )

        self.assertEqual(workflow_state["workflow"], WORKFLOW_COST_CALCULATION)
        self.assertEqual(extracted["unit_cost"], 35)
        self.assertEqual(extracted["total_units"], 100)
        self.assertTrue(workflow_state["is_ready"])
        self.assertEqual(workflow_state["calculation_trace"]["selected_formula"], "unit_cost_times_quantity")
        self.assertEqual(workflow_state["calculation_trace"]["computed_total_cost"], 3500)
        self.assertEqual(workflow_state["calculation_trace"]["computed_cost_per_unit"], 35)

    def test_priority_switches_active_content_workflow_to_cost_calculation(self):
        app_state = {
            "workflow": {
                "current_workflow": WORKFLOW_CONTENT_PLAN,
                "workflow_state_v2": new_workflow_state(WORKFLOW_CONTENT_PLAN),
            },
            "conversation": {"workflow_state_v2": new_workflow_state(WORKFLOW_CONTENT_PLAN)},
        }

        decision = classify_message_priority(MSG_COST_35_100, app_state)

        self.assertEqual(decision["classification"], WORKFLOW_SWITCH)
        self.assertEqual(decision["detected_new_intent"], WORKFLOW_COST_CALCULATION)

    def test_variant_after_completed_cost_does_not_reuse_marketing_content(self):
        app_state = {
            "store": {"last_completed_workflow": _completed_cost_workflow()},
            "conversation": {
                "response_memory": {
                    "last_generated_response": "\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e0a\u0e32\u0e44\u0e17\u0e22",
                    "last_response_type": WORKFLOW_CONTENT_PLAN,
                    "last_generation_context": {"workflow": WORKFLOW_CONTENT_PLAN},
                }
            },
        }

        followup = classify_completed_workflow_followup(app_state, MSG_VARIANT)
        transformation = transform_response(MSG_VARIANT, app_state)

        self.assertFalse(followup["reuse_completed_workflow"])
        self.assertTrue(transformation["handled"])
        self.assertEqual(transformation["transformation_source"], "completed_response")


if __name__ == "__main__":
    unittest.main()
