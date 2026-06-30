# V5 Glossary

## Purpose

This glossary defines official SME Companion V5 architecture terminology. These terms should be used consistently across documentation, implementation planning, reviews, and migration work.

## Terms

### AI-First Business Operating System

The V5 product model where AI coordinates business understanding, reasoning, workflow, memory, transformation, and response. It is not a chatbot attached to business tools.

### Business Doctrine

The architectural and business principles that guide system behavior. Doctrine defines how V5 should interpret requests, preserve ownership, reason about business meaning, use memory, and evolve safely.

### Business Knowledge

The structured business brain of the system. It contains domains, skills, rules, examples, workflow links, response guidance, and reasoning patterns.

### Business Rule

A rule that constrains or guides business behavior. Examples include protecting margin, not inventing missing costs, asking for required fields, and disclosing assumptions.

### Business Skill

A specific business capability with a canonical definition. A skill includes intent, required entities, required memory, rules, reasoning pattern, workflow integration, response style, confidence rules, and diagnostics.

### Canonical Object

A standard object used across engines to carry state, decisions, context, or results. Canonical objects prevent hidden state and unclear ownership.

### Confidence

The system's assessed reliability for a match, decision, extraction, memory item, workflow action, or response. Confidence should consider clarity, completeness, memory freshness, rule conflicts, and tool availability.

### Conversation

The user's interaction with SME Companion across one or more turns. A conversation may include questions, commands, corrections, confirmations, interruptions, files, workflow continuation, and feedback.

### ConversationFrame

The canonical object produced by Conversation Intelligence for a user turn. It contains normalized message data, conversation act, resolved references, candidate entities, ambiguity flags, and diagnostics.

### Conversation Intelligence

The engine that interprets the user turn before business execution. It frames the conversation but does not render the final response.

### Diagnostics

Structured information that explains system behavior. Diagnostics may include routing, skill selection, memory use, workflow transitions, planner decisions, LLM use, transformation provenance, confidence, and fallback reasons.

### Domain

A major business area owned by V5 Business Knowledge, such as Products, Inventory, Sales, Pricing, Accounting, Workflow, Reasoning, or Executive Intelligence.

### Engine

A V5 architectural component with a defined purpose, inputs, outputs, responsibilities, ownership, and consumers.

### Fallback

A controlled response or path used when the preferred path is unavailable, incomplete, low confidence, invalid, or unsafe. A fallback should be useful and specific, not generic.

### KnowledgeContext

The canonical object produced by Business Knowledge. It contains candidate domains, candidate skills, required entities, required memory, rules, reasoning patterns, response guidance, and diagnostics.

### LLM Adapter

The engine boundary for model execution. It calls the selected LLM or provider and returns drafts, structured outputs, or diagnostics. It does not own architecture or business truth.

### Memory

The V5 continuity layer. Memory preserves useful business state across turns, sessions, workflows, and transformations. It should store facts with owner, source, confidence, timestamp, and freshness rules.

### Memory With Purpose

The doctrine that memory should store only information that improves future business behavior. V5 should not persist every detail by default.

### One Owner Per State

The ownership rule that every important state has a single canonical owner. This prevents conflicting writes, stale copies, and unclear behavior.

### One Response Per Turn

The response rule that each user turn produces one final `ResponseEnvelope`. Engines may contribute, but they should not independently render competing final answers.

### Owner

The engine or memory type responsible for creating, updating, and validating a state or object.

### Planner

The orchestration engine that converts reasoning into an execution decision. It decides whether to answer, ask, start or continue workflow, transform input, retrieve memory, use a tool, call the LLM, or fallback.

### PlannerDecision

The canonical object produced by the Planner. It defines the primary action, engine path, fallback path, workflow action, memory actions, LLM action, response expectation, confidence, and diagnostics.

### Reasoning

The process of interpreting business meaning, applying rules, identifying known and missing facts, assessing risk, and recommending the next action.

### ReasoningDecision

The canonical object produced by Business Reasoning. It contains the business goal, decision type, selected domain and skill, known facts, missing facts, assumptions, recommended action, confidence, and diagnostics.

### Response Envelope

The canonical final response object for one turn. It contains final text, source, domain, skill, confidence, workflow summary, memory summary, reasoning summary, follow-up, rendering hints, and diagnostics.

### Response Intelligence

The engine that owns final response selection, composition, priority, and rendering guidance. It ensures the user receives one coherent answer.

### Skill

Short form of Business Skill. A skill is narrower than a domain and represents a specific business capability.

### Source Of Truth

The canonical place where a fact, state, object, or decision is owned. Consumers may read the source of truth but should not create competing versions.

### Store Memory

The memory type that owns durable store profile facts such as store name, business type, channels, location, operating model, and owner-defined preferences.

### Transformation

The engine process that converts messy input into structured business output, such as records, plans, scripts, documents, summaries, dashboard cards, reports, or extracted fields.

### TransformationResult

The canonical object produced by Transformation. It contains structured output, target schema, validation status, confidence, provenance, correction needs, and diagnostics.

### V4 Compatibility

The migration principle that V5 must preserve existing V4 behavior while new architecture owners are introduced through adapters, registries, or compatibility paths.

### Workflow

A durable business process that can span turns. Workflows collect fields, validate completeness, pause, resume, complete, cancel, fail, or chain into another workflow.

### Workflow State

The current canonical process state for a workflow instance. It includes status, collected fields, missing fields, validation state, next action, transitions, and diagnostics.

### WorkflowState

The canonical object owned by Workflow. It represents active or historical workflow process state.
