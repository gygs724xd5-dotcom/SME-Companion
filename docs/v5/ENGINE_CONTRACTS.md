# V5 Engine Contracts

## Purpose

This document defines the engine-level contracts for SME Companion V5. Each engine has a clear purpose, input boundary, output boundary, responsibility set, ownership model, and consumer list.

These contracts are documentation-only and implementation-neutral.

## Contract Rules

- Each engine owns one primary architectural concern.
- Engines exchange canonical objects, not hidden state.
- Engines may attach diagnostics, but diagnostics do not become business truth.
- Engines should not bypass downstream owners.
- Response Intelligence is the final response owner.
- Workflow is the process owner.
- Memory is the continuity owner.
- The LLM Adapter is an execution boundary, not a business owner.

## Conversation Intelligence

### Purpose

Conversation Intelligence interprets the user turn before business execution.

### Inputs

- Raw user message.
- Uploaded file or image references.
- Active UI surface.
- Recent conversation memory.
- Active workflow summary.
- Store context reference.
- User action metadata.

### Outputs

- `ConversationFrame`.
- Conversation act.
- Resolved references.
- Candidate entities.
- Ambiguity flags.
- Interruption or continuation signal.
- Diagnostics.

### Responsibilities

- Normalize the turn.
- Detect whether the message is a question, command, correction, continuation, confirmation, cancellation, interruption, or feedback.
- Resolve references such as "this product", "that customer", or "continue".
- Identify whether an active workflow may own the turn.
- Detect missing context and ambiguity.
- Preserve conversational continuity without making final business decisions.

### Ownership

Conversation Intelligence owns turn interpretation and conversation framing.

It does not own business rules, workflow state, memory writes, LLM prompts, or final response rendering.

### Consumers

- Business Knowledge.
- Business Reasoning.
- Planner.
- Workflow.
- Memory.
- Response Intelligence.

## Business Knowledge

### Purpose

Business Knowledge maps conversation meaning to structured business domains, skills, doctrine, rules, workflows, examples, and response guidance.

### Inputs

- `ConversationFrame`.
- Store profile reference.
- Skill registry.
- Domain registry.
- Business doctrine.
- Business rules.
- Workflow definitions.
- Tool capability registry.

### Outputs

- `KnowledgeContext`.
- Candidate domains.
- Candidate skills.
- Required entities.
- Required memory.
- Applicable business rules.
- Reasoning patterns.
- Workflow links.
- Tool requirements.
- Diagnostics.

### Responsibilities

- Select and rank candidate domains.
- Select and rank candidate skills.
- Load skill standards and domain rules.
- Attach relevant examples and vocabulary.
- Identify required entities and memory.
- Identify workflow and tool requirements.
- Explain why skills matched or were rejected.

### Ownership

Business Knowledge owns domain definitions, skill definitions, business doctrine, rule references, and knowledge selection.

It does not own active workflow state, final reasoning decisions, memory persistence, or final response wording.

### Consumers

- Business Reasoning.
- Planner.
- Workflow.
- Transformation.
- Response Intelligence.
- Developer diagnostics.

## Business Reasoning

### Purpose

Business Reasoning turns conversation understanding, knowledge, entities, memory, and workflow context into an explainable business decision.

### Inputs

- `ConversationFrame`.
- `KnowledgeContext`.
- Relevant memory results.
- Active `WorkflowState`.
- Store profile facts.
- Candidate entities.
- Business rules.
- Tool availability.

### Outputs

- `ReasoningDecision`.
- Business goal.
- Selected or recommended domain.
- Selected or recommended skill.
- Known facts.
- Missing facts.
- Assumptions.
- Risk and opportunity.
- Recommended next action.
- Confidence.
- Diagnostics.

### Responsibilities

- Interpret intent in business terms.
- Identify the owner goal and decision type.
- Apply business rules and reasoning patterns.
- Determine known, missing, stale, and uncertain facts.
- Recommend whether to answer, ask, transform, use a workflow, use a tool, retrieve memory, or use the LLM.
- Provide response guidance without rendering the final response.

### Ownership

Business Reasoning owns the business interpretation and recommendation for the turn.

It does not own process execution, workflow persistence, memory writes, LLM calls, or final response rendering.

### Consumers

- Planner.
- Workflow.
- Memory.
- Transformation.
- Response Intelligence.
- LLM Adapter.

## Planner

### Purpose

The Planner converts reasoning into an auditable execution plan.

### Inputs

- `ConversationFrame`.
- `KnowledgeContext`.
- `ReasoningDecision`.
- Active `WorkflowState`.
- Memory retrieval results.
- Tool availability.
- Runtime capability flags.
- Compatibility constraints.

### Outputs

- `PlannerDecision`.
- Primary execution path.
- Fallback path.
- Engine actions.
- Tool requirements.
- LLM requirements.
- Memory read and write intentions.
- Workflow action.
- Confidence.
- Diagnostics.

### Responsibilities

- Decide whether to answer, ask, start workflow, continue workflow, use tool, transform input, retrieve memory, call LLM, or fallback.
- Respect active workflow ownership and interruption rules.
- Select primary and fallback execution paths.
- Decide whether LLM use is needed and what prepared context it should receive.
- Produce an auditable plan before execution.

### Ownership

The Planner owns orchestration decisions.

It does not own domain knowledge, business rules, workflow state transitions, memory persistence, transformation schemas, LLM generation, or final rendering.

### Consumers

- Workflow.
- Memory.
- Transformation.
- LLM Adapter.
- Response Intelligence.
- Developer diagnostics.

## Workflow

### Purpose

Workflow manages durable business processes that can span multiple turns.

### Inputs

- `PlannerDecision`.
- `ConversationFrame`.
- `ReasoningDecision`.
- Active `WorkflowState`.
- Workflow definitions.
- Extracted fields.
- Validation rules.
- Memory context.

### Outputs

- Updated `WorkflowState`.
- Required next action.
- Collected fields.
- Missing fields.
- Validation results.
- Completion result.
- Memory write proposals.
- Diagnostics.

### Responsibilities

- Start workflows.
- Continue active workflows.
- Collect and validate required fields.
- Pause, resume, cancel, complete, fail, or chain workflows.
- Handle interruptions with Planner and Response Intelligence.
- Emit state and next required action.
- Propose completion memory through Memory.

### Ownership

Workflow owns workflow process and workflow state.

It does not own final response wording, durable business memory persistence, domain definitions, or LLM behavior.

### Consumers

- Memory.
- Response Intelligence.
- Planner.
- Business Reasoning.
- Transformation.
- Developer diagnostics.

## Memory

### Purpose

Memory preserves business continuity across turns, sessions, workflows, and structured outputs.

### Inputs

- `ConversationFrame`.
- `ReasoningDecision`.
- `PlannerDecision`.
- `WorkflowState`.
- `TransformationResult`.
- Memory read requests.
- Memory write proposals.
- Store context.

### Outputs

- Retrieved memory context.
- `BusinessMemoryItem` records.
- Updated workflow memory.
- Updated conversation memory.
- Updated transformation memory.
- Memory write confirmations or rejections.
- Freshness and confidence metadata.
- Diagnostics.

### Responsibilities

- Retrieve relevant memory.
- Persist approved memory writes.
- Maintain owner-specific memory types.
- Preserve provenance, confidence, timestamps, and freshness.
- Resolve conflicts through documented priority rules.
- Reject low-value or low-confidence memory writes.
- Keep diagnostics separate from business truth.

### Ownership

Memory owns continuity state through explicit memory types.

It does not own business reasoning, workflow process logic, transformation schemas, or response rendering.

### Consumers

- Conversation Intelligence.
- Business Knowledge.
- Business Reasoning.
- Planner.
- Workflow.
- Transformation.
- Response Intelligence.
- Developer diagnostics.

## Transformation

### Purpose

Transformation converts messy input into structured business outputs.

### Inputs

- Raw user input.
- File, image, or document references.
- `ConversationFrame`.
- `KnowledgeContext`.
- `ReasoningDecision`.
- `PlannerDecision`.
- Workflow requirements.
- Target schema.
- Memory context.
- Optional LLM output.

### Outputs

- `TransformationResult`.
- Extracted entities.
- Normalized records.
- Generated drafts.
- Validation results.
- Source provenance.
- Confidence.
- Correction requirements.
- Diagnostics.

### Responsibilities

- Extract fields from raw text, files, images, or documents.
- Normalize entities into business schemas.
- Generate structured business outputs such as product records, plans, scripts, reports, dashboard cards, and summaries.
- Validate output shape against skill or workflow requirements.
- Preserve source provenance.
- Identify correction needs.

### Ownership

Transformation owns structured output derived from raw input.

It does not own workflow process, permanent memory persistence, business rule definition, LLM generation policy, or final presentation.

### Consumers

- Workflow.
- Memory.
- Response Intelligence.
- Planner.
- LLM Adapter.
- Developer diagnostics.

## Response Intelligence

### Purpose

Response Intelligence decides what the user should receive and produces one response envelope for the turn.

### Inputs

- `ConversationFrame`.
- `KnowledgeContext`.
- `ReasoningDecision`.
- `PlannerDecision`.
- `WorkflowState`.
- Memory context.
- `TransformationResult`.
- LLM output.
- Fallback status.
- Diagnostics from all engines.

### Outputs

- `ResponseEnvelope`.
- Final owner-facing text.
- Response source.
- Follow-up question.
- Confidence.
- Rendering guidance.
- Aggregated diagnostics.

### Responsibilities

- Select the highest-priority valid response source.
- Prevent duplicate, empty, stale, repetitive, or conflicting responses.
- Preserve active workflow prompts and results.
- Compose owner-friendly final text.
- Include assumptions, confidence, and follow-up when needed.
- Produce one response envelope for UI rendering.

### Ownership

Response Intelligence owns final response selection and rendering guidance.

It does not own workflow process, memory persistence, business knowledge, or raw LLM generation.

### Consumers

- UI rendering layer.
- Conversation Memory.
- Business Memory when response outcome is approved for persistence.
- Developer diagnostics.

## LLM Adapter

### Purpose

The LLM Adapter provides a controlled boundary between V5 architecture and LLM execution.

### Inputs

- Prepared prompt context.
- `ConversationFrame`.
- Relevant `KnowledgeContext`.
- `ReasoningDecision`.
- `PlannerDecision`.
- Memory excerpts.
- Workflow state summary.
- Transformation context.
- Response style constraints.
- Safety and capability constraints.

### Outputs

- LLM draft.
- Extracted or classified fields when requested.
- Natural-language explanation.
- Confidence or uncertainty signal when available.
- Token and model diagnostics.
- Error or fallback status.

### Responsibilities

- Call the selected LLM or model provider.
- Enforce prompt boundaries and context constraints.
- Return structured results when requested.
- Preserve model, token, and error diagnostics.
- Avoid becoming a hidden source of business truth.
- Allow deterministic engines to validate and prioritize output.

### Ownership

The LLM Adapter owns model execution and provider interaction.

It does not own architecture, business state, workflow state, memory truth, final response priority, or UI rendering.

### Consumers

- Transformation.
- Response Intelligence.
- Business Reasoning when LLM-assisted reasoning is explicitly planned.
- Planner.
- Developer diagnostics.
