import unittest

from brain.conversation_manager import route_quick_action
from brain.task_router import build_task_route


COST_UP_30_TO_40 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
COST_UP_RECENTLY = "\u0e0a\u0e48\u0e27\u0e07\u0e19\u0e35\u0e49\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21"
RAW_MATERIAL_UP_PRICE_SAME = "\u0e23\u0e32\u0e04\u0e32\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17 \u0e41\u0e15\u0e48\u0e23\u0e32\u0e04\u0e32\u0e02\u0e32\u0e22\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
COST_DOWN_50_TO_42 = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e25\u0e14\u0e08\u0e32\u0e01 50 \u0e40\u0e2b\u0e25\u0e37\u0e2d 42 \u0e1a\u0e32\u0e17"
CORRECT_COST_STILL_30 = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
WRONG_COST_DID_NOT_INCREASE = "\u0e40\u0e21\u0e37\u0e48\u0e2d\u0e01\u0e35\u0e49\u0e1a\u0e2d\u0e01\u0e1c\u0e34\u0e14 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e40\u0e1e\u0e34\u0e48\u0e21"
LATEST_35_NOT_40 = "\u0e15\u0e31\u0e27\u0e40\u0e25\u0e02\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14\u0e04\u0e37\u0e2d 35 \u0e1a\u0e32\u0e17 \u0e44\u0e21\u0e48\u0e43\u0e0a\u0e48 40"
EXPLICIT_COST_TOTAL = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e13\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 \u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a 30 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 40 \u0e0a\u0e34\u0e49\u0e19"
EXPLICIT_UNIT_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
PROFIT_80_35 = "\u0e02\u0e32\u0e22 80 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
QUANTITY_40 = "40 \u0e0a\u0e34\u0e49\u0e19"


def _entities(route):
    return (route.get("extracted_entities") or {}).get("extracted_entities") or {}


def _workflow(route):
    return route.get("business_workflow") or {}


def _amount(value):
    return value.get("amount") if isinstance(value, dict) else value


def _assert_no_cost_workflow_admission(testcase, route):
    gate = route.get("workflow_admission_gate") or {}
    workflow = _workflow(route)
    testcase.assertFalse(gate.get("admitted"))
    testcase.assertNotEqual(gate.get("decision"), "ADMIT")
    testcase.assertNotEqual(workflow.get("workflow_action"), "start_new")
    testcase.assertIsNone(workflow.get("workflow_state"))
    testcase.assertIsNone(workflow.get("next_question"))
    testcase.assertNotEqual(workflow.get("next_question"), "\u0e02\u0e32\u0e22\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14\u0e01\u0e35\u0e48\u0e0a\u0e34\u0e49\u0e19\u0e04\u0e23\u0e31\u0e1a")
    testcase.assertFalse((route.get("cognitive_authority_audit") or {}).get("workflow_started_before_intent_disambiguation"))
    testcase.assertFalse((route.get("cognitive_authority_audit") or {}).get("workflow_started_despite_low_understanding_confidence"))


class V51041AnalyticalVsExecutableWorkflowHotfixTest(unittest.TestCase):
    def test_cost_change_observation_preserves_comparison_without_cost_workflow(self):
        route = build_task_route({}, COST_UP_30_TO_40)
        entities = _entities(route)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(entities.get("analytical_statement_detected"))
        self.assertTrue(entities.get("comparison_change_detected"))
        self.assertEqual((entities.get("comparison_change") or {}).get("subject"), "cost")
        self.assertEqual((entities.get("comparison_change") or {}).get("from_value"), 30)
        self.assertEqual((entities.get("comparison_change") or {}).get("to_value"), 40)
        self.assertFalse(entities.get("prices"))

    def test_cost_increase_without_numbers_is_analytical_not_executable(self):
        route = build_task_route({}, COST_UP_RECENTLY)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(_entities(route).get("analytical_statement_detected"))

    def test_raw_material_change_does_not_infer_selling_price_from_to_value(self):
        route = build_task_route({}, RAW_MATERIAL_UP_PRICE_SAME)
        entities = _entities(route)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(entities.get("comparison_change_detected"))
        self.assertEqual((entities.get("comparison_change") or {}).get("subject"), "raw_material_cost")
        self.assertFalse(entities.get("prices"))

    def test_cost_decrease_is_comparison_not_cost_workflow(self):
        route = build_task_route({}, COST_DOWN_50_TO_42)

        _assert_no_cost_workflow_admission(self, route)
        self.assertEqual((_entities(route).get("comparison_change") or {}).get("from_value"), 50)
        self.assertEqual((_entities(route).get("comparison_change") or {}).get("to_value"), 42)

    def test_correction_current_cost_suppresses_workflow(self):
        route = build_task_route({}, CORRECT_COST_STILL_30)
        entities = _entities(route)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(entities.get("correction_detected"))
        self.assertEqual(entities.get("correction_current_value"), 30)
        self.assertEqual((entities.get("correction") or {}).get("target"), "cost")

    def test_correction_withdraws_prior_cost_change_claim(self):
        route = build_task_route({}, WRONG_COST_DID_NOT_INCREASE)
        entities = _entities(route)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(entities.get("correction_detected"))
        self.assertIn("cost_change", entities.get("superseded_claims") or [])

    def test_latest_value_correction_retains_provenance_and_latest_value_wins(self):
        route = build_task_route({}, LATEST_35_NOT_40)
        entities = _entities(route)

        _assert_no_cost_workflow_admission(self, route)
        self.assertTrue(entities.get("correction_detected"))
        self.assertEqual(entities.get("correction_current_value"), 35)
        self.assertIn(40, entities.get("superseded_values") or [])

    def test_explicit_cost_total_workflow_still_admitted(self):
        route = build_task_route({}, EXPLICIT_COST_TOTAL)
        workflow = _workflow(route)

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertEqual(_amount((workflow.get("extracted_entities") or {}).get("quantity")), 40)
        self.assertEqual(_amount((workflow.get("extracted_entities") or {}).get("cost")), 30)

    def test_explicit_unit_cost_question_remains_executable(self):
        route = build_task_route({}, EXPLICIT_UNIT_COST)
        workflow = _workflow(route)

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertEqual(_amount((workflow.get("extracted_entities") or {}).get("quantity")), 20)

    def test_profit_calculation_still_returns_45_semantics(self):
        route = build_task_route({}, PROFIT_80_35)
        workflow_entities = _workflow(route).get("extracted_entities") or {}

        self.assertEqual(route["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual((_workflow(route).get("workflow_state") or {}).get("workflow_id"), "PROFIT_CALCULATION")
        self.assertEqual(workflow_entities["price"] - workflow_entities["cost"], 45)

    def test_active_cost_workflow_continuation_still_valid_for_real_answer(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route(state, QUANTITY_40)

        self.assertEqual((_workflow(route).get("workflow_state") or {}).get("workflow_id"), "COST_CALCULATION")
        self.assertIn(_workflow(route).get("workflow_action"), {"continue", "complete"})

    def test_active_cost_workflow_does_not_capture_analytical_or_correction_turn(self):
        for message in (COST_UP_30_TO_40, CORRECT_COST_STILL_30):
            with self.subTest(message=message):
                state = {}
                route_quick_action(state, "cost_calculator")

                route = build_task_route(state, message)

                _assert_no_cost_workflow_admission(self, route)

    def test_authority_invariants_remain_passive(self):
        route = build_task_route({}, COST_UP_30_TO_40)
        judgment = route.get("business_judgment") or {}
        invariants = judgment.get("constitutional_invariants") or {}
        audit_invariants = (route.get("cognitive_authority_audit") or {}).get("constitutional_invariants") or {}
        handoff = route.get("judgment_response_handoff") or {}

        self.assertEqual(judgment.get("judgment_status"), "INSUFFICIENT_EVIDENCE")
        self.assertFalse(invariants.get("recommendation_generated"))
        self.assertFalse(invariants.get("decision_made"))
        self.assertFalse(invariants.get("planner_invoked"))
        self.assertFalse(invariants.get("workflow_started_by_judgment"))
        self.assertFalse(invariants.get("tool_called_by_judgment"))
        self.assertFalse(invariants.get("business_memory_mutated_by_judgment"))
        self.assertFalse(audit_invariants.get("commit_boundary_changed"))
        self.assertEqual(handoff.get("response_commit_boundary_owner"), "response_commit_boundary")
        self.assertFalse(handoff.get("direct_response_commit"))

    def test_new_conversation_does_not_reuse_prior_workflow_state(self):
        state = {}
        route_quick_action(state, "cost_calculator")

        route = build_task_route({}, COST_UP_30_TO_40)

        _assert_no_cost_workflow_admission(self, route)
        self.assertFalse(route.get("planner_locked", False))


if __name__ == "__main__":
    unittest.main()
