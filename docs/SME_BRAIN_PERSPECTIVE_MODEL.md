# SME Brain Perspective Model

This document defines how SME Brain uses perspectives to interpret a business situation. It describes ideal cognition, not implementation.

## 1. Purpose

Perspective is the interpretive lens applied to a situation before judgment.

Experienced business decision-makers do not view every problem from one angle. They consider financial impact, customer trust, operations, brand, ethics, owner constraints, market timing, execution feasibility, and risk.

Perspective answers:

> From which business lenses should this situation be evaluated before judgment is formed?

## 2. Why Perspective Must Exist

Perspective cannot merge with Business Situation because the situation describes what is happening; perspective decides how to look at it.

It cannot merge with Evidence because evidence evaluates information quality, while perspective selects interpretive relevance.

It cannot merge with Knowledge because knowledge supplies content, methods, rules, and patterns; perspective decides which kinds of knowledge matter.

It cannot merge with Judgment because judgment synthesizes perspectives and chooses a reasoned assessment.

## 3. Responsibilities

Perspective must:

- identify relevant business lenses;
- prevent premature single-domain framing;
- expose competing stakeholder concerns;
- determine which knowledge categories are needed;
- identify which risks and opportunities matter;
- ensure principles and policies are considered when relevant;
- support multi-perspective judgment;
- preserve minority perspectives when they materially change risk.

Perspective must not:

- decide the final answer;
- override Truth Status;
- select execution;
- become a domain router;
- let a domain label claim cognitive authority;
- ignore principles or policy because a commercial perspective is stronger.

## 4. Inputs

Perspective receives:

- BusinessSituation;
- TruthState;
- material uncertainty;
- risks;
- opportunities;
- constraints;
- objectives;
- stakeholder context;
- policies;
- principles;
- domain signals;
- expected consequence.

## 5. Outputs

Perspective produces a `PerspectiveSet`.

`PerspectiveSet` includes:

- selected perspectives;
- why each perspective matters;
- priority or salience;
- risks each perspective sees;
- opportunities each perspective sees;
- knowledge needs;
- conflict between perspectives;
- perspectives intentionally excluded and why.

## 6. Semantic Objects

### Perspective

A business lens for interpreting the situation.

### PerspectiveSet

The selected group of perspectives relevant to judgment.

### PerspectiveWeight

The current importance of a perspective for this situation.

### PerspectiveConflict

A tension between perspectives, such as revenue versus trust or speed versus accuracy.

### StakeholderLens

A perspective tied to a stakeholder, such as owner, customer, staff, supplier, regulator, platform, or community.

## 7. Standard Perspectives

SME Brain should support at least:

- financial perspective;
- customer perspective;
- operational perspective;
- sales perspective;
- marketing perspective;
- brand perspective;
- strategic perspective;
- policy perspective;
- principle perspective;
- execution perspective;
- risk perspective;
- owner capacity perspective;
- market perspective;
- learning perspective.

Domain perspectives such as pricing, sales, finance, marketing, customer service, inventory, and operations should live here, not as constitutional authority layers.

## 8. Ownership

Perspective Authority owns lens selection and perspective conflict surfacing.

Business Judgment Authority owns synthesis across perspectives.

Knowledge Authority owns the quality of knowledge used by each perspective.

Principles and Policy Authorities constrain judgment when their perspectives are relevant.

## 9. Allowed Dependencies

Perspective may depend on:

- Business Situation;
- TruthState;
- EvidenceSet;
- Knowledge categories;
- stakeholder model;
- risk model;
- principle and policy triggers;
- business domain ontology.

## 10. Forbidden Dependencies

Perspective must not depend on:

- workflow availability;
- skill availability;
- current implementation modules;
- keyword-only domain matching;
- desired response format;
- execution convenience;
- the easiest answer.

## 11. Confidence

Perspective confidence means confidence that a lens is relevant and weighted appropriately.

It is not confidence that the final judgment is correct.

Perspective confidence should be lower when:

- the situation is ambiguous;
- evidence is thin;
- domains overlap;
- stakes are high;
- important stakeholders are unclear;
- multiple perspectives conflict.

## 12. Uncertainty

Perspective uncertainty asks:

- Are we looking at the right problem?
- Is this mainly financial, operational, customer, strategic, or brand-related?
- Are we missing a stakeholder?
- Is a hidden risk lens needed?
- Does a principle or policy lens change what is acceptable?

This uncertainty can justify asking only when the selected perspective would materially change the next action.

## 13. Explainability

Perspective should explain:

- why a lens was used;
- why a lens was not used;
- which perspectives conflict;
- how perspective weighting affected judgment;
- why a non-obvious lens matters.

For user-facing communication, this often appears as concise reasoning:

> I would look at this as both a margin issue and a customer trust issue.

## 14. Failure Modes

### Single-Lens Capture

The Brain treats every issue as sales, marketing, finance, or workflow.

### Domain Authority Confusion

Domain labels become final authority.

### Principle Blindness

Commercial benefit hides ethical or trust risk.

### Policy Blindness

Advice ignores business rules or compliance constraints.

### Over-Framing

The Brain applies too many lenses and slows down simple help.

### Perspective Bias

The first detected lens dominates all later reasoning.

## 15. Examples

### Customer Says Price Is Expensive

Relevant perspectives:

- pricing;
- sales;
- customer trust;
- margin;
- brand positioning.

Judgment should not default to discounting. It should evaluate whether the issue is value communication, wrong audience, margin problem, or service trust problem.

### Staff Shortage

Relevant perspectives:

- operations;
- customer service;
- owner capacity;
- financial;
- risk.

The Brain should not only suggest hiring. It may consider hours, menu simplification, demand smoothing, automation, or service expectations.

## 16. Final Standard

Perspective prevents premature judgment.

SME Brain should not ask "Which domain owns this?" first. It should ask "Which lenses must be considered for a responsible business judgment?"

