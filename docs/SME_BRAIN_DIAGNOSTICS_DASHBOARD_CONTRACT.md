# SME Companion V5.14.0 SME Brain Diagnostics Dashboard Contract

V5.14.0 defines the SME Brain Diagnostics Dashboard contract as documentation only.

This document does not introduce runtime code, app changes, Streamlit UI, dashboard components, workflow behavior, router behavior, planner behavior, response generation behavior, prompts, tests, active gates, or business vertical implementation.

The dashboard is a future developer/admin diagnostic surface for inspecting SME Brain health, layer progress, shadow diagnostics, regression safety, and next recommended architecture actions.

Response Authority, Evidence Gap, and Business Situation remain shadow mode only. Their diagnostics are observable for development and audit, but this contract must not activate them as behavior gates.

## 1. Purpose

The SME Brain Diagnostics Dashboard should provide a developer/admin view of SME Brain health.

Its purpose is to:

- make shadow diagnostics visible and interpretable;
- help identify which brain layer made which diagnostic decision;
- help decide when a layer is ready for limited active gating;
- help detect regressions, stale context reuse, over-questioning, or wrong response modes;
- support architecture development before business vertical expansion.

The dashboard answers:

> What does the SME Brain currently believe happened inside the runtime, and which layer needs attention next?

It does not answer:

> What should the customer-facing final response say?

## 2. Non-goals

The SME Brain Diagnostics Dashboard is not:

- a customer-facing business dashboard;
- a sales, inventory, accounting, marketing, or operations dashboard;
- an active response controller;
- a replacement for tests;
- an LLM monitoring product;
- a source of final response behavior;
- a business vertical or use-case implementation.

The dashboard is not allowed to change final response behavior.

## 3. Position in Architecture

The dashboard sits outside the response path.

Suggested position:

```text
Shadow brain layers
    -> runtime diagnostics
    -> diagnostics snapshot
    -> SME Brain Diagnostics Dashboard
```

Runtime diagnostics are produced by shadow brain layers. The diagnostics dashboard reads those diagnostics.

The dashboard must be read-only. It must not write to workflow state, business memory, routing, planner state, response generation, commit boundary state, durable business records, or external systems.

The dashboard is an observability surface, not a runtime authority.

## 4. Diagnostic Sources

Current shadow diagnostic sources:

- Response Authority;
- Evidence Gap;
- Business Situation.

Future diagnostic sources may include:

- Truth Status;
- Perspective confidence;
- Skill matching;
- Business Knowledge;
- Workflow health;
- Memory quality;
- Commit boundary audit;
- Regression test status.

All sources must remain independently owned by their runtime layer. The dashboard may aggregate and display diagnostics, but it must not reinterpret them as authoritative behavior.

## 5. Core Dashboard Sections

The future dashboard should support these sections:

- Brain Layer Progress;
- Shadow Mode Diagnostics;
- Current Turn Trace;
- Response Mode Audit;
- Evidence Sufficiency Audit;
- Business Situation Audit;
- Regression Safety Status;
- Test Health;
- Protected Dirty Files Status;
- Active vs Shadow Layer Map;
- Next Recommended Architecture Step.

Sections may be implemented incrementally. V5.14.0 defines the contract only.

## 6. Brain Layer Progress Model

Each brain layer progress row should use this model:

```yaml
layer_name: "Response Authority"
version: "5.11.x"
contract_status: "complete"
helper_status: "complete"
shadow_wiring_status: "complete"
acceptance_status: "complete"
audit_status: "complete"
active_gate_status: "shadow_only"
test_count: 0
last_commit: null
risk_level: "low | medium | high"
notes: []
```

Field meanings:

- `layer_name`: human-readable layer name.
- `version`: layer or contract version.
- `contract_status`: documentation/contract readiness.
- `helper_status`: pure helper implementation readiness.
- `shadow_wiring_status`: passive runtime diagnostics wiring readiness.
- `acceptance_status`: acceptance guard readiness.
- `audit_status`: runtime audit readiness.
- `active_gate_status`: whether the layer is inactive, shadow only, candidate, limited active, or active.
- `test_count`: known test count for the layer or layer family.
- `last_commit`: last known commit reference when available.
- `risk_level`: current development or activation risk.
- `notes`: short developer notes.

## 7. Shadow Mode Diagnostics Model

The dashboard must support stable keys from current shadow layers.

Response Authority keys:

- `response_authority_decision`
- `response_authority_mode`
- `response_authority_reason`
- `response_authority_workflow_allowed`
- `response_authority_shadow_mode`

Evidence Gap keys:

- `evidence_gap_profile`
- `evidence_gap_detected`
- `evidence_gap_type`
- `evidence_missing_fields`
- `evidence_conflicting_fields`
- `evidence_smallest_next_question`
- `evidence_sufficient`
- `evidence_can_answer_with_assumptions`
- `evidence_gap_reason`
- `evidence_gap_confidence`
- `evidence_gap_shadow_mode`

Business Situation keys:

- `business_situation_profile`
- `business_situation_detected`
- `business_situation_type`
- `business_domain`
- `perspective_stance`
- `business_risk_level`
- `business_opportunity_level`
- `business_urgency_level`
- `owner_attention`
- `recommended_response_posture`
- `business_reasoning_summary`
- `business_situation_confidence`
- `business_situation_shadow_mode`

Diagnostics should be displayed as shadow observations. They must not be presented as proof that final runtime behavior used those values.

## 8. Current Turn Trace

The dashboard should provide a read-only current turn trace.

Expected trace fields:

```yaml
user_message_summary: ""
detected_intent: null
semantic_type: null
evidence_gap_result: {}
business_situation_result: {}
response_authority_result: {}
workflow_state_summary: {}
reset_boundary_status: "none | active | respected | violated | unknown"
final_response_route: "direct | workflow | reset | planner | llm | unknown"
commit_boundary_status: "not_applicable | passed | failed | unknown"
mismatch_flags: []
```

The trace should summarize user messages where possible rather than storing or exposing full private customer text unnecessarily.

The trace is an audit view only. It must not change workflow state, reset handling, final response routing, or commit boundary behavior.

## 9. Mismatch Flags

Mismatch flags identify possible differences between shadow diagnostics and observed runtime behavior.

Example flags:

- `authority_direct_but_workflow_started`
- `evidence_sufficient_but_clarification_asked`
- `evidence_gap_but_direct_answer_given`
- `business_situation_detected_but_generic_response`
- `stale_context_reused_after_reset`
- `completed_workflow_forced_continuation`
- `diagnostics_missing`
- `shadow_layer_error`
- `active_gate_violation`

Mismatch flags are diagnostic leads. They are not automatic failures unless an acceptance guard or active gate contract explicitly makes them failures.

## 10. Regression Safety Status

The dashboard should track whether core guards still pass.

Core guard areas:

- deterministic cost workflow completion boundary;
- completed workflow reset isolation;
- analytical cost semantic direct response;
- semantic correction direct response;
- shadow diagnostics non-authoritative;
- fail-closed diagnostics;
- commit boundary output shape.

Regression safety status should distinguish:

- passing;
- failing;
- not run;
- unknown;
- blocked by environment.

The dashboard may display guard status, but tests and acceptance guards remain the source of verification.

## 11. Test Health

The Test Health section should use these fields:

```yaml
total_tests: null
targeted_response_authority_tests: null
targeted_evidence_gap_tests: null
targeted_business_situation_tests: null
last_full_suite_result: "unknown"
last_full_suite_count: null
last_diff_check_result: "unknown"
known_warnings: []
protected_dirty_files: []
```

Field meanings:

- `total_tests`: total known tests in the repository or current suite.
- `targeted_response_authority_tests`: targeted tests for Response Authority.
- `targeted_evidence_gap_tests`: targeted tests for Evidence Gap.
- `targeted_business_situation_tests`: targeted tests for Business Situation.
- `last_full_suite_result`: latest full suite result when known.
- `last_full_suite_count`: latest full suite count when known.
- `last_diff_check_result`: latest `git diff --check` result when known.
- `known_warnings`: warnings that do not currently fail the suite.
- `protected_dirty_files`: files known to be dirty and protected from edits.

For the V5.13 baseline, the latest reported full suite was 696 tests passing after V5.13.4. Future dashboard snapshots should record the exact suite result from their own run instead of assuming this baseline remains current.

## 12. Layer Readiness Scoring

The dashboard should use a simple readiness model:

- `0%`: contract missing;
- `20%`: contract complete;
- `40%`: pure helper and unit tests complete;
- `60%`: shadow runtime wiring complete;
- `80%`: acceptance guards complete;
- `100%`: runtime audit complete.

Active gate status is tracked separately. A layer can be 100% ready in the shadow lifecycle and still remain shadow only.

## 13. Active Gate Policy

The dashboard may recommend active gating candidates, but it must not activate them.

Active gating should require:

- contract complete;
- helper complete;
- shadow diagnostics stable;
- acceptance guards pass;
- runtime audit complete;
- mismatch rate acceptable;
- explicit human approval;
- rollback plan.

Limited active gating should be narrow, reversible, and covered by acceptance guards before it changes user-visible behavior.

## 14. UX Principles

The dashboard is developer/admin only.

UX principles:

- show clear layer status;
- prefer simple cards and charts;
- show only useful diagnostics by default;
- allow drill-down into raw diagnostics;
- avoid exposing confusing internal reasoning to normal SME users;
- keep customer chat simple and AI-first.

The dashboard should help developers find runtime risks quickly. It should not become a second product surface for business owners before the underlying observability model is stable.

## 15. Data Safety and Boundaries

The dashboard is read-only.

Safety boundaries:

- do not store private customer data unnecessarily;
- summarize user messages where possible;
- do not expose internal diagnostics in normal user chat;
- do not let dashboard actions mutate production state;
- do not write business memory from dashboard observations;
- do not treat raw diagnostics as user-facing explanations.

If a future implementation persists dashboard snapshots, it must define a retention and redaction policy before storing customer-sensitive content.

## 16. Failure Modes

Known failure modes this contract is intended to prevent:

- dashboard becomes source of truth instead of runtime;
- dashboard metrics are stale;
- dashboard encourages premature active gating;
- too much raw diagnostic noise;
- confusing developer diagnostics with user-facing explanation;
- misreading shadow diagnostics as actual behavior;
- accidentally leaking internal diagnostics to customers;
- using dashboard recommendations to bypass tests or audits;
- turning mismatch flags into behavior changes without a gate contract.

## 17. Roadmap

### V5.14.0

Dashboard contract documentation.

### V5.14.1

Dashboard data model / pure snapshot helper and tests.

### V5.14.2

Shadow diagnostics snapshot wiring.

### V5.14.3

Dashboard acceptance guards.

### V5.14.4

Optional Streamlit/admin UI prototype.

### V5.14.5

Runtime audit.
