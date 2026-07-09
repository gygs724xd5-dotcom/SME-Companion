# SME Brain Knowledge Model

This document defines what Knowledge means in SME Brain. It describes ideal cognition, not implementation.

## 1. Purpose

Knowledge is structured understanding that improves interpretation, judgment, decision, execution, or conversation.

Knowledge is not one object. It includes facts, policies, principles, rules, skills, experience, reasoning patterns, procedures, methods, and domain models.

Knowledge answers:

> What general, stored, learned, governed, or reusable understanding should inform this business situation?

## 2. Why Knowledge Must Exist

Knowledge cannot merge with Evidence because knowledge is often general, while evidence bears on this situation.

Knowledge cannot merge with Truth Status because general knowledge is not automatically local truth.

Knowledge cannot merge with Perspective because Perspective identifies the Situation Frame; Knowledge supplies reusable experience, doctrine, methods, rules, and patterns relevant to that frame.

Knowledge cannot merge with Judgment because knowledge informs assessment but does not decide what helps now.

## 3. Knowledge Categories

### Facts

Claims treated as true within a scope. Facts may be business-specific, domain-general, or external.

### Policies

Organization-specific rules, permissions, approval requirements, and constraints.

### Principles

Durable values and business ethics such as honesty, fairness, customer respect, transparency, and harm avoidance.

### Rules

Operational or domain rules that guide action, such as margin thresholds, refund conditions, platform restrictions, or inventory reorder rules.

### Business Skills

Bounded capabilities that can perform work under Brain supervision.

The V5.15.0 Business Skill Schema contract defines the reusable skill fields, evidence requirements, reasoning contract, response boundaries, lifecycle, and diagnostics keys for these capabilities.

### Experience

Patterns learned from prior cases, business history, outcomes, or observed practice.

### Reasoning Patterns

Reusable ways of thinking, such as margin analysis, customer objection analysis, root-cause diagnosis, campaign fit analysis, cash flow triage, and trade-off analysis.

### Procedures

Ordered methods for execution when a task is known and procedural reliability matters.

### Domain Models

Structured understanding of domains such as pricing, marketing, sales, customer service, finance, operations, inventory, compliance, and strategy.

## 4. Responsibilities

Knowledge must:

- identify relevant knowledge by situation and recognized Situation Frame;
- separate general knowledge from local evidence;
- preserve applicability limits;
- expose decay and freshness where relevant;
- distinguish principles, policies, rules, skills, and procedures;
- avoid generic advice when local evidence should dominate;
- support judgment with methods and patterns;
- support execution with procedures only after decision.

Knowledge must not:

- decide the answer;
- override local truth without justification;
- own conversation;
- force workflow;
- turn skills into authorities;
- treat policies as universal principles;
- treat principles as detailed business policy;
- treat procedures as cognition.

## 5. Inputs

Knowledge receives:

- BusinessSituation;
- TruthState;
- Perspective diagnostics;
- EvidenceSet;
- material uncertainty;
- domain needs;
- principle triggers;
- policy triggers;
- skill needs;
- execution needs;
- user constraints.

## 6. Outputs

Knowledge produces a `KnowledgeContext`.

`KnowledgeContext` includes:

- KnowledgeReferences;
- applicable principles;
- applicable policies;
- applicable rules;
- domain concepts;
- reasoning patterns;
- available skills;
- available procedures;
- known limitations;
- freshness and decay notes;
- applicability explanation.

## 7. Semantic Objects

### KnowledgeReference

A unit of knowledge relevant to the situation.

### Principle

A durable value constraint.

### Policy

An organization-specific rule.

### BusinessRule

A practical rule affecting action.

### ReasoningPattern

A reusable method of analysis.

### DomainModel

A structured representation of a business domain.

### Procedure

A reliable execution sequence.

### SkillCapability

A bounded capability that may be invoked by Decision and Execution.

### ExperiencePattern

A learned pattern from prior business cases or memory.

## 8. Ownership

Knowledge Authority owns knowledge quality, categorization, decay, and applicability.

Policy Authority owns organization-specific policy meaning.

Principles Authority owns universal principle meaning.

Skill Authority owns bounded skill capability integrity.

Execution Authority owns procedures only after a Decision authorizes execution.

Judgment Authority owns synthesis.

## 9. Allowed Dependencies

Knowledge may depend on:

- Perspective diagnostics for frame-specific retrieval;
- TruthState for local fact constraints;
- EvidenceSet for situation relevance;
- Memory for experience patterns;
- policy stores;
- principle sets;
- domain models;
- skill registry;
- procedure library.

## 10. Forbidden Dependencies

Knowledge must not depend on:

- workflow state as the primary retrieval key;
- current skill availability to decide what knowledge matters;
- response style;
- implementation folder structure;
- tool output without evidence evaluation;
- generic domain match without situation relevance.

## 11. Confidence

Knowledge confidence means confidence that a knowledge reference is valid, current, relevant, and applicable.

It should consider:

- durability;
- source quality;
- domain fit;
- local evidence fit;
- recency;
- policy scope;
- principle priority;
- known exceptions.

## 12. Uncertainty

Knowledge uncertainty arises when:

- the domain is unclear;
- the rule scope is unclear;
- local facts may override general guidance;
- policy is missing or ambiguous;
- principle conflict exists;
- experience pattern may not fit;
- procedure requirements are unknown.

This uncertainty should inform Judgment. It should not automatically become a question.

## 13. Explainability

Knowledge should explain:

- what reference was used;
- why it applies;
- what its limits are;
- whether it is a principle, policy, rule, skill, procedure, pattern, or fact;
- how it influenced judgment.

## 14. Failure Modes

### Knowledge Monolith

Facts, policies, principles, skills, and procedures are treated as one object.

### Generic Advice

Knowledge ignores local truth.

### Procedure Capture

Procedures dictate cognition.

### Skill Capture

Available skills determine what the Brain thinks the user needs.

### Policy-Principle Confusion

Local policy is treated as moral truth, or principles are mistaken for concrete operating rules.

### Stale Knowledge

Outdated market, platform, legal, pricing, or operational guidance shapes current advice.

## 15. Examples

### Discount Request

Knowledge may include pricing psychology, margin rules, customer trust principles, discount policy, and sales objection patterns.

It should not conclude "give discount." Judgment decides.

### Refund Complaint

Knowledge may include refund policy, fairness principles, service recovery patterns, reputation risk, and customer communication skill capability.

Conversation should receive judgment, not raw policy.

## 16. Final Standard

Knowledge is disciplined reusable understanding.

SME Brain must separate what is generally known, locally true, morally required, organizationally permitted, procedurally executable, and judgment-worthy.
