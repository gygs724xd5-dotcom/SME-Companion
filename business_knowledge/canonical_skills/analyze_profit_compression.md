---
skill_id: analyze_profit_compression
display_name: Analyze Profit Compression
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - PROFITABILITY_STRUCTURE
      - UNIT_ECONOMICS
    secondary:
      - PRICING_POSITION
      - CASH_CONVERSION
  metrics:
    input:
      - analysis_timeframe
      - total_revenue
      - net_profit
    derived:
      - gross_margin
    context:
      - average_order_value
      - unit_cost
      - discount_rate
      - channel_fee_rate
  relationship_rules:
    - profit_comparisons_require_compatible_timeframes
    - revenue_growth_not_guaranteed_by_profit_growth
  evidence:
    required:
      - analysis_timeframe
      - total_revenue
      - net_profit
    optional:
      - average_order_value
      - unit_cost
      - discount_rate
      - channel_fee_rate
  supported_frames:
    - PROFIT_COMPRESSION
  supported_intents:
    - analyze_profit_compression
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

# Analyze Profit Compression

## Purpose
Prepare comparison of revenue and profit movement across compatible periods.

## Misuse Constraints
Do not claim costs, discounts, channels, or waste caused the decline without later Judgment authority.
