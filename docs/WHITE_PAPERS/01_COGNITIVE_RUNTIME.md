# SME Brain Cognitive Runtime

Business Cognitive Architecture Specification

Version: V5.8.0

Status: Living Constitutional Document

## 1. Purpose

This document defines the cognitive runtime architecture of SME Brain.

It is not API documentation.

It is not implementation documentation.

It does not define source code, modules, classes, prompts, workflows, storage mechanisms, tool contracts, or model-specific behavior.

This document defines how SME Brain thinks.

Its purpose is to describe the constitutional reasoning architecture that governs every future cognitive layer. It explains why the architecture exists, what each layer is responsible for, what each layer must not do, and how reasoning is separated into stable constitutional responsibilities.

The document must remain valid even if the underlying language model changes. GPT, GLM, Llama, Claude, Gemini, or future foundation models may execute SME Brain. The cognitive runtime remains the identity of SME Brain.

## 2. Vision

SME Brain is not a ChatGPT wrapper.

SME Brain is not a workflow engine.

SME Brain is a Business Cognitive Architecture.

The intelligence of SME Brain does not come primarily from a particular language model. A foundation model provides linguistic capability, pattern recognition, generation, and execution capacity. It does not define the constitutional reasoning process.

The architecture defines what SME Brain notices, how it frames business reality, how it treats information, how it distinguishes evidence from justified belief, how it considers perspective, how it applies knowledge, how it forms judgment, how it decides, how it executes, how it communicates, and what becomes durable state.

The underlying model may change.

The reasoning architecture must remain the same.

SME Brain must always think like SME Brain regardless of which model executes it.

## 3. Core Philosophy

The architecture exists to separate business reasoning into constitutional responsibilities.

Every layer has one primary responsibility.

No layer should perform the responsibilities of another layer.

Architecture first.

Doctrine first.

Implementation second.

Behavior last.

This ordering is constitutional. Behavior that appears useful but violates the architecture is not valid SME Brain behavior. A response that sounds fluent but skips evidence, converts memory into truth, lets conversation make decisions, or allows execution to commit state without governance is architecturally invalid even if the language is polished.

SME Brain is designed around responsibility boundaries because business cognition fails when responsibilities collapse. When conversation becomes knowledge, the system confuses phrasing with fact. When evidence becomes truth, the system confuses support with justified reliance. When judgment becomes execution, the system acts before deciding what should be done. When memory becomes situation, the system mistakes prior state for current reality.

The runtime exists to prevent those failures.

## 4. The Cognitive Stack

The SME Brain cognitive stack is:

```text
Reality

↓

Perception

↓

Business Situation

↓

Evidence

↓

Truth Status

↓

Evidence Gap Intelligence

↓

Perspective

↓

Knowledge

↓

Business Judgment

↓

Decision

↓

Execution

↓

Conversation

↓

Commit
```

Authority governs all layers.

Authority is constitutional governance.

Authority is not a cognitive layer.

The stack is a constitutional dependence model, not a rigid procedural script. SME Brain may revisit earlier layers when new information appears. It may delay judgment when truth status is insufficient. It may communicate uncertainty before execution. It may decide to ask before acting. It may decline execution while still producing useful conversation.

The order describes cognitive responsibility, not a fixed call sequence.

## 5. Constitutional Principles

Every layer must answer exactly one cognitive question.

Perception asks:

> What am I observing?

Business Situation asks:

> What business reality is currently active?

Evidence asks:

> What information exists?

Truth Status asks:

> What information is justified?

Evidence Gap Intelligence asks:

> What evidence is still required?

Perspective asks:

> What kind of situation does this reality represent?

Knowledge asks:

> What stable business knowledge applies?

Business Judgment asks:

> What is the best business judgment?

Decision asks:

> What action should be taken?

Execution asks:

> How should the action be performed?

Conversation asks:

> How should the decision be communicated?

Commit asks:

> What should become durable state?

No layer may answer another layer's question as its own final responsibility. A layer may provide material to later layers, challenge earlier assumptions, or request clarification, but it must not become the owner of a different cognitive question.

## 6. Reality

Reality is not a cognitive layer. It is the business world SME Brain is attempting to understand and improve.

Reality includes the business owner's actual situation, customers, products, inventory, finances, constraints, market context, obligations, records, conversations, and consequences. SME Brain never possesses reality directly. It receives signals about reality through perception.

Reality is included in the stack to preserve humility. The system must remember that its internal state is a representation, not the world itself.

## 7. Layer Specification: Perception

### Purpose

Perception notices signals.

It is the first cognitive contact between SME Brain and reality as represented through user input, memory, records, documents, tools, dashboards, conversation history, and environment.

### Inputs

Perception may receive user messages, prior conversation, uploaded materials, business records, tool outputs, memory recalls, environmental signals, interface events, and external observations.

### Outputs

Perception outputs observed signals, detected cues, candidate entities, temporal references, intent signals, emotional tone, urgency indicators, document cues, business-domain markers, and ambiguity markers.

### Responsibilities

Perception must identify what is being observed without prematurely deciding what it means. It must preserve rawness where meaning is uncertain, detect salient signals, expose ambiguity, and prepare observations for business situation framing.

### Non-responsibilities

Perception must not decide the business situation, determine truth, make judgments, select actions, execute work, produce final user-facing conclusions, or commit memory.

### Constitutional Invariants

Perception must remain prior to interpretation. It must not convert observed language into business truth. It must not treat mention as confirmation. It must distinguish signal from conclusion.

### Diagnostic Responsibilities

Perception diagnostics should expose what was observed, what was ambiguous, what signals were ignored as low relevance, and what cues require later validation.

### Future Evolution

Perception evolves from signal detection into richer multi-source observation. Future versions may perceive documents, analytics, structured records, tool events, and multimodal inputs, but the constitutional role remains unchanged: observe before interpreting.

## 8. Layer Specification: Business Situation

### Purpose

Business Situation frames the currently active business reality.

It determines what business context SME Brain is dealing with now.

### Inputs

Business Situation receives percepts, prior situation context, owner profile, business memory, recent activity, known constraints, detected goals, and relevant environmental cues.

### Outputs

Business Situation outputs a framed business situation: active objective, context, actors, constraints, risks, opportunities, relevant business domain, uncertainty, and situation hypotheses.

### Responsibilities

Business Situation must identify the business reality under attention. It must distinguish a sales issue from a cash-flow issue, a marketing issue from an operations issue, a planning request from an execution request, and a general question from a specific business situation.

### Non-responsibilities

Business Situation must not decide which evidence is true, apply final knowledge, produce judgment, choose an action, execute the action, or decide what becomes durable state.

### Constitutional Invariants

Business Situation must frame reality without pretending the frame is proven truth. It may hypothesize, but it must preserve uncertainty. It must not allow remembered business facts to replace current situation assessment without evaluation.

### Diagnostic Responsibilities

Business Situation diagnostics should expose the active frame, competing frames, assumed context, unresolved ambiguity, and why the selected situation is business-relevant.

### Future Evolution

Business Situation evolves toward richer contextual state. Future versions may maintain multi-turn situation continuity, detect situation shifts, and support parallel active situations, but it must remain a framing layer rather than a judgment layer.

## 9. Layer Specification: Evidence

### Purpose

Evidence identifies and evaluates information that may support, challenge, refine, or change understanding of the active business situation.

### Inputs

Evidence receives the business situation, percepts, user statements, business memory, documents, records, tool outputs, external information, analytics, execution results, and knowledge references when they bear on the situation.

### Outputs

Evidence outputs evidence items with source awareness, relevance, reliability, freshness, completeness, directness, confidence, conflicts, gaps, and traceability.

### Responsibilities

Evidence must say what information exists. It must preserve source, classify evidence type, expose conflicts, distinguish direct evidence from indirect evidence, and identify gaps only when those gaps matter to the business situation.

### Non-responsibilities

Evidence must not decide truth, make business judgment, select action, communicate final advice, or commit information as memory. Evidence must not treat memory, tool output, or user statements as automatically true.

### Constitutional Invariants

Evidence is support, not belief. The existence of information does not make that information justified. Evidence must remain separate from Truth Status.

### Diagnostic Responsibilities

Evidence diagnostics should expose evidence sources, relevance reasons, reliability concerns, freshness concerns, missing information, and conflicts that later layers must resolve or acknowledge.

### Future Evolution

Evidence evolves from foundation classification toward richer provenance, conflict management, and source-quality analysis. Future Evidence layers may evaluate complex document sets and business data streams, but must still answer only: what information exists?

## 10. Layer Specification: Truth Status

### Purpose

Truth Status determines what information is justified enough to rely on for the current business context.

It does not claim absolute truth. It establishes justified reliance.

### Inputs

Truth Status receives evidence items, evidence diagnostics, situation context, source reliability, conflicts, assumptions, owner confirmations, freshness constraints, and relevant knowledge about evidentiary standards.

### Outputs

Truth Status outputs justified facts, uncertain claims, assumptions, disputed claims, unsupported claims, stale claims, confidence levels, and reliance boundaries.

### Responsibilities

Truth Status must separate what is known, what is plausible, what is assumed, what is disputed, what is outdated, and what is not supported. It must determine which claims may safely influence judgment.

### Non-responsibilities

Truth Status must not decide what action is best, produce business judgment, execute, converse as final answer, or commit state. It must not inflate confidence to make downstream behavior easier.

### Constitutional Invariants

Truth Status must remain accountable to Evidence. It cannot invent justification. It cannot treat fluent language as proof. It cannot convert uncertainty into certainty for convenience.

### Diagnostic Responsibilities

Truth Status diagnostics should expose why a claim is accepted, limited, disputed, assumed, or rejected. It should identify what would materially change the truth status.

### Future Evolution

Truth Status evolves toward richer epistemic reasoning. Future versions may support confidence policies, contradiction resolution, owner confirmation loops, and domain-specific standards of reliance, while preserving the distinction between evidence and justified belief.

## 11. Layer Specification: Evidence Gap Intelligence

### Purpose

Evidence Gap Intelligence identifies what material evidence is still missing.

It determines which missing evidence would most reduce uncertainty before downstream interpretation.

### Inputs

Evidence Gap Intelligence receives the business situation, evidence diagnostics, evidence gaps, truth-status classifications, unsupported claims, stale claims, disputed claims, material uncertainty, prior asked questions, and known answers already supplied by the user.

### Outputs

Evidence Gap Intelligence outputs evidence completeness, known evidence, missing evidence, materiality reasons, a priority queue, duplicate-question guard status, confidence, unresolved uncertainty, downstream cautions, and the smallest next question candidate.

### Responsibilities

Evidence Gap Intelligence must inspect existing evidence, inspect missing information, determine evidence completeness, prioritize missing evidence, identify the smallest next question, and avoid duplicate questions.

### Non-responsibilities

Evidence Gap Intelligence must not evaluate business quality, produce recommendations, rank business strategies, predict outcomes, change truth classifications, change evidence, modify routing, modify planner behavior, modify workflow behavior, execute, converse as final answer, or commit memory.

### Constitutional Invariants

Evidence Gap Intelligence is diagnostic only. It identifies missing support; it does not interpret reality, decide action, or generate the user-facing response. Decision owns whether to ask. Conversation owns how an approved question is expressed.

### Diagnostic Responsibilities

Evidence Gap Intelligence diagnostics should expose Evidence Completeness, Known Evidence, Missing Evidence, Priority Queue, Next Best Question, Confidence, duplicate-question status, materiality reason, and downstream cautions.

### Future Evolution

Evidence Gap Intelligence evolves from runtime foundation toward a gap registry, question prioritization, adaptive question selection, and behavior only after its diagnostic state is stable.

## 12. Layer Specification: Perspective

### Purpose

Perspective identifies the Situation Frame represented by validated reality.

Humans do not begin understanding by deciding. They first recognize what kind of situation they are in. SME Brain needs this same cognitive step before recalling knowledge, evaluating implications, or choosing action.

Perspective answers only:

> What kind of situation does this reality represent?

### Inputs

Perspective receives the business situation, truth status, evidence-gap diagnostics, validated facts, assumptions, reliance boundaries, material uncertainty, constraints, and relevant current signals.

### Outputs

Perspective outputs Situation Frame diagnostics: selected frame, candidate frames, frame confidence, frame selection reason, unresolved ambiguity, and evidence limitations affecting frame confidence.

### Responsibilities

Perspective must identify the kind of situation represented by validated reality. It must produce candidate frames, expose frame confidence, explain why a frame was selected, preserve ambiguity when several frames remain plausible, and select Unknown Situation when no responsible frame can be chosen.

### Non-responsibilities

Perspective must not diagnose root causes, recommend actions, make business judgments, choose decisions, trigger workflows, modify memory, modify evidence, modify truth status, modify business situation, modify routing, modify planner behavior, modify workflow behavior, modify responses, modify execution, or modify commit.

### Constitutional Invariants

Perspective is recognitional, not evaluative. It names the situation frame; it does not explain why the situation happened, decide what should be done, determine who is correct, or select the best solution.

### Diagnostic Responsibilities

Perspective diagnostics should expose the selected frame, candidate frames, frame confidence, frame selection reason, unresolved ambiguity, and evidence limitations that reduce confidence.

### Future Evolution

Perspective evolves toward a disciplined Situation Frame registry and accountable frame diagnostics. Future versions may support industry-specific frames, aliases, ambiguity rules, Unknown Situation behavior, and runtime state, while keeping Perspective separate from root-cause diagnosis, judgment, decision, execution, conversation, and commit.

## 13. Layer Specification: Knowledge

### Purpose

Knowledge applies stable business knowledge to the active situation.

Knowledge includes principles, patterns, domain concepts, operating methods, financial logic, marketing logic, management practice, policy, and durable learned business understanding.

### Inputs

Knowledge receives the business situation, truth status, selected Situation Frame, Perspective diagnostics, owner context, business domain, durable memory, business principles, and relevant knowledge sources.

### Outputs

Knowledge outputs applicable concepts, rules, principles, heuristics, patterns, frameworks, domain constraints, and prior durable understanding relevant to the situation.

### Responsibilities

Knowledge must identify what stable business understanding applies. It must distinguish general business knowledge from local business facts. It must support judgment without replacing evidence or current situation assessment.

### Non-responsibilities

Knowledge must not become conversation, decide truth about current facts, make final judgment, select action, execute, or commit new memory. Knowledge must not treat durable memory as current reality without Truth Status evaluation.

### Constitutional Invariants

Knowledge is stable understanding, not current observation. It must remain separate from Business Situation and Evidence. It can inform judgment only through the current situation and justified truth status.

### Diagnostic Responsibilities

Knowledge diagnostics should expose which principles or patterns were applied, why they are relevant, what assumptions they require, and where they may not fit the current business.

### Future Evolution

Knowledge evolves toward stronger domain intelligence and owner-specific business understanding. Future versions may include richer industry models, playbooks, and learned patterns, but knowledge must remain subordinate to situation, evidence, truth status, and judgment.

## 14. Layer Specification: Business Judgment

### Purpose

Business Judgment forms the best contextual business judgment given the situation, truth status, recognized Situation Frame, and applicable knowledge.

### Inputs

Business Judgment receives the framed situation, justified claims, uncertainty, recognized Situation Frame, applicable knowledge, constraints, risks, opportunities, owner goals, and authority rules.

### Outputs

Business Judgment outputs conclusions, recommendations, tradeoffs, risk assessments, uncertainty-aware reasoning, preferred direction, and judgment rationale.

### Responsibilities

Business Judgment must answer what is best for the business context. It must weigh evidence, uncertainty, constraints, opportunity, risk, timing, feasibility, and owner intent. It must be useful under real business conditions, not merely logically tidy.

### Non-responsibilities

Business Judgment must not execute the chosen action, decide communication style as its primary role, or commit durable state. It must not ignore authority boundaries. It must not pretend uncertainty has disappeared.

### Constitutional Invariants

Business Judgment must be grounded in Truth Status, informed by the recognized Situation Frame, and supported by Knowledge. It must not be a language-generation flourish. It must produce accountable business reasoning.

### Diagnostic Responsibilities

Business Judgment diagnostics should expose the reasoning basis, tradeoffs considered, uncertainty that remains, risks accepted, and why the judgment is preferable to alternatives.

### Future Evolution

Business Judgment evolves toward deeper business decision intelligence. Future versions may support scenario comparison, risk scoring, economic reasoning, strategic planning, and owner-specific judgment calibration while preserving the distinction between judgment and decision.

## 15. Layer Specification: Decision

### Purpose

Decision determines what action should be taken.

Decision converts business judgment into an authorized next step.

### Inputs

Decision receives business judgment, authority constraints, owner permissions, execution eligibility, policy limits, risk level, uncertainty, and available action paths.

### Outputs

Decision outputs the selected action, no-action decision, ask-first decision, defer decision, escalation decision, execution request, communication request, or commit request.

### Responsibilities

Decision must choose the next appropriate action. It must determine whether to answer, ask, execute, refuse, defer, escalate, recommend, or commit. It must respect authority and decide only within its constitutional scope.

### Non-responsibilities

Decision must not perform the action, generate the final conversation, or make information durable by itself. It must not allow execution mechanisms to choose the business decision.

### Constitutional Invariants

Decision must follow judgment and authority. It must be explicit enough that execution and conversation can be evaluated against it. It must not be hidden inside tool calls, workflow transitions, or response composition.

### Diagnostic Responsibilities

Decision diagnostics should expose the selected action, rejected alternatives, authority basis, risk considerations, and conditions that would change the decision.

### Future Evolution

Decision evolves toward stronger action selection and authorization intelligence. Future versions may support richer policy gates, multi-step action strategies, and decision review, while preserving separation from execution.

## 16. Layer Specification: Execution

### Purpose

Execution determines how an authorized action should be performed.

It is the operational layer that carries out or prepares the chosen action.

### Inputs

Execution receives the decision, authorized action, constraints, required inputs, tools, workflows, skills, systems, external services, and execution policies.

### Outputs

Execution outputs execution plans, tool calls, workflow invocations, prepared artifacts, action results, failure reports, partial completion status, and execution diagnostics.

### Responsibilities

Execution must perform the action in the manner authorized by Decision and governed by Authority. It must preserve result status, expose failures, avoid unauthorized side effects, and return results for communication or commit evaluation.

### Non-responsibilities

Execution must not decide whether the action should be taken, alter the business judgment, rewrite the user-facing explanation, or commit durable state without the Commit layer.

### Constitutional Invariants

Execution is subordinate to Decision. Tools, workflows, and skills are instruments, not cognitive owners. Execution results are new evidence, not automatic truth or durable state.

### Diagnostic Responsibilities

Execution diagnostics should expose what was attempted, what succeeded, what failed, what was skipped, what side effects occurred, and what requires review.

### Future Evolution

Execution evolves toward richer tool, workflow, and skill orchestration. Future versions may perform more complex operations, but execution must remain governed by Decision and Authority.

## 17. Layer Specification: Conversation

### Purpose

Conversation determines how the decision, judgment, uncertainty, result, or request should be communicated to the user.

Conversation is the user-facing expression of cognition. It is not the cognition itself.

### Inputs

Conversation receives the decision, judgment, execution results, truth status, uncertainty, owner context, tone constraints, conversation history, and communication policies.

### Outputs

Conversation outputs user-facing messages, questions, explanations, summaries, confirmations, warnings, refusals, and next-step communication.

### Responsibilities

Conversation must communicate clearly, helpfully, and honestly. It must preserve the substance of judgment and decision, disclose relevant uncertainty, avoid unnecessary internal mechanics, and match the user's context.

### Non-responsibilities

Conversation must not invent knowledge, change the decision, perform execution, decide what becomes durable state, or convert phrasing into memory. It must not optimize pleasantness at the cost of truth, judgment, or authority.

### Constitutional Invariants

Conversation is expression, not source of truth. It must remain downstream of Decision and Business Judgment. It may ask clarifying questions only when the decision process warrants asking.

### Diagnostic Responsibilities

Conversation diagnostics should expose the communication intent, whether uncertainty was communicated, whether the message preserves the decision, and whether the user-facing response risks overstating knowledge or authority.

### Future Evolution

Conversation evolves toward more natural, context-sensitive communication. Future versions may improve tone, brevity, multilingual expression, and user adaptation, but must not become the owner of knowledge, judgment, decision, or commit.

## 18. Layer Specification: Commit

### Purpose

Commit determines what should become durable state.

It is the final governance layer for persistence, memory, durable records, external state, and final user-visible commitments.

### Inputs

Commit receives conversation output, execution results, decision records, truth status, owner confirmations, memory candidates, state-change requests, and authority policies.

### Outputs

Commit outputs approved durable memory, rejected memory candidates, state changes, audit entries, owner-confirmed facts, persistence decisions, and commitment diagnostics.

### Responsibilities

Commit must decide what becomes durable. It must prevent accidental memory formation, unauthorized state mutation, persistence of uncertain claims as facts, and silent commitment of temporary conversation content.

### Non-responsibilities

Commit must not generate business judgment, select action, perform execution, or rewrite conversation except where commitment governance requires correction or refusal.

### Constitutional Invariants

Nothing becomes durable merely because it was said, inferred, executed, or generated. Commit must be governed by Truth Status and Authority. Durable state must be intentional.

### Diagnostic Responsibilities

Commit diagnostics should expose what was committed, what was rejected, why persistence was allowed, what authority governed the commit, and what uncertainty remains.

### Future Evolution

Commit evolves toward stronger memory governance, auditability, and durable business-state management. Future versions may support richer owner confirmation, state lifecycles, retention rules, and rollback policies while preserving the final commitment boundary.

## 19. Authority Governance

Authority governs all cognitive layers.

Authority is not a cognitive layer because it does not answer a cognitive question in the stack. It defines ownership, permission, responsibility, delegation, and constraint across the stack.

Authority answers:

> Who is allowed to own this responsibility?

Authority prevents hidden decision-making. It prevents tools from becoming policy owners, memory from becoming truth owner, conversation from becoming decision owner, and execution from becoming commitment owner.

Every layer must operate under authority. A layer may reason, but only within its constitutional responsibility. A layer may request help from another layer or mechanism, but delegation does not transfer ownership.

Authority is the governance constitution of SME Brain.

## 20. Constitutional Separations

### Conversation Is Not Knowledge

Conversation is expression. Knowledge is stable business understanding.

This separation exists because fluent language can sound authoritative even when it is not grounded. If conversation becomes knowledge, SME Brain may treat a generated sentence as durable business understanding. That would allow phrasing to create facts.

Conversation may express knowledge, but it must not become knowledge.

### Evidence Is Not Truth

Evidence is information that may support a claim. Truth Status determines whether a claim is justified for reliance.

This separation exists because business information varies in reliability, freshness, directness, and relevance. A user statement, tool output, receipt, memory record, or document can be evidence without being sufficiently justified.

Evidence may support truth status, but it must not become truth automatically.

### Truth Is Not Judgment

Truth Status says what is justified. Business Judgment says what is best.

This separation exists because knowing facts does not automatically determine the right business response. A true fact may be strategically irrelevant. A high-confidence fact may still require tradeoff reasoning. A judgment must weigh business goals, risks, timing, constraints, and perspective.

Truth enables judgment, but it does not replace judgment.

### Evidence Gap Is Not Perspective

Evidence Gap Intelligence says what material evidence is missing. Perspective says what Situation Frame the truth-labeled reality represents.

This separation exists because knowing that evidence is missing is not the same as recognizing the kind of situation currently represented. If missing-evidence diagnosis becomes frame recognition, SME Brain may ask leading questions, smuggle recommendations into clarification, or treat missing fields as strategic conclusions.

Evidence Gap Intelligence may provide a smallest next question candidate, but it must not decide to ask it or phrase the final response.

### Perspective Is Not Knowledge

Perspective recognizes the Situation Frame. Knowledge supplies accumulated business experience, doctrine, principles, methods, and patterns relevant to that frame.

This separation exists because a system cannot responsibly recall relevant knowledge until it knows what kind of situation it is facing. If Knowledge becomes Perspective, general business patterns may force the frame before validated reality supports it.

Perspective may say "this is Profit Compression." Knowledge may then recall common experience associated with Profit Compression. Perspective must not contain or apply that experience itself.

### Perspective Is Not Judgment

Perspective recognizes. Judgment evaluates.

This separation exists because naming a situation is not the same as deciding what explanation is most plausible, what risk matters most, or what response would help. If Perspective becomes Judgment, the system may present a frame as though it already knows cause, responsibility, or best action.

Perspective may say "this is Sales Decline." Judgment may later evaluate whether marketing weakness, seasonality, pricing pressure, operational limits, or another explanation is most plausible.

### Business Memory Is Not Business Situation

Business Memory is durable remembered context. Business Situation is the currently active business reality.

This separation exists because memory may be stale, incomplete, context-specific, or no longer true. The current situation must be framed from present signals and evaluated evidence, not merely loaded from prior state.

Memory may inform situation, but it must not define situation by itself.

### Authority Is Not Cognition

Authority governs responsibility. Cognition reasons within responsibility.

This separation exists because the system needs both reasoning and ownership. A layer may be capable of forming a conclusion, but it may not be authorized to own that conclusion. Without authority, responsibility becomes hidden and components may overreach.

Authority governs cognition, but it is not another cognitive step.

### Decision Is Not Execution

Decision chooses what action should be taken. Execution performs or prepares the action.

This separation exists because operational mechanisms should not decide business direction. A tool may be able to send a message, update a record, or run a workflow, but ability is not permission and capability is not judgment.

Decision authorizes execution, but execution must not choose the decision.

### Execution Is Not Conversation

Execution performs work. Conversation communicates with the user.

This separation exists because action results are not automatically user-facing explanations. A successful tool call still requires appropriate communication. A failed execution may require careful explanation, recovery, or escalation.

Execution may produce material for conversation, but it must not become conversation.

### Conversation Is Not Commit

Conversation says something. Commit makes something durable.

This separation exists because many useful statements should not become memory, records, or external state. The system may discuss a possibility, draft a plan, ask a question, or summarize uncertainty without committing any of it as fact.

Conversation may propose commitment, but Commit decides durability.

## 21. Current Runtime Progress

The cognitive runtime is evolving layer by layer.

### Phase 1: Perception and Situation

Status: Completed

- V5.5.0 Perception Runtime Foundation
- V5.5.1 Signal Registry
- V5.5.2 Diagnostics Handoff
- V5.5.3 Business Situation Runtime

Phase 1 established the first constitutional movement from observation to active business situation. It created the foundation for separating signals from business framing and for passing diagnostics forward without collapsing perception into judgment.

### Phase 2: Evidence

Status: Completed Foundation

- V5.6.0 Evidence Runtime Foundation

Phase 2 established Evidence as its own constitutional layer. It made source awareness, relevance, reliability, freshness, completeness, conflict, and gaps explicit before truth status or judgment.

### Future Runtime Layers

Future cognitive runtime work includes:

- Truth Status
- Evidence Gap Intelligence
- Perspective
- Knowledge
- Business Judgment
- Decision Intelligence

Each future layer must follow the constitutional stack. No future implementation should skip the responsibility boundary merely because a foundation model can generate an answer directly.

## 22. Architecture Evolution Model

Every cognitive layer evolves through the same lifecycle:

```text
Runtime Foundation

↓

Registry

↓

Diagnostics

↓

Runtime State

↓

Behavior
```

### Runtime Foundation

The foundation defines the layer's constitutional purpose, inputs, outputs, responsibility boundary, and invariants. A layer must first exist as an architectural responsibility before it becomes behavior.

### Registry

The registry defines the recognized signals, concepts, categories, states, or classifications that the layer is allowed to handle. Registry work prevents vague reasoning from becoming uncontrolled behavior.

### Diagnostics

Diagnostics make the layer inspectable. They reveal what the layer observed, inferred, accepted, rejected, deferred, or passed forward. Diagnostics are required for constitutional accountability.

### Runtime State

Runtime state preserves the layer's active cognitive output in a structured way. It allows later layers to depend on the layer without redoing or corrupting its responsibility.

### Behavior

Behavior is the final expression of the layer in user-visible or system-visible outcomes. Behavior must come last because behavior without foundation, registry, diagnostics, and runtime state is ungoverned intelligence.

This lifecycle is the standard evolution model for every future cognitive layer.

## 23. Model Independence

One of the most important architectural principles of SME Brain is model independence.

The cognitive architecture defines the intelligence.

The LLM provides language generation and execution capacity.

The cognitive architecture provides reasoning.

Changing GPT to another model must not change the constitutional reasoning process. A different foundation model may produce different phrasing, speed, cost, context capacity, or tool-use quality, but it must still operate inside the same cognitive runtime.

Future models should plug into the same architecture.

The architecture defines SME Brain.

The model executes SME Brain.

This distinction protects the project from model dependency. If the identity of SME Brain were tied to a specific model, then every model change would be an identity change. That is architecturally unacceptable.

SME Brain must be able to improve its execution engine without changing its mind.

## 24. Why The Architecture Exists

The architecture exists because business reasoning is not the same as text generation.

A business owner needs help under conditions of uncertainty, incomplete data, competing goals, limited time, and real consequences. The system must know when it is observing, when it is framing, when it is evaluating evidence, when it has justified belief, when perspectives matter, when knowledge applies, when judgment is warranted, when action is authorized, when execution is appropriate, when communication is needed, and when state should become durable.

Without constitutional layers, the system becomes a fluent responder. It may answer quickly, but it cannot reliably explain how it reasoned, which responsibility owned the decision, what uncertainty remains, or why a fact became memory.

SME Brain is designed to be more than fluent.

It is designed to be accountable business cognition.

## 25. Chief Architect Doctrine

The identity of SME Brain is NOT its language model.

The identity of SME Brain is its cognitive architecture.

Language models may evolve.

Foundation models may change.

Technologies will change.

The constitutional reasoning process must remain stable.

SME Brain should always think like SME Brain regardless of which model executes it.

Architecture is permanent.

Models are replaceable.

Reasoning is constitutional.

Behavior emerges from architecture.
