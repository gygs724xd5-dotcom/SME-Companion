import copy
import unittest

from brain.cognitive_authority_audit import PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT, WORKFLOW_AMBIGUITY_CONFLICT
from brain.task_router import build_task_route, developer_diagnostics
from brain.workflow_admission_gate import build_workflow_admission_decision


PROFIT_ASSESSMENT = "\u0e23\u0e49\u0e32\u0e19\u0e02\u0e2d\u0e07\u0e09\u0e31\u0e19\u0e01\u0e33\u0e44\u0e23\u0e14\u0e35\u0e44\u0e2b\u0e21"
PROFIT_DROP = "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e41\u0e15\u0e48\u0e01\u0e33\u0e44\u0e23\u0e25\u0e14"
EXPLICIT_PROFIT = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e01\u0e33\u0e44\u0e23\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
NUMERIC_PROFIT = "\u0e02\u0e32\u0e22 80 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
COST_AMBIGUOUS = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
COST_EXPLICIT = "\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 10 \u0e0a\u0e34\u0e49\u0e19 \u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 25 \u0e1a\u0e32\u0e17"
PRICE_QUESTION = "\u0e02\u0e32\u0e22\u0e23\u0e32\u0e04\u0e32\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17\u0e04\u0e23\u0e31\u0e1a"


def _conflict_types(audit: dict) -> set[str]:
    return {
        item.get("authority_conflict_type")
        for item in audit.get("authority_conflicts") or []
        if isinstance(item, dict)
    }


def _gate(message: str, *, candidate: str = "PROFIT_CALCULATION", entities: dict | None = None) -> dict:
    return build_workflow_admission_decision(
        raw_user_message=message,
        conversation_understanding={"detected_intent": "unknown", "confidence": "LOW", "confidence_score": 0.25},
        intent_resolution={
            "resolved_intent": "profit_calculation",
            "resolved_workflow": candidate,
            "confidence": "HIGH",
            "confidence_score": 0.86,
        },
        planner_output={"workflow": candidate},
        workflow_candidate=candidate,
        extracted_entities=entities or {},
    )


class WorkflowAdmissionGateV583Test(unittest.TestCase):
    def test_gate_admits_explicit_executable_profit_calculation(self):
        result = _gate(NUMERIC_PROFIT, entities={"prices": [{"amount": 80}], "costs": [{"amount": 35}]})

        self.assertEqual(result["decision"], "ADMIT")
        self.assertEqual(result["workflow_candidate"], "PROFIT_CALCULATION")
        self.assertTrue(result["workflow_executable"])

    def test_gate_admits_explicit_calculation_request_even_when_required_fields_are_missing(self):
        result = _gate(EXPLICIT_PROFIT)

        self.assertEqual(result["decision"], "ADMIT")
        self.assertTrue(result["executable_request_detected"])
        self.assertFalse(result["workflow_executable"])
        self.assertEqual(result["missing_entities"], ["price", "cost"])

    def test_gate_blocks_business_level_profit_assessment(self):
        result = _gate(PROFIT_ASSESSMENT)

        self.assertEqual(result["decision"], "REJECT_TO_CONVERSATION")
        self.assertEqual(result["reason"], "AMBIGUOUS_BUSINESS_ASSESSMENT")
        self.assertTrue(result["business_level_scope_detected"])

    def test_gate_blocks_analytical_profit_question(self):
        result = _gate(PROFIT_DROP)

        self.assertEqual(result["decision"], "REJECT_TO_CONVERSATION")
        self.assertEqual(result["reason"], "ANALYTICAL_QUESTION_NOT_EXECUTABLE")
        self.assertTrue(result["analytical_question_detected"])

    def test_gate_detects_keyword_only_workflow_match(self):
        result = _gate(COST_AMBIGUOUS, candidate="COST_CALCULATION")

        self.assertNotEqual(result["decision"], "ADMIT")
        self.assertTrue(result["keyword_only_match_detected"])

    def test_gate_respects_low_confidence_conversation_understanding(self):
        result = _gate(COST_AMBIGUOUS, candidate="COST_CALCULATION")

        self.assertEqual(result["decision"], "DEFER_FOR_CLARIFICATION")
        self.assertEqual(result["reason"], "LOW_UNDERSTANDING_CONFIDENCE")

    def test_gate_distinguishes_workflow_admitted_from_workflow_executable(self):
        result = _gate(EXPLICIT_PROFIT)

        self.assertTrue(result["admitted"])
        self.assertFalse(result["workflow_executable"])

    def test_gate_returns_safe_result_when_no_workflow_candidate_exists(self):
        result = build_workflow_admission_decision(raw_user_message="hello", workflow_candidate=None)

        self.assertFalse(result["admitted"])
        self.assertEqual(result["reason"], "NO_WORKFLOW_CANDIDATE")

    def test_gate_does_not_mutate_inputs(self):
        understanding = {"detected_intent": "unknown", "confidence": "LOW"}
        resolver = {"resolved_workflow": "PROFIT_CALCULATION"}
        planner = {"workflow": "PROFIT_CALCULATION"}
        entities = {"prices": [{"amount": 80}]}
        before = copy.deepcopy((understanding, resolver, planner, entities))

        build_workflow_admission_decision(
            raw_user_message=PROFIT_ASSESSMENT,
            conversation_understanding=understanding,
            intent_resolution=resolver,
            planner_output=planner,
            extracted_entities=entities,
        )

        self.assertEqual((understanding, resolver, planner, entities), before)

    def test_blocked_workflow_does_not_initialize_workflow_state(self):
        route = build_task_route({}, PROFIT_ASSESSMENT)
        workflow = route["business_workflow"]

        self.assertIsNone(workflow.get("workflow_state"))
        self.assertEqual(workflow.get("workflow_action"), "interrupt")
        self.assertEqual(route["workflow_admission_gate"]["decision"], "REJECT_TO_CONVERSATION")

    def test_blocked_workflow_does_not_ask_workflow_next_question(self):
        route = build_task_route({}, PROFIT_ASSESSMENT)

        self.assertNotEqual((route["business_workflow"] or {}).get("next_question"), PRICE_QUESTION)
        self.assertFalse(route["workflow_response_allowed"])

    def test_admitted_workflow_retains_existing_behavior(self):
        route = build_task_route({}, EXPLICIT_PROFIT)
        workflow = route["business_workflow"]

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), "PROFIT_CALCULATION")
        self.assertEqual(workflow.get("next_question"), PRICE_QUESTION)

    def test_numeric_profit_workflow_executes_normally(self):
        route = build_task_route({}, NUMERIC_PROFIT)
        workflow = route["business_workflow"]

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue((workflow.get("readiness_decision") or {}).get("workflow_executable"))

    def test_cognitive_authority_audit_records_gate_decision(self):
        route = build_task_route({}, PROFIT_ASSESSMENT)
        audit = route["cognitive_authority_audit"]

        self.assertTrue(audit["workflow_admission_gate_consulted"])
        self.assertEqual(audit["workflow_admission_gate_decision"], "REJECT_TO_CONVERSATION")
        self.assertEqual(audit["workflow_admission_gate_reason"], "AMBIGUOUS_BUSINESS_ASSESSMENT")

    def test_winning_authority_becomes_gate_for_rejected_candidates(self):
        audit = build_task_route({}, PROFIT_ASSESSMENT)["cognitive_authority_audit"]

        self.assertEqual(audit["winning_authority"], "workflow_admission_gate")
        self.assertEqual(audit["winning_stage"], "WORKFLOW_ADMISSION")

    def test_workflow_admitted_despite_ambiguity_absent_after_correct_rejection(self):
        audit = build_task_route({}, PROFIT_ASSESSMENT)["cognitive_authority_audit"]

        self.assertNotIn(WORKFLOW_AMBIGUITY_CONFLICT, _conflict_types(audit))

    def test_perspective_remains_non_authoritative(self):
        audit = build_task_route({}, PROFIT_ASSESSMENT)["cognitive_authority_audit"]

        self.assertIn(PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT, _conflict_types(audit))
        self.assertFalse(audit["cognitive_runtime_authoritative"])

    def test_analytical_profit_route_does_not_start_profit_calculation(self):
        route = build_task_route({}, PROFIT_DROP)

        self.assertNotEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertIsNone((route["business_workflow"] or {}).get("workflow_state"))
        self.assertIsNone((route["business_workflow"] or {}).get("next_question"))

    def test_cost_executable_admits_supported_workflow(self):
        route = build_task_route({}, COST_EXPLICIT)

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((route["business_workflow"].get("workflow_state") or {}).get("workflow_id"), "COST_CALCULATION")

    def test_developer_and_observatory_diagnostics_expose_gate(self):
        route = build_task_route({}, PROFIT_ASSESSMENT)
        diagnostics = developer_diagnostics(route)

        self.assertEqual(diagnostics["workflow_admission_decision"], "REJECT_TO_CONVERSATION")
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Cognitive Authority"]["workflow_admission_gate_decision"],
            "REJECT_TO_CONVERSATION",
        )
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Brain Observatory"]["cognitive_authority"]["workflow_admission_gate_decision"],
            "REJECT_TO_CONVERSATION",
        )


if __name__ == "__main__":
    unittest.main()
