# SME Companion V5 Doctrine

## Purpose

This doctrine defines the architectural principles for SME Companion V5. It is the standard used to evaluate future V5 design, implementation, migration, and review decisions.

V5 is an architecture target. This document does not require runtime changes by itself.

## Core Doctrine

### AI-First Business Operating System

SME Companion V5 is an AI-first Business Operating System for small and medium businesses.

The system is not a chat interface with business features attached. It is a business operating layer that understands owner intent, business context, active work, known facts, missing facts, and next actions.

The architecture must support:

- Persistent business context.
- Durable workflows.
- Business-domain routing.
- Explainable reasoning.
- Purposeful memory.
- Structured transformation.
- One coherent response per turn.

### Business-First Interpretation

Every user turn should be interpreted as a business event before it is treated as a text generation request.

The system should ask:

- What is the owner trying to accomplish?
- Which business domain owns this request?
- Which skill or workflow applies?
- What facts are known, missing, stale, or uncertain?
- What business risk or opportunity is present?
- What should happen next?

Business meaning is the primary interpretation layer.

### Business Meaning Before Keywords

Keywords can be useful signals, but they are not the architecture.

V5 should route and reason from:

- Business goal.
- Conversation act.
- Active workflow state.
- Domain context.
- Skill requirements.
- Memory.
- Entities.
- Business rules.
- Risk and confidence.

For example, "Customer says too expensive" should be understood as a sales objection, pricing, margin, value framing, and customer trust problem. It should not be handled by matching only the word "expensive".

### One Owner Per State

Every important state has one canonical owner.

Examples:

- Conversation Memory owns conversational continuity.
- Workflow Memory owns workflow progress.
- Store Memory owns durable store profile facts.
- Business Memory owns learned business facts and events.
- Transformation Memory owns structured outputs derived from raw input.
- Response Intelligence owns final response selection.

Duplicate ownership creates conflicts, stale behavior, and unexplainable routing. Derived copies may exist only when marked as derived and traceable to the source owner.

### One Canonical Source of Truth

V5 should maintain one canonical source of truth for each business object, state, and decision.

Canonical sources must be explicit:

- A workflow field should come from Workflow State.
- A durable store attribute should come from Store Memory.
- A selected skill should come from Business Knowledge and Planner decisions.
- A final turn answer should come from the Response Envelope.

When facts conflict, the system must apply documented priority rules and disclose uncertainty when needed.

### One Response Per Turn

Each user turn should produce one final response envelope.

Multiple engines may contribute to the turn, but they must not independently render competing final answers. This prevents duplicate messages, stale prompts, overwritten workflow responses, and generic fallbacks after useful answers.

The UI renders the final envelope. It should not independently decide business behavior.

### Response Intelligence Owns Rendering

Response Intelligence owns final response selection, composition, priority, and rendering guidance.

It decides how to present:

- Workflow prompts.
- Workflow results.
- Clarifications.
- Deterministic tool or transformation output.
- Business reasoning recommendations.
- LLM-composed text.
- Fallbacks.
- Diagnostics metadata.

No upstream engine should bypass Response Intelligence to produce the final owner-facing answer.

### Workflow Owns Process

Workflow owns durable business processes across turns.

Workflow is responsible for:

- Starting structured work.
- Collecting required fields.
- Validating completeness.
- Pausing and resuming.
- Handling interruptions.
- Completing and chaining workflows.
- Emitting next required action.
- Writing completion memory through Memory.

Workflow should expose state and next action. It should not own final response wording.

### Memory With Purpose

Memory exists to improve business continuity, not to store everything.

A memory write is justified only when it helps future business behavior:

- Remembering a durable store fact.
- Preserving a completed workflow outcome.
- Tracking a customer, product, supplier, or operational event.
- Maintaining continuity across turns.
- Improving future routing or diagnostics.

Memory must include owner, source, timestamp, confidence, and freshness rules where applicable.

### Explainable Reasoning

V5 decisions must be explainable to developers and, when useful, to owners.

The system should be able to explain:

- Why a domain matched.
- Why a skill matched.
- Why a workflow started, continued, paused, or completed.
- Which facts were used.
- Which facts were missing.
- Which assumptions were made.
- Which business rules applied.
- Why confidence was high, medium, or low.

Explainability is part of correctness, not an optional debug feature.

### Diagnostics By Design

Every engine should produce useful diagnostics as part of its contract.

Diagnostics should cover:

- Routing.
- Domain and skill selection.
- Memory reads and proposed writes.
- Workflow state transitions.
- Reasoning decisions.
- Planner path selection.
- Transformation provenance.
- LLM use.
- Response priority.
- Fallbacks.

Diagnostics must remain separate from business truth. They explain behavior; they do not become hidden business state.

### LLM Is An Execution Component, Not The Architecture

The LLM is a useful execution component for language generation, extraction, classification, drafting, and explanation.

The LLM is not the architecture and must not become the sole source of truth.

The LLM should receive prepared context from Conversation Intelligence, Business Knowledge, Business Reasoning, Planner, Workflow, Memory, Transformation, and Response Intelligence. Its output should be validated, prioritized, and wrapped in the Response Envelope.

### Documentation-First Evolution

V5 evolves through documentation-first architecture.

Before runtime implementation, the architecture should define:

- Engine contracts.
- Canonical objects.
- Ownership boundaries.
- Skill standards.
- Workflow lifecycle.
- Memory types.
- Response envelope.
- Diagnostics.
- Migration rules.

Runtime implementation should follow the documented contracts instead of inventing hidden behavior.

### Preserve V4 Compatibility During Migration

V5 must preserve completed V4 behavior during migration.

V4 compatibility may require adapters, registries, compatibility wrappers, and transitional paths. These are acceptable when they keep behavior stable while moving toward V5 contracts.

Migration should be incremental:

- Do not break existing owner workflows.
- Do not remove working V4 behavior before a V5 owner exists.
- Do not mix V4 and V5 ownership without an adapter boundary.
- Do not let compatibility paths become undocumented architecture.

## Doctrine Review Questions

Every future V5 change should answer:

- Which engine owns this behavior?
- Which canonical object carries this state?
- What is the source of truth?
- What diagnostics explain the decision?
- Does this preserve one response per turn?
- Does this keep workflow process separate from response rendering?
- Does this use memory with purpose?
- Does this preserve V4 compatibility during migration?
