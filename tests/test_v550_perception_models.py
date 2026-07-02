import ast
import copy
import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from brain.perception_engine import PERCEPTION_DIAGNOSTICS, build_percept
from brain.perception_models import PERCEPTION_VERSION, Percept


class PerceptionModelsTest(unittest.TestCase):
    def test_percept_creation(self):
        percept = build_percept(
            user_message="Customer says the price is expensive",
            active_workspace="sales",
            current_context={"surface": "chat"},
        )

        self.assertIsInstance(percept, Percept)
        self.assertTrue(percept.percept_id.startswith("percept_"))
        self.assertEqual(percept.version, PERCEPTION_VERSION)
        self.assertEqual(percept.runtime_mode, "diagnostics_only")
        self.assertEqual(percept.created_by, "perception_engine")
        self.assertIn("current_user_message", percept.detected_signal_types)

    def test_serialization(self):
        payload = build_percept(
            user_message="hello",
            uploaded_documents=[{"name": "invoice.pdf"}],
            dashboard_state={"tab": "overview"},
        ).to_dict()

        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertIn("percept_id", payload)
        self.assertIn(PERCEPTION_VERSION, encoded)
        self.assertEqual(payload["uploaded_documents"], [{"name": "invoice.pdf"}])
        self.assertEqual(payload["dashboard_state"], {"tab": "overview"})

    def test_immutable_behavior(self):
        source = {"nested": {"value": 1}}
        percept = build_percept(dashboard_state=source)

        with self.assertRaises(FrozenInstanceError):
            percept.user_message = "changed"
        with self.assertRaises(TypeError):
            percept.dashboard_state["nested"] = {"value": 2}
        with self.assertRaises(TypeError):
            percept.dashboard_state["nested"]["value"] = 3

        source["nested"]["value"] = 99
        self.assertEqual(percept.to_dict()["dashboard_state"], {"nested": {"value": 1}})

    def test_deterministic_output(self):
        kwargs = {
            "user_message": "calculate margin",
            "business_memory_reference": {"store": "demo"},
            "uploaded_images": ["receipt.jpeg"],
            "timestamp": "2026-07-02T00:00:00+00:00",
        }

        self.assertEqual(build_percept(**kwargs).to_dict(), build_percept(**kwargs).to_dict())

    def test_diagnostics_only_guarantees(self):
        diagnostics = build_percept(user_message="price?").to_dict()["diagnostics"]

        self.assertEqual(diagnostics, PERCEPTION_DIAGNOSTICS)
        self.assertTrue(diagnostics["perception_created"])
        self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")
        self.assertFalse(diagnostics["routing_changed"])
        self.assertFalse(diagnostics["planner_changed"])
        self.assertFalse(diagnostics["workflow_changed"])
        self.assertFalse(diagnostics["responses_changed"])
        self.assertFalse(diagnostics["commit_boundary_changed"])
        self.assertFalse(diagnostics["memory_changed"])
        self.assertFalse(diagnostics["execution_changed"])

    def test_no_workflow_ownership(self):
        payload = build_percept(user_message="start workflow").to_dict()

        self.assertNotIn("workflow_owner", payload)
        self.assertNotIn("workflow_action", payload)
        self.assertNotIn("workflow_decision", payload)
        self.assertFalse(payload["diagnostics"]["workflow_changed"])

    def test_no_planner_ownership(self):
        payload = build_percept(user_message="make a plan").to_dict()

        self.assertNotIn("planner_owner", payload)
        self.assertNotIn("planner_output", payload)
        self.assertNotIn("plan", payload)
        self.assertFalse(payload["diagnostics"]["planner_changed"])

    def test_no_response_ownership(self):
        payload = build_percept(user_message="reply to customer").to_dict()

        self.assertNotIn("response", payload)
        self.assertNotIn("response_text", payload)
        self.assertNotIn("response_envelope", payload)
        self.assertFalse(payload["diagnostics"]["responses_changed"])

    def test_no_commit_ownership(self):
        payload = build_percept(user_message="save this").to_dict()

        self.assertNotIn("commit", payload)
        self.assertNotIn("memory_write", payload)
        self.assertNotIn("write_proposals", payload)
        self.assertFalse(payload["diagnostics"]["commit_boundary_changed"])
        self.assertFalse(payload["diagnostics"]["memory_changed"])

    def test_empty_input_handling(self):
        payload = build_percept().to_dict()

        self.assertTrue(payload["percept_id"].startswith("percept_"))
        self.assertEqual(payload["user_message"], "")
        self.assertEqual(payload["detected_signal_types"], [])
        self.assertEqual(payload["signal_sources"], [])
        self.assertEqual(payload["signal_count"], 0)
        self.assertEqual(payload["runtime_mode"], "diagnostics_only")

    def test_multiple_signal_sources(self):
        percept = build_percept(
            user_message="price question",
            conversation_history_reference={"turns": 2},
            business_memory_reference={"store_id": "demo"},
            store_profile_reference={"profile_id": "store"},
            uploaded_documents=["menu.pdf"],
            uploaded_images=["receipt.jpeg"],
            dashboard_state={"active_tab": "dashboard"},
            active_workspace="pricing",
            current_context={"locale": "th-TH"},
        )

        self.assertEqual(percept.signal_count, 9)
        self.assertEqual(
            percept.signal_sources,
            (
                "user_message",
                "conversation_history_reference",
                "business_memory_reference",
                "store_profile_reference",
                "uploaded_documents",
                "uploaded_images",
                "dashboard_state",
                "active_workspace",
                "current_context",
            ),
        )

    def test_build_percept_does_not_mutate_inputs(self):
        source = {
            "conversation_history_reference": {"turns": [{"message": "hello"}]},
            "uploaded_documents": [{"name": "doc.pdf"}],
            "dashboard_state": {"tab": "chat"},
        }
        original = copy.deepcopy(source)

        build_percept(**source)

        self.assertEqual(source, original)

    def test_perception_engine_has_no_runtime_ownership_imports(self):
        source = Path("brain/perception_engine.py").read_text(encoding="utf-8")
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
