# SME Brain Business Ontology

SME Companion V6 sees the business world through business meaning, not workflow machinery.

This document defines the semantic foundation for how SME Brain perceives business reality before it reasons, judges, decides, or responds. It extends `SME_BRAIN.md` and `SME_BRAIN_CONTRACTS.md`.

The ontology is not implementation. It does not define code, classes, APIs, database structures, UI components, or workflow states.

It answers one question:

> What exists inside the business world of SME Brain?

## 1. Purpose of Business Ontology

Ontology defines what the Brain can perceive.

Cognition depends on ontology because the Brain cannot reason well about a world it cannot name. If the Brain sees the world as workflows, states, steps, and missing fields, it will behave procedurally. If it sees the world as business situations, objectives, evidence, uncertainty, opportunities, risks, constraints, capabilities, and conversation purposes, it can exercise judgment.

The ontology exists to prevent procedural concepts from becoming the center of thought.

It gives SME Brain a stable vocabulary for business reality:

- what is happening;
- what the user may want;
- what evidence exists;
- what is unknown;
- what could improve the business;
- what could harm the business;
- what limits action;
- what the Brain can do;
- why the Brain should communicate.

Without ontology, the Brain is vulnerable to routing language.

With ontology, the Brain can interpret business meaning before deciding whether any workflow, skill, tool, or response is appropriate.

## 2. Business Situation

A Business Situation is a meaningful business condition or moment that calls for judgment, help, action, interpretation, or support.

It is not a workflow state.

It is not a task step.

It is not a missing-field container.

A Business Situation answers:

> What business reality is the user facing now?

Examples include:

**Sales Declining**

The business may be experiencing lower revenue, lower order volume, fewer customers, reduced conversion, smaller basket size, weaker repeat purchases, or seasonal demand changes.

The Brain should perceive this as a diagnostic and strategic situation, not as a predefined sales workflow.

**Customer Complaint**

The business may face customer dissatisfaction, reputation risk, service recovery needs, operational defects, refund decisions, or communication risk.

The Brain should perceive both the human relationship and the business consequence.

**Marketing Opportunity**

The business may have a timely chance to attract demand, launch a promotion, use a seasonal moment, respond to a local event, or engage customers.

The Brain should perceive potential value, timing, audience, offer, and risk.

**Need Pricing Decision**

The business may need to set, change, discount, bundle, or defend prices.

The Brain should perceive margin, positioning, customer perception, competitor pressure, and cash implications.

**Inventory Shortage**

The business may not have enough stock, ingredients, materials, or capacity to fulfill demand.

The Brain should perceive operational continuity, substitution options, customer expectations, cash tied in stock, and urgency.

**Business Growth Opportunity**

The business may be considering expansion, hiring, new products, new channels, partnerships, or additional investment.

The Brain should perceive upside, constraints, risk, timing, operational readiness, and owner capacity.

A Business Situation may contain several overlapping realities. "Sales are down" may include pricing risk, marketing opportunity, inventory constraints, customer retention weakness, and financial pressure at the same time.

The Brain must not flatten a situation into a single workflow too early.

## 3. Business Objective

A Business Objective is a desired business outcome.

Objectives describe what the user or business may want to improve, achieve, prevent, create, or decide.

Examples include:

- increase sales;
- reduce costs;
- improve customer retention;
- launch a new product;
- improve cash flow;
- reduce waste;
- recover from a customer complaint;
- improve staff productivity;
- attract new customers;
- increase repeat purchases;
- protect brand trust.

Objectives are different from workflows.

An objective says:

> What outcome matters?

A workflow says:

> What procedure should be followed?

The same objective may be served by many possible actions. Increasing sales may involve promotion, pricing changes, product bundling, customer reactivation, new channels, better signage, improved conversion, or operational fixes.

The Brain should treat objectives as outcome direction, not procedural control.

Objectives may be explicit, inferred, competing, or evolving. The Brain must be able to revise its understanding of the objective as the situation becomes clearer.

## 4. Evidence

Evidence is any information that may help the Brain understand the business situation, form judgment, reduce uncertainty, identify risk, identify opportunity, or decide the next useful action.

Evidence is not automatically true.

Evidence has source, reliability, confidence, freshness, and importance.

Possible sources include:

**Conversation**

What the user has said in the current exchange or prior turns.

Conversation is often high relevance but may be incomplete, emotional, ambiguous, or informal.

**Store Profile**

Stable known facts about the business, such as business type, products, location, audience, operating model, brand, or owner preferences.

Store Profile evidence is useful for continuity but may become stale.

**Business Memory**

Durable remembered facts, preferences, decisions, patterns, and history about this business.

Business Memory reduces repeated questions, but it must be checked for freshness and conflict.

**Business Knowledge**

Generalizable business, domain, market, strategic, regulatory, or methodological knowledge.

Business Knowledge improves judgment but is not specific proof about this business unless connected to local evidence.

**OCR**

Text or structure extracted from images, scans, receipts, menus, screenshots, labels, invoices, or documents.

OCR evidence may be highly useful but must be treated according to extraction quality.

**Dashboard**

Current or historical business metrics, operational records, sales data, inventory, expenses, customer data, or performance indicators.

Dashboard evidence may be reliable when well-maintained, but it can still be incomplete, delayed, or context-poor.

**Analytics**

Derived patterns, comparisons, trends, forecasts, ratios, summaries, or performance signals.

Analytics can reveal meaning but depend on input quality, time range, assumptions, and method.

**External Information**

Information from outside the business, such as market trends, platform rules, competitor context, regulations, public events, seasonality, or economic conditions.

External evidence may improve judgment but should be checked for relevance, recency, and reliability.

**User Input**

Direct statements, corrections, preferences, constraints, confirmations, or clarifications from the user.

Current user input is often authoritative about intent and context, but may still require interpretation when stakes are high.

Evidence should be evaluated by:

- reliability: how trustworthy the source is;
- confidence: how strongly it supports a conclusion;
- freshness: whether it is current enough;
- importance: how much it could affect judgment;
- consistency: whether it conflicts with other evidence;
- directness: whether it observes the issue directly or indirectly.

The Brain should not seek all possible evidence. It should seek evidence when it materially improves judgment.

## 5. Material Uncertainty

Uncertainty is an unknown, ambiguity, conflict, stale assumption, weak inference, or unsupported belief in the business situation.

Not all uncertainty matters.

The ontology distinguishes three levels:

**Unknown**

Something the Brain does not know.

Example: the exact brand color for a social post.

Unknowns are common and unavoidable.

**Unimportant Unknown**

Something the Brain does not know but that does not materially change the next useful action.

Example: the exact brand color may not matter when the user asks for rough campaign ideas.

Unimportant unknowns should not trigger questions.

**Material Uncertainty**

Something unknown, ambiguous, conflicting, stale, or risky enough that resolving it could change the recommendation, action, warning, or business outcome.

Example: whether a promotion is meant to attract new customers or reactivate existing customers may materially change the offer, message, and channel.

Material Uncertainty should influence judgment when:

- it changes the likely best action;
- it changes risk;
- it changes expected business impact;
- it changes whether assumptions are acceptable;
- it changes whether the Brain should answer, ask, calculate, verify, search, or warn;
- it may cause financial, operational, legal, customer, or brand harm if ignored.

The Brain should not worship certainty.

It should manage uncertainty in proportion to business consequence.

## 6. Business Opportunity

A Business Opportunity is a possible path to improve the business situation.

An opportunity is not the same as an objective.

An objective is the desired outcome.

An opportunity is a possible opening, lever, timing advantage, or improvement path that may help achieve an objective.

Examples include:

**Promotion**

A chance to stimulate demand through offer, timing, message, channel, or audience focus.

**Seasonality**

A predictable or timely demand pattern, such as holidays, school terms, weather, local events, paydays, or cultural moments.

**Cross-selling**

An opportunity to increase order value by pairing related products or services.

**Upselling**

An opportunity to move customers toward higher-value options, premium versions, bundles, or add-ons.

**Operational Improvement**

A chance to reduce waste, save time, improve service speed, reduce errors, or increase capacity.

Other opportunities may include partnerships, new channels, customer reactivation, price repositioning, product launches, staff training, better merchandising, supplier changes, or loyalty programs.

The Brain should identify opportunities as possibilities, not commands.

An opportunity must be judged against risk, constraints, evidence, and objective fit.

## 7. Business Risk

Business Risk is the possibility that an action, inaction, assumption, or recommendation could harm the business.

Risk is central to judgment because a helpful answer is not merely one that achieves an objective. It must also avoid unnecessary harm.

Examples include:

**Pricing Risk**

A price, discount, bundle, or promotion may reduce margin, damage positioning, train customers to wait for discounts, or create unfair expectations.

**Inventory Risk**

The business may run out of stock, overstock, waste perishable goods, tie up cash, or fail to fulfill demand.

**Customer Satisfaction Risk**

An action may disappoint customers, mishandle complaints, weaken trust, create confusion, or damage reviews.

**Financial Risk**

The business may face cash flow pressure, margin loss, debt burden, uncontrolled expense, poor investment timing, or unsustainable commitments.

**Operational Risk**

The business may lack staff, time, process, capacity, supplier reliability, quality control, or execution readiness.

Other risks may include legal, regulatory, tax, brand, platform, safety, privacy, reputational, partnership, and owner-burnout risks.

Risks influence judgment by changing:

- whether to answer directly;
- whether to warn;
- whether to ask;
- whether to calculate;
- whether to verify evidence;
- whether to recommend a safer option;
- whether to require confirmation;
- whether to avoid action.

The Brain must be able to challenge the user's premise when risk justifies it.

## 8. Business Constraints

Business Constraints are limits that shape what is possible, wise, legal, affordable, timely, or acceptable.

Constraints are not failures. They are part of business reality.

Examples include:

**Budget**

Available money, spending limits, cash flow, affordability, or investment capacity.

**Time**

Deadlines, owner availability, staff time, lead time, opening hours, seasonality, or urgency.

**Resources**

Staff, tools, ingredients, inventory, equipment, suppliers, space, skills, customer base, and operating capacity.

**Policies**

Business rules, refund policies, service policies, platform policies, compliance obligations, or internal operating standards.

**Halal Requirements**

Religious, sourcing, preparation, labeling, handling, certification, or customer trust constraints that affect products, suppliers, operations, or communication.

**Business Rules**

Owner-defined or business-defined rules such as minimum margin, no discounting, premium positioning, delivery radius, approved suppliers, product exclusions, or brand voice.

Constraints should guide judgment rather than merely block action.

A good Brain uses constraints to produce realistic recommendations.

## 9. Business Capability

A Business Capability is something SME Brain can do to help the business.

Capability describes function, not ownership.

Examples include:

- calculate;
- forecast;
- analyze;
- recommend;
- summarize;
- generate content;
- OCR;
- search knowledge;
- search memory;
- compare options;
- diagnose;
- classify;
- extract;
- translate;
- explain;
- validate;
- plan;
- monitor;
- estimate.

Capability is different from Skill.

A capability is the kind of help that can be performed.

A Skill is a bounded mechanism that executes one or more capabilities under Brain supervision.

For example, "forecast" is a capability. A future cash flow forecasting skill may execute that capability. The Brain still decides whether forecasting is needed, what evidence matters, how risk should be handled, and how the result should be communicated.

Capabilities belong to the Brain's perception of what help is possible.

Skills belong to execution.

## 10. Business Skill

A Business Skill is a bounded capability executor.

Skills exist to perform specialized business work, not to own conversation or reasoning.

Skills may analyze, generate, extract, transform, compare, summarize, validate, calculate, or produce bounded recommendations within their scope.

Skills do not own conversations.

Skills do not own reasoning.

Skills never decide.

Skills never determine the user's final objective.

Skills never ask the user directly merely because information is missing.

Skills never produce final conversation.

Skills return evidence, findings, assumptions, limitations, confidence, and bounded recommendations to the Brain.

The Brain decides whether the Skill result is useful, sufficient, risky, incomplete, or worth communicating.

If a Skill requires the user to move through its own sequence of prompts, it has become a workflow owner and violates the ontology.

## 11. Decision Context

Decision Context is everything the Brain should consider before choosing what to do next.

It is the semantic environment for judgment.

Decision Context may include:

- Business Situation;
- Business Objective;
- Evidence;
- Material Uncertainty;
- Business Risk;
- Business Opportunity;
- Business Constraints;
- Memory;
- Knowledge;
- user intent;
- expected business impact;
- cost of asking;
- cost of acting;
- reversibility;
- urgency;
- confidence;
- available capabilities;
- user preference;
- communication needs.

Decision Context does not require all information to be complete.

It requires enough meaning to choose a useful next action.

The Brain should consider Decision Context to determine whether to answer, ask, search memory, search knowledge, calculate, use OCR, call a tool, invoke a skill, warn, confirm, support, or challenge.

## 12. Conversation Purpose

Conversation exists to help the business owner act, understand, decide, recover, improve, or feel supported.

The ontology includes conversation purpose because communication is not just output. It is part of business help.

Examples include:

**Teach**

Help the user understand a concept, pattern, method, tradeoff, or business principle.

**Recommend**

Advise a course of action based on judgment.

**Warn**

Surface risk that the user may not see.

**Confirm**

Seek approval before persistence, external action, irreversible action, or high-risk continuation.

**Explore**

Help discover direction when the situation is open-ended or ambiguous.

**Clarify**

Ask a focused question when material uncertainty blocks useful judgment.

**Support**

Help the user handle pressure, confusion, customer conflict, or decision overload while still staying business-focused.

**Challenge**

Push back when the user's premise, desired action, or assumption may harm the business.

Conversation Purpose ensures that the Brain speaks for a reason.

The Brain should not generate responses merely because a workflow step requires text.

## 13. Relationships

The ontology concepts relate by meaning, not implementation sequence.

A Business Situation is the business reality under attention.

A Business Objective describes the outcome that may matter.

Evidence informs what the Brain can believe.

Material Uncertainty identifies what may be unknown enough to change judgment.

Business Opportunity identifies possible upside.

Business Risk identifies possible harm.

Business Constraints define the limits of responsible action.

Business Capability defines what kinds of help are possible.

Business Skill executes bounded capabilities when the Brain asks for them.

Decision Context brings the relevant concepts together before action.

Conversation Purpose explains why the Brain communicates.

The conceptual relationship is:

```text
Business Situation
        |
        v
Business Objective
        |
        v
Evidence + Memory + Knowledge
        |
        v
Material Uncertainty
        |
        v
Opportunity + Risk + Constraints
        |
        v
Judgment
        |
        v
Decision
        |
        v
Conversation Purpose
        |
        v
Conversation
```

This is not a workflow.

The Brain may enter through any concept. A user may present a risk first, an objective first, evidence first, a complaint first, or an opportunity first.

The relationship describes semantic dependence, not procedural order.

## 14. Ontology Boundaries

The following do not belong inside SME Brain Ontology:

**Workflow**

Workflow is a subordinate execution mechanism. It is not how the Brain sees business reality.

**State Machines**

State machines describe procedural control. The ontology describes business meaning.

**Steps**

Steps belong to plans, procedures, or execution. They are not fundamental business entities.

**Missing Fields**

Missing fields belong to structures. The Brain cares about material uncertainty.

**UI Components**

Buttons, forms, screens, panels, and layouts are interface details. They do not define business reality.

**Implementation Details**

Functions, modules, files, classes, services, prompts, storage choices, and orchestration mechanisms are implementation concerns.

**Database Objects**

Tables, records, columns, indexes, documents, and storage formats may represent business meaning, but they are not the ontology itself.

**API Structures**

Requests, responses, endpoints, payloads, and protocol shapes are technical contracts, not cognitive ontology.

**Routing Labels**

Intent labels, route names, workflow IDs, and handler names may assist implementation, but they must not become the Brain's view of the world.

These concepts are excluded because they encourage the Brain to perceive machinery instead of business reality.

## 15. Stability Rules

This ontology should remain stable for many years.

It may evolve, but only by preserving the distinction between business meaning and procedural machinery.

Safe evolution principles:

- Add concepts only when they represent durable business reality.
- Do not add concepts merely because an implementation needs a container.
- Do not rename workflow concepts and place them inside the ontology.
- Prefer broader semantic concepts over narrow procedural labels.
- Keep objectives separate from workflows.
- Keep uncertainty separate from missing data.
- Keep capabilities separate from skills.
- Keep evidence separate from truth.
- Keep conversation purpose separate from response text.
- Keep ontology independent of UI, database, API, and model choices.
- Reject any ontology change that makes asking questions mandatory because data is absent.
- Reject any ontology change that lets Skills own reasoning or conversation.
- Preserve explainability: the Brain must be able to say why a concept influenced judgment.

The ontology should be challenged whenever a new concept is proposed.

The test is:

> Does this concept describe business reality, or does it describe machinery?

If it describes machinery, it does not belong here.

## Final Answer: If Workflow Disappeared Tomorrow

If Workflow disappeared tomorrow, SME Brain should still understand the business world.

It should still perceive:

- business situations;
- objectives;
- evidence;
- uncertainty;
- opportunities;
- risks;
- constraints;
- capabilities;
- skill boundaries;
- decision context;
- conversation purpose.

Workflow is not required for understanding.

Workflow may help execute known procedures, but it does not define what the business is, what the user needs, what evidence means, what risk exists, what opportunity is available, or why the Brain should communicate.

If removing Workflow makes the Brain unable to understand the user, then Workflow was secretly the ontology.

That would be a failure.

The correct standard is:

> SME Brain understands business reality first. Workflow, if present, is only one possible instrument for acting on that understanding.
