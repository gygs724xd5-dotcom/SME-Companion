---
skill_id: evaluate_sales_funnel
display_name: Evaluate Sales Funnel
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: sales
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - SALES_FUNNEL
    secondary:
      - CUSTOMER_RETENTION
  metrics:
    input:
      - analysis_timeframe
      - traffic_count
      - inquiry_count
      - conversion_rate
    derived: []
    context:
      - order_count
      - average_order_value
      - repeat_purchase_rate
  relationship_rules:
    - sales_decline_can_be_traffic_or_conversion
  evidence:
    required:
      - analysis_timeframe
    conditionally_required:
      - traffic_count
      - conversion_rate
  supported_frames:
    - SALES_DECLINE
    - DEMAND_WEAKNESS
    - GROWTH_OPPORTUNITY
  supported_intents:
    - evaluate_sales_funnel
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
  reviewed_version: 5.9.3
---

# Evaluate Sales Funnel

## Purpose
Prepare funnel evidence by checking traffic and conversion separately.
