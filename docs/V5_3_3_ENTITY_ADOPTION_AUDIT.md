# V5.3.3 Canonical Entity Adoption Audit

Audit date: 2026-07-02

Scope: `brain/`, `app.py`, `tests/`, and `business_knowledge/` integration content.

Doctrine read first: `docs/ARCHITECTURE_DOCTRINE.md`.

Audit mode: documentation only. No production behavior was changed. No Workflow, Reasoning, Response, Planner behavior, Business Memory, or store data migration was performed.

## Executive Summary

Canonical Entity Runtime is present and `brain/task_router.py` now builds `canonical_entities`, but legacy extraction still actively produces and consumes business entity fields in routing, workflow collection, and app-level fallback paths.

Findings: 14

- MUST MIGRATE BEFORE V5.4: 6
- SHOULD MIGRATE: 5
- SAFE legacy compatibility: 3

Layer summary:

- Entity Runtime / legacy entity layer: 2 findings
- Routing / Planner adapter boundary: 1 finding
- Workflow: 5 findings
- Response / app fallback: 2 findings
- Reasoning / business intelligence guards: 2 findings
- Tests: 1 finding
- Business Knowledge: 1 finding

No Business Memory entity extraction or store-data mutation path was found in this audit.

## Migration Priority Map

| Priority | Findings | Migration target |
| --- | ---: | --- |
| HIGH | 6 | Replace active regex/manual entity extraction that writes cost, price, quantity, product, date, or customer fields with `canonical_entities.slots` and grouped canonical entities. |
| MEDIUM | 5 | Replace fallback parsers, numeric evidence checks, and legacy field normalization after HIGH paths are migrated. |
| LOW | 3 | Keep compatibility tests/docs/upload-only receipt flow until callers no longer require legacy shapes. |

## Findings

### MUST MIGRATE BEFORE V5.4

| ID | Layer | File | Function / section | Entity type | Current extraction method | Recommended canonical replacement | Priority | Risk notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-01 | Legacy entity extraction | `brain/business_entity_extractor.py:90` | `_extract_money`, `_extract_unit_cost`, `_extract_labeled_money`, `_normalize_profit_money` | cost, price, selling_price, unit_cost | Regex money parsing and intent-specific relabeling into `prices`, `costs`, `cost`, `unit_cost`, `cost_per_unit`. | Source money fields from `canonical_entities.grouped_entities.money` and `canonical_entities.slots.cost`, `slots.price`, `slots.selling_price`; keep this module only as an adapter if legacy callers still need old keys. | HIGH | This is the largest duplicate of Entity Runtime. It can disagree with canonical role assignment and can continue to make Workflow/Reasoning trust legacy fields. |
| F-02 | Legacy entity extraction | `brain/business_entity_extractor.py:105` | `_extract_quantities`, `_extract_dates`, `_extract_customer_phrases`, `_extract_product_or_service_names` | quantity, date, customer phrase, product | Regex, keyword/date matching, alias lookup, and phrase capture into `quantities`, `dates`, `customer_phrases`, `product_or_service_names`. | Use `canonical_entities.slots.quantity`, `slots.quantity_unit`, `slots.date`, `slots.product`, plus grouped canonical `quantity`, `date`, and `product` entities. Customer phrase should become a canonical customer/entity type before migration or remain explicitly outside canonical entity scope. | HIGH | Product/date/quantity extraction may diverge from Entity Runtime. Customer phrase extraction is not currently represented in canonical slots, so it needs an explicit canonical model decision. |
| F-03 | Routing boundary | `brain/task_router.py:491` | `build_task_route` | all business entities | Calls `extract_business_entities(...)` and independently calls `canonical_entity_payload(...)`; legacy `entity_result` is still propagated to `business_context`, `extracted_entities`, `llm_reasoning_context`, and response gate payloads. | Build canonical entities once, pass them as the authoritative entity payload, and generate any temporary legacy compatibility shape from canonical payload at the boundary. | HIGH | Two entity sources coexist in the central route. Downstream layers can read different values for the same user message. |
| F-04 | Workflow | `brain/workflow_field_extractor.py:33` | `_extract_product`, `_extract_quantity`, `_extract_cost_fields`, `_extract_profit_fields`, `extract_workflow_fields` | product, quantity, daily capacity, cost, selling_price, ingredients_costs | Workflow-level regex and line parsing; manual numeric parsing of ingredient costs, total units, unit cost, and selling price. | Workflow should receive already-extracted canonical slots/grouped entities and only map them to workflow-required fields. Ingredient line items need a canonical line-item representation or an explicit Workflow-only collection model. | HIGH | Direct violation of doctrine once canonical entities are available: Workflow owns execution, not extraction. This path can mark workflows ready from non-canonical parsing. |
| F-05 | Workflow | `brain/workflow_state_machine.py:447` | `update_workflow_state`, `_direct_answer_fields`, `_first_number` | product, business_type, target_customer, promotion, daily_capacity, total_units | Calls `extract_workflow_fields(...)`, then applies direct-answer parsers and `_first_number` to fill missing fields. | Accept canonical entity payload as input to workflow update, map `slots.product` and `slots.quantity` to workflow fields, and keep direct-answer capture only for non-canonical free-text fields. | HIGH | Workflow can still extract product and quantity independently of Entity Runtime during active workflow turns. |
| F-06 | Workflow | `brain/business_workflow_engine.py:556` | `_normalize_workflow_entities`, `_unit_cost_from_message`, `_quantity_from_entities_or_message` | cost, unit_cost, cost_per_unit, quantity, total_units | Workflow normalization reads `entities` but also reparses `user_message` with money/unit and quantity regexes. | Remove message regex fallback once canonical fields are available; map `canonical_entities.slots.cost`, `slots.quantity`, and grouped money/quantity entities into workflow fields before readiness checks. | HIGH | This duplicates canonical extraction inside workflow execution and can synthesize fields not present in Entity Runtime. |

### SHOULD MIGRATE

| ID | Layer | File | Function / section | Entity type | Current extraction method | Recommended canonical replacement | Priority | Risk notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-07 | Workflow compatibility | `brain/business_workflow_engine.py:622` | `_has_entity`, `_entity_aliases`, `_entities_to_fields`, `_canonical_entity` | product, price, cost, quantity, date | Alias-based legacy field detection and conversion from `prices`, `costs`, `quantities`, `dates` into workflow fields. | Keep as temporary adapter, but prefer canonical slots first. Eventually delete aliases that exist only to support `extract_business_entities`. | MEDIUM | Mostly compatibility, but it encourages downstream dependence on legacy shapes. |
| F-08 | App fallback / Response-adjacent | `app.py:2981` | `_parse_cost_inputs`, `_cost_result_reply` | ingredient cost, total cost, quantity, selling_price | App-level line parser with regex numbers and Thai keyword heuristics; immediately produces a response. | Route cost requests through canonical entity payload and Workflow execution. If free-form ingredient lists remain unsupported by Entity Runtime, define the gap instead of keeping a parallel app parser. | MEDIUM | Response/app layer can compute and communicate from its own extraction, bypassing canonical runtime and Workflow. |
| F-09 | App workflow output | `app.py:3196` | `_generate_cost_calculation`, `_numeric_workflow_value`, `_generate_profit_calculation` | cost, price, selling_price, quantity | Numeric coercion over legacy workflow fields and aliases such as `prices`, `costs`, `quantity`, `total_units`. | After workflow migration, consume canonical-derived workflow fields with one canonical field contract; leave numeric coercion only as formatting defense. | MEDIUM | Not primary extraction, but it normalizes legacy entity shapes in the Response/app layer and can hide upstream inconsistencies. |
| F-10 | Reasoning / business intelligence guard | `brain/business_intelligence_bridge.py:126` | `_is_cost_calculation_skill_request` | cost, price, quantity | Uses legacy `entities.get("costs")`, `prices`, `quantities`, raw `re.search(r"\d")`, and unit keyword checks. | Use `canonical_entities.slots.cost`, `slots.price`, `slots.quantity`, and grouped entity counts for evidence. | MEDIUM | Guard logic can infer numeric entity evidence outside Entity Runtime and affect skill matching/Reasoning decisions. |
| F-11 | Planner/intent guard | `brain/cost_intent_isolation.py:9` | `is_strong_cost_calculation_message` | cost, quantity | Regex count of numbers plus cost/unit/quantity patterns. | Use canonical money/quantity entities as supporting context while keeping Planner ownership of intent decisions. If retained, classify as intent evidence, not entity extraction. | MEDIUM | It is intent isolation rather than entity persistence, but it still duplicates cost/quantity parsing patterns and may drift from canonical coverage. |

### SAFE Legacy Compatibility

| ID | Layer | File | Function / section | Entity type | Current extraction method | Recommended canonical replacement | Priority | Risk notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-12 | Receipt workflow | `app.py:3577` | `_receipt_uploaded_reply`, `_handle_receipt_workflow` | receipt/invoice amount | No amount extraction found. Current path acknowledges upload and states OCR/amount extraction is not enabled. | When OCR is introduced, receipt/invoice amount must be emitted through Entity Runtime as canonical money entities before Workflow/Reasoning/Response use it. | LOW | Safe today. Future OCR is a high-risk insertion point if implemented directly in Workflow or Response. |
| F-13 | Tests | `tests/test_business_intent_entity_extraction.py`, `tests/test_v493_workflow_readiness_calculation_audit.py`, `tests/test_active_workflow_routing.py` | Legacy extractor and workflow state tests | cost, price, product, quantity, date | Tests directly assert `extract_business_entities(...)`, `update_workflow_state(...)`, legacy `total_units`, and legacy field extraction behavior. | During migration, convert these into canonical adapter compatibility tests or replace with canonical entity tests plus workflow mapping tests. | LOW | Safe as regression coverage now, but they will block removal of legacy extraction until updated. |
| F-14 | Business Knowledge content | `business_knowledge/skills/**`, `business_knowledge/templates/**` | Markdown examples and skill instructions | price, quantity, customer, date, amount | Static examples and guidance mention price, quantity, dates, customers, deposits, and totals. No executable extraction found. | No migration needed unless a loader begins parsing entity values from skill examples. | LOW | Safe. Keep Business Knowledge as knowledge only; do not allow it to become an extraction layer. |

## Non-Findings

- `brain/entity_runtime.py` is the canonical owner and is not a legacy finding.
- `brain/planner_adapter.py` carries canonical entities as supporting context and does not extract entities.
- `brain/workflow_state_machine.py` readiness checks and `brain/workflow_readiness.py` alias checks are not extraction by themselves, but they depend on legacy field names and should be cleaned up after high-priority migrations.
- `business_knowledge/` contains entity-like examples but no executable parser in this audit scope.
- No Business Memory write path was found that extracts or stores cost, price, quantity, product, date, customer, supplier, or receipt/invoice amount.

## Recommended Migration Sequence

1. Add a canonical-to-legacy compatibility adapter at the routing boundary so existing callers can receive legacy keys derived from `canonical_entities`.
2. Replace `brain/task_router.py` direct `extract_business_entities(...)` usage with canonical payload plus the compatibility adapter.
3. Migrate Workflow field collection to accept canonical payload and remove message regex fallbacks in `brain/workflow_field_extractor.py`, `brain/workflow_state_machine.py`, and `brain/business_workflow_engine.py`.
4. Move app-level cost fallback handling behind Workflow or retire it after Workflow canonical migration.
5. Update Reasoning/business intelligence guards to use canonical entity evidence.
6. Update tests from legacy extractor assertions to canonical runtime and canonical-to-workflow mapping assertions.

## Remaining Risks

- Ingredient-level cost lines are richer than the current simple canonical money slots. Migration needs either grouped money entities with raw spans or a canonical line-item model.
- Customer phrase extraction is not clearly covered by canonical entity slots. Decide whether customer utterance is a canonical entity, conversation-understanding evidence, or a skill-specific input.
- Receipt/invoice amount extraction is not implemented, but future OCR could easily bypass Entity Runtime if not guarded.
- Legacy aliases (`prices`, `costs`, `quantities`, `total_units`) are widespread. Removing them before an adapter exists would create workflow readiness regressions.
- Some files show mojibake Thai string literals in PowerShell output; audit classification used code structure and Unicode escape patterns where present, not display rendering.

## Verification

Required commands for this audit:

```powershell
python -m py_compile app.py
python -m unittest discover -s tests
```

Actual result:

- `python -m py_compile app.py`: passed.
- `python -m unittest discover -s tests`: passed, 227 tests in 2.910s. Streamlit emitted bare-mode `ScriptRunContext` warnings during tests; no failures or errors.
