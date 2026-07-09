# SME Companion V5.14.5 Brain Diagnostics Dashboard Runtime Audit

V5.14.5 audits the Brain Diagnostics Dashboard runtime and UI wiring. It does not activate the dashboard snapshot as a behavior gate, does not activate Response Authority, Evidence Gap, or Business Situation, and does not change final response behavior.

## Audit Result

The Brain Diagnostics Dashboard remains a developer/admin, read-only, shadow diagnostics surface.

Runtime status:

- Dashboard Snapshot: shadow/read-only only.
- Response Authority: shadow mode only.
- Evidence Gap: shadow mode only.
- Business Situation: shadow mode only.
- Final response behavior: unchanged by dashboard snapshot and UI.
- Workflow/router/planner behavior: unchanged by dashboard snapshot and UI.

## Runtime Wiring

The dashboard snapshot is recorded through `_record_brain_diagnostics_snapshot_shadow` in `app.py`.

The snapshot is stored only as diagnostics state:

- `brain_diagnostics_snapshot`
- `brain_diagnostics_dashboard_snapshot`
- `last_brain_diagnostics_snapshot`
- `brain_diagnostics_snapshot_shadow_mode`

The Streamlit prototype renderer is exposed through `_show_brain_dashboard_admin_panel` in `app.py`. That panel returns immediately unless `developer_mode` is enabled, then renders inside the `Developer diagnostics` area using the read-only renderer from `brain/diagnostics_dashboard_ui.py`.

## Read-Only Guarantees

The dashboard renderer:

- reads supplied snapshot data or Streamlit session state;
- renders metrics, captions, JSON views, warnings, and expanders;
- does not expose buttons that mutate state;
- does not expose active gate toggles;
- does not expose workflow controls;
- does not expose reset controls;
- does not edit memory;
- does not trigger response rewrites;
- does not call an LLM;
- does not write to workflow state, router/planner state, commit boundary state, business memory, or final response data.

## Diagnostic Sources

The dashboard reads existing shadow diagnostics for:

- Response Authority diagnostics;
- Evidence Gap diagnostics;
- Business Situation diagnostics.

If a snapshot is missing a shadow diagnostics section, the renderer may fill the local rendered copy from existing session diagnostic keys. That copy is not written back to session state and does not override the owning diagnostic layer.

## Failure Handling

The dashboard handles:

- missing snapshot: shows a no-snapshot diagnostic message;
- minimal snapshot: renders available sections and omits missing rows safely;
- malformed snapshot: shows a warning and raw snapshot view;
- snapshot helper failure: records fail-closed shadow diagnostics with `shadow_layer_error` and `brain_diagnostics_snapshot_shadow_error`.

Fail-closed snapshot diagnostics keep:

- `runtime_mutation: False`
- `ui_rendered: False`
- `llm_called: False`
- `active_gate_changed: False`
- `response_behavior_changed: False`

## Non-Override Boundaries

The dashboard cannot override:

- final response generation;
- workflow continuation;
- reset behavior;
- router/planner behavior;
- commit boundary behavior;
- Response Authority diagnostics;
- Evidence Gap diagnostics;
- Business Situation diagnostics.

The dashboard may display mismatch flags and recommendations, but those values are audit leads only. They are not runtime authority and do not activate gates.

## Validation Coverage

V5.14.5 adds `tests/test_v5145_diagnostics_dashboard_runtime_audit.py`.

The audit tests verify:

- renderer importability;
- missing snapshot handling;
- malformed snapshot handling;
- shadow/read-only snapshot diagnostics;
- absence of known mutating UI controls and active gate helpers;
- developer/admin-only app wiring;
- read access to existing snapshot and diagnostic keys without state mutation;
- Response Authority diagnostics are not altered;
- Evidence Gap diagnostics are not altered;
- Business Situation diagnostics are not altered;
- commit boundary and final response output shape are unchanged;
- existing protected behavior acceptance guards remain present;
- fail-closed snapshot diagnostics remain stable.
