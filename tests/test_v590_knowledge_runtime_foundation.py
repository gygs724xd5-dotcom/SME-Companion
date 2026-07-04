import copy
import unittest

from brain.brain_observatory import build_brain_observatory
from brain.business_knowledge_registry import (
    BusinessKnowledgeRegistry,
    FRAME_TO_KNOWLEDGE,
    validate_knowledge_registry,
)
from brain.knowledge_metric_adapter import extract_canonical_metrics
from brain.knowledge_runtime import build_knowledge_runtime
from brain.task_router import build_task_route


CAPACITY = "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19"
CAPACITY_DAY = "\u0e17\u0e33\u0e44\u0e14\u0e49 100 \u0e0a\u0e34\u0e49\u0e19\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19"
REVENUE = "\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22 20,000 \u0e1a\u0e32\u0e17"
COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17"
PROFIT_DROP = "\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e41\u0e15\u0e48\u0e01\u0e33\u0e44\u0e23\u0e25\u0e14"
STARTUP = "\u0e2d\u0e22\u0e32\u0e01\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19\u0e02\u0e32\u0e22\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21\u0e41\u0e15\u0e48\u0e44\u0e21\u0e48\u0e23\u0e39\u0e49\u0e43\u0e0a\u0e49\u0e17\u0e38\u0e19\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
STOCK_LOW = "\u0e02\u0e2d\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d\u0e41\u0e04\u0e48 3 \u0e0a\u0e34\u0e49\u0e19"
CASH_STRESS = "\u0e02\u0e32\u0e22\u0e44\u0e14\u0e49\u0e41\u0e15\u0e48\u0e44\u0e21\u0e48\u0e21\u0e35\u0e40\u0e07\u0e34\u0e19\u0e2a\u0e14"
PROFIT_REQUEST = "\u0e0a\u0e48\u0e27\u0e22\u0e04\u0e33\u0e19\u0e27\u0e19\u0e01\u0e33\u0e44\u0e23\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22"
NUMERIC_PROFIT = "\u0e02\u0e32\u0e22 80 \u0e1a\u0e32\u0e17 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19 35 \u0e1a\u0e32\u0e17 \u0e01\u0e33\u0e44\u0e23\u0e01\u0e35\u0e48\u0e1a\u0e32\u0e17"
MADE_TO_ORDER_TOPIC = "\u0e02\u0e32\u0e22\u0e0a\u0e39\u0e04\u0e23\u0e35\u0e21 \u0e17\u0e33\u0e15\u0e32\u0e21\u0e2d\u0e2d\u0e40\u0e14\u0e2d\u0e23\u0e4c"


def _knowledge(message: str, state: dict | None = None) -> dict:
    return build_task_route(state or {}, message)["business_situation"]["diagnostics"]["knowledge"]


def _ids(items):
    return [item["knowledge_id"] for item in items]


class V590KnowledgeRuntimeFoundationTest(unittest.TestCase):
    def test_registry_loads_all_seed_definitions_and_validates(self):
        registry = BusinessKnowledgeRegistry()
        definitions = registry.list()
        ids = [item.knowledge_id for item in definitions]
        validation = validate_knowledge_registry(registry)

        self.assertEqual(len(definitions), 12)
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["registered_knowledge_count"], 12)
        for expected in {
            "STARTUP_COST_STRUCTURE", "PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS",
            "PRICING_POSITION", "SALES_FUNNEL", "CUSTOMER_RETENTION",
            "INVENTORY_HEALTH", "SUPPLY_RELIABILITY", "OPERATING_CAPACITY",
            "ORDER_FULFILLMENT", "CASH_CONVERSION", "PROCESS_FLOW",
        }:
            self.assertIn(expected, ids)

    def test_registry_contract_fields_and_relationship_rules_are_present(self):
        valid_frames = set(FRAME_TO_KNOWLEDGE)
        for definition in BusinessKnowledgeRegistry().list():
            self.assertTrue(definition.allowed_outputs)
            self.assertTrue(definition.forbidden_outputs)
            self.assertIsNotNone(definition.skill_references)
            self.assertTrue(definition.source_provenance)
            self.assertTrue(set(definition.applicable_frames).issubset(valid_frames))
            rule_ids = [rule.rule_id for rule in definition.relationship_rules]
            self.assertEqual(len(rule_ids), len(set(rule_ids)))
        self.assertTrue(BusinessKnowledgeRegistry().get("OPERATING_CAPACITY").misuse_constraints)
        self.assertTrue(BusinessKnowledgeRegistry().get("INVENTORY_HEALTH").misuse_constraints)

    def test_frame_based_selection_and_caps_are_deterministic(self):
        cases = {
            "PROFIT_COMPRESSION": ("PROFITABILITY_STRUCTURE", "UNIT_ECONOMICS"),
            "SALES_DECLINE": ("SALES_FUNNEL",),
            "INVENTORY_RISK": ("INVENTORY_HEALTH",),
            "CASH_FLOW_STRESS": ("CASH_CONVERSION",),
            "CAPACITY_CONSTRAINT": ("OPERATING_CAPACITY",),
        }
        for frame, expected_ids in cases.items():
            first = build_knowledge_runtime(perspective_runtime={"selected_frame": frame, "candidate_frames": []})
            second = build_knowledge_runtime(perspective_runtime={"selected_frame": frame, "candidate_frames": []})
            ids = _ids(first["primary_knowledge"] + first["secondary_knowledge"])
            for expected in expected_ids:
                self.assertIn(expected, ids)
            self.assertLessEqual(len(first["primary_knowledge"]), 2)
            self.assertLessEqual(len(first["secondary_knowledge"]), 3)
            self.assertEqual(first["primary_knowledge"], second["primary_knowledge"])
            self.assertEqual(first["secondary_knowledge"], second["secondary_knowledge"])

    def test_context_based_selection_outside_known_frame(self):
        startup = build_knowledge_runtime(user_message=STARTUP, perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"})
        capacity = build_knowledge_runtime(user_message=CAPACITY, perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"})
        mto = build_knowledge_runtime(
            user_message=CAPACITY,
            perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"},
            business_situation={"known_evidence": [{"summary": MADE_TO_ORDER_TOPIC}]},
        )

        self.assertIn("STARTUP_COST_STRUCTURE", _ids(startup["primary_knowledge"] + startup["secondary_knowledge"]))
        self.assertIn("OPERATING_CAPACITY", _ids(capacity["primary_knowledge"]))
        self.assertIn("ORDER_FULFILLMENT", _ids(mto["secondary_knowledge"]))

    def test_ranking_handles_context_freshness_contradiction_redundancy_and_input_immutability(self):
        situation = {"known_evidence": [{"summary": MADE_TO_ORDER_TOPIC}], "objective": CAPACITY}
        before = copy.deepcopy(situation)
        result = build_knowledge_runtime(
            user_message=CAPACITY,
            business_situation=situation,
            perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"},
        )
        self.assertEqual(situation, before)
        self.assertEqual(_ids(result["primary_knowledge"])[0], "OPERATING_CAPACITY")
        self.assertLessEqual(len(result["primary_knowledge"]), 2)
        self.assertTrue(result["deferred_knowledge"] or result["secondary_knowledge"])

        contradicted = build_knowledge_runtime(
            user_message="\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e40\u0e1b\u0e34\u0e14\u0e23\u0e49\u0e32\u0e19 startupcost",
            perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"},
        )
        self.assertTrue(any(item["knowledge_id"] == "STARTUP_COST_STRUCTURE" for item in contradicted["excluded_knowledge"]))

    def test_metric_adapter_completeness_and_non_invention(self):
        quantity = extract_canonical_metrics(user_message=CAPACITY)["output_quantity"]
        complete_quantity = extract_canonical_metrics(user_message=CAPACITY_DAY)["output_quantity"]
        revenue = extract_canonical_metrics(user_message=REVENUE)["total_revenue"]
        cost = extract_canonical_metrics(user_message=COST)["unit_cost"]
        profit = extract_canonical_metrics(user_message="\u0e01\u0e33\u0e44\u0e23\u0e25\u0e14")["net_profit"]

        self.assertEqual(quantity["value"], 100)
        self.assertEqual(quantity["unit"], "pieces")
        self.assertEqual(quantity["completeness_status"], "AVAILABLE_INCOMPLETE")
        self.assertIn("timeframe", quantity["missing_components"])
        self.assertEqual(complete_quantity["timeframe"], "day")
        self.assertEqual(complete_quantity["completeness_status"], "AVAILABLE_COMPLETE")
        self.assertEqual(revenue["value"], 20000)
        self.assertEqual(revenue["currency"], "THB")
        self.assertIn("timeframe", revenue["missing_components"])
        self.assertIn("scope", cost["missing_components"])
        self.assertIn("comparison_period", profit["missing_components"])
        self.assertNotEqual(quantity.get("metric_id"), "maximum_capacity")

    def test_metric_adapter_historical_unverified_conflicting_and_structured_values(self):
        historical = extract_canonical_metrics(user_message="\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e01\u0e48\u0e2d\u0e19\u0e22\u0e2d\u0e14\u0e02\u0e32\u0e22 20000 \u0e1a\u0e32\u0e17")["total_revenue"]
        unverified = extract_canonical_metrics(user_message="\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e19\u0e48\u0e32\u0e08\u0e30 35 \u0e1a\u0e32\u0e17")["unit_cost"]
        conflicting = extract_canonical_metrics(
            user_message=REVENUE,
            structured_business_data={"total_revenue": {"value": 15000, "currency": "THB"}},
        )["total_revenue"]

        self.assertEqual(historical["completeness_status"], "HISTORICAL")
        self.assertEqual(unverified["completeness_status"], "UNVERIFIED")
        self.assertEqual(conflicting["completeness_status"], "CONFLICTING")
        self.assertIn("conflict_resolution", conflicting["missing_components"])

    def test_capacity_gap_prioritization_and_handoff(self):
        result = build_knowledge_runtime(
            user_message=CAPACITY,
            business_situation={"known_evidence": [{"summary": MADE_TO_ORDER_TOPIC}]},
            perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"},
        )
        gap = result["next_knowledge_gap"]
        handoff = result["clarification_handoff"]

        self.assertEqual(gap["metric_id"], "output_time_period")
        self.assertEqual(gap["priority_tier"], "BLOCKING")
        self.assertIn("capacity_requires_time_unit", gap["blocking_relationship_rules"])
        self.assertEqual(handoff["source_gap_id"], gap["gap_id"])
        self.assertEqual(handoff["known_partial_value"]["value"], 100)
        self.assertIn("Capacity requires", handoff["why_it_matters"])
        self.assertEqual(handoff["handoff_type"], "REQUEST_TIMEFRAME")
        self.assertEqual(handoff["conversation_constraints"]["max_questions"], 1)

    def test_gap_merge_suppression_workflow_ownership_and_conflicts(self):
        result = build_knowledge_runtime(
            user_message=PROFIT_DROP,
            perspective_runtime={"selected_frame": "PROFIT_COMPRESSION"},
            workflow_owned_fields=["selling_price", "unit_cost"],
        )
        gap_ids = [gap["metric_id"] for gap in result["knowledge_gaps"]]
        self.assertEqual(gap_ids.count("analysis_timeframe"), 1)
        self.assertEqual(result["next_knowledge_gap"]["metric_id"], "analysis_timeframe")

        duplicate = build_knowledge_runtime(
            user_message=CAPACITY,
            perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"},
            conversation_context={"application_state": {"conversation": {"chat_history": [{"role": "assistant", "content": "100 ชิ้นนี้ทำได้ต่อวันหรือต่อรอบครับ?"}]}}},
        )
        self.assertTrue(duplicate["suppressed_gaps"])

        conflict = build_knowledge_runtime(
            user_message=REVENUE,
            perspective_runtime={"selected_frame": "PROFIT_COMPRESSION"},
            structured_business_data={"total_revenue": {"value": 15000, "currency": "THB"}},
        )
        self.assertTrue(any(gap["gap_type"] == "CONFLICT_UNRESOLVED" for gap in conflict["knowledge_gaps"]))

    def test_clarification_authority_uses_handoff_without_exposing_internal_ids(self):
        route = build_task_route({"conversation_memory": {"business_topic": MADE_TO_ORDER_TOPIC}}, CAPACITY)
        text = route["final_response_text"]
        clarification = route["clarification_authority"]

        self.assertEqual(clarification["selected_response_mode"], "KNOWLEDGE_GAP_CLARIFICATION")
        self.assertTrue(clarification["knowledge_used_for_gap"])
        self.assertEqual(clarification["clarification_handoff_type"], "REQUEST_TIMEFRAME")
        self.assertIn("\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19", text)
        self.assertIn("\u0e15\u0e48\u0e2d\u0e23\u0e2d\u0e1a", text)
        self.assertNotIn("OPERATING_CAPACITY", text)
        self.assertNotIn("\u0e02\u0e22\u0e32\u0e22", text)

    def test_audit_and_observatory_record_knowledge_boundaries(self):
        route = build_task_route({}, PROFIT_DROP)
        audit = route["cognitive_authority_audit"]
        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}

        self.assertTrue(audit["knowledge_runtime_consulted"])
        self.assertIn("PROFITABILITY_STRUCTURE", audit["knowledge_primary_ids"])
        self.assertTrue(audit["knowledge_gap_selected"])
        self.assertTrue(audit["knowledge_authoritative_for_relevance"])
        self.assertFalse(audit["knowledge_authoritative_for_judgment"])
        self.assertFalse(audit["knowledge_authoritative_for_decision"])
        self.assertTrue(audit["knowledge_gap_prioritization_consulted"])
        self.assertTrue(audit["clarification_handoff_created"])
        self.assertEqual(observatory["layer_order"][observatory["layer_order"].index("Perspective") + 1], "Knowledge")
        self.assertEqual(layers["Knowledge"]["runtime_state"]["registered_knowledge_count"], 12)
        self.assertIn("next_knowledge_gap", layers["Knowledge"]["runtime_state"])

    def test_constitutional_boundaries(self):
        result = build_knowledge_runtime(user_message=CAPACITY, perspective_runtime={"selected_frame": "UNKNOWN_SITUATION"})
        invariants = result["constitutional_invariants"]
        self.assertTrue(invariants["knowledge_runtime_created"])
        self.assertTrue(invariants["knowledge_retrieval_performed"])
        self.assertTrue(invariants["knowledge_selection_performed"])
        self.assertTrue(invariants["metric_completeness_interpreted"])
        self.assertTrue(invariants["knowledge_gap_prioritization_performed"])
        self.assertFalse(invariants["root_causes_diagnosed"])
        self.assertFalse(invariants["business_judgment_produced"])
        self.assertFalse(invariants["decision_made"])
        self.assertFalse(invariants["recommendations_generated"])
        self.assertFalse(invariants["workflow_internal_logic_changed"])
        self.assertFalse(invariants["business_memory_mutated"])
        self.assertFalse(invariants["external_model_called"])

    def test_required_visible_outcomes(self):
        capacity = build_task_route({"conversation_memory": {"business_topic": MADE_TO_ORDER_TOPIC}}, CAPACITY)
        startup = build_task_route({}, STARTUP)
        profit = build_task_route({}, PROFIT_DROP)
        stock = build_task_route({}, STOCK_LOW)
        cash = build_task_route({}, CASH_STRESS)
        workflow = build_task_route({}, PROFIT_REQUEST)
        numeric = build_task_route({}, NUMERIC_PROFIT)

        capacity_knowledge = capacity["business_situation"]["diagnostics"]["knowledge"]
        self.assertIn("OPERATING_CAPACITY", _ids(capacity_knowledge["primary_knowledge"]))
        self.assertEqual(capacity_knowledge["incomplete_metrics"]["output_quantity"]["value"], 100)
        self.assertEqual(capacity_knowledge["next_knowledge_gap"]["metric_id"], "output_time_period")
        self.assertIn("\u0e15\u0e48\u0e2d\u0e27\u0e31\u0e19", capacity["final_response_text"])
        self.assertNotIn("\u0e02\u0e22\u0e32\u0e22", capacity["final_response_text"])

        self.assertIn("STARTUP_COST_STRUCTURE", _ids(startup["business_situation"]["diagnostics"]["knowledge"]["primary_knowledge"]))
        self.assertNotEqual(startup["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertIn("\u0e40\u0e1b\u0e34\u0e14\u0e2b\u0e19\u0e49\u0e32\u0e23\u0e49\u0e32\u0e19", startup["final_response_text"])
        self.assertNotRegex(startup["final_response_text"], r"\d{3,}")

        profit_knowledge = profit["business_situation"]["diagnostics"]["knowledge"]
        self.assertEqual(profit["business_situation"]["diagnostics"]["perspective"]["selected_frame"], "PROFIT_COMPRESSION")
        self.assertIn("PROFITABILITY_STRUCTURE", _ids(profit_knowledge["primary_knowledge"]))
        self.assertIn("UNIT_ECONOMICS", _ids(profit_knowledge["primary_knowledge"]))
        self.assertNotEqual(profit["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertIn("\u0e0a\u0e48\u0e27\u0e07", profit["final_response_text"])
        self.assertNotIn("\u0e04\u0e27\u0e23", profit["final_response_text"])

        stock_knowledge = stock["business_situation"]["diagnostics"]["knowledge"]
        self.assertIn("INVENTORY_HEALTH", _ids(stock_knowledge["primary_knowledge"]))
        self.assertEqual(stock_knowledge["next_knowledge_gap"]["question_intent"], "ESTABLISH_SALES_VELOCITY")
        self.assertNotIn("\u0e2a\u0e31\u0e48\u0e07\u0e40\u0e1e\u0e34\u0e48\u0e21", stock["final_response_text"])

        cash_knowledge = cash["business_situation"]["diagnostics"]["knowledge"]
        self.assertIn("CASH_CONVERSION", _ids(cash_knowledge["primary_knowledge"]))
        self.assertEqual(cash_knowledge["next_knowledge_gap"]["question_intent"], "ESTABLISH_PAYMENT_TIMING")
        self.assertNotIn("\u0e25\u0e39\u0e01\u0e2b\u0e19\u0e35\u0e49", cash["final_response_text"])

        self.assertEqual(workflow["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertFalse(workflow["clarification_authority"]["knowledge_used_for_gap"])
        self.assertEqual(numeric["workflow_admission_gate"]["decision"], "ADMIT")
        self.assertEqual(numeric["business_workflow"]["extracted_entities"]["price"] - numeric["business_workflow"]["extracted_entities"]["cost"], 45)


if __name__ == "__main__":
    unittest.main()
