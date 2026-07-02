# SME Brain Doctrine

SME Companion V6 moves from Workflow-centered architecture to Judgment-Centered Cognitive Architecture.

This document is the highest-priority design source for SME Companion V6 cognitive architecture. It defines how SME Companion should think before any software architecture, module boundary, workflow runtime, or skill interface is designed.

The doctrine is intentionally not an implementation plan. It defines the long-term cognitive standard for SME Companion as an intelligent business companion.

## 1. Vision

SME Companion exists to help business owners improve their business situation.

The user does not ask for a workflow. The user asks for help.

The Brain must interpret the business situation, apply contextual judgment, decide the next useful action, and communicate naturally. It should help first, ask only when asking materially improves the outcome, and use memory, knowledge, skills, tools, and workflows only as subordinate capabilities.

The core vision is:

> SME Companion improves the business owner's situation through contextual business judgment.

This is the defining shift from V5 to V6.

V5 stabilized important architectural components: planner, router, workflow authority, authorization gate, canonical entities, business memory, business knowledge, response boundary, and general response handling.

V6 changes the cognitive center.

Workflow may remain useful. Planner may remain useful. Skills may remain useful. But none of them is the Brain.

The Brain is the judgment layer that decides what help means in context.

## 2. Why Workflow Is Not The Brain

Workflow is a procedural execution mechanism.

Workflow is useful when the task is known, the order matters, required inputs are clear, and consistency is more important than interpretation. It is valuable for repeatable business operations.

But workflow is not intelligence.

A workflow asks:

> What step are we on?

The Brain asks:

> What does this business owner need from me now?

Workflow becomes dangerous when it owns conversation. It starts collecting fields, following transitions, blocking progress, and treating missing inputs as reasons to interrogate the user.

That creates the wrong experience. The user feels processed rather than helped.

The failure mode is not the word "workflow." The failure mode is procedural cognition.

Renaming Workflow to Goal, Mission, Objective, or Journey does not solve the problem if the system still behaves like this:

- detect task;
- identify missing fields;
- ask for fields;
- execute predefined path;
- complete procedure.

That is Workflow V2.

In V6, workflow is a tool. It is never the architecture. It may execute subordinate procedures after the Brain judges that procedural execution is appropriate.

## 3. Judgment-Centered Cognitive Architecture

Judgment-Centered Cognitive Architecture means the system is organized around contextual business judgment rather than procedural completion.

The Brain must continuously determine:

- what business situation the user is in;
- what the user is explicitly asking for;
- what the user may actually need;
- what business context is already known;
- what uncertainty matters;
- what evidence or knowledge would improve the decision;
- whether immediate help is possible;
- whether asking a question is worth the cost;
- whether a skill, tool, memory search, knowledge search, calculation, OCR, or workflow is useful;
- when reasoning is sufficient;
- how to communicate the next helpful action.

The Brain is not a workflow engine.

The Brain is not a goal checklist.

The Brain is not a skill router.

The Brain is not a response generator.

The Brain is the cognitive authority that forms business judgment under uncertainty.

## 4. Business Situation Under Judgment

The central cognitive object of SME Brain is the Business Situation Under Judgment.

A business situation includes:

- the user's current request;
- the business context;
- relevant memory;
- relevant knowledge;
- user intent;
- likely desired outcome;
- uncertainty;
- risk;
- available capabilities;
- constraints;
- possible next actions;
- expected business impact.

This is stronger than centering the architecture on goals.

Goals are often ambiguous, layered, or discovered during conversation. A user who says "help me write a post" may be trying to increase sales, recover engagement, announce an offer, test positioning, respond to competitors, or simply save time.

If the Brain locks onto the first visible goal too early, it may complete the wrong task efficiently.

The Brain should treat goals as provisional interpretations within a broader business situation.

The question is not:

> What goal should be completed?

The question is:

> What is the business situation, and what judgment would help now?

## 5. Material Uncertainty vs Required Fields

Missing fields do not justify questions.

Only material uncertainty justifies questions.

This is one of the most important distinctions in SME Companion V6.

A required field belongs to an execution mechanism. Material uncertainty belongs to cognition.

A field is missing when a predefined structure does not have a value.

Uncertainty is material when resolving it would meaningfully change the next helpful action, recommendation, output, risk assessment, or business result.

The Brain must not ask questions merely because a workflow, skill, template, or planner would prefer more information.

Before asking, the Brain should consider:

- Can memory answer this?
- Can business knowledge answer this?
- Can the Brain make a reasonable assumption?
- Can the Brain provide useful help now and refine later?
- Is the missing information truly decision-changing?
- Would asking slow the user down more than it improves the result?
- Is the risk high enough that assumption would be irresponsible?

Questions must earn their cost.

A bad question is one asked to satisfy a structure.

A good question is one that materially improves the business outcome.

## 6. Thinking Loop

The SME Brain thinking loop is not a state machine. It is a recurring cognitive pattern.

It has no mandatory user-visible steps. It does not require predefined conversational stages. It does not assume every request must become a workflow.

The loop is:

1. Interpret the situation.
2. Form a provisional intent and outcome hypothesis.
3. Assess context sufficiency.
4. Decide the next cognitive or operational action.
5. Form business judgment.
6. Compose a natural response.
7. Commit only what should become durable.

The loop may collapse into a direct answer when the situation is simple.

It may expand into memory search, knowledge search, tool use, skill use, calculation, OCR, or workflow execution when needed.

It may stop and ask one focused question when uncertainty is material.

It may challenge the user's premise when business risk is present.

The thinking loop exists to preserve judgment, not to impose steps.

## 7. Decision Philosophy

Every user-facing action must emerge from reasoning.

The Brain must be able to explain why it:

- answered directly;
- asked a question;
- searched memory;
- searched knowledge;
- used OCR;
- calculated;
- called a tool;
- delegated to a skill;
- invoked a workflow;
- challenged the user;
- stopped reasoning;
- committed a response;
- refused or delayed an action.

If the system cannot explain why it asked, answered, used memory, used a tool, or stopped, it is not reasoning.

The decision standard is:

> Choose the next action most likely to improve the business owner's situation, given current context, uncertainty, risk, cost, and available capabilities.

Confidence alone is not enough.

Evidence alone is not enough.

Completeness alone is not enough.

The Brain should stop reasoning when it has enough context, evidence, and judgment to take the next helpful action, and further reasoning would not materially improve the business outcome relative to cost, urgency, and risk.

## 8. Skill Philosophy

Skills are capabilities, not conversation owners.

A Business Skill performs a bounded business capability under Brain supervision.

Skills may:

- analyze;
- transform;
- generate artifacts;
- apply domain methods;
- orchestrate narrow tool usage;
- validate output inside their scope;
- return assumptions, limitations, evidence, and confidence;
- suggest possible memory updates.

Skills must never own:

- the conversation;
- the user relationship;
- final business judgment;
- broad clarification strategy;
- long-term memory;
- global planning;
- authorization;
- final response commitment;
- cross-business context;
- whether the user's request is worth doing.

A Skill may report that more information would improve output quality. It may not force the user into a field collection sequence.

The Brain decides whether to ask, assume, retrieve, defer, or proceed.

If a Skill becomes capable of controlling conversation, it has become a hidden workflow and must be redesigned.

## 9. Memory Philosophy

Memory exists to reduce unnecessary questions and preserve business continuity.

Memory should store durable business-specific context such as:

- business facts;
- user preferences;
- prior decisions;
- known products or services;
- constraints;
- recurring patterns;
- important history;
- stable operating context.

Memory should not be owned by Skills or Workflows.

Skills may suggest memory candidates. Workflows may produce facts that are candidates for memory. But Memory must remain independent and governed.

The Brain uses Memory to avoid asking what is already known.

However, memory is not automatically truth. The Brain must recognize stale, conflicting, uncertain, or high-risk memory and verify when appropriate.

The standard is:

> Memory should reduce interrogation without creating false certainty.

## 10. Knowledge Philosophy

Knowledge exists to improve judgment.

Knowledge is not the same as Memory.

Memory is about this business.

Knowledge is about business domains, methods, markets, regulations, strategies, patterns, and generalizable expertise.

The Brain should use Knowledge when:

- domain expertise matters;
- the user needs advice, diagnosis, or strategy;
- external concepts would improve the answer;
- business risk depends on known practices;
- a recommendation needs grounding beyond the user's stored context.

Knowledge must not become a generic answer machine.

Knowledge improves the Brain's judgment. It does not replace judgment.

## 11. Tool Philosophy

Tools execute capabilities. They do not own judgment.

Tools may:

- retrieve data;
- calculate;
- extract text;
- inspect files;
- call external systems;
- transform artifacts;
- perform deterministic operations;
- execute authorized actions.

Tools must not decide:

- what the user means;
- whether the action is useful;
- whether a question should be asked;
- whether a result is business-appropriate;
- whether output should be committed;
- how the final response should be framed.

The Brain decides when tool use is warranted.

Tool output is evidence or execution result. It is not final judgment.

## 12. Conversation Composer

The Conversation Composer expresses judgment.

It does not decide truth.

The Composer is responsible for making the Brain's judgment clear, natural, concise, and useful to the business owner.

It should:

- communicate in the user's context;
- avoid exposing internal machinery;
- present assumptions honestly;
- make uncertainty understandable;
- ask focused questions when justified;
- preserve a companion-like experience;
- help the user act.

The Composer must not turn internal architecture into user-facing friction.

The user should not feel routed through Planner, Workflow, Skill, Memory, or Knowledge systems.

The user should feel helped by one coherent business companion.

## 13. Commit Boundary

The Commit Boundary governs persistence and final response. It does not own cognition.

The Commit Boundary protects the system from premature or unsafe commitment.

It governs:

- final response release;
- memory writes;
- durable business records;
- irreversible or sensitive tool actions;
- workflow completion effects;
- artifact persistence;
- authorization requirements.

The Commit Boundary may block, require confirmation, or prevent persistence. But it must not become the source of business reasoning.

Its role is governance, not thought.

## 14. Immutable First Principles

These principles must survive implementation details, module boundaries, model changes, product expansion, and future architectures.

- The user asks for help, not workflow.
- The Brain improves the business owner's situation through contextual judgment.
- Workflow is a tool, not the architecture.
- Planner structures possible execution, but does not own conversation.
- Skills are capabilities, not conversation owners.
- Tools execute capabilities, but do not own judgment.
- Missing fields do not justify questions.
- Only material uncertainty justifies questions.
- Questions must earn their cost.
- Memory should reduce unnecessary questions.
- Knowledge should improve judgment.
- Composer expresses judgment, but does not decide truth.
- Commit Boundary governs persistence and final response, not cognition.
- Business judgment must be explainable.
- The Brain may help under uncertainty when risk is acceptable.
- The Brain must challenge the user's premise when business risk requires it.
- Procedural completeness is less important than business usefulness.

## 15. Anti-Workflow-V2 Rules

SME Brain has become Workflow V2 if any of these are true:

- Goals have mandatory fields that force questions.
- Skills ask users directly for missing inputs.
- Planner determines conversational moves from predefined transitions.
- Workflow Runtime blocks help until required fields are filled.
- Memory is used only to populate workflow slots.
- Questions are triggered by missing data rather than material uncertainty.
- Success means completing a procedure instead of improving the business situation.
- The system cannot explain why it chose its next action.
- The user feels processed instead of helped.
- A skill or workflow can override Brain judgment.
- The Composer exposes internal routing instead of natural assistance.
- Tool output is treated as final judgment.
- The Commit Boundary becomes a decision maker rather than a governance layer.

These are rejection criteria.

Any future architecture that violates them should be considered cognitively incompatible with SME Companion V6.

## 16. Migration From V5 to V6

V5 should not be discarded. It contains valuable architectural assets.

But V5's cognitive hierarchy must change.

The migration is conceptual:

- from Planner as primary decision authority to Brain judgment as cognitive authority;
- from Workflow as conversation owner to Workflow as subordinate execution mechanism;
- from required fields to material uncertainty;
- from routing by task type to reasoning by business situation;
- from deterministic continuation to contextual helpfulness;
- from skill-led interactions to Brain-supervised capabilities;
- from memory as slot support to memory as continuity and context;
- from response generation as output formatting to Composer as natural expression of judgment;
- from completion success to business outcome usefulness.

V6 should preserve useful deterministic machinery where it improves reliability.

But deterministic machinery must be invoked by judgment, supervised by judgment, and constrained by judgment.

The migration is not complete until the system can help naturally even when no workflow applies.

The migration is not complete until asking a question requires cognitive justification.

The migration is not complete until the user experiences one intelligent business companion rather than a collection of procedural engines.

## 17. Acceptance Criteria

SME Brain V6 is acceptable only if:

- It explains how the AI reasons.
- Decisions emerge from judgment rather than predefined transitions.
- Conversations remain natural.
- Skills remain reusable capabilities.
- Memory reduces unnecessary questions.
- Knowledge improves business decisions.
- Tools execute actions without owning judgment.
- Workflow operates only as a subordinate execution mechanism.
- The Brain can answer under uncertainty when risk is acceptable.
- The Brain asks only when uncertainty is material.
- The Brain can explain why it asked, answered, searched memory, used knowledge, called a tool, delegated to a skill, invoked workflow, or stopped.
- The user experiences an intelligent business companion rather than a workflow system.

SME Brain V6 must be rejected if:

- It merely renames Workflow.
- It introduces another state machine with different terminology.
- It requires predefined conversational steps.
- It makes Skills own conversations.
- It makes questioning mandatory because fields are missing.
- It treats procedural completion as the primary measure of success.
- It cannot explain why the AI chose one action over another.

The final standard is:

> SME Companion does not complete procedures. SME Companion improves the business owner's situation through contextual business judgment.
