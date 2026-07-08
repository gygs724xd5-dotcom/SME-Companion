# SME Companion V5.13.4 Business Situation Runtime Audit

V5.13.4 audits Business Situation runtime wiring as diagnostics only.

Business Situation remains shadow mode only. Its profile is recorded for developer diagnostics and response audit visibility, but it does not select final response text, force owner-advisory wording, continue workflows, alter reset behavior, override Evidence Gap, override Response Authority, or change the commit boundary.

## Audited Runtime Paths

The shadow diagnostic writer is exercised across these paths:

- reset boundary handling;
- active workflow or locked workflow handling;
- normal planner or assistant turn handling;
- fail-closed handling when business-situation evaluation raises an exception;
- response audit/debug-state visibility.

When diagnostics are available, each path must expose these stable keys:

```text
business_situation_profile
business_situation_detected
business_situation_type
business_domain
perspective_stance
business_risk_level
business_opportunity_level
business_urgency_level
owner_attention
recommended_response_posture
business_reasoning_summary
business_situation_confidence
business_situation_shadow_mode
```

The fail-closed path records `NO_BUSINESS_SITUATION`, `GENERAL`, `NEUTRAL`, and `reasoning_summary=business_situation_shadow_error` as diagnostics. That fallback is intentionally non-authoritative and does not force the final response pipeline to use neutral text, ask a question, or change workflow handling.

## Non-Authority Invariants

- `business_situation_type` is not used to choose final response text.
- `perspective_stance` is not used to inject advice into the final response.
- `recommended_response_posture` is not used to rewrite the final response.
- `owner_attention` is not appended to direct or workflow responses.
- Business Situation diagnostics do not override Evidence Gap diagnostics.
- Business Situation diagnostics do not override Response Authority diagnostics.
- Evidence Gap remains shadow mode only.
- Response Authority remains shadow mode only.
- reset acknowledgement behavior remains owned by the reset path.
- active workflow continuation remains owned by Conversation OS and workflow handlers.
- direct semantic and direct analytical responses remain owned by existing response builders.
- commit boundary output remains independent from Business Situation diagnostics.

Coverage lives in `tests/test_v5134_business_situation_runtime_audit.py`.
