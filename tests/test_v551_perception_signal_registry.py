import ast
import copy
import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from brain.perception_engine import PERCEPTION_DIAGNOSTICS, build_percept
from brain.perception_signal_registry import (
    get_signal_type_definition,
    get_signal_types_by_source,
    list_signal_types,
    signal_type_exists,
)
from brain.perception_signals import (
    SIGNAL_SET_VERSION,
    SIGNAL_VERSION,
    Signal,
    SignalSet,
    build_signal,
    build_signal_set,
    build_signal_set_from_percept_fields,
)


CANONICAL_SIGNAL_TYPES = {
    "user_message",
    "conversation_history",
    "business_memory_reference",
    "store_profile_reference",
    "uploaded_document",
    "uploaded_image",
    "dashboard_state",
    "active_workspace",
    "current_context",
    "execution_result",
}


class PerceptionSignalRegistryTest(unittest.TestCase):
    def test_signal_creation(self):
        signal = build_signal(
            signal_type="user_message",
            source_ref="price question",
            captured_at="2026-07-02T00:00:00+00:00",
        )

        self.assertIsInstance(signal, Signal)
        self.assertTrue(signal.signal_id.startswith("signal_"))
        self.assertEqual(signal.signal_type, "user_message")
        self.assertEqual(signal.source, "user")
        self.assertEqual(signal.modality, "text")
        self.assertEqual(signal.payload_summary, "price question")
        self.assertEqual(signal.version, SIGNAL_VERSION)
        self.assertTrue(signal.diagnostics["signal_registry_created"])
        self.assertEqual(signal.diagnostics["runtime_mode"], "diagnostics_only")

    def test_signal_set_creation(self):
        signal_set = build_signal_set(
            [
                build_signal(signal_type="user_message", source_ref="hello"),
                build_signal(signal_type="dashboard_state", source_ref={"tab": "overview"}),
            ]
        )

        self.assertIsInstance(signal_set, SignalSet)
        self.assertTrue(signal_set.signal_set_id.startswith("signal_set_"))
        self.assertEqual(signal_set.signal_count, 2)
        self.assertEqual(signal_set.signal_types, ("user_message", "dashboard_state"))
        self.assertEqual(signal_set.signal_sources, ("user", "dashboard"))
        self.assertEqual(signal_set.version, SIGNAL_SET_VERSION)
        self.assertTrue(signal_set.diagnostics["signal_set_created"])

    def test_json_serialization(self):
        payload = build_signal_set(
            [
                build_signal(signal_type="uploaded_document", source_ref={"name": "invoice.pdf"}),
                build_signal(signal_type="uploaded_image", source_ref="receipt.jpeg"),
            ]
        ).to_dict()

        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertIn("signal_set_id", payload)
        self.assertIn(SIGNAL_SET_VERSION, encoded)
        self.assertEqual(payload["signal_count"], 2)
        self.assertEqual(payload["signals"][0]["source_ref"], {"name": "invoice.pdf"})

    def test_deterministic_output(self):
        kwargs = {
            "signal_type": "store_profile_reference",
            "source_ref": {"profile_id": "store"},
            "captured_at": "2026-07-02T00:00:00+00:00",
        }

        self.assertEqual(build_signal(**kwargs).to_dict(), build_signal(**kwargs).to_dict())
        self.assertEqual(
            build_signal_set([build_signal(**kwargs)]).to_dict(),
            build_signal_set([build_signal(**kwargs)]).to_dict(),
        )

    def test_immutable_and_defensive_behavior(self):
        source = {"nested": {"value": 1}}
        signal = build_signal(signal_type="dashboard_state", source_ref=source)

        with self.assertRaises(FrozenInstanceError):
            signal.signal_type = "changed"
        with self.assertRaises(TypeError):
            signal.source_ref["nested"] = {"value": 2}
        with self.assertRaises(TypeError):
            signal.source_ref["nested"]["value"] = 3

        source["nested"]["value"] = 99
        self.assertEqual(signal.to_dict()["source_ref"], {"nested": {"value": 1}})

    def test_all_canonical_signal_types_exist(self):
        self.assertEqual(CANONICAL_SIGNAL_TYPES, set(list_signal_types()))
        for signal_type in CANONICAL_SIGNAL_TYPES:
            self.assertTrue(signal_type_exists(signal_type))
            self.assertEqual(get_signal_type_definition(signal_type)["signal_type"], signal_type)

    def test_registry_lookup_works(self):
        self.assertEqual(get_signal_types_by_source("upload"), ("uploaded_document", "uploaded_image"))
        self.assertEqual(get_signal_type_definition("dashboard_state")["source"], "dashboard")
        self.assertFalse(signal_type_exists("workflow_action"))

    def test_unknown_signal_type_safe_fallback(self):
        definition = get_signal_type_definition("not_registered")
        signal = build_signal(signal_type="not_registered", source_ref={"value": 1})

        self.assertEqual(definition["signal_type"], "unknown")
        self.assertEqual(signal.signal_type, "not_registered")
        self.assertEqual(signal.source, "unknown")
        self.assertFalse(signal.diagnostics["signal_type_registered"])
        self.assertTrue(signal.diagnostics["unknown_signal_type"])

    def test_build_signal_set_from_percept_fields(self):
        signal_set = build_signal_set_from_percept_fields(
            user_message="price?",
            business_memory_reference={"store": "demo"},
            uploaded_documents=[{"name": "menu.pdf"}],
            uploaded_images=["receipt.jpeg"],
            active_workspace="pricing",
        )

        self.assertEqual(signal_set.signal_count, 5)
        self.assertEqual(
            signal_set.signal_types,
            (
                "user_message",
                "business_memory_reference",
                "uploaded_document",
                "uploaded_image",
                "active_workspace",
            ),
        )
        self.assertTrue(signal_set.diagnostics["signal_registry_created"])
        self.assertTrue(signal_set.diagnostics["signal_set_created"])

    def test_build_percept_remains_backward_compatible(self):
        payload = build_percept(
            user_message="price?",
            conversation_history_reference={"turns": 1},
            uploaded_documents=[{"name": "menu.pdf"}],
            active_workspace="pricing",
        ).to_dict()

        self.assertIn("percept_id", payload)
        self.assertNotIn("signal_set", payload)
        self.assertIn("current_user_message", payload["detected_signal_types"])
        self.assertIn("conversation_history_reference", payload["detected_signal_types"])
        self.assertEqual(payload["diagnostics"], PERCEPTION_DIAGNOSTICS)
        self.assertTrue(payload["diagnostics"]["signal_registry_created"])
        self.assertTrue(payload["diagnostics"]["signal_set_created"])

    def test_build_percept_does_not_mutate_inputs(self):
        source = {
            "conversation_history_reference": {"turns": [{"message": "hello"}]},
            "uploaded_documents": [{"name": "doc.pdf"}],
            "dashboard_state": {"tab": "chat"},
        }
        original = copy.deepcopy(source)

        build_percept(**source)

        self.assertEqual(source, original)

    def test_no_workflow_planner_router_response_ownership(self):
        payload = build_signal(signal_type="user_message", source_ref="start workflow").to_dict()
        signal_set_payload = build_signal_set([Signal.from_dict(payload)]).to_dict()
        percept_payload = build_percept(user_message="start workflow").to_dict()

        for item in (payload, signal_set_payload, percept_payload):
            self.assertNotIn("workflow_owner", item)
            self.assertNotIn("workflow_action", item)
            self.assertNotIn("workflow_decision", item)
            self.assertNotIn("planner_owner", item)
            self.assertNotIn("planner_output", item)
            self.assertNotIn("router_decision", item)
            self.assertNotIn("route", item)
            self.assertNotIn("response", item)
            self.assertNotIn("response_text", item)

    def test_diagnostics_only_guarantees(self):
        signal_set_diagnostics = build_signal_set(
            [build_signal(signal_type="user_message", source_ref="hello")]
        ).to_dict()["diagnostics"]
        percept_diagnostics = build_percept(user_message="hello").to_dict()["diagnostics"]

        for diagnostics in (signal_set_diagnostics, percept_diagnostics):
            self.assertTrue(diagnostics["signal_registry_created"])
            self.assertTrue(diagnostics["signal_set_created"])
            self.assertEqual(diagnostics["runtime_mode"], "diagnostics_only")
            self.assertFalse(diagnostics["routing_changed"])
            self.assertFalse(diagnostics["planner_changed"])
            self.assertFalse(diagnostics["workflow_changed"])
            self.assertFalse(diagnostics["responses_changed"])
            self.assertFalse(diagnostics["memory_changed"])
            self.assertFalse(diagnostics["execution_changed"])
            self.assertFalse(diagnostics["commit_boundary_changed"])

    def test_new_perception_modules_have_no_runtime_ownership_imports(self):
        forbidden = (
            "task_router",
            "planner",
            "workflow",
            "response",
            "llm",
            "memory",
        )
        violations = []
        for path in (
            Path("brain/perception_signals.py"),
            Path("brain/perception_signal_registry.py"),
        ):
            parsed = ast.parse(path.read_text(encoding="utf-8"))
            imported_modules = []
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
                if isinstance(node, ast.ImportFrom):
                    imported_modules.append(node.module or "")
            violations.extend(
                f"{path}:{module}"
                for module in imported_modules
                if any(name in module for name in forbidden)
            )

        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
