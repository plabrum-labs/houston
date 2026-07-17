# Budibase

**What it is:** Open-source low-code platform for internal apps, portals, and automations, with a built-in relational database and an automation engine, self-hostable.
**Axis:** app-builder, workflow, agent.
**Depth:** thin — docs, GitHub, and vendor blog only.

## Products & surfaces

| Product | What it is |
|---|---|
| **Budibase Apps** | Grid-based drag-drop UI builder over a built-in DB or external connectors (Postgres/MySQL/Mongo/REST/GraphQL/Google Sheets/Airtable). |
| **Automations** | Trigger-based workflow engine (20+ triggers including webhook/cron), including AI-assisted steps. |
| **Agents (2026)** | Multiple scoped AI agents, each restricted to a chosen subset of data/APIs, dispatched via a chat router. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Built-in DB + external connectors, same builder | No separate "internal tool DB" product; internal data model lives alongside external connections | maybe |
| Scoped multi-agent chat router | Each agent restricted to specific data/APIs; a router decides which agent handles a request | yes |
| Model-agnostic via LiteLLM | Any OpenAI-format-compatible LLM can back the automation/agent layer | maybe |

## Worth stealing

**Per-agent data/API scoping as the access-control primitive for AI.** Budibase's 2026 direction is multiple specialized agents, each with access only to the data and APIs an admin explicitly grants, with a chat interface routing a request to the right agent. This is a coarser-grained but simpler version of the "AI sees only what it's scoped to" principle also seen in Retool (schema-only context, see `retool.md`) — here the scoping unit is the whole agent, not the individual context fetch.

## Worth avoiding

Not independently verified; no confirmed cautionary mechanism for this file at current research depth.

## Facts & figures

- Automation engine: 20+ documented trigger types (vendor-reported).
- 2026 roadmap: multi-agent chat routing, LiteLLM-based model agnosticism (vendor blog, forward-looking — treat as roadmap, not shipped fact, unless separately confirmed).

## Sources

- [Budibase](https://budibase.com/) · [GitHub](https://github.com/budibase/budibase)
- [Budibase 2026 – the AI Workflow Toolkit](https://budibase.com/blog/updates/future-of-budibase-2026/) — vendor roadmap post, dates/claims not independently confirmed as shipped
- **Not directly verified:** whether the multi-agent chat router described in the 2026 post has shipped vs. remains roadmap at time of writing.
