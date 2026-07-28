# UI — v0

UI is Houston's frontend platform: the component library every app's interface is built from, and
the codegen that derives an app's screens from its ontology. An app declares its object model once;
UI turns that declaration into a working, themed interface — lists that filter and sort, forms that
validate, buttons for exactly the actions the current actor may perform — without anyone writing a
screen. Every line of that interface lands in the app's repo as ordinary code the builder owns and
edits.

The platform's shape follows from one constraint: **the ontology is the app's source of truth and
lives in version control, so anything derivable from it is generated rather than authored.** What
cannot be derived — visual identity, layout judgement, the screens that do not look like a list or a
form — is written by hand against components that were built to be composed.

## Four tiers

An app's frontend is four layers, distinguished by what each knows about the app:

- **Primitives** know nothing about the app. Buttons, dialogs, tables, comboboxes, inputs. They
  carry behavior, accessibility, and appearance, and are ignorant of what a `Vessel` is.
- **Ontology-aware components** know the *shape* of an app but not its content. A resource table, a
  form renderer, an action launcher. Each is generic over any entity and renders whatever
  **definition** it is handed. These are written once and shipped to every app unchanged.
- **Generated definitions** are the per-entity data the tier above consumes — this entity's columns,
  this action's fields, the registry mapping actions to their forms. Derived from the ontology,
  regenerated on every schema change, never edited.
- **Pages** compose the three tiers into routes. Hand-written, and small — a list screen is a
  generated definition, a generated data hook, and a resource table wired together.

The tiers exist so that **a schema change touches only the third**. Adding a field to an entity
regenerates one definition file; no component and no page is edited.

## Primitives

Primitives are the app's visual vocabulary and carry no platform contract. Behavior and
accessibility — focus management, keyboard interaction, ARIA semantics — are the part worth getting
right once, and they are the reason primitives are shared at all rather than rebuilt per app.

Divergence in a primitive breaks nothing shared: an app that rewrites its button affects no other
app and no backend contract. Primitives are therefore delivered **fully owned** — source copied into
the app's repo, edited freely from the moment it lands.

## Ontology-aware components

These are the platform's substance. Each is **generic over the entity it renders** and takes its
per-entity knowledge as an argument:

- **Resource table** — a list over any entity: columns, sorting, filtering, search, pagination, row
  selection, and navigation to a detail view.
- **Form renderer** — a form over any action's input: field widgets chosen by declared type,
  required-field handling, submission and error surfacing.
- **Action launcher** — the control that offers an entity's legal actions, opens the corresponding
  form, and confirms destructive ones.
- **Detail scaffolding** — an entity's fields, its related entities, and its available actions.

A component in this tier renders a definition it did not author and cannot validate against the
backend. Its correctness therefore depends entirely on the definitions it is handed being derived
from the same schema the backend enforces — which is why definitions are generated and not written.

## Generated definitions

Codegen reads the ontology's published surface and emits, per entity and per action, the definitions
the components consume: a **column definition** naming each column's key, display type, label, and
whether it sorts and filters; a **form definition** naming each field's widget, label, requirement,
and ordering; and an **action registry** mapping every action to its form and its label.

Generated files are marked as generated and are never edited. The generator runs as part of the
app's build tooling, so a schema change and its interface change land in the same commit.

**Definitions are emitted as data wherever a data representation exists.** A definition that is data
regenerates cleanly no matter how far the surrounding app has moved, which is what lets an app take
new schema and new component behavior indefinitely. Emitting rendered markup instead is reserved for
the cases where no data representation covers the output, and it is understood as a **fork point**:
the first time an app needs that output to differ, it stops regenerating that file and owns it.

## The presentation metadata contract

A typed API describes an entity's shape but not how it is presented. Codegen requires both, so the
ontology publishes **presentation metadata** alongside its typed surface: which columns filter and
sort, each column's display type and label, an entity's state machine and its states, and per action
each field's type, label, placeholder, ordering, and — where a field references another entity — the
entity it points at and the action that creates one.

This metadata is declared where the schema is declared, in the app's Go source, so a field and its
presentation cannot drift apart. It is published as a served surface, not a build artifact, so
codegen reads the same running app the frontend will call.

The contract is deliberately narrow: it carries **presentation intent**, never presentation
decisions. `filterable` is metadata; whether that renders as a dropdown or a typeahead is the
component's judgement and is not expressible in the schema.

## Theming

Theming is **fully owned**. An app's tokens — color, typography, spacing, radius, elevation — land
in its repo as editable source, and the primitives that consume them land beside them. An app's
visual identity is the least shared thing it has, and nothing in the platform reads an app's tokens,
so divergence costs nothing.

The platform ships **theme sets** as registry entries: complete, coherent token collections an app
pulls as a starting point and then edits. An app runs one theme set at a time, with a light and dark
mode.

## The gallery

The gallery is the browsable surface showing every component in every state, and it is **generated
from the registry**. Each registry entry declares the examples that demonstrate it; the gallery is
built from those declarations. A component therefore cannot ship without appearing in the gallery,
and cannot appear without shipping — the drift between a component library and its documentation is
removed by construction rather than by discipline.

It serves two readers with one artifact. A **builder** browses it to choose a component and see the
command that pulls it. **Claude** reads it as the source of truth for what exists and how each
component is composed, which is what makes generated app code use the intended component instead of
reinventing one.

The gallery generator is itself a registry primitive, so an app that has diverged pulls it and
builds a gallery of its own components under its own tokens. The published gallery shows the
registry; a vendored gallery shows the app.

## Escaping the generator

Generated output is a starting point with a defined exit. Every generated definition can be
superseded by a hand-written one of the same shape placed beside it: the app stops regenerating that
entity or action and owns the definition outright, while every other entity continues to regenerate.
The escape is **per definition**, so outgrowing the generator for one screen costs that screen and
nothing else.

Below that, a page ignores generated definitions entirely and composes ontology-aware components, or
bare primitives, by hand. There is no boundary to cross and no mode to leave — generated code,
adjusted code, and fully hand-written code are the same kind of code in the same repo.

## Seams

**Blackstar (`../../blackstar/`)** — Blackstar owns the object/link/action model and the typed API
over it, and additionally publishes the presentation metadata described above. UI consumes both and
declares neither. The dependency runs one way: an entity exists because the ontology says so, and UI
renders whatever it is told exists.

**CLI (`../../cli/`)** — The CLI delivers every tier of this platform into an app. Primitives,
ontology-aware components, theme sets, and the gallery generator are registry entries with owned
surfaces; the codegen is a pinned tool the app invokes. UI decides where each of its seams sits and
publishes the entries; the CLI owns the uniform mechanism that carries them in.

UI publishes the skills that teach an agent to use it — how to run the codegen, which component to
reach for, how to compose a page from generated definitions. The gallery is what those skills point
at. Nothing in the platform's design assumes an agent is involved; the components and the codegen
behave identically under a human.

**Auth (`../../auth/`)** — Which actions an actor may perform is enforced by the backend. UI's action
components render the permitted set the API reports and gate nothing themselves; a control the
frontend fails to hide is still refused by the backend.

## Boundaries

UI does not define what an entity is, what actions exist, or who may perform them — those are the
ontology's and access control's. It does not enforce authorization; it reflects it. It does not own
delivery, versioning, or upgrade of its own components — that is the CLI's. It does not host or serve
the built frontend. It does not own the app's routing, its data-fetching client, or its build
toolchain beyond the generators it contributes to them. It generates an interface from a declared
model and supplies the components that interface is made of — nothing above that, nothing below it.

## Not yet designed

- The definition formats themselves — the concrete shape of a column, form, and action definition,
  and how a hand-written definition declares that it supersedes a generated one.
- The registry entry format for a gallery example, and how a component declares the states it must
  demonstrate.
- Detail-view derivation: how much of an entity's detail screen is derivable from the ontology
  versus inherently a layout judgement.
- The display-type vocabulary: the closed set of column display types and form field widgets, and
  how an app adds one without forking the generator.
- Dashboards, charts, and aggregate views — presentations over query results rather than over
  entities.
- Whether an app runs more than one theme set at once, and what that would mean for owned tokens.
- The frontend client framework and build tooling this platform targets.
