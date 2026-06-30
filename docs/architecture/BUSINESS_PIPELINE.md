# Business Pipeline

This document maps the business pipeline that enriches one user message before final response generation.

## Pipeline

```text
user_message
  |
  v
detect_business_intent()
  |
  v
extract_business_entities()
  |
  v
decide_business_workflow()
  |
  v
understand_conversation()
  |
  v
get_last_context() / remember_turn()
  |
  v
build_business_context()
  |
  v
resolve_intent()
  |
  v
build_execution_plan()
  |
  v
run_business_intelligence_bridge()
  |
  v
rank_business_skills()
  |
  v
reason_business_message()
  |
  v
build_reasoning()
  |
  v
build_reasoning_context()
  |
  v
decide_llm_usage()
  |
  v
build_prompt_context() if LLM is needed
```

## Intent

| File | Function | Output |
| --- | --- | --- |
| `brain/business_intent_engine.py` | `detect_business_intent()` | `detected_intent`, `intent_confidence`, `matched_intent_keywords` |
| `brain/conversation_understanding_engine.py` | `understand_conversation()` | `detected_intent`, `legacy_intent`, `planner_message`, references, clarification flag |
| `brain/intent_resolver.py` | `resolve_intent()` | resolved intent/workflow and planner message |

Business intent detects broad business meaning. Conversation understanding normalizes app-level intent and references. Intent resolver reconciles interpretation, memory, and business context for planning.

## Entity

| File | Function | Output |
| --- | --- | --- |
| `brain/business_entity_extractor.py` | `extract_business_entities()` | product/service names, prices, costs, quantities, dates, customer phrases, business type hints, missing entities |

Entity extraction is current-message oriented. It does not write the response. It influences workflow completeness, prompt context, and skill matching.

## Workflow

| File | Function | Output |
| --- | --- | --- |
| `brain/business_workflow_engine.py` | `decide_business_workflow()` | workflow action, stage, progress, missing entities, next question |
| `brain/conversation_manager.py` | `continue_workflow()` | Conversation OS event and workflow state |
| `brain/workflow_state_machine.py` | `update_workflow_state()` | V2 workflow state and extracted fields |
| `brain/workflow_reply_builder.py` | `build_workflow_reply()` | natural workflow prompt/result metadata |

Workflow logic exists in three layers:

- Conversation OS controls lifecycle and planner lock.
- Business workflow intelligence decides whether the message should start, continue, interrupt, complete, cancel, or resume.
- V2 state machine collects required fields and generates workflow-ready state.

## Skill

| File | Function | Output |
| --- | --- | --- |
| `brain/business_skill_loader.py` | `load_all_business_skills()`, `search_business_skills()` | markdown business skills |
| `brain/business_skill_matcher.py` | `rank_business_skills()` | ranked skills, score, confidence, provenance |
| `brain/business_intelligence_bridge.py` | `run_business_intelligence_bridge()` | matched skill, domain, audit, bridge diagnostics |

Skill matching is advisory. It enriches planner output and LLM prompt context but should not directly render.

## Reasoning

| File | Function | Output |
| --- | --- | --- |
| `brain/business_reasoning_engine.py` | `reason_business_message()` | business principle, thinking pattern, decision tree, recommended response, response mode |
| `brain/reasoning_engine.py` | `build_reasoning()` | deterministic app action, workflow readiness, LLM need |

Business reasoning extracts structured guidance from matched skills. Legacy reasoning still owns some deterministic actions such as receipt acknowledgements.

## Prompt

| File | Function | Output |
| --- | --- | --- |
| `brain/llm_orchestrator.py` | `build_reasoning_context()` | broad LLM decision context |
| `llm/prompt_context_builder.py` | `build_prompt_context()` | compact provider prompt context and diagnostics |

Prompt context includes planner output, workflow, normalized business context, business intent/entities, workflow context, recent conversation, store profile, selected skill, reasoning, and LLM decision. It dedupes sections and enforces a character budget.

## LLM

| File | Function | Output |
| --- | --- | --- |
| `brain/llm_orchestrator.py` | `decide_llm_usage()` | `should_use_llm`, `response_mode`, reason |
| `llm/llm_router.py` | `generate_llm_response()` | provider response text or `None` |

LLM output can replace deterministic response text only before rendering. If budget, demo guard, key availability, or provider call fails, deterministic text remains the fallback.
