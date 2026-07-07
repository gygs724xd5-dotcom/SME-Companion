# SME Brain Cognitive Response Authority

SME Companion V5.11.0 introduces Cognitive Response Authority as an architecture specification only.

This document defines how SME Brain should decide the kind of response a user receives on a turn. It does not define code, APIs, prompts, workflows, runtime orchestration, diagnostics UI, or business vertical behavior.

## 1. Purpose

Cognitive Response Authority owns final response-mode selection.

Its purpose is to prevent the response layer from confusing:

- direct semantic answers with workflow starts;
- business analysis with data collection;
- completed workflow output with stale workflow continuation;
- reset or New Chat state with previous context;
- semantic corrections with LLM fallback;
- evidence insufficiency with arbitrary refusal.

Cognitive Response Authority answers:

> What kind of response is authorized for this user turn?

It does not answer:

> What exact final wording should be shown?

Conversation rendering, style, and final copy may be handled by response composition, but response composition must not override the authorized response mode.

## 2. Position in the SME Brain Stack

Cognitive Response Authority sits after conversation interpretation and before final response composition.

Conceptually, the stack is:

1. User message and current session state.
2. Conversation interpretation.
3. Workflow state inspection.
4. Cognitive Response Authority.
5. Response composition.
6. UI rendering.

Cognitive Response Authority is not Workflow Authority. It may authorize starting, continuing, completing, or refusing workflow mutation, but workflow state does not own cognition.

Cognitive Response Authority is not Evidence Authority. It may consider evidence sufficiency, but it does not determine truth.

Cognitive Response Authority is not the LLM. It may authorize LLM-assisted response only after higher-priority response modes do not apply.

## 3. Inputs and Outputs

Inputs:

- current user message;
- normalized conversation act or intent when available;
- active workflow state;
- completed workflow release state;
- reset or New Chat boundary state;
- semantic correction signals;
- analytical business analysis signals;
- deterministic transformation or workflow result;
- available evidence summary;
- confidence and uncertainty markers;
- safety or policy constraints when relevant.

Outputs:

- `response_mode`;
- `response_authority_reason`;
- `workflow_authorization` when relevant;
- `evidence_sufficiency_status` when relevant;
- `reset_boundary_respected`;
- `completed_workflow_released`;
- `llm_assistance_allowed`;
- optional future diagnostics fields.

The output is a response-mode decision. It is not a durable memory write, workflow mutation, business record update, or final rendered answer.

## 4. Canonical Response Modes

### DIRECT_SEMANTIC_ANSWER

Use when the user asks a direct question or makes a semantic correction that can be answered from the current message and stable context without starting or continuing a workflow.

### DIRECT_BUSINESS_ANALYSIS

Use when the user asks for reasoning, comparison, interpretation, cost analysis, trade-off assessment, or business advice that can be answered without collecting workflow fields.

### CLARIFICATION_QUESTION

Use when material uncertainty prevents a responsible answer or action, and one focused question would resolve the blocking uncertainty.

### START_WORKFLOW

Use when the current user message explicitly requests a task that requires a known workflow and the task is not merely a semantic answer or analysis.

### CONTINUE_WORKFLOW

Use when an active workflow is collecting required information, the current user message supplies relevant continuation data, and no reset boundary or completed workflow release state blocks continuation.

### COMPLETE_WORKFLOW

Use when a deterministic workflow has enough required information to produce its final result for the current task.

### REFUSE_WORKFLOW_MUTATION

Use when a workflow continuation, restart, overwrite, or mutation would violate reset isolation, completed workflow release, user intent, or deterministic workflow boundaries.

### LLM_ASSISTED_RESPONSE

Use only after higher-priority deterministic, semantic, analytical, clarification, workflow, reset, and refusal modes do not apply. LLM assistance may draft or explain, but it does not own response-mode authority.

### RESET_ACKNOWLEDGEMENT

Use when the current user action establishes a reset or New Chat boundary. The response should acknowledge the fresh context and must not leak or continue pre-reset workflow state.

## 5. Authority Order

Cognitive Response Authority resolves response mode in this order:

1. Current user message.
2. Reset boundary.
3. Completed workflow release state.
4. Explicit workflow intent.
5. Semantic correction or analysis.
6. Evidence sufficiency.
7. Fallback LLM response.

The current user message is first because the system must answer what the user is doing now, not what stale state suggests.

Reset boundary is second because isolation must defeat previous context before workflow logic runs.

Completed workflow release state is third because a completed workflow must not keep owning unrelated future turns.

Explicit workflow intent is fourth because workflows should start only when the user asks for workflow-like execution.

Semantic correction or analysis is fifth because many business-owner turns look operational but are actually requests for meaning, correction, or reasoning.

Evidence sufficiency is sixth because the system should answer when evidence is sufficient, ask when evidence is materially insufficient, and avoid fabricating certainty.

Fallback LLM response is last because generative assistance should fill only the space not already governed by stronger authority.

## 6. Analytical Cost Statements

Analytical cost statements belong to `DIRECT_BUSINESS_ANALYSIS` unless the user explicitly asks to run or continue a cost workflow.

Rules:

- A question about whether a cost is high, low, profitable, risky, or sustainable is analysis, not workflow collection.
- A user-provided cost figure should not automatically trigger missing-field prompts.
- If the user asks for interpretation of a cost, answer the interpretation directly when enough context exists.
- If important context is missing, ask one clarification question rather than starting a deterministic workflow by default.
- Do not treat analytical cost wording as permission to mutate workflow state.

Example:

> "Is 100 baht too expensive for this product?"

This should authorize business analysis, not a cost workflow, unless the user explicitly asks to calculate margin, build a pricing plan, or complete a known cost template.

## 7. Semantic Corrections

Semantic corrections belong to `DIRECT_SEMANTIC_ANSWER` when the user is correcting meaning, wording, identity, classification, or prior interpretation.

Rules:

- The latest correction from the user controls the response.
- A correction is not a workflow continuation unless it clearly supplies requested workflow data.
- The system should acknowledge the corrected meaning and answer under that meaning.
- Do not ask for workflow fields when the correction resolves the user's intent.
- Do not let stale workflow state override a direct correction.

Semantic correction authority protects direct owner communication from being swallowed by workflow machinery.

## 8. Deterministic Workflow Completion

Deterministic workflow completion belongs to `COMPLETE_WORKFLOW` only when all required inputs for the active task are present and the result can be produced without invention.

Rules:

- Completion must be tied to the active workflow instance.
- Completion must produce the workflow result, not a generic LLM summary.
- After completion, the workflow should enter a release state so unrelated future messages are not treated as continuation.
- Missing non-critical detail may be stated as an assumption only when the workflow contract permits it.
- Missing critical detail requires `CLARIFICATION_QUESTION`, not completion.
- A completed workflow must not be reopened by ambiguous follow-up text.

## 9. New Chat and Reset Isolation

Reset and New Chat boundaries authorize `RESET_ACKNOWLEDGEMENT` or fresh-turn handling.

Rules:

- Pre-reset workflow state must not continue after the boundary.
- Pre-reset completed workflow release state must not control the new context.
- The first post-reset user message should be interpreted as a fresh message.
- Reset acknowledgement should be brief and should not restate stale workflow details.
- Runtime diagnostics may later record reset isolation, but V5.11.0 does not implement new diagnostics behavior.

## 10. Future Diagnostics Fields

Future implementation may expose diagnostics such as:

```yaml
response_authority_version: "5.11.x"
response_mode: "DIRECT_BUSINESS_ANALYSIS"
response_authority_reason: "analytical_cost_statement"
authority_order_applied:
  - current_user_message
  - reset_boundary
  - completed_workflow_release_state
  - explicit_workflow_intent
  - semantic_correction_or_analysis
  - evidence_sufficiency
  - fallback_llm_response
reset_boundary_respected: true
completed_workflow_released: true
workflow_mutation_refused: false
evidence_sufficiency_status: "sufficient | insufficient | not_applicable"
llm_assistance_allowed: false
```

These fields are roadmap diagnostics only. V5.11.0 does not require runtime implementation.

## 11. Invariants

- One user turn should have one authorized response mode.
- Current user message outranks stale workflow state.
- Reset isolation outranks workflow continuation.
- Completed workflow release prevents accidental continuation.
- Explicit workflow intent is required to start a workflow.
- Semantic correction must be answered as correction before workflow fallback.
- Analytical business analysis must not be converted into deterministic workflow collection by default.
- Deterministic workflow completion must not rely on invented critical inputs.
- LLM fallback must not override deterministic or semantic authority.
- Response Authority does not write memory, execute tools, or mutate business records.

## 12. Failure Modes

Known failure modes this architecture is intended to prevent:

- stale workflow continuation after New Chat;
- active workflow prompts overriding direct semantic answers;
- completed workflows retaining ownership of later unrelated turns;
- cost analysis being misclassified as cost workflow collection;
- semantic corrections being treated as missing workflow fields;
- deterministic workflow completion being replaced by generic LLM prose;
- LLM fallback answering before evidence sufficiency is checked;
- reset acknowledgement leaking previous workflow context;
- ambiguous follow-up text mutating workflow state without authorization.

## 13. Roadmap V5.11.0 to V5.11.3

### V5.11.0

Architecture documentation only. Define Cognitive Response Authority, canonical response modes, authority order, invariants, failure modes, and roadmap.

### V5.11.1

Introduce passive diagnostics for response-mode selection without changing user-visible behavior. Diagnostics should observe authority decisions but not enforce them.

### V5.11.2

Add guarded runtime enforcement for reset isolation, completed workflow release, semantic correction priority, analytical cost analysis, and deterministic workflow completion boundaries.

### V5.11.3

Expand diagnostics and acceptance coverage across representative owner-facing conversations, including direct answers, business analysis, workflow starts, workflow continuation, workflow completion, reset isolation, and fallback LLM response.
