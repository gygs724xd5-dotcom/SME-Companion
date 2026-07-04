import copy
import unittest

from brain.cognitive_authority_audit import (
    COGNITIVE_AUTHORITY_AUDIT_VERSION,
    LOW_CONFIDENCE_CONFLICT,
    PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT,
    WORKFLOW_AMBIGUITY_CONFLICT,
    WORKFLOW_UNCERTAINTY_CONFLICT,
    AuthorityStage,
    attach_cognitive_authority_audit,
    build_cognitive_authority_audit,
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


def _conflict_types(audit: dict) -> set[str]:
    return {
        item.get("authority_conflict_type")
        for item in audit.get("authority_conflicts") or []
        if isinstance(item, dict)
    }


class CognitiveAuthorityTransitionAuditTest(unittest.TestCase):
    def test_audit_can_be_built_from_complete_response_path(self):
        route = build_task_route({}, "profit price 80 cost 35")
        route.update(
            {
                "response_source": "workflow_response",
                "response_mode": "workflow",
                "commit_source": "response_commit_boundary",
            }
        )

        audit = build_cognitive_authority_audit(route)

        self.assertEqual(audit["audit_version"], COGNITIVE_AUTHORITY_AUDIT_VERSION)
        self.assertEqual(audit["response_source"], "workflow_response")
        self.assertEqual(audit["commit_source"], "response_commit_boundary")
        self.assertEqual(audit["winning_stage"], AuthorityStage.COMMIT.value)

    def test_audit_tolerates_missing_optional_diagnostics(self):
        audit = build_cognitive_authority_audit(
            {
                "conversation_understanding": {"detected_intent": "unknown", "confidence": "LOW"},
                "intent_resolution": {"resolved_intent": "general_business_help"},
                "business_situation": {"diagnostics": {}},
            }
        )

        self.assertEqual(audit["selected_intent"], "general_business_help")
        self.assertFalse(audit["workflow_admitted"])
        self.assertIsInstance(audit["authority_chain"], list)

    def test_audit_attaches_under_business_situation_diagnostics(self):
        route = build_task_route({}, "profit price 80 cost 35")

        self.assertIn("cognitive_authority_audit", route["business_situation"]["diagnostics"])
        self.assertEqual(
            route["business_situation"]["diagnostics"]["cognitive_authority_audit"]["audit_version"],
            COGNITIVE_AUTHORITY_AUDIT_VERSION,
        )

    def test_authority_chain_preserves_stage_order(self):
        audit = build_cognitive_authority_audit(build_task_route({}, "profit price 80 cost 35"))
        stages = [item["stage"] for item in audit["authority_chain"]]

        self.assertEqual(stages, [stage.value for stage in AuthorityStage])

    def test_winning_authority_is_identified(self):
        audit = build_cognitive_authority_audit(
            build_task_route({}, "profit price 80 cost 35"),
            response_source="workflow_response",
        )

        self.assertEqual(audit["winning_authority"], "workflow_response")
        self.assertEqual(audit["winning_stage"], AuthorityStage.RESPONSE_GENERATION.value)

    def test_low_understanding_high_resolver_conflict_is_detected(self):
        route = {
            "conversation_understanding": {
                "raw_text": "ร้านของฉันกำไรดีไหม",
                "detected_intent": "unknown",
                "confidence": "LOW",
                "confidence_score": 0.25,
                "clarification_required": True,
            },
            "intent_resolution": {
                "resolved_intent": "profit_calculation",
                "resolved_workflow": "PROFIT_CALCULATION",
                "confidence": "HIGH",
                "confidence_score": 0.86,
                "source": "conversation_intelligence",
            },
            "planner_output": {"task_type": "Profit Calculation", "workflow": "PROFIT_CALCULATION"},
            "business_workflow": {
                "workflow_action": "start_new",
                "workflow_state": {"workflow_id": "PROFIT_CALCULATION"},
                "workflow_reason": "planner selected workflow execution",
                "workflow_confidence": 0.86,
                "required_entities": ["price", "cost"],
                "missing_entities": ["price", "cost"],
                "readiness_decision": {"workflow_executable": False, "missing_fields": ["price", "cost"]},
            },
            "business_situation": {"diagnostics": {}},
        }

        audit = build_cognitive_authority_audit(route)

        self.assertIn(LOW_CONFIDENCE_CONFLICT, _conflict_types(audit))

    def test_workflow_admitted_despite_ambiguity_is_detected(self):
        route = {
            "conversation_understanding": {
                "detected_intent": "unknown",
                "confidence": "LOW",
                "clarification_required": True,
            },
            "intent_resolution": {"resolved_intent": "profit_calculation", "resolved_workflow": "PROFIT_CALCULATION"},
            "planner_output": {"workflow": "PROFIT_CALCULATION"},
            "business_workflow": {
                "workflow_action": "start_new",
                "workflow_state": {"workflow_id": "PROFIT_CALCULATION"},
                "required_entities": ["price", "cost"],
                "missing_entities": ["price", "cost"],
            },
            "business_situation": {"diagnostics": {}},
        }

        audit = build_cognitive_authority_audit(route)

        self.assertTrue(audit["workflow_admitted"])
        self.assertTrue(audit["workflow_started_before_intent_disambiguation"])
        self.assertIn(WORKFLOW_AMBIGUITY_CONFLICT, _conflict_types(audit))

    def test_cognitive_runtime_consulted_but_non_authoritative_is_recorded(self):
        route = build_task_route({}, "profit price 80 cost 35")
        audit = route["business_situation"]["diagnostics"]["cognitive_authority_audit"]

        self.assertTrue(audit["cognitive_runtime_consulted"])
        self.assertFalse(audit["cognitive_runtime_authoritative"])
        self.assertIn("diagnostics_only", audit["cognitive_runtime_override_reason"])

    def test_perspective_diagnostics_only_status_is_recorded_correctly(self):
        route = build_task_route({}, "profit price 80 cost 35")
        audit = route["business_situation"]["diagnostics"]["cognitive_authority_audit"]

        self.assertIn(PERSPECTIVE_NOT_AUTHORITATIVE_CONFLICT, _conflict_types(audit))

    def test_workflow_executable_false_is_distinct_from_workflow_admitted_true(self):
        route = {
            "conversation_understanding": {"detected_intent": "unknown", "confidence": "LOW"},
            "intent_resolution": {"resolved_intent": "profit_calculation", "resolved_workflow": "PROFIT_CALCULATION"},
            "planner_output": {"workflow": "PROFIT_CALCULATION"},
            "business_workflow": {
                "workflow_action": "start_new",
                "workflow_state": {"workflow_id": "PROFIT_CALCULATION"},
                "required_entities": ["price", "cost"],
                "missing_entities": ["price", "cost"],
                "readiness_decision": {"workflow_executable": False},
            },
            "business_situation": {"diagnostics": {}},
        }

        audit = build_cognitive_authority_audit(route)

        self.assertTrue(audit["workflow_admitted"])
        self.assertFalse(audit["workflow_executable"])

    def test_response_mode_and_response_source_are_recorded(self):
        audit = build_cognitive_authority_audit(
            build_task_route({}, "profit price 80 cost 35"),
            response_source="workflow_response",
            selected_response_mode="WORKFLOW",
        )

        self.assertEqual(audit["selected_response_mode"], "WORKFLOW")
        self.assertEqual(audit["response_source"], "workflow_response")

    def test_fallback_source_is_recorded_when_present(self):
        audit = build_cognitive_authority_audit(
            build_task_route({}, "hello"),
            response_source="empty_response_fallback",
            fallback_selected=True,
            fallback_source="empty_response_fallback",
        )

        self.assertTrue(audit["fallback_selected"])
        self.assertEqual(audit["fallback_source"], "empty_response_fallback")

    def test_commit_source_is_recorded(self):
        audit = build_cognitive_authority_audit(
            build_task_route({}, "hello"),
            commit_source="response_commit_boundary",
        )

        self.assertEqual(audit["commit_source"], "response_commit_boundary")
        self.assertEqual(audit["winning_stage"], AuthorityStage.COMMIT.value)

    def test_no_runtime_decision_is_changed(self):
        baseline = build_task_route({}, "profit price 80 cost 35")
        route = build_task_route({}, "profit price 80 cost 35")
        before = _stable_behavior(route)

        attach_cognitive_authority_audit(route)

        self.assertEqual(_stable_behavior(baseline), before)
        self.assertEqual(_stable_behavior(route), before)

    def test_no_workflow_is_blocked(self):
        route = build_task_route({}, "profit price 80 cost 35")
        before = copy.deepcopy(route.get("business_workflow"))

        attach_cognitive_authority_audit(route)

        self.assertEqual(route.get("business_workflow"), before)

    def test_no_response_text_is_changed(self):
        route = {"final_response_text": "same reply", "business_situation": {"diagnostics": {}}}

        attach_cognitive_authority_audit(route)

        self.assertEqual(route["final_response_text"], "same reply")

    def test_existing_runtime_diagnostics_remain_compatible(self):
        route = build_task_route({}, "profit price 80 cost 35")
        diagnostics = route["business_situation"]["diagnostics"]
        developer = developer_diagnostics(route)

        self.assertIn("perspective", diagnostics)
        self.assertIn("evidence_gap", diagnostics)
        self.assertIn("truth", diagnostics)
        self.assertIn("evidence", diagnostics)
        self.assertIn("Cognitive Authority", developer["diagnostic_groups"])
        self.assertIn("Brain Observatory", developer["diagnostic_groups"])

    def test_regression_profit_assessment_authority_path_fixture(self):
        route = {
            "conversation_understanding": {
                "raw_text": "ร้านของฉันกำไรดีไหม",
                "detected_intent": "unknown",
                "confidence": "LOW",
                "confidence_score": 0.25,
                "clarification_required": True,
            },
            "intent_resolution": {
                "resolved_intent": "profit_calculation",
                "resolved_workflow": "PROFIT_CALCULATION",
                "confidence": "HIGH",
                "confidence_score": 0.86,
                "source": "conversation_intelligence",
            },
            "planner_output": {"task_type": "Profit Calculation", "workflow": "PROFIT_CALCULATION"},
            "business_workflow": {
                "workflow_action": "start_new",
                "workflow_state": {"workflow_id": "PROFIT_CALCULATION"},
                "workflow_reason": "planner selected workflow execution",
                "workflow_confidence": 0.86,
                "required_entities": ["price", "cost"],
                "missing_entities": ["price", "cost"],
                "readiness_decision": {"workflow_executable": False, "missing_fields": ["price", "cost"]},
            },
            "business_situation": {"diagnostics": {}},
        }

        audit = build_cognitive_authority_audit(route)

        self.assertEqual(audit["diagnostic_summary"]["conversation_understanding"]["detected_intent"], "unknown")
        self.assertEqual(audit["diagnostic_summary"]["conversation_understanding"]["confidence"], "LOW")
        self.assertEqual(audit["selected_intent"], "profit_calculation")
        self.assertEqual(audit["selected_workflow"], "PROFIT_CALCULATION")
        self.assertTrue(audit["workflow_admitted"])
        self.assertFalse(audit["workflow_executable"])
        self.assertFalse(audit["cognitive_runtime_authoritative"])
        self.assertEqual(audit["winning_authority"], "workflow_path")
        self.assertIn(LOW_CONFIDENCE_CONFLICT, _conflict_types(audit))

    def test_regression_numeric_profit_workflow_is_coherent(self):
        route = build_task_route({}, "ขาย 80 บาท ต้นทุน 35 บาท กำไรกี่บาท")
        audit = route["business_situation"]["diagnostics"]["cognitive_authority_audit"]

        self.assertEqual(audit["selected_intent"], (route.get("intent_resolution") or {}).get("resolved_intent"))
        self.assertEqual(audit["selected_workflow"], (route.get("planner_output") or {}).get("workflow") or (route.get("intent_resolution") or {}).get("resolved_workflow"))
        self.assertEqual(audit["workflow_admitted"], bool(audit["selected_workflow"]))
        self.assertNotIn(LOW_CONFIDENCE_CONFLICT, _conflict_types(audit))

    def test_regression_customer_growth_profit_drop_records_actual_winning_authority(self):
        route = build_task_route({}, "ลูกค้าเพิ่มแต่กำไรลด")
        audit = route["business_situation"]["diagnostics"]["cognitive_authority_audit"]

        self.assertEqual(audit["selected_intent"], (route.get("intent_resolution") or {}).get("resolved_intent"))
        self.assertEqual(audit["selected_workflow"], (route.get("planner_output") or {}).get("workflow") or (route.get("intent_resolution") or {}).get("resolved_workflow"))
        self.assertTrue(audit["winning_authority"])
        self.assertIn(audit["winning_stage"], [stage.value for stage in AuthorityStage])

    def test_workflow_admitted_despite_cognitive_uncertainty_is_detected(self):
        route = {
            "conversation_understanding": {"detected_intent": "profit_calculation", "confidence": "HIGH"},
            "intent_resolution": {"resolved_intent": "profit_calculation", "resolved_workflow": "PROFIT_CALCULATION"},
            "planner_output": {"workflow": "PROFIT_CALCULATION"},
            "business_workflow": {
                "workflow_action": "start_new",
                "workflow_state": {"workflow_id": "PROFIT_CALCULATION"},
                "required_entities": ["price", "cost"],
                "missing_entities": ["cost"],
            },
            "business_situation": {
                "material_uncertainty": [{"kind": "entity_uncertainty", "description": "cost"}],
                "diagnostics": {},
            },
        }

        audit = build_cognitive_authority_audit(route)

        self.assertIn(WORKFLOW_UNCERTAINTY_CONFLICT, _conflict_types(audit))


if __name__ == "__main__":
    unittest.main()
