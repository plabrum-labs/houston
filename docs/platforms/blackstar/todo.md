# Blackstar (Ontology) — todo

The typed data model — `ent` schema + `huma` typed API — that every other platform reads and
writes through. Houston's equivalent of Foundry's Ontology: the object / link / action layer
every other tool consumes.

- Codename: Blackstar
- Source: Palantir Foundry (Ontology)

## What it is

The shared object model an app defines once in Go (`ent`) and serves as a typed OpenAPI surface
(`huma`). Other platforms — the agent, access control, analysis — consume this surface rather
than reaching into raw tables. Distinct from the data layer (`../data/`), which owns physical
isolation, RLS, roles, and migrations; Blackstar owns the *logical object model* on top of it.

## To design

- [ ] Object / link / action model: how entities, relationships, and state-changing actions are
      declared once and exposed to every consumer.
- [ ] The typed API surface as the single contract three consumers share — the app UI, the
      bundled agent, and external callers.
- [ ] Where the CRUD / schema-metadata pillar and the actions (write) pillar from snacks land.
- [ ] Relationship to the data layer: what Blackstar owns vs. what `../data/` owns.
- [ ] Object Explorer — browse / search over an app's entities. Decide: folded into Blackstar
      as a default browse/search surface, or its own platform (codename Lazarus if split).

## Open questions

- Is Object Explorer part of this platform or separate?
- How much of the frontend "default UI over the object model" belongs here vs. the app-builder
  layer.

## Source material

- Archive: `../../_archive/app-model-and-agents.md`, `../../_archive/many-backends-architecture.md`.
