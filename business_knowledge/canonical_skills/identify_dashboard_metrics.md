---
skill_id: identify_dashboard_metrics
display_name: Identify Dashboard Metrics
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: reporting
procedural_role: EVIDENCE_COLLECTION
stage: EVIDENCE_STRUCTURING
canonical_references:
  knowledge:
    primary:
      - SALES_FUNNEL
    secondary:
      - PROFITABILITY_STRUCTURE
      - INVENTORY_HEALTH
  metrics:
    input:
      - analysis_timeframe
      - total_revenue
      - order_count
      - gross_margin
      - current_stock
    derived: []
    context:
      - average_order_value
      - net_profit
  relationship_rules:
    - orders_and_revenue_can_diverge_by_aov
  evidence:
    required:
      - analysis_timeframe
    optional:
      - total_revenue
      - order_count
      - gross_margin
      - current_stock
  supported_intents:
    - identify_dashboard_metrics
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

# Identify Dashboard Metrics

## Purpose
Prepare candidate dashboard metrics without creating a dashboard or invoking tools.
