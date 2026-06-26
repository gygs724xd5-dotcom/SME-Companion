# Architecture

SME Companion is a Streamlit application with local deterministic engines, optional provider-backed LLM responses, and JSON-based memory. The architecture is intentionally lightweight so the product can be tested quickly while the core business and product-learning loops mature.

## System Diagram

```text
User
  |
  v
Streamlit UI
app.py
  |
  +-------------------+-------------------+-------------------+
  |                   |                   |                   |
  v                   v                   v                   v
Business Brain   Conversation Brain   Product Brain       Demo Loader
brain/           brain/               feedback/           demo/
  |                   |                   |                   |
  +-------------------+-------------------+-------------------+
                      |
                      v
                  LLM Layer
                  llm/
                      |
            +---------+---------+
            |                   |
            v                   v
        DeepSeek             OpenAI

Memory Layer
memory/, data/, product_backlog.json
```

## Runtime Flow

```text
1. User selects a demo store or creates a store profile.
2. app.py stores profile and session state.
3. Business engines generate diagnosis, insights, content, goals, campaign, and sales guidance.
4. Chat messages pass through conversation intent detection.
5. Product feedback messages are routed to the Product Brain.
6. Business-context messages use local engines and, when enabled, the LLM layer.
7. Memory and feedback are persisted to local JSON files.
```

## Business Brain

The Business Brain lives primarily in `brain/` and `content_engine.py`.

| Module | Responsibility |
| --- | --- |
| `brain/business_diagnosis_engine.py` | Diagnoses business status from profile and recent topics. |
| `brain/business_insight_engine.py` | Detects missing content types and recommends next angles. |
| `brain/business_memory_engine.py` | Stores and loads business events. |
| `brain/business_os_engine.py` | Builds a current business operating state. |
| `brain/goal_engine.py` | Creates, loads, and evaluates business goals. |
| `brain/content_calendar_engine.py` | Generates a content calendar. |
| `brain/content_strategy_engine.py` | Selects content strategy by context. |
| `brain/campaign_engine.py` | Generates sales campaign ideas. |
| `brain/promotion_engine.py` | Suggests promotions. |
| `brain/sales_strategy_engine.py` | Suggests sales strategy. |
| `brain/sme_companion_engine.py` | Builds companion-level business guidance. |
| `content_engine.py` | Generates content plans, daily content, and sales briefs. |

## Conversation Brain

The Conversation Brain coordinates chat understanding, reply structure, and session continuity.

```text
User message
  |
  v
conversation_intent_engine
  |
  +-- product feedback -> Product Brain
  |
  +-- business chat -> chat_intelligence_engine -> chat_companion_engine
  |
  +-- optional LLM context -> llm_context_builder -> LLM Layer
  |
  v
response_cleaner
```

| Module | Responsibility |
| --- | --- |
| `brain/conversation_intent_engine.py` | Detects conversation intent and context requirements. |
| `brain/chat_intelligence_engine.py` | Scores and explains business chat intent using playbooks. |
| `brain/chat_companion_engine.py` | Produces companion-style chat responses. |
| `brain/llm_context_builder.py` | Builds compact context for provider calls. |
| `brain/response_cleaner.py` | Removes duplicate lines, duplicate bullets, and internal labels. |

## Product Brain

The Product Brain turns product feedback into structured learning.

```text
Chat feedback
  |
  v
product_classifier
  |
  v
product_learning_engine
  |
  +-- feedback log
  +-- backlog upsert
  +-- duplicate merge
  +-- priority assignment
  +-- trend summary
```

| Module | Responsibility |
| --- | --- |
| `feedback/product_classifier.py` | Classifies product feedback and builds records. |
| `feedback/product_priority.py` | Calculates severity and priority. |
| `feedback/product_backlog.py` | Loads, saves, deduplicates, and updates backlog issues. |
| `feedback/product_learning_engine.py` | Records feedback and prepares dashboard data. |
| `feedback/feedback_engine.py` | General feedback category and acknowledgement helpers. |
| `feedback/feedback_analyzer.py` | Summarizes feedback records. |
| `feedback/feedback_storage.py` | Stores and loads feedback JSON data. |

## LLM Layer

The LLM Layer lives in `llm/` and is optional at runtime.

```text
app.py / brain engines
  |
  v
llm_router.py
  |
  +-- deepseek_client.py
  |
  +-- openai_client.py
```

| Module | Responsibility |
| --- | --- |
| `llm/llm_router.py` | Selects provider availability and routes generation calls. |
| `llm/deepseek_client.py` | Loads DeepSeek configuration and sends DeepSeek requests. |
| `llm/openai_client.py` | Loads OpenAI configuration and sends OpenAI requests. |
| `billing/budget_guard.py` | Tracks daily and monthly LLM usage state. |

When provider keys are missing or calls fail, the app is expected to use deterministic fallback responses.

## Memory Layer

SME Companion currently uses local JSON persistence.

| Location | Responsibility |
| --- | --- |
| `memory/store_memory.py` | Store profiles, generated content history, and recent topics. |
| `memory/store_memory.json` | Local store memory data. |
| `data/business_memory.json` | Business event memory. |
| `data/business_goals.json` | Business goal storage. |
| `data/feedback/feedback_log.jsonl` | Product feedback event log when created at runtime. |
| `product_backlog.json` | Local product issue backlog. |

This is appropriate for local demos and early product learning. A production system should move durable memory and feedback into a database.

## Developer Console

The current developer console capability is embedded in the Streamlit app as feedback summary data prepared by `feedback/product_learning_engine.py`.

Planned expansion includes backlog review workflows, release readiness views, trend inspection, issue lifecycle controls, and exportable sprint summaries.

## Future APIs

Future APIs should expose stable access to:

- Store profiles and business memory.
- Business goals and operating state.
- Product feedback records.
- Product backlog issues.
- Developer summary and trend data.
- LLM provider status and usage state.

The current codebase is not yet structured as an API service; `app.py` is the main orchestration layer.

## Folder Responsibilities

| Folder | Responsibility |
| --- | --- |
| `billing/` | LLM budget and usage controls. |
| `brain/` | Business, conversation, goal, content, campaign, and insight logic. |
| `data/` | Local runtime JSON data. |
| `demo/` | Demo profiles and demo session injection. |
| `feedback/` | Product learning, feedback capture, backlog, priority, and analysis. |
| `knowledge/` | Business-type playbooks and playbook selection. |
| `llm/` | Provider clients and provider routing. |
| `memory/` | Store profile and generated content memory. |
