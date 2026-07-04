---
skill_id: compare_revenue_and_profit
display_name: Compare Revenue and Profit
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: COMPARISON
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - PROFITABILITY_STRUCTURE
    secondary:
      - UNIT_ECONOMICS
  metrics:
    input:
      - analysis_timeframe
      - total_revenue
      - net_profit
    derived: []
    context:
      - average_order_value
  relationship_rules:
    - profit_comparisons_require_compatible_timeframes
  evidence:
    required:
      - analysis_timeframe
      - total_revenue
      - net_profit
  supported_frames:
    - PROFIT_COMPRESSION
  supported_intents:
    - compare_revenue_and_profit
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

# Compare Revenue and Profit

## Purpose
Prepare period-compatible revenue and profit comparison.
