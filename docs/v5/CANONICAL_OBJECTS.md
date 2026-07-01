# V5 Canonical Objects

## Purpose

This document defines the canonical data objects used across SME Companion V5. These objects establish clear boundaries between engines and prevent hidden state ownership.

As of V5.1.1, lightweight runtime dataclasses exist in `brain/canonical_objects.py` as foundation contracts. They are intentionally additive and coexist with the existing V4 dict-based runtime. Routing, planner, workflow, and response behavior should not be migrated to these objects until a later explicit runtime migration.

## Object Rules

- Every canonical object has one owner.
- Required fields must be present for the object to be valid.
- Optional fields may be omitted but must not be used as hidden required state.
- Lifecycle should be explicit.
- Consumers may read objects but must not mutate fields owned by another engine.
- Derived objects must preserve provenance to their source.

## ConversationFrame

### Purpose

Represents the interpreted user turn before business execution.

### Owner

Conversation Intelligence.

### Required Fields

- `turn_id`
- `user_message`
- `normalized_message`
- `conversation_act`
- `store_id`
- `timestamp`
- `active_workflow_hint`
- `resolved_references`
- `candidate_entities`
- `ambiguity_flags`
- `diagnostics`

### Optional Fields

- `uploaded_files`
- `ui_surface`
- `prior_turn_reference`
- `interruption_signal`
- `correction_target`
- `confirmation_target`
- `language`
- `user_role`

### Lifecycle

Created at the start of a turn by Conversation Intelligence. Read by downstream engines during the turn. May be summarized into Conversation Memory after the response is finalized.

### Consumers

- Business Knowledge.
- Business Reasoning.
- Planner.
- Workflow.
- Memory.
- Transformation.
- Response Intelligence.
- LLM Adapter.

## KnowledgeContext

### Purpose

Represents the business knowledge selected for the turn.

### Owner

Business Knowledge.

### Required Fields

- `knowledge_context_id`
- `conversation_frame_id`
- `candidate_domains`
- `candidate_skills`
- `selected_domain_hint`
- `required_entities`
- `required_memory`
- `business_rules`
- `reasoning_patterns`
- `response_guidance`
- `diagnostics`

### Optional Fields

- `workflow_links`
- `tool_requirements`
- `examples`
- `domain_vocabulary`
- `reject_reasons`
- `knowledge_gaps`
- `version`

### Lifecycle

Created after Conversation Intelligence frames the turn. Refined by Business Knowledge during domain and skill selection. Read by Reasoning, Planner, Workflow, Transformation, Response Intelligence, and LLM Adapter.

### Consumers

- Business Reasoning.
- Planner.
- Workflow.
- Transformation.
- Response Intelligence.
- LLM Adapter.

## ReasoningDecision

### Purpose

Represents the explainable business interpretation and recommendation for the turn.

### Owner

Business Reasoning.

### Required Fields

- `reasoning_decision_id`
- `conversation_frame_id`
- `knowledge_context_id`
- `business_goal`
- `decision_type`
- `selected_domain`
- `selected_skill_id`
- `known_facts`
- `missing_facts`
- `assumptions`
- `recommended_action`
- `confidence`
- `diagnostics`

### Optional Fields

- `risk`
- `opportunity`
- `business_stage`
- `rule_applications`
- `rejected_actions`
- `memory_requirements`
- `workflow_recommendation`
- `tool_recommendation`
- `response_mode`

### Lifecycle

Created after knowledge selection and memory retrieval are available. Used by Planner to choose the execution path. Included in diagnostics and response guidance.

### Consumers

- Planner.
- Workflow.
- Memory.
- Transformation.
- Response Intelligence.
- LLM Adapter.

## PlannerDecision

### Purpose

Represents the execution plan for the current turn.

### Owner

Planner.

### Required Fields

- `planner_decision_id`
- `conversation_frame_id`
- `reasoning_decision_id`
- `primary_action`
- `primary_engine_path`
- `fallback_path`
- `workflow_action`
- `memory_actions`
- `llm_action`
- `response_expectation`
- `confidence`
- `diagnostics`

### Optional Fields

- `tool_actions`
- `transformation_action`
- `compatibility_path`
- `guard_action`
- `interruption_handling`
- `execution_constraints`
- `deferred_actions`

### Lifecycle

Created after Business Reasoning. Consumed by execution engines during the turn. Reflected in the Response Envelope diagnostics.

### Consumers

- Workflow.
- Memory.
- Transformation.
- LLM Adapter.
- Response Intelligence.
- Developer diagnostics.

## WorkflowState

### Purpose

Represents active or historical workflow process state.

### Owner

Workflow.

### Required Fields

- `workflow_id`
- `workflow_instance_id`
- `owner_domain`
- `owner_skill_id`
- `status`
- `required_fields`
- `collected_fields`
- `missing_fields`
- `last_transition`
- `next_required_action`
- `created_at`
- `updated_at`
- `diagnostics`

### Optional Fields

- `paused_reason`
- `interruption_context`
- `validation_errors`
- `completion_result`
- `completion_memory_proposals`
- `chained_workflow_id`
- `cancel_reason`
- `failure_reason`
- `history`

### Lifecycle

Created when a workflow starts. Updated only by Workflow through explicit transitions. Persisted through Workflow Memory. Completed, cancelled, failed, or chained when process ownership ends or moves.

### Consumers

- Conversation Intelligence.
- Business Reasoning.
- Planner.
- Memory.
- Transformation.
- Response Intelligence.

## BusinessSkill

### Purpose

Represents a canonical business capability used for routing, reasoning, workflow selection, and response guidance.

### Owner

Business Knowledge.

### Required Fields

- `skill_id`
- `skill_name`
- `domain`
- `intent`
- `description`
- `required_entities`
- `required_memory`
- `business_rules`
- `reasoning`
- `response_style`
- `diagnostics`
- `confidence`

### Optional Fields

- `example_questions`
- `workflow`
- `follow_up`
- `tools`
- `future_extensions`
- `related_skills`
- `version`
- `status`

### Lifecycle

Defined in the skill registry. Loaded by Business Knowledge when relevant. Referenced by Reasoning, Planner, Workflow, Transformation, and Response Intelligence. Versioned when the skill definition changes.

### Consumers

- Business Knowledge.
- Business Reasoning.
- Planner.
- Workflow.
- Transformation.
- Response Intelligence.
- Developer diagnostics.

## BusinessMemoryItem

### Purpose

Represents a durable or semi-durable business fact, event, preference, decision, or completed workflow summary.

### Owner

Memory.

### Required Fields

- `memory_id`
- `store_id`
- `memory_type`
- `owner`
- `subject`
- `content`
- `source`
- `confidence`
- `created_at`
- `updated_at`
- `freshness`
- `provenance`

### Optional Fields

- `expires_at`
- `related_domain`
- `related_skill_id`
- `related_workflow_id`
- `entities`
- `tags`
- `supersedes`
- `superseded_by`
- `confirmation_status`
- `diagnostics`

### Lifecycle

Created from explicit user input, approved workflow completion, transformation output, or high-confidence business event. Retrieved when relevant. Updated, confirmed, expired, downgraded, or superseded by Memory according to ownership and freshness rules.

### Consumers

- Conversation Intelligence.
- Business Knowledge.
- Business Reasoning.
- Planner.
- Workflow.
- Transformation.
- Response Intelligence.

## TransformationResult

### Purpose

Represents structured output derived from raw user input, files, images, documents, LLM assistance, or workflow data.

### Owner

Transformation.

### Required Fields

- `transformation_id`
- `source_reference`
- `target_schema`
- `result_type`
- `structured_output`
- `validation_status`
- `confidence`
- `provenance`
- `created_at`
- `diagnostics`

### Optional Fields

- `raw_extraction`
- `normalized_entities`
- `correction_required`
- `validation_errors`
- `llm_assisted`
- `workflow_instance_id`
- `memory_write_proposals`
- `rendering_hints`
- `version`

### Lifecycle

Created when the Planner requests transformation or a workflow requires structured output. May be corrected by user input, validated against a target schema, persisted in Transformation Memory, and presented through Response Intelligence.

### Consumers

- Workflow.
- Memory.
- Response Intelligence.
- Planner.
- LLM Adapter.
- Developer diagnostics.

## ResponseEnvelope

### Purpose

Represents the single final response package for one user turn.

### Owner

Response Intelligence.

### Required Fields

- `response_id`
- `turn_id`
- `text`
- `source`
- `domain`
- `skill_id`
- `confidence`
- `created_at`
- `diagnostics`

### Optional Fields

- `workflow`
- `memory`
- `reasoning_summary`
- `follow_up`
- `assumptions`
- `rendering_hints`
- `fallback_used`
- `transformation_result_id`
- `llm_diagnostics`
- `developer_trace`

### Lifecycle

Created after all required engines have contributed to the turn. Rendered by the UI. May be summarized into Conversation Memory and may trigger approved memory writes. It is the final owner-facing response for the turn.

### Consumers

- UI rendering layer.
- Conversation Memory.
- Business Memory when approved.
- Developer diagnostics.
