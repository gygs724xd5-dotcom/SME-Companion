# SME Brain Authority Model

SME Companion V6 must not contain a "God Brain."

The phrase "the Brain decides" is directionally useful but constitutionally insufficient. It hides responsibility. It makes ownership vague. It allows future components to claim authority they should not have.

This document defines the Authority Model for SME Brain.

Authority is constitutional.

Components are implementation.

They must never be confused.

This document extends `SME_BRAIN.md`, `SME_BRAIN_THEORY.md`, `SME_BRAIN_ONTOLOGY.md`, `SME_BRAIN_EPISTEMOLOGY.md`, `SME_BRAIN_PRINCIPLES.md`, and `SME_BRAIN_CONTRACTS.md`.

This is a constitutional architecture specification. It does not define code, APIs, classes, modules, workflows, runtime orchestration, or implementation mechanics.

## 1. Purpose of Authority

Authority defines who is responsible for a kind of judgment, decision, constraint, or commitment.

Authority is different from components.

A component is a possible implementation unit.

An authority is a responsibility boundary.

The same authority may be expressed through different future components, models, tools, or systems. The authority remains stable even when implementation changes.

The purpose of authority is to make SME Brain answer:

> Which authority owns this decision?

not:

> What component should run?

Without explicit authority, the system risks:

- a God Brain that owns everything;
- Skills making policy decisions;
- Memory silently changing judgment;
- Tools becoming truth;
- Composer changing decisions;
- Execution modifying business records without governance;
- duplicate decision makers;
- hidden workflow control.

Authority protects cognition by making responsibility explicit.

## 2. Authority Principles

**Single Ownership**

Every constitutional responsibility should have one owning authority.

Other authorities may contribute, challenge, or request work, but they must not co-own the final responsibility.

**Explicit Authority**

Every important judgment, decision, persistence act, execution act, and user-facing communication should be traceable to the authority that owns it.

**Delegation Without Transfer**

An authority may request work from another authority, Skill, Tool, or execution mechanism. Delegation does not transfer ownership unless the Constitution explicitly says so.

**No Hidden Authority**

No Skill, Tool, Memory system, workflow, model, prompt, or Composer may secretly make decisions outside its authority.

**No Overlapping Ownership**

Two authorities must not own the same final responsibility. Overlap creates contradiction, inconsistent behavior, and unreviewable decisions.

**Authority Before Component**

Future implementation must respect authority boundaries. Components are servants of authority, not sources of authority.

**Principled Override**

When one authority constrains another, the constraint must be explicit. For example, Policy may reject a proposed action, but Policy does not thereby own Business Judgment.

**Explainable Authority**

The system should be able to explain why a given authority controlled a given decision.

**No Workflow Authority Over Cognition**

Workflow may execute subordinate procedures, but it must not own judgment, policy, conversation, memory, truth, or final decision.

## 3. Authority Map

The constitutional authorities are:

1. Business Situation Authority
2. Evidence Authority
3. Truth Authority
4. Business Judgment Authority
5. Principles Authority
6. Policy Authority
7. Decision Authority
8. Conversation Authority
9. Memory Authority
10. Knowledge Authority
11. Skill Authority
12. Tool Authority
13. Execution Authority
14. Commit Authority

Some candidate authorities are intentionally not separate:

**Planner Authority**

Planning is not a top-level constitutional authority in SME Brain V6. Planning is a possible contribution to Decision or Execution when complex pursuit is needed. If Planner becomes an authority over conversation or judgment, Workflow V2 returns.

**Workflow Authority**

Workflow is not a constitutional authority over cognition. It may exist inside Execution Authority as a subordinate procedural mechanism.

**Composer Authority**

Composer is not separate from Conversation Authority. Conversation Authority owns communicative purpose and final expression boundaries. A future Composer may serve that authority.

**Reasoning Authority**

Reasoning is a cognitive process used by several authorities. It is not a separate owner of final responsibility. Business Judgment Authority owns the formed judgment.

## 4. Responsibilities

### 4.1 Business Situation Authority

Owns:

- interpretation of the current business situation;
- distinction between what the user said and what is inferred;
- identification of relevant objective, context, constraints, risks, opportunities, and uncertainty;
- protection against premature workflow framing.

Must never own:

- final judgment;
- final decision;
- memory persistence;
- policy enforcement;
- execution;
- final conversation rendering.

### 4.2 Evidence Authority

Owns:

- classification of information as evidence;
- source awareness;
- evidence quality evaluation;
- confidence, freshness, reliability, relevance, completeness, and consistency as evidence properties;
- surfacing evidence conflicts.

Must never own:

- final truth;
- final business judgment;
- policy;
- execution;
- conversation rendering;
- memory persistence.

### 4.3 Truth Authority

Owns:

- determining what should be treated as true enough for the current decision context;
- distinguishing fact, assumption, observation, belief, and hypothesis;
- resolving or preserving conflicts between evidence sources;
- preventing tool output, memory, OCR, or user statements from becoming unquestioned truth.

Must never own:

- business recommendation;
- policy approval;
- final response style;
- execution;
- durable memory writes by itself.

Truth Authority does not claim absolute truth. It owns justified truth-status for the current business context.

### 4.4 Business Judgment Authority

Owns:

- Business Judgment;
- assessment of the situation under uncertainty;
- weighing evidence, objectives, risk, opportunity, constraints, trade-offs, and business consequence;
- forming the current assessment;
- identifying alternative hypotheses;
- recommending what appears beneficial.

Must never own:

- memory persistence;
- policy permission;
- principle acceptability;
- execution;
- final conversation rendering;
- final commit.

Business Judgment Authority proposes what may help. It does not decide what is acceptable, permitted, executed, or persisted.

### 4.5 Principles Authority

Owns:

- universal business principles;
- selected Principle Set evaluation;
- ethical acceptability;
- rejection of deception, exploitation, hidden material uncertainty, and irresponsible harm;
- value-balancing constraints.

Must never own:

- business facts;
- evidence classification;
- organization-specific policy;
- execution;
- memory persistence;
- final response rendering.

Principles Authority can reject or reshape a judgment proposal. It does not replace business realism.

### 4.6 Policy Authority

Owns:

- organization-specific policies;
- business rules;
- approval constraints;
- compliance constraints;
- owner-defined operating rules;
- selected Principle Set application where organization-specific rules exist.

Must never own:

- universal moral floor;
- final business judgment;
- evidence truth;
- conversation style;
- execution by itself.

Policy Authority constrains what is permitted in this organization. It may be stricter than Principles, but it must not weaken the universal moral floor.

### 4.7 Decision Authority

Owns:

- final selection of the next authorized cognitive, communicative, or operational action;
- choosing between answer, ask, use memory, use knowledge, use OCR, call tool, call skill, wait, observe, delegate, warn, confirm, or execute;
- reconciling judgment, principles, policy, evidence, uncertainty, and commit constraints into an authorized next move;
- explaining why this action is appropriate now.

Must never own:

- raw evidence quality;
- truth creation;
- memory persistence;
- tool output;
- skill output;
- final wording independent of Conversation Authority;
- execution effects independent of Commit Authority.

Decision Authority authorizes the next move. It does not invent facts or bypass constraints.

### 4.8 Conversation Authority

Owns:

- communicative purpose;
- final user-facing expression;
- clarity, tone, structure, and naturalness;
- faithful expression of judgment, uncertainty, principles, policy, and decision;
- preventing internal machinery from leaking into user experience.

Must never own:

- truth;
- business judgment;
- policy;
- memory persistence;
- execution;
- changing the decision it is meant to express.

Conversation Authority may clarify presentation. It must not alter substance.

### 4.9 Memory Authority

Owns:

- durable business memory;
- memory retrieval as business context;
- memory correction, decay, conflict surfacing, and forgetting principles;
- evaluation of memory candidates;
- preventing Skills, Tools, and Workflows from writing memory directly.

Must never own:

- final business judgment;
- final decision;
- policy;
- conversation rendering;
- execution.

Memory Authority contributes context and continuity. It does not decide what should be done.

### 4.10 Knowledge Authority

Owns:

- generalizable business knowledge;
- domain principles, methods, market patterns, regulatory concepts, and durable expertise;
- knowledge quality and knowledge decay;
- distinguishing general knowledge from business-specific memory.

Must never own:

- local business truth by itself;
- final judgment;
- policy;
- memory persistence;
- execution;
- conversation rendering.

Knowledge Authority improves interpretation. It does not override strong business-specific evidence without reason.

### 4.11 Skill Authority

Owns:

- bounded skill capability execution;
- skill-scope assumptions, findings, evidence, limitations, and confidence;
- declaring what a Skill can and cannot contribute.

Must never own:

- conversation;
- final decision;
- policy;
- principles;
- memory persistence;
- final business judgment;
- user clarification strategy;
- final response.

Skill Authority owns the integrity of Skill output, not the business conversation.

### 4.12 Tool Authority

Owns:

- concrete tool capability output;
- tool-scope result boundaries;
- tool limitations;
- tool confidence where applicable;
- distinguishing output from truth.

Must never own:

- business judgment;
- truth-status beyond its output;
- policy;
- conversation;
- memory persistence;
- final decision.

Tool Authority produces outputs. Other authorities determine meaning, truth-status, acceptability, and action.

### 4.13 Execution Authority

Owns:

- carrying out authorized operational actions;
- subordinate procedural execution;
- workflow execution when a workflow is appropriate;
- external action within permitted boundaries;
- reporting execution result, failure, or limitation.

Must never own:

- whether the action is wise;
- whether the action is ethical;
- whether the action is permitted;
- final conversation;
- truth alteration without Commit Authority;
- memory persistence by itself.

Execution Authority executes what has been authorized. It does not authorize itself.

### 4.14 Commit Authority

Owns:

- final commitment boundaries;
- response release;
- durable memory writes;
- durable business records;
- irreversible or sensitive external actions;
- approval and confirmation gates;
- preventing premature persistence or unsafe commitment.

Must never own:

- business judgment;
- evidence interpretation;
- principles;
- policy substance;
- conversation style;
- skill findings;
- tool output.

Commit Authority governs what becomes final or durable. It is governance, not cognition.

## 5. Delegation

Authorities may request work from each other.

Delegation is necessary because business judgment requires many kinds of contribution.

Examples:

- Business Judgment Authority may request Evidence Authority to evaluate source quality.
- Evidence Authority may request Memory Authority for business context.
- Decision Authority may request Policy Authority to check whether a proposed action is permitted.
- Conversation Authority may request Business Judgment Authority for a reasoning summary.
- Commit Authority may request Policy Authority to confirm approval requirements.
- Skill Authority may request Tool Authority for bounded extraction or calculation.

Delegation must preserve ownership.

The requesting authority remains responsible for its own decision. The receiving authority owns only its contribution.

No delegation may allow:

- Skills to own conversation;
- Tools to own truth;
- Memory to own judgment;
- Composer to own decision;
- Execution to own authorization;
- Workflow to own cognition.

## 6. Conflict Resolution

Conflicts between authorities are expected.

They should be resolved by constitutional priority and responsibility boundaries, not by whichever component speaks last.

**Judgment vs Policy**

If Business Judgment recommends an action but Policy forbids it, the action must not proceed as-is.

Judgment may propose alternatives. Policy constrains permission.

**Judgment vs Principles**

If Judgment recommends something beneficial but Principles reject it as deceptive, exploitative, unfair, or irresponsibly harmful, the action must not be recommended as-is.

Principles constrain acceptability.

**Memory vs Evidence**

If Memory disagrees with current Evidence, Evidence Authority and Truth Authority must evaluate freshness, reliability, source fit, and consequence.

Memory does not automatically win because it is stored. Current evidence does not automatically win because it is recent.

**Truth vs User Statement**

The user's current statement is highly authoritative for intent, preference, and business-specific correction.

It is not automatically decisive for recorded facts, calculations, legal constraints, or external truth.

Truth Authority must respect the user without becoming credulous.

**Knowledge vs Dashboard**

Business Knowledge is general. Dashboard evidence is local.

Strong local evidence usually constrains general knowledge, but general knowledge may reveal risks or interpretations that dashboard data alone cannot show.

**Conversation vs Decision**

Conversation Authority may improve clarity and tone, but it must not change the authorized decision.

If faithful communication is impossible without changing substance, the conflict must return to Decision Authority.

**Execution vs Commit**

Execution may report what can be done. Commit Authority determines whether it may become durable, external, irreversible, or final.

**Policy vs Principles**

Policy may be stricter than Principles.

Policy must not authorize actions below the universal moral floor.

If Policy conflicts with Universal Principles, Principles prevail.

## 7. Authority Boundaries

The following must never cross authority boundaries:

- Skills deciding policy.
- Skills owning conversation.
- Skills determining final judgment.
- Tools deciding truth-status beyond their output.
- Tool output becoming final judgment automatically.
- Memory changing judgment without Business Judgment Authority.
- Memory writing itself from Skill output without Commit Authority.
- Knowledge overriding local business evidence without Truth Authority.
- Composer changing decisions.
- Conversation Authority hiding material uncertainty that Judgment or Principles require disclosed.
- Execution modifying truth.
- Execution authorizing itself.
- Workflow determining user questions.
- Workflow blocking help because procedural fields are incomplete.
- Commit Authority inventing business reasoning.
- Policy Authority weakening Universal Principles.
- Decision Authority bypassing Principles, Policy, or Commit constraints.

Authority leakage is a constitutional violation.

## 8. Authority Graph

SME Brain should be understood as a semantic authority graph, not a workflow, pipeline, or sequence.

Authorities relate by meaning and responsibility.

```text
Business Situation Authority
        connects to
Evidence Authority
        connects to
Truth Authority
        connects to
Business Judgment Authority

Business Judgment Authority
        is constrained by
Principles Authority
Policy Authority

Business Judgment Authority
        informs
Decision Authority

Decision Authority
        may request
Memory Authority
Knowledge Authority
Skill Authority
Tool Authority
Execution Authority

Conversation Authority
        expresses authorized meaning from
Decision Authority
Business Judgment Authority
Principles Authority
Policy Authority

Commit Authority
        governs finality across
Conversation
Memory
Records
Execution
External actions
```

This graph is not a pipeline.

There is no mandatory sequence.

There is no universal next step.

There is no hidden state machine.

The same business situation may require only Conversation Authority and Business Judgment Authority. Another may require Evidence, Truth, Policy, Commit, Execution, and Memory. Another may require only Knowledge and Conversation.

The runtime question should never be:

> What component should run next?

The constitutional question is:

> Which authority owns this decision, constraint, contribution, or commitment?

## 9. Scalability

The Authority Model must scale to:

- 1000 Skills;
- millions of stores;
- hundreds of policies;
- many LLMs;
- many tools;
- many principle sets;
- many business domains.

It scales only if authority remains independent from implementation.

**1000 Skills**

Skills remain bounded contributors. Skill Authority owns skill-scope output integrity, but never conversation, judgment, policy, or memory persistence. This prevents skill sprawl from becoming authority sprawl.

**Millions of Stores**

Memory Authority and Policy Authority must remain store-specific where appropriate, while Universal Principles and constitutional authority boundaries remain shared.

**Hundreds of Policies**

Policy Authority may evaluate many organization-specific constraints, but Policy must remain distinct from Principles, Judgment, and Decision.

**Many LLMs**

Models may contribute reasoning, language, extraction, or analysis, but models do not own authority merely because they generate text.

**Many Tools**

Tool Authority keeps tool outputs bounded. Truth Authority and Judgment Authority determine what those outputs mean.

**Many Principle Sets**

Principles Authority supports different value lenses while preserving the universal moral floor and stable cognitive structure.

The system scales when every new capability asks:

> What authority does this serve?

not:

> What authority can this component take?

## 10. Failure Modes

**God Object**

One component or conceptual Brain owns judgment, truth, policy, memory, conversation, execution, and commit.

Consequence: unreviewable decisions, brittle architecture, hidden contradictions, and loss of accountability.

**Circular Ownership**

Two authorities depend on each other to define their own responsibility.

Example: Decision owns Judgment because it chooses actions, while Judgment owns Decision because it decides what to do.

Consequence: unclear responsibility and inconsistent behavior.

**Authority Leakage**

A subordinate capability performs decisions outside its scope.

Example: a Skill asks the user questions directly or a Tool output becomes final truth.

Consequence: Workflow V2, hidden agents, unsafe autonomy.

**Duplicate Ownership**

Two authorities both claim final say over the same responsibility.

Example: Conversation Authority and Decision Authority both decide whether to ask.

Consequence: conflicting outputs and unpredictable behavior.

**Hidden Decision Making**

A prompt, model, skill, workflow, or tool silently makes a decision without naming the authority it serves.

Consequence: the system cannot explain itself.

**Policy Capture**

Organization Policy is treated as moral truth.

Consequence: unethical local rules can override universal principles.

**Principle Capture**

Principles ignore business reality and block practical, responsible action.

Consequence: moral language becomes commercially useless.

**Execution Capture**

Execution mechanisms begin deciding what should be done because they know how to do it.

Consequence: capability becomes authority.

**Memory Capture**

Stored context silently determines present judgment.

Consequence: stale assumptions, user correction fatigue, and personalization errors.

**Composer Capture**

Conversation style changes the meaning of the decision.

Consequence: beautiful language hides incorrect substance.

## 11. Authority Evolution

Authorities may evolve, but only carefully.

Evolution is acceptable when:

- a new authority represents a durable constitutional responsibility;
- an existing authority has become too broad to audit;
- a responsibility boundary is repeatedly confused;
- scale reveals a persistent ownership gap;
- the change improves explainability and accountability.

Evolution is not acceptable when:

- it merely renames a component;
- it creates overlapping ownership;
- it gives Skills, Tools, Workflows, or models hidden authority;
- it weakens Principles, Policy, Truth, or Commit constraints;
- it turns a procedural mechanism into a cognitive authority;
- it makes the architecture less explainable.

Authorities should remain fewer than components.

The test for adding an authority is:

> Does this represent a stable responsibility that must remain true across implementations?

If not, it is not an authority.

## Final Requirement: If Workflow Disappeared Forever

If Workflow disappeared forever, every authority should still know its responsibilities.

Business Situation Authority would still interpret business reality.

Evidence Authority would still evaluate information.

Truth Authority would still determine what is justified enough to rely on.

Business Judgment Authority would still assess what appears beneficial.

Principles Authority would still evaluate acceptability.

Policy Authority would still constrain organization-specific permission.

Decision Authority would still authorize the next move.

Conversation Authority would still express meaning to the user.

Memory Authority would still preserve and retrieve durable business context.

Knowledge Authority would still provide generalizable expertise.

Skill Authority would still govern bounded capability contributions.

Tool Authority would still govern tool output boundaries.

Execution Authority would still carry out authorized operational actions where non-workflow execution exists.

Commit Authority would still govern finality and persistence.

Workflow is not the source of authority.

Workflow is only one possible subordinate execution mechanism.

The final standard is:

> SME Brain authority survives without Workflow because authority is grounded in responsibility, not procedure.
