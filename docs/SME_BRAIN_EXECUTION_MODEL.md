# SME Brain Execution Model

This document defines Execution in SME Brain. It describes ideal cognition, not implementation.

## 1. Purpose

Execution carries out authorized actions.

Execution is where a decision becomes operational work: tool use, skill call, workflow run, calculation, retrieval, artifact generation, OCR, transformation, or external action.

Execution answers:

> What has been authorized, what will be done within scope, what result was produced, and what limitations or failures occurred?

## 2. Why Execution Must Exist

Execution cannot merge with Decision because choosing an action is different from performing it.

It cannot merge with Judgment because execution capability does not determine what is wise.

It cannot merge with Conversation because execution output must be interpreted before user communication.

It cannot merge with Commit because execution may produce candidate effects that still require final governance.

## 3. Responsibilities

Execution must:

- perform only authorized actions;
- preserve execution scope;
- select appropriate execution mechanism after Decision;
- run workflows only as subordinate procedures;
- call tools or skills within bounded authority;
- report results, failures, limitations, and side effects;
- produce evidence or artifacts for further judgment;
- avoid expanding its own scope;
- request confirmation when required by Decision or Commit.

Execution must not:

- decide whether an action is wise;
- decide whether an action is permitted;
- ask user questions on its own;
- own conversation;
- own business reasoning;
- modify truth-status without Evidence and Truth review;
- persist memory by itself;
- treat workflow completion as business success.

## 4. Inputs

Execution receives:

- Decision;
- ActionAuthorization;
- ExecutionPlan if needed;
- scope constraints;
- required inputs;
- allowed tools;
- allowed skills;
- allowed workflow;
- policy constraints;
- confirmation requirements;
- commit constraints.

## 5. Outputs

Execution produces:

- `ExecutionPlan`;
- `ExecutionResult`;
- artifacts;
- tool outputs;
- skill results;
- workflow results;
- failures;
- limitations;
- side effects;
- new evidence;
- commit candidates.

## 6. Semantic Objects

### ExecutionPlan

A bounded plan for carrying out an authorized action.

### ExecutionStep

A unit of operational work inside an execution plan.

### ExecutionResult

The outcome of execution.

### ToolCallResult

The bounded result of a tool.

### SkillResult

The bounded result of a skill.

### WorkflowRun

A procedural execution sequence authorized by Decision.

### Artifact

A produced object such as draft, calculation, summary, table, plan, or document.

### SideEffect

Any external, durable, or state-changing consequence.

## 7. Workflow Position

Workflow must remain execution only.

Workflow is useful when:

- the task is procedural;
- order matters;
- required inputs are genuinely necessary for safe execution;
- repeatability matters;
- consistency matters more than interpretation.

Workflow must not:

- own conversation;
- define the business situation;
- decide what the user needs;
- ask because fields are missing;
- block useful help when judgment can proceed;
- declare business success because procedural completion occurred.

Workflow asks:

> What procedure should be carried out?

Judgment asks:

> What would help this business owner now?

Decision asks:

> Should this procedure be used now?

## 8. Ownership

Execution Authority owns carrying out authorized actions.

Decision Authority owns action selection.

Business Judgment Authority owns business reasoning.

Tool Authority owns tool-scope output.

Skill Authority owns skill-scope output.

Commit Authority owns durable and external finality.

Conversation Authority owns user expression.

## 9. Allowed Dependencies

Execution may depend on:

- Decision authorization;
- execution scope;
- tools;
- skills;
- workflows;
- procedures;
- policy constraints;
- commit constraints;
- required operational inputs;
- confirmation status.

## 10. Forbidden Dependencies

Execution must not depend on:

- its own ability as justification for action;
- workflow readiness as business readiness;
- skill-required fields as user questions;
- tool output as truth;
- response needs;
- hidden expansion of scope;
- direct memory persistence.

## 11. Confidence

Execution confidence means confidence that the action can be carried out successfully within scope.

It is not business judgment confidence.

Execution confidence should consider:

- input sufficiency for execution;
- tool reliability;
- skill reliability;
- procedure fit;
- failure likelihood;
- reversibility;
- side effect risk.

## 12. Uncertainty

Execution uncertainty concerns operational feasibility:

- missing operational inputs;
- unclear authorization;
- tool limits;
- skill limits;
- external system uncertainty;
- workflow precondition uncertainty;
- side effect uncertainty.

Execution uncertainty should return to Decision, Judgment, or Commit when it affects business meaning, authorization, or finality.

## 13. Explainability

Execution should explain:

- what was authorized;
- what was done;
- what was not done;
- what failed;
- what result was produced;
- what limitations apply;
- whether new evidence or commit candidates exist.

## 14. Failure Modes

### Execution Capture

Execution decides what should be done because it knows how to do it.

### Workflow Capture

Workflow becomes conversation owner.

### Tool Capture

Tool output becomes final truth.

### Skill Capture

Skill output becomes final judgment or final response.

### Scope Creep

Execution performs actions beyond authorization.

### Hidden Side Effects

Execution creates durable or external effects without Commit.

## 15. Examples

### Cost Calculation

Decision authorizes calculation.

Execution performs arithmetic and returns result, assumptions, missing operational inputs, and confidence. Judgment decides what the result means for pricing.

### Content Skill

Decision authorizes content generation.

Execution calls a content skill. The skill returns a draft and limitations. Conversation expresses it only after judgment and commit checks.

### Receipt Workflow

Decision authorizes receipt extraction.

Execution runs OCR and structured extraction. Truth Status evaluates extracted values before they become facts.

## 16. Final Standard

Execution is disciplined action under authorization.

SME Brain must preserve this rule:

> Execution can do work, but it cannot decide why the work matters.

