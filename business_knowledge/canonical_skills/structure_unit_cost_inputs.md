---
skill_id: structure_unit_cost_inputs
display_name: Structure Unit Cost Inputs
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: finance
procedural_role: EVIDENCE_COLLECTION
stage: EVIDENCE_STRUCTURING
canonical_references:
  knowledge:
    primary:
      - UNIT_ECONOMICS
    secondary:
      - PROFITABILITY_STRUCTURE
  metrics:
    input:
      - unit_cost
    derived: []
    context:
      - selling_price
  relationship_rules:
    - contribution_margin_needs_realized_price_and_variable_cost
  evidence:
    required:
      - unit_cost
    optional:
      - selling_price
  supported_intents:
    - structure_unit_cost_inputs
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
  reviewed_version: 5.9.3
---

# Structure Unit Cost Inputs

## Purpose
Prepare unit-cost evidence without deciding price, margin, or profitability action.
