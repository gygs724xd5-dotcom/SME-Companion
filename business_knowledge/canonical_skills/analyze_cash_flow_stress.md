---
skill_id: analyze_cash_flow_stress
display_name: Analyze Cash Flow Stress
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - CASH_CONVERSION
    secondary:
      - PROFITABILITY_STRUCTURE
  metrics:
    input:
      - receivable_days
    derived: []
    context:
      - cash_balance
      - accounts_receivable
      - accounts_payable
      - inventory_value
  relationship_rules:
    - payment_timing_affects_liquidity
  evidence:
    required:
      - receivable_days
    optional:
      - cash_balance
      - accounts_receivable
      - accounts_payable
      - inventory_value
  supported_frames:
    - CASH_FLOW_STRESS
  supported_intents:
    - analyze_cash_flow_stress
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

# Analyze Cash Flow Stress

## Purpose
Prepare cash conversion analysis by checking when sales become cash.

## Misuse Constraints
Do not claim cash is trapped in receivables, diagnose losses, or recommend borrowing.
