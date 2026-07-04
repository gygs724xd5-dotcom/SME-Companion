---
skill_id: calculate_product_margin
display_name: Calculate Product Margin
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: METRIC_CALCULATION
stage: EVIDENCE_STRUCTURING
canonical_references:
  knowledge:
    primary:
      - UNIT_ECONOMICS
    secondary:
      - PROFITABILITY_STRUCTURE
  metrics:
    input:
      - selling_price
      - unit_cost
    derived:
      - contribution_margin
    context: []
  relationship_rules:
    - contribution_margin_needs_realized_price_and_variable_cost
  evidence:
    required:
      - selling_price
      - unit_cost
  supported_intents:
    - calculate_product_margin
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

# Calculate Product Margin

## Purpose
Prepare product margin calculation inputs without executing workflow formulas.
