import ast
import copy
import inspect
import unittest
from unittest.mock import patch

import app
import brain.diagnostics_dashboard_ui as dashboard_ui


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyStreamlit:
    def __init__(self, session_state=None, checkbox_value=False, button_value=False):
        self.session_state = session_state or {}
        self.checkbox_value = checkbox_value
        self.button_value = button_value
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

    def checkbox(self, label, value=False, key=None, help=None):
        self.calls.append(("checkbox", label, value, key, help))
        return self.checkbox_value

    def button(self, label, key=None, help=None, **kwargs):
        self.calls.append(("button", label, key, help, kwargs))
        return self.button_value

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

    def test_admin_panel_hides_dashboard_renderer_by_default(self):
        state = {"developer_mode": True}
        dummy = _DummyStreamlit(session_state=state, checkbox_value=False)

        with patch.object(app, "st", dummy), patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        render.assert_not_called()
        self.assertIn(
            ("caption", "Brain Diagnostics Dashboard hidden for performance. Enable to render."),
            dummy.calls,
        )
        self.assertTrue(
            any(
                call[0] == "checkbox"
                and call[1] == "Render SME Brain Diagnostics Dashboard"
                and call[2] is False
                for call in dummy.calls
            )
        )
        self.assertFalse(any(call[0] == "expander" for call in dummy.calls))

    def test_admin_panel_enable_alone_does_not_render_without_frozen_snapshot(self):
        state = {"developer_mode": True}
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True)

        with patch.object(app, "st", dummy), \
            patch.object(app, "build_brain_diagnostics_snapshot") as build_snapshot, \
            patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        build_snapshot.assert_not_called()
        render.assert_not_called()
        self.assertIn(
            ("expander", "SME Brain Diagnostics - developer/admin only", False),
            dummy.calls,
        )
        self.assertIn(
            ("info", "Dashboard enabled. Load a snapshot to render diagnostics."),
            dummy.calls,
        )
        self.assertTrue(
            any(
                call[0] == "button"
                and call[1] == "Load/Refresh Brain Diagnostics Snapshot"
                and call[2] == "brain_dashboard_refresh_requested"
                for call in dummy.calls
            )
        )

    def test_admin_panel_manual_refresh_builds_and_stores_frozen_snapshot(self):
        snapshot = _minimal_snapshot()
        state = {
            "developer_mode": True,
        }
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True, button_value=True)

        with patch.object(app, "st", dummy), \
            patch.object(app, "build_brain_diagnostics_snapshot", return_value=snapshot) as build_snapshot, \
            patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        build_snapshot.assert_called_once()
        self.assertEqual(state["brain_dashboard_frozen_snapshot"]["dashboard_version"], snapshot["dashboard_version"])
        self.assertIsNot(state["brain_dashboard_frozen_snapshot"], snapshot)
        self.assertIsNotNone(state["brain_dashboard_frozen_at"])
        self.assertTrue(state["brain_dashboard_frozen_snapshot"]["diagnostics"]["brain_diagnostics_snapshot_manual_refresh"])
        render.assert_called_once_with(
            snapshot=state["brain_dashboard_frozen_snapshot"],
            diagnostics_state={},
        )

    def test_admin_panel_manual_refresh_ignores_existing_snapshot_fallbacks(self):
        snapshot = _minimal_snapshot()
        old_snapshot = _minimal_snapshot()
        old_snapshot["dashboard_version"] = "old"
        state = {
            "developer_mode": True,
            "last_brain_diagnostics_snapshot": old_snapshot,
            "brain_diagnostics_dashboard_snapshot": old_snapshot,
        }
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True, button_value=True)

        with patch.object(app, "st", dummy), \
            patch.object(app, "build_brain_diagnostics_snapshot", return_value=snapshot) as build_snapshot, \
            patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        build_snapshot.assert_called_once()
        self.assertEqual(state["brain_dashboard_frozen_snapshot"]["dashboard_version"], snapshot["dashboard_version"])
        self.assertEqual(state["last_brain_diagnostics_snapshot"], old_snapshot)
        self.assertEqual(state["brain_diagnostics_dashboard_snapshot"], old_snapshot)
        render.assert_called_once_with(
            snapshot=state["brain_dashboard_frozen_snapshot"],
            diagnostics_state={},
        )

    def test_admin_panel_renders_only_from_existing_frozen_snapshot(self):
        live_snapshot = _minimal_snapshot()
        frozen_snapshot = _minimal_snapshot()
        frozen_snapshot["dashboard_version"] = "frozen"
        state = {
            "developer_mode": True,
            "brain_diagnostics_snapshot": live_snapshot,
            "brain_dashboard_frozen_snapshot": frozen_snapshot,
            "brain_dashboard_frozen_at": "2026-07-09T00:00:00+00:00",
        }
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True, button_value=False)

        with patch.object(app, "st", dummy), patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        render.assert_called_once_with(snapshot=frozen_snapshot, diagnostics_state={})

    def test_admin_panel_refresh_does_not_mutate_original_diagnostics_state(self):
        snapshot = _minimal_snapshot()
        state = {
            "developer_mode": True,
            "brain_diagnostics_snapshot": snapshot,
            "last_task_route": {"workflow": "unchanged"},
            "planner_output": {"decision": "unchanged"},
            "last_generated_response": "unchanged response",
        }
        before_snapshot = copy.deepcopy(snapshot)
        before_runtime_state = {
            "last_task_route": copy.deepcopy(state["last_task_route"]),
            "planner_output": copy.deepcopy(state["planner_output"]),
            "last_generated_response": state["last_generated_response"],
        }
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True, button_value=True)

        with patch.object(app, "st", dummy), patch.object(app, "_render_brain_dashboard_admin_ui"):
            app._show_brain_dashboard_admin_panel()

        state["brain_dashboard_frozen_snapshot"]["dashboard_version"] = "changed in ui copy"
        self.assertEqual(snapshot, before_snapshot)
        self.assertEqual(
            {
                "last_task_route": state["last_task_route"],
                "planner_output": state["planner_output"],
                "last_generated_response": state["last_generated_response"],
            },
            before_runtime_state,
        )

    def test_admin_panel_manual_refresh_fail_closed_when_build_fails(self):
        state = {
            "developer_mode": True,
            "brain_dashboard_frozen_snapshot": _minimal_snapshot(),
            "brain_dashboard_frozen_at": "2026-07-09T00:00:00+00:00",
        }
        dummy = _DummyStreamlit(session_state=state, checkbox_value=True, button_value=True)

        with patch.object(app, "st", dummy), \
            patch.object(app, "build_brain_diagnostics_snapshot", side_effect=RuntimeError("boom")), \
            patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()

        self.assertIsNone(state["brain_dashboard_frozen_snapshot"])
        self.assertIsNone(state["brain_dashboard_frozen_at"])
        render.assert_not_called()
        self.assertIn(("info", "Dashboard enabled. Load a snapshot to render diagnostics."), dummy.calls)

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
