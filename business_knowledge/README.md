# SME Business Knowledge

`business_knowledge/` is the foundation for SME Companion V4 business reasoning.
It is a static, versioned knowledge layer that teaches the platform how experienced
SME owners think before any workflow, agent, or LLM response is selected.

This layer is not a Q&A database, product documentation, or prompt collection.
It defines durable business doctrine, domain boundaries, skill structure, and
starter reasoning patterns that future engines can load and apply.

## Architecture

```text
business_knowledge/
  README.md                  Architecture and operating rules
  doctrine.md                Permanent business principles
  schema.md                  Required Business Skill schema
  domains/                   Numbered business domain namespaces
  templates/                 Reusable authoring templates
  skills/                    Loadable Business Skill templates
```

Future runtime architecture:

```text
Business Doctrine
  -> Business Skill
  -> Business Reasoning Engine
  -> Conversation Engine / Workflow Engine
  -> Natural business response
  -> Business Memory learning tags
```

## Folder Layout

- `domains/` contains the official domain catalog. Domain folders are numbered
  to keep loader order stable.
- `templates/` contains the canonical Business Skill template.
- `skills/` contains starter skill templates grouped by domain.

Domain folders use this convention:

```text
NN_domain_name
```

Skill files use this convention:

```text
NNN_skill_name.md
```

Example:

```text
skills/01_sales/001_customer_asks_price.md
```

## Doctrine

Doctrine is the constitution of SME Companion. Every Business Skill must cite
one or more doctrine items and must behave consistently with them.

Doctrine should be rare, stable, and difficult to change. If a rule is specific
to one business situation, it belongs in a Business Skill, not doctrine.

## Domains

The first domain catalog is:

1. Sales
2. Marketing
3. Customer Service
4. Pricing
5. Cost Calculation
6. Products
7. Inventory
8. Purchasing
9. Receipt OCR
10. CRM
11. Finance
12. Operations
13. Store Management
14. Promotion
15. Social Media
16. Business Analysis
17. Business Strategy
18. Customer Psychology
19. Business Growth
20. Executive Intelligence

## Skill Format

Every Business Skill must follow the schema in `schema.md` and the authoring
template in `templates/business_skill_template.md`.

Each skill teaches exactly one business principle. The principle is the business
judgment the AI should learn, not a response script.

## Versioning

The foundation starts at `v4.foundation`.

Recommended future versioning:

- Doctrine changes: increment the doctrine version and document the reason.
- Schema changes: increment the schema version and provide migration notes.
- Skill changes: update the skill revision inside the file when behavior changes.
- New domains: append a new numbered folder; do not renumber existing domains.

## Future Expansion

This layer is designed to support:

- Skill Loader: read and validate skill files by schema.
- Business Memory: use memory tags to save reusable owner and store context.
- Business Reasoning Engine: apply thinking patterns and decision trees.
- Conversation Engine: choose conversation stage, goal, and response mode.
- Workflow Engine: route skill output into deterministic workflows.
- Business Agents: specialize agents by domain without duplicating doctrine.
- Executive Intelligence: reason across domains for higher-level decisions.
- Future AI Learning: improve skills by adding observed patterns, not ad hoc prompts.

