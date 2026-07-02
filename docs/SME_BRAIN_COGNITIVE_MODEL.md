# SME Brain Cognitive Model

This document defines the ideal cognitive architecture of SME Brain. It is not an implementation plan, runtime design, module map, API contract, prompt design, or migration guide.

SME Brain should be modeled on how an experienced business decision-maker thinks under uncertainty. The model begins with perception of business reality and ends with useful, governed communication or action.

## 1. Core Cognitive Standard

SME Brain exists to improve the business owner's situation through contextual business judgment.

The Brain must not be designed around workflows, routers, planner states, skills, tools, or response generation. Those may exist as instruments, but they are not cognition.

The cognitive model should answer:

> What is happening in this business, what matters, what is sufficiently known, what remains uncertain, what perspectives should be considered, what judgment is warranted, what action is most useful, what may be executed, and how should this be communicated?

## 2. Recommended Cognitive Flow

The ideal cognitive flow is:

```text
Perception
    -> Business Situation
    -> Evidence
    -> Truth Status
    -> Perspective
    -> Knowledge
    -> Business Judgment
    -> Decision
    -> Execution
    -> Conversation
    -> Commit
```

This is a cognitive dependence graph, not a mandatory sequence.

The Brain may revisit earlier layers when new evidence appears. It may seek knowledge before final truth status is stable. It may decide to ask before full judgment is possible. It may answer directly when the situation is simple. The order describes meaning, not procedure.

## 3. Why This Flow Is Better Than The Draft Flow

The draft flow was:

```text
Perception -> Business Situation -> Evidence -> Truth -> Perspective -> Knowledge -> Business Judgment -> Decision -> Execution -> Conversation
```

The improved flow changes three things.

First, "Truth" becomes "Truth Status" because SME Brain rarely possesses absolute truth. It needs justified reliance for a decision context.

Second, "Commit" is explicit and final. Conversation and execution may produce candidate outputs, but nothing becomes durable, external, or user-final until commitment is governed.

Third, Knowledge follows Perspective as well as Evidence. Knowledge is not merely lookup. An experienced operator asks which frame is relevant before selecting methods, principles, domain patterns, rules, or experience.

## 4. Layer Summary

### Perception

Purpose: notice signals from user input, memory, documents, dashboards, tools, conversation history, and environment.

Output: raw or lightly interpreted percepts.

Cannot merge with Business Situation because perception notices signals before the Brain understands what they mean.

### Business Situation

Purpose: frame the business reality under attention.

Output: BusinessSituation with objective hypotheses, context, constraints, risks, opportunities, uncertainty, and relevant actors.

Cannot merge with Evidence because situation framing decides what information is relevant, while evidence evaluates information quality.

### Evidence

Purpose: classify and evaluate information that bears on the situation.

Output: EvidenceSet with source, relevance, reliability, freshness, completeness, confidence, and conflicts.

Cannot merge with Truth Status because evidence is support, not justified belief.

### Truth Status

Purpose: determine what may be treated as fact, assumption, observation, belief, hypothesis, or unresolved conflict for the current decision.

Output: TruthState.

Cannot merge with Perspective because truth-status concerns justified reliance, while perspective concerns interpretive lens.

### Perspective

Purpose: decide which business lenses should evaluate the situation.

Output: PerspectiveSet such as financial, customer, operational, strategic, brand, policy, principle, market, owner, or execution perspective.

Cannot merge with Knowledge because perspectives select the kind of interpretation needed; knowledge supplies content.

### Knowledge

Purpose: bring relevant generalizable expertise, policies, principles, rules, methods, procedures, skills, and experience into judgment.

Output: KnowledgeContext with references and applicability.

Cannot merge with Judgment because knowledge informs judgment but does not decide what helps this business now.

### Business Judgment

Purpose: assess what is happening, what matters, what is beneficial, what is risky, and what should be believed or recommended under uncertainty.

Output: BusinessJudgment.

Cannot merge with Decision because judgment says what appears wise; decision chooses what to do next under constraints.

### Decision

Purpose: select the next authorized cognitive, communicative, or operational action.

Output: Decision and NextBestAction.

Cannot merge with Execution because deciding an action is not carrying it out.

### Execution

Purpose: carry out authorized operational actions, including workflow, tool use, skill calls, calculations, retrieval, or artifact production.

Output: ExecutionResult or ExecutionPlan.

Cannot merge with Conversation because execution produces results; conversation expresses meaning to the user.

### Conversation

Purpose: communicate the Brain's judgment, decision, uncertainty, assumptions, warning, question, or result naturally.

Output: ConversationIntent and ComposedResponse.

Cannot merge with Commit because wording is not finality. Commit governs release, persistence, confirmation, and external consequences.

### Commit

Purpose: decide what becomes final, durable, external, or user-visible.

Output: CommitDecision.

Cannot merge with Conversation or Execution because governance must constrain both.

## 5. Authority Position

Authority should not remain a separate cognitive layer in the flow.

Authority is constitutional governance over ownership. It defines who owns each kind of responsibility across all layers. It should annotate and constrain the cognitive model rather than sit inside it as another step.

Domain authorities such as pricing, sales, finance, marketing, customer service, and operations should be treated as perspectives or knowledge domains, not constitutional authorities.

Constitutional authority belongs to responsibilities: Situation, Evidence, Truth Status, Perspective, Knowledge, Judgment, Decision, Execution, Conversation, Commit, Policy, Principles, Memory, Skill, and Tool.

## 6. Boundary Review

### Business Situation -> Evidence

Why: the situation determines relevance; evidence evaluates support.

Crosses: situation hypotheses, context needs, uncertainty candidates, relevant domains.

Must never cross: procedural required fields masquerading as evidence needs.

Owner: Situation owns framing; Evidence owns quality.

### Evidence -> Truth Status

Why: evidence must not become truth automatically.

Crosses: evidence claims, source quality, conflicts, confidence, freshness.

Must never cross: unqualified certainty, tool output as final fact, memory as unquestioned truth.

Owner: Truth Status owns justified reliance.

### Truth Status -> Perspective

Why: interpretation should use facts and assumptions at their proper strength.

Crosses: facts, assumptions, unresolved conflicts, hypotheses.

Must never cross: hidden uncertainty or unsupported certainty.

Owner: Perspective owns lens selection; Truth Status owns epistemic labels.

### Perspective -> Knowledge

Why: the Brain should retrieve the kind of knowledge relevant to the lens.

Crosses: selected lenses, domain needs, principle needs, policy needs, skill needs.

Must never cross: a domain label claiming final judgment.

Owner: Perspective owns lens relevance; Knowledge owns content quality.

### Knowledge -> Judgment

Why: knowledge informs but does not decide.

Crosses: principles, policies, rules, experience, methods, domain patterns, procedures, skill capabilities.

Must never cross: generic best practice as a final answer.

Owner: Judgment owns synthesis.

### Judgment -> Decision

Why: wise assessment is not the same as next action.

Crosses: recommendation, risks, alternatives, confidence, uncertainty, expected business impact.

Must never cross: unauthorized action or hidden policy bypass.

Owner: Decision owns action selection.

### Decision -> Execution

Why: execution must be authorized before it acts.

Crosses: selected action, constraints, parameters, allowed scope, confirmation requirements.

Must never cross: permission for execution to redefine the business objective or ask user questions on its own.

Owner: Decision owns authorization; Execution owns carrying out.

### Execution -> Conversation

Why: results need interpretation before user communication.

Crosses: execution result, failure, limitations, evidence produced, artifacts created.

Must never cross: raw tool result as final user meaning.

Owner: Conversation owns expression; Judgment may need to reassess result meaning.

### Conversation -> Commit

Why: a response may have durable or external consequences.

Crosses: proposed response, memory candidates, confirmation needs, external action effects.

Must never cross: final release without governance when stakes require confirmation.

Owner: Commit owns finality.

## 7. Semantic Objects

The complete cognitive model requires:

- `Percept`
- `BusinessSituation`
- `Evidence`
- `EvidenceSet`
- `TruthState`
- `Assumption`
- `Hypothesis`
- `MaterialUncertainty`
- `Perspective`
- `PerspectiveSet`
- `KnowledgeReference`
- `KnowledgeContext`
- `Principle`
- `Policy`
- `BusinessRule`
- `Procedure`
- `SkillCapability`
- `BusinessJudgment`
- `JudgmentAlternative`
- `Decision`
- `NextBestAction`
- `DecisionAlternative`
- `ExecutionPlan`
- `ExecutionResult`
- `ConversationIntent`
- `ComposedResponse`
- `CommitDecision`
- `Explanation`

## 8. Five-Year Scalability

This architecture scales to 100+ domains and 1000+ skills only if domains and skills remain subordinate. New domains should add perspectives and knowledge. New skills should add execution capabilities. New models should contribute perception, evidence evaluation, knowledge retrieval, judgment drafts, or conversation drafts, but never own authority by virtue of generation.

The stable center must remain:

```text
Situation -> Evidence -> Truth Status -> Perspective -> Knowledge -> Judgment -> Decision -> Execution -> Conversation -> Commit
```

If any future system routes directly from user intent to workflow, skill, or response without passing through judgment and decision ownership, it is not SME Brain V6.

