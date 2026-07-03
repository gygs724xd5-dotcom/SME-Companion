import ast
import copy
import unittest
from pathlib import Path

from brain.brain_observatory import (
    BRAIN_OBSERVATORY_SOURCE,
    BRAIN_OBSERVATORY_VERSION,
    COGNITIVE_LAYERS,
    build_brain_observatory,
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


class BrainObservatoryTest(unittest.TestCase):
    def test_observatory_reflects_runtime_state(self):
        route = build_task_route({}, "profit price 150 cost 100")

        observatory = build_brain_observatory(route)
        layers = {layer["layer"]: layer for layer in observatory["layers"]}

        self.assertTrue(observatory["observatory_created"])
        self.assertEqual(observatory["observatory_version"], BRAIN_OBSERVATORY_VERSION)
        self.assertEqual(observatory["observatory_source"], BRAIN_OBSERVATORY_SOURCE)
        self.assertEqual(observatory["layer_order"], list(COGNITIVE_LAYERS))
        self.assertEqual(layers["Reality"]["runtime_state"]["user_message"], "profit price 150 cost 100")
        self.assertEqual(
            layers["Business Situation"]["runtime_state"]["current_business"],
            route["business_situation"]["current_business"],
        )
        self.assertEqual(
            layers["Evidence"]["runtime_state"]["evidence_available"],
            route["business_situation"]["diagnostics"]["evidence"]["evidence_available"],
        )
        self.assertEqual(layers["Truth Status"]["status"], "placeholder")
        self.assertEqual(layers["Decision"]["status"], "placeholder")

    def test_constitution_monitor_highlights_violations(self):
        route = build_task_route({}, "profit price 150 cost 100")
        route = copy.deepcopy(route)
        route["diagnostic_probe"] = {
            "routing_changed": True,
            "planner_changed": False,
            "workflow_changed": False,
            "responses_changed": False,
            "execution_changed": False,
            "commit_boundary_changed": True,
        }

        monitor = build_brain_observatory(route)["constitution_monitor"]

        self.assertEqual(monitor["status"], "violation")
        self.assertTrue(monitor["highlight_violations"])
        self.assertIn("routing_changed", monitor["violations"])
        self.assertIn("commit_changed", monitor["violations"])

    def test_diagnostics_timeline_uses_execution_order(self):
        observatory = build_brain_observatory(build_task_route({}, "customer says price is expensive"))
        timeline = observatory["diagnostics_timeline"]

        self.assertEqual([item["layer"] for item in timeline], list(COGNITIVE_LAYERS))
        self.assertEqual([item["order"] for item in timeline], list(range(1, len(COGNITIVE_LAYERS) + 1)))
        self.assertTrue(all("diagnostics" in item for item in timeline))

    def test_observatory_does_not_alter_behavior_or_route_payload(self):
        state = {"business_memory": {"events": [{"payload": {"business_type": "coffee_shop"}}]}}
        baseline = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        route = build_task_route(copy.deepcopy(state), "profit price 150 cost 100")
        before = copy.deepcopy(route)

        observatory = build_brain_observatory(route)

        self.assertEqual(route, before)
        self.assertEqual(_stable_behavior(baseline), _stable_behavior(route))
        self.assertTrue(observatory["diagnostic_only"])
        self.assertFalse(observatory["invariants"]["used_for_routing"])
        self.assertFalse(observatory["invariants"]["used_for_planner"])
        self.assertFalse(observatory["invariants"]["used_for_workflow"])
        self.assertFalse(observatory["invariants"]["used_for_response"])
        self.assertFalse(observatory["invariants"]["used_for_execution"])
        self.assertFalse(observatory["invariants"]["used_for_commit"])

    def test_developer_diagnostics_expose_observatory_without_behavioral_route_fields(self):
        route = build_task_route({}, "profit price 150 cost 100")
        diagnostics = developer_diagnostics(route)

        self.assertTrue(diagnostics["brain_observatory_created"])
        self.assertEqual(diagnostics["brain_observatory_version"], BRAIN_OBSERVATORY_VERSION)
        self.assertIn("Brain Observatory", diagnostics["diagnostic_groups"])
        self.assertEqual(
            diagnostics["diagnostic_groups"]["Brain Observatory"]["runtime_mode"],
            "developer_diagnostics_only",
        )
        self.assertNotIn("observatory_decision", route)
        self.assertNotIn("observatory_route", route)
        self.assertNotIn("observatory_workflow", route)
        self.assertNotIn("observatory_response", route)
        self.assertNotIn("observatory_execution", route)
        self.assertNotIn("observatory_commit", route)

    def test_observatory_has_no_runtime_ownership_imports(self):
        parsed = ast.parse(Path("brain/brain_observatory.py").read_text(encoding="utf-8"))
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
