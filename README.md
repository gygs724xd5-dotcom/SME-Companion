# SME Companion

SME Companion is a Streamlit business companion for Thai small and medium-sized business owners. It helps owners describe their store, explore demo businesses, generate practical content ideas, receive business guidance, and capture product feedback from normal chat conversations.

The project combines deterministic local business engines with an optional LLM layer. It can run without provider keys using fallback responses, while OpenAI or DeepSeek can be enabled for richer assistant replies.

## Vision

SME Companion is designed to become a lightweight business brain for SME owners: a system that remembers the business context, understands conversations, learns from product feedback, and eventually helps operators make better daily decisions.

Read the long-term product vision in [VISION.md](VISION.md) and the delivery plan in [ROADMAP.md](ROADMAP.md).

## Key Features

| Area | Current capability |
| --- | --- |
| Interactive demo | Six demo store profiles for coffee, restaurant, clothing, beauty, construction materials, and online store scenarios. |
| Business companion | Store profile setup, business diagnosis, insights, content suggestions, promotion ideas, sales strategy, and campaign planning. |
| Conversation intelligence | Chat intent detection, business context handling, response cleaning, follow-up handling, and conversation memory within the session. |
| Product learning | Natural-language product feedback detection, local feedback log, product backlog upsert, priority assignment, duplicate merging, trend summaries, and developer feedback summary. |
| LLM routing | Provider selection for DeepSeek or OpenAI with deterministic fallback behavior. |
| Cost guard | Daily and monthly LLM usage tracking for demo reliability and budget control. |
| Local memory | JSON-based store memory, business memory, business goals, feedback logs, and backlog data. |

## Architecture Overview

SME Companion is organized around several cooperating layers:

```text
Streamlit UI (app.py)
  |
  +-- Business Brain
  |     business diagnosis, insights, goals, content, campaigns, sales strategy
  |
  +-- Conversation Brain
  |     intent detection, chat guidance, context updates, response cleanup
  |
  +-- Product Brain
  |     product feedback classification, backlog, priority, trend summaries
  |
  +-- LLM Layer
  |     provider router, DeepSeek client, OpenAI client, fallback behavior
  |
  +-- Memory Layer
        local JSON store profiles, business events, goals, feedback, backlog
```

For a fuller technical description, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Folder Structure

```text
SMEContentAI/
  app.py                         Streamlit application entry point
  content_engine.py              Content plan and sales brief helpers
  billing/                       LLM usage and budget guard
  brain/                         Business, conversation, content, goal, and insight engines
  data/                          Local JSON memory and goal data
  demo/                          Demo store JSON files and demo loader
  feedback/                      Product feedback, backlog, priority, and analysis modules
  knowledge/                     Store-type playbooks and playbook router
  llm/                           DeepSeek, OpenAI, and provider routing
  memory/                        Store profile and generated content memory
  README.md                      Project overview
  CHANGELOG.md                   Semantic release history
  ROADMAP.md                     Product phases and expected outcomes
  VISION.md                      Long-term vision
  ARCHITECTURE.md                Technical architecture
  SPRINT_HISTORY.md              Chronological sprint record
  CONTRIBUTING.md                Developer workflow
```

## Local Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Create a local environment file:

```bash
cp .env.example .env
```

3. Add provider keys if LLM-backed responses are needed:

```bash
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
```

4. Run the app:

```bash
streamlit run app.py
```

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `APP_ENV` | No | Marks the runtime environment, for example `development`. |
| `LLM_PROVIDER` | No | Selects the default provider. Current example value: `deepseek`. |
| `DEEPSEEK_API_KEY` | No | Enables DeepSeek-backed LLM responses. |
| `DEEPSEEK_MODEL` | No | Overrides the DeepSeek model. Example: `deepseek-v4-flash`. |
| `OPENAI_API_KEY` | No | Enables OpenAI-backed LLM responses. |
| `OPENAI_MODEL` | No | Overrides the OpenAI model when configured. |

The application is expected to continue operating with deterministic fallback responses when provider keys are absent or provider calls fail.

## Persistent Store Profile

Manual store profiles are saved locally as UTF-8 JSON at:

```text
data/store_profile/active_store.json
```

This persistence is intentionally simple for V2.3.1. It keeps the active manual store profile, business memory snapshot, goals, diagnosis, Business OS state, and knowledge-layer data available across browser refreshes, Streamlit reruns, and app reloads. Demo stores are isolated and are not written to this file.

The local JSON file does not store API keys. Streamlit Cloud local filesystem storage may not be permanent across redeploys, restarts, or environment changes. A production version should move this profile persistence to a database with user authentication and account-level ownership.

## Streamlit Deployment

1. Push the repository to the deployment branch.
2. Configure the Streamlit app entry point as:

```text
app.py
```

3. Add required secrets in Streamlit Cloud:

```toml
DEEPSEEK_API_KEY = "..."
OPENAI_API_KEY = "..."
```

4. Add optional model/provider settings if needed:

```toml
DEEPSEEK_MODEL = "deepseek-v4-flash"
OPENAI_MODEL = "gpt-4.1-mini"
LLM_PROVIDER = "deepseek"
APP_ENV = "production"
```

5. Smoke test demo store selection, chat, fallback behavior, product feedback capture, and developer feedback summary.

## Screenshots

Screenshots should be added as the UI stabilizes:

| Screen | Placeholder |
| --- | --- |
| Demo store selector | `docs/screenshots/demo-store-selector.png` |
| Business dashboard | `docs/screenshots/business-dashboard.png` |
| Chat companion | `docs/screenshots/chat-companion.png` |
| Developer feedback summary | `docs/screenshots/developer-feedback-summary.png` |

## Development Workflow

1. Create a focused branch for each sprint or fix.
2. Keep runtime changes separate from documentation-only work.
3. Run the Streamlit app locally before deployment.
4. Check that demo stores still load.
5. Check that chat works with and without provider keys.
6. Review local JSON writes for memory, goals, feedback, and backlog behavior.
7. Update [CHANGELOG.md](CHANGELOG.md), [ROADMAP.md](ROADMAP.md), or [SPRINT_HISTORY.md](SPRINT_HISTORY.md) when a sprint changes product behavior.

## Current Version

Current documented product version: **V2.0 Product Brain Foundation**.

V2.0 represents the foundation for a product brain: product feedback can be detected from chat, classified, stored, prioritized, merged into a backlog, and summarized for developer review.

## Future Roadmap

The future roadmap is maintained in [ROADMAP.md](ROADMAP.md).
