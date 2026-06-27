# Architecture

## Current Runtime Pipeline

```text
User
  -> Conversation Understanding
  -> Conversation Intelligence
  -> Intent Resolver
  -> Planner
  -> Task Router
  -> Workflow
  -> Reasoning
  -> Response Intelligence
  -> Response Guard
  -> UI
```

## Architectural Decision: Planner-First Responses

The response layer must read planner and intent resolution output before generic chat. High-confidence plans that need information must ask for the specific missing field instead of returning generic fallback copy.

Implemented extension:

- `brain.response_intelligence_engine`
- planner output now includes `workflow`
- `app.py` syncs route intelligence back to session/application state
- final response guard replaces generic or repetitive responses when planner state can answer

## Security Architecture

Manual store data is scoped by authenticated owner id.

- `memory.auth` stores local owner credentials with salted PBKDF2 hashes.
- `memory.store_profile_storage` supports owner-scoped store files.
- Anonymous sessions cannot restore legacy `active_store.json`.

This is a local production foundation, not the final public-cloud auth system.

## OCR / Inventory Boundary

`brain.inventory_engine` defines document and stock movement foundations. OCR status starts as `pending_external_ocr`; no fake OCR is generated.

## Translation Boundary

`brain.translation_engine` creates provider-ready translation requests for Thai, English, Arabic, and Chinese across chat, PDF, invoice, and product description surfaces.
