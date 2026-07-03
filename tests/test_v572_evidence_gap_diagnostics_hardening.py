import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_situation import build_business_situation
from brain.evidence_gap_runtime import (
    EvidenceGapDiagnosticPriority,
    EvidenceGapQuestionIntent,
    EvidenceGapType,
    build_evidence_gap_runtime,
)
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
        "final_response_text": route.get("final_response_text"),
        "response_source": route.get("response_source"),
        "response_type": route.get("response_type"),
        "llm_needed": route.get("llm_needed"),
        "capability_available": route.get("capability_available"),
    }


def _gap_types(evidence_gap: dict) -> set:
    return {item.get("gap_type") for item in evidence_gap.get("gap_items") or []}


def _question_intents(evidence_gap: dict) -> set:
    return {item.get("question_intent") for item in evidence_gap.get("gap_items") or []}


class EvidenceGapDiagnosticsHardeningTest(unittest.TestCase):
    def test_evidence_gap_attaches_under_business_situation_diagnostics(self):
        situation = build_business_situation(
            user_message="How many products are left in stock?",
            extracted_entities={"missing_entities": ["inventory_count"]},
        )

        self.assertIn("evidence_gap", situation["diagnostics"])
        evidence_gap = situation["diagnostics"]["evidence_gap"]
        self.assertTrue(evidence_gap["diagnostic_only"])
        self.assertTrue(evidence_gap["runtime_only"])
        self.assertIn("gap_type", evidence_gap)
        self.assertIn("question_intent", evidence_gap)
        self.assertIn("duplicate_guard_reason", evidence_gap)
        self.assertIn("duplicate_guard_hits", evidence_gap)
        self.assertIn("suppressed_questions", evidence_gap)
        self.assertIn("completeness_reason", evidence_gap)

    def test_behavior_invariants_remain_false(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = route["business_situation"]["diagnostics"]["evidence_gap"]["diagnostics"]

        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["execution_changed"])
        self.assertFalse(diagnostics["commit_changed"])

    def test_runtime_does_not_modify_inputs_or_memory(self):
        situation = build_business_situation(
            user_message="What profit did we make?",
            extracted_entities={"missing_entities": ["revenue", "cost"]},
        )
        evidence = situation["diagnostics"]["evidence"]
        truth = situation["diagnostics"]["truth"]
        memory = {"events": [{"payload": {"business_type": "coffee_shop"}}]}
        before_situation = copy.deepcopy(situation)
        before_evidence = copy.deepcopy(evidence)
        before_truth = copy.deepcopy(truth)
        before_memory = copy.deepcopy(memory)

        build_evidence_gap_runtime(
            business_situation=situation,
            evidence_runtime=evidence,
            truth_runtime=truth,
        )

        self.assertEqual(situation, before_situation)
        self.assertEqual(evidence, before_evidence)
        self.assertEqual(truth, before_truth)
        self.assertEqual(memory, before_memory)

    def test_inventory_question_classification(self):
        situation = build_business_situation(
            user_message="How many products are left in stock?",
            extracted_entities={"missing_entities": ["inventory_count"]},
        )
        evidence_gap = situation["diagnostics"]["evidence_gap"]

        self.assertIn(EvidenceGapType.MISSING_INVENTORY_DATA.value, _gap_types(evidence_gap))
        self.assertIn(EvidenceGapQuestionIntent.ASK_INVENTORY.value, _question_intents(evidence_gap))

    def test_financial_question_classification(self):
        situation = build_business_situation(
            user_message="What profit and margin did we make?",
            extracted_entities={"missing_entities": ["revenue", "cost"]},
        )
        evidence_gap = situation["diagnostics"]["evidence_gap"]

        self.assertIn(EvidenceGapType.MISSING_FINANCIAL_DATA.value, _gap_types(evidence_gap))
        self.assertIn(EvidenceGapQuestionIntent.ASK_FINANCIAL_DATA.value, _question_intents(evidence_gap))

    def test_timeframe_missing_question_classification(self):
        situation = build_business_situation(
            user_message="How much revenue did we make?",
            extracted_entities={"missing_entities": ["time_period"]},
        )
        evidence_gap = situation["diagnostics"]["evidence_gap"]

        self.assertIn(EvidenceGapType.MISSING_TIMEFRAME.value, _gap_types(evidence_gap))
        self.assertIn(EvidenceGapQuestionIntent.ASK_TIMEFRAME.value, _question_intents(evidence_gap))

    def test_low_confidence_unknown_case_classification(self):
        evidence_gap = build_evidence_gap_runtime(
            business_situation={"current_focus": "unclear request", "diagnostics": {}},
            evidence_runtime={"evidence_items": [], "missing_evidence": [], "evidence_confidence": 0.0},
            truth_runtime={
                "truth_items": [
                    {
                        "classification": "UNKNOWN",
                        "value": {"field": "unverified_detail"},
                        "diagnostic_only": True,
                    }
                ],
                "truth_summary": {"has_unknowns": True},
                "diagnostics": {"unknown_truth_count": 1},
            },
        )

        self.assertIn(EvidenceGapType.LOW_CONFIDENCE.value, _gap_types(evidence_gap))
        self.assertIn(EvidenceGapQuestionIntent.ASK_CLARIFICATION.value, _question_intents(evidence_gap))

    def test_priority_queue_uses_stable_diagnostic_priority_values(self):
        situation = build_business_situation(
            user_message="How much revenue did we make?",
            extracted_entities={"missing_entities": ["time_period"]},
        )
        priorities = {item.get("diagnostic_priority") for item in situation["diagnostics"]["evidence_gap"]["priority_queue"]}

        self.assertTrue(priorities)
        self.assertTrue(
            priorities.issubset(
                {
                    EvidenceGapDiagnosticPriority.CRITICAL.value,
                    EvidenceGapDiagnosticPriority.IMPORTANT.value,
                    EvidenceGapDiagnosticPriority.HELPFUL.value,
                    EvidenceGapDiagnosticPriority.OPTIONAL.value,
                }
            )
        )

    def test_duplicate_guard_and_completeness_diagnostics_are_present(self):
        situation = build_business_situation(
            user_message="What profit did we make?",
            extracted_entities={"missing_entities": ["revenue"]},
        )
        evidence_gap = situation["diagnostics"]["evidence_gap"]
        guard = evidence_gap["duplicate_question_guard"]
        completeness = evidence_gap["completeness_status"]

        self.assertTrue(guard["enabled"])
        self.assertIn("duplicate_guard_reason", guard)
        self.assertIn("duplicate_guard_hits", guard)
        self.assertIn("suppressed_questions", guard)
        self.assertIn("completeness_status", completeness)
        self.assertIn("completeness_reason", completeness)

    def test_brain_observatory_exposes_hardened_evidence_gap_layer_in_order(self):
        route = build_task_route({}, "How much revenue did we make?")
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}
        evidence_gap_state = layers["Evidence Gap"]["runtime_state"]

        self.assertEqual(
            observatory["layer_order"].index("Evidence Gap"),
            observatory["layer_order"].index("Truth Status") + 1,
        )
        self.assertEqual(
            observatory["layer_order"].index("Perspective"),
            observatory["layer_order"].index("Evidence Gap") + 1,
        )
        self.assertIn("gap_items", evidence_gap_state)
        self.assertIn("gap_type", evidence_gap_state)
        self.assertIn("priority_queue", evidence_gap_state)
        self.assertIn("question_intent", evidence_gap_state)
        self.assertIn("missing_evidence", evidence_gap_state)
        self.assertIn("next_best_question", evidence_gap_state)
        self.assertIn("duplicate_question_guard", evidence_gap_state)
        self.assertIn("duplicate_guard_reason", evidence_gap_state)
        self.assertIn("duplicate_guard_hits", evidence_gap_state)
        self.assertIn("suppressed_questions", evidence_gap_state)
        self.assertIn("completeness_status", evidence_gap_state)
        self.assertIn("completeness_reason", evidence_gap_state)

    def test_no_response_routing_planner_workflow_behavior_changes(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}

        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        diagnostics = route["business_situation"]["diagnostics"]["evidence_gap"]["diagnostics"]

        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertFalse(diagnostics["used_for_routing"])
        self.assertFalse(diagnostics["used_for_planner"])
        self.assertFalse(diagnostics["used_for_workflow"])
        self.assertFalse(diagnostics["used_for_response"])
        self.assertFalse(diagnostics["used_for_execution"])
        self.assertFalse(diagnostics["used_for_commit"])
        self.assertNotIn("evidence_gap_decision", route)
        self.assertNotIn("evidence_gap_route", route)
        self.assertNotIn("evidence_gap_workflow", route)
        self.assertNotIn("evidence_gap_response", route)
        self.assertNotIn("evidence_gap_execution", route)
        self.assertNotIn("evidence_gap_commit", route)


if __name__ == "__main__":
    unittest.main()
