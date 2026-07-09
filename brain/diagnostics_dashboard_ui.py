from __future__ import annotations

from copy import deepcopy
from typing import Any

import streamlit as st


_SNAPSHOT_STATE_KEYS = (
    "brain_diagnostics_snapshot",
    "brain_diagnostics_dashboard_snapshot",
    "last_brain_diagnostics_snapshot",
)

_DIAGNOSTIC_STATE_KEYS = (
    ("response_authority", "last_response_authority_diagnostics"),
    ("evidence_gap", "last_evidence_gap_diagnostics"),
    ("business_situation", "last_business_situation_diagnostics"),
)


def _as_dict(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return deepcopy(value) if isinstance(value, list) else []


def _state_get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    try:
        return state.get(key, default)
    except Exception:
        return default


def _resolve_snapshot(snapshot: dict | None, diagnostics_state: dict | None) -> dict | None:
    if snapshot is not None:
        return deepcopy(snapshot) if isinstance(snapshot, dict) else snapshot

    state = diagnostics_state if diagnostics_state is not None else st.session_state
    for key in _SNAPSHOT_STATE_KEYS:
        candidate = _state_get(state, key)
        if isinstance(candidate, dict) and candidate:
            return deepcopy(candidate)
        if candidate not in (None, {}, []):
            return candidate
    return None


def _snapshot_with_state_diagnostics(snapshot: dict, diagnostics_state: dict | None) -> dict:
    result = deepcopy(snapshot)
    if diagnostics_state is None:
        diagnostics_state = st.session_state
    shadow = result.setdefault("shadow_diagnostics", {})
    if not isinstance(shadow, dict):
        result["shadow_diagnostics"] = {}
        shadow = result["shadow_diagnostics"]
    for section, state_key in _DIAGNOSTIC_STATE_KEYS:
        if shadow.get(section):
            continue
        diagnostics = _state_get(diagnostics_state, state_key)
        if isinstance(diagnostics, dict) and diagnostics:
            shadow[section] = deepcopy(diagnostics)
    return result


def _progress_value(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, int(value)))
    return 0


def _metric_text(value: Any, fallback: str = "unknown") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _json_view(value: Any) -> None:
    try:
        st.json(value)
    except Exception as json_error:
        try:
            st.warning(f"Unable to render JSON view: {type(json_error).__name__}")
            st.json({"raw_snapshot_repr": repr(value)})
        except Exception:
            st.warning("Unable to render raw diagnostics snapshot.")


def _shadow_mode_text(value: Any) -> str:
    if value is True:
        return "shadow"
    if value is False:
        return "not shadow"
    return "unknown"


def _render_layer_progress(snapshot: dict) -> None:
    with st.container(border=True):
        st.subheader("Brain Layer Progress")
        rows = _as_list(snapshot.get("layer_progress"))
        if not rows:
            st.caption("No layer progress rows recorded.")
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            st.caption(_metric_text(row.get("layer_name"), "Unnamed layer"))
            st.progress(_progress_value(row.get("readiness_score")))
            cols = st.columns(4)
            cols[0].metric("Readiness", f"{_progress_value(row.get('readiness_score'))}%")
            cols[1].metric("Gate", _metric_text(row.get("active_gate_status")))
            cols[2].metric("Risk", _metric_text(row.get("risk_level")))
            cols[3].metric("Audit", _metric_text(row.get("audit_status")))


def _render_shadow_map(snapshot: dict) -> None:
    with st.container(border=True):
        st.subheader("Shadow Mode Map")
        layer_map = _as_dict(snapshot.get("active_vs_shadow_layer_map"))
        if not layer_map:
            st.caption("No active/shadow map recorded.")
            return
        cols = st.columns(3)
        for index, (name, status) in enumerate(layer_map.items()):
            status = _as_dict(status)
            cols[index % 3].metric(name, _metric_text(status.get("mode")), _metric_text(status.get("active_gate_status")))


def _render_current_turn_trace(snapshot: dict) -> None:
    with st.container(border=True):
        st.subheader("Current Turn Trace")
        trace = _as_dict(snapshot.get("current_turn_trace"))
        if not trace:
            st.caption("No current turn trace recorded.")
            return
        cols = st.columns(3)
        cols[0].metric("Route", _metric_text(trace.get("final_response_route")))
        cols[1].metric("Response Mode", _metric_text(trace.get("response_mode")))
        cols[2].metric("Reset Boundary", _metric_text(trace.get("reset_boundary_status")))
        with st.expander("Trace details", expanded=False):
            _json_view(trace)


def _render_diagnostic_section(snapshot: dict, title: str, section_key: str, shadow_key: str) -> None:
    with st.container(border=True):
        st.subheader(title)
        diagnostics = _as_dict(_as_dict(snapshot.get("shadow_diagnostics")).get(section_key))
        if not diagnostics:
            st.caption(f"No {title} diagnostics recorded.")
            return
        cols = st.columns(3)
        cols[0].metric("Shadow Mode", _shadow_mode_text(diagnostics.get(shadow_key)))
        cols[1].metric("Type", _metric_text(diagnostics.get(f"{section_key}_type") or diagnostics.get("business_situation_type")))
        cols[2].metric("Confidence", _metric_text(diagnostics.get(f"{section_key}_confidence") or diagnostics.get("business_situation_confidence")))
        with st.expander(f"{title} raw diagnostics", expanded=False):
            _json_view(diagnostics)


def _render_flags_and_safety(snapshot: dict) -> None:
    with st.container(border=True):
        st.subheader("Mismatch Flags")
        flags = _as_list(snapshot.get("mismatch_flags"))
        if flags:
            st.warning(", ".join(str(flag) for flag in flags))
        else:
            st.info("No mismatch flags recorded.")

    with st.container(border=True):
        st.subheader("Test / Regression Safety")
        health = _as_dict(snapshot.get("test_health"))
        regression = _as_dict(snapshot.get("regression_safety_status"))
        cols = st.columns(3)
        cols[0].metric("Full Suite", _metric_text(health.get("last_full_suite_result")))
        cols[1].metric("Suite Count", _metric_text(health.get("last_full_suite_count")))
        cols[2].metric("Diff Check", _metric_text(health.get("last_diff_check_result")))
        with st.expander("Regression safety details", expanded=False):
            _json_view({"test_health": health, "regression_safety_status": regression})


def _render_protected_and_next(snapshot: dict) -> None:
    with st.container(border=True):
        st.subheader("Protected Dirty Files")
        protected = _as_list(snapshot.get("protected_dirty_files"))
        if not protected:
            protected = _as_list(_as_dict(snapshot.get("test_health")).get("protected_dirty_files"))
        if protected:
            _json_view(protected)
        else:
            st.caption("No protected dirty files recorded in snapshot.")

    with st.container(border=True):
        st.subheader("Next Recommended Step")
        next_step = _as_dict(snapshot.get("next_recommended_step"))
        recommendation = next_step.get("recommendation")
        if recommendation:
            st.info(str(recommendation))
        else:
            st.caption("No recommendation recorded.")
        notes = _as_list(next_step.get("notes"))
        if notes:
            _json_view({"notes": notes})


def render_brain_diagnostics_dashboard(
    snapshot: dict | None = None,
    diagnostics_state: dict | None = None,
) -> None:
    """Render the read-only SME Brain Diagnostics Dashboard prototype.

    The renderer only reads supplied data or Streamlit session state. It does
    not mutate runtime state, activate gates, call an LLM, or influence final
    response behavior.
    """
    st.subheader("SME Brain Diagnostics")
    st.caption("Developer/Admin read-only diagnostics")

    resolved = _resolve_snapshot(snapshot, diagnostics_state)
    if resolved is None:
        st.info("No brain diagnostics snapshot recorded yet. Send a message to generate diagnostics.")
        return
    if not isinstance(resolved, dict):
        st.warning("Brain diagnostics snapshot is malformed. Raw snapshot is shown for debugging.")
        with st.expander("Raw Snapshot", expanded=False):
            _json_view(resolved)
        return

    try:
        dashboard_snapshot = _snapshot_with_state_diagnostics(resolved, diagnostics_state)
        if not dashboard_snapshot:
            st.info("No brain diagnostics snapshot recorded yet. Send a message to generate diagnostics.")
            return
        _render_layer_progress(dashboard_snapshot)
        _render_shadow_map(dashboard_snapshot)
        _render_current_turn_trace(dashboard_snapshot)
        _render_diagnostic_section(
            dashboard_snapshot,
            "Response Authority",
            "response_authority",
            "response_authority_shadow_mode",
        )
        _render_diagnostic_section(
            dashboard_snapshot,
            "Evidence Gap",
            "evidence_gap",
            "evidence_gap_shadow_mode",
        )
        _render_diagnostic_section(
            dashboard_snapshot,
            "Business Situation",
            "business_situation",
            "business_situation_shadow_mode",
        )
        _render_flags_and_safety(dashboard_snapshot)
        _render_protected_and_next(dashboard_snapshot)
        with st.expander("Raw Snapshot", expanded=False):
            _json_view(dashboard_snapshot)
    except Exception as render_error:
        st.warning(f"Brain diagnostics dashboard failed safely: {type(render_error).__name__}")
        with st.expander("Raw Snapshot", expanded=False):
            _json_view(resolved)
