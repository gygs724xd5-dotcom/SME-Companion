import copy
import unittest

from brain.business_situation import build_business_situation
from brain.evidence_runtime import (
    EVIDENCE_RUNTIME_SOURCE,
    EVIDENCE_RUNTIME_VERSION,
    build_evidence_runtime,
)
from brain.task_router import build_task_route, developer_diagnostics


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
        "final_response_text": route.get("final_response_text"),
        "response_source": route.get("response_source"),
        "response_type": route.get("response_type"),
        "llm_needed": route.get("llm_needed"),
        "capability_available": route.get("capability_available"),
    }


class EvidenceRuntimeFoundationTest(unittest.TestCase):
    def test_evidence_runtime_can_be_created_from_business_situation(self):
        situation = build_business_situation(
            user_message="ลดราคา 10% แล้วกำไรเหลือเท่าไร",
            business_context={
                "business_type": "coffee_shop",
                "current_goal": "promotion",
                "current_problem": "profit impact",
            },
            extracted_entities={"missing_entities": ["selling_price", "cost_per_unit", "quantity"]},
        )

        evidence = build_evidence_runtime(business_situation=situation)

        self.assertTrue(evidence["evidence_available"])
        self.assertEqual(evidence["version"], EVIDENCE_RUNTIME_VERSION)
        self.assertEqual(evidence["evidence_source"], EVIDENCE_RUNTIME_SOURCE)
        self.assertTrue(evidence["runtime_only"])
        self.assertTrue(evidence["diagnostic_only"])

    def test_evidence_runtime_exposes_evidence_items_missing_and_conflicting_evidence(self):
        situation = build_business_situation(
            user_message="Now we are a fish shop. ลดราคา 10% แล้วกำไรเหลือเท่าไร",
            application_state={"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}},
            business_context={"business_type": "coffee_shop", "source": "business_memory"},
            extracted_entities={"missing_entities": ["selling_price", "cost_per_unit", "quantity"]},
        )

        evidence = situation["diagnostics"]["evidence"]
        missing_fields = {item["field"] for item in evidence["missing_evidence"]}

        self.assertGreaterEqual(len(evidence["evidence_items"]), 1)
        self.assertIn("selling_price", missing_fields)
        self.assertIn("cost_per_unit", missing_fields)
        self.assertIn("quantity", missing_fields)
        self.assertEqual(len(evidence["conflicting_evidence"]), 1)
        self.assertEqual(
            evidence["conflicting_evidence"][0]["conflict_type"],
            "business_memory_conversation_conflict",
        )

    def test_evidence_diagnostics_are_diagnostic_only_and_runtime_only(self):
        situation = build_business_situation(user_message="price 150 cost 100")
        evidence = situation["diagnostics"]["evidence"]
        diagnostics = evidence["evidence_diagnostics"]

        self.assertTrue(diagnostics["evidence_runtime_created"])
        self.assertEqual(diagnostics["evidence_runtime_version"], EVIDENCE_RUNTIME_VERSION)
        self.assertTrue(diagnostics["diagnostic_only"])
        self.assertTrue(diagnostics["runtime_only"])
        self.assertFalse(diagnostics["used_for_routing"])
        self.assertFalse(diagnostics["used_for_planner"])
        self.assertFalse(diagnostics["used_for_workflow"])
        self.assertFalse(diagnostics["used_for_response"])
        self.assertFalse(diagnostics["used_for_execution"])
        self.assertFalse(diagnostics["used_for_commit"])

    def test_evidence_does_not_modify_business_situation_classification(self):
        kwargs = {
            "user_message": "Actually we are now a bakery.",
            "application_state": {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}},
            "business_context": {"business_type": "coffee_shop", "source": "business_memory"},
        }

        situation = build_business_situation(**kwargs)
        before = copy.deepcopy(situation)
        build_evidence_runtime(business_situation=situation)

        self.assertEqual(situation, before)
        self.assertEqual(situation["current_business"], "bakery")
        self.assertEqual(situation["situation_source"], "conversation_runtime")

    def test_evidence_does_not_modify_business_memory(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}
        before = copy.deepcopy(state)

        route = build_task_route(state, "Actually we are now a bakery.")

        self.assertEqual(state["business_memory"], before["business_memory"])
        self.assertEqual(route["business_situation"]["current_business"], "bakery")
        self.assertTrue(route["business_situation"]["diagnostics"]["evidence"]["runtime_only"])

    def test_evidence_does_not_modify_routing_planner_workflow_response_execution_or_commit(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        evidence_diagnostics = route["business_situation"]["diagnostics"]["evidence"]["evidence_diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(evidence_diagnostics["used_for_routing"])
        self.assertFalse(evidence_diagnostics["used_for_planner"])
        self.assertFalse(evidence_diagnostics["used_for_workflow"])
        self.assertFalse(evidence_diagnostics["used_for_response"])
        self.assertFalse(evidence_diagnostics["used_for_execution"])
        self.assertFalse(evidence_diagnostics["used_for_commit"])
        self.assertFalse(evidence_diagnostics["business_memory_modified"])

    def test_existing_perception_and_business_situation_diagnostics_remain_intact(self):
        route = build_task_route({}, "profit price 150 cost 100")
        situation = route["business_situation"]
        perception = situation["diagnostics"]["perception"]
        runtime = situation["diagnostics"]["runtime"]

        self.assertTrue(perception["perception_situation_diagnostics_created"])
        self.assertEqual(perception["runtime_mode"], "diagnostics_only")
        self.assertTrue(runtime["runtime_only"])
        self.assertTrue(runtime["diagnostic_only"])
        self.assertFalse(runtime["routing_changed"])
        self.assertIn("evidence", situation["diagnostics"])

    def test_developer_diagnostics_expose_evidence_without_behavioral_route_fields(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = developer_diagnostics(route)

        self.assertTrue(diagnostics["evidence_runtime_created"])
        self.assertEqual(diagnostics["evidence_runtime_version"], EVIDENCE_RUNTIME_VERSION)
        self.assertIn("Evidence", diagnostics["diagnostic_groups"])
        self.assertNotIn("evidence_decision", route)
        self.assertNotIn("evidence_route", route)
        self.assertNotIn("evidence_workflow", route)
        self.assertNotIn("evidence_response", route)
        self.assertNotIn("evidence_execution", route)
        self.assertNotIn("evidence_commit", route)


if __name__ == "__main__":
    unittest.main()
