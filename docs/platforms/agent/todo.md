# Agent — todo

Every Houston app is agent-native by construction: the app's typed API surface (see
`../blackstar/`) *is* the agent's tool surface, so an app ships with a competent agent and no
hand-authored orchestration.

- Source: Palantir AIP (Logic / Chatbot Studio / Evals)

## What it is

- Tools auto-derived from the app's typed API — adding an endpoint adds a tool for free, with no
  separate "define agent tools" step that can drift from the real endpoints.
- The agent acts as the calling user, through the same RLS / org scoping every human request
  goes through; no separate agent-permissions model.
- Model / framework-agnostic underneath — the loop drives a stable typed tool surface, so the
  model behind it is a swappable detail.
- The same tool surface exposed as an MCP server, so a customer's own agent can drive their app.

## To design

- [ ] Auto-derivation of the tool surface from the `huma` / ontology API.
- [ ] Bundled-agent packaging: how a builder "turns it on," branding, on-by-default vs opt-in.
- [ ] MCP server exposure of the same surface.
- [ ] Async agent tasks: asynq-triggered ephemeral workspace, RLS-scoped pulls into a per-task
      DuckDB workspace for local iterate / aggregate. (See archive `app-model-and-agents.md`.)
- [ ] Evals: a quality / testing framework for agent behavior.
- [ ] Model Studio (no-code model training / deployment) — decide whether it belongs in this
      platform or is a separate one. Unresolved.

## Open questions

- Is Model Studio part of the agent platform or its own thing?
- The agent-authored analysis DSL (archive `quiver-agent-dsl.md`) is deferred and may not be
  distinct from the ontology — revisit after Blackstar lands; not scaffolded yet.
- Bundled agent on by default or opt-in per app.
- Async task trigger surface: chat-initiated only, or also scheduled / cron.

## Source material

- Archive: `../../_archive/app-model-and-agents.md`, `../../_archive/quiver-agent-dsl.md`.
