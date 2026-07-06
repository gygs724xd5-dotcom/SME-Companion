import unittest

from brain.response_mode_engine import ASK_NEXT_FIELD
from brain.task_router import build_task_route
from brain.workflow_output_renderer import generate_cost_calculation_reply
from brain.workflow_reply_builder import build_workflow_reply
from brain.workflow_state_machine import update_workflow_state


LIVE_COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
VARIANT_B = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 300 \u0e1a\u0e32\u0e17 \u0e17\u0e33\u0e44\u0e14\u0e49 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e15\u0e48\u0e2d\u0e0a\u0e34\u0e49\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
VARIANT_C = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e0a\u0e34\u0e49\u0e19\u0e25\u0e30 15 \u0e1a\u0e32\u0e17 \u0e17\u0e33 20 \u0e0a\u0e34\u0e49\u0e19 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
PROFIT = "\u0e02\u0e32\u0e22 80 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
ANALYTICAL = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
CORRECTION = "\u0e41\u0e01\u0e49\u0e43\u0e2b\u0e21\u0e48 \u0e08\u0e23\u0e34\u0e07 \u0e46 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e22\u0e31\u0e07 30 \u0e1a\u0e32\u0e17\u0e40\u0e17\u0e48\u0e32\u0e40\u0e14\u0e34\u0e21"
LABELED_FEES = "\u0e04\u0e48\u0e32\u0e01\u0e25\u0e48\u0e2d\u0e07 50 \u0e04\u0e48\u0e32\u0e2a\u0e48\u0e07 30 \u0e04\u0e48\u0e32\u0e41\u0e23\u0e07 20 \u0e23\u0e27\u0e21\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
LABELED_BAHT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17 \u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
BARE_AMBIGUOUS = "40 30 20 \u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"


def _workflow(route):
    return route.get("business_workflow") or {}


def _route_entities(route):
    return (_workflow(route).get("extracted_entities") or {})


class V510421ComponentCostLivePathHotfixTest(unittest.TestCase):
    def test_exact_live_input_completes_and_generates_90(self):
        route = build_task_route({}, LIVE_COMPONENT_TOTAL)
        workflow = _workflow(route)
        state, extracted = update_workflow_state({}, LIVE_COMPONENT_TOTAL, detected_workflow="COST_CALCULATION")
        visible = generate_cost_calculation_reply(state)
        reply = build_workflow_reply(state, generated_reply=visible)

        self.assertEqual((route.get("intent_resolution") or {}).get("resolved_intent"), "cost_calculation")
        self.assertEqual((route.get("intent_resolution") or {}).get("resolved_workflow"), "COST_CALCULATION")
        self.assertTrue((route.get("workflow_admission_gate") or {}).get("explicit_calculation_request_detected"))
        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertEqual(workflow.get("missing_entities"), [])
        self.assertEqual(workflow.get("readiness_missing_fields"), [])
        self.assertEqual(workflow.get("required_entities"), ["component_costs"])
        self.assertEqual(workflow.get("completed_entities"), ["component_costs"])
        self.assertEqual(workflow.get("requested_output"), "total_cost")
        self.assertEqual(workflow.get("calculation_variant"), "TOTAL_COST_FROM_COMPONENTS")
        self.assertEqual(workflow.get("selected_formula"), "sum_component_costs")
        self.assertEqual(workflow.get("computed_total_cost"), 90)
        self.assertEqual(state.get("missing_fields"), [])
        self.assertTrue(state.get("is_ready"))
        self.assertEqual(reply.get("response_mode"), "GENERATE_OUTPUT")
        self.assertNotEqual(reply.get("response_mode"), ASK_NEXT_FIELD)
        self.assertNotIn("\u0e21\u0e35\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e2b\u0e23\u0e37\u0e2d\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e27\u0e31\u0e15\u0e16\u0e38\u0e14\u0e34\u0e1a", reply.get("reply") or "")
        self.assertIn("90", visible)
        self.assertEqual([item["amount"] for item in extracted.get("component_costs") or []], [40, 30, 20])

    def test_component_labels_amounts_and_provenance_are_preserved(self):
        route = build_task_route({}, LIVE_COMPONENT_TOTAL)
        components = _route_entities(route).get("component_costs") or []

        self.assertEqual([item["label"] for item in components], ["\u0e41\u0e1b\u0e49\u0e07", "\u0e44\u0e02\u0e48", "\u0e19\u0e49\u0e33\u0e15\u0e32\u0e25"])
        self.assertEqual([item["amount"] for item in components], [40, 30, 20])
        self.assertEqual([item["order"] for item in components], [0, 1, 2])
        self.assertTrue(all(item.get("raw_text") for item in components))
        self.assertTrue(all(item.get("source") == "workflow_field_extractor" for item in components))
        self.assertTrue(all(item.get("provenance") == "deterministic_labeled_component_cost" for item in components))

    def test_variant_b_total_cost_per_unit_still_returns_15(self):
        route = build_task_route({}, VARIANT_B)
        workflow = _workflow(route)
        state, _ = update_workflow_state({}, VARIANT_B, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertEqual(trace.get("calculation_variant"), "COST_PER_UNIT_FROM_TOTAL_COST")
        self.assertEqual(trace.get("computed_cost_per_unit"), 15)

    def test_variant_c_unit_cost_quantity_still_returns_300(self):
        route = build_task_route({}, VARIANT_C)
        workflow = _workflow(route)
        state, _ = update_workflow_state({}, VARIANT_C, detected_workflow="COST_CALCULATION")
        trace = state.get("calculation_trace") or {}

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertEqual(trace.get("calculation_variant"), "TOTAL_COST_FROM_UNIT_COST")
        self.assertEqual(trace.get("computed_total_cost"), 300)

    def test_profit_workflow_still_returns_45(self):
        route = build_task_route({}, PROFIT)
        workflow = _workflow(route)
        entities = workflow.get("extracted_entities") or {}

        self.assertEqual((workflow.get("workflow_state") or {}).get("workflow_id"), "PROFIT_CALCULATION")
        self.assertEqual(entities["price"] - entities["cost"], 45)

    def test_analytical_statement_remains_suppressed(self):
        route = build_task_route({}, ANALYTICAL)
        entities = (route.get("extracted_entities") or {}).get("extracted_entities") or {}

        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))
        self.assertTrue(entities.get("analytical_statement_detected"))
        comparison = (route.get("workflow_admission_gate") or {}).get("comparison_values") or {}
        self.assertEqual(comparison.get("from_value"), 30)
        self.assertEqual(comparison.get("to_value"), 40)
        self.assertNotIn("selling_price", _route_entities(route))

    def test_correction_remains_suppressed(self):
        route = build_task_route({}, CORRECTION)
        entities = (route.get("extracted_entities") or {}).get("extracted_entities") or {}

        self.assertNotEqual((route.get("workflow_admission_gate") or {}).get("decision"), "ADMIT")
        self.assertIsNone((_workflow(route).get("workflow_state") or {}).get("workflow_id"))
        self.assertTrue(entities.get("correction_detected"))
        self.assertEqual(entities.get("correction_current_value"), 30)

    def test_labeled_fee_components_sum_to_100(self):
        route = build_task_route({}, LABELED_FEES)
        workflow = _workflow(route)
        state, extracted = update_workflow_state({}, LABELED_FEES, detected_workflow="COST_CALCULATION")

        self.assertEqual([item["label"] for item in extracted.get("component_costs") or []], ["\u0e04\u0e48\u0e32\u0e01\u0e25\u0e48\u0e2d\u0e07", "\u0e04\u0e48\u0e32\u0e2a\u0e48\u0e07", "\u0e04\u0e48\u0e32\u0e41\u0e23\u0e07"])
        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertEqual(workflow.get("computed_total_cost"), 100)
        self.assertIn("100", generate_cost_calculation_reply(state))

    def test_labeled_baht_components_sum_to_90(self):
        route = build_task_route({}, LABELED_BAHT)
        workflow = _workflow(route)
        components = _route_entities(route).get("component_costs") or []

        self.assertEqual(workflow.get("workflow_action"), "complete")
        self.assertEqual(workflow.get("computed_total_cost"), 90)
        self.assertEqual([item["currency"] for item in components], ["THB", "THB", "THB"])

    def test_bare_ambiguous_numbers_do_not_become_component_costs(self):
        route = build_task_route({}, BARE_AMBIGUOUS)
        state, extracted = update_workflow_state({}, BARE_AMBIGUOUS, detected_workflow="COST_CALCULATION")

        self.assertFalse((_route_entities(route).get("component_costs") or []))
        self.assertFalse(extracted.get("component_costs"))
        self.assertIn("ingredients_costs", state.get("missing_fields") or [])
        self.assertFalse(state.get("is_ready"))


if __name__ == "__main__":
    unittest.main()
