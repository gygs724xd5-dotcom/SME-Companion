# SME Brain Perspective Architecture Review

Architecture Review IX

SME Companion V5.8.0

Perspective Architecture Constitution

Status: Doctrine Accepted For Future Runtime Design

Scope: Architecture only. No runtime, Python, module contract, API, prompt, workflow, planner, routing behavior, response behavior, diagnostics implementation, memory mutation, execution behavior, or implementation mechanism is defined here.

## 1. Purpose

Perspective is the constitutional layer that identifies the Situation Frame represented by validated reality.

It answers only:

> What kind of situation does this reality represent?

It does not answer:

> Why did this happen?

It does not answer:

> What should we do?

It does not answer:

> Who is correct?

It does not answer:

> Which solution is best?

Perspective exists because humans do not begin understanding by deciding. They first recognize what kind of situation they are in. SME Brain needs the same cognitive step before recalling knowledge, evaluating implications, or choosing action.

## 2. Constitutional Position

The cognitive runtime is:

```text
Reality
    -> Perception
    -> Business Situation
    -> Evidence
    -> Truth Status
    -> Evidence Gap Intelligence
    -> Perspective
    -> Knowledge
    -> Business Judgment
    -> Decision
    -> Execution
    -> Conversation
    -> Commit
```

Perspective sits after Evidence Gap Intelligence because frame recognition must know the limits of available evidence before naming the situation.

Perspective sits before Knowledge because SME Brain cannot responsibly recall relevant experience until it knows which kind of situation is present.

## 3. Responsibilities

Perspective must:

- identify Situation Frames;
- produce candidate frames;
- expose frame confidence;
- explain frame selection diagnostics;
- preserve ambiguity when several frames are plausible;
- select Unknown Situation when validated reality does not support a responsible frame.

Perspective must remain diagnostic and recognitional. It names the situation type; it does not interpret causes or decide consequences.

## 4. Non-responsibilities

Perspective must not:

- recommend actions;
- diagnose root causes;
- make business judgments;
- choose decisions;
- trigger workflows;
- modify business memory;
- modify evidence;
- modify truth runtime;
- modify business situation;
- modify routing;
- modify planner behavior;
- modify workflow behavior;
- modify responses;
- modify execution;
- modify commit.

Perspective must not become a domain router, workflow precondition checker, response planner, or recommendation engine.

## 5. Inputs

Perspective may receive:

- Business Situation frame;
- Truth Status classifications;
- validated facts;
- assumptions and reliance boundaries;
- Evidence Gap Intelligence diagnostics;
- material uncertainty;
- known constraints;
- relevant current signals.

Perspective may use these inputs only to recognize the situation frame. It must not use them to fill missing evidence, evaluate strategy, execute retrieval, or decide action.

## 6. Outputs

Perspective produces frame diagnostics.

Future architectural outputs may include:

- `selected_frame`;
- `candidate_frames`;
- `frame_confidence`;
- `frame_selection_reason`;
- unresolved ambiguity;
- evidence limitations affecting frame selection.

These are doctrine categories only. They do not define runtime fields, schemas, API contracts, or diagnostics behavior.

## 7. Situation Frame Definition

A Situation Frame is a recognized class of business reality.

It names the type of business situation represented by validated reality.

A Situation Frame is not:

- a root-cause diagnosis;
- a recommendation;
- a decision;
- a workflow route;
- a domain label by itself;
- a final business judgment.

Examples:

```text
Reality:
Customers up
Revenue up
Profit down

Situation Frame:
Profit Compression
```

```text
Reality:
Inventory remaining: 3 units

Situation Frame:
Low Inventory Risk
```

```text
Reality:
Revenue declining for several weeks

Situation Frame:
Sales Decline
```

## 8. Candidate Frames

Candidate Situation Frames may eventually include:

- Profit Compression;
- Sales Decline;
- Inventory Risk;
- Cash Flow Stress;
- Demand Surge;
- Demand Weakness;
- Operational Bottleneck;
- Capacity Constraint;
- Supplier Disruption;
- Pricing Pressure;
- Customer Retention Risk;
- Growth Opportunity;
- Seasonality;
- Market Expansion;
- Competitive Pressure;
- Unknown Situation.

This list is illustrative only. It is not a registry, enum, runtime configuration, or implementation requirement.

## 9. Diagnostics

Perspective diagnostics should make frame recognition inspectable.

Diagnostics should eventually explain:

- which frame was selected;
- which candidate frames were considered;
- why the selected frame fits the validated reality;
- what confidence level applies;
- what evidence limitations reduce confidence;
- why Unknown Situation was selected when no frame is responsible.

Diagnostics must not include:

- action recommendations;
- cause diagnosis;
- strategy ranking;
- workflow selection;
- response wording;
- execution instructions.

## 10. Constitutional Invariants

Perspective shall only:

- identify Situation Frames;
- produce candidate frames;
- expose frame confidence;
- explain frame selection diagnostics.

Perspective shall never:

- recommend actions;
- diagnose root causes;
- make business judgments;
- choose decisions;
- trigger workflows;
- modify business memory;
- modify evidence;
- modify truth runtime;
- modify business situation;
- modify routing;
- modify planner behavior;
- modify workflow behavior;
- modify responses;
- modify execution;
- modify commit.

## 11. Failure Modes

### Cause Leakage

Perspective explains why the situation happened.

Consequence: Judgment is bypassed and hypotheses are presented before evaluation.

### Recommendation Leakage

Perspective suggests what should be done.

Consequence: Decision and Judgment collapse into frame recognition.

### Judgment Leakage

Perspective evaluates which cause, option, or strategy is best.

Consequence: the layer no longer answers only what kind of situation this is.

### Domain Capture

Perspective treats a domain label as the frame.

Example: calling the situation "finance" instead of recognizing Profit Compression.

### Workflow Capture

Workflow requirements or planner fields determine the selected frame.

Consequence: procedural needs masquerade as cognition.

### Evidence Overreach

Perspective selects a confident frame despite missing or weak evidence that could materially change the frame.

Consequence: Knowledge and Judgment are steered by an unsupported frame.

### Unknown Situation Avoidance

Perspective refuses to admit that the current reality does not yet support a recognized frame.

Consequence: false precision enters downstream reasoning.

## 12. Relationship To Knowledge

Perspective selects the situation.

Knowledge supplies accumulated experience.

Perspective may say:

```text
This is Profit Compression.
```

Knowledge may later say:

```text
Experienced businesses often observe Profit Compression when costs, mix, discounting, waste, or fulfillment burdens change.
```

Knowledge contains generalizable business experience, doctrine, principles, methods, and patterns. Perspective does not contain that experience. It only recognizes which situation frame should guide knowledge recall.

Knowledge must not force a frame before Perspective has recognized one from validated reality.

## 13. Relationship To Judgment

Perspective recognizes.

Judgment evaluates.

Perspective may say:

```text
This is Sales Decline.
```

Judgment may later say:

```text
Based on current evidence, marketing weakness is the most plausible explanation.
```

Perspective must never determine plausibility, weigh explanations, or decide which interpretation is best. Those are Judgment responsibilities.

## 14. Relationship To Decision

Perspective identifies the frame.

Decision chooses the next authorized action.

Perspective may say:

```text
Inventory Risk.
```

Decision may later say:

```text
Reorder inventory.
```

Perspective must never choose action, decide to ask, decide to retrieve, decide to execute, or decide to respond.

## 15. Conceptual Inspiration

This section is conceptual inspiration only. It is not scientific proof. It is not theological doctrine for the runtime. It is not a functional dependency, religious requirement, implementation rule, or source of authority.

One inspiration for the Perspective layer comes from the observation that, in Islamic tradition, humanity begins not with decision-making but with learning the names of things.

From an architectural perspective, this suggests an important cognitive sequence:

```text
Observe
    -> Recognize
    -> Name / Frame
    -> Recall Knowledge
    -> Judge
    -> Decide
```

The Perspective layer therefore represents the act of recognizing and framing reality before experience and judgment are applied.

Again, this is conceptual inspiration only. SME Brain does not depend on religious doctrine, and the Perspective layer has no religious runtime requirement.

## 16. Future Runtime Roadmap

Future Perspective runtime work should follow the standard cognitive layer lifecycle:

```text
Runtime Foundation
    -> Registry
    -> Diagnostics
    -> Runtime State
    -> Behavior
```

### V5.8.1 Perspective Runtime Foundation

Define purpose, inputs, outputs, constitutional boundaries, frame confidence concept, diagnostic shape, and invariants.

No routing, planner, workflow, response, retrieval, memory, execution, judgment, decision, or commit behavior should be introduced.

### V5.8.2 Situation Frame Registry

Define recognized frame names, aliases, frame criteria, ambiguity handling, and Unknown Situation behavior.

### V5.8.3 Frame Diagnostics

Define how selected frame, candidate frames, confidence, selection reason, and evidence limitations are exposed for constitutional accountability.

### V5.8.4 Runtime State

Define a stable frame state object only after foundation, registry, and diagnostics are accepted.

### V5.8.5 Behavior

Only after doctrine, registry, diagnostics, and runtime state are stable may behavior be considered. Behavior must remain subordinate to Knowledge, Judgment, Decision, Conversation, and Commit.

## 17. Architecture Decision

Perspective is a required constitutional layer.

It owns Situation Frame recognition.

It must remain separate from Evidence Gap Intelligence, Knowledge, Business Judgment, Decision, Execution, Conversation, Commit, Workflow, Planner, Routing, and Authority.

The official boundary is:

```text
Evidence represents information.
Truth Status evaluates reliance.
Evidence Gap Intelligence identifies missing support.
Perspective identifies the Situation Frame.
Knowledge recalls relevant experience.
Business Judgment evaluates business implications.
Decision selects action.
Execution performs authorized work.
Conversation expresses faithfully.
Commit governs finality.
Authority governs responsibility.
```

The constitutional standard is:

> Perspective names the kind of situation before Knowledge explains experience, Judgment evaluates implications, or Decision chooses action.
