import copy
import unittest

from brain.business_situation import build_business_situation
from brain.task_router import build_task_route


def _stable_behavior(route: dict) -> dict:
    planner = route.get("planner_output") or {}
    workflow = route.get("business_workflow") or {}
    return {
        "task_type": planner.get("task_type"),
        "workflow": planner.get("workflow"),
        "next_step": planner.get("next_step"),
        "workflow_action": workflow.get("workflow_action"),
        "workflow_id": (workflow.get("workflow_state") or {}).get("workflow_id"),
        "workflow_response_allowed": route.get("workflow_response_allowed"),
        "final_response_gate": route.get("final_response_gate"),
        "response_source": route.get("response_source"),
        "response_type": route.get("response_type"),
    }


class BusinessSituationRuntimeTest(unittest.TestCase):
    def test_runtime_business_is_separate_from_business_memory(self):
        state = {
            "business_memory": {
                "events": [
                    {"payload": {"business_type": "coffee_shop"}},
                ]
            }
        }

        situation = build_business_situation(
            user_message="Actually we are now a bakery.",
            application_state=state,
            business_context={"business_type": "coffee_shop", "source": "business_memory", "confidence": 0.45},
        )

        self.assertEqual(situation["current_business"], "bakery")
        self.assertEqual(state["business_memory"]["events"][0]["payload"]["business_type"], "coffee_shop")
        self.assertEqual(situation["business_context"]["business_type"], "coffee_shop")

    def test_runtime_business_may_differ_from_durable_memory(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        situation = build_business_situation(
            user_message="Now we are a fish shop.",
            application_state=state,
            business_context={"business_type": "coffee_shop", "source": "business_memory", "confidence": 0.45},
        )

        diagnostics = situation["situation_diagnostics"]
        self.assertEqual(situation["current_business"], "fish_shop")
        self.assertTrue(diagnostics["memory_conflict"])
        self.assertEqual(diagnostics["memory_value"], "coffee_shop")
        self.assertEqual(diagnostics["conversation_value"], "fish_shop")
        self.assertEqual(diagnostics["current_value"], "fish_shop")
        self.assertEqual(diagnostics["business_source"], "conversation_runtime")

    def test_business_memory_remains_unchanged_after_route(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}
        before = copy.deepcopy(state)

        route = build_task_route(state, "Actually we are now a bakery.")

        self.assertEqual(state["business_memory"], before["business_memory"])
        self.assertEqual(route["business_situation"]["current_business"], "bakery")
        self.assertEqual(before["business_memory"]["events"][0]["payload"]["business_type"], "coffee_shop")

    def test_runtime_override_exists_only_in_conversation_runtime(self):
        memory_state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        first = build_task_route(memory_state, "Actually we are now a bakery.")
        second = build_task_route(memory_state, "What should I do today?")

        self.assertEqual(first["business_situation"]["current_business"], "bakery")
        self.assertEqual(second["business_situation"]["current_business"], "coffee_shop")
        self.assertFalse(second["business_situation"]["situation_diagnostics"]["memory_conflict"])

    def test_diagnostics_explain_runtime_selection(self):
        situation = build_business_situation(
            user_message="Actually we are now a bakery.",
            application_state={"business_memory": {"business_type": "coffee_shop"}},
            business_context={"business_type": "coffee_shop", "source": "business_memory"},
        )

        diagnostics = situation["diagnostics"]["runtime"]
        self.assertTrue(diagnostics["runtime_only"])
        self.assertTrue(diagnostics["diagnostic_only"])
        self.assertEqual(diagnostics["override_reason"], "conversation_runtime_overrides_durable_memory")
        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["execution_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])

    def test_behavioral_surfaces_remain_unchanged_for_equivalent_routes(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        diagnostics = route["business_situation"]["diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["memory_changed"])
        self.assertFalse(diagnostics["execution_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])

    def test_runtime_fields_do_not_create_behavioral_route_fields(self):
        route = build_task_route({}, "Actually we are now a bakery.")

        self.assertNotIn("current_business", route)
        self.assertNotIn("situation_decision", route)
        self.assertNotIn("situation_route", route)
        self.assertNotIn("situation_workflow", route)
        self.assertNotIn("situation_response", route)
        self.assertNotIn("situation_commit", route)


if __name__ == "__main__":
    unittest.main()
