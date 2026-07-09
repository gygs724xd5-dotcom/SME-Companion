import ast
import copy
import inspect
import unittest
from unittest.mock import patch

import brain.diagnostics_dashboard_ui as dashboard_ui


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyStreamlit:
    def __init__(self):
        self.session_state = {}
        self.calls = []

    def subheader(self, value):
        self.calls.append(("subheader", value))

    def caption(self, value):
        self.calls.append(("caption", value))

    def container(self, border=False):
        self.calls.append(("container", border))
        return _Context()

    def columns(self, count):
        self.calls.append(("columns", count))
        return [self for _ in range(count)]

    def metric(self, label, value, delta=None):
        self.calls.append(("metric", label, value, delta))

    def progress(self, value):
        self.calls.append(("progress", value))

    def expander(self, label, expanded=False):
        self.calls.append(("expander", label, expanded))
        return _Context()

    def json(self, value):
        self.calls.append(("json", copy.deepcopy(value)))

    def info(self, value):
        self.calls.append(("info", value))

    def warning(self, value):
        self.calls.append(("warning", value))


def _minimal_snapshot():
    return {
        "dashboard_version": "5.14.4",
        "layer_progress": [
            {
                "layer_name": "Response Authority",
                "readiness_score": 80,
                "active_gate_status": "shadow_only",
                "risk_level": "medium",
                "audit_status": "missing",
            }
        ],
        "shadow_diagnostics": {
            "response_authority": {
                "response_authority_mode": "DIRECT_BUSINESS_ANALYSIS",
                "response_authority_shadow_mode": True,
            },
            "evidence_gap": {"evidence_gap_type": "NO_GAP", "evidence_gap_shadow_mode": True},
            "business_situation": {
                "business_situation_type": "COST_CHANGE",
                "business_situation_shadow_mode": True,
            },
        },
        "current_turn_trace": {"final_response_route": "direct"},
        "test_health": {"last_full_suite_result": "unknown"},
        "protected_dirty_files": ["data/business_memory.json"],
        "active_vs_shadow_layer_map": {
            "Response Authority": {
                "mode": "shadow",
                "active_gate_status": "shadow_only",
                "readiness_score": 80,
            }
        },
        "mismatch_flags": [],
        "next_recommended_step": {"recommendation": "Keep dashboard read-only."},
        "diagnostics": {
            "runtime_mutation": False,
            "llm_called": False,
            "active_gate_changed": False,
            "response_behavior_changed": False,
        },
    }


class V5144DiagnosticsDashboardUITest(unittest.TestCase):
    def _render_with_dummy(self, *args, **kwargs):
        dummy = _DummyStreamlit()
        with patch.object(dashboard_ui, "st", dummy):
            dashboard_ui.render_brain_diagnostics_dashboard(*args, **kwargs)
        return dummy

    def test_dashboard_renderer_exists_and_can_be_imported(self):
        self.assertTrue(callable(dashboard_ui.render_brain_diagnostics_dashboard))

    def test_renderer_handles_none_snapshot_without_crashing(self):
        dummy = self._render_with_dummy(None, diagnostics_state={})

        self.assertIn(
            ("info", "No brain diagnostics snapshot recorded yet. Send a message to generate diagnostics."),
            dummy.calls,
        )

    def test_renderer_handles_minimal_snapshot_without_crashing_or_mutating_input(self):
        snapshot = _minimal_snapshot()
        before = copy.deepcopy(snapshot)

        dummy = self._render_with_dummy(snapshot, diagnostics_state={})

        self.assertEqual(snapshot, before)
        self.assertIn(("subheader", "SME Brain Diagnostics"), dummy.calls)
        self.assertTrue(any(call[0] == "json" for call in dummy.calls))

    def test_renderer_does_not_render_large_raw_snapshot_by_default(self):
        snapshot = _minimal_snapshot()
        snapshot["diagnostics"]["large_raw_payload"] = "x" * 5000
        snapshot["current_turn_trace"]["events"] = [
            {"event": index, "payload": "y" * 1000}
            for index in range(50)
        ]

        dummy = self._render_with_dummy(snapshot, diagnostics_state={})
        rendered_json = [call[1] for call in dummy.calls if call[0] == "json"]

        self.assertTrue(rendered_json)
        self.assertNotIn("x" * 5000, str(rendered_json))
        self.assertIn("truncated", str(rendered_json))
        self.assertTrue(
            any(
                call[0] == "caption"
                and "Full raw diagnostics are skipped by default" in call[1]
                for call in dummy.calls
            )
        )

    def test_renderer_can_opt_in_to_full_raw_snapshot_for_admin_debugging(self):
        snapshot = _minimal_snapshot()
        snapshot["diagnostics"]["large_raw_payload"] = "x" * 5000

        dummy = self._render_with_dummy(
            snapshot,
            diagnostics_state={},
            render_full_raw_snapshot=True,
        )
        rendered_json = [call[1] for call in dummy.calls if call[0] == "json"]

        self.assertTrue(any("x" * 5000 in str(value) for value in rendered_json))

    def test_renderer_handles_malformed_snapshot_defensively(self):
        dummy = self._render_with_dummy(["bad", "shape"], diagnostics_state={})

        self.assertTrue(any(call[0] == "warning" for call in dummy.calls))
        self.assertTrue(any(call[0] == "expander" and call[1] == "Raw Snapshot" for call in dummy.calls))

    def test_renderer_reads_existing_snapshot_state_keys(self):
        snapshot = _minimal_snapshot()

        dummy = self._render_with_dummy(diagnostics_state={"brain_diagnostics_dashboard_snapshot": snapshot})

        self.assertIn(("subheader", "Brain Layer Progress"), dummy.calls)

    def test_renderer_is_read_only_by_design_where_static_analysis_can_verify(self):
        source = inspect.getsource(dashboard_ui.render_brain_diagnostics_dashboard)
        tree = ast.parse(source)
        streamlit_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "st":
                streamlit_calls.append(node.func.attr)

        self.assertNotIn("button", streamlit_calls)
        self.assertNotIn("checkbox", streamlit_calls)
        self.assertNotIn("toggle", streamlit_calls)
        self.assertNotIn("text_input", streamlit_calls)

    def test_no_active_gate_mutation_helper_is_introduced(self):
        public_names = [name for name in dir(dashboard_ui) if not name.startswith("_")]
        mutation_names = [name for name in public_names if "gate" in name.lower() and "render" not in name.lower()]

        self.assertEqual(mutation_names, [])


if __name__ == "__main__":
    unittest.main()
