---
skill_id: analyze_inventory_risk
display_name: Analyze Inventory Risk
skill_version: 1.0.0
schema_version: 5.9.1
status: active
domain: inventory
procedural_role: ANALYSIS_PREPARATION
stage: ANALYSIS_PREPARATION
canonical_references:
  knowledge:
    primary:
      - INVENTORY_HEALTH
    secondary:
      - SUPPLY_RELIABILITY
  metrics:
    input:
      - current_stock
      - average_daily_sales
      - current_order_volume
    derived:
      - days_of_stock
    context:
      - supplier_lead_time
      - shelf_life
      - inventory_age
  relationship_rules:
    - stock_quantity_needs_velocity
  evidence:
    required:
      - current_stock
    conditionally_required:
      - average_daily_sales
      - current_order_volume
    optional:
      - supplier_lead_time
      - shelf_life
      - inventory_age
  supported_frames:
    - INVENTORY_RISK
  supported_intents:
    - analyze_inventory_risk
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

# Analyze Inventory Risk

## Purpose
Prepare inventory-risk analysis by pairing current stock with demand or sales velocity.

## Misuse Constraints
Do not recommend reordering or label stock sufficient or insufficient without velocity.
