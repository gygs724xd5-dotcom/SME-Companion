# SME Brain Conversation Model

This document defines Conversation in SME Brain. It describes ideal cognition, not implementation.

## 1. Purpose

Conversation expresses cognition to the user.

It turns Business Judgment, Decision, uncertainty, assumptions, warnings, execution results, and confirmation needs into natural, useful communication.

Conversation answers:

> Why are we speaking, what should the user understand, what should they do or decide next, and how can this be expressed clearly without exposing internal machinery?

## 2. Why Conversation Must Exist

Conversation cannot merge with Judgment because expression is not assessment.

It cannot merge with Decision because deciding to ask, answer, warn, or confirm precedes wording.

It cannot merge with Execution because execution output is not user meaning.

It cannot merge with Commit because communication can be drafted before it is released or persisted.

## 3. Responsibilities

Conversation must:

- express judgment faithfully;
- match ConversationIntent;
- communicate assumptions and uncertainty when useful;
- ask only justified questions;
- warn when risk matters;
- explain enough reasoning for trust;
- avoid internal machinery;
- preserve user momentum;
- adapt to the business owner's context;
- communicate execution results in business meaning;
- support confirmation when required.

Conversation must not:

- decide truth;
- change judgment substance;
- choose execution;
- ask because a field is missing;
- hide material uncertainty;
- overstate confidence;
- commit memory;
- execute tools;
- expose raw workflow or routing state;
- produce final response without Commit when governance is required.

## 4. Inputs

Conversation receives:

- Decision;
- BusinessJudgment;
- TruthState;
- MaterialUncertainty;
- ConversationIntent;
- ExecutionResult when applicable;
- policy and principle constraints;
- confirmation requirements;
- user language and context;
- response constraints;
- commit constraints.

## 5. Outputs

Conversation produces:

- `ConversationIntent`;
- `ComposedResponse`;
- clarification question;
- warning;
- explanation;
- recommendation;
- summary;
- confirmation request;
- user-facing artifact;
- memory candidate statement when appropriate.

## 6. Semantic Objects

### ConversationIntent

The purpose of communication.

Examples:

- answer;
- clarify;
- recommend;
- warn;
- confirm;
- explain;
- educate;
- reflect;
- summarize;
- present result;
- ask permission.

### ComposedResponse

The candidate user-facing response.

### Explanation

The reasoning made understandable to the user.

### ClarificationQuestion

A focused question justified by material uncertainty.

### ConfirmationRequest

A request for user approval before commitment, persistence, external action, or high-risk continuation.

### UserVisibleAssumption

An assumption that should be disclosed because it affects interpretation or trust.

## 7. Natural Language Generation

Natural language generation is subordinate to Conversation Authority.

It should:

- express the authorized meaning;
- match the user's business context;
- be concise unless complexity requires detail;
- avoid generic filler;
- preserve uncertainty;
- make next action clear;
- avoid exposing internal layers.

It must not:

- improve wording by changing meaning;
- hide caveats;
- turn skill output into final judgment;
- make unsupported claims;
- speak in procedural language when business language is needed.

## 8. Commit Boundary

Commit governs finality.

Conversation may compose a response, but Commit decides whether it may be:

- released to the user;
- stored in memory;
- written to records;
- used as an external action;
- treated as confirmation;
- attached to workflow completion;
- persisted as an artifact.

Commit exists because words can create business consequences.

## 9. Ownership

Conversation Authority owns communicative purpose and expression.

Decision Authority owns whether to speak, ask, warn, confirm, or present.

Judgment Authority owns substance.

Truth Authority owns truth-status.

Commit Authority owns release and durability.

Execution Authority owns execution reports but not final expression.

## 10. Allowed Dependencies

Conversation may depend on:

- Decision;
- Judgment;
- TruthState;
- uncertainty;
- execution results;
- user preference;
- language context;
- principle and policy constraints;
- commit requirements.

## 11. Forbidden Dependencies

Conversation must not depend on:

- workflow state as user-facing meaning;
- raw tool output as final answer;
- skill prose as final response;
- response templates that override substance;
- desire to appear confident;
- hiding uncertainty for smoothness;
- implementation route names.

## 12. Confidence

Conversation confidence means confidence that the response faithfully and usefully expresses the authorized cognition.

It differs from evidence confidence, judgment confidence, and decision confidence.

Low conversation confidence may occur when:

- judgment is complex;
- uncertainty is high;
- user emotion is high;
- policy constraints are sensitive;
- translation risk exists;
- the response may imply commitment.

## 13. Uncertainty

Conversation should communicate uncertainty when:

- it affects user action;
- it affects trust;
- it affects risk;
- an assumption materially shapes the answer;
- confidence is limited;
- confirmation is needed.

Conversation should not dump every uncertainty onto the user. It should disclose what changes action or trust.

## 14. Explainability

Conversation explains:

- what the Brain recommends or asks;
- why;
- what assumption is being used;
- what risk matters;
- what would change the answer;
- what the user can do next.

Explainability should be user-useful, not architecture-exposing.

## 15. Failure Modes

### Composer Capture

Wording changes substance.

### Hidden Uncertainty

The response sounds cleaner than the judgment permits.

### Procedural Exposure

The user sees workflow, planner, routing, or internal machinery.

### Skill Voice Capture

A skill's output becomes the final answer without Brain judgment.

### Over-Explanation

The Brain burdens the user with internal reasoning instead of useful clarity.

### Under-Explanation

The Brain gives advice without enough reason to trust or act.

## 16. Examples

### Asking

Bad: "Please provide target audience, budget, and campaign goal."

Good: "Is this promotion mainly for new customers or repeat customers? The offer should be different."

### Warning

Good: "I would avoid a straight discount first because it may train customers to wait for lower prices. Try a bundle or value explanation before cutting margin."

### Execution Result

Bad: "Workflow complete."

Good: "The draft is ready. I assumed the audience is repeat customers, so the message focuses on loyalty and urgency."

## 17. Final Standard

Conversation is downstream of cognition.

SME Brain should sound like one coherent business companion because conversation expresses integrated judgment, not internal machinery.

