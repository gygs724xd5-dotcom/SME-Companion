# SME Companion V5 Architecture

## Target Pipeline

```text
User
  |
  v
Conversation Intelligence
  |
  v
Business Knowledge
  |
  v
Business Reasoning
  |
  v
Planner
  |
  v
Workflow
  |
  v
Memory
  |
  v
Response Intelligence
  |
  v
Transformation
  |
  v
LLM
```

This is the target conceptual architecture for V5. Runtime implementation may still contain V4 compatibility paths while components are migrated.

## User

The user is the business owner, staff member, or operator using SME Companion to run practical business tasks. User input may be a question, instruction, document, receipt, product detail, customer message, decision request, workflow continuation, correction, or feedback.

The user layer provides:

- Raw message text.
- Uploaded files or images.
- Selected quick actions.
- Store context.
- Active UI surface.
- Permission boundaries.

## Conversation Intelligence

Conversation Intelligence interprets the turn before business execution.

Responsibilities:

- Normalize the message.
- Detect conversation act: question, command, correction, continuation, cancellation, confirmation, interruption, or feedback.
- Resolve references such as "this product", "that customer", or "continue".
- Identify whether an active workflow owns the turn.
- Detect ambiguity and missing context.
- Produce a conversation frame for downstream components.

Conversation Intelligence should not generate the final business answer. It prepares the turn.

## Business Knowledge

Business Knowledge maps the conversation frame to business domains, skills, doctrine, examples, and operating concepts.

Responsibilities:

- Select candidate business domains.
- Rank relevant business skills.
- Load skill standards and business rules.
- Provide domain vocabulary and required entities.
- Attach examples and response guidance.
- Expose tool and workflow requirements.

Business Knowledge is the structured business brain of the system.

## Business Reasoning

Business Reasoning decides what the request means in business terms.

Responsibilities:

- Interpret intent using domains, skills, entities, state, and memory.
- Identify business goal, risk, stage, and decision type.
- Determine known facts, missing facts, and assumptions.
- Apply business rules and reasoning patterns.
- Recommend response mode and next action.

Business Reasoning is not keyword matching. It reasons from business context and produces an explainable recommendation.

## Planner

The Planner converts reasoning into an execution plan.

Responsibilities:

- Decide whether to answer, ask, start workflow, continue workflow, use tool, transform input, retrieve memory, or call LLM.
- Select primary and fallback paths.
- Set confidence and diagnostics.
- Respect active workflow locks and user interruptions.
- Produce a plan that can be audited before execution.

The Planner is the orchestration layer. It should not own domain rules or final wording.

V5.1.4 introduced `PlannerContext` as a bridge layer between V5 runtime context and the existing V4 planner. The adapter packages selected domain, selected skill, business goal, decision type, workflow state, planner inputs, hints, constraints, confidence, and diagnostics for developer visibility.

V5.2.0 Phase 1 is the first runtime planner migration. The existing planner now reads available V5 `KnowledgeContext`, `ReasoningContext`, and `PlannerContext` objects through a migration layer before falling back to the V4 planner logic. The priority order is:

1. `KnowledgeContext`
2. `ReasoningContext`
3. `PlannerContext`
4. Existing V4 planner fallback

The migration layer normalizes selected domain, selected skill, business goal, decision type, and confidence into V4-compatible planner hints. It does not replace the legacy route object, planner output schema, workflow behavior, UI behavior, response wording, memory behavior, or transformation behavior.

The planner migration exposes diagnostics under `diagnostic_groups["Planner Migration"]`, including runtime source, runtime version, whether V5 context was used, whether legacy fallback was used, selected domain, selected skill, business goal, decision type, confidence, and reason.

## Workflow

Workflow manages structured business processes across turns.

Responsibilities:

- Start workflows from planner decisions or explicit user actions.
- Collect required fields.
- Validate completeness.
- Pause, resume, cancel, complete, or chain workflows.
- Emit workflow state and next required action.
- Write completion memory through the memory layer.

Workflow is responsible for process continuity, not general chat.

## Memory

Memory stores state required for continuity.

Responsibilities:

- Maintain conversation state and transcript references.
- Persist business facts with ownership and provenance.
- Store workflow progress.
- Store transformation history and outputs.
- Track knowledge use and learning opportunities.
- Expose retrieval results with freshness and confidence.

Memory should be read and written through explicit contracts.

## Response Intelligence

Response Intelligence decides what the user should receive.

Responsibilities:

- Prioritize workflow prompts, direct answers, reasoning results, LLM output, fallbacks, and safeguards.
- Prevent repetitive, empty, unsafe, or low-value responses.
- Enforce owner-friendly style.
- Compose a response envelope with source, confidence, follow-up, and diagnostics.
- Ensure the final answer matches the current turn and active workflow state.

Response Intelligence owns the final response before rendering.

## Transformation

Transformation converts messy input into structured business outputs.

Responsibilities:

- Turn conversation into records, plans, scripts, documents, dashboards, summaries, and reports.
- Normalize extracted entities into business schemas.
- Prepare structured context for tools or LLMs.
- Validate output shape against target skill or workflow requirements.
- Preserve source provenance.

Transformation can happen before or after LLM use depending on the task, but the V5 architecture treats it as a first-class layer.

## LLM

The LLM is a generation and reasoning aid used when deterministic business logic is insufficient or natural language synthesis is needed.

Responsibilities:

- Generate owner-facing language from prepared context.
- Rewrite or improve structured drafts.
- Explain reasoning in natural language.
- Assist with extraction or classification when confidence warrants it.

The LLM receives constrained context from the Planner, Memory, Business Knowledge, Reasoning, Workflow, and Transformation layers. It should not be the only source of truth.

## Response Boundary

Every turn should end with a `ResponseEnvelope` conceptually containing:

- Final text.
- Response source.
- Domain and skill.
- Workflow state.
- Memory reads and writes.
- Reasoning summary.
- Confidence.
- Fallback path if used.
- Developer diagnostics.
