# Features

Laundry list of Houston platform features, mapped against their source of inspiration (Palantir Foundry/AIP, Hex, or existing `snacks` capabilities being ported). Codenames are working names, not final product branding. Status is Accepted / Pending / Rejected — Pending means acknowledged but not yet designed, not turned down.

| Item | Codename | Source | What it does | Status |
|---|---|---|---|---|
| Ontology | Blackstar | Palantir Foundry | Typed data model (`ent` + `huma`) every other platform reads/writes through | Accepted |
| Object Explorer | Lazarus | Palantir Foundry | Browse/search an app's entities | Pending |
| Workshop / Slate | Fashion | Palantir Foundry | Schema-driven default UI, override points, full-custom escape hatch | Accepted |
| Quiver / Contour | — | Palantir Foundry | Point-and-click / no-code analysis | Rejected |
| Hex-like notebook | Moonage Daydream | Hex | notebooks publishable as standalone interactive apps | Accepted |
| Map | Ziggy | Palantir Foundry | Geospatial analysis | Pending |
| Model Studio | Sane | Palantir Foundry | No-code ML model training/deployment | Pending |
| Notepad | Heroes | Palantir Foundry | Collaborative reports embedding live data | Pending |
| AIP Logic + Chatbot Studio + Evals | Duke | Palantir AIP | Agent builder ... | Accepted |
| Apollo | Changes | Palantir Foundry | ECS runner fleet + skill-driven deploy | Rejected |
| Infrastructure layer | Diamond Dogs | Houston | app deplopyment infrastructure (pulumi) | Accepted |
| Automate | Ashes to Ashes | Palantir Foundry | Condition-triggered actions on data | Pending |
| Data Connection / Pipeline Builder | Station to Station | Palantir Foundry | Ingest/sync external data into an app's schema | Pending |
| Writeback | Station to Station (outbound) | Palantir Foundry | Sync Houston data back out to external systems — outbound counterpart to Data Connection; this is Houston's outbound/webhook mechanism | Pending |
| Marketplace | Fame | Palantir Foundry | Package/distribute reusable app templates | Pending |
| Approvals | — | Palantir Foundry (Actions-adjacent) | Human-in-the-loop sequenced approval chains (e.g. multi-step sign-off on an Action); narrowly scoped to human sequencing, not event-driven logic — that's Automate/AIP Logic's job | Pending |
| Auth / identity | Major | snacks | Identity, sessions, actor context RLS keys off; incl. SSO/SAML for enterprise customers | Accepted |
| Billing | Golden Years | snacks | Subscription/payment handling via Stripe | Accepted |
| Ledger | Cash Girl | Houston (net new) | Double-entry accounting primitive — balances, journal entries, reconciliation; not Stripe-specific, sits alongside Billing | Accepted |
| Comms | Sound and Vision | snacks | Email transport (state-machine-backed email service) | Accepted |
| Notifications | Speed of Life | Houston (core platform) | Cross-channel notification hub — unifies Comms (email) + Threads (in-app) + push, per-user preference/digest center; not yet unified in snacks (email and threads are separate, no shared preference layer) | Pending |
| Events | Five Years | snacks (promoted to core platform) | Event bus / audit log — auto-fired on CRUD/state-machine transitions today; the backbone other platforms (Automate, Approvals, Notifications, Writeback) subscribe to once built | Accepted |
| Embeddings | Starman | snacks | Vector search / semantic matching infra | Accepted |
| Form DSL | folds into Fashion | snacks | No separate surface | Accepted |
| Multi-tenancy / RLS | — | snacks | Org-scoped tenancy via Postgres RLS + session GUCs | Accepted |
| RBAC / role guards | — | snacks | `Actor[R]` protocol, role-gated route/transition guards | Accepted |
| State machine framework | — | snacks | Generic state machine w/ role-gated transitions; spine for Actions and Events | Accepted |
| CRUD / schema-metadata pillar | folds into Blackstar | snacks | Declarative list/detail endpoint factories, filtering/search/paging, OpenAPI codegen | Accepted |
| Actions (write pillar) | — | snacks | Declarative state-changing write operations, principal-gated | Accepted |
| Background jobs / task queue | — | snacks | SAQ-based scheduled/cron + on-demand jobs, RLS-aware; distinct from Automate's condition-triggered actions | Accepted |
| Media & documents | — | snacks | S3-backed media/photo upload + document model, Jinja2/WeasyPrint PDF generation | Accepted |
| Full-text / trigram search | — | snacks | `SearchMixin`, TSVECTOR + trigram indexing, search registry | Accepted |
| Threads / in-app messaging | folds into Sound and Vision | snacks | Non-email chat threads, unread counts, presence, WS broadcast; in-app channel feeding Notifications | Accepted |
| App scaffolding CLI | — | snacks | `snacks-scaffold` bootstraps new Litestar + Vite apps | Accepted |
| Infra-as-code modules | folds into Diamond Dogs | snacks | Terraform for ECS, EC2, networking, S3, Vercel | Accepted |
| Frontend component platform | — | snacks | `ResourceTable`, action dialogs, shortcuts, theming provider | Accepted |
| LLM orchestration | folds into Duke | snacks | Multi-provider (Anthropic/OpenAI/local) client, tool-calling, streaming | Accepted |
| Business sequences | — | snacks | Per-org sequential ID generator (e.g. invoice numbers) | Pending |
| Dashboards / widgets | — | snacks | User-configurable dashboards + LLM tools to manage them | Pending |
| Time-series analytics aggregation | — | snacks | `/data` endpoints for granularity/time-range aggregation | Pending |
| Feature flags | — | Houston (net new) | Per-tenant/per-app rollout flags; confirmed absent in snacks | Pending |
| Observability / APM | — | Houston (net new) | Logging, tracing, error monitoring across tenant apps; confirmed absent in snacks | Pending |


