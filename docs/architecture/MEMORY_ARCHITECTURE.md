# Memory Architecture

SME Companion uses Streamlit session state, shared in-process application state, and JSON files. Memory is currently practical and local, not a durable multi-user database architecture.

## Memory Layers

| Memory | Location | Owner | Purpose |
| --- | --- | --- | --- |
| Chat transcript | `st.session_state["chat_history"]` | `app.py` | Rendered user/assistant messages. |
| Conversation memory | `application_state["conversation"]`, `brain/conversation_memory_engine.py` | `app.py`, task router | Compact recent context, intent, workflow, topic, references. |
| Business context | `application_state["business_context"]`, `conversation["business_context"]` | `brain/business_context_engine.py`, app sync helpers | Current business type, product, topic, source/confidence/conflicts. |
| Store profile | `st.session_state`, `application_state["store"]`, `data/stores/.../store_profile.json` | `app.py`, `memory/store_profile_storage.py` | Store identity and profile. |
| Workflow memory | `st.session_state["conversation_state"]`, `application_state["workflow"]`, `conversation["conversation_os"]` | `app.py`, `brain/conversation_manager.py` | Active workflow, collected fields, missing fields, workflow status. |
| Business memory | `data/business_memory.json`, session `business_memory` | `memory/store_memory.py`, `brain/business_context_engine.py` | Business events and context fallback. |
| Receipt memory | `application_state["receipt"]`, `data/receipts/` | `memory/receipt_state.py`, `memory/receipt_storage.py` | Uploaded receipt status and file metadata. |
| Developer memory | `application_state["developer"]`, `st.session_state` diagnostics keys | `app.py`, `brain/task_router.py` | Planner output, route, LLM decision, response audit, prompt context. |

## Conversation Memory

`brain/conversation_memory_engine.get_last_context()` compacts the transcript into:

- recent user messages
- recent assistant replies
- last user message
- last assistant reply
- previous and last intent
- previous and last workflow
- focused business topic
- reference target
- turn count

`remember_turn()` updates this memory during `build_task_route()`. In the current pipeline this update happens before the final assistant reply is known, so assistant reply memory is usually sourced from prior chat history rather than the current response.

## Business Memory

Business events are saved from the bottom fallback path through `save_business_event()`. Business context can read from business memory only after higher-priority sources are unavailable.

Business memory is lower priority than:

1. Current message
2. Active workflow fields
3. Store profile
4. Conversation memory
5. Business memory

## Store Profile

Store profile is loaded into session/application state and reused by:

- companion dashboard sections
- deterministic chat response
- business context
- prompt context
- LLM context
- persistence after chat event

Store profile fields are normalized in `app.py` and persisted under `data/stores/...`.

## Workflow Memory

Workflow state exists in both legacy and Conversation OS forms:

- Legacy session keys: `current_workflow`, `workflow_step`, `workflow_data`, `workflow_state_v2`.
- Application workflow section: `current_workflow`, `workflow`, `step`, `workflow_state_v2`, `is_ready`.
- Conversation OS: `conversation_os.active_workflow_id`, `workflow_states`, `conversation_stack`, `planner_locked`.

Sync helpers in `app.py` and `brain/conversation_manager.py` keep these views aligned:

- `_sync_session_to_application_state()`
- `_sync_conversation_os_to_session()`
- `_sync_workflow_state_v2()`
- `sync_legacy_workflow_state()`

## Priority Rules

Business context priority is explicit in `brain/business_context_engine.py`:

```text
current_message
workflow
store_profile
conversation_memory
business_memory
```

Response source priority is explicit in `brain/response_intelligence_engine.py`, but not fully authoritative yet because `app.py` selects many responses before final audit:

```text
guard_response
workflow_response
reasoning_response
direct_conversation_response
llm_response
deterministic_response
legacy_response
fallback_response
```

## Risks

- The same workflow facts are mirrored in several structures.
- `chat_history` is both display log and memory source.
- Business context may be stale when it comes from conversation or business memory.
- Current assistant reply is not committed to compact memory until after `build_task_route()`.

## V5 Recommendation

Keep three distinct memory concepts:

- `ConversationLog`: append-only user/assistant turns.
- `ConversationState`: current intent, references, active workflow, compact memory.
- `ResponseEnvelope`: final response and diagnostics for each turn.

Derived memory should be rebuilt from these sources, not independently mutated in multiple places.
