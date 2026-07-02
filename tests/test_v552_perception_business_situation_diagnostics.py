import ast
import copy
import unittest
from pathlib import Path

from brain.business_situation import build_business_situation
from brain.perception_engine import build_percept
from brain.perception_signals import build_signal_set_from_percept_fields
from brain.perception_situation_diagnostics import (
    PERCEPTION_SITUATION_DIAGNOSTICS_SOURCE,
    PERCEPTION_SITUATION_DIAGNOSTICS_VERSION,
    build_perception_situation_diagnostics,
)
from brain.task_router import build_task_route


def _without_situation_identity(situation: dict) -> dict:
    payload = copy.deepcopy(situation)
    payload.pop("situation_id", None)
    diagnostics = payload.get("diagnostics") or {}
    diagnostics.pop("perception", None)
    payload["diagnostics"] = diagnostics
    return payload


class PerceptionBusinessSituationDiagnosticsTest(unittest.TestCase):
    def test_helper_creates_diagnostics_only_handoff(self):
        percept = build_percept(
            user_message="price?",
            business_memory_reference={"store": "demo"},
            active_workspace="pricing",
        )
        signal_set = build_signal_set_from_percept_fields(
            user_message=percept.user_message,
            business_memory_reference=percept.business_memory_reference,
            active_workspace=percept.active_workspace,
        )

        diagnostics = build_perception_situation_diagnostics(
            percept=percept,
            signal_set=signal_set,
        )

        self.assertTrue(diagnostics["perception_situation_diagnostics_created"])
        self.assertEqual(
            diagnostics["perception_situation_diagnostics_version"],
            PERCEPTION_SITUATION_DIAGNOSTICS_VERSION,
        )
        self.assertEqual(
            diagnostics["perception_situation_diagnostics_source"],
            PERCEPTION_SITUATION_DIAGNOSTICS_SOURCE,
        )
        self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")
        self.assertEqual(diagnostics["percept_signal_count"], 3)
        self.assertEqual(diagnostics["canonical_signal_count"], 3)
        self.assertFalse(diagnostics["handoff_changed_business_situation"])
        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["memory_changed"])
        self.assertFalse(diagnostics["execution_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])

    def test_business_situation_stores_perception_diagnostics_without_behavior_change(self):
        perception_diagnostics = build_perception_situation_diagnostics(
            percept=build_percept(user_message="customer says price is expensive"),
            signal_set=build_signal_set_from_percept_fields(user_message="customer says price is expensive"),
        )
        kwargs = {
            "user_message": "customer says price is expensive",
            "conversation_understanding": {"detected_intent": "pricing_question", "confidence": 0.8},
            "business_context": {
                "detected_intent": "pricing_question",
                "business_type": "coffee_shop",
                "confidence": 0.7,
            },
            "intent_resolution": {"resolved_intent": "pricing_question"},
            "canonical_entities": {"slots": {"budget": "1000"}, "entities": []},
            "extracted_entities": {"missing_entities": ["target_customer"]},
        }

        baseline = build_business_situation(**kwargs)
        with_perception = build_business_situation(
            **kwargs,
            perception_diagnostics=perception_diagnostics,
        )

        self.assertEqual(
            _without_situation_identity(baseline),
            _without_situation_identity(with_perception),
        )
        stored = with_perception["diagnostics"]["perception"]
        self.assertTrue(stored["perception_situation_diagnostics_created"])
        self.assertEqual(stored["runtime_mode"], "diagnostics_only")
        self.assertFalse(stored["handoff_changed_business_situation"])

    def test_task_route_exposes_perception_diagnostics_without_planner_or_workflow_change(self):
        baseline = build_task_route({}, "profit price 150 cost 100")
        route = build_task_route({}, "profit price 150 cost 100")
        perception = ((route.get("business_situation") or {}).get("diagnostics") or {}).get("perception") or {}

        self.assertTrue(perception["perception_situation_diagnostics_created"])
        self.assertEqual(perception["runtime_mode"], "diagnostics_only")
        self.assertEqual(perception["canonical_signal_types"], ["user_message"])
        self.assertEqual(baseline["planner_output"]["task_type"], route["planner_output"]["task_type"])
        self.assertEqual(baseline["planner_output"]["workflow"], route["planner_output"]["workflow"])
        self.assertEqual(baseline["planner_output"]["next_step"], route["planner_output"]["next_step"])
        self.assertEqual(
            baseline["business_workflow"].get("workflow_action"),
            route["business_workflow"].get("workflow_action"),
        )
        self.assertEqual(
            (baseline["business_workflow"].get("workflow_state") or {}).get("workflow_id"),
            (route["business_workflow"].get("workflow_state") or {}).get("workflow_id"),
        )
        self.assertEqual(baseline["workflow_response_allowed"], route["workflow_response_allowed"])
        self.assertFalse(perception["routing_changed"])
        self.assertFalse(perception["planner_changed"])
        self.assertFalse(perception["workflow_changed"])
        self.assertFalse(perception["responses_changed"])
        self.assertFalse(perception["commit_boundary_changed"])

    def test_perception_diagnostics_do_not_create_behavioral_top_level_route_fields(self):
        route = build_task_route({}, "start workflow")

        self.assertNotIn("perception_decision", route)
        self.assertNotIn("perception_route", route)
        self.assertNotIn("perception_workflow", route)
        self.assertNotIn("perception_response", route)
        self.assertNotIn("perception_commit", route)

    def test_helper_has_no_runtime_ownership_imports(self):
        source = Path("brain/perception_situation_diagnostics.py").read_text(encoding="utf-8")
        parsed = ast.parse(source)
        imported_modules = []
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")

        forbidden = (
            "task_router",
            "planner",
            "workflow",
            "response",
            "llm",
            "memory",
        )
        self.assertFalse(
            [
                module
                for module in imported_modules
                if any(name in module for name in forbidden)
            ]
        )


if __name__ == "__main__":
    unittest.main()
