---
skill_id: analyze_operating_capacity
display_name: Analyze Operating Capacity
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: operations
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - OPERATING_CAPACITY
    secondary:
      - ORDER_FULFILLMENT
      - PROCESS_FLOW
  metrics:
    input:
      - output_quantity
      - output_time_period
      - current_order_volume
    derived:
      - utilization_rate
    context:
      - business_model
      - backlog_count
  relationship_rules:
    - capacity_requires_time_unit
  evidence:
    required:
      - output_quantity
      - output_time_period
    conditionally_required:
      - current_order_volume
    optional:
      - production_hours
      - staffing_level
      - backlog_count
  supported_frames:
    - CAPACITY_CONSTRAINT
    - DEMAND_SURGE
    - OPERATIONAL_BOTTLENECK
  supported_intents:
    - analyze_operating_capacity
    - assess_capacity_readiness
applicability:
  any:
    - field: business_model
      operator: in
      values:
        - made_to_order
        - production
        - hybrid
    - field: output_quantity
      operator: exists
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
    - workflow_execution
    - business_memory_mutation
compatibility:
  mode: strict_canonical
review:
  status: approved
  reviewed_version: 5.9.1
---

# Analyze Operating Capacity

## Purpose
Prepare operating-capacity analysis by checking whether output has both quantity and time period.

## Procedure
Confirm output quantity, output time period, and only then current demand or order volume.

## Misuse Constraints
Do not diagnose insufficient capacity. Do not recommend hiring, expansion, or equipment.
