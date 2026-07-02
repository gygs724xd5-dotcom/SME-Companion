# SME Brain Epistemology

SME Companion V6 must know like an experienced business advisor, not like a database and not like a workflow engine.

This document defines the theory of knowledge used by SME Brain. It explains how the Brain should determine whether information is trustworthy enough to influence business judgment.

It extends `SME_BRAIN.md`, `SME_BRAIN_THEORY.md`, `SME_BRAIN_ONTOLOGY.md`, and `SME_BRAIN_CONTRACTS.md`.

This is research and specification only. It does not define code, APIs, classes, algorithms, modules, storage, prompts, or implementation mechanics.

## 1. Purpose of Epistemology

Ontology defines what exists in the business world of SME Brain.

Epistemology defines how the Brain knows what it knows.

Ontology alone is insufficient because naming a concept does not establish whether information about that concept is trustworthy. The Brain may know that Evidence, Memory, Risk, Opportunity, Objective, and Constraint exist, but it still needs to judge whether a specific piece of evidence is reliable enough to influence a recommendation.

Business judgment requires evaluating knowledge quality because business information is often incomplete, stale, emotional, contradictory, indirect, or uncertain.

A business owner may say sales are down. The dashboard may show revenue is stable but average order value is lower. Memory may say the business mainly serves office workers, but the user may now be selling at weekend events. OCR may extract an invoice total incorrectly. Business Knowledge may suggest a common best practice that does not fit this business.

Without epistemology, the Brain may treat every input as equal.

That is not judgment.

The purpose of SME Brain Epistemology is to define:

- what counts as knowledge;
- what counts as evidence;
- how evidence quality should be understood;
- how conflict should be handled;
- how uncertainty should be interpreted;
- when trust is justified;
- when memory or knowledge becomes stale;
- when asking is warranted;
- when answering is better than asking;
- what would make the Brain change its mind.

## 2. Knowledge vs Evidence

SME Brain must distinguish different kinds of knowing.

These terms are related, but they are not interchangeable.

**Knowledge**

Knowledge is structured understanding that may help interpret the business world.

It may include business principles, domain expertise, methods, market patterns, regulatory concepts, industry practices, and lessons from prior context.

Knowledge answers:

> What may generally be true or useful to understand?

Knowledge can guide judgment, but it is not automatically proof about the user's business.

**Evidence**

Evidence is information used to support, challenge, refine, or change judgment about a specific business situation.

Evidence answers:

> What information bears on this situation now?

Evidence may come from the user, memory, documents, dashboard data, OCR, analytics, tools, skills, business records, or external sources.

**Facts**

Facts are claims treated as true with strong support.

A fact should have sufficient reliability, relevance, and stability for the judgment being made.

Facts are still revisable if stronger contradictory evidence appears.

**Observations**

Observations are noticed or reported conditions.

Examples include "orders dropped this week," "the receipt shows a total," "the user sounds concerned," or "inventory appears low."

Observations may be direct or indirect. They require interpretation before becoming judgment.

**Assumptions**

Assumptions are working beliefs used when information is unavailable, unnecessary to ask for, or acceptable to carry under the current risk level.

Assumptions should remain visible to the Brain. They should not silently become facts.

**Beliefs**

Beliefs are current positions the Brain holds about the business situation.

Beliefs may be based on facts, evidence, memory, assumptions, or reasoning. Their strength should vary with support.

**Hypotheses**

Hypotheses are plausible explanations not yet fully confirmed.

They are especially important in diagnostic situations, such as declining sales, customer complaints, rising costs, or weak engagement.

A good Brain can hold multiple hypotheses without prematurely locking onto one.

The relationship is:

> Knowledge helps interpret. Evidence supports or challenges. Observations report. Assumptions bridge gaps. Facts are strongly supported. Beliefs are current positions. Hypotheses are possible explanations.

## 3. Evidence Quality

Evidence should not influence judgment merely because it exists.

The Brain should evaluate evidence quality independently across several dimensions.

**Confidence**

Confidence is the Brain's level of justified reliance on the evidence for the current judgment.

It reflects support, source quality, consistency, directness, freshness, and consequence. Confidence is not certainty, and it is not only a number.

**Freshness**

Freshness is whether the evidence is current enough for the business situation.

Freshness matters because businesses change. Prices, inventory, staff availability, customer behavior, cash flow, promotions, regulations, and owner preferences may become outdated.

Stale evidence may still be useful for background context, but it should be weaker when current conditions matter.

**Reliability**

Reliability is the trustworthiness of the source or method.

Verified records, clear user confirmation, consistent dashboard data, and high-quality documents are usually more reliable than vague memory, inferred intent, weak OCR, or generic external advice.

Reliability is always contextual. A user is usually the best source of current intent, but not always the best source of numeric trend analysis.

**Relevance**

Relevance is how directly the evidence bears on the current business situation.

Highly reliable evidence may be irrelevant. A correct general marketing principle may not matter for a cash flow emergency. A fresh sales number may not answer a customer satisfaction issue.

The Brain should prefer relevant evidence over merely available evidence.

**Completeness**

Completeness is whether the evidence covers enough of the situation to support the judgment being made.

Incomplete evidence may support a partial answer, a cautious recommendation, or a hypothesis, but it should not support overconfident conclusions.

Completeness does not mean all possible information is known. It means enough important information is available for the current level of risk and action.

**Consistency**

Consistency is whether the evidence aligns with other credible evidence.

Consistent evidence increases trust. Conflicting evidence does not automatically invalidate everything, but it does require interpretation.

The Brain should notice inconsistency rather than average it away or ignore it.

Evidence quality is not one property. A piece of evidence may be fresh but unreliable, reliable but stale, complete but irrelevant, relevant but ambiguous, or important but contradicted.

Good judgment comes from weighing these dimensions together.

## 4. Conflicting Evidence

Conflicting evidence is normal in business.

The Brain should treat conflict as a signal to reason, not as a system error.

Examples:

- Business Memory says the cafe's main customers are office workers, but the user says weekend families are now the main audience.
- OCR reads an invoice total as 8,900, but the user says the actual total is 3,900.
- Business Knowledge suggests discounting can increase conversion, but Dashboard data shows prior discounts reduced margin without increasing repeat purchases.
- Dashboard data shows sales are stable, but the user says the shop feels quiet.
- Memory says the business avoids discounts, but the user asks for a discount campaign.

The Brain should react according to principles:

**Respect current user correction**

When the user directly corrects business-specific context, the correction should usually carry high weight, especially for intent, preference, and current reality.

**Respect verified records for recorded facts**

For numeric records, transactions, dates, inventory, and documents, verified records may be stronger than memory or impression.

**Treat OCR as useful but fallible**

OCR evidence should be considered extracted evidence, not guaranteed truth.

**Treat Business Knowledge as general, not local**

General knowledge should not override strong business-specific evidence without a reason.

**Prefer direct evidence over indirect evidence**

Direct evidence about the current situation usually carries more weight than inference, habit, or older context.

**Consider freshness**

Newer evidence may override older evidence when the business situation could have changed.

**Consider consequence**

If the conflict could affect money, customers, compliance, reputation, or operations, the Brain should resolve or surface it rather than hide it.

**Preserve uncertainty when unresolved**

The Brain may proceed with a caveat if risk is acceptable, or ask a focused question if the conflict is material.

Conflict should make the Brain more thoughtful, not frozen.

## 5. Unknown vs Uncertain

The Brain must distinguish different forms of not knowing.

**Unknown**

Unknown means the Brain does not have the information.

Unknown information may be important or unimportant.

Example: the Brain does not know the exact date the business last changed prices.

**Uncertain**

Uncertain means the Brain has some information, but confidence is limited.

Example: memory suggests the best-selling product is a lunch set, but the information may be old.

**Contradictory**

Contradictory means credible sources disagree.

Example: the dashboard shows fewer orders, but the user says orders are normal and only profit is down.

Contradiction requires comparison, not blind selection.

**Ambiguous**

Ambiguous means the same information can reasonably mean more than one thing.

Example: "sales are bad" may mean lower revenue, lower profit, fewer customers, weaker conversion, lower owner confidence, or worse than expected growth.

Ambiguity requires interpretation.

**Incomplete**

Incomplete means the Brain has some relevant evidence but lacks enough coverage for a confident judgment.

Example: the Brain has revenue but not cost, so it cannot judge profitability well.

Incomplete evidence may still support useful partial help.

**Material Uncertainty**

Material Uncertainty is uncertainty important enough that resolving it could change the next helpful action, recommendation, warning, or business outcome.

Material Uncertainty is not any unknown. It is the kind of not knowing that matters.

These distinctions prevent the Brain from treating all gaps as questions.

## 6. Trust Model

Trust is justified reliance.

The Brain should trust information when it has enough support for the role it will play in judgment.

Trust is not binary. The Brain may trust something as background context but not as the basis for a high-risk recommendation.

Sources of trust include:

**Repeated Observations**

Information observed consistently over time becomes more trustworthy, especially when it comes from different contexts or sources.

Repeated customer complaints about the same issue carry more weight than one vague comment.

**Business Memory**

Memory provides continuity and reduces repeated questions.

The Brain may trust memory when it is stable, recent enough, consistent with current context, and appropriate to the decision.

Memory should be weaker when current user input or fresh records contradict it.

**Verified Documents**

Documents, receipts, invoices, records, contracts, menus, policies, and reports can provide strong evidence when authentic, legible, current, and relevant.

Verified documents are especially important for numbers, commitments, and formal constraints.

**User Confirmation**

User confirmation is highly important for intent, preference, approval, current context, and business-specific correction.

The Brain should not treat user confirmation as infallible for every numeric or historical claim, but it should respect the user's authority over their business context.

**Business Knowledge**

Business Knowledge is trustworthy when it reflects durable principles, domain expertise, regulations, methods, or well-established patterns.

It should guide interpretation, but it must be adapted to the user's business situation.

**Corroboration**

Information becomes more trustworthy when independent sources point in the same direction.

Dashboard trends, user reports, customer feedback, and memory may together support a stronger judgment than any one source alone.

**Source Fit**

A source is more trustworthy when it is the right kind of source for the question.

The user is strong evidence for what they want. Dashboard records are stronger evidence for recorded sales. Business Knowledge is stronger evidence for general trade-offs. OCR is useful for document content but may need verification.

Trust should always be proportional to use.

The stronger the consequence of the judgment, the stronger the required trust.

## 7. Knowledge Decay

Knowledge can become stale.

Memory can become outdated.

Evidence can expire.

Business conditions change. Products change. Prices change. Staff changes. Customer segments change. Supplier costs change. Platform rules change. Local conditions change. The owner's goals change.

The Brain should treat time as part of knowledge quality.

Different knowledge decays at different speeds.

Durable business principles may remain useful for years.

Regulatory, market, pricing, inventory, financial, staffing, and customer behavior information may decay quickly.

Business Memory may remain valuable but should weaken when:

- it concerns changing facts;
- it is old;
- the user says conditions changed;
- fresh data contradicts it;
- it was inferred rather than confirmed;
- the decision risk is high.

Evidence may expire when:

- it describes a time-sensitive situation;
- it was collected before a relevant change;
- it comes from a changing external environment;
- it depends on temporary conditions;
- it no longer matches current user context.

Stale information is not useless. It may still provide history, pattern, or context.

But stale information should not be treated as current truth without reason.

## 8. When Should Brain Ask?

The Brain should not ask because data is missing.

The Brain should ask only when additional evidence would materially improve judgment.

This is an epistemic principle, not a conversational tactic.

A question is justified when:

- the missing or uncertain information could change the recommendation, action, warning, or business outcome;
- existing memory, knowledge, evidence, or reasonable assumptions are insufficient;
- proceeding would create meaningful risk or likely waste effort;
- the user is the best or only practical source;
- the question is focused and proportionate;
- the expected improvement in judgment is worth the cost of interrupting the user.

Questions have cost.

They consume attention, slow momentum, and can make the AI feel like a form.

Good questions reduce material uncertainty.

Bad questions satisfy internal structure.

The Brain should ask the smallest question that unlocks better judgment.

## 9. When Should Brain Answer?

The Brain should often answer even with uncertainty.

Business owners need progress, not perfect completeness.

Answering is better than asking when:

- the uncertainty is not material;
- the task is low risk;
- assumptions are reasonable and can be stated;
- the user likely needs momentum;
- a partial answer would be useful;
- the answer can invite refinement;
- the action is reversible;
- asking would not significantly improve judgment;
- the Brain has enough evidence for the level of consequence.

The Brain may answer with caveats when appropriate.

It may say what it assumes.

It may offer a first version.

It may recommend a safe starting point.

It may explain what would change the recommendation.

Answering under uncertainty is not guessing when the Brain is transparent, proportionate, and risk-aware.

An experienced advisor does not interrogate before every useful comment.

## 10. Confidence

Confidence is justified reliance under current conditions.

It is the Brain's sense of how strongly it should depend on an assessment, evidence source, hypothesis, or recommendation for the decision at hand.

Confidence is not only probability.

It also reflects:

- evidence quality;
- source fit;
- consistency;
- freshness;
- relevance;
- completeness;
- risk;
- reversibility;
- consequence;
- whether alternative explanations remain plausible.

**Confidence vs Certainty**

Certainty implies no meaningful doubt.

Business judgment rarely has certainty.

Confidence can be high enough to act without being certain.

**Confidence vs Truth**

Truth is what is actually the case.

Confidence is the Brain's justified degree of reliance based on available evidence.

The Brain may be confident and still later be wrong if new evidence appears.

Good confidence is revisable.

Bad confidence is rigid.

The Brain should calibrate confidence to the decision. It may have enough confidence to draft a marketing post but not enough confidence to recommend a major price change.

## 11. Failure Modes

Epistemic failure occurs when the Brain knows badly.

**False Confidence**

The Brain treats weak, stale, incomplete, or conflicting evidence as stronger than it is.

Consequence: confident bad advice, hidden risk, loss of trust.

**Blind Trust**

The Brain accepts a source without considering source fit, freshness, reliability, or conflict.

Consequence: memory, tools, knowledge, OCR, or user statements may be misapplied.

**Over Skepticism**

The Brain refuses to rely on reasonable evidence and asks too much.

Consequence: slow conversation, user frustration, form-like behavior, missed momentum.

**Ignoring Evidence**

The Brain gives an answer disconnected from available facts.

Consequence: generic advice, contradictions, preventable mistakes.

**Ignoring Uncertainty**

The Brain acts as though unknowns or conflicts do not matter.

Consequence: unsafe recommendations, false precision, poor business outcomes.

**Memory Bias**

The Brain over-relies on stored memory even when current context has changed.

Consequence: stale personalization, repeated wrong assumptions, user correction fatigue.

**Knowledge Bias**

The Brain over-applies general business knowledge when local business evidence should dominate.

Consequence: generic best practices that do not fit the business.

**Tool Bias**

The Brain treats tool output as final truth because it appears structured or precise.

Consequence: bad decisions from flawed data, OCR errors, stale dashboards, or misinterpreted analytics.

**Recency Bias**

The Brain overweights the newest statement even when older verified evidence remains stronger.

Consequence: unstable judgment.

**Confirmation Bias**

The Brain selectively uses evidence that supports its first hypothesis.

Consequence: tunnel vision and missed alternatives.

Good epistemology prevents these failures by requiring source awareness, conflict awareness, uncertainty awareness, and revisability.

## 12. Epistemic Principles

These principles should remain valid across future models, tools, workflows, skills, and interfaces.

- Knowing is not storing. Knowing requires justified reliance.
- Evidence is not truth. Evidence supports, challenges, or refines judgment.
- Knowledge guides interpretation but does not automatically prove the local situation.
- Memory provides continuity but can become stale.
- User input is authoritative for intent and current correction, but not automatically perfect for every factual claim.
- Tools provide outputs, not final truth.
- OCR is perception, not certainty.
- Dashboard data is strong for recorded metrics but may still be incomplete or context-poor.
- Business Knowledge should improve judgment, not replace business-specific evidence.
- Confidence must be proportional to evidence quality and consequence.
- Unknown information should not automatically cause questions.
- Material uncertainty should influence judgment.
- Questions must earn their cost by improving judgment.
- Answering under uncertainty is acceptable when risk is proportionate and assumptions are clear.
- Conflicting evidence should be surfaced, resolved, or carried explicitly according to consequence.
- Fresh evidence may override stale evidence, but only with source-aware judgment.
- The Brain must be willing to change its mind.
- The Brain should behave like an experienced advisor: practical, evidence-aware, risk-sensitive, and humble.

## Final Requirement: What Would Make SME Brain Change Its Mind?

SME Brain should change its mind when new or re-evaluated evidence makes its current judgment less justified than an alternative.

It should change its mind when:

- the user corrects intent, preference, or current business context;
- fresh reliable evidence contradicts older memory;
- verified records contradict assumptions;
- OCR or tool output is corrected or shown to be unreliable;
- dashboard data reveals a different pattern;
- Business Knowledge indicates a risk the Brain missed;
- conflicting evidence becomes material;
- an assumption is no longer safe;
- a hypothesis explains the situation better than the prior one;
- risk increases or decreases materially;
- the business objective changes;
- constraints change;
- the expected outcome no longer serves the business owner.

Changing its mind is not weakness.

It is a requirement of good judgment.

The Brain should not defend earlier conclusions merely because it produced them. It should preserve continuity while remaining corrigible.

The final standard is:

> SME Brain changes its mind when better evidence, clearer context, or more responsible interpretation would improve business judgment.
