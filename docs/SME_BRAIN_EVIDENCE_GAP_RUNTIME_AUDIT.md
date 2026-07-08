# SME Companion V5.12.4 Evidence Gap Runtime Audit

V5.12.4 audits Evidence Gap runtime wiring as diagnostics only.

Evidence Gap remains shadow mode only. Its profile is recorded for developer diagnostics and response audit visibility, but it does not select final response text, force clarification, continue workflows, alter reset behavior, or override the commit boundary.

## Audited Runtime Paths

The shadow diagnostic writer is exercised across these paths:

- reset boundary handling;
- active workflow or locked workflow handling;
- normal planner or assistant turn handling;
- fail-closed handling when evidence-gap evaluation raises an exception;
- response audit/debug-state visibility.

When diagnostics are available, each path must expose these stable keys:

```text
evidence_gap_profile
evidence_gap_detected
evidence_gap_type
evidence_missing_fields
evidence_conflicting_fields
evidence_smallest_next_question
evidence_sufficient
evidence_can_answer_with_assumptions
evidence_gap_reason
evidence_gap_confidence
evidence_gap_shadow_mode
```

The fail-closed path records `USER_CONFIRMATION_GAP`, `evidence_sufficient=false`, and `reason=evidence_gap_shadow_error` as diagnostics. That fallback is intentionally non-authoritative and does not force the final response pipeline to ask a question or use the gap type as response text.

## Non-Authority Invariants

- `evidence_gap_type` is not used to choose final response text.
- `evidence_sufficient` is not used to force clarification.
- `evidence_smallest_next_question` is not appended to direct or workflow responses.
- Evidence Gap diagnostics do not override Response Authority diagnostics.
- Response Authority remains shadow mode only.
- reset acknowledgement behavior remains owned by the reset path.
- active workflow continuation remains owned by Conversation OS and workflow handlers.
- direct semantic and direct analytical responses remain owned by existing response builders.
- commit boundary output remains independent from Evidence Gap diagnostics.

Coverage lives in `tests/test_v5124_evidence_gap_runtime_audit.py`.
