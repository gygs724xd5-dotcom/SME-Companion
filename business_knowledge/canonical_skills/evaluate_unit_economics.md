---
skill_id: evaluate_unit_economics
display_name: Evaluate Unit Economics
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - UNIT_ECONOMICS
    secondary:
      - PRICING_POSITION
      - PROFITABILITY_STRUCTURE
  metrics:
    input:
      - selling_price
      - unit_cost
    derived:
      - contribution_margin
    context:
      - discount_rate
      - channel_fee_rate
      - fulfillment_cost
  relationship_rules:
    - contribution_margin_needs_realized_price_and_variable_cost
  evidence:
    required:
      - selling_price
      - unit_cost
    optional:
      - discount_rate
      - channel_fee_rate
      - fulfillment_cost
  supported_frames:
    - PROFIT_COMPRESSION
    - PRICING_PRESSURE
    - GROWTH_OPPORTUNITY
  supported_intents:
    - evaluate_unit_economics
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

# Evaluate Unit Economics

## Purpose
Prepare per-unit economics from selling price and unit cost.
