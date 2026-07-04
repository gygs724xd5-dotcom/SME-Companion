---
skill_id: plan_order_fulfillment
display_name: Plan Order Fulfillment
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: operations
procedural_role: PLANNING_SUPPORT
stage: PLANNING_SUPPORT
canonical_references:
  knowledge:
    primary:
      - ORDER_FULFILLMENT
    secondary:
      - OPERATING_CAPACITY
      - PROCESS_FLOW
  metrics:
    input:
      - order_volume
      - fulfillment_time
    derived: []
    context:
      - business_model
      - current_order_volume
      - backlog_count
  relationship_rules:
    - made_to_order_connects_demand_to_capacity
  evidence:
    required:
      - order_volume
      - fulfillment_time
  supported_frames:
    - DEMAND_SURGE
    - OPERATIONAL_BOTTLENECK
    - CAPACITY_CONSTRAINT
  supported_intents:
    - plan_order_fulfillment
applicability:
  any:
    - field: business_model
      operator: in
      values:
        - made_to_order
        - hybrid
readiness:
  required_evidence_policy: all
  conflict_policy: block
  stale_policy: partial
  missing_optional_policy: allow
authority:
  allowed:
    - procedural_analysis
    - evidence_sequence
    - clarification_support
  forbidden:
    - root_cause_diagnosis
    - final_judgment
    - final_decision
    - planner_invocation
    - workflow_execution
    - business_memory_mutation
compatibility:
  mode: strict_canonical
review:
  status: approved
  reviewed_version: 5.9.1
---

# Plan Order Fulfillment

## Purpose
Prepare downstream fulfillment planning context only.

## Misuse Constraints
In V5.9.1 this skill is deferred and must not invoke Planner or Workflow.
