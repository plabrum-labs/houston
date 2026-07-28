# CLI — v0

The CLI is Houston's build-time tool. It does two things: **creates a new app**, and **pulls shared
code into an existing one**. Both are the same operation underneath — resolving names in a registry
and writing source into a repo — which is why they are one tool rather than a scaffolder and a
package manager.

The CLI runs on the builder's machine and touches no Houston infrastructure. It reads a registry and
writes files. Everything it produces is ordinary source in the app's repo from the moment it lands.

## Owned over pinned

Everything the CLI delivers arrives as **owned code sitting on a pinned core**:

- **Owned.** Source copied into the app's repo. The app owns it and edits it freely; its divergence
  affects no other app.
- **Pinned.** Upstream behavior the app depends on and does not edit, resolved as a normal package
  dependency. Uniformity is the point — the platform and every other app rely on its shape.

These are not two catalogs. Every registry entry places a **seam** between a pinned core and an
owned surface, and what defines an entry is *where it puts that seam*. An entry with no owned
surface is simply a dependency; an entry with no pinned core is simply source.

What pushes an entry toward pinned is one question: **would an app's divergence break a contract the
platform or other apps rely on.** Frontend components sit almost entirely owned — an app rewriting
its own table breaks nothing shared. Shared data models sit entirely pinned — an app editing them is
exactly the drift the seam exists to prevent. Each publishing platform decides where its own seam
falls; the CLI owns what owned and pinned *mean* and how they reach an app.

## The registry

The registry is the catalog the CLI resolves against. An **entry** is a named unit declaring the
source files making up its owned surface, the packages making up its pinned core, and the entries it
composes.

The registry is **ecosystem-agnostic**. Houston apps are Go on the server and TypeScript in the
browser, and a single app pulls from both, so an entry declares which ecosystem its pinned core
resolves in and where in the repo its owned source lands. The CLI delegates dependency installation
to the native package manager for that ecosystem and performs the file copy itself. Nothing about
the owned/pinned seam is language-specific — copying source and resolving a version are the same
operations either way.

The registry is the source of truth for how shared code fits together.

## Pulling

Pulling an entry resolves it, installs its pinned core, and writes its owned source into the app.
From that moment the source is the app's own file — indistinguishable from anything the builder
wrote, editable without ceremony, and reviewed through the app's own version control.

**Pulling is a write, and the CLI is stateless with respect to the app.** It records nothing about
what was pulled, keeps no manifest, and never reads back what it wrote. An app's history of what it
took and how it changed it is the app's version control, which already tracks exactly that.

Re-pulling an entry writes the current source over the destination. An app that has edited that
source reviews the result as a diff in its own repo — the same review it would give any other change
to its own files.

## Scaffolding

Creating a new app is pulling a **baseline set** of entries into an empty repo, plus the project
structure that holds them — module definitions, build configuration, and the wiring that makes the
pulled entries into a running app. An app therefore starts already composed from the same entries
every other app is built from, rather than from a template that drifts from the registry.

Scaffolding has **two front doors over one core**:

- **A config.** A declarative description of the app to create — its name, which capabilities it
  wants, which theme, which ecosystem targets. This is the real input, and it is a file, so it can
  be written by hand, committed, diffed, and regenerated.
- **Interactive prompts.** A guided sequence that asks the same questions and produces the same
  config, for a builder who does not yet know what to write.

Interactive mode is a way to author a config, not a separate path — it resolves through the same
core, so an interactive run and a config run with the same answers produce the same app.

**The config is what makes scaffolding agent-drivable.** Houston's authoring loop is Claude running
locally, and an agent describing an app as a config it pipes in is a far more reliable interface
than an agent driving an interactive prompt sequence. Config-first is not a convenience; it is what
lets the primary builder interface use the tool at all.

## Seams

**UI (`../../ui/`)** — UI publishes the component library, its theme sets, and its codegen into the
registry, and declares where its seam falls: components fully owned, codegen pinned. The CLI carries
them. It never opens a component to understand it — it copies files and resolves versions.

**The capability platforms** (`../../auth/`, `../../billing/`, `../../data/`, and the rest) — each
publishes its primitives as registry entries and decides its own seam. The CLI is the single uniform
way every one of them reaches an app, which is what makes every Houston app compose the platform the
same way.

**Agents** — Scaffolding an app is an agent piping a config; adding a capability is an agent
invoking a pull. The CLI publishes the skills that teach this, and its non-interactive interface is
what makes them reliable. It has no agent-specific mode — an agent and a human drive the same tool
the same way.

**Launchpad (`../../launchpad/`)** — Deployment is not the CLI's. The CLI composes an app in a repo;
shipping that app to the fleet is a separate seam.

## Boundaries

The CLI does not define what any entry *does* — each publishing platform owns its primitive's
behavior and its pinned contract. It does not provision or run infrastructure, deploy anything, hold
application data, or execute application logic. It does not read or validate the source it copies.

**It does not manage owned source over time.** It runs no merge, resolves no conflict, and holds no
record of what an app pulled or how far that has since diverged. Owned source is the app's, and the
app's version control is already a complete answer to what changed and when — a second one inside
the CLI would duplicate it and disagree with it.

It resolves names against a registry and writes files into a repo with a clear line between what the
app owns and what stays pinned — nothing above that, nothing below it.

## Not yet designed

- **Registry hosting and distribution** — where the registry lives, whether entries are public, and
  how an entry is published.
- The config format for scaffolding, and how it names capabilities.
- **What a scaffolded app runs against locally.** Application logic iterates with nothing behind it,
  but identity, tenancy, and billing need something prod-like to behave against — and whatever
  provides it has to keep local iteration free of Houston.
- **How each platform's skills are packaged and installed.** Skills belong to the platform they
  document, but a builder installs the whole Houston surface in one step.
- What a pull does when an entry composes other entries — whether the CLI follows that graph or the
  entry lists its siblings for the caller to pull.
- Whether an app can publish private entries into its own registry scope.
