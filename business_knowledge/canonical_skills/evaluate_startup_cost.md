---
skill_id: evaluate_startup_cost
display_name: Evaluate Startup Cost
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: startup
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - STARTUP_COST_STRUCTURE
    secondary:
      - UNIT_ECONOMICS
      - ORDER_FULFILLMENT
  metrics:
    input:
      - business_model
      - location_model
      - starting_scale
    derived: []
    context:
      - product_category
      - sales_channel
  relationship_rules:
    - business_model_changes_startup_cost
  evidence:
    required:
      - business_model
      - location_model
    conditionally_required:
      - starting_scale
  supported_intents:
    - evaluate_startup_cost
    - estimate_startup_requirements
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

# Evaluate Startup Cost

## Purpose
Prepare startup-cost evidence by identifying business model and location model first.

## Misuse Constraints
Do not invent budget, recommend loans, or assume a storefront.
