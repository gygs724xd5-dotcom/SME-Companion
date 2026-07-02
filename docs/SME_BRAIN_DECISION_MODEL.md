# SME Brain Decision Model

This document defines Decision in SME Brain. It describes ideal cognition, not implementation.

## 1. Purpose

Decision is the selection of the next authorized action.

Judgment assesses what appears true, useful, risky, and beneficial. Decision chooses what SME Brain should do next.

Decision answers:

> Given the judgment, uncertainty, constraints, principles, policy, available capabilities, cost, risk, reversibility, and user context, what should happen now?

## 2. Judgment vs Decision

Judgment says:

> This is what appears to be happening and what would likely help.

Decision says:

> This is the next authorized move.

Judgment may conclude that a discount is risky. Decision may choose to draft a value-based reply instead of asking another question.

Judgment may conclude evidence is insufficient for a hiring recommendation. Decision may choose to ask one focused question about current cash flow.

Judgment may conclude a promotion is useful. Decision may choose to call a content skill, answer directly, or ask for audience clarification depending on material uncertainty.

## 3. Why Decision Must Exist

Decision cannot merge with Judgment because wise assessment does not automatically determine action.

It cannot merge with Execution because action selection is not action performance.

It cannot merge with Conversation because deciding to ask, warn, answer, execute, or confirm precedes wording.

It cannot merge with Commit because commit governs finality, not action selection.

## 4. Responsibilities

Decision must:

- select the next best action;
- compare alternatives;
- weigh cost of asking against cost of assuming;
- determine whether to answer, ask, retrieve, calculate, use knowledge, call skill, call tool, execute workflow, warn, confirm, wait, or stop;
- authorize execution scope;
- define expected outcome;
- define confidence;
- preserve explanation;
- honor principles, policy, and commit constraints;
- prevent hidden workflow transitions.

Decision must not:

- invent facts;
- override judgment substance;
- execute actions by itself;
- let tools, skills, or workflows choose the next action;
- choose a question because a field is missing;
- bypass confirmation for high-risk or irreversible actions;
- let conversation alter the selected action.

## 5. Inputs

Decision receives:

- BusinessJudgment;
- JudgmentAlternatives;
- MaterialUncertainty;
- risk level;
- reversibility;
- urgency;
- available capabilities;
- user preference;
- policy constraints;
- principle constraints;
- commit constraints;
- execution options;
- conversation needs.

## 6. Outputs

Decision produces:

- `Decision`;
- `NextBestAction`;
- `DecisionAlternatives`;
- execution authorization when relevant;
- conversation intent when communication is relevant;
- confirmation requirement when needed;
- explanation.

## 7. Semantic Objects

### Decision

The selected next move and reason.

### NextBestAction

The practical expression of the selected move.

### DecisionAlternative

A plausible next action not selected.

### DecisionConfidence

Confidence that the selected move is appropriate now.

### DecisionExplanation

Why this move was chosen over alternatives.

### ActionAuthorization

The scope of any permitted execution.

### ConfirmationRequirement

The condition requiring user approval before action or commit.

## 8. Decision Types

SME Brain may decide to:

- answer;
- ask;
- warn;
- recommend;
- explain;
- retrieve memory;
- retrieve knowledge;
- inspect evidence;
- calculate;
- call tool;
- call skill;
- invoke workflow;
- create artifact;
- confirm;
- wait;
- refuse;
- defer;
- execute;
- commit;
- stop reasoning.

## 9. Next Best Action

NextBestAction is not a workflow next step.

It is the action most likely to improve the business owner's situation now, given:

- judgment;
- expected business impact;
- risk;
- uncertainty;
- cost;
- urgency;
- reversibility;
- capability availability;
- user attention cost;
- policy and principle constraints.

## 10. Decision Confidence

Decision confidence differs from judgment confidence.

Judgment confidence concerns the assessment.

Decision confidence concerns the appropriateness of the next move.

The Brain may have low judgment confidence but high decision confidence that it should ask one focused question.

The Brain may have medium judgment confidence but high decision confidence that drafting a reversible first version is useful.

## 11. Decision Alternatives

Every meaningful Decision should preserve alternatives when stakes justify it.

Alternatives may include:

- answer now;
- ask first;
- assume and proceed;
- search memory;
- search knowledge;
- calculate;
- call skill;
- use workflow;
- warn;
- confirm;
- defer.

Decision should explain why the selected alternative dominates.

## 12. Business Impact

Decision must consider expected business impact:

- revenue;
- margin;
- cash flow;
- customer trust;
- brand;
- operational feasibility;
- risk reduction;
- time saved;
- owner clarity;
- compliance;
- learning.

The most complete action is not always the best action. The best action improves the situation relative to cost and risk.

## 13. Ownership

Decision Authority owns Decision.

Judgment informs Decision. Principles, Policy, and Commit constrain Decision. Execution carries out authorized actions. Conversation expresses the selected decision.

## 14. Allowed Dependencies

Decision may depend on:

- BusinessJudgment;
- risk and uncertainty;
- policy and principles;
- execution capability;
- user preference;
- memory and knowledge availability;
- commit requirements;
- urgency and reversibility.

## 15. Forbidden Dependencies

Decision must not depend on:

- workflow order as primary authority;
- required fields as automatic question triggers;
- skill desire for more input;
- tool availability as reason to use tool;
- response template needs;
- implementation routing;
- model confidence alone.

## 16. Explainability

Decision must explain:

- why this action;
- why now;
- why not the main alternatives;
- what uncertainty remains;
- what expected outcome it serves;
- what policy, principle, or commit constraint applies.

The explanation may be internal or user-facing depending on context.

## 17. Failure Modes

### Workflow Decision

Next action is selected by procedural state.

### Tool-Driven Decision

The Brain uses a tool because it exists.

### Skill-Driven Decision

A skill controls clarification or conversation.

### Judgment Collapse

Decision is skipped and judgment directly becomes output.

### Over-Questioning

The selected action is ask because information is absent, not because uncertainty is material.

### Under-Confirmation

The Brain proceeds with irreversible or sensitive action without approval.

## 18. Examples

### Low-Risk Content Draft

Judgment: a promotion post would help, audience is assumed but not critical.

Decision: draft now with an explicit assumption and invite refinement.

### High-Risk Pricing Change

Judgment: discount may help conversion but could hurt margin.

Decision: ask for current margin or recommend a non-discount value framing first.

### Customer Complaint

Judgment: trust risk is high.

Decision: produce a careful reply and recommend verification before promising refund if policy is unclear.

## 19. Final Standard

Decision is responsible movement.

SME Brain should not merely know what might be right. It must choose the next helpful, authorized, explainable move.

