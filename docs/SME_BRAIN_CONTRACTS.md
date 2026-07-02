# SME Brain Cognitive Contracts

SME Companion V6.1 defines a shared cognitive language for every future Brain component.

These contracts replace Workflow State with meaning-bearing cognitive objects. They are not implementation types, classes, APIs, schemas, or algorithms. They define the architectural objects that Planner, Reasoning, Memory, Knowledge, Skills, Tools, Conversation Composer, and Commit Boundary must understand.

The purpose is simple:

> SME Brain should exchange business meaning, not procedural state.

## Contract Principles

- Contracts describe cognition, not implementation.
- Contracts represent what the Brain understands, judges, decides, and communicates.
- No contract may require a predefined workflow path.
- No contract may force a question merely because data is missing.
- Every decision must be explainable.
- Skills and tools may contribute evidence, but they do not own judgment.
- Conversation is composed only after judgment and decision.

## 1. BusinessSituation

### Purpose

BusinessSituation represents the user's current business situation as understood by the Brain.

It is the starting point for judgment. It is not a workflow state, task state, or routing state.

BusinessSituation answers:

> What business situation is the user asking SME Companion to enter?

### Includes

**Objective**

The provisional business outcome the user appears to want.

The objective may be explicit, inferred, incomplete, or evolving. It must not be treated as a fixed workflow goal too early.

**Detected Intent**

The Brain's current interpretation of what the user is trying to do.

Examples include asking for advice, creating content, diagnosing a problem, making a decision, checking a document, understanding performance, planning an action, or correcting prior work.

**Business Context**

Known context about the business, owner, products, customers, operations, constraints, prior decisions, and current situation.

Business context may come from memory, user messages, dashboard data, files, or prior conversation.

**Current Evidence**

The information currently available to support interpretation and judgment.

Evidence may be strong, weak, fresh, stale, direct, inferred, user-provided, or externally sourced.

**Assumptions**

Explicit working assumptions the Brain is using when information is unavailable or not worth asking for.

Assumptions allow the Brain to help under uncertainty without pretending certainty.

**Uncertainty**

Known unknowns that may affect the quality, safety, or direction of the response.

Uncertainty is not the same as missing fields. It matters only when it could change judgment or action.

**Constraints**

Limits affecting the situation.

Constraints may include budget, time, inventory, staffing, brand, legal risk, cash flow, user preference, market conditions, platform limits, or available data.

**Desired Outcome**

The useful end state the Brain believes would help the user.

The desired outcome may be a direct answer, recommendation, draft, diagnosis, explanation, warning, calculation, artifact, plan, or next question.

### Responsibilities

BusinessSituation is responsible for carrying the meaning of the user's current business context.

It should:

- preserve the difference between what the user said and what the Brain inferred;
- hold enough context for judgment to begin;
- make assumptions and uncertainties visible;
- prevent premature conversion into workflow state;
- allow the Brain to help even when information is incomplete.

BusinessSituation must not:

- define required fields;
- force a route;
- determine the next step;
- own conversation;
- declare a workflow complete or incomplete.

## 2. Evidence

### Purpose

Evidence represents information used by the Brain to understand, judge, decide, or respond.

Evidence is not automatically truth. It is a contribution to judgment.

### Sources

Evidence may come from:

- Memory;
- Knowledge;
- User;
- OCR;
- Dashboard;
- Skills;
- Tools;
- prior conversation;
- uploaded documents;
- business records;
- calculations.

### Evidence Qualities

**Confidence**

How strongly the Brain believes the evidence supports a conclusion.

Confidence may be affected by source quality, consistency, directness, ambiguity, corroboration, and recency.

**Freshness**

How current the evidence is.

Freshness matters because business conditions change. A remembered product line, price, promotion, staff count, or cash position may become stale.

**Reliability**

How trustworthy the source or method is.

A verified business record is usually more reliable than a vague memory. A user's current statement may override older stored memory. OCR output may require validation.

**Importance**

How much the evidence could affect the business judgment or decision.

Low-importance evidence should not slow the conversation. High-importance evidence may justify more reasoning, verification, or a question.

### Responsibilities

Evidence should:

- make the basis of judgment visible;
- allow conflicting information to be compared;
- support explainable decisions;
- distinguish facts, observations, assumptions, and inferences;
- preserve source awareness.

Evidence must not:

- decide the answer by itself;
- force a workflow transition;
- become durable memory without governance;
- override current user context without judgment.

## 3. MaterialUncertainty

### Purpose

MaterialUncertainty replaces Missing Fields as the cognitive reason to ask, search, calculate, inspect, or defer.

It represents an unknown that may meaningfully affect business judgment.

### What Uncertainty Is

Uncertainty is the Brain's recognition that some part of the situation is unknown, ambiguous, conflicting, stale, risky, or under-supported.

Examples:

- The user wants a promotion, but the Brain does not know whether the goal is new customers or repeat purchases.
- Memory says the business sells lunch sets, but the user now mentions catering.
- OCR read a total from a receipt, but the image is blurry.
- The user asks whether to hire, but cash flow is unknown.

### How Uncertainty Differs From Missing Data

Missing data means a value is absent from a structure.

Material uncertainty means the unknown could change the next helpful action.

Missing data is procedural.

Material uncertainty is cognitive.

A missing field may be irrelevant. A known field may still be unreliable. The Brain must care about business impact, not structural completeness.

### When Uncertainty Justifies Asking

Uncertainty justifies asking the user only when:

- resolving it would materially change the recommendation, answer, action, or risk;
- memory cannot answer it reliably;
- knowledge cannot resolve it;
- assumptions would be too risky or likely wrong;
- tool use cannot obtain it;
- proceeding would likely waste the user's time or harm the business outcome;
- the question is focused enough to earn its cost.

The Brain should ask the smallest useful question.

MaterialUncertainty must not become a renamed required-field system.

## 4. BusinessJudgment

### Purpose

BusinessJudgment is the central cognitive object of SME Brain.

It represents the Brain's current assessment of the business situation, including what appears true, what may be happening, what matters, what is risky, and what action would likely help.

BusinessJudgment answers:

> Given the situation and evidence, what should SME Companion believe and do next?

### Includes

**Current Assessment**

The Brain's best current view of the situation.

This may include diagnosis, interpretation, recommendation direction, risk view, or expected business impact.

**Confidence**

How strongly the Brain trusts the current assessment.

Confidence should be proportional to evidence quality, uncertainty, risk, and consistency.

**Alternative Hypotheses**

Plausible other interpretations.

Alternative hypotheses matter when the situation may have multiple explanations or when different interpretations would lead to different actions.

**Risks**

Potential business, financial, operational, brand, legal, trust, or execution risks.

Risks influence whether to answer, ask, warn, calculate, verify, or defer.

**Reasoning Summary**

A concise explanation of why the Brain reached the assessment.

The summary should make decisions explainable without exposing unnecessary internal machinery to the user.

### Why Judgment Is Not Goal

A Goal is an intended outcome.

BusinessJudgment is an assessment under uncertainty.

A goal says:

> What are we trying to achieve?

Judgment says:

> What is going on, what matters, what is uncertain, what is risky, and what should be done next?

Goals can be wrong, premature, incomplete, or too narrow.

Judgment can revise the goal, challenge the goal, split the goal, delay the goal, or decide that a different outcome would help the business more.

Therefore, Goal must never replace BusinessJudgment as the center of SME Brain.

## 5. Decision

### Purpose

Decision represents what the Brain chooses to do next.

Decision is where judgment becomes action.

It is not a workflow transition. It is an explainable cognitive commitment.

### Possible Actions

**Answer**

Provide a response directly because context is sufficient and risk is acceptable.

**Ask**

Ask the user a focused question because material uncertainty prevents a useful or safe next action.

**Use Memory**

Retrieve business-specific context to reduce unnecessary questions or improve continuity.

**Use Knowledge**

Retrieve general business, domain, market, regulatory, or methodological knowledge to improve judgment.

**Use OCR**

Extract information from visual or scanned material when the user's request depends on image or document content.

**Call Tool**

Use a concrete capability for retrieval, calculation, transformation, inspection, or external action.

**Call Skill**

Request a bounded business capability from a Skill under Brain supervision.

**Wait**

Pause because user input, confirmation, external completion, or risk resolution is required.

**Observe**

Inspect available context, artifacts, messages, data, or environment before deciding further.

**Delegate**

Assign a bounded subtask to another capability while retaining Brain ownership of judgment and conversation.

### Required Decision Meaning

Each Decision must include:

**Why**

The cognitive reason this action is appropriate now.

**Confidence**

How confident the Brain is that this action is the right next move.

**Expected Outcome**

What the Brain expects the action to accomplish for the business situation.

### Responsibilities

Decision should:

- make action selection explainable;
- connect judgment to behavior;
- prevent hidden workflow transitions;
- expose when the Brain is acting under uncertainty;
- preserve Brain ownership over skills, tools, and workflows.

Decision must not:

- be selected only because it is the next procedural step;
- be controlled by a Skill;
- be controlled by a Tool;
- be controlled by Workflow State;
- force a question because a field is missing.

## 6. NextBestAction

### Purpose

NextBestAction represents the Brain's judgment of the most useful next move for the business owner.

It is the actionable expression of a Decision.

### Difference From Workflow Next Step

A Workflow Next Step is procedural.

It asks:

> What step follows in the predefined process?

NextBestAction is cognitive.

It asks:

> What action would most improve the user's business situation now?

A Workflow Next Step depends on state transition.

NextBestAction depends on judgment, evidence, uncertainty, risk, cost, and expected usefulness.

A Workflow Next Step may be "collect target audience."

A NextBestAction may be:

> Draft a useful promotion using known business context, while noting the assumed audience.

or:

> Ask whether the promotion is meant for new customers or repeat customers because the offer strategy would differ.

### Responsibilities

NextBestAction should:

- convert Decision into practical movement;
- remain flexible under uncertainty;
- preserve natural conversation;
- favor business usefulness over procedural completeness.

NextBestAction must not:

- be derived solely from workflow order;
- require all fields to be complete;
- make Skills or Tools conversation owners;
- hide the reason for action selection.

## 7. BusinessSkillRequest

### Purpose

BusinessSkillRequest represents how the Brain asks a Skill for help.

It is a bounded request for capability execution.

It is not delegation of conversation ownership.

### Required Meaning

A BusinessSkillRequest should communicate:

- the business situation relevant to the skill;
- the specific capability requested;
- the desired output type;
- relevant evidence;
- assumptions the skill should respect;
- uncertainties the skill should consider;
- constraints;
- quality expectations;
- risk sensitivities;
- what the skill must not decide.

### Skill Boundaries

Skills never own conversations.

Skills never decide the user's intent.

Skills never decide whether to ask the user.

Skills never determine final business judgment.

Skills never produce final conversation.

Skills execute bounded capabilities and return structured cognitive contributions to the Brain.

### Responsibilities

BusinessSkillRequest should:

- give Skills enough context to be useful;
- prevent Skills from asking broad clarification questions;
- preserve Brain ownership of judgment;
- make Skill execution auditable;
- keep Skills reusable across business situations.

BusinessSkillRequest must not:

- hand over the conversation;
- let the Skill define required user fields;
- let the Skill commit memory;
- let the Skill produce final user response.

## 8. BusinessSkillResult

### Purpose

BusinessSkillResult represents what a Skill returns to the Brain.

It is a cognitive contribution, not a final answer.

### May Return

**Evidence**

Information discovered, produced, extracted, calculated, or validated by the Skill.

**Findings**

Skill-level observations or analysis relevant to the request.

**Recommendations**

Bounded recommendations within the Skill's scope.

**Assumptions**

Assumptions used by the Skill.

**Limitations**

Where the Skill's output may be incomplete, uncertain, risky, or dependent on missing context.

**Confidence**

How reliable the Skill believes its findings are within its bounded scope.

**Suggested Memory Candidates**

Facts or preferences that may be worth remembering, subject to Memory governance and Commit Boundary rules.

### Must Not Return

BusinessSkillResult must never return final user conversation.

It must not:

- speak directly to the user;
- decide final wording;
- commit memory;
- override Brain judgment;
- declare the conversation complete;
- force the next question;
- trigger workflow continuation by itself.

The Brain evaluates Skill results as evidence, findings, or bounded recommendations.

The Composer later expresses the Brain's final judgment if a response is warranted.

## 9. ConversationIntent

### Purpose

ConversationIntent represents why the Brain is communicating with the user.

It bridges Decision and ComposedResponse.

ConversationIntent is not the text of the response. It is the communicative purpose.

### Examples

**Answer**

The Brain has enough context to respond directly.

**Clarify**

The Brain needs a focused answer to material uncertainty.

**Educate**

The user would benefit from understanding a concept, tradeoff, or method.

**Recommend**

The Brain is advising a course of action.

**Warn**

The Brain sees business, financial, operational, legal, brand, or trust risk.

**Confirm**

The Brain needs user approval before persistence, external action, irreversible action, or high-risk continuation.

**Explore**

The situation is open-ended and the Brain is helping discover direction.

**Reflect**

The Brain is restating, synthesizing, or validating the user's situation to improve alignment.

**Explain**

The Brain is making its reasoning, assumptions, evidence, or decision understandable.

### Responsibilities

ConversationIntent should:

- make communication purposeful;
- prevent generic response generation;
- let the Composer choose appropriate phrasing and structure;
- preserve the reason for speaking;
- connect the response to Decision and BusinessJudgment.

ConversationIntent must not:

- decide the truth of the answer;
- choose tool or skill execution;
- own conversation state;
- replace BusinessJudgment.

## 10. ComposedResponse

### Purpose

ComposedResponse is the final response object generated for the user.

It is generated only by the Conversation Composer.

Never by Skills.

Never by Memory.

Never by Knowledge.

Never by Tools.

Never by Workflow.

### Responsibilities

ComposedResponse should:

- express the Brain's judgment clearly;
- match the ConversationIntent;
- communicate assumptions where useful;
- make uncertainty understandable;
- ask only justified questions;
- present recommendations or warnings naturally;
- avoid exposing internal machinery;
- preserve continuity and trust;
- help the business owner act.

### May Include

- direct answer;
- recommendation;
- focused question;
- explanation;
- warning;
- summary;
- next action;
- confirmation request;
- stated assumptions;
- relevant evidence summary;
- limitation note.

### Must Not Include

ComposedResponse must not:

- expose raw workflow state;
- pretend Skill output is final judgment;
- ask questions only because fields are missing;
- hide high-risk uncertainty;
- commit memory by itself;
- execute tools by itself;
- override Commit Boundary governance.

## Contract Relationships

The primary cognitive flow is:

```text
BusinessSituation
        |
        v
Evidence
        |
        v
MaterialUncertainty
        |
        v
BusinessJudgment
        |
        v
Decision
        |
        v
NextBestAction
        |
        v
ConversationIntent
        |
        v
ComposedResponse
```

This flow is conceptual, not procedural.

The Brain may revisit earlier objects as new evidence appears. It may search memory before forming judgment. It may use knowledge before evaluating uncertainty. It may call a skill before composing a response. It may answer directly when the situation is already clear.

The point is not sequence.

The point is meaning.

## Component Responsibilities Through Contracts

**Planner**

Planner may help structure complex pursuit, but it communicates through BusinessSituation, Decision, and NextBestAction. Planner must not reduce the Brain to workflow state.

**Reasoning**

Reasoning forms BusinessJudgment from BusinessSituation, Evidence, and MaterialUncertainty.

**Memory**

Memory contributes Evidence and business context. It does not own judgment or final response.

**Knowledge**

Knowledge contributes Evidence and generalizable expertise. It improves judgment but does not replace it.

**Skills**

Skills receive BusinessSkillRequest and return BusinessSkillResult. They never own conversation.

**Tools**

Tools contribute Evidence or execution results. They do not decide what should be done.

**Conversation Composer**

Composer receives BusinessJudgment, Decision, NextBestAction, and ConversationIntent. It produces ComposedResponse.

**Commit Boundary**

Commit Boundary governs whether response release, memory persistence, durable records, or external actions are allowed. It does not create BusinessJudgment.

## Stability Standard

These contracts should remain stable even if future implementations change models, tools, storage, workflows, skills, planners, or user interfaces.

A future engineer should be able to build SME Brain without Workflow State by using these contracts as the shared language of cognition.

The final standard is:

> SME Brain components exchange situation, evidence, uncertainty, judgment, decision, intent, and response. They do not exchange procedural control as the center of thought.
