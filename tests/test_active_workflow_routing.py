import unittest

from brain.business_context_engine import build_business_context
from brain.response_intelligence_engine import select_planner_first_response
from brain.task_router import build_task_route
from brain.workflow_readiness import WORKFLOW_CONTENT_PLAN
from brain.workflow_state_machine import new_workflow_state, update_workflow_state


REPEATED_CREATE_POST_QUESTION = "โพสต์นี้จะโฟกัสสินค้าหรือประเภทร้านอะไรครับ"


def _active_content_plan_app_state() -> dict:
    workflow_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
    return {
        "workflow": {
            "current_workflow": WORKFLOW_CONTENT_PLAN,
            "workflow": WORKFLOW_CONTENT_PLAN,
            "workflow_step": workflow_state["step"],
            "step": workflow_state["step"],
            "workflow_data": {},
            "workflow_state_v2": workflow_state,
            "is_ready": False,
        },
        "conversation": {"workflow_state_v2": workflow_state},
        "store": {},
        "receipt": {},
        "dashboard": {},
        "ui": {},
        "developer": {},
    }


def _content_plan_waiting_for(field: str, *, collected_fields: dict | None = None) -> dict:
    workflow_state = new_workflow_state(WORKFLOW_CONTENT_PLAN)
    workflow_state["required_fields"] = [field]
    workflow_state["collected_fields"] = dict(collected_fields or {})
    workflow_state["missing_fields"] = [field]
    workflow_state["is_ready"] = False
    return workflow_state


class ActiveWorkflowRoutingTest(unittest.TestCase):
    def test_active_content_plan_answer_updates_fields_without_repeating_question(self):
        state = _active_content_plan_app_state()
        route = build_task_route(state, "ชูครีม")

        planner_first = select_planner_first_response(route, [])
        self.assertFalse(planner_first["handled"])

        workflow_state, extracted = update_workflow_state(
            state["workflow"]["workflow_state_v2"],
            "ชูครีม",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["product"], "ชูครีม")
        self.assertEqual(workflow_state["collected_fields"]["product"], "ชูครีม")
        self.assertNotIn("product_or_business_type", workflow_state["missing_fields"])
        self.assertEqual(workflow_state["step"], "ready_to_generate")

    def test_select_planner_first_does_not_intercept_active_workflow_continuation(self):
        route = {
            "planner_output": {
                "workflow": WORKFLOW_CONTENT_PLAN,
                "next_step": "collect_missing_information",
                "missing_information": ["product_or_business_type"],
            },
            "llm_reasoning_context": {
                "workflow": {
                    "workflow_state_v2": new_workflow_state(WORKFLOW_CONTENT_PLAN),
                },
            },
            "intent_resolution": {"resolved_workflow": WORKFLOW_CONTENT_PLAN},
        }

        result = select_planner_first_response(route, [])

        self.assertFalse(result["handled"])

    def test_quick_action_create_post_then_product_answer_does_not_repeat_missing_question(self):
        state = _active_content_plan_app_state()
        route = build_task_route(state, "สินค้า")

        planner_first = select_planner_first_response(route, [])
        self.assertFalse(planner_first["handled"])
        self.assertNotEqual(planner_first.get("reply"), REPEATED_CREATE_POST_QUESTION)

        workflow_state, extracted = update_workflow_state(
            state["workflow"]["workflow_state_v2"],
            "สินค้า",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["product"], "สินค้า")
        self.assertFalse(workflow_state["missing_fields"])

    def test_product_extracts_from_bare_thai_answer(self):
        workflow_state, extracted = update_workflow_state(
            new_workflow_state(WORKFLOW_CONTENT_PLAN),
            "ชูครีม",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["product"], "ชูครีม")
        self.assertEqual(workflow_state["collected_fields"]["product"], "ชูครีม")
        self.assertFalse(workflow_state["missing_fields"])

    def test_initial_create_post_starts_real_content_workflow_state(self):
        route = build_task_route({}, "สร้างโพสต์")
        self.assertEqual((route.get("planner_output") or {}).get("workflow"), WORKFLOW_CONTENT_PLAN)

        workflow_state, extracted = update_workflow_state(
            {},
            "สร้างโพสต์",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted, {})
        self.assertEqual(workflow_state["workflow"], WORKFLOW_CONTENT_PLAN)
        self.assertEqual(workflow_state["collected_fields"], {})
        self.assertIn("product_or_business_type", workflow_state["missing_fields"])
        self.assertEqual(workflow_state["step"], "collecting_content_inputs")
        self.assertFalse(workflow_state["is_ready"])

    def test_product_extracts_from_thai_product_name_pattern(self):
        workflow_state, extracted = update_workflow_state(
            new_workflow_state(WORKFLOW_CONTENT_PLAN),
            "สินค้า ชื่อ ชูครีม",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["product"], "ชูครีม")
        self.assertEqual(workflow_state["collected_fields"]["product"], "ชูครีม")
        self.assertFalse(workflow_state["missing_fields"])

    def test_target_customer_extracts_from_short_thai_answer(self):
        workflow_state, extracted = update_workflow_state(
            _content_plan_waiting_for("target_customer"),
            "วัยรุ่น",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["target_customer"], "วัยรุ่น")
        self.assertEqual(workflow_state["collected_fields"]["target_customer"], "วัยรุ่น")
        self.assertFalse(workflow_state["missing_fields"])

    def test_promotion_extracts_from_discount_answer(self):
        workflow_state, extracted = update_workflow_state(
            _content_plan_waiting_for("promotion"),
            "ลด 10%",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["promotion"], "ลด 10%")
        self.assertEqual(workflow_state["collected_fields"]["promotion"], "ลด 10%")
        self.assertFalse(workflow_state["missing_fields"])

    def test_business_type_extracts_from_shop_answer(self):
        workflow_state, extracted = update_workflow_state(
            _content_plan_waiting_for("business_type"),
            "ร้านขายขนม",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["business_type"], "ร้านขายขนม")
        self.assertEqual(workflow_state["collected_fields"]["business_type"], "ร้านขายขนม")
        self.assertFalse(workflow_state["missing_fields"])

    def test_active_workflow_answer_overrides_store_profile_memory_field(self):
        workflow_state, extracted = update_workflow_state(
            _content_plan_waiting_for("product_or_business_type", collected_fields={"product": "กาแฟ"}),
            "ชูครีม",
            detected_workflow=WORKFLOW_CONTENT_PLAN,
        )

        self.assertEqual(extracted["product"], "ชูครีม")
        self.assertEqual(workflow_state["collected_fields"]["product"], "ชูครีม")
        self.assertFalse(workflow_state["missing_fields"])

    def test_planner_first_does_not_fake_workflow_question_without_active_workflow(self):
        route = {
            "planner_output": {
                "workflow": WORKFLOW_CONTENT_PLAN,
                "next_step": "collect_missing_information",
                "missing_information": ["product_or_business_type"],
            },
            "intent_resolution": {"resolved_workflow": WORKFLOW_CONTENT_PLAN},
        }

        result = select_planner_first_response(route, [])

        self.assertFalse(result["handled"])

    def test_active_workflow_answer_does_not_update_business_context_from_product_alias(self):
        state = _active_content_plan_app_state()

        context = build_business_context(state, "ชูครีม")

        self.assertNotEqual(context.get("business_type"), "cosmetic_store")
        self.assertNotEqual(context.get("current_product"), "cream")

    def test_planner_first_still_collects_non_workflow_missing_information_without_active_workflow(self):
        route = {
            "planner_output": {
                "workflow": None,
                "task_type": "General Business Help",
                "next_step": "collect_missing_information",
                "missing_information": ["store_name"],
            },
            "intent_resolution": {"resolved_workflow": None},
        }

        result = select_planner_first_response(route, [])

        self.assertTrue(result["handled"])
        self.assertIn("reply", result)


if __name__ == "__main__":
    unittest.main()
