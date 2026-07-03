# SME Brain Judgment Model

This document defines Business Judgment. It describes ideal cognition, not implementation.

## 1. Purpose

Business Judgment is the central cognitive act of SME Brain.

It is the reasoned assessment of a business situation under uncertainty. It synthesizes situation, evidence, truth-status, recognized Situation Frame, knowledge, principles, policies, risks, opportunities, constraints, and expected business impact.

Judgment answers:

> What is going on, what matters, what is likely true enough, what are the plausible interpretations, what is beneficial or risky, and what should be recommended or considered?

## 2. Why Judgment Must Exist

Judgment cannot merge with Business Situation because situation framing is not assessment.

It cannot merge with Evidence because evidence supports judgment but does not weigh business consequence.

It cannot merge with Truth Status because truth-status decides justified reliance, not business wisdom.

It cannot merge with Perspective because Perspective recognizes the Situation Frame, while Judgment evaluates implications, explanations, alternatives, risks, and recommendations.

It cannot merge with Knowledge because knowledge is reusable understanding, not contextual assessment.

It cannot merge with Decision because judgment says what appears wise; decision selects what to do next.

## 3. Responsibilities

Judgment must:

- synthesize the recognized Situation Frame with knowledge, evidence, risks, opportunities, and constraints;
- weigh evidence according to TruthState;
- reason under uncertainty;
- identify risks, opportunities, and trade-offs;
- compare alternatives;
- consider principles and policies;
- assess expected business impact;
- determine whether immediate help is possible;
- decide whether more evidence would materially improve assessment;
- produce a reasoned recommendation or assessment;
- explain its reasoning.

Judgment must not:

- execute actions;
- release final responses;
- persist memory;
- bypass policy or principles;
- treat workflow completion as success;
- let a skill or tool determine final assessment;
- hide material uncertainty;
- decide final wording.

## 4. Inputs

Judgment receives:

- BusinessSituation;
- EvidenceSet;
- TruthState;
- Perspective diagnostics;
- KnowledgeContext;
- MaterialUncertainty;
- risks;
- opportunities;
- constraints;
- principles;
- policies;
- user preferences;
- available capabilities;
- consequence level.

## 5. Outputs

Judgment produces a `BusinessJudgment`.

`BusinessJudgment` includes:

- current assessment;
- recommendation direction;
- alternative hypotheses;
- confidence;
- material uncertainties;
- key evidence;
- principles and policy constraints;
- risks;
- opportunities;
- trade-offs;
- expected business impact;
- reasoning summary;
- what would change the judgment.

## 6. Semantic Objects

### BusinessJudgment

The current reasoned assessment.

### JudgmentAlternative

A plausible competing assessment or course.

### Tradeoff

A tension between benefits and costs, such as margin versus conversion.

### BusinessImpact

Expected effect on revenue, cost, cash, operations, brand, trust, risk, or owner capacity.

### JudgmentConfidence

Confidence in the assessment, calibrated to evidence quality and consequence.

### JudgmentExplanation

The concise reason the assessment is warranted.

## 7. How Judgment Is Formed

Judgment forms through:

1. Situation framing.
2. Evidence evaluation.
3. Truth-status assignment.
4. Situation Frame recognition.
5. Knowledge application.
6. Hypothesis generation.
7. Risk and opportunity evaluation.
8. Alternative comparison.
9. Principle and policy constraint.
10. Confidence calibration.
11. Business impact estimation.
12. Reasoned assessment.

This is not a mandatory procedural sequence. It is the cognitive content that must be represented.

## 8. Evidence Requirements

Judgment requires enough evidence for the consequence level.

Low-risk reversible tasks can proceed with assumptions.

High-risk financial, legal, customer trust, operational, or irreversible actions require stronger evidence or confirmation.

The question is not "Is all data complete?"

The question is:

> Is the evidence sufficient for the risk and usefulness of the next judgment?

## 9. Truth And Judgment

TruthState constrains Judgment.

Facts may support strong recommendations.

Assumptions may support tentative recommendations.

Hypotheses may support diagnostic exploration.

Conflicts may require caveats, more evidence, or safer alternatives.

Judgment must never silently upgrade weak truth-status because a clear answer is desired.

## 10. Uncertainty In Judgment

Uncertainty affects Judgment by changing:

- confidence;
- whether to answer or ask;
- whether to warn;
- whether to recommend a reversible step;
- whether to seek knowledge, memory, skill, or tool support;
- whether to present alternatives;
- whether to refuse or defer.

Uncertainty is not failure. Unmanaged uncertainty is failure.

## 11. Confidence Calculation

Judgment confidence should be based on:

- evidence confidence;
- truth-status confidence;
- frame confidence;
- knowledge applicability;
- consistency between the recognized frame, evidence, and knowledge;
- severity of unresolved uncertainty;
- reversibility of recommended action;
- business consequence;
- alternative hypothesis strength;
- principle and policy clarity.

Confidence should be explainable, not just numeric.

## 12. Frame-Aware Judgment

Judgment should use Perspective diagnostics by:

- preserving the selected Situation Frame;
- considering candidate frames when confidence is limited;
- respecting Unknown Situation when no frame is responsible;
- weighing business consequence after the frame is recognized;
- preserving high-risk alternative hypotheses;
- avoiding commercial capture by revenue-only logic;
- avoiding principle capture by impractical abstraction.

Example:

A customer complaint may be framed as Pricing Pressure, Customer Retention Risk, or Unknown Situation depending on validated evidence. Judgment then evaluates causes, tradeoffs, and possible recommendations.

Judgment must evaluate from the frame; it must not ask Perspective to perform evaluation.

## 13. Principles And Judgment

Principles constrain judgment by defining what must not be recommended even if commercially useful.

Principles should reject deception, exploitation, hidden material uncertainty, irresponsible harm, and unfair treatment.

Principles do not replace business realism. They shape responsible alternatives.

## 14. Ownership

Business Judgment Authority owns BusinessJudgment.

It may request evidence, truth-status, knowledge, perspective, policy, principle, skill, or tool contributions.

Delegation does not transfer judgment ownership.

## 15. Allowed Dependencies

Judgment may depend on:

- BusinessSituation;
- EvidenceSet;
- TruthState;
- Perspective diagnostics;
- KnowledgeContext;
- principles;
- policies;
- memory;
- skill findings;
- tool outputs after evidence evaluation;
- execution results after truth evaluation.

## 16. Forbidden Dependencies

Judgment must not depend on:

- workflow state as the source of business meaning;
- skill availability as the source of need;
- response fluency;
- implementation routing;
- required fields as the measure of readiness;
- tool output without TruthStatus;
- policy bypass because advice is helpful.

## 17. Failure Modes

### Workflow Judgment

Judgment becomes procedural completion.

### Single-Frame Capture

One Situation Frame dominates after evidence changes or candidate frames remain materially plausible.

### Evidence-Free Judgment

The Brain gives generic advice disconnected from situation.

### False Precision

The Brain states confident numbers or recommendations on weak evidence.

### Over-Questioning

Judgment refuses to act until all data is complete.

### Principle Avoidance

Commercial benefit hides trust or ethical risk.

### Decision Collapse

Judgment directly executes without a separate decision.

## 18. Examples

### Promotion Request

Judgment should assess objective, audience, offer, margin risk, brand fit, timing, available evidence, and whether assumptions are safe. It may judge that drafting a first version is useful while noting assumed audience.

### Hiring Question

Judgment should consider demand, cash flow, workload, service quality, owner capacity, and alternatives. It may recommend testing part-time help before full hiring if evidence is thin.

## 19. Final Standard

Business Judgment is practical wisdom under uncertainty.

SME Brain succeeds when it can explain not only what it recommends, but why that recommendation fits this business situation now.
