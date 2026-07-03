# SME Brain Truth Model

This document defines how SME Brain determines what may be treated as true enough for business judgment. It describes ideal cognition, not implementation.

Architecture Review VI expands this doctrine in `SME_BRAIN_TRUTH_STATUS_ARCHITECTURE_REVIEW.md`.

## 1. Purpose

Truth in SME Brain is not absolute certainty. It is justified reliance for a current business decision.

Truth Status exists because evidence does not speak for itself. A business owner may say something, memory may say something else, a dashboard may imply a third interpretation, and knowledge may warn about a fourth risk.

Truth Status answers:

> Given the available evidence, what can the Brain responsibly treat as fact, assumption, observation, belief, hypothesis, or unresolved conflict?

## 2. Why Truth Status Must Exist

Truth Status cannot merge with Evidence because evidence is support, not belief.

It cannot merge with Judgment because judgment weighs business consequence, trade-offs, opportunity, and action. Truth Status only determines justified reliance.

It cannot merge with Knowledge because knowledge is generalizable understanding, not necessarily local truth.

It cannot merge with Conversation because communication must express truth; it must not create truth.

## 3. Responsibilities

Truth Status must:

- classify claims by epistemic status;
- distinguish fact, observation, assumption, belief, hypothesis, estimate, preference, policy, principle, and unresolved conflict;
- resolve evidence conflicts when justified;
- preserve conflicts when not resolved;
- prevent memory, tools, OCR, skills, and user statements from becoming unquestioned truth;
- calibrate confidence to consequence;
- decide whether uncertainty is acceptable for judgment;
- identify what would change the Brain's mind.

Truth Status must not:

- recommend business action;
- choose the next step;
- ask questions by itself;
- persist memory;
- execute tools;
- rewrite evidence to fit a preferred conclusion;
- hide material uncertainty from judgment.

## 4. Inputs

Truth Status receives:

- BusinessSituation;
- EvidenceSet;
- evidence conflicts;
- assumptions;
- hypotheses;
- relevant policies;
- relevant principles;
- freshness context;
- consequence level;
- risk sensitivity.

## 5. Outputs

Truth Status produces a `TruthState`.

`TruthState` includes:

- accepted facts;
- observations;
- assumptions;
- estimates;
- beliefs;
- hypotheses;
- unresolved conflicts;
- rejected claims;
- confidence by claim;
- reason for truth-status;
- change conditions.

## 6. Semantic Objects

### Fact

A claim with enough support to rely on for the current decision.

### Observation

A reported or detected condition that may require interpretation.

### Assumption

A working belief used because the cost of resolving it is not justified or the risk is acceptable.

### Estimate

A numeric or qualitative approximation with known uncertainty.

### Belief

The Brain's current position based on evidence and reasoning.

### Hypothesis

A plausible explanation that remains open to revision.

### Conflict

A disagreement between credible claims.

### Rejected Claim

A claim not relied on because it is contradicted, irrelevant, stale, unreliable, or outside scope.

## 7. Ownership

Truth Authority owns Truth Status.

Evidence Authority owns evidence quality. Truth Authority owns what can be relied on.

Business Judgment Authority uses TruthState but cannot silently upgrade assumptions into facts.

Conversation Authority expresses TruthState faithfully.

Commit Authority governs whether truth claims may become durable records.

## 8. Allowed Dependencies

Truth Status may depend on:

- Evidence quality;
- source fit;
- freshness;
- corroboration;
- business consequence;
- policy and principle constraints;
- user correction;
- verified records;
- memory decay rules;
- domain knowledge about source reliability.

## 9. Forbidden Dependencies

Truth Status must not depend on:

- desired response fluency;
- workflow completion;
- planner preference;
- skill output confidence outside skill scope;
- tool precision without source evaluation;
- the need to avoid asking a question;
- convenience of execution.

## 10. Confidence

Truth confidence is claim-specific.

It should not be expressed as one global score for the whole situation.

High confidence means the claim is sufficiently supported for the current consequence level.

Medium confidence means the claim can support reversible or low-risk judgment with caveats.

Low confidence means the claim should remain an assumption or hypothesis.

Conflicted confidence means credible claims disagree and the conflict matters.

## 11. Uncertainty

Truth Status handles uncertainty by:

- preserving assumptions visibly;
- keeping hypotheses separate from facts;
- marking estimates;
- surfacing conflict;
- lowering confidence when freshness is weak;
- recommending evidence improvement to Judgment when consequence is high.

Truth Status should not force certainty. It should support responsible action under uncertainty.

## 12. Explainability

Truth Status should be able to explain:

- why a claim is treated as fact;
- why a claim remains an assumption;
- why a conflict was resolved or preserved;
- why one source was preferred over another;
- what evidence would change the status.

The user does not need every internal detail, but high-risk responses should disclose material assumptions or uncertainty.

## 13. Failure Modes

### False Certainty

Weak or conflicting evidence is treated as fact.

### Eternal Uncertainty

The Brain refuses to rely on reasonable evidence.

### Source Worship

Dashboard, OCR, memory, user statement, or tool output is trusted because of its source category rather than source fit.

### Assumption Laundering

An assumption becomes a fact because it passes through multiple layers.

### Conflict Suppression

Contradictions are hidden to produce a cleaner answer.

### Truth Capture By Conversation

The final response smooths away uncertainty and changes meaning.

## 14. Examples

### User Correction

Memory says the shop sells lunch sets. User says they now focus on catering.

Truth Status should treat current user correction as strong evidence for current business context, while retaining older memory as historical context.

### OCR Number

OCR reads 8,900, but image quality is poor.

Truth Status should classify the value as extracted estimate or low-confidence observation unless verified.

### Policy Claim

User says refunds are never allowed.

Truth Status can treat this as a reported policy, but Policy evaluation and Principles may still constrain whether it is acceptable to apply.

## 15. Final Standard

Truth Status is justified reliance, not certainty.

SME Brain must know the difference between what it saw, what it inferred, what it assumes, what it believes, and what it can responsibly act on.
