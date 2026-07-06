import unittest

from brain.response_mode_engine import ASK_NEXT_FIELD, determine_response_mode
from brain.task_router import build_task_route
from brain.workflow_reply_builder import build_workflow_reply
from brain.workflow_state_machine import update_workflow_state


LIVE_COST_PER_UNIT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
VARIANT_A_COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
VARIANT_C_UNIT_COST_TOTAL = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 15 \u0e1a\u0e32\u0e17 \u0e17\u0e33 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
ANALYTICAL_STATEMENT = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
PROFIT_80_35 = "\u0e02\u0e32\u0e22 80 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
ZERO_QUANTITY = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 0 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"


def _workflow(route):
    return route.get("business_workflow") or {}


def _entities(route):
    return (route.get("extracted_entities") or {}).get("extracted_entities") or {}


class V51042CostPerUnitLiveExecutionHotfixTest(unittest.TestCase):
    def test_exact_live_input_completes_cost_per_unit_execution(self):
        route = build_task_route({}, LIVE_COST_PER_UNIT)
        workflow = _workflow(route)
        state, extracted = update_workflow_state({}, LIVE_COST_PER_UNIT, detected_workflow="COST_CALCULATION")
        reply = build_workflow_reply(state)
        mode = determine_response_mode(workflow_state=state, planner=route.get("planner_output") or {})

        self.assertEqual((route.get("intent_resolution") or {}).get("resolved_intent"), "cost_calculation")
        self.assertEqual((route.get("intent_resolution") or {}).get("resolved_workflow"), "COST_CALCULATION")
        self.assertTrue((route.get("workflow_admission_gate") or {}).get("explicit_calculation_request_detected"))
        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertTrue(workflow.get("workflow_complete"))
        self.assertEqual(workflow.get("missing_entities"), [])
        self.assertEqual(workflow.get("readiness_missing_fields"), [])
        self.assertEqual((route.get("planner_output") or {}).get("missing_information"), [])
        self.assertNotEqual((route.get("planner_output") or {}).get("next_step"), "collect_missing_information")
        self.assertEqual(workflow.get("calculation_variant"), "COST_PER_UNIT_FROM_TOTAL_COST")
        self.assertEqual(workflow.get("requested_output"), "cost_per_unit")
        self.assertEqual(workflow.get("input_total_cost"), 300)
        self.assertEqual(workflow.get("input_total_units"), 20)
        self.assertEqual(workflow.get("computed_cost_per_unit"), 15)
        self.assertEqual(extracted.get("total_cost"), 300)
        self.assertEqual(extracted.get("total_units"), 20)
        self.assertEqual(extracted.get("requested_output"), "cost_per_unit")
        self.assertEqual(state.get("missing_fields"), [])
        self.assertTrue(state.get("is_ready"))
        self.assertNotEqual(mode.mode, ASK_NEXT_FIELD)
        self.assertNotEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertNotIn("\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a", reply.get("reply") or "")
        self.assertFalse(_entities(route).get("prices"))

    def test_variant_a_component_costs_compute_total_without_quantity(self):
        state, extracted = update_workflow_state({}, VARIANT_A_COMPONENT_TOTAL, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}

        self.assertEqual([item["cost"] for item in extracted.get("ingredients_costs") or []], [40, 30, 20])
        self.assertEqual(state.get("missing_fields"), [])
        self.assertTrue(state.get("is_ready"))
        self.assertEqual(trace.get("calculation_variant"), "TOTAL_COST_FROM_COMPONENTS")
        self.assertEqual(trace.get("selected_formula"), "sum_component_costs")
        self.assertEqual(trace.get("computed_total_cost"), 90)

    def test_variant_c_unit_cost_and_quantity_compute_total(self):
        state, extracted = update_workflow_state({}, VARIANT_C_UNIT_COST_TOTAL, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}

        self.assertEqual(extracted.get("unit_cost"), 15)
        self.assertEqual(extracted.get("total_units"), 20)
        self.assertNotIn("selling_price", extracted)
        self.assertEqual(state.get("missing_fields"), [])
        self.assertEqual(trace.get("calculation_variant"), "TOTAL_COST_FROM_UNIT_COST")
        self.assertEqual(trace.get("selected_formula"), "unit_cost_times_quantity")
        self.assertEqual(trace.get("computed_total_cost"), 300)

    def test_analytical_statement_remains_suppressed(self):
        route = build_task_route({}, ANALYTICAL_STATEMENT)

        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))
        self.assertTrue(_entities(route).get("analytical_statement_detected"))

    def test_correction_remains_suppressed(self):
        route = build_task_route({}, CORRECTION)

        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))
        self.assertTrue(_entities(route).get("correction_detected"))
        self.assertEqual(_entities(route).get("correction_current_value"), 30)

    def test_profit_calculation_still_returns_45(self):
        route = build_task_route({}, PROFIT_80_35)
        workflow_entities = _workflow(route).get("extracted_entities") or {}

        self.assertEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertEqual((_workflow(route).get("workflow_state") or {}).get("workflow_id"), "PROFIT_CALCULATION")
        self.assertEqual(workflow_entities["price"] - workflow_entities["cost"], 45)

    def test_division_by_zero_blocks_execution_safely(self):
        state, extracted = update_workflow_state({}, ZERO_QUANTITY, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}
        reply = build_workflow_reply(state)

        self.assertEqual(extracted.get("total_cost"), 300)
        self.assertEqual(extracted.get("total_units"), 0)
        self.assertFalse(state.get("is_ready"))
        self.assertIn("total_units", state.get("missing_fields") or [])
        self.assertEqual(trace.get("validation_error"), "quantity_must_be_greater_than_zero")
        self.assertIsNone(trace.get("computed_cost_per_unit"))
        self.assertEqual(reply.get("response_mode"), ASK_NEXT_FIELD)


if __name__ == "__main__":
    unittest.main()
