import copy
import unittest

from brain.brain_observatory import COGNITIVE_LAYERS, build_brain_observatory
from brain.business_situation import build_business_situation
from brain.evidence_gap_runtime import (
    EVIDENCE_GAP_RUNTIME_SOURCE,
    EVIDENCE_GAP_RUNTIME_VERSION,
    EvidenceGapPriority,
    build_evidence_gap_runtime,
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


class EvidenceGapRuntimeFoundationTest(unittest.TestCase):
    def test_evidence_gap_runtime_can_be_created(self):
        situation = build_business_situation(
            user_message="profit after discount",
            extracted_entities={"missing_entities": ["selling_price", "cost_per_unit"]},
        )

        evidence_gap = build_evidence_gap_runtime(
            business_situation=situation,
            evidence_runtime=situation["diagnostics"]["evidence"],
            truth_runtime=situation["diagnostics"]["truth"],
        )

        self.assertEqual(evidence_gap["version"], EVIDENCE_GAP_RUNTIME_VERSION)
        self.assertEqual(evidence_gap["source"], EVIDENCE_GAP_RUNTIME_SOURCE)
        self.assertTrue(evidence_gap["runtime_only"])
        self.assertTrue(evidence_gap["diagnostic_only"])
        self.assertTrue(evidence_gap["diagnostics"]["evidence_gap_runtime_created"])

    def test_missing_evidence_priority_queue_question_and_duplicate_guard_exist(self):
        situation = build_business_situation(
            user_message="profit after discount",
            extracted_entities={"missing_entities": ["selling_price", "cost_per_unit"]},
        )
        evidence_gap = situation["diagnostics"]["evidence_gap"]
        fields = {item["field"] for item in evidence_gap["missing_evidence"]}

        self.assertIn("selling_price", fields)
        self.assertIn("cost_per_unit", fields)
        self.assertGreaterEqual(len(evidence_gap["gap_items"]), 2)
        self.assertGreaterEqual(len(evidence_gap["priority_queue"]), 2)
        self.assertEqual(evidence_gap["priority_queue"][0]["priority"], EvidenceGapPriority.HIGH.value)
        self.assertTrue(evidence_gap["next_best_question"]["question"])
        self.assertTrue(evidence_gap["duplicate_question_guard"]["enabled"])
        self.assertEqual(evidence_gap["completeness_status"]["status"], "incomplete")

    def test_diagnostics_are_attached_to_business_situation(self):
        situation = build_business_situation(
            user_message="profit after discount",
            extracted_entities={"missing_entities": ["selling_price"]},
        )
        diagnostics = situation["diagnostics"]["evidence_gap"]["diagnostics"]

        self.assertIn("evidence_gap", situation["diagnostics"])
        self.assertTrue(diagnostics["evidence_gap_runtime_created"])
        self.assertEqual(diagnostics["evidence_gap_runtime_version"], EVIDENCE_GAP_RUNTIME_VERSION)
        self.assertTrue(diagnostics["reads_business_situation_diagnostics"])
        self.assertTrue(diagnostics["reads_evidence_runtime_diagnostics"])
        self.assertTrue(diagnostics["reads_truth_runtime_diagnostics"])

    def test_developer_diagnostics_and_observatory_expose_evidence_gap_layer(self):
        route = build_task_route({}, "profit after discount")
        diagnostics = developer_diagnostics(route)
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}

        self.assertTrue(diagnostics["evidence_gap_runtime_created"])
        self.assertEqual(diagnostics["evidence_gap_runtime_version"], EVIDENCE_GAP_RUNTIME_VERSION)
        self.assertIn("Evidence Gap", diagnostics["diagnostic_groups"])
        self.assertIn("Evidence Gap", COGNITIVE_LAYERS)
        self.assertEqual(
            observatory["layer_order"].index("Evidence Gap"),
            observatory["layer_order"].index("Truth Status") + 1,
        )
        self.assertEqual(
            observatory["layer_order"].index("Perspective"),
            observatory["layer_order"].index("Evidence Gap") + 1,
        )
        self.assertEqual(layers["Evidence Gap"]["status"], "observed")
        self.assertTrue(layers["Evidence Gap"]["diagnostics"]["evidence_gap_runtime_created"])

    def test_evidence_gap_does_not_modify_inputs(self):
        situation = build_business_situation(
            user_message="profit after discount",
            extracted_entities={"missing_entities": ["selling_price"]},
        )
        before = copy.deepcopy(situation)

        build_evidence_gap_runtime(
            business_situation=situation,
            evidence_runtime=situation["diagnostics"]["evidence"],
            truth_runtime=situation["diagnostics"]["truth"],
        )

        self.assertEqual(situation, before)

    def test_no_behavior_changes_occur(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        evidence_gap_diagnostics = route["business_situation"]["diagnostics"]["evidence_gap"]["diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(evidence_gap_diagnostics["routing_changed"])
        self.assertFalse(evidence_gap_diagnostics["planner_changed"])
        self.assertFalse(evidence_gap_diagnostics["workflow_changed"])
        self.assertFalse(evidence_gap_diagnostics["responses_changed"])
        self.assertFalse(evidence_gap_diagnostics["execution_changed"])
        self.assertFalse(evidence_gap_diagnostics["commit_changed"])
        self.assertFalse(evidence_gap_diagnostics["business_situation_modified"])
        self.assertFalse(evidence_gap_diagnostics["business_memory_modified"])
        self.assertFalse(evidence_gap_diagnostics["evidence_runtime_modified"])
        self.assertFalse(evidence_gap_diagnostics["truth_runtime_modified"])
        self.assertFalse(evidence_gap_diagnostics["business_meaning_interpreted"])
        self.assertFalse(evidence_gap_diagnostics["recommendation_produced"])
        self.assertFalse(evidence_gap_diagnostics["decision_made"])

    def test_no_behavioral_route_fields_are_added(self):
        route = build_task_route({}, "profit after discount")

        self.assertNotIn("evidence_gap_decision", route)
        self.assertNotIn("evidence_gap_route", route)
        self.assertNotIn("evidence_gap_workflow", route)
        self.assertNotIn("evidence_gap_response", route)
        self.assertNotIn("evidence_gap_execution", route)
        self.assertNotIn("evidence_gap_commit", route)


if __name__ == "__main__":
    unittest.main()
