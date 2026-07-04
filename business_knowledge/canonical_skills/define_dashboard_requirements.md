---
skill_id: define_dashboard_requirements
display_name: Define Dashboard Requirements
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: reporting
procedural_role: PLANNING_SUPPORT
stage: PLANNING_SUPPORT
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
    derived: []
    context:
      - total_revenue
      - order_count
      - current_stock
  relationship_rules:
    - orders_and_revenue_can_diverge_by_aov
  evidence:
    required:
      - analysis_timeframe
    optional:
      - total_revenue
      - order_count
      - current_stock
  supported_intents:
    - define_dashboard_requirements
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

# Define Dashboard Requirements

## Purpose
Prepare downstream dashboard requirements only. This Skill is deferred in V5.9.3 and does not build dashboards.
