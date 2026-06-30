# SME Companion V4.9 Response Flow Audit

This audit maps how one chat message travels through SME Companion until the final response is rendered. It documents current behavior only. It does not prescribe business logic changes.

## System Response Flow

```text
User Message
  |
  v
app._show_chat_companion()
  |
  v
Conversation OS
  |
  v
Conversation Understanding + Planner/Task Router
  |
  v
Business Intent -> Entity Extractor -> Business Context -> Business Workflow
  |
  v
Business Intelligence Bridge -> Business Skill Matcher -> Business Reasoning
  |
  v
Prompt Context Builder -> LLM Orchestrator -> LLM Router
  |
  v
Response Intelligence -> Final Response Selection/Audit
  |
  v
chat_history append -> st.chat_message("assistant") -> rendered response
```

## Stage Map

| Stage | File | Function | Input | Output | Responsibilities | Can modify response? | Can stop pipeline? | Can replace response? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| User Message | `app.py` | `_show_chat_companion()` | `st.chat_input()` or `pending_quick_prompt` | `user_message` string | Receives current turn. | No | Yes, if empty | No |
| Conversation OS | `app.py`, `brain/conversation_manager.py` | `conversation_os_active_workflow_state()`, `continue_workflow()` | `application_state`, `user_message` | active workflow, continuation event | Enforces planner lock, continue/pause/cancel/resume workflow, handles temporary interrupts. | Yes, for control/interrupt replies in `app.py` | Yes | Yes |
| Planner | `app.py`, `brain/task_router.py`, `brain/planner_engine.py` | `_record_reasoning()`, `build_task_route()`, `build_execution_plan()` | synchronized app state, user message or planner message | `task_route`, `planner_output`, `reasoning` | Builds route metadata, task, capability, skills, LLM decision, response gate. | No | Yes indirectly through route decisions | No |
| Intent Engine | `brain/business_intent_engine.py`, `brain/conversation_understanding_engine.py` | `detect_business_intent()`, `understand_conversation()` | raw message, state | business intent, conversation interpretation | Detects broad business intent, legacy intent, references, planner message. | No; direct reply helper can later write | No | No |
| Entity Extractor | `brain/business_entity_extractor.py` | `extract_business_entities()` | message, detected intent | extracted entities, required/completed/missing entities | Pulls prices, costs, quantities, dates, product names, customer phrases. | No | No | No |
| Business Context | `brain/business_context_engine.py` | `build_business_context()` | state, message, understanding, memory | normalized business context | Chooses context by priority: current message, workflow, store profile, conversation memory, business memory. | No | No | No |
| Business Workflow | `brain/business_workflow_engine.py` | `decide_business_workflow()` | message, intent, entities, state | workflow action/intelligence | Decides continue, interrupt, resume, complete, cancel, start_new; asks missing entity question metadata. | No | Yes indirectly through gate/handler | No |
| Business Intelligence Bridge | `brain/business_intelligence_bridge.py` | `run_business_intelligence_bridge()`, `inject_business_intelligence()` | message, context, planner output | bridge result, enriched planner | Connects skill matching and business reasoning to planner. Fail-open. | No | No | No |
| Business Skill Matcher | `brain/business_skill_matcher.py`, `brain/business_skill_loader.py` | `rank_business_skills()`, `top_business_skill_match()`, loader/search helpers | message, context, candidate skills | ranked skills, match audit | Scores business skills and provenance. | No | No | No |
| Business Reasoning | `brain/business_reasoning_engine.py`, `brain/reasoning_engine.py` | `reason_business_message()`, `build_reasoning()` | matched skill or state/message | structured reasoning | Extracts principle, decision tree, response mode, workflow, memory tags; legacy deterministic action. | No, except `app.py` uses some reasoning actions for receipt reply | Yes for receipt reasoning path | No |
| Prompt Context Builder | `llm/prompt_context_builder.py`, `brain/llm_orchestrator.py` | `build_prompt_context()`, `build_reasoning_context()` | app state, planner, workflow, skill, reasoning, business context | compact prompt context | Selects/dedupes context sections, enforces prompt budget, stores diagnostics. | No | No | No |
| LLM Orchestrator | `brain/llm_orchestrator.py`, `llm/llm_router.py` | `decide_llm_usage()`, `generate_llm_response()` | reasoning context, prompt context | LLM decision and optional text | Decides if provider should be called; routes to DeepSeek/OpenAI. | Yes, when LLM reply exists | No; falls back on no reply | Yes |
| Response Intelligence | `brain/response_intelligence_engine.py`, `app.py` | `select_planner_first_response()`, `guard_response()`, `_resolve_assistant_reply()` | route, reply candidates, chat history | possibly changed reply/source | Handles planner-first missing info reply, empty fallback, repetitive/generic guard. | Yes | Yes on planner-first branch | Yes |
| Final Response Selection | `app.py`, `brain/response_intelligence_engine.py` | `_finalize_ai_pipeline_debug_trace()`, `select_final_response()` | selected reply, source, candidates, route | response audit diagnostics | Records final origin and candidates; applies workflow response gate metadata. Current helper usually audits already-selected text. | No in current use when text already supplied | No | Only when called without final text |
| UI Rendering | `app.py` | `_append_workflow_reply()`, `_render_assistant_message()`, `_render_assistant_response()`, `_render_markdown()` | assistant message text | Streamlit-rendered response | Appends to history, syncs state, streams/markdown renders. | Cleans text before render | Yes after render because turn returns | No after render |

## Call Graph For One User Request

Typical non-locked, non-quick-action chat request:

```text
_show_chat_companion()
  -> _sync_conversation_business_context()
  -> render previous chat_history via st.chat_message()
  -> st.chat_input()
  -> start_pipeline_trace()
  -> _update_chat_developer_diagnostics()
  -> _latest_chat_context()
  -> _sync_chat_history_to_application_state()
  -> st.chat_message("user")
  -> _sync_session_to_application_state()
  -> conversation_os_active_workflow_state()
  -> understand_conversation()
  -> _update_conversation_state_after_user()
  -> _record_reasoning()
      -> _sync_session_to_application_state()
      -> build_task_route()
          -> detect_business_intent()
          -> extract_business_entities()
          -> decide_business_workflow()
          -> understand_conversation() if needed
          -> get_last_context()
          -> build_business_context()
          -> resolve_intent()
          -> remember_turn()
          -> build_execution_plan()
          -> run_business_intelligence_bridge()
              -> search_business_skills()
              -> load_all_business_skills()
              -> rank_business_skills()
              -> reason_business_message()
          -> inject_business_intelligence()
          -> get_capability()
          -> is_capability_available()
          -> load_skills()
          -> build_reasoning()
          -> build_reasoning_context()
          -> decide_llm_usage()
          -> workflow_response_gate()
      -> _update_application_section("developer")
  -> _sync_route_intelligence_to_session()
  -> select_planner_first_response()
  -> classify_message_priority()
  -> detect_workflow_intent()
  -> workflow handlers or direct/simple/product branches if matched
  -> analyze_chat_intent()
  -> generate_chat_response()
  -> build_reasoning_context()
  -> decide_llm_usage()
  -> build_prompt_context() if LLM needed
  -> generate_llm_response() if allowed
      -> get_llm_provider()
      -> deepseek_client.generate_response() or openai_client.generate_response()
  -> save_business_event()
  -> _resolve_assistant_reply()
  -> guard_response()
      -> select_planner_first_response()
  -> _update_conversation_state_after_assistant()
  -> st.session_state["chat_history"].append(assistant_message)
  -> _finalize_ai_pipeline_debug_trace()
      -> _resolve_assistant_reply()
      -> workflow_response_gate()
      -> determine_response_mode()
      -> select_final_response()
      -> _update_chat_developer_diagnostics()
  -> _sync_chat_history_to_application_state()
  -> st.chat_message("assistant")
      -> _render_assistant_message()
          -> clean_response()
          -> _render_assistant_response()
              -> st.write_stream() or st.markdown()
      -> _render_assistant_footer()
  -> finalize_pipeline_trace()
```

Locked Conversation OS workflow request:

```text
_show_chat_companion()
  -> st.chat_input()
  -> append user message
  -> conversation_os_active_workflow_state()
  -> classify_message_priority()
  -> conversation_os_continue_workflow()
  -> _sync_conversation_os_to_session()
  -> temporary interrupt/cancel/pause branch OR
  -> _handle_state_machine_workflow()
      -> classify_message_priority()
      -> update_workflow_state()
      -> prepare_content_collection_state()
      -> _sync_workflow_state_v2()
      -> _generate_workflow_reply() if ready
      -> _maybe_improve_workflow_reply_with_llm()
      -> build_workflow_reply()
  -> _finalize_ai_pipeline_debug_trace()
  -> _append_workflow_reply()
      -> _workflow_response_source_for_current_route()
      -> _resolve_assistant_reply()
      -> append chat_history
      -> st.chat_message("assistant")
```

## Response Writers

| Name/pattern | File | Function | Purpose | Who calls it | Who consumes it |
| --- | --- | --- | --- | --- | --- |
| `reply` | `app.py` | reset branch in `_show_chat_companion()` | Reset confirmation. | `_show_chat_companion()` | `chat_history`, renderer |
| `reply` | `app.py` | Conversation OS temporary interrupt/cancel/pause branches | Control replies for active workflows. | `_show_chat_companion()` | `_append_workflow_reply()` or direct render |
| `reply` | `app.py` | `_handle_product_feedback()` | Product feedback acknowledgement. | `_show_chat_companion()` | `chat_history`, renderer |
| `reply` | `app.py` | `_cost_intro_reply()`, `_cost_result_reply()`, `_handle_cost_workflow()` | Legacy cost workflow prompts/results. | `_show_chat_companion()` | `_append_workflow_reply()` |
| `reply` | `app.py` | `_handle_dashboard_workflow()` | Dashboard placeholder response. | quick action and chat workflow branches | `_append_workflow_reply()` |
| `reply` | `app.py` | `_receipt_uploaded_reply()`, `_handle_receipt_workflow()` | Receipt placeholder/ack response. | `_show_chat_companion()`, `_handle_receipt_workflow()` | `_append_workflow_reply()` |
| `reply` | `app.py` | `_workflow_missing_reply()`, `_generate_*()`, `_generate_workflow_reply()` | V2 workflow prompts and generated deterministic workflow outputs. | `_handle_state_machine_workflow()` | `build_workflow_reply()` |
| `reply` | `app.py` | `_maybe_improve_workflow_reply_with_llm()` | Optional LLM replacement for workflow generated text. | `_handle_state_machine_workflow()` | `build_workflow_reply()` |
| `workflow_response` | `app.py` | `_append_workflow_reply()` | Normalizes and records workflow response source. | many workflow branches | `chat_history`, diagnostics, renderer |
| `deterministic_response` | `app.py` | `_show_chat_companion()` | Holds `generate_chat_response()` result. | `_show_chat_companion()` | LLM overlay, guard, final append |
| `llm_response` | `app.py`, `llm/llm_router.py` | `generate_llm_response()` | Provider-generated replacement text. | `_show_chat_companion()`, `_maybe_improve_workflow_reply_with_llm()` | response object or workflow reply |
| `legacy_response` | `app.py`, `brain/chat_companion_engine.py` | `generate_chat_response()` | Legacy deterministic local companion reply. | `_show_chat_companion()` | response object, response audit |
| `direct_conversation_response` | `app.py`, `brain/conversation_understanding_engine.py` | `_greeting_reply()`, `_follow_up_reply()`, `build_direct_reply()` | Direct short-circuit answers. | `_show_chat_companion()` | `chat_history`, renderer |
| `planner_first_response` | `brain/response_intelligence_engine.py` | `select_planner_first_response()` | Missing-information or context-update response before legacy generation. | `_show_chat_companion()`, `guard_response()` | `_append_workflow_reply()` or guard |
| `guard_response` | `brain/response_intelligence_engine.py` | `guard_response()` | Replacement for empty/generic/repetitive final response. | `_show_chat_companion()` | final `response["reply"]` |
| `final_response` | `app.py`, `brain/response_intelligence_engine.py` | `_finalize_ai_pipeline_debug_trace()`, `select_final_response()` | Audit final selected source and preview. | all finalize branches | developer diagnostics |
| `response` | `brain/chat_companion_engine.py` | `generate_chat_response()` return dict | Deterministic response payload with metadata. | `_show_chat_companion()` | LLM merge, persistence, final append |
| `response_text` / `reply_text` | Project-wide search | No canonical variable found as a primary runtime owner. | N/A | N/A |
| `assistant_response` | `app.py` | `_render_assistant_response()` parameter concept | Rendering text only, not response composition. | `_render_assistant_message()` | Streamlit |

## Response Selectors

| Selector | Priority | Selection rule | Override rule | Fallback rule |
| --- | --- | --- | --- | --- |
| Reset command branch | Highest after input | `_is_reset_command(user_message)` | Resets session and returns immediately. | Empty fallback via `_resolve_assistant_reply()` |
| Conversation OS locked branch | Before planner path | Active workflow locks planner. `continue_workflow()` decides control/continue. | New intent/workflow switch pauses workflow and releases planner. | Workflow missing reply or workflow handler |
| Reasoning receipt branch | Before planner-first | `reasoning.action in {"receipt_uploaded_ack", "receipt_ocr_pending"}` | Forces receipt reasoning response. | `_receipt_uploaded_reply()` |
| Planner-first response | Before workflow handlers | `select_planner_first_response()` handles business context update or missing info. | Skips if active workflow exists or workflow collection should proceed elsewhere. | `handled=False` continues pipeline |
| V2 workflow selection | Before legacy workflow | `detected_workflow_v2` in dashboard/receipt/sales/cost/content. | LLM may improve ready workflow output. | `_workflow_missing_reply()` |
| Legacy workflow selection | Before simple/product/fallback | Legacy `detect_workflow()` or active legacy cost state. | `_workflow_response_source_for_current_route()` can relabel source when gate blocks. | Legacy handler reply |
| Direct/simple conversation | Before product and deterministic fallback | Greeting, correction, follow-up. | None after branch starts. | Continue to product/deterministic if no simple reply |
| Product feedback | Before deterministic fallback | `conversation_intent == "PRODUCT_FEEDBACK"`. | None. | `_resolve_assistant_reply()` |
| LLM over deterministic | Inside bottom fallback path | Start with `deterministic_response`; if `decide_llm_usage()` true and provider returns text, replace with LLM reply. | Budget, demo guard, missing key, provider error keep deterministic. | Deterministic response remains |
| Response guard | After deterministic/LLM | `guard_response()` replaces generic or repetitive replies. | Uses planner-first/missing info only when it can produce a better answer. | Original reply remains |
| Final response audit | After selected text exists | `select_final_response()` records selected source and candidates. | If workflow source is blocked by gate, source is relabeled before audit. | If no selected text, chooses first available by `SOURCE_PRIORITY` |

`SOURCE_PRIORITY` in `brain/response_intelligence_engine.py` is:

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

In the current app path, this priority mostly documents/audits. The actual response is commonly selected earlier in `app.py`.

## State Ownership

| State | Created | Updated | Reused |
| --- | --- | --- | --- |
| `chat_history` | `_init_session_state()`, `_reset_chat_session()`, demo loaders | `_show_chat_companion()`, `_append_workflow_reply()`, exception handler | Render loop, prompt context, memory, diagnostics, product dashboard |
| `conversation_history` | No canonical runtime key found; conversation history is `chat_history`. | N/A | N/A |
| `planner_output` | `build_task_route()` via `build_execution_plan()` | `_record_reasoning()` stores in `application_state["developer"]`; bridge can enrich plan | diagnostics, prompt context, response guard, LLM decision |
| `workflow_state` | Conversation OS `start_workflow()`, state machine `new_workflow_state()` | `continue_workflow()`, `_sync_workflow_state_v2()`, `_set_workflow_state()` | workflow handlers, planner, business workflow, prompt context |
| `assistant_reply` | `_latest_chat_context()` local variable | Read-only local snapshot | `_handle_product_feedback()` signature, reference context |
| `last_response` | No canonical runtime key found. | N/A | N/A |
| `cached_response` | No canonical runtime key found. | N/A | N/A |
| `last_llm_response` | No canonical runtime key found. LLM text is local `llm_reply`. | N/A | N/A |
| `response_source` | `_resolve_assistant_reply()`, `_workflow_response_source_for_current_route()`, bottom path local variable | `_finalize_ai_pipeline_debug_trace()`, `_update_chat_developer_diagnostics()` | developer diagnostics, response audit |
| `reply_builder` | Workflow reply builder or `_finalize_ai_pipeline_debug_trace()` default | `_update_chat_developer_diagnostics()` | developer diagnostics and legacy response detection |

## Legacy Architecture

| Path | Why still exists | When used | New architecture replacement status | Recommended future action |
| --- | --- | --- | --- | --- |
| `brain/chat_companion_engine.generate_chat_response()` | Local deterministic companion fallback predates router/bridge. | Bottom fallback path; used whenever LLM is not selected or unavailable. | Partially replaced by planner, business intelligence, prompt context, response guard. | Merge into Response Composer as deterministic candidate, then remove direct ownership. |
| Legacy workflow detector `brain/conversation_workflow_engine.detect_workflow()` | Older workflow trigger system. | After V2 workflow detection, before direct/product/fallback path. | V2 state machine and Conversation OS handle newer workflows. | Keep short term, then merge triggers into workflow registry. |
| `_handle_cost_workflow()` legacy cost state | Pre-V2 cost calculation flow. | Active `WORKFLOW_COST_CALCULATION` legacy state or legacy detected cost workflow. | V2 cost state machine exists. | Merge into V2, then remove. |
| `_handle_dashboard_workflow()` placeholder | Dashboard request currently records feedback/request, not full dashboard builder. | Dashboard quick action, V2 and legacy dashboard routes. | Planner/capability layer knows dashboard capability. | Keep until dashboard capability owns response envelope. |
| `_handle_receipt_workflow()` placeholder | OCR is not implemented. | Receipt quick action, V2 and legacy receipt routes. | Capability registry has OCR placeholder and receipt upload. | Keep with explicit placeholder status. |
| Simple direct branch (`_greeting_reply()`, `_follow_up_reply()`) | Fast UX for greetings/follow-up. | Before product and fallback generation. | Conversation understanding can build some direct replies. | Merge under direct-response candidate. |
| `_append_workflow_reply()` render helper | Shared append/render for many workflow branches. | Many early-return branches. | Response Intelligence exists but does not own rendering. | Keep until all branches return a `ResponseEnvelope`. |
| Response source alias `planner_response` | Historical name for deterministic companion. | Bottom fallback path and product feedback resolution. | `SOURCE_ALIASES` maps it to deterministic. | Rename in V5 migration only. |

## UI Render Flow

| Render/input point | File/function | Multiple or single? | Notes |
| --- | --- | --- | --- |
| `st.chat_input()` | `app.py::_show_chat_companion()` | Single active chat input | Also supports `pending_quick_prompt` instead of typed input. |
| Render old transcript | `app.py::_show_chat_companion()` loop over `chat_history` | Multiple render calls | Renders all prior messages before new input processing. |
| User message render | `app.py::_show_chat_companion()` | One per accepted input | Happens before response selection. |
| Assistant render reset branch | `app.py::_show_chat_companion()` | Separate branch | Returns immediately. |
| Assistant render Conversation OS temporary interrupt | `app.py::_show_chat_companion()` | Separate branch | Returns immediately. |
| Assistant render direct/simple/product/bottom path | `app.py::_show_chat_companion()` | Separate branches | Each appends and renders itself. |
| Assistant render workflow helper | `app.py::_append_workflow_reply()` | Shared by many workflow branches | Appends, syncs, renders, finalizes. |
| Exception render | `app.py::_handle_chat_pipeline_exception()` | Separate branch | Appends fallback if needed, renders fallback. |

There is no single render point. A response cannot be meaningfully replaced after a branch has called `st.chat_message("assistant")`; the turn normally returns immediately after rendering. Replacement must happen before append/render.

## Single Source Of Truth Recommendation

Introduce a `ResponseEnvelope` object created once per user turn:

```text
ResponseEnvelope
  id
  user_message
  final_text
  source
  candidates[]
  route
  workflow_state_before
  workflow_state_after
  prompt_context_id
  llm_decision
  response_mode
  reply_builder
  diagnostics
  render_status
```

All branches should return a `ResponseEnvelope` to one composer/render function. The UI should append/render only after the envelope is finalized.

## Final Architecture Report

### Strengths

- Strong diagnostic intent already exists: pipeline trace, developer diagnostics, response audit, response candidates.
- Business layer is mostly metadata-producing and fail-open, reducing risk from skill matching errors.
- Conversation OS has explicit lifecycle concepts: active workflow, pause, resume, cancel, stack, planner lock.
- LLM use is guarded by deterministic fallback, budget checks, demo limits, and provider availability.

### Weaknesses

- Response selection is split between `app.py` branches, workflow helpers, LLM replacement logic, guard logic, and final audit.
- `select_final_response()` often audits a decision already made elsewhere rather than owning the decision.
- Multiple render points make late replacement impossible and make branch consistency hard to reason about.
- Legacy response paths use newer diagnostics labels, so `planner_response`, `deterministic_response`, and `legacy_response` can be confusing.

### Duplicate Responsibilities

- Workflow detection exists in Conversation OS, V2 state machine detection, legacy `detect_workflow()`, planner, and business workflow intelligence.
- Prompt context is built from both `brain.llm_orchestrator.build_reasoning_context()` and `llm.prompt_context_builder.build_prompt_context()`.
- Business context appears in `application_state["business_context"]`, `conversation["business_context"]`, planner output, and LLM context.
- Response source is set in `_append_workflow_reply()`, bottom fallback path, `_finalize_ai_pipeline_debug_trace()`, and response intelligence.

### Possible Race Conditions / Ordering Risks

- Streamlit reruns can render existing `chat_history` before a branch appends a new assistant message.
- User message is appended before many downstream failures; exception handler must avoid duplicate user entries.
- Conversation OS and legacy workflow state are synced in both directions; stale `workflow_state_v2` can affect planner decisions if sync order changes.
- LLM reply is local until it replaces `response`; a provider failure falls back silently except diagnostics/captions.

### Suggested V5 Architecture

```text
InputAdapter
  -> ConversationStateLoader
  -> RouteBuilder
  -> CandidateBuilders
      - ControlResponseCandidate
      - WorkflowResponseCandidate
      - DirectResponseCandidate
      - DeterministicResponseCandidate
      - LLMResponseCandidate
      - FallbackResponseCandidate
  -> ResponseComposer
  -> StateCommitter
  -> Renderer
```

### Recommended Response Composer Design

- Accepts route, state snapshot, and candidates.
- Applies a single priority table and gates.
- Returns a `ResponseEnvelope`.
- Never renders.
- Commits to `chat_history` only after final text/source are selected.
- Stores full audit under `application_state["developer"]["response_envelope"]`.

### Recommended Single Source Of Truth

Use the finalized `ResponseEnvelope` as the per-turn source of truth. `chat_history` should be the display log derived from envelopes, not the only place the final response lives.
