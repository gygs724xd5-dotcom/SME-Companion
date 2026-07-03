# SME Brain Truth Status Architecture Review

Architecture Review VI

Truth Status Runtime Constitution

Status: Doctrine Accepted For Future Runtime Design

Scope: Architecture only. No runtime, Python, module contract, API, prompt, workflow, memory mutation, retrieval behavior, or implementation mechanism is defined here.

## 1. Purpose

Truth Status is the constitutional layer that determines justified reliance.

It answers:

> What information can the SME Brain rely upon?

It does not answer:

> What information exists?

Evidence already owns that responsibility.

Truth Status exists because information does not become reliable merely by being present, fluent, recent, retrieved, remembered, extracted, calculated, or asserted. A user statement, memory record, document, tool result, dashboard metric, OCR output, skill result, or knowledge reference may be useful evidence. None of them is automatically truth.

Truth Status classifies the reliability status of claims so later layers can reason without converting support into certainty.

## 2. Constitutional Position

The cognitive runtime is:

```text
Reality
    -> Perception
    -> Business Situation
    -> Evidence
    -> Truth Status
    -> Perspective
    -> Knowledge
    -> Business Judgment
    -> Decision
    -> Execution
    -> Conversation
    -> Commit
```

Authority governs every layer but is not itself a cognitive layer.

Truth Status sits after Evidence and before Perspective because SME Brain must know how strongly it may rely on claims before selecting interpretive lenses, applying knowledge, forming judgment, choosing action, executing, communicating, or committing durable state.

## 3. Doctrine

Evidence represents information.

Truth Status evaluates reliance.

Perspective reasons over truth.

Knowledge applies doctrine.

Business Judgment evaluates business implications.

Decision commits action.

Every layer owns exactly one constitutional responsibility.

Truth Status should classify. It should never invent. It should never erase evidence. It should never replace business judgment.

## 4. What Is Truth?

Truth in SME Brain is not metaphysical certainty.

Truth is a claim's current justified status for reliance within a business situation.

This definition is intentionally practical because SME Brain operates under incomplete information, changing business context, memory decay, imperfect source quality, and consequence-sensitive decisions.

A claim may be treated as true only when available evidence justifies reliance at the level required by the current context. The same claim may have a different truth status in a different context if the consequence, freshness requirement, source fit, or conflict profile changes.

Truth Status therefore does not produce absolute truth. It produces governed truth status.

## 5. What Is Justified Reliance?

Justified reliance means SME Brain may allow a claim to influence downstream reasoning without misleading later layers about its strength.

Reliance is justified when the claim has enough support for the current consequence level, given:

- source reliability;
- source fit;
- directness;
- freshness;
- corroboration;
- conflict state;
- completeness;
- business relevance;
- reversibility of downstream action;
- cost of being wrong;
- authority constraints;
- user confirmation where required.

Justified reliance is not the same as confidence alone.

A claim can be likely but not reliance-worthy if the consequence is high, the source is weak, or the claim is stale. A claim can be partially reliable for low-risk reasoning while still unsuitable for execution or commit.

## 6. What Is Uncertainty?

Uncertainty is the condition in which a claim's status does not support unrestricted reliance.

Uncertainty may arise from:

- missing material evidence;
- stale evidence;
- ambiguous source meaning;
- weak source reliability;
- indirect evidence;
- incomplete evidence;
- conflicting evidence;
- inferred claims;
- estimates;
- changing business reality;
- unclear authority or ownership;
- high consequence relative to support.

Uncertainty is not failure.

Truth Status must preserve uncertainty as a constitutional object so later layers can reason honestly. Some uncertainty is acceptable for low-risk or reversible judgment. Some uncertainty must block conclusion, require caveats, trigger a question through Decision, or prevent commit.

Truth Status does not decide which action to take under uncertainty. It classifies the uncertainty and marks reliance boundaries for Business Judgment and Decision.

## 7. What Is Conflicting Evidence?

Conflicting evidence exists when two or more credible evidence items support incompatible claims, incompatible values, incompatible timing, or incompatible interpretations that matter to the business situation.

Conflict is material when resolving it could change:

- the truth status of a claim;
- the perspective selected;
- the applicable knowledge;
- the business judgment;
- the next decision;
- the safety of execution;
- the permissibility of commit;
- the honesty of conversation.

Truth Status may classify a conflict as resolved only when the evidence basis justifies preferring one claim over another.

It must preserve the conflict when resolution would require invention, hidden assumptions, source worship, or convenience.

Truth Status must never erase conflicting evidence. Evidence remains intact. Truth Status only classifies whether the conflict blocks reliance, limits reliance, or can be responsibly resolved.

## 8. What Is Historical Truth?

Historical truth is the justified status of a claim about what was true, recorded, believed, decided, observed, or done at a prior time.

Historical truth is not automatically current truth.

Examples:

- a prior store profile may historically record that the business sold lunch sets;
- a past conversation may historically show that the owner preferred discount campaigns;
- a prior receipt may historically show a transaction amount;
- an old dashboard snapshot may historically show last month's sales.

Those claims may be reliable history while no longer describing current reality.

Truth Status must preserve temporal scope. It should classify claims as historical when their evidentiary support is tied to a prior time and current applicability is not justified.

Historical truth can inform Knowledge, Perspective, Judgment, and Decision only with its temporal boundary visible.

## 9. What Is Runtime Truth?

Runtime truth is the current truth status assigned during an active cognitive pass.

It is local to the current business situation, evidence set, consequence level, and authority context.

Runtime truth may include:

- current facts;
- current observations;
- current assumptions;
- current estimates;
- current hypotheses;
- current disputes;
- current unsupported claims;
- current stale claims;
- current rejected claims.

Runtime truth does not mutate Evidence.

Runtime truth does not commit memory.

Runtime truth does not bind future cognition forever.

It is a governed statement of what SME Brain may rely on now.

## 10. Can Multiple Truths Coexist?

Multiple truth statuses can coexist.

Multiple incompatible final truths should not be collapsed into one conclusion unless Evidence and Truth Status justify the collapse.

Coexistence is valid when claims differ by:

- time;
- source;
- scope;
- business unit;
- owner;
- location;
- product;
- customer segment;
- confidence level;
- consequence level;
- perspective relevance.

For example, "the shop used to sell lunch sets" and "the shop now focuses on catering" can both be true when their temporal scopes differ.

"Dashboard revenue is stable" and "the owner reports sales feel down" can both be retained when they measure different realities or when the conflict is unresolved.

Truth Status should support plural classification:

- true within scope;
- historically true;
- currently true;
- assumed for now;
- plausible but unproven;
- disputed;
- stale;
- contradicted;
- unsupported;
- not reliance-worthy.

The constitutional standard is not forced singularity. It is honest reliance.

## 11. When Should SME Brain Refuse To Conclude?

SME Brain should refuse to conclude when Truth Status cannot justify reliance and a conclusion would create material risk, false certainty, unauthorized commitment, misleading communication, or inappropriate action.

Truth Status should mark refusal-to-conclude conditions when:

- material evidence is absent;
- evidence conflict is unresolved and decision-changing;
- source reliability is too weak for the consequence level;
- available evidence is stale for a current claim;
- the claim depends on unstated assumptions;
- the claim exceeds evidence scope;
- the claim would require legal, financial, medical, compliance, or contractual certainty beyond support;
- the claim would authorize irreversible or high-risk execution;
- the claim would become durable memory without confirmation;
- downstream layers would likely overstate the claim.

Refusing to conclude is not the same as refusing to help.

Truth Status may still provide bounded classifications such as "unresolved," "low-confidence estimate," "historical record only," "assumption for drafting," or "not reliable enough for execution." Business Judgment and Decision then determine whether to ask, proceed with caveats, defer, escalate, or decline action.

## 12. Layer Responsibilities

### Perception

Perception observes signals.

It notices user input, records, documents, tool outputs, memory cues, environment cues, and ambiguity.

It must not decide truth.

### Business Situation

Business Situation frames the active business reality.

It determines what situation is under attention and what information would be relevant.

It must not decide which claims are reliable.

### Evidence

Evidence collects, represents, and evaluates information quality.

It identifies source, relevance, reliability, freshness, completeness, directness, conflict, limitations, and gaps.

It must not decide justified reliance.

### Truth Status

Truth Status classifies claims by reliance status.

It decides what is fact, assumption, estimate, observation, hypothesis, disputed, stale, unsupported, rejected, historically true, or currently reliance-worthy.

It must not collect evidence, retrieve information, classify business situations, produce recommendations, make decisions, modify memory, modify evidence, or resolve workflow.

### Perspective

Perspective selects interpretive lenses using Truth Status.

It reasons over facts, assumptions, hypotheses, and conflicts at their proper strength.

It must not override truth labels.

### Knowledge

Knowledge applies stable doctrine, policies, principles, rules, skills, procedures, domain models, and experience.

It must distinguish general knowledge from locally justified truth.

It must not turn general doctrine into current fact.

### Business Judgment

Business Judgment evaluates business implications.

It weighs truth, uncertainty, perspectives, knowledge, risk, opportunity, constraints, and goals.

It must not silently upgrade assumptions into facts.

### Decision

Decision selects the next authorized action.

It may decide to answer, ask, defer, refuse, execute, escalate, or commit based on judgment and authority.

It must not create truth.

### Execution

Execution performs authorized operational work.

Execution results become new evidence candidates.

Execution must not treat its result as final truth without Truth Status.

### Conversation

Conversation expresses judgment, decision, uncertainty, and results.

It must preserve truth status faithfully.

It must not smooth uncertainty into certainty.

### Commit

Commit governs durability, finality, external effects, and memory writes.

It may rely on Truth Status when deciding whether a claim may become durable.

It must not make uncertain claims durable as facts.

## 13. Constitutional Invariants

Truth Status must obey these invariants:

- Evidence represents information; Truth Status evaluates reliance.
- Truth Status classifies claims; it does not invent claims.
- Truth Status never erases, edits, suppresses, or rewrites evidence.
- Truth Status never retrieves evidence or searches for information.
- Truth Status never treats memory as current truth without evaluation.
- Truth Status never treats tool output as final truth.
- Truth Status never treats model fluency as proof.
- Truth Status never treats workflow completion as evidence of truth.
- Truth Status never creates recommendations.
- Truth Status never chooses actions.
- Truth Status never executes.
- Truth Status never commits memory.
- Truth Status never replaces Business Judgment.
- Truth Status preserves material uncertainty.
- Truth Status preserves unresolved conflict.
- Truth Status distinguishes historical truth from runtime truth.
- Truth Status supports multiple scoped truths when scope justifies coexistence.
- Truth Status refuses conclusion when reliance is not justified for the consequence level.
- Truth Status exposes reliance boundaries to downstream layers.

## 14. Relationship With Evidence

Evidence is upstream of Truth Status.

Evidence answers:

> What information exists?

Truth Status answers:

> What information can be relied upon?

Evidence may provide:

- evidence items;
- source classifications;
- claims;
- relevance;
- reliability;
- freshness;
- completeness;
- directness;
- conflicts;
- limitations;
- gaps;
- candidate truth-status hints.

Truth Status may consume those outputs but cannot replace them.

Evidence remains accountable for representing information. Truth Status remains accountable for reliance classification.

Truth Status may reject reliance on evidence without deleting the evidence. It may accept reliance on a claim only to the degree justified. It may mark a claim as historical, stale, low-confidence, disputed, assumption, estimate, or unsupported.

The boundary is:

```text
Evidence says: this source supports this claim with these qualities and limitations.
Truth Status says: this claim may or may not be relied on under these boundaries.
```

## 15. Relationship With Perspective

Perspective is downstream of Truth Status.

Perspective receives claims with reliance labels, not raw certainty.

Perspective may reason differently depending on whether a claim is:

- fact;
- assumption;
- estimate;
- hypothesis;
- disputed;
- historical;
- stale;
- unsupported;
- rejected.

Perspective must not strip those labels.

If a customer-trust perspective depends on a disputed complaint, it must preserve that dispute. If a financial perspective depends on an estimated margin, it must preserve that estimate. If a strategic perspective depends on stale memory, it must keep the temporal limitation visible.

Truth Status constrains Perspective by defining the epistemic strength of material used for lenses.

Perspective constrains later Judgment by ensuring that truth-labeled material is interpreted through relevant business viewpoints.

## 16. Relationship With Knowledge

Knowledge is downstream of Perspective and constrained by Truth Status.

Knowledge applies doctrine to claims, but general doctrine does not create local truth.

For example:

- pricing knowledge may say discounts can damage perceived value;
- refund knowledge may say fair service recovery protects trust;
- operations knowledge may say bottlenecks can mimic sales problems;
- finance knowledge may say revenue can rise while profit falls.

Those are useful knowledge references. They are not proof that the user's business currently has those conditions.

Truth Status protects Knowledge from becoming generic certainty. Knowledge may use truth-labeled claims as anchors, assumptions as conditional premises, hypotheses as possibilities, and conflicts as limits.

Knowledge must not upgrade a plausible doctrine into a current fact.

## 17. Truth Status Classifications

Future runtime design should support these constitutional classifications:

- `fact`: justified for reliance in the current context;
- `observation`: reported or detected condition requiring interpretation;
- `assumption`: working premise accepted within explicit limits;
- `estimate`: approximate value with known uncertainty;
- `hypothesis`: plausible explanation not yet established;
- `belief`: current position based on evidence and reasoning, below settled fact where appropriate;
- `disputed`: credible evidence conflicts materially;
- `historical`: justified about a prior time, not automatically current;
- `stale`: formerly supported but freshness is insufficient for current reliance;
- `unsupported`: claim lacks sufficient evidence;
- `contradicted`: stronger evidence challenges the claim;
- `rejected`: not reliance-worthy because of contradiction, scope failure, irrelevance, unreliability, or authority constraint;
- `refuse_to_conclude`: no responsible conclusion is justified for the current consequence level.

These are architectural categories, not implementation enums.

## 18. Diagnostic Duties

Truth Status diagnostics should be able to explain:

- which claims were evaluated;
- what status each material claim received;
- why the status was assigned;
- which evidence supported the status;
- which evidence limited or challenged the status;
- whether reliance is current, historical, scoped, conditional, or blocked;
- what uncertainty remains;
- what conflict remains;
- what would change the status;
- which downstream layers must preserve caveats.

Diagnostics exist for constitutional accountability. They are not necessarily user-facing.

## 19. Failure Modes

### Evidence Collapse

Evidence is treated as truth merely because it exists.

### Source Worship

A dashboard, tool, memory record, OCR result, skill output, or user statement is trusted because of source category rather than source fit.

### Recency Capture

The newest claim overrides stronger evidence without justification.

### Memory Capture

Stored context silently becomes current business reality.

### Fluency Capture

A generated explanation sounds confident and is treated as proof.

### Conflict Suppression

Contradictions are hidden so downstream reasoning feels cleaner.

### Assumption Laundering

An assumption becomes a fact because it passes through multiple layers.

### Judgment Leakage

Truth Status begins recommending actions or selecting what is best.

### Commit Leakage

Uncertain claims become durable memory or external commitments.

## 20. Future Runtime Roadmap

Future Truth Status runtime work should follow the standard cognitive layer lifecycle:

```text
Runtime Foundation
    -> Registry
    -> Diagnostics
    -> Runtime State
    -> Behavior
```

### Phase 1: Runtime Foundation

Define Truth Status purpose, inputs, outputs, constitutional boundaries, invariants, and allowed classifications.

No retrieval, recommendations, decisions, memory writes, or execution behavior should be introduced.

### Phase 2: Truth Status Registry

Define recognized truth classifications, reliance dimensions, conflict states, historical/current scope labels, and refusal-to-conclude categories.

The registry should constrain vocabulary so Truth Status remains classification rather than free-form judgment.

### Phase 3: Diagnostics

Expose claim-level status, reasons, supporting evidence references, limiting evidence references, conflict status, uncertainty status, and change conditions.

Diagnostics must make false certainty visible during development.

### Phase 4: Runtime State

Introduce a structured truth-state object that downstream layers can consume without reclassifying evidence or losing caveats.

Runtime state must remain temporary unless Commit later authorizes durability.

### Phase 5: Downstream Integration

Perspective should consume Truth Status labels.

Knowledge should apply doctrine only within truth boundaries.

Business Judgment should reason from facts, assumptions, estimates, hypotheses, and conflicts without silently upgrading them.

Decision should use refusal-to-conclude and uncertainty markers when choosing whether to answer, ask, defer, execute, or refuse.

Commit should prevent uncertain claims from becoming durable facts.

### Phase 6: Behavior

Only after foundation, registry, diagnostics, and runtime state are stable should user-visible behavior depend on Truth Status.

Behavior should communicate uncertainty only when material. It should not expose internal machinery by default.

## 21. Architecture Decision

Truth Status is a required constitutional layer.

It owns justified reliance.

It must remain separate from Evidence, Perspective, Knowledge, Business Judgment, Decision, Execution, Conversation, Commit, and Authority.

The official boundary is:

```text
Evidence represents information.
Truth Status evaluates reliance.
Perspective reasons over truth.
Knowledge applies doctrine.
Business Judgment evaluates business implications.
Decision selects action.
Execution performs authorized work.
Conversation expresses faithfully.
Commit governs finality.
Authority governs responsibility.
```

Truth Status should classify what SME Brain may rely on.

It should never invent information, erase evidence, produce recommendations, make decisions, modify memory, resolve workflow, or replace business judgment.

The constitutional standard is:

> SME Brain must know the difference between information that exists and information it may responsibly rely upon.
