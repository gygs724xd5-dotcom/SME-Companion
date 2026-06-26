# Changelog

All notable changes to SME Companion are documented here.

This project uses semantic product milestones alongside release-candidate entries. Versions are ordered chronologically from the earliest documented milestone to the current foundation release.

## [2.0.0] - Product Brain Foundation

### Added

- Product Brain foundation for converting user feedback into structured product learning.
- Product backlog support through `product_backlog.json` and feedback backlog helpers.
- Duplicate issue detection and issue upsert behavior for repeated product feedback.
- Priority and severity support for product issues.
- Aggregated developer-facing feedback summary data.

### Impact

- SME Companion can now learn from how users describe problems, confusion, missing features, and product requests inside normal chat.
- The project has a path from raw feedback to product backlog intelligence.

## [1.9.6] - Conversation Memory

### Added

- Conversation state helpers for current chat sessions.
- Business context synchronization from user messages.
- Correction and reset handling for conversation flow.
- Recent chat context helpers and assistant footer handling.

### Impact

- The assistant can respond with better continuity inside a session.
- Business profile and conversation context can influence follow-up responses more naturally.

## [1.9.5] - Product Learning Engine

### Added

- `PRODUCT_FEEDBACK` intent for natural Thai feedback inside chat.
- Local JSONL product feedback storage at `data/feedback/feedback_log.jsonl`.
- Thai feedback acknowledgement without requiring an LLM call.
- Product feedback classification, summarization, priority assignment, and backlog update support.
- Developer feedback summary inside the Streamlit app.

### Impact

- Users can report product problems and feature requests directly in normal language.
- Developers can review product learning signals without manually reading every chat.

## [1.9.0] - Conversation Intelligence

### Added

- Conversation intent detection for business and non-business chat modes.
- Chat companion response engine with business-context-aware answers.
- Chat intelligence engine with store playbook routing.
- Response cleaning and Thai localization helpers.
- Business insight display support from chat and content history.

### Impact

- SME Companion moved from static content generation toward a guided business conversation experience.
- Chat responses became more grounded in store type, recent topics, business profile, and known playbooks.

## [1.8.x] - RC Series

### Added

- Release-candidate validation across demo readiness, UX copy, AI conversation behavior, reliability, budget guard behavior, and deployment readiness.
- Fallback behavior for missing provider keys, provider errors, and budget exhaustion.
- Demo guard behavior to reduce accidental overuse during public demos.

### Impact

- The app became safer to show publicly and easier to test before deployment.
- Demo reliability became a first-class product requirement.

## [1.7.0] - Interactive Demo

### Added

- Six demo stores for Thai SME scenarios: coffee shop, restaurant, clothing store, beauty store, construction materials, and online store.
- Landing flow for selecting demo stores or entering manual store setup.
- Thai UX polish across demo cards, banners, welcome messages, content labels, and reliability messages.
- LLM provider layer for OpenAI and DeepSeek-backed responses with deterministic fallback.
- DeepSeek demo chat path for demo mode.
- Daily and monthly budget guard for LLM usage.

### Impact

- SME Companion became usable as an interactive demo instead of only a local prototype.
- Business owners and testers could quickly experience realistic SME scenarios without manual setup.
