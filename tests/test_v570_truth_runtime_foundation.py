import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_situation import build_business_situation
from brain.task_router import build_task_route, developer_diagnostics
from brain.truth_runtime import (
    TRUTH_RUNTIME_SOURCE,
    TRUTH_RUNTIME_VERSION,
    TruthClassification,
    build_truth_runtime,
)


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


class TruthRuntimeFoundationTest(unittest.TestCase):
    def test_truth_runtime_can_be_created_from_evidence_runtime(self):
        situation = build_business_situation(
            user_message="profit price 150 cost 100",
            business_context={"business_type": "coffee_shop", "confidence": 0.8},
        )

        truth = build_truth_runtime(evidence_runtime=situation["diagnostics"]["evidence"])

        self.assertEqual(truth["version"], TRUTH_RUNTIME_VERSION)
        self.assertEqual(truth["source"], TRUTH_RUNTIME_SOURCE)
        self.assertTrue(truth["runtime_only"])
        self.assertTrue(truth["diagnostic_only"])
        self.assertGreaterEqual(len(truth["truth_items"]), 1)
        self.assertTrue(truth["diagnostics"]["truth_runtime_created"])

    def test_truth_runtime_stores_classifications_without_business_judgment(self):
        evidence = {
            "evidence_items": [
                {
                    "evidence_id": "evidence_user_message",
                    "evidence_type": "current_message",
                    "source": "user",
                    "value": "price 150",
                    "confidence": 1.0,
                },
                {
                    "evidence_id": "evidence_memory",
                    "evidence_type": "conversation_memory",
                    "source": "memory",
                    "value": {"business_type": "coffee_shop"},
                    "confidence": 0.7,
                },
            ],
            "missing_evidence": [{"field": "cost_per_unit", "source": "planning_uncertainty"}],
            "conflicting_evidence": [{"conflict_type": "business_memory_conversation_conflict", "source": "business_situation_runtime"}],
        }

        truth = build_truth_runtime(evidence_runtime=evidence)
        classifications = {item["classification"] for item in truth["truth_items"]}

        self.assertIn(TruthClassification.OBSERVED.value, classifications)
        self.assertIn(TruthClassification.HISTORICAL.value, classifications)
        self.assertIn(TruthClassification.INSUFFICIENT.value, classifications)
        self.assertIn(TruthClassification.CONFLICTING.value, classifications)
        self.assertFalse(truth["diagnostics"]["business_reasoning_performed"])
        self.assertFalse(truth["diagnostics"]["decision_made"])

    def test_truth_runtime_is_attached_to_business_situation_diagnostics(self):
        situation = build_business_situation(user_message="profit price 150 cost 100")
        truth = situation["diagnostics"]["truth"]

        self.assertTrue(truth["diagnostics"]["truth_runtime_created"])
        self.assertEqual(truth["diagnostics"]["truth_runtime_version"], TRUTH_RUNTIME_VERSION)
        self.assertTrue(truth["diagnostics"]["reads_evidence_runtime_only"])
        self.assertIn("evidence", situation["diagnostics"])
        self.assertIn("truth", situation["diagnostics"])

    def test_developer_diagnostics_and_observatory_expose_truth_runtime(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = developer_diagnostics(route)
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}

        self.assertTrue(diagnostics["truth_runtime_created"])
        self.assertEqual(diagnostics["truth_runtime_version"], TRUTH_RUNTIME_VERSION)
        self.assertIn("Truth Runtime", diagnostics["diagnostic_groups"])
        self.assertEqual(layers["Truth Status"]["status"], "observed")
        self.assertTrue(layers["Truth Status"]["diagnostics"]["truth_runtime_created"])
        self.assertGreaterEqual(len(layers["Truth Status"]["runtime_state"]["truth_items"]), 1)

    def test_truth_runtime_does_not_modify_evidence_or_business_situation(self):
        situation = build_business_situation(user_message="Actually we are now a bakery.")
        evidence = copy.deepcopy(situation["diagnostics"]["evidence"])
        before = copy.deepcopy(situation)

        build_truth_runtime(evidence_runtime=situation["diagnostics"]["evidence"])

        self.assertEqual(situation, before)
        self.assertEqual(situation["diagnostics"]["evidence"], evidence)

    def test_truth_runtime_does_not_modify_behavioral_surfaces(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        truth_diagnostics = route["business_situation"]["diagnostics"]["truth"]["diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(truth_diagnostics["used_for_routing"])
        self.assertFalse(truth_diagnostics["used_for_planner"])
        self.assertFalse(truth_diagnostics["used_for_workflow"])
        self.assertFalse(truth_diagnostics["used_for_response"])
        self.assertFalse(truth_diagnostics["used_for_execution"])
        self.assertFalse(truth_diagnostics["used_for_commit"])
        self.assertFalse(truth_diagnostics["business_situation_modified"])
        self.assertFalse(truth_diagnostics["evidence_modified"])
        self.assertFalse(truth_diagnostics["business_memory_modified"])
        self.assertFalse(truth_diagnostics["authority_modified"])

    def test_backward_compatibility_flags_remain_false(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = route["business_situation"]["diagnostics"]
        observatory_invariants = build_brain_observatory(route)["invariants"]

        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["execution_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])
        self.assertFalse(observatory_invariants["routing_changed"])
        self.assertFalse(observatory_invariants["planner_changed"])
        self.assertFalse(observatory_invariants["workflow_changed"])
        self.assertFalse(observatory_invariants["responses_changed"])
        self.assertFalse(observatory_invariants["execution_changed"])
        self.assertFalse(observatory_invariants["commit_changed"])


if __name__ == "__main__":
    unittest.main()
