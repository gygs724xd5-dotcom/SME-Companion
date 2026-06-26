# SME Companion V2.3 Platform Architecture

SME Companion V2.3 introduces an AI-native platform foundation before response generation. The goal is to turn each user message into a task plan, check capability availability, load documentation-driven skills, and then let existing reasoning, workflow, and LLM layers decide how to respond.

This sprint does not implement OCR, POS Sync, Inventory, forecasting, or autonomous actions.

## Architecture Diagram

```text
User Message
    |
    v
Planner Engine
    |
    v
Capability Registry
    |
    v
Skill Loader
    |
    v
Reasoning Engine
    |
    v
Existing Workflow Layer
    |
    v
LLM Prompt Context Builder (only when LLM is needed)
    |
    v
Response Layer
```

Developer Mode reads the same route and shows diagnostics only. It does not mutate planner, capability, workflow, or LLM behavior.

## Application State

`memory.application_state` remains the shared state container. It keeps compact sections for:

- `conversation`
- `workflow`
- `store`
- `receipt`
- `dashboard`
- `ui`
- `developer`

The planner reads this state before reasoning. It does not write business results or generate user responses.

## Planner

`brain.planner_engine.build_execution_plan(application_state, user_message)` converts the request into:

- goal
- task type
- required skills
- required information
- known information
- missing information
- execution eligibility
- next step
- priority
- estimated response mode

The planner is deterministic and response-free.

## Capability Registry

`brain.capability_registry` registers every platform capability, including available capabilities and future placeholders.

Available foundation capabilities include:

- Sales Plan
- Content Plan
- Cost Calculation
- Dashboard Request
- Receipt Upload
- Conversation Memory
- Product Feedback
- Developer Intelligence

Future unavailable capabilities include:

- OCR
- Inventory
- POS Sync
- Business Forecast

Each capability defines `name`, `description`, `available`, `maturity`, and `required_modules`.

## Skill Loader

`brain.skill_loader` loads markdown skills from `skills/`. Skills are documentation-driven and are not executable code.

The loader returns a `Skill` object with:

- `name`
- `path`
- `content`
- `available`

## Reasoning

Existing `brain.reasoning_engine.build_reasoning` remains the deterministic reasoning layer. The new `brain.task_router` calls it after planning, capability lookup, and skill loading.

## Workflow

Existing workflows remain unchanged. The router only prepares route metadata. Current workflow generation still owns deterministic workflow replies.

## LLM

`llm.prompt_context_builder.build_prompt_context` creates compact LLM context only when LLM use is needed.

It can include:

- application state UI flags
- conversation memory
- workflow state
- planner output
- selected capability
- loaded skill
- store profile
- product brain context
- developer mode context when enabled

Unrelated context should not be sent.

## Developer Intelligence

Developer Intelligence remains read-only for this sprint. Developer Mode can show:

- Planner Output
- Task Type
- Selected Capability
- Loaded Skill
- Reasoning Mode
- Workflow Ready
- LLM Needed
- Capability Available

## Future Placeholders

The foundation reserves names for future engines and agents without implementing them:

- OCR Engine
- Inventory Engine
- Sales Forecast Engine
- Business Memory
- Marketing Agent
- Financial Agent
- Inventory Agent
