# SME Brain Perspective Model

This document defines Perspective as a constitutional cognitive layer of SME Brain. It describes ideal cognition, not implementation.

Perspective is doctrine only until a future runtime is explicitly designed.

## 1. Purpose

Perspective identifies the Situation Frame represented by validated reality.

Perspective answers only:

> What kind of situation does this reality represent?

Perspective does not explain why the situation happened. It does not decide what should be done. It does not evaluate which explanation is best.

## 2. Definition

Perspective is the process of recognizing and naming the kind of business situation now represented by the available, truth-labeled reality.

It transforms:

```text
Validated Reality
    -> Recognized Situation Frame
```

Examples:

```text
Customers up
Revenue up
Profit down
    -> Profit Compression
```

```text
Inventory remaining: 3 units
    -> Low Inventory Risk
```

```text
Revenue declining for several weeks
    -> Sales Decline
```

Perspective identifies the frame only.

## 3. Why Perspective Must Exist

Perspective exists before Knowledge because SME Brain cannot know which experience, concepts, patterns, or principles to recall until it knows what kind of situation it is facing.

Without Perspective, Knowledge retrieval risks becoming generic, domain-keyword driven, or premature. A sales metric could trigger sales knowledge, finance knowledge, operations knowledge, or inventory knowledge. Perspective determines the situation frame first.

Perspective cannot merge with Business Situation because Business Situation organizes the active business reality under attention, while Perspective recognizes the kind of situation represented by validated reality.

Perspective cannot merge with Evidence Gap Intelligence because missing-evidence diagnosis is not frame recognition.

Perspective cannot merge with Knowledge because Knowledge supplies accumulated experience and doctrine after the situation frame has been identified.

Perspective cannot merge with Business Judgment because Judgment evaluates. Perspective does not evaluate.

## 4. Responsibilities

Perspective must:

- identify Situation Frames;
- produce candidate frames;
- expose frame confidence;
- explain frame selection diagnostics;
- preserve uncertainty when the frame is ambiguous;
- surface Unknown Situation when no responsible frame can be selected.

Perspective must not:

- recommend actions;
- diagnose root causes;
- make business judgments;
- choose decisions;
- trigger workflows;
- modify business memory;
- modify evidence;
- modify truth status;
- modify business situation;
- modify routing;
- modify planner behavior;
- modify responses;
- modify execution;
- modify commit.

## 5. Inputs

Perspective may receive:

- BusinessSituation;
- TruthState;
- validated facts;
- assumptions and reliance boundaries;
- EvidenceGapProfile diagnostics;
- material uncertainty;
- known constraints;
- relevant current signals.

Perspective must not fill missing evidence, call tools, search externally, execute workflows, or write memory.

## 6. Outputs

Perspective produces Situation Frame diagnostics.

Future architectural outputs may include:

- `selected_frame`;
- `candidate_frames`;
- `frame_confidence`;
- `frame_selection_reason`;
- unresolved ambiguity;
- evidence limitations affecting frame confidence.

These are doctrine categories, not implementation fields.

## 7. Situation Frame

A Situation Frame is a recognized class of business reality.

It names what kind of situation the current validated reality represents without explaining causes, evaluating implications, or choosing action.

Examples:

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

These examples are not a runtime registry.

## 8. Ownership

Perspective Authority owns Situation Frame recognition.

Evidence Gap Intelligence owns missing support.

Knowledge Authority owns relevant accumulated experience, principles, patterns, methods, and doctrine.

Business Judgment Authority owns evaluation.

Decision Authority owns action selection.

## 9. Allowed Dependencies

Perspective may depend on:

- Business Situation framing;
- Truth Status classifications;
- Evidence Gap diagnostics;
- current validated reality;
- known material uncertainty;
- business ontology for naming Situation Frames.

## 10. Forbidden Dependencies

Perspective must not depend on:

- workflow availability;
- skill availability;
- planner convenience;
- routing labels;
- desired response format;
- execution convenience;
- memory write needs;
- the easiest recommendation to explain.

## 11. Confidence

Frame confidence means confidence that the selected Situation Frame matches the validated reality.

It is not confidence that:

- the cause is known;
- the business is healthy or unhealthy;
- a recommendation is correct;
- a decision should be taken;
- execution should proceed.

Frame confidence should be lower when:

- evidence is thin;
- truth status is uncertain;
- missing evidence could change the frame;
- multiple frames fit the same facts;
- the situation is new or poorly represented by known frames.

## 12. Uncertainty

Perspective uncertainty asks:

- Is this Profit Compression or Pricing Pressure?
- Is this Sales Decline or Seasonality?
- Is this Inventory Risk or Supplier Disruption?
- Is this Demand Weakness or Capacity Constraint?
- Is no responsible frame currently selectable?

Perspective uncertainty does not ask:

- Why did this happen?
- What should the owner do?
- Which explanation is best?
- Which action is most useful?

## 13. Explainability

Perspective diagnostics should explain:

- which frame was selected;
- which candidate frames were considered;
- why the selected frame fits the validated reality;
- what evidence limitations reduced confidence;
- why a frame remains unknown when applicable.

For example:

```text
Selected frame: Profit Compression.
Reason: Revenue and customer activity are up while profit is down.
Confidence limit: Cost evidence is not yet detailed enough to explain the cause.
```

The explanation identifies the frame. It does not diagnose the cause.

## 14. Failure Modes

### Cause Leakage

The layer explains why the situation happened.

### Recommendation Leakage

The layer suggests what should be done.

### Judgment Leakage

The layer evaluates which explanation or strategy is best.

### Domain Capture

A domain label such as sales, finance, or inventory is treated as the situation frame without recognizing the actual business condition.

### Workflow Capture

Workflow fields or planner needs determine the frame.

### Over-Framing

The layer selects a precise frame when validated reality supports only Unknown Situation or broad ambiguity.

### Knowledge Capture

General business knowledge forces the frame before current truth-labeled reality supports it.

## 15. Final Standard

Perspective prevents premature knowledge retrieval, judgment, and decision.

SME Brain should not ask "What should we do?" at the Perspective layer.

It should ask:

> What kind of situation does this reality represent?
