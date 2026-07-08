# SME Companion V5.13.0 Perspective / Business Situation Reasoning Runtime Contract

V5.13.0 defines the Perspective / Business Situation Reasoning runtime contract as documentation only.

This document does not introduce runtime code, workflow behavior, router behavior, planner behavior, app changes, prompts, tests, or business vertical implementation.

Perspective / Business Situation Reasoning remains a future SME Brain layer. Response Authority and Evidence Gap remain shadow mode only and must not be activated as behavior gates by this contract.

## 1. Purpose

Perspective / Business Situation Reasoning interprets the business situation behind the current user turn.

Its purpose is to:

- identify what kind of business situation the user is describing;
- add owner-level judgment context and practical business perspective;
- prevent flat, mechanical answers when the user needs business reasoning;
- separate business interpretation from workflow execution and response generation.

Perspective answers:

> What kind of business situation is this, and what business perspective should shape the answer?

It does not choose final response mode, run workflows, or write final user-facing answer text.

## 2. Position in the SME Brain Stack

For the V5.13 runtime contract, the relevant response path is:

```text
Perception / Understanding
    -> Truth Status
    -> Evidence Gap Intelligence
    -> Perspective / Business Situation Reasoning
    -> Cognitive Response Authority
    -> Response Generation
    -> Commit Boundary
```

Evidence Gap determines sufficiency.

Perspective determines the business situation and stance.

Response Authority determines response mode.

Response Generation writes the final answer.

Earlier runtime contracts may describe Response Authority before Perspective because Response Authority was introduced first as a shadow diagnostic foundation. The intended contract going forward is that Perspective can provide business situation signals to Response Authority, while Response Authority remains responsible for response-mode selection.

## 3. Relationship With Response Authority

Perspective does not choose final response mode.

Perspective outputs business situation signals, such as situation type, business domain, stance, risk, opportunity, urgency, owner attention, and confidence.

Cognitive Response Authority may use the Perspective profile as one signal in a future runtime implementation when selecting a response mode.

Perspective must not directly start workflows, continue workflows, complete workflows, refuse workflow mutation, or force clarification.

Perspective must not override direct semantic answers or direct analytical answers. If the user asks a direct question or supplies a correction that can be answered directly, Perspective may classify the situation but must not convert the turn into workflow behavior or generic advice.

## 4. Relationship With Evidence Gap

Evidence Gap Intelligence says whether enough reliable information exists to answer safely and usefully.

Perspective says what the situation means when information is sufficient enough to interpret.

If evidence is insufficient, contradictory, stale, or materially uncertain, Perspective should lower confidence or mark the situation unresolved rather than overclaiming.

Perspective must not ask clarification directly. It may recommend the type of clarification needed as a diagnostic signal for downstream layers.

The intended boundary is:

```text
Evidence Gap Intelligence says: evidence is sufficient, insufficient, conflicted, stale, or answerable with assumptions.
Perspective says: the situation appears to be cost change, pricing decision, customer issue, planning decision, or another business situation type.
Response Authority says: the authorized response mode is direct answer, business analysis, clarification, workflow, refusal, reset acknowledgement, or fallback.
```

## 5. Inputs

Future implementation may evaluate these inputs:

- `user_message`;
- intent or semantic classification;
- extracted entities;
- `evidence_gap_profile`;
- truth status and confidence;
- business memory and known context;
- active workflow state;
- completed workflow context;
- reset boundary state;
- calculation result if available;
- cost, pricing, sales, customer, inventory, or domain signals;
- recent conversation context;
- owner goal or business objective if known.

Inputs must be treated as read-only. Perspective must not mutate workflow state, memory, context, router state, planner state, evidence gap diagnostics, truth status, or response authority diagnostics.

## 6. Outputs

Future implementation should produce a `BusinessSituationProfile`.

The profile should include:

```yaml
situation_detected: true
situation_type: "COST_CHANGE"
business_domain: "COST"
perspective_stance: "ANALYTICAL"
risk_level: "LOW"
opportunity_level: "NONE"
urgency_level: "NORMAL"
owner_attention: "watch margin impact before changing price"
recommended_response_posture: "ANALYTICAL"
reasoning_summary: "The user is interpreting a cost movement and needs business meaning, not workflow collection."
confidence: 0.85
assumptions: []
diagnostics: {}
```

Field meanings:

- `situation_detected`: whether the current turn contains a business situation.
- `situation_type`: canonical business situation type.
- `business_domain`: canonical business domain most relevant to the turn.
- `perspective_stance`: business stance that should inform downstream reasoning.
- `risk_level`: estimated business risk level for the situation.
- `opportunity_level`: estimated business opportunity level for the situation.
- `urgency_level`: estimated urgency for owner attention.
- `owner_attention`: the practical business lever, issue, or next consideration the owner should watch.
- `recommended_response_posture`: suggested communication posture for downstream response generation.
- `reasoning_summary`: concise diagnostic explanation of the interpretation.
- `confidence`: confidence in the situation interpretation, not confidence in the final answer.
- `assumptions`: assumptions used to interpret the situation.
- `diagnostics`: implementation-specific diagnostics that remain non-authoritative.

## 7. Canonical Situation Types

The canonical V5.13.0 situation types are:

- `NO_BUSINESS_SITUATION`
- `COST_CHANGE`
- `COST_CORRECTION`
- `PRICING_DECISION`
- `PROFIT_MARGIN_RISK`
- `SALES_OPPORTUNITY`
- `INVENTORY_RISK`
- `CUSTOMER_ISSUE`
- `CASHFLOW_CONCERN`
- `OPERATIONAL_BOTTLENECK`
- `PLANNING_DECISION`
- `WORKFLOW_STATUS`
- `DATA_QUALITY_ISSUE`
- `GENERAL_BUSINESS_QUESTION`

These names are a runtime contract vocabulary. They do not require implementation in V5.13.0.

## 8. Canonical Business Domains

The canonical V5.13.0 business domains are:

- `COST`
- `PRICING`
- `SALES`
- `INVENTORY`
- `CUSTOMER`
- `CASHFLOW`
- `OPERATIONS`
- `MARKETING`
- `PRODUCT`
- `SUPPLIER`
- `ACCOUNTING`
- `GENERAL`

## 9. Perspective Stance

The canonical V5.13.0 perspective stances are:

- `ANALYTICAL`
- `CAUTIOUS`
- `PROACTIVE`
- `CORRECTIVE`
- `EXPLANATORY`
- `STRATEGIC`
- `OPERATIONAL`
- `OWNER_ADVISORY`
- `NEUTRAL`

Perspective stance describes the business lens that should shape later reasoning. It is not the final response mode and must not force response generation to use specific wording.

## 10. Business Reasoning Rules

Perspective should follow these rules when implemented:

- Analytical cost statements should be interpreted as `COST_CHANGE` situations unless stronger current evidence indicates another type.
- Cost corrections should be interpreted as `COST_CORRECTION`, not workflow continuation.
- If margin or profit is affected, `risk_level` should increase.
- If the user asks what to do next, `owner_attention` should identify the next business lever.
- If evidence is insufficient, lower confidence and avoid overclaiming.
- If evidence is contradictory, mark the situation as unresolved or use a cautious stance.
- If the message is casual or non-business, return `NO_BUSINESS_SITUATION`.
- Durable memory may inform perspective, but stale completed workflow context after reset must not dominate the active interpretation.
- Current user message and valid current context outrank old workflow context.
- Workflow status can be recognized as `WORKFLOW_STATUS`, but recognition must not continue the workflow by itself.

## 11. Response Posture Rules

Perspective may recommend a response posture for downstream layers:

- `ANALYTICAL` for numeric, cost, pricing, revenue, profit, or margin interpretation.
- `CORRECTIVE` for user corrections.
- `CAUTIOUS` for conflicting, stale, unresolved, or low-confidence situations.
- `PROACTIVE` for opportunity, planning, growth, or next-step situations.
- `OWNER_ADVISORY` when the user needs practical business decision guidance.
- `NEUTRAL` when the turn is not business-relevant.

Recommended response posture is advisory diagnostics only. Cognitive Response Authority and response generation remain responsible for whether and how the final answer uses it.

## 12. Reset and New Chat Isolation

Reset and New Chat boundaries invalidate active situation interpretation from old completed workflow context.

Old completed workflow context should not define the current business situation after reset.

Durable business memory may remain background context only when allowed by memory policy and truth status.

Active situation interpretation must be based primarily on the current user message, current valid context, current evidence gap profile, current truth status, and current active workflow state.

Perspective must distinguish:

- durable business memory that may provide background context;
- released or pre-reset completed workflow context that must not control the current turn;
- current-turn evidence supplied by the user now.

## 13. Diagnostics Contract

Future shadow diagnostics should use stable keys:

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

Diagnostics are for auditability and future acceptance guards. They must not become a behavior gate in V5.13.0.

## 14. Invariants

Perspective / Business Situation Reasoning must obey these invariants when implemented:

- It must be pure and deterministic for the same inputs.
- It must not mutate input context.
- It must not generate final user-facing answer text.
- It must not start, continue, complete, or refuse workflows.
- It must not override Evidence Gap Intelligence.
- It must not override Cognitive Response Authority.
- It must not reuse stale completed workflow context after reset.
- It must distinguish analysis, correction, workflow status, and general business advice.
- It must prefer practical business usefulness over generic commentary.
- It must not commit memory or external state.
- It must remain shadow diagnostics only until a later contract explicitly activates behavior.

## 15. Failure Modes

Known failure modes this contract is intended to prevent:

- over-advising when the user only needs a direct answer;
- treating corrections as workflow continuation;
- treating casual messages as business situations;
- reusing stale context after reset;
- overclaiming with insufficient evidence;
- ignoring margin or risk impact;
- giving generic advice without identifying the actual business lever;
- confusing situation interpretation with response generation;
- using durable memory as current reality without truth-status support;
- allowing Perspective diagnostics to become a workflow gate or response-mode gate.

## 16. Roadmap

### V5.13.0

Runtime contract documentation only.

### V5.13.1

Introduce a pure `business_situation` helper and unit tests.

### V5.13.2

Add shadow diagnostics wiring without changing user-visible behavior.

### V5.13.3

Add acceptance guards for cost change interpretation, cost correction handling, margin-risk sensitivity, reset isolation, casual message handling, and owner-attention diagnostics.

### V5.13.4

Audit runtime diagnostics across reset handling, workflow handling, normal planner turns, and fail-closed business-situation errors.
