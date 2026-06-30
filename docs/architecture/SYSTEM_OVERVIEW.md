# SME Companion Architecture Overview

This document describes the current SME Companion V4.9 runtime architecture as observed in the codebase. It is a developer reference, not a design target.

## System Shape

```text
Streamlit UI
app.py
  |
  +-- Session state and application_state synchronization
  +-- Conversation OS and workflow lock handling
  +-- Conversation understanding and legacy intent detection
  +-- Task router / planner / business intelligence bridge
  +-- Workflow handlers and deterministic response builders
  +-- Optional LLM prompt construction and provider routing
  +-- Response guard, response audit, chat history append, rendering

brain/
  |
  +-- Conversation OS, priority, understanding, memory
  +-- Planner, capability, skill loading
  +-- Business intent, entity, context, workflow, skill matching, reasoning
  +-- Workflow state machine and workflow reply builder
  +-- Response intelligence and response mode decisions

llm/
  |
  +-- Prompt context builder
  +-- Provider router
  +-- OpenAI / DeepSeek clients

memory/ and data/
  |
  +-- Shared in-process application_state
  +-- Store profile files
  +-- Business memory JSON
  +-- Receipt state and receipt files

feedback/
  |
  +-- Product feedback classification
  +-- Product learning and backlog capture
```

## Core Layers

| Layer | Primary files | Responsibility | Writes user-visible response? |
| --- | --- | --- | --- |
| UI shell | `app.py` | Streamlit screen, chat input, chat message rendering, session state. | Yes |
| Shared state | `memory/application_state.py`, `app.py` sync helpers | Keeps `conversation`, `workflow`, `store`, `receipt`, `dashboard`, `ui`, `developer`. | No |
| Conversation OS | `brain/conversation_manager.py`, `brain/conversation_priority_engine.py` | Owns active workflow lock, pause/resume/cancel/continue, workflow stack. | No, but can stop/redirect pipeline |
| Understanding | `brain/conversation_understanding_engine.py`, `brain/conversation_intent_engine.py` | Normalizes user message, legacy intent, references, planner message. | Sometimes via `build_direct_reply` |
| Planner/router | `brain/task_router.py`, `brain/planner_engine.py` | Builds route metadata, capability, skills, reasoning, LLM decision, response gate. | No |
| Business interpretation | `brain/business_intent_engine.py`, `brain/business_entity_extractor.py`, `brain/business_context_engine.py`, `brain/business_workflow_engine.py` | Intent, entities, context ownership, workflow action. | No |
| Business intelligence | `brain/business_intelligence_bridge.py`, `brain/business_skill_matcher.py`, `brain/business_reasoning_engine.py` | Skill search, skill match audit, business principle/reasoning. | No |
| Workflow response | `app.py`, `brain/workflow_state_machine.py`, `brain/workflow_reply_builder.py` | Collects fields, generates workflow prompts/results. | Yes |
| Deterministic companion | `brain/chat_companion_engine.py` | Local response fallback and legacy deterministic business coach. | Yes |
| LLM | `brain/llm_orchestrator.py`, `llm/prompt_context_builder.py`, `llm/llm_router.py` | Decides LLM usage, builds context, calls provider. | Yes |
| Response intelligence | `brain/response_intelligence_engine.py`, `app.py` finalize helpers | Guard fallback/repetitive responses, audit final source, response gate. | Yes, can replace before render |
| Rendering | `app.py` | Appends `assistant` message, syncs history, renders Streamlit message. | Final visible output |

## Current Source Of Truth

There is no single response source of truth yet. The effective source of truth is split across:

- `st.session_state["chat_history"]`: rendered conversation transcript.
- `st.session_state["last_task_route"]`: route/planner/business diagnostics.
- `st.session_state["last_response_source"]` and `last_response_audit`: final response diagnostics.
- `memory.application_state["conversation"]["chat_history"]`: synchronized copy for engines.
- Local `response`, `reply`, and `response_source` variables inside `_show_chat_companion()`.

For V5, response composition should become one explicit `ResponseEnvelope` produced before any UI rendering.
