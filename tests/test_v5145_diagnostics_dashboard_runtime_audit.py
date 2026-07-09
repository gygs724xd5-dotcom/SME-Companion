import ast
import copy
import inspect
import unittest
from unittest.mock import patch

import app
import brain.diagnostics_dashboard_ui as dashboard_ui
import tests.test_v5143_diagnostics_dashboard_acceptance as v5143_acceptance
from brain.general_response_router import build_general_direct_response
from brain.response_commit_boundary import commit_response_boundary
from brain.task_router import build_task_route


ANALYTICAL_COST = "\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e08\u0e32\u0e01 30 \u0e40\u0e1b\u0e47\u0e19 40 \u0e1a\u0e32\u0e17"
COMPONENT_TOTAL = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e44\u0e02\u0e48 30 \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21\u0e40\u0e17\u0e48\u0e32\u0e44\u0e23"
EXPECTED_COMPONENT = "\u0e41\u0e1b\u0e49\u0e07 40 \u0e1a\u0e32\u0e17 + \u0e44\u0e02\u0e48 30 \u0e1a\u0e32\u0e17 + \u0e19\u0e49\u0e33\u0e15\u0e32\u0e25 20 \u0e1a\u0e32\u0e17\n\u0e15\u0e49\u0e19\u0e17\u0e38\u0e19\u0e23\u0e27\u0e21 = 90 \u0e1a\u0e32\u0e17"


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyStreamlit:
    def __init__(self, session_state=None):
        self.session_state = session_state or {}
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


def _diagnostics_state():
    return {
        "developer_mode": True,
        "conversation_reset_diagnostics": {},
        "last_response_authority_diagnostics": {
            "response_authority_mode": "DIRECT_BUSINESS_ANALYSIS",
            "response_authority_reason": "analytical_statement_detected",
            "response_authority_workflow_allowed": False,
            "response_authority_shadow_mode": True,
        },
        "last_evidence_gap_diagnostics": {
            "evidence_gap_type": "NO_GAP",
            "evidence_sufficient": True,
            "evidence_gap_shadow_mode": True,
        },
        "last_business_situation_diagnostics": {
            "business_situation_detected": True,
            "business_situation_type": "COST_CHANGE",
            "business_situation_shadow_mode": True,
        },
        "brain_diagnostics_snapshot_shadow_mode": True,
    }


def _minimal_snapshot():
    return {
        "dashboard_version": "5.14.5",
        "layer_progress": [],
        "shadow_diagnostics": {},
        "current_turn_trace": {},
        "test_health": {},
        "active_vs_shadow_layer_map": {},
        "mismatch_flags": [],
        "next_recommended_step": {},
        "diagnostics": {
            "runtime_mutation": False,
            "llm_called": False,
            "active_gate_changed": False,
            "response_behavior_changed": False,
        },
    }


def _record_snapshot(session_state=None):
    state = session_state or _diagnostics_state()
    with patch.object(app.st, "session_state", state), patch.object(app, "_update_application_section"):
        return app._record_brain_diagnostics_snapshot_shadow(
            current_turn_trace={"final_response_route": "direct"}
        )


def _commit_component_reply(route):
    return commit_response_boundary(
        session_state={"chat_history": [{"role": "user", "content": COMPONENT_TOTAL}]},
        application_state={"conversation": {"conversation_memory": route.get("conversation_memory") or {}}},
        final_reply=EXPECTED_COMPONENT,
        intent="cost_calculation",
        workflow="COST_CALCULATION",
        response_metadata={"user_message": COMPONENT_TOTAL, "response_source": "workflow_response"},
        assistant_message={"role": "assistant", "show_business_insights": False},
    )


class V5145DiagnosticsDashboardRuntimeAuditTest(unittest.TestCase):
    def _render_with_dummy(self, *args, **kwargs):
        dummy = _DummyStreamlit()
        with patch.object(dashboard_ui, "st", dummy):
            dashboard_ui.render_brain_diagnostics_dashboard(*args, **kwargs)
        return dummy

    def test_dashboard_renderer_remains_importable(self):
        self.assertTrue(callable(dashboard_ui.render_brain_diagnostics_dashboard))

    def test_dashboard_renderer_handles_missing_snapshot(self):
        dummy = self._render_with_dummy(None, diagnostics_state={})

        self.assertIn(
            ("info", "No brain diagnostics snapshot recorded yet. Send a message to generate diagnostics."),
            dummy.calls,
        )

    def test_dashboard_renderer_handles_malformed_snapshot(self):
        dummy = self._render_with_dummy(object(), diagnostics_state={})

        self.assertTrue(any(call[0] == "warning" for call in dummy.calls))
        self.assertTrue(any(call[0] == "expander" and call[1] == "Raw Snapshot" for call in dummy.calls))

    def test_snapshot_remains_shadow_and_read_only(self):
        state = _diagnostics_state()
        snapshot = _record_snapshot(state)

        self.assertTrue(state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertTrue(snapshot["diagnostics"]["brain_diagnostics_snapshot_shadow_mode"])
        self.assertFalse(snapshot["diagnostics"]["runtime_mutation"])
        self.assertFalse(snapshot["diagnostics"]["llm_called"])
        self.assertFalse(snapshot["diagnostics"]["active_gate_changed"])
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])

    def test_dashboard_ui_exposes_no_known_mutating_controls_or_gate_helpers(self):
        source = inspect.getsource(dashboard_ui)
        tree = ast.parse(source)
        banned_controls = {
            "button",
            "checkbox",
            "toggle",
            "radio",
            "selectbox",
            "multiselect",
            "text_input",
            "text_area",
            "number_input",
            "file_uploader",
            "download_button",
            "form_submit_button",
            "chat_input",
        }
        streamlit_calls = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        public_names = [name for name in dir(dashboard_ui) if not name.startswith("_")]
        active_gate_helpers = [
            name
            for name in public_names
            if any(token in name.lower() for token in ("enable_gate", "disable_gate", "activate_gate", "workflow_control"))
        ]

        self.assertFalse(banned_controls.intersection(streamlit_calls))
        self.assertEqual(active_gate_helpers, [])

    def test_dashboard_is_wired_only_through_developer_admin_diagnostics_area(self):
        source = inspect.getsource(app._show_brain_dashboard_admin_panel)
        tree = ast.parse(source)
        render_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_render_brain_dashboard_admin_ui"
        ]
        self.assertEqual(len(render_calls), 1)
        self.assertIn('if not st.session_state.get("developer_mode"):', source)
        self.assertIn("return", source)
        self.assertIn("SME Brain Diagnostics - developer/admin only", source)

        state = {"developer_mode": False}
        dummy = _DummyStreamlit(state)
        with patch.object(app, "st", dummy), patch.object(app, "_render_brain_dashboard_admin_ui") as render:
            app._show_brain_dashboard_admin_panel()
        render.assert_not_called()

    def test_dashboard_reads_existing_snapshot_and_diagnostic_keys_without_mutating_state(self):
        state = _diagnostics_state()
        state["brain_diagnostics_dashboard_snapshot"] = _minimal_snapshot()
        before = copy.deepcopy(state)

        dummy = self._render_with_dummy(diagnostics_state=state)

        self.assertIn(("subheader", "SME Brain Diagnostics"), dummy.calls)
        self.assertEqual(state, before)

    def test_dashboard_does_not_alter_response_authority_diagnostics(self):
        state = _diagnostics_state()
        before = copy.deepcopy(state["last_response_authority_diagnostics"])

        self._render_with_dummy(_minimal_snapshot(), diagnostics_state=state)

        self.assertEqual(state["last_response_authority_diagnostics"], before)

    def test_dashboard_does_not_alter_evidence_gap_diagnostics(self):
        state = _diagnostics_state()
        before = copy.deepcopy(state["last_evidence_gap_diagnostics"])

        self._render_with_dummy(_minimal_snapshot(), diagnostics_state=state)

        self.assertEqual(state["last_evidence_gap_diagnostics"], before)

    def test_dashboard_does_not_alter_business_situation_diagnostics(self):
        state = _diagnostics_state()
        before = copy.deepcopy(state["last_business_situation_diagnostics"])

        self._render_with_dummy(_minimal_snapshot(), diagnostics_state=state)

        self.assertEqual(state["last_business_situation_diagnostics"], before)

    def test_dashboard_does_not_change_commit_boundary_or_final_response_shape(self):
        route = build_task_route({}, COMPONENT_TOTAL)
        baseline_commit = _commit_component_reply(route)
        baseline_reply = build_general_direct_response(ANALYTICAL_COST)

        _record_snapshot(_diagnostics_state())

        result = _commit_component_reply(route)
        assistant_messages = [item for item in result["chat_history"] if item.get("role") == "assistant"]
        self.assertEqual(set(result.keys()), set(baseline_commit.keys()))
        self.assertEqual(assistant_messages[0]["content"], EXPECTED_COMPONENT)
        self.assertNotIn("brain_diagnostics_snapshot", assistant_messages[0]["content"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), baseline_reply)

    def test_existing_protected_behaviors_remain_covered_by_acceptance_guards(self):
        guard_names = {
            name
            for name in dir(v5143_acceptance.V5143DiagnosticsDashboardAcceptanceTest)
            if name.startswith("test_")
        }

        self.assertIn("test_completed_workflow_context_after_reset_is_not_reused_by_snapshot_state", guard_names)
        self.assertIn("test_deterministic_workflow_completion_boundary_remains_intact", guard_names)
        self.assertIn("test_commit_boundary_output_is_unchanged_by_dashboard_snapshot_diagnostics", guard_names)

    def test_snapshot_fail_closed_diagnostics_remain_stable(self):
        state = _diagnostics_state()
        expected_reply = build_general_direct_response(ANALYTICAL_COST)
        with patch.object(app, "build_brain_diagnostics_snapshot", side_effect=RuntimeError("boom")) as build_snapshot:
            snapshot = _record_snapshot(state)

        build_snapshot.assert_not_called()
        self.assertTrue(state["brain_diagnostics_snapshot_shadow_mode"])
        self.assertEqual(snapshot["mismatch_flags"], [])
        self.assertEqual(
            snapshot["diagnostics"]["brain_diagnostics_snapshot_reason"],
            "dashboard_snapshot_runtime_disabled_by_default",
        )
        self.assertFalse(snapshot["diagnostics"]["response_behavior_changed"])
        self.assertEqual(build_general_direct_response(ANALYTICAL_COST), expected_reply)


if __name__ == "__main__":
    unittest.main()
