# SME Brain Evidence Gap Intelligence Architecture Review

Architecture Review VIII

Evidence Gap Intelligence Runtime Constitution

Status: Doctrine Accepted For Future Runtime Design

Scope: Architecture only. No runtime, Python, module contract, API, prompt, workflow, planner, memory mutation, routing behavior, response behavior, or implementation mechanism is defined here.

## 1. Purpose

Evidence Gap Intelligence is the constitutional layer that determines what material evidence is still missing.

It answers:

> What evidence is still required?

It does not answer:

> What evidence currently exists?

Evidence already owns that responsibility.

It does not answer:

> What kind of situation does this reality represent?

Perspective owns Situation Frame recognition.

Evidence Gap Intelligence exists because a business advisor should not ask generic clarification questions when the evidence gap is knowable. If SME Brain already knows which missing evidence would reduce uncertainty most, it should surface that missing evidence precisely instead of saying only "please provide more information."

The layer exists to reduce uncertainty, not to increase intelligence.

## 2. Constitutional Position

The cognitive runtime becomes:

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

Evidence Gap Intelligence sits after Truth Status because missing evidence is only meaningful after the system knows which claims are unsupported, uncertain, stale, disputed, or insufficient for reliance.

It sits before Perspective because Perspective should identify a Situation Frame from reality whose evidence limitations are explicit. Perspective must not invent missing evidence or silently name frames around generic uncertainty.

## 3. Doctrine

Evidence represents information.

Truth Status evaluates reliance.

Evidence Gap Intelligence identifies missing evidence.

Perspective identifies the Situation Frame represented by truth-labeled reality.

Business Judgment evaluates business implications.

Decision selects action.

Evidence Gap Intelligence must remain diagnostic. It may identify and prioritize missing evidence, but it must not decide whether to ask the user, answer with caveats, defer, retrieve, execute, or refuse. Those are downstream responsibilities.

## 4. Core Responsibility

Evidence Gap Intelligence determines:

- what material evidence is absent;
- what missing evidence limits truth status;
- which gap most reduces uncertainty;
- which gap should be asked first if Decision chooses to ask;
- whether the current evidence set is complete enough for downstream interpretation;
- whether a candidate question duplicates an already answered question.

It does not determine:

- what the business situation means;
- whether the business is healthy or unhealthy;
- what strategy is best;
- what recommendation should be made;
- what action should be taken;
- what response should be sent;
- what memory should be committed.

## 5. Inputs

Evidence Gap Intelligence may receive:

- Business Situation frame;
- Evidence diagnostics;
- Evidence gaps;
- Truth Status classifications;
- unsupported claims;
- stale claims;
- disputed claims;
- material uncertainty;
- prior asked questions in the current situation;
- known answers already supplied by the user;
- consequence level from downstream context where available as diagnostic input.

The layer must not perform retrieval, external search, workflow execution, memory writes, or tool calls to fill gaps. It identifies missing evidence only.

## 6. Outputs

Evidence Gap Intelligence produces an `EvidenceGapProfile`.

An `EvidenceGapProfile` should include:

- evidence completeness;
- known evidence;
- missing evidence;
- materiality reason;
- priority queue;
- next best evidence need;
- smallest next question;
- duplicate-question guard result;
- confidence;
- unresolved uncertainty;
- downstream cautions.

These are architectural categories, not implementation fields.

## 7. Evidence Completeness

Evidence completeness is the degree to which available evidence is sufficient for responsible downstream interpretation.

Completeness is not the same as having every possible field.

Completeness should consider:

- business situation relevance;
- truth-status limitation;
- consequence of being wrong;
- whether the missing evidence could change perspective selection;
- whether the missing evidence could change judgment;
- whether the missing evidence could change the next decision;
- whether the missing evidence has already been asked and not answered;
- whether the user is likely able to answer the question directly.

Evidence Gap Intelligence must avoid missing-field confusion. A missing field is not automatically a material evidence gap.

## 8. Evidence Gap Types

The recognized initial gap types are:

- Business Context;
- Missing Business Type;
- Missing Timeline;
- Missing Customer Information;
- Missing Sales Information;
- Missing Inventory Information;
- Missing Cost Information;
- Missing Competitor Information;
- Missing Weather;
- Missing Promotion History;
- Missing Supplier Information;
- Missing Financial Information.

These are constitutional gap classes. Future registry work may normalize names, add subtypes, define aliases, and attach domain-specific question patterns.

## 9. Prioritization Standard

Evidence Gap Intelligence prioritizes missing evidence by uncertainty reduction.

The highest-priority gap is the missing evidence that would most reduce material uncertainty with the smallest user burden.

Priority should consider:

- materiality to the active business situation;
- relationship to unsupported or limited truth-status claims;
- ability to disambiguate competing explanations;
- likelihood that the answer changes downstream interpretation;
- specificity of the question;
- ease for the user to answer;
- whether the question has already been asked;
- whether the answer can unlock several downstream gaps at once.

Priority must not consider:

- which strategy the system prefers;
- which workflow needs fields;
- which answer would make a recommendation easier to justify;
- which question sounds most conversational;
- which response template is available.

## 10. Smallest Next Question

Evidence Gap Intelligence may produce a smallest next question as a diagnostic candidate.

The smallest next question is the narrowest user-answerable question that most reduces material uncertainty.

It should be:

- specific;
- answerable without analysis burden;
- connected to a material gap;
- non-duplicative;
- neutral;
- free of recommendation language;
- limited to one primary evidence need.

It should not:

- ask for every missing field;
- ask the user to diagnose the cause;
- imply a conclusion;
- smuggle a recommendation;
- request information already known;
- combine unrelated gaps;
- turn into a workflow form.

Decision owns whether to ask the question.

Conversation owns how to phrase the approved question to the user.

## 11. Duplicate Question Guard

Evidence Gap Intelligence must inspect prior questions and known answers in the current situation before producing a next-question candidate.

A question is duplicative when:

- the same evidence need was already answered;
- the same evidence need was already asked and remains pending;
- a stronger equivalent evidence item already exists;
- the answer is available in current evidence;
- the question only rephrases a known unknown without reducing uncertainty.

When the top-priority gap is duplicate-blocked, the layer may surface the next non-duplicative material gap.

If every material gap is duplicate-blocked, it should report no new smallest question.

## 12. Relationship With Evidence

Evidence is upstream.

Evidence answers:

> What information exists?

Evidence Gap Intelligence answers:

> What material information is still missing?

Evidence may expose gaps as part of completeness analysis, but Evidence Gap Intelligence owns prioritizing those gaps and converting them into diagnostic question candidates.

Evidence Gap Intelligence must not edit, delete, suppress, rewrite, or create evidence items.

The boundary is:

```text
Evidence says: this information exists, and these limitations or gaps are visible.
Evidence Gap Intelligence says: this missing evidence is the next most useful uncertainty reducer.
```

## 13. Relationship With Truth Status

Truth Status is upstream.

Truth Status answers:

> What information can be relied upon?

Evidence Gap Intelligence uses Truth Status to understand which claims are unsupported, stale, disputed, contradicted, assumed, or not reliance-worthy.

It must not change truth classifications.

It may say:

```text
This claim remains unsupported because timeline evidence is missing.
```

It must not say:

```text
This claim should be treated as true after asking about timeline.
```

Truth Status owns reliance. Evidence Gap Intelligence owns missing support.

## 14. Relationship With Perspective

Perspective is downstream.

Perspective receives truth-labeled claims and evidence-gap diagnostics.

Perspective may use gap diagnostics to avoid over-framing a thin evidence base. It may recognize that Profit Compression, Sales Decline, Inventory Risk, Demand Weakness, or Unknown Situation remains conditional when material evidence is missing.

Perspective must not ask its own evidence questions as a substitute for Evidence Gap Intelligence.

Evidence Gap Intelligence must not select Situation Frames.

The boundary is:

```text
Evidence Gap Intelligence says: customer-count evidence is missing.
Perspective says: Sales Decline remains a candidate frame, but confidence is limited until customer-count evidence is known.
```

## 15. Relationship With Decision and Conversation

Evidence Gap Intelligence does not decide to ask.

Decision decides whether the next action is to ask, answer, defer, execute, refuse, or proceed with caveats.

Conversation expresses the selected action.

Evidence Gap Intelligence may provide a question candidate, but that candidate is not automatically user-facing.

This protects SME Brain from letting a diagnostic layer become the response layer.

## 16. Developer Diagnostics

Developer diagnostics should expose:

- Evidence Completeness;
- Known Evidence;
- Missing Evidence;
- Priority Queue;
- Next Best Question;
- Confidence;
- Duplicate Question Guard;
- Materiality Reason;
- Downstream Cautions.

Diagnostics exist for constitutional accountability. They are not necessarily user-facing.

## 17. Examples

### Sales Decline

User says:

```text
ยอดขายตก
```

Known evidence:

- Business type: coffee shop;
- Sales decreased: reported by user.

Missing evidence:

- Timeline;
- Customer count;
- Promotion history;
- Weather.

Priority:

1. Timeline;
2. Customer count;
3. Promotion history;
4. Weather.

Smallest next question:

```text
ยอดขายเริ่มลดตั้งแต่เมื่อไรครับ?
```

The layer does not conclude why sales declined. It only identifies that timeline evidence most reduces uncertainty first.

### Price Complaint

User says:

```text
ลูกค้าบอกว่าอาหารแพง
```

Known evidence:

- Customer complaint exists;
- Price concern is reported by user.

Missing evidence:

- Number of customers;
- Sales trend;
- Price change history.

Smallest next question:

```text
ลูกค้าหลายคนพูดเหมือนกันหรือเป็นเพียงบางคนครับ?
```

The layer does not decide whether the food is overpriced. It identifies that complaint breadth is the smallest evidence need before interpretation.

## 18. Constitutional Invariants

Evidence Gap Intelligence must obey these invariants:

- It inspects existing evidence.
- It inspects missing information.
- It determines evidence completeness.
- It prioritizes missing evidence.
- It identifies the smallest next question.
- It avoids duplicate questions.
- It remains diagnostic only.
- It never evaluates business quality.
- It never produces recommendations.
- It never ranks business strategies.
- It never predicts outcomes.
- It never changes truth classifications.
- It never changes evidence.
- It never modifies routing.
- It never modifies planner behavior.
- It never modifies workflow behavior.
- It never performs execution.
- It never commits memory.
- It never becomes the response layer.

## 19. Failure Modes

### Generic Clarification

The system says "please provide more information" when the highest-value missing evidence is identifiable.

### Question Flooding

The system asks for every missing field instead of the smallest uncertainty reducer.

### Workflow Capture

Required workflow fields masquerade as evidence gaps.

### Judgment Leakage

The layer recommends a business action while deciding which evidence is missing.

### Perspective Leakage

The layer interprets what the missing evidence means before Perspective acts.

### Truth Leakage

The layer changes unsupported claims into facts after identifying a possible missing source.

### Duplicate Question Loop

The system repeatedly asks for evidence already supplied, already asked, or already represented.

### Conversation Capture

The diagnostic question candidate bypasses Decision and Conversation and becomes the final response automatically.

## 20. Future Runtime Roadmap

Future Evidence Gap Intelligence runtime work should follow the standard cognitive layer lifecycle:

```text
Runtime Foundation
    -> Registry
    -> Diagnostics
    -> Runtime State
    -> Behavior
```

### V5.7.1 Evidence Gap Runtime Foundation

Define purpose, inputs, outputs, constitutional boundaries, completeness concept, diagnostic shape, and invariants.

No routing, planner, workflow, response, retrieval, memory, or execution behavior should be introduced.

### V5.7.2 Evidence Gap Registry

Define recognized evidence gap types, aliases, materiality rules, duplicate-question rules, and domain-specific gap families.

### V5.7.3 Question Prioritization

Define prioritization logic for uncertainty reduction, user burden, materiality, and non-duplication.

### V5.7.4 Adaptive Question Selection

Define how the diagnostic question candidate may adapt to context, prior answers, language, and user burden while remaining subordinate to Decision and Conversation.

## 21. Architecture Decision

Evidence Gap Intelligence is a required constitutional layer.

It owns missing-evidence diagnosis.

It must remain separate from Evidence, Truth Status, Perspective, Knowledge, Business Judgment, Decision, Execution, Conversation, Commit, Workflow, Planner, Routing, and Authority.

The official boundary is:

```text
Evidence represents information.
Truth Status evaluates reliance.
Evidence Gap Intelligence identifies missing support.
Perspective identifies the Situation Frame.
Knowledge applies doctrine.
Business Judgment evaluates business implications.
Decision selects action.
Execution performs authorized work.
Conversation expresses faithfully.
Commit governs finality.
Authority governs responsibility.
```

The constitutional standard is:

> A great advisor does not begin by answering. A great advisor begins by asking the smallest question that most reduces uncertainty.

Evidence Gap Intelligence exists to make that smallest question knowable before downstream layers decide what to do with it.
