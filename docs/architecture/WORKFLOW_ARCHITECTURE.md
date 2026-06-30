# Workflow Architecture

SME Companion currently has Conversation OS lifecycle management, V2 workflow state machines, and legacy workflow handlers.

## Lifecycle

```text
Start
  |
  v
COLLECT missing fields
  |
  v
EXECUTE / generate response
  |
  v
END

Side paths:
  interrupt -> pause workflow -> answer new intent -> resume
  cancel -> CANCELLED
  temporary interrupt -> answer quick question -> ask missing field again
```

## Start

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `start_workflow()` | Creates Conversation OS workflow state, pauses existing lower-priority workflow, locks planner. |
| `brain/workflow_state_machine.py` | `new_workflow_state()` | Creates V2 state machine state. |
| `app.py` | `_handle_state_machine_workflow()` | Starts/updates V2 state when detected workflow enters handler. |

Start can be triggered by quick actions, planner/workflow detection, or active Conversation OS switching.

## Continue

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `continue_workflow()` | Handles control intents, unrelated questions, priority routing, and field extraction. |
| `brain/conversation_priority_engine.py` | `classify_message_priority()` | Classifies whether message is workflow answer, new intent, switch, or other route. |
| `brain/workflow_state_machine.py` | `update_workflow_state()` | Extracts fields and updates missing/ready state. |
| `app.py` | `_handle_state_machine_workflow()` | Builds workflow reply and optionally improves with LLM. |

Continue is the strongest path when `planner_locked` is true.

## Resume

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `resume_workflow()` | Restores paused workflow from active state, stack, or `last_paused_workflow_id`. |
| `brain/business_workflow_engine.py` | `decide_business_workflow()` | Emits `workflow_action="resume"` for business workflow intelligence. |

Resume restores planner lock and returns workflow to `COLLECT` or `EXECUTE`.

## Interrupt

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `continue_workflow()` | Temporary interrupt for unrelated question; can release planner for priority route. |
| `brain/business_workflow_engine.py` | `decide_business_workflow()` | Emits `interrupt` for override intents and general questions. |
| `app.py` | locked workflow branch | Renders temporary interrupt response or pauses workflow for new intent. |

Interrupt can produce a response immediately, so it is a pipeline stop point.

## Complete

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `complete_workflow()` | Marks workflow `END`, records completion memory, unlocks or resumes stack. |
| `app.py` | `_sync_conversation_os_from_v2_state()` | Calls completion when V2 workflow state reaches `completed`. |
| `app.py` | `_handle_state_machine_workflow()` | Generates final workflow reply when `is_ready` is true, then marks state completed. |

Completion writes memory into `business_memory`, `conversation_memory.completed_workflows`, and `store.last_completed_workflow`.

## Cancel

| File | Function | Responsibility |
| --- | --- | --- |
| `brain/conversation_manager.py` | `cancel_workflow()` | Marks workflow `CANCELLED` and unlocks/resumes stack. |
| `brain/conversation_manager.py` | `detect_control_intent()` | Detects cancel control text. |
| `app.py` | locked workflow branch | Renders cancellation reply. |

## Legacy Workflow Paths

| Legacy path | Current usage | Recommendation |
| --- | --- | --- |
| `brain/conversation_workflow_engine.detect_workflow()` | Legacy detection for cost/dashboard/receipt/product feedback. | Merge into workflow registry. |
| `app.py::_handle_cost_workflow()` | Legacy cost collection/result. | Migrate to V2 state machine. |
| `app.py::_set_workflow_state()` / `_clear_workflow_state()` | Legacy session workflow state. | Keep only as compatibility until Conversation OS is sole owner. |
| `app.py::_append_workflow_reply()` | Shared append/render helper for many workflow branches. | Replace with composer/render boundary. |

## Response Gate

`brain/task_router.workflow_response_gate()` decides whether a workflow response source should be allowed:

- Allows workflow response only when workflow action is `continue` or `start_new`, missing entities exist, and intent is not in bypass list.
- Blocks for `interrupt`, `resume`, `complete`, `cancel`.
- Blocks for general/direct response intents.
- Blocks when entity completeness is already complete.

This gate currently relabels/audits selected source more often than it prevents response generation.
