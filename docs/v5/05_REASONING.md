# Business Reasoning Engine

## Purpose

The V5 Business Reasoning Engine turns conversation understanding, business knowledge, entities, memory, and workflow state into an explainable business decision.

It does not rely on keyword matching as the primary mechanism. Keywords can be signals, but the decision must come from business meaning.

## V5.1.3 Runtime Foundation

V5.1.3 introduces `brain/business_reasoning_runtime.py` as an additive runtime reasoning context layer.

The runtime creates a canonical `ReasoningContext` from the existing route, `KnowledgeContext`, workflow state, and memory. It infers high-level diagnostic context only:

- Business goal.
- Decision type.
- Business stage.
- Selected domain and skill.
- Known and missing entities.
- Assumptions, risks, and opportunities.
- Recommended next action.
- Reasoning pattern.
- Confidence.
- Runtime diagnostics.

This foundation is diagnostics-only. It does not change planner decisions, routing behavior, workflow behavior, response behavior, or Conversation OS behavior.

The existing planner remains the execution decision owner. Planner migration to consume `ReasoningContext` will occur in a later explicit architecture step.

## Reasoning Flow

```text
Reasoning
  |
  v
Workflow Selection
  |
  v
Decision Making
  |
  v
Response
```

## Inputs

The Reasoning Engine receives:

- Conversation frame.
- Candidate domains.
- Candidate skills.
- Extracted entities.
- Active workflow state.
- Relevant memory.
- Store profile.
- Business rules.
- Tool availability.
- Confidence diagnostics.

## Reasoning

The engine identifies:

- User business goal.
- Business stage.
- Decision type.
- Known facts.
- Missing facts.
- Risk.
- Opportunity.
- Relevant business principle.
- Recommended next action.

Example:

An owner says, "Customer says too expensive."

The reasoning engine should infer a sales objection and margin/trust problem. It should not merely match the word "expensive". It should consider whether product, price, customer type, margin, and offer context are known.

## Workflow Selection

After reasoning, the engine determines whether the request should:

- Start a workflow.
- Continue the active workflow.
- Pause the active workflow.
- Resume a previous workflow.
- Complete a workflow.
- Chain into a new workflow.
- Produce a direct answer without workflow.

Workflow selection depends on business state, not phrase matching alone.

## Decision Making

The engine produces a decision containing:

- Primary action.
- Domain.
- Skill.
- Workflow action.
- Required entities.
- Memory requirements.
- Response mode.
- Tool requirements.
- Confidence.
- Fallback path.

Decision examples:

- Ask for missing product cost before calculating price.
- Continue purchase workflow because the user supplied quantity.
- Answer quick interruption and then resume active workflow.
- Use OCR transformation before accounting classification.
- Use LLM only for final wording after structured reasoning is complete.

## Response

The Reasoning Engine does not own final rendering. It provides response guidance:

- What the response should accomplish.
- What facts it can state.
- What assumptions must be disclosed.
- What question should be asked next.
- Whether to include a recommendation, warning, checklist, table, or script.

Response Intelligence then composes the final response envelope.

## Confidence

Reasoning confidence should consider:

- Intent clarity.
- Entity completeness.
- Skill match quality.
- Memory freshness.
- Workflow ownership.
- Business rule conflicts.
- Tool availability.

Low confidence should lead to clarification, not fabricated certainty.

## Diagnostics

Every reasoning decision should expose:

- Candidate skills considered.
- Selected skill and reason.
- Rejected skills and reasons.
- Missing entities.
- Memory used.
- Business rules applied.
- Workflow decision.
- Confidence score or label.
