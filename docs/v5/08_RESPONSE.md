# V5 Response Architecture

## Purpose

V5 Response Intelligence ensures the user receives one coherent answer for each turn. It coordinates conversation intelligence, workflow state, reasoning output, transformations, LLM text, and fallback logic before rendering.

## Response Intelligence

Response Intelligence owns final response selection.

Responsibilities:

- Choose the highest-priority valid response source.
- Prevent empty, repetitive, irrelevant, or stale replies.
- Ensure active workflow prompts are not accidentally overwritten.
- Apply owner-friendly business style.
- Attach confidence and follow-up.
- Produce a response envelope.

## Conversation Intelligence

Conversation Intelligence contributes:

- Conversation act.
- Reference resolution.
- Clarification needs.
- Interruption status.
- Active workflow ownership.
- User intent continuity.

It helps Response Intelligence decide whether the answer should be direct, clarifying, workflow-driven, or continuation-based.

## Transformation

Transformation contributes structured outputs such as:

- Product descriptions.
- Cost calculations.
- Extracted receipt fields.
- Sales scripts.
- Marketing posts.
- Purchase plans.
- Dashboard summaries.
- Business reports.

Response Intelligence decides how to present transformed output and whether more data is needed.

## Response Composer

The Response Composer creates the final owner-facing response.

It should receive:

- Planner decision.
- Reasoning guidance.
- Workflow state.
- Transformation output.
- LLM draft if used.
- Memory context.
- Business rules.
- Style requirements.
- Fallback status.

It should produce:

- Final text.
- Follow-up question if needed.
- Structured sections if useful.
- Response source.
- Confidence.
- Diagnostics.

## Priority

Response priority should be explicit.

Recommended order:

1. Safety or guard response.
2. Required workflow prompt or workflow result.
3. Clarification for missing critical context.
4. Deterministic transformation or tool result.
5. Business reasoning recommendation.
6. LLM-composed response from prepared context.
7. Companion fallback.
8. Generic fallback.

Priority is not absolute when a response is invalid. Response Intelligence should validate freshness, relevance, and completeness.

## Fallback

Fallback should be useful, not generic.

A good fallback should:

- Admit what is missing.
- Ask one practical next question.
- Preserve the active workflow if present.
- Avoid pretending to complete the task.
- Suggest a domain-specific next step when possible.

Example:

"I can help calculate that, but I need the selling price and cost per unit first. What is the cost for one unit?"

## Response Envelope

Every turn should conceptually produce one response envelope:

```yaml
text: "Final assistant response"
source: "workflow | reasoning | transformation | llm | fallback | guard"
domain: "Selected domain"
skill_id: "Selected skill"
workflow:
  id: "workflow_id_or_none"
  status: "collecting | ready | completed | none"
memory:
  read:
    - "memory reference"
  write:
    - "memory write proposal"
confidence: "high | medium | low"
follow_up: "Question or null"
diagnostics:
  planner: {}
  reasoning: {}
  response_priority: []
```

The UI renders the envelope. It should not independently decide business behavior.

