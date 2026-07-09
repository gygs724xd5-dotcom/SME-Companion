# SME Companion V5.15.0 Business Skill Schema / Business Knowledge Contract

V5.15.0 defines the Business Skill Schema / Business Knowledge contract as documentation only.

This document does not introduce runtime code, app changes, skill loader implementation, workflow behavior, router behavior, planner behavior, prompts, tests, active gates, or business vertical implementation.

Response Authority, Evidence Gap, Business Situation, Dashboard Snapshot, and Business Skill remain shadow/read-only or contract-only. Final response behavior is unchanged.

## 1. Purpose

Business Skill Schema defines a reusable schema for SME business skills.

Its purpose is to:

- give SME Companion structured business capabilities beyond generic chat;
- connect business knowledge, evidence requirements, reasoning, response posture, and tools;
- support future expansion from 20 core domains toward 100+ standardized skills;
- keep business skill selection observable, deterministic, and safe;
- define how future skills are defined, loaded, selected, reasoned with, tested, and observed.

Business skills are bounded business capabilities under SME Brain supervision. They are not conversation owners, response authorities, workflow authorities, or memory writers.

## 2. Non-goals

V5.15.0 does not:

- implement a skill loader;
- create all 100 skills;
- add vertical workflows;
- replace Response Authority, Evidence Gap, or Business Situation;
- make recommendations without evidence;
- activate any gate;
- change app behavior, routing, planning, prompts, workflows, response generation, or UI behavior.

## 3. Position in the SME Brain Stack

Suggested V5.15 position:

```text
Perception / Understanding
    -> Truth Status
    -> Evidence Gap Intelligence
    -> Business Situation Reasoning
    -> Business Skill Schema / Business Knowledge
    -> Cognitive Response Authority
    -> Response Generation
    -> Commit Boundary
    -> Diagnostics Dashboard
```

Business Skill Schema sits in the Knowledge layer. It declares what reusable capability exists and what evidence, rules, reasoning, confidence, risk, tools, memory, and diagnostics govern that capability.

It does not execute the skill, select final response mode, compose final wording, start workflows, call tools, mutate memory, or commit state.

## 4. Relationship With Existing Layers

### Response Authority

Response Authority decides the authorized response mode.

Business Skill does not directly choose final response mode. A skill may suggest response posture or domain-specific answer structure, but Response Authority remains responsible for whether the turn is a direct answer, business analysis, clarification, workflow, refusal, reset acknowledgement, or LLM-assisted response.

### Evidence Gap

Evidence Gap determines whether required skill evidence is present.

The skill schema declares required evidence. A future Evidence Gap runtime may use skill requirements to detect missing, stale, contradictory, or confirmable evidence. Missing evidence should be handed to Evidence Gap instead of handled privately by the skill.

### Business Situation

Business Situation identifies the situation type, business domain, perspective stance, risk, opportunity, urgency, and owner attention.

Future skill selection may use `situation_type`, `business_domain`, and `perspective_stance` as selection signals. Business Skill must not override the situation profile.

### Diagnostics Dashboard

The Diagnostics Dashboard may show selected skill, missing evidence, confidence, mismatch flags, and shadow status in a future version.

The dashboard remains read-only. Dashboard display must not activate skill behavior or make diagnostics authoritative.

## 5. Core Business Skill Object

The canonical `BusinessSkill` schema should use these fields:

```yaml
skill_id: "cost_per_unit_calculation"
skill_version: "5.15.0"
skill_name: "Cost Per Unit Calculation"
business_domain: "Cost"
business_subdomain: "Unit Economics"
skill_category: "Calculation Skill"
intent_patterns: []
example_questions: []
supported_situation_types: []
required_evidence: []
optional_evidence: []
evidence_quality_rules: []
reasoning_steps: []
calculation_rules: []
business_rules: []
response_template: {}
follow_up_policy: {}
tool_requirements: []
memory_requirements: {}
confidence_policy: {}
risk_policy: {}
assumptions_policy: {}
diagnostics_contract: {}
tests_required: []
active_status: "CONTRACTED"
```

Field meanings:

- `skill_id`: stable machine-readable identifier.
- `skill_version`: version of the skill contract or definition.
- `skill_name`: human-readable name.
- `business_domain`: canonical domain.
- `business_subdomain`: narrower domain area when useful.
- `skill_category`: skill category such as explanation, calculation, diagnostic, or reporting.
- `intent_patterns`: phrases, intents, or semantic signals that may indicate relevance.
- `example_questions`: representative user questions.
- `supported_situation_types`: Business Situation types the skill can support.
- `required_evidence`: evidence that must be present or explicitly assumable.
- `optional_evidence`: evidence that improves quality but does not block output.
- `evidence_quality_rules`: freshness, confidence, source, and validation requirements.
- `reasoning_steps`: structured non-final reasoning path.
- `calculation_rules`: formulas, rounding rules, and numeric constraints.
- `business_rules`: domain rules and operating constraints.
- `response_template`: non-final structure for downstream response generation.
- `follow_up_policy`: smallest-question and duplicate-question rules.
- `tool_requirements`: tools the skill may need if runtime later permits tool use.
- `memory_requirements`: memory reads, confirmation needs, and mutation boundaries.
- `confidence_policy`: how skill confidence is calculated or downgraded.
- `risk_policy`: risk triggers, escalation, and blocked conditions.
- `assumptions_policy`: allowed assumptions, default assumptions, and disclosure rules.
- `diagnostics_contract`: stable diagnostic keys and expected values.
- `tests_required`: required validation categories before activation.
- `active_status`: lifecycle status; V5.15.0 uses contract-only status.

## 6. Canonical 20 Business Domains

Initial V5.15 domain taxonomy:

| Domain | Scope |
| --- | --- |
| Product | Products, SKUs, descriptions, variants, positioning, bundles. |
| Inventory | Stock levels, reorder risk, shrinkage, availability, stock movement. |
| Sales | Sales conversations, objections, follow-up, conversion, pipeline. |
| Customer | Customer profiles, service history, segmentation, retention, complaints. |
| Pricing | Price setting, discounts, bundles, willingness to pay, value framing. |
| Cost | Cost inputs, unit cost, cost changes, contribution margin, break-even. |
| Accounting | Revenue, expenses, reconciliation, reports, owner summaries. |
| Marketing | Campaigns, promotions, content, audiences, channels, offer clarity. |
| Supplier | Supplier records, terms, reliability, negotiation, alternatives. |
| Purchasing | Purchase planning, order quantities, budget fit, receiving. |
| Recipe / Production | Recipes, bill of materials, yield, batch production, production cost. |
| Operations | SOPs, daily process, bottlenecks, fulfillment, service consistency. |
| HR / Staff | Roles, schedules, hiring, training, tasking, staff communication. |
| Documents | Business documents, contracts, invoices, policies, forms. |
| Dashboard / Reporting | KPIs, alerts, summaries, dashboard explanations, reporting views. |
| Cashflow | Cash obligations, inflows, shortages, working capital, timing risk. |
| Profitability | Gross margin, net profit, product profitability, profit drivers. |
| Workflow Engine | Workflow status, procedural support, recovery, process orchestration. |
| Business Knowledge | Memory lookup explanation, knowledge application, domain doctrine. |
| Executive Intelligence | Owner priorities, decision briefings, strategy, governance, expansion. |

These domains are taxonomy only. V5.15.0 does not implement vertical behavior.

## 7. Business Skill Categories

Business skills should declare one primary category:

- `Explanation Skill`: explains a concept, metric, rule, or business situation.
- `Calculation Skill`: computes a result from validated inputs.
- `Diagnostic Skill`: identifies likely issue, risk, gap, or cause candidate.
- `Comparison Skill`: compares options, periods, suppliers, products, or outcomes.
- `Planning Skill`: structures a practical plan or sequence.
- `Checklist Skill`: produces a bounded checklist or readiness review.
- `Data Capture Skill`: structures information for later use without committing it.
- `Workflow Support Skill`: supports workflow status, preparation, or interpretation.
- `Decision Support Skill`: contributes bounded decision analysis under Brain supervision.
- `Reporting Skill`: summarizes business data, dashboard state, or owner-facing status.

The category describes capability shape. It does not grant authority to choose response mode, start workflows, ask users directly, or produce final wording.

## 8. Required Evidence Schema

Each required evidence item should use this schema:

```yaml
field_name: "unit_cost"
field_type: "number"
required: true
source: "current_turn | business_memory | workflow_context | document | dashboard | tool | user_confirmation"
freshness: "current_turn | session | durable | max_age:30d | not_applicable"
confidence_required: 0.8
example_values: [12.5, 100, "confirmed supplier invoice total"]
validation_rule: "positive_number"
missing_question: "What is the unit cost?"
can_assume: false
assumption_default: null
sensitive: false
user_confirmation_required: false
```

Field meanings:

- `field_name`: stable evidence field identifier.
- `field_type`: expected data type or semantic type.
- `required`: whether the field blocks skill readiness.
- `source`: allowed evidence source.
- `freshness`: freshness requirement for the field.
- `confidence_required`: minimum acceptable evidence confidence.
- `example_values`: examples for documentation and tests.
- `validation_rule`: deterministic validation rule or named validator.
- `missing_question`: smallest next question candidate.
- `can_assume`: whether the skill may proceed with a disclosed assumption.
- `assumption_default`: default value or assumption note when allowed.
- `sensitive`: whether the evidence requires extra care.
- `user_confirmation_required`: whether user confirmation is needed before use.

## 9. Evidence Requirement Rules

Business skills must declare required evidence explicitly.

Rules:

- Missing evidence should be handed to Evidence Gap.
- Skills must not ask duplicate questions.
- Skills must not use stale completed workflow context after reset.
- Durable business memory may inform optional evidence but must not override the current turn.
- Current user statements outrank stale durable memory unless Truth Status or policy says otherwise.
- Workflow-owned evidence must be ignored after reset or release unless the user explicitly re-enters that workflow.
- If evidence is insufficient, skill output should be blocked or downgraded.
- If evidence is contradictory, skill output must fail closed or return a blocked diagnostic.
- If evidence is assumable, the assumption must be explicit and visible to downstream layers.

## 10. Reasoning Contract

Business skills should define:

- `reasoning_steps`;
- `calculation_rules`;
- `business_rules`;
- `constraints`;
- `output_claim_limits`;
- `assumptions`;
- confidence calculation;
- failure conditions.

Reasoning rules:

- Reasoning must be structured and non-final.
- Skill reasoning must stay inside the skill scope.
- Skill reasoning must not hide unsupported assumptions.
- Skill reasoning must not convert general knowledge into local fact.
- Calculation rules must define formulas, input units, rounding, and invalid values.
- Business rules must identify when local evidence or policy can override generic doctrine.
- Confidence must be downgraded for missing optional evidence, low-quality evidence, stale evidence, or risky assumptions.
- Failure conditions must be explicit and deterministic where possible.

## 11. Response Contract

Skills may provide response templates, but Response Generation owns final wording and Response Authority owns response mode.

Skill output must be structured and non-final. It should suggest:

```yaml
summary: ""
analysis_points: []
business_implication: ""
next_best_action: ""
caveats: []
follow_up_question: null
```

Rules:

- The skill must not generate final user-facing answer text directly.
- The skill must not expose raw internal diagnostics to normal users.
- The skill may suggest domain-specific answer structure.
- The skill may suggest caveats, assumptions, and confidence notes.
- Response Generation may accept, revise, omit, or reframe skill structure according to the final response contract.

## 12. Follow-up Policy

Follow-up behavior must preserve SME Brain's smallest-question standard.

Rules:

- Ask only the smallest next question.
- Do not ask if sufficient evidence exists.
- Do not ask broad intake forms.
- Do not force workflow unless Response Authority permits.
- Do not continue a completed workflow unless explicitly re-entered.
- Do not ask again for information already provided in the current turn or valid active context.
- Prefer useful partial output with disclosed assumptions when risk is acceptable and the skill allows assumptions.
- Escalate missing evidence to Evidence Gap diagnostics rather than privately managing question loops.

## 13. Tool and Integration Policy

Skills may declare tool requirements, including:

- `calculator`;
- `OCR / document extraction`;
- `inventory database`;
- `sales data`;
- `customer data`;
- `accounting export`;
- `external API`;
- `LPR / parking hardware` for future verticals.

Tool rules:

- Skills must not directly call tools unless runtime explicitly supports it.
- Tool declarations describe capability needs, not permissions.
- Tool output is evidence or execution result, not final judgment.
- Tool requirements must identify required inputs, side effects, confirmation needs, and failure modes.
- Sensitive or external tools must require explicit runtime authority before use.

## 14. Memory Policy

Business Skill selection may read memory only through future runtime boundaries that preserve Memory ownership.

Allowed memory use:

- read durable business facts as optional context;
- use confirmed durable facts as evidence when freshness and source rules permit;
- use prior patterns or preferences as low-risk background context;
- surface memory conflicts to Evidence Gap or Truth Status diagnostics.

Not allowed:

- mutating business memory from skill selection;
- treating durable memory as current reality without evidence evaluation;
- overriding current-turn evidence with memory;
- using pre-reset active workflow context as current evidence;
- committing suggested memory updates without Commit Boundary governance.

User confirmation is needed when memory evidence is stale, conflicting, sensitive, high-risk, or would affect a durable record, external action, financial calculation, or owner-facing commitment.

Durable memory differs from active workflow context. Durable memory may provide background evidence subject to freshness and confidence. Active workflow context belongs to a workflow instance and is invalid after reset, release, or completion unless the user explicitly re-enters it.

Reset boundaries clear active skill evidence tied to the old workflow or released turn. They do not delete durable memory, but they prevent old active context from controlling the new turn.

## 15. Skill Selection Contract

Future skill selection should consider:

- user intent;
- Business Situation profile;
- Evidence Gap profile;
- business domain;
- required evidence availability;
- confidence;
- risk;
- active workflow state;
- reset boundary;
- duplicate question history.

Selection rules:

- Skill selection must remain diagnostic-only until explicitly wired.
- Selection must be deterministic for the same inputs.
- Selection must prefer domain-specific skills when evidence and confidence support them.
- Selection must fail closed when required evidence is missing, contradictory, stale, or blocked.
- Selection must not mutate business memory, workflow state, router state, planner state, prompts, or response behavior.
- Selection must not make a skill active merely because the skill exists.
- Selection diagnostics must distinguish selected, candidate, deferred, blocked, and unavailable skills.

## 16. Diagnostics Contract

Stable future diagnostic keys:

- `business_skill_profile`
- `business_skill_selected`
- `business_skill_id`
- `business_skill_name`
- `business_skill_domain`
- `business_skill_category`
- `business_skill_confidence`
- `business_skill_required_evidence`
- `business_skill_missing_evidence`
- `business_skill_optional_evidence`
- `business_skill_reasoning_ready`
- `business_skill_blocked_reason`
- `business_skill_follow_up_question`
- `business_skill_shadow_mode`
- `business_skill_active_status`

Diagnostics are for observability, acceptance guards, and future dashboard display. They must not become behavior gates until a later explicit contract activates them.

## 17. Skill Lifecycle

Business skills should progress through this lifecycle:

| Status | Meaning |
| --- | --- |
| `DRAFT` | Proposed skill exists but contract is incomplete. |
| `CONTRACTED` | Schema, evidence, reasoning, response, risk, and diagnostics contract are defined. |
| `UNIT_TESTED` | Pure helper or validator tests cover contract behavior. |
| `SHADOW_AVAILABLE` | Skill can be selected or evaluated in diagnostics without user-visible behavior changes. |
| `ACCEPTANCE_GUARDED` | Acceptance guards prove boundaries and non-regression behavior. |
| `RUNTIME_AUDITED` | Runtime audit confirms shadow behavior, failure handling, and no unauthorized effects. |
| `LIMITED_ACTIVE` | Narrow active use is enabled under explicit gate, rollback, and acceptance coverage. |
| `STABLE` | Skill is production-ready within defined scope and monitored boundaries. |

V5.15.0 creates the schema contract only. New skills should begin no higher than `CONTRACTED` unless later versions add tests, shadow wiring, guards, and audit.

## 18. Invariants

- Skill schema must be deterministic.
- Skill selection must not mutate business memory.
- Skill must not override Response Authority.
- Skill must not override Evidence Gap.
- Skill must not override Business Situation.
- Skill must not start workflows by itself.
- Skill must not generate final answer text directly.
- Skill must not expose internal diagnostics to normal users.
- Skill must fail closed when evidence is insufficient or contradictory.
- Skill must distinguish durable memory from active workflow context.
- Skill must not use stale completed workflow context after reset.
- Skill must not call tools unless runtime explicitly authorizes tool execution.
- Skill must remain contract-only or shadow/read-only until a later explicit gate enables behavior.

## 19. Failure Modes

Known failure modes this contract is intended to prevent:

- generic skill selected when domain-specific skill is needed;
- skill asks duplicate questions;
- skill uses stale workflow context after reset;
- skill generates advice without evidence;
- skill silently assumes missing numbers;
- skill conflicts with workflow ownership;
- skill produces final text too early;
- skill becomes active before acceptance guards;
- skill knowledge becomes outdated or untested;
- skill treats durable memory as current truth;
- skill routes around Evidence Gap or Response Authority;
- skill tool requirement becomes unauthorized tool execution.

## 20. Initial Skill Roadmap

Initial candidate skills are documentation targets only. V5.15.0 does not implement them.

| Candidate Skill | Domain | Category |
| --- | --- | --- |
| Cost per unit calculation | Cost | Calculation Skill |
| Cost change analysis | Cost | Diagnostic Skill |
| Price suggestion basics | Pricing | Decision Support Skill |
| Gross margin explanation | Profitability | Explanation Skill |
| Break-even basics | Profitability | Calculation Skill |
| Inventory low-stock explanation | Inventory | Explanation Skill |
| Sales trend explanation | Sales | Reporting Skill |
| Customer complaint triage | Customer | Diagnostic Skill |
| Cashflow warning explanation | Cashflow | Diagnostic Skill |
| Supplier reliability check | Supplier | Comparison Skill |
| Daily shop summary | Dashboard / Reporting | Reporting Skill |
| Promotion idea framing | Marketing | Planning Skill |
| Product profitability explanation | Profitability | Explanation Skill |
| Simple purchase planning | Purchasing | Planning Skill |
| Staff task checklist | HR / Staff | Checklist Skill |
| Document/OCR extraction review | Documents | Data Capture Skill |
| Business dashboard explanation | Dashboard / Reporting | Explanation Skill |
| Workflow status explanation | Workflow Engine | Workflow Support Skill |
| Business memory lookup explanation | Business Knowledge | Explanation Skill |
| Owner decision briefing | Executive Intelligence | Decision Support Skill |

Each candidate must later receive its own evidence schema, reasoning contract, response contract, diagnostics contract, tests, guards, and audit before activation.

## 21. V5.15 Roadmap

### V5.15.0

Business Skill Schema / Business Knowledge contract.

### V5.15.1

Pure `BusinessSkill` model/helper and tests.

### V5.15.2

Skill registry contract and seed skill metadata.

### V5.15.3

Skill selection shadow helper.

### V5.15.4

Skill diagnostics dashboard integration.

### V5.15.5

Acceptance guards.

### V5.15.6

Runtime audit.

## 22. Recommended Next Step

After V5.15.0, implement a pure `BusinessSkill` schema helper.

Do not implement real vertical workflows yet.

Do not activate skill selection yet.

Do not change final response behavior, UI behavior, router behavior, planner behavior, workflow behavior, prompts, or active gates.

The next implementation should prove that skill definitions can be represented, validated, and inspected as pure data before any runtime skill selection or business vertical behavior is introduced.
