# Debugging Guide

This guide maps diagnostics to the layer that owns them.

## First Places To Inspect

| Question | Inspect |
| --- | --- |
| What did the user type? | `st.session_state["last_chat_input"]`, pipeline trace `user_message` |
| What rendered? | `st.session_state["chat_history"][-1]` |
| Why this source? | `st.session_state["last_response_source"]`, `last_response_audit` |
| What did planner decide? | `st.session_state["last_task_route"]["planner_output"]` |
| What was the business intent/entity result? | `last_task_route["detected_intent"]`, `last_task_route["extracted_entities"]` |
| Which skill matched? | `last_task_route["business_intelligence"]` |
| Why did workflow take over? | `conversation_os`, `workflow_state_v2`, `conversation_priority`, `workflow_response_gate()` |
| Why did LLM not run? | `last_llm_decision`, budget guard messages, provider key availability |
| What prompt context was sent? | `st.session_state["last_prompt_context"]`, developer prompt context |
| Was final response guarded/replaced? | `last_response_audit.final_response_candidates`, `response_source_after_gate` |

## In-App Developer Diagnostics

`app.py` renders these expanders when `developer_mode` is enabled:

- Workflow Diagnostics
- Shared Application State
- Platform Planner Diagnostics
- AI Pipeline Debug

These are driven by:

- `_show_workflow_diagnostics()`
- `_show_shared_application_state_diagnostics()`
- `_show_platform_diagnostics()`
- `_show_ai_pipeline_debug_trace()`

## Pipeline Trace

`brain/pipeline_debugger.py` records ordered events:

- `start_pipeline_trace(user_message)`
- `add_pipeline_event(stage, function, message, metadata)`
- `finalize_pipeline_trace()`
- `get_pipeline_trace()`

The trace is stored under `application_state["debug"]["last_pipeline_trace"]` when possible and mirrored through app diagnostics.

## Layer Diagnostics

| Layer | Diagnostic fields |
| --- | --- |
| Conversation OS | `conversation.conversation_os`, active workflow, planner lock, stack, event |
| Conversation priority | `conversation_priority.classification`, `priority_action`, `detected_new_intent`, `allow_field_extraction` |
| Understanding | `conversation_understanding.detected_intent`, `legacy_intent`, `planner_message`, references |
| Planner | `planner_output.task_type`, `workflow`, `next_step`, `missing_information`, `estimated_response_mode` |
| Business intent/entity | `detected_intent`, `extracted_entities`, `missing_entities`, `entity_completeness` |
| Business context | `business_context.source`, `confidence`, `conflicts`, `is_stale`, `context_isolation_applied` |
| Skill matching | `business_intelligence.matched_skill`, `ranking_table`, `skill_match_audit` |
| Reasoning | `reasoning.action`, `workflow_ready`, `llm_needed`, `response_mode` |
| Prompt | `last_prompt_context`, `included_context_sections`, `omitted_context_sections`, `prompt_context_size` |
| LLM | `last_llm_decision.should_use_llm`, `reason`, `llm_latency_ms`, `token_usage`, `error` |
| Response | `last_response_source`, `last_response_empty`, `reply_builder`, `response_audit` |
| UI | final `chat_history` append and Streamlit render branch |

## Common Failure Patterns

### Wrong workflow continues

Inspect:

- `conversation_os.active_workflow_id`
- `workflow_state_v2.workflow`
- `classify_message_priority()` event
- `planner_locked`

Likely causes:

- Planner is locked by active workflow.
- Message classified as workflow answer.
- Legacy and V2 workflow state are out of sync.

### Workflow answer is generated but response source says direct/LLM

Inspect:

- `workflow_response_gate(task_route)`
- `_source_when_workflow_response_blocked()`
- `response_source_before_gate`
- `response_source_after_gate`

Likely cause: selected text came from workflow branch, but response gate relabeled source because intent/action says workflow response should be bypassed.

### LLM expected but deterministic response rendered

Inspect:

- `last_llm_decision.should_use_llm`
- `last_llm_decision.reason`
- budget guard state
- provider key availability
- provider error captured in LLM decision

Likely causes:

- Missing information blocks LLM.
- Deterministic task/workflow selected.
- Budget/demo guard blocked call.
- Provider returned no text.

### Generic fallback rendered

Inspect:

- `_resolve_assistant_reply()` input reply
- `last_response_empty`
- `guard_response()` candidate
- `final_response_candidates`

Likely causes:

- Branch produced empty reply.
- LLM returned empty and deterministic reply was empty.
- Response cleaner removed all text.

### Skill match seems stale or unrelated

Inspect:

- `business_context.source`
- `previous_context_intent`
- `intent_changed`
- `context_isolation_applied`
- `skill_match_audit.suspicious_matches`

Likely causes:

- Context or metadata token outweighed current-message evidence.
- Intent isolation did not suppress enough historical context.

## Recommended Future Developer Dashboard

Do not implement this as part of V4.9. Recommended sections:

| Section | Contents |
| --- | --- |
| Pipeline Overview | ordered stage timeline, elapsed time, stop branch, final source |
| Conversation | raw message, normalized text, chat history count, latest references |
| Intent | conversation intent, business intent, legacy intent, confidence |
| Entity | extracted entities, required/completed/missing, confidence |
| Workflow | Conversation OS status, planner lock, active workflow, state machine, gate decision |
| Business Context | selected context, source priority, stale/conflict flags |
| Skill Matching | candidate table, selected skill, provenance, suspicious tokens |
| Reasoning | action, response mode, decision tree, questions, avoid rules |
| Prompt | included/omitted sections, prompt size, redacted prompt preview |
| LLM | decision, provider, budget state, latency, fallback reason |
| Response Composer | candidates, priority, selected candidate, override/gate decisions |
| UI | chat append status, render branch, final text preview |

## Debugging Rule Of Thumb

Debug in this order:

1. Confirm final rendered `chat_history`.
2. Confirm `last_response_source` and response audit.
3. Confirm route/planner/workflow gate.
4. Confirm workflow lock and priority classification.
5. Confirm LLM decision and prompt only if source was expected to be LLM.
