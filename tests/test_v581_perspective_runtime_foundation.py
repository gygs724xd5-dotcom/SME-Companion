import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_situation import build_business_situation
from brain.perspective_runtime import (
    PERSPECTIVE_FOUNDATION_REASON,
    PERSPECTIVE_RUNTIME_SOURCE,
    PERSPECTIVE_RUNTIME_VERSION,
    PerspectiveFrameStatus,
    build_perspective_runtime,
)
from brain.task_router import build_task_route, developer_diagnostics


PERSPECTIVE_INVARIANTS = (
    "routing_changed",
    "planner_changed",
    "workflow_changed",
    "responses_changed",
    "execution_changed",
    "commit_changed",
    "business_memory_changed",
    "business_situation_changed",
    "evidence_runtime_changed",
    "truth_runtime_changed",
    "evidence_gap_runtime_changed",
    "knowledge_invoked",
    "judgment_invoked",
    "decision_invoked",
    "recommendations_generated",
    "root_causes_diagnosed",
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


class PerspectiveRuntimeFoundationTest(unittest.TestCase):
    def test_perspective_runtime_can_be_built_with_complete_upstream_diagnostics(self):
        situation = build_business_situation(
            user_message="profit price 150 cost 100",
            business_context={"business_type": "coffee_shop", "confidence": 0.8},
        )

        perspective = build_perspective_runtime(
            business_situation=situation,
            evidence_runtime=situation["diagnostics"]["evidence"],
            truth_runtime=situation["diagnostics"]["truth"],
            evidence_gap_runtime=situation["diagnostics"]["evidence_gap"],
        )

        self.assertEqual(perspective["version"], PERSPECTIVE_RUNTIME_VERSION)
        self.assertEqual(perspective["source"], PERSPECTIVE_RUNTIME_SOURCE)
        self.assertTrue(perspective["runtime_only"])
        self.assertTrue(perspective["diagnostic_only"])
        self.assertTrue(perspective["diagnostics"]["perspective_runtime_created"])
        self.assertEqual(
            perspective["source_layers"],
            {
                "business_situation": True,
                "evidence_runtime": True,
                "truth_runtime": True,
                "evidence_gap_runtime": True,
            },
        )

    def test_perspective_runtime_can_be_built_when_upstream_diagnostics_are_missing(self):
        perspective = build_perspective_runtime(business_situation={"diagnostics": {}})

        self.assertEqual(perspective["selected_frame"], "UNKNOWN_SITUATION")
        self.assertEqual(perspective["candidate_frames"], [])
        self.assertEqual(perspective["frame_confidence"], 0.0)
        self.assertEqual(perspective["frame_status"], PerspectiveFrameStatus.FOUNDATION_ONLY.value)
        self.assertEqual(
            perspective["source_layers"],
            {
                "business_situation": True,
                "evidence_runtime": False,
                "truth_runtime": False,
                "evidence_gap_runtime": False,
            },
        )

    def test_perspective_attaches_under_business_situation_diagnostics(self):
        situation = build_business_situation(user_message="How much revenue did we make?")

        self.assertIn("perspective", situation["diagnostics"])
        perspective = situation["diagnostics"]["perspective"]
        self.assertEqual(perspective["selected_frame"], "UNKNOWN_SITUATION")
        self.assertEqual(perspective["candidate_frames"], [])
        self.assertEqual(perspective["frame_confidence"], 0.0)
        self.assertEqual(perspective["frame_selection_reason"], PERSPECTIVE_FOUNDATION_REASON)
        self.assertEqual(perspective["frame_status"], PerspectiveFrameStatus.FOUNDATION_ONLY.value)

    def test_perspective_does_not_modify_upstream_inputs(self):
        situation = build_business_situation(
            user_message="profit after discount",
            extracted_entities={"missing_entities": ["selling_price", "cost_per_unit"]},
        )
        evidence = situation["diagnostics"]["evidence"]
        truth = situation["diagnostics"]["truth"]
        evidence_gap = situation["diagnostics"]["evidence_gap"]
        before_situation = copy.deepcopy(situation)
        before_evidence = copy.deepcopy(evidence)
        before_truth = copy.deepcopy(truth)
        before_evidence_gap = copy.deepcopy(evidence_gap)

        build_perspective_runtime(
            business_situation=situation,
            evidence_runtime=evidence,
            truth_runtime=truth,
            evidence_gap_runtime=evidence_gap,
        )

        self.assertEqual(situation, before_situation)
        self.assertEqual(evidence, before_evidence)
        self.assertEqual(truth, before_truth)
        self.assertEqual(evidence_gap, before_evidence_gap)

    def test_all_constitutional_invariants_remain_false(self):
        perspective = build_business_situation(user_message="profit price 150 cost 100")["diagnostics"]["perspective"]

        for key in PERSPECTIVE_INVARIANTS:
            self.assertIn(key, perspective["constitutional_invariants"])
            self.assertFalse(perspective["constitutional_invariants"][key])
            self.assertFalse(perspective["diagnostics"][key])

    def test_brain_observatory_exposes_perspective_after_evidence_gap_and_before_knowledge(self):
        route = build_task_route({}, "profit price 150 cost 100")
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}
        order = observatory["layer_order"]
        perspective_state = layers["Perspective"]["runtime_state"]

        self.assertEqual(order.index("Perspective"), order.index("Evidence Gap") + 1)
        self.assertEqual(order.index("Knowledge"), order.index("Perspective") + 1)
        self.assertEqual(layers["Perspective"]["status"], "observed")
        self.assertEqual(layers["Knowledge"]["status"], "placeholder")
        self.assertEqual(perspective_state["selected_frame"], "UNKNOWN_SITUATION")
        self.assertEqual(perspective_state["candidate_frames"], [])
        self.assertEqual(perspective_state["frame_confidence"], 0.0)
        self.assertEqual(perspective_state["frame_selection_reason"], PERSPECTIVE_FOUNDATION_REASON)
        self.assertEqual(perspective_state["frame_status"], PerspectiveFrameStatus.FOUNDATION_ONLY.value)
        self.assertIn("source_layers", perspective_state)
        self.assertIn("constitutional_invariants", perspective_state)

    def test_developer_diagnostics_expose_perspective_without_knowledge_invocation(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = developer_diagnostics(route)

        self.assertIn("Perspective", diagnostics["diagnostic_groups"])
        self.assertTrue(diagnostics["perspective_runtime_created"])
        self.assertEqual(diagnostics["perspective_runtime_version"], PERSPECTIVE_RUNTIME_VERSION)
        self.assertEqual(diagnostics["perspective_selected_frame"], "UNKNOWN_SITUATION")
        self.assertEqual(diagnostics["perspective_candidate_frame_count"], 0)
        self.assertEqual(diagnostics["perspective_frame_confidence"], 0.0)
        self.assertEqual(diagnostics["perspective_frame_status"], PerspectiveFrameStatus.FOUNDATION_ONLY.value)
        self.assertFalse(diagnostics["perspective_constitutional_invariants"]["knowledge_invoked"])

    def test_existing_v57x_compatibility_is_preserved(self):
        route = build_task_route({}, "profit price 150 cost 100")
        situation = route["business_situation"]

        self.assertIn("evidence", situation["diagnostics"])
        self.assertIn("truth", situation["diagnostics"])
        self.assertIn("evidence_gap", situation["diagnostics"])
        self.assertTrue(situation["diagnostics"]["evidence"]["evidence_diagnostics"]["evidence_runtime_created"])
        self.assertTrue(situation["diagnostics"]["truth"]["diagnostics"]["truth_runtime_created"])
        self.assertTrue(situation["diagnostics"]["evidence_gap"]["diagnostics"]["evidence_gap_runtime_created"])

    def test_no_routing_planner_workflow_response_behavior_changes_occur(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        perspective_diagnostics = route["business_situation"]["diagnostics"]["perspective"]["diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(perspective_diagnostics["routing_changed"])
        self.assertFalse(perspective_diagnostics["planner_changed"])
        self.assertFalse(perspective_diagnostics["workflow_changed"])
        self.assertFalse(perspective_diagnostics["responses_changed"])
        self.assertFalse(perspective_diagnostics["execution_changed"])
        self.assertFalse(perspective_diagnostics["commit_changed"])
        self.assertNotIn("perspective_decision", route)
        self.assertNotIn("perspective_route", route)
        self.assertNotIn("perspective_workflow", route)
        self.assertNotIn("perspective_response", route)
        self.assertNotIn("perspective_execution", route)
        self.assertNotIn("perspective_commit", route)


if __name__ == "__main__":
    unittest.main()
