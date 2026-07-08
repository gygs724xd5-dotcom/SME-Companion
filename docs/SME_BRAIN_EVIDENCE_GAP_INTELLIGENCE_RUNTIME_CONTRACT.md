# SME Companion V5.12.0 Evidence Gap Intelligence Runtime Contract

V5.12.0 defines the Evidence Gap Intelligence runtime contract as documentation only.

This document does not introduce runtime code, workflow behavior, router behavior, planner behavior, app changes, prompts, tests, or business vertical implementation.

Evidence Gap Intelligence remains a future SME Brain layer. Response Authority remains shadow mode only and must not be activated as a behavior gate by this contract.

## 1. Purpose

Evidence Gap Intelligence determines whether the current turn has enough reliable information to answer safely and usefully.

Its purpose is to:

- detect whether evidence is sufficient for a useful answer;
- prevent unnecessary questions when current evidence is already sufficient;
- prevent overconfident answers when key data is missing, stale, or contradictory;
- support smallest-next-question behavior when one focused answer would resolve the blocking gap.

Evidence Gap Intelligence answers:

> Is the evidence sufficient, and if not, what is the smallest material gap?

It does not choose final response text.

## 2. Position in the SME Brain Stack

For the V5.12 runtime contract, the relevant response path is:

```text
Perception / Understanding
    -> Truth Status
    -> Evidence Gap Intelligence
    -> Cognitive Response Authority
    -> Perspective / Business Situation
    -> Response Generation
    -> Commit Boundary
```

Evidence Gap Intelligence sits after Truth Status because missing evidence should be diagnosed from current reliance limits, unsupported claims, stale claims, and contradictions.

It sits before Cognitive Response Authority because Response Authority may use evidence sufficiency as one signal when deciding the authorized response mode.

## 3. Relationship With Cognitive Response Authority

Evidence Gap Intelligence does not choose final response text.

Evidence Gap Intelligence outputs evidence sufficiency, gap diagnostics, and question need. Cognitive Response Authority may use that profile as one signal when selecting a response mode.

Cognitive Response Authority remains the response-mode decider. Evidence Gap Intelligence must not override it, directly authorize a workflow, directly start a workflow, or directly force a clarification response.

The intended boundary is:

```text
Evidence Gap Intelligence says: evidence is sufficient, insufficient, conflicted, or answerable with assumptions.
Cognitive Response Authority says: the authorized response mode is direct answer, business analysis, clarification, workflow, refusal, reset acknowledgement, or fallback.
```

## 4. Inputs

Future implementation may evaluate these inputs:

- `user_message`;
- extracted entities;
- intent or semantic classification;
- active workflow requirements;
- known business memory and context;
- truth status and confidence;
- completed workflow context;
- reset boundary state;
- available calculation inputs;
- missing required fields;
- contradictory facts.

Inputs must be treated as read-only. Evidence Gap Intelligence must not mutate workflow state, memory, context, router state, planner state, or truth status.

## 5. Outputs

Future implementation should produce an `EvidenceGapProfile`.

The profile should include:

```yaml
evidence_sufficient: true
gap_detected: false
gap_type: "NO_GAP"
missing_fields: []
conflicting_fields: []
smallest_next_question: null
can_answer_with_assumptions: false
assumption_notes: []
confidence: 1.0
reason: "current_turn_contains_required_evidence"
diagnostics: {}
```

Field meanings:

- `evidence_sufficient`: whether the current turn has enough reliable evidence to answer safely and usefully.
- `gap_detected`: whether a material evidence gap exists.
- `gap_type`: canonical gap type.
- `missing_fields`: specific missing fields or evidence items blocking a reliable answer.
- `conflicting_fields`: fields or claims with unresolved contradiction.
- `smallest_next_question`: the narrowest useful question candidate, or `null`.
- `can_answer_with_assumptions`: whether a direct answer is acceptable with clearly stated assumptions.
- `assumption_notes`: assumptions that must be disclosed if used.
- `confidence`: confidence in the evidence-gap diagnosis, not confidence in the final answer.
- `reason`: stable short reason for the profile.
- `diagnostics`: implementation-specific diagnostics that remain non-authoritative.

## 6. Canonical Gap Types

The canonical V5.12.0 gap types are:

- `NO_GAP`
- `MISSING_REQUIRED_FIELD`
- `MISSING_BUSINESS_CONTEXT`
- `AMBIGUOUS_INTENT`
- `CONTRADICTORY_EVIDENCE`
- `STALE_CONTEXT`
- `WORKFLOW_REQUIREMENT_GAP`
- `CALCULATION_INPUT_GAP`
- `MEMORY_LOOKUP_GAP`
- `USER_CONFIRMATION_GAP`

These names are a runtime contract vocabulary. They do not require implementation in V5.12.0.

## 7. Smallest-Next-Question Rule

When evidence is insufficient and a question is warranted, Evidence Gap Intelligence should identify the smallest useful next question.

Rules:

- Ask only one necessary question when possible.
- Do not ask broad forms when one field is missing.
- Do not ask if the system can answer safely with a clearly stated assumption.
- Do not ask again for information already provided in the current turn.
- Do not revive stale completed workflow context after reset.

The smallest next question is a diagnostic candidate only. Response Authority and response generation remain responsible for whether and how it reaches the user.

## 8. Direct Answer Rules

Evidence Gap Intelligence should prefer useful direct answers over unnecessary clarification when evidence is sufficient.

Rules:

- If the user asks an analytical statement and enough numbers are present, answer directly.
- If the user gives a correction with enough information, answer directly.
- If the user asks a general business explanation, do not force workflow data collection.
- If key calculation inputs are missing, ask the smallest next question.

Missing workflow fields are not automatically evidence gaps for a general explanation or analytical answer.

## 9. Workflow Relationship

Evidence Gap Intelligence may identify missing workflow requirements.

It must not decide `START_WORKFLOW` or `CONTINUE_WORKFLOW` by itself. It should provide requirement-level diagnostics to Cognitive Response Authority, which remains responsible for response-mode selection.

Completed workflows should be treated as released unless the user explicitly re-enters them. Evidence Gap Intelligence must not use released workflow state to manufacture a continuation gap.

## 10. Reset and New Chat Isolation

Reset and New Chat boundaries invalidate active evidence from old completed workflow context.

Durable business memory may remain available when allowed by memory policy and truth status, but stale active workflow context must not be used as current evidence after reset.

Evidence Gap Intelligence must distinguish:

- durable business memory that may inform current context;
- active workflow evidence that belongs to a pre-reset or released workflow;
- current-turn evidence supplied by the user now.

## 11. Diagnostics Contract

Future shadow diagnostics should use stable keys:

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

Diagnostics are for auditability and future acceptance guards. They must not become a behavior gate in V5.12.0.

## 12. Invariants

Evidence Gap Intelligence must obey these invariants when implemented:

- It must be pure and deterministic for the same inputs.
- It must not mutate workflow, memory, context, router, planner, or truth-status inputs.
- It must not generate final user-facing answer text.
- It must not override Cognitive Response Authority.
- It must prefer useful direct answers over unnecessary clarification.
- It must fail closed when evidence is contradictory.
- It must avoid duplicate clarification questions.
- It must not directly start, continue, complete, or refuse workflows.
- It must not commit memory or external state.
- It must not activate Response Authority as a behavior gate.

## 13. Failure Modes

Known failure modes this contract is intended to prevent:

- over-questioning;
- under-questioning;
- stale context reuse;
- duplicate question loop;
- treating analysis as workflow;
- treating correction as workflow continuation;
- confusing durable memory with active workflow evidence;
- asking broad questions instead of the smallest next question;
- treating workflow requirements as mandatory for general business explanations;
- using contradictory evidence as though it were reliable.

## 14. Roadmap

### V5.12.0

Runtime contract documentation only.

### V5.12.1

Introduce a pure `evidence_gap` helper and unit tests.

### V5.12.2

Add shadow diagnostics wiring without changing user-visible behavior.

### V5.12.3

Add acceptance guards for direct answers, smallest-next-question behavior, reset isolation, duplicate question avoidance, and contradiction handling.

### V5.12.4

Audit runtime diagnostics across reset handling, workflow handling, normal planner turns, and fail-closed evidence-gap errors.
