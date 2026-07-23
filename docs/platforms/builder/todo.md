# Builder — todo

The Claude Code plugin and Houston skills a builder runs locally to scaffold and iterate on an
app. Claude Code + Houston skills, run on the builder's own machine, is the primary interface for
constructing a Houston app — not a hosted web IDE or dashboard.

- Source: Foundry (Workshop / Slate)

## What it is

- **One substrate, not a separate low-code layer.** There is no independent DSL that compiles to
  code. A Houston app is idiomatic Go + `ent` schema + `huma` handlers, made ergonomic through
  `snacks-go` conventions (form / workflow helpers, auth / billing helpers, agent-tool
  registration). Writing declarative-feeling app code and writing fully custom code are the same
  activity at different points on one spectrum, so there is no wall between "easy mode" and "real
  code" — the next thing the low-code shape can't express is just the next line in the same repo.
- **Skills teach Claude the conventions.** A catalog of Houston skills (`bootstrap-app` and
  siblings such as `add-form`, `add-workflow`, `add-agent-tool`) encodes how a Houston app is
  idiomatically structured, so Claude writes consistent, platform-compatible code whether the human
  never reads a diff or reviews and extends every line.
- **Iteration is local and cheap for the builder, not Houston.** A builder describes an app and
  Claude scaffolds and iterates entirely on the builder's machine at the builder's own Claude usage
  cost. Houston compute is touched only by the final deployed artifact — not by the trial-and-error
  of getting there.
- **A `deploy` skill is the seam to the fleet.** Deploy provisions schema / subdomain / billing and
  ships to the runner fleet once the builder is ready, rather than every iteration cycle hitting
  Houston infra.
- **Packaged as an installable plugin / MCP.** The skill suite is distributed as a Claude plugin so
  a builder installs the whole Houston builder surface in one step and drives it from local Claude
  Code.

## To design

- [ ] Skill catalog: the set beyond `bootstrap-app` (`add-form`, `add-workflow`, `add-agent-tool`,
      `deploy`) and what each encodes.
- [ ] SDK ergonomics — the real design work: which `snacks-go` conventions make code feel
      declarative enough that Claude reliably writes idiomatic apps instead of reinventing patterns
      per app (good defaults, strong typing, codegen for boilerplate).
- [ ] Plugin / MCP packaging and distribution of the skill suite as one installable surface.
- [ ] The `deploy` skill's seam with Launchpad (`../launchpad/`) placement and Snacks
      (`../snacks/`) registry pulls — what deploy provisions vs. what the app already composed
      locally.
- [ ] Local dev backing service for iteration that touches auth / RLS / multi-tenant orgs /
      billing, which need *something* prod-like to behave against.

## Open questions

- Local dev backing service: a shared low-cost dev Houston instance, a local Docker Postgres + RLS
  harness, or something else.
- Whether the SDK conventions are ergonomic enough for reliably idiomatic generated code — where
  the composability risk actually lives.

## Seam with neighbours

- **Snacks (`../snacks/`)** is the registry + CLI that delivers owned / pinned primitives into the
  app's repo. Builder is the Claude-driven authoring layer above it: skills drive the snacks CLI and
  the capability platforms to compose and extend an app.
- **Agent (`../agent/`)** is the *runtime* agent-native behavior of a deployed app (auto-derived
  tools, MCP exposure of the app's own API). Builder is the *build-time* toolchain that produces the
  app in the first place.

## Source material

- Archive: `../../_archive/app-model-and-agents.md` (App-building model / Builder experience
  sections).
