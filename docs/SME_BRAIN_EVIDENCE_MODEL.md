# SME Brain Evidence Model

This document defines how SME Brain treats information as evidence. It describes ideal cognition, not software implementation.

## 1. Purpose

Evidence is information that may support, challenge, refine, or change understanding of a specific business situation.

Evidence exists because experienced business decision-makers do not treat all inputs equally. They ask:

> What do we know, where did it come from, how reliable is it, how current is it, how relevant is it, and how much should it change judgment?

Evidence must exist separately from Business Situation and Truth Status.

It cannot merge with Business Situation because a situation is a frame of business reality, while evidence is support for claims inside that frame.

It cannot merge with Truth Status because evidence is not automatically true.

## 2. Responsibilities

Evidence must:

- preserve source awareness;
- distinguish user statements, memory, documents, records, dashboards, OCR, tools, skills, knowledge, and external information;
- evaluate relevance, reliability, freshness, completeness, directness, consistency, and importance;
- expose conflicts;
- support assumptions and hypotheses without converting them to facts;
- identify evidence gaps only when they matter;
- preserve enough traceability for explanation.

Evidence must not:

- decide the answer;
- select the next action;
- force a question;
- become durable memory by itself;
- treat tool output as final truth;
- treat stored memory as current fact without evaluation;
- treat general knowledge as local evidence unless connected to the situation.

## 3. Inputs

Evidence may receive:

- current user message;
- prior conversation;
- business memory;
- store profile;
- documents;
- receipts;
- dashboard metrics;
- analytics;
- OCR output;
- tool output;
- skill findings;
- external sources;
- business knowledge;
- policy statements;
- principle references;
- owner confirmations;
- execution results.

## 4. Outputs

Evidence produces an `EvidenceSet`.

An `EvidenceSet` contains:

- evidence items;
- source;
- claim;
- evidence type;
- relevance;
- reliability;
- freshness;
- completeness;
- directness;
- confidence;
- importance;
- conflicts;
- limitations;
- candidate truth-status;
- explanation trace.

## 5. Semantic Objects

### Evidence

An individual information item that bears on the current situation.

### EvidenceSet

The collection of evidence relevant to the situation.

### EvidenceClaim

The claim an evidence item appears to support.

### EvidenceSource

The origin of the evidence.

### EvidenceQuality

The quality profile of evidence across multiple dimensions.

### EvidenceConflict

A conflict between evidence items that may affect truth, judgment, or decision.

### EvidenceGap

A missing or weak area of support. It becomes important only if it creates material uncertainty.

## 6. Ownership

Evidence Authority owns evidence classification and quality evaluation.

Memory, Knowledge, Skills, Tools, and Execution may contribute evidence, but they do not own evidence quality outside their scope.

Truth Status owns whether evidence becomes fact, assumption, belief, or hypothesis.

Judgment owns how evidence affects business assessment.

## 7. Allowed Dependencies

Evidence may depend on:

- Business Situation for relevance;
- Perception for raw signals;
- Memory for stored context;
- Knowledge for general references;
- Tool and Skill outputs as bounded sources;
- Execution results as new observations;
- Policy and Principle references as claims or constraints.

## 8. Forbidden Dependencies

Evidence must not depend on:

- workflow state to decide relevance;
- required fields to define evidence gaps;
- response needs to inflate confidence;
- skill preference to determine what matters;
- tool precision to imply truth;
- model fluency to imply reliability.

## 9. Confidence

Evidence confidence is justified reliance in a specific context.

It should consider:

- source fit;
- directness;
- recency;
- corroboration;
- consistency;
- method quality;
- completeness;
- consequence of being wrong.

Confidence is not merely probability. A low-risk creative task can use lower-confidence evidence. A financial, legal, customer trust, or irreversible action requires stronger evidence.

## 10. Uncertainty

Evidence creates uncertainty when:

- relevant evidence is absent;
- evidence is stale;
- sources conflict;
- a claim is inferred rather than observed;
- evidence is ambiguous;
- evidence is incomplete for the consequence level;
- evidence is precise but source quality is weak.

Not every evidence gap justifies asking the user. Only material uncertainty can justify a question.

## 11. Explainability

Evidence must be explainable at three levels:

- what evidence was considered;
- why it mattered;
- why it was trusted, discounted, or held as uncertain.

The Brain does not need to expose all evidence to the user. It must be able to explain the evidence basis when needed.

## 12. Failure Modes

### Evidence Flattening

All information is treated equally.

Impact: weak memory, tool output, and user impressions can override stronger records.

### Evidence Capture

A single source dominates because it is available or structured.

Impact: dashboard, OCR, or tool output becomes false certainty.

### Missing-Field Confusion

Absent fields become evidence gaps.

Impact: the Brain asks procedural questions instead of judging materiality.

### Recency Bias

The newest statement automatically overrides stronger older evidence.

Impact: unstable and reactive judgment.

### Memory Bias

Stored context silently shapes current judgment.

Impact: stale personalization and user correction fatigue.

### Knowledge Bias

General knowledge is treated as local proof.

Impact: generic recommendations that do not fit the business.

## 13. Examples

### Pricing Question

User says: "Customers say this is expensive."

Evidence includes current user report, known price, margin data if available, prior customer objections, competitor context if available, and business positioning.

The evidence layer should not decide whether to discount. It should expose what supports or weakens discounting.

### Receipt OCR

OCR reads a total as 8,900.

Evidence should mark source as OCR, directness as document-derived, reliability as dependent on image quality, and confidence as limited if the image is unclear.

Truth Status decides whether the total can be relied on.

### Sales Decline

User says sales are down, but dashboard shows revenue is stable.

Evidence should preserve both claims and surface conflict. Judgment may hypothesize lower foot traffic but higher order value, lower profit despite stable revenue, or perception mismatch.

## 14. Final Standard

Evidence is disciplined attention.

SME Brain must not ask what information exists only to satisfy a structure. It must ask what information matters for responsible judgment.

