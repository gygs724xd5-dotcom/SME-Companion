# V5 Developer Guide

## Purpose

This guide describes how future developers should extend SME Companion V5 without breaking the architecture. It is documentation-only and does not require runtime changes by itself.

## Add a New Domain

1. Assign the next stable domain ID.
2. Define domain responsibility and boundaries.
3. List related domains.
4. Add at least five candidate skills.
5. Define common entities and memory needs.
6. Define domain-level business rules.
7. Add routing diagnostics expectations.

A domain should own a clear business area. Avoid creating domains for implementation details.

## Add a New Skill

1. Use the canonical Business Skill Standard.
2. Assign a stable skill ID.
3. Choose one owning domain.
4. Define intent, examples, required entities, and required memory.
5. Add business rules and reasoning pattern.
6. Define workflow integration.
7. Define response style and follow-up behavior.
8. Add confidence and diagnostics rules.

Do not add a skill that only contains a response template. A skill must support reasoning and routing.

## Add a New Workflow

1. Define the workflow business outcome.
2. Identify owning domain and skills.
3. Define required fields.
4. Define lifecycle states.
5. Define start, continue, pause, resume, cancel, complete, and chain behavior.
6. Define validation rules.
7. Define memory reads and writes.
8. Define response requirements for each state.

Workflows should expose state and next action. Response wording belongs to Response Intelligence.

## Add a New Reasoning Rule

1. Identify the business decision the rule supports.
2. Define the domain and skills affected.
3. List inputs required.
4. Define the decision logic in business terms.
5. Define confidence conditions.
6. Define fallback when data is missing.
7. Add diagnostics explaining when the rule fired.

Reasoning rules should not be keyword-only. Keywords may be signals, but the rule must consider context.

## Planner Adapter and Migration

V5.1.4 adds `PlannerContext` as a bridge from V5 runtime objects into the existing V4 planner surface. It is an adapter foundation only.

When extending this layer:

1. Package context only; do not execute planner logic.
2. Keep existing V4 planner output as the source of truth.
3. Attach `PlannerContext` to developer diagnostics only.
4. Preserve routing, workflow, response, and Conversation OS behavior.
5. Use diagnostics such as `planner_context_created`, `planner_context_version`, `planner_context_source`, `planner_selected_domain`, `planner_selected_skill`, `planner_business_goal`, `planner_confidence`, and `planner_context_present`.

V5.2.0 Phase 1 begins the runtime planner migration. The migration layer may now read existing V5 context objects before invoking the legacy planner:

1. Prefer `KnowledgeContext`.
2. Fall back to `ReasoningContext`.
3. Fall back to `PlannerContext`.
4. Use the existing V4 planner logic when V5 context is missing, incomplete, or unmapped.

The migration layer must keep returning the legacy route object expected by downstream code. It may normalize planner inputs and expose migration diagnostics, but it must not change response wording, workflow behavior, UI behavior, Conversation OS behavior, memory behavior, or transformation behavior.

Use planner migration diagnostics such as `planner_runtime_source`, `planner_runtime_version`, `planner_used_v5_context`, `planner_used_legacy_fallback`, `planner_selected_domain`, `planner_selected_skill`, `planner_business_goal`, `planner_decision_type`, `planner_confidence`, and `planner_reason`.

## Add New Memory

1. Identify the memory type.
2. Define the owner.
3. Define what facts are stored.
4. Define source and confidence metadata.
5. Define freshness and expiry rules.
6. Define read priority.
7. Define write conditions.
8. Define conflict resolution behavior.

Do not store a fact in multiple memory types unless one is derived and clearly marked.

## Add a New Transformation

1. Define source input.
2. Define target output schema.
3. Define required entities.
4. Define validation rules.
5. Define correction flow.
6. Define memory write behavior.
7. Define whether LLM assistance is allowed.
8. Define response presentation style.

Transformation should preserve source provenance and confidence.

## Architecture Safety Rules

- Do not let UI rendering own business decisions.
- Do not let LLM output bypass workflow, memory, or response priority.
- Do not write permanent memory from low-confidence inference.
- Do not duplicate workflow state across owners.
- Do not add domain behavior as scattered conditionals when a skill or workflow should own it.
- Do not create hidden response paths outside the response envelope concept.
- Do not break V4 compatibility while migrating toward V5.

## Review Checklist

Before accepting future V5 architecture work, verify:

- Domain ownership is clear.
- Skill schema is complete.
- Workflow state has one owner.
- Memory reads and writes are explicit.
- Reasoning is explainable.
- Response source is auditable.
- Fallback behavior is useful.
- Diagnostics are available.
