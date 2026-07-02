import unittest

from brain.business_entity_extractor import extract_business_entities
from brain.business_intent_engine import detect_business_intent
from brain.business_workflow_engine import decide_business_workflow
from brain.conversation_manager import active_workflow_state, continue_workflow, route_quick_action, sync_legacy_workflow_state
from brain.task_router import build_task_route


COST_500 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 500"
QUANTITY_100 = "100 \u0e0a\u0e34\u0e49\u0e19"
PROMOTION_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e34\u0e14\u0e42\u0e1b\u0e23\u0e42\u0e21\u0e0a\u0e31\u0e48\u0e19\u0e23\u0e49\u0e32\u0e19"
CONTENT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1e\u0e2a\u0e15\u0e4c\u0e02\u0e32\u0e22\u0e01\u0e32\u0e41\u0e1f"


def _carry_route_state(state: dict, route: dict) -> dict:
    next_state = dict(state or {})
    next_state["conversation_memory"] = route.get("conversation_memory") or {}
    next_state["business_context"] = route.get("business_context") or {}
    next_state["conversation_intelligence"] = route.get("conversation_intelligence") or {}

    conversation = dict(next_state.get("conversation") or {})
    conversation.update(
        {
            "conversation_memory": route.get("conversation_memory") or {},
            "business_context": route.get("business_context") or {},
            "intent_resolution": route.get("intent_resolution") or {},
            "understanding": route.get("conversation_understanding") or {},
        }
    )

    workflow_state = (route.get("business_workflow") or {}).get("workflow_state")
    if workflow_state:
        conversation_os = conversation.setdefault("conversation_os", {})
        conversation_os.setdefault("workflow_states", {})
        workflow_id = workflow_state.get("workflow_id")
        conversation_os["active_workflow_id"] = workflow_id
        conversation_os["workflow_states"][workflow_id] = workflow_state
        sync_legacy_workflow_state(next_state, workflow_state)

    next_state["conversation"] = conversation
    return next_state


def _active_cost_state() -> dict:
    return _carry_route_state({}, build_task_route({}, COST_500))


class V536WorkflowRuntimeReleaseBoundaryTest(unittest.TestCase):
    def test_cost_to_promotion_releases_cost_workflow_completely(self):
        state = _active_cost_state()

        route = build_task_route(state, PROMOTION_REQUEST)
        workflow = route["business_workflow"]
        skill = route["business_intelligence"].get("matched_skill") or {}
        os_state = state["conversation"]["conversation_os"]

        self.assertEqual(route["intent_resolution"]["resolved_intent"], "marketing_strategy")
        self.assertIsNone(route["planner_output"]["workflow"])
        self.assertEqual(skill.get("skill_id"), "02.002.create_promotion")
        self.assertEqual(workflow["workflow_action"], "release")
        self.assertTrue(workflow["workflow_released"])
        self.assertFalse(workflow["workflow_resume_available"])
        self.assertIsNone(workflow["workflow_state"])
        self.assertIsNone(workflow["next_question"])
        self.assertEqual(workflow["required_entities"], [])
        self.assertEqual(workflow["completed_entities"], [])
        self.assertEqual(workflow["missing_entities"], [])
        self.assertIsNone((workflow["workflow_readiness_decision"] or {}).get("workflow_id"))
        self.assertTrue(workflow["workflow_domain_boundary_applied"])
        self.assertEqual(workflow["previous_workflow_id"], "COST_CALCULATION")
        self.assertIsNone(workflow["next_workflow_id"])
        self.assertIsNone(os_state.get("active_workflow_id"))
        self.assertEqual(os_state.get("workflow_states"), {})
        self.assertEqual(os_state.get("conversation_stack"), [])
        self.assertIsNone(os_state.get("last_paused_workflow_id"))
        self.assertFalse(os_state.get("planner_locked"))

    def test_planner_none_with_active_cost_returns_no_cost_readiness_residue(self):
        state = _active_cost_state()
        business_intent = {"detected_intent": "marketing_strategy", "intent_confidence": 0.9}
        entities = extract_business_entities(PROMOTION_REQUEST, "marketing_strategy")

        decision = decide_business_workflow(
            PROMOTION_REQUEST,
            business_intent=business_intent,
            entity_result=entities,
            application_state=state,
            planner_decision={"workflow": None, "intent_resolution": {"resolved_intent": "marketing_strategy", "resolved_workflow": None}},
            resolved_workflow=None,
        )

        self.assertEqual(decision["workflow_action"], "release")
        self.assertIsNone(decision["workflow_state"])
        self.assertFalse(decision["workflow_resume_available"])
        self.assertTrue(decision["workflow_released"])
        self.assertEqual(decision["missing_entities"], [])
        self.assertNotIn("quantity", decision["missing_entities"])
        self.assertIsNone(decision["next_question"])
        self.assertIsNone((decision["workflow_readiness_decision"] or {}).get("workflow_id"))

    def test_cost_to_content_plan_starts_new_workflow_without_cost_residue(self):
        state = _active_cost_state()

        route = build_task_route(state, CONTENT_REQUEST)
        workflow = route["business_workflow"]

        self.assertEqual(route["planner_output"]["workflow"], "CONTENT_PLAN")
        self.assertEqual(workflow["workflow_action"], "start_new")
        self.assertEqual((workflow["workflow_state"] or {}).get("workflow_id"), "CONTENT_PLAN")
        self.assertTrue(workflow["workflow_domain_boundary_applied"])
        self.assertEqual(workflow["previous_workflow_id"], "COST_CALCULATION")
        self.assertEqual(workflow["next_workflow_id"], "CONTENT_PLAN")
        self.assertNotIn("quantity", workflow.get("missing_entities") or [])
        self.assertNotEqual((workflow["workflow_readiness_decision"] or {}).get("workflow_id"), "COST_CALCULATION")

    def test_cost_quantity_followup_still_continues_and_calculates(self):
        state = _active_cost_state()

        route = build_task_route(state, QUANTITY_100)
        workflow = route["business_workflow"]

        self.assertEqual(route["planner_output"]["workflow"], "COST_CALCULATION")
        self.assertEqual(workflow["workflow_action"], "continue")
        self.assertTrue(workflow["workflow_complete"])
        self.assertEqual(workflow["input_cost"], 500)
        self.assertEqual(workflow["input_quantity"], 100)
        self.assertEqual(workflow["computed_cost_per_unit"], 5)

    def test_explicit_resume_still_uses_paused_workflow(self):
        state = {}
        route_quick_action(state, "cost_calculator")
        continue_workflow(state, "pause")

        message = "\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e48\u0e2d"
        business_intent = detect_business_intent(message)
        entities = extract_business_entities(message, business_intent["detected_intent"])
        decision = decide_business_workflow(
            message,
            business_intent={**business_intent, "detected_intent": "unknown"},
            entity_result=entities,
            application_state=state,
            planner_decision={"workflow": None, "intent_resolution": {"resolved_intent": "continue_previous_workflow", "resolved_workflow": None}},
            resolved_workflow=None,
        )

        self.assertEqual(decision["workflow_action"], "resume")
        self.assertTrue(decision["workflow_resume_available"])
        self.assertEqual((decision["workflow_state"] or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertEqual((active_workflow_state(state) or {}).get("workflow_id"), None)


if __name__ == "__main__":
    unittest.main()
