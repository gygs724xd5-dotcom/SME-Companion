---
skill_id: analyze_sales_decline
display_name: Analyze Sales Decline
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
      - PRICING_POSITION
  metrics:
    input:
      - analysis_timeframe
      - traffic_count
      - conversion_rate
      - order_count
    derived: []
    context:
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
      - order_count
    optional:
      - average_order_value
      - repeat_purchase_rate
  supported_frames:
    - SALES_DECLINE
    - DEMAND_WEAKNESS
  supported_intents:
    - analyze_sales_decline
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

# Analyze Sales Decline

## Purpose
Prepare sales-decline analysis by separating timeframe, traffic, conversion, orders, and repeat purchase evidence.

## Misuse Constraints
Do not recommend campaigns, set targets, build a plan, or name a cause.
