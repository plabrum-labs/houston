# CLI — vision

The beliefs the CLI is designed around, held across every version. Each version's `design.md` says
what the tool *is*; this says what it is *for* and what it refuses to become.

The CLI exists because a Houston app is composed rather than authored from scratch, and because the
thing doing the composing is usually an agent. Those two facts set every constraint below.

## The primary builder is Claude, running locally

Houston's app-building interface is Claude Code on the builder's own machine — not a hosted web IDE,
not a dashboard, not a visual builder. This is a deliberate departure from how comparable platforms
work, and it is the assumption the CLI is shaped by.

An agent uses a tool differently from a human. It cannot see a spinner, cannot answer a prompt it
did not anticipate, and cannot recover from a half-finished interactive session. So every CLI
capability is **non-interactive first**: it takes a declarative input, runs to completion, and
reports what it did. Interactive modes exist for humans, and they are ways of producing that same
declarative input — never a separate path with capabilities of its own.

A tool built this way is also better for humans. A config that an agent can write is a config a
human can commit, diff, review, and regenerate.

## One substrate, no low-code layer

There is no independent DSL that compiles to an app, and no visual layer that generates code the
builder is not expected to read. A Houston app is ordinary code in ordinary languages, made
ergonomic by conventions and by good primitives.

The consequence is that **writing declarative-feeling app code and writing fully custom code are the
same activity at different points on one spectrum**. There is no "easy mode" to graduate out of and
no wall to hit — the next thing the convenient shape cannot express is just the next line in the
same file. Everything the CLI delivers lands as source the builder can read and change, because the
moment a builder cannot follow what they were given, the spectrum has a wall in it.

This is why the CLI writes code into a repo instead of hiding it behind an abstraction, and why
owned source is owned outright rather than managed on the builder's behalf.

## Iteration is the builder's cost, not Houston's

A builder describes an app and iterates on it entirely on their own machine, at their own agent
cost. Houston's compute is touched only by the deployed artifact — never by the trial and error of
getting there.

This is a deliberate cost-structure bet against platforms where every iteration cycle is the
platform's bill. It holds only if the CLI stays a local tool: no build service, no remote
resolution step, no round trip to Houston to scaffold or pull. The moment iteration requires
Houston, the economics invert.

The tension this creates is real and unresolved: iteration is genuinely free for pure application
logic, but anything touching identity, tenancy, or billing needs *something* prod-like to behave
against. Whatever answers that has to preserve the property above.

## Skills belong to the platform they drive

Claude knows how to use the CLI because skills encode its conventions. Those skills are documentation
of an interface, so each one belongs to the platform whose interface it documents — scaffolding with
the CLI, deployment with the fleet, component work with the frontend.

No platform owns "the skills." A layer that collected every platform's agent interface would own a
slice of each of them and could not be understood on its own.

## What this asks of the CLI

- Every capability is reachable without a human at the keyboard.
- Declarative input is the real interface; prompts are a way of writing it.
- Output is source in the builder's repo, readable and editable, never a managed artifact.
- Nothing it does requires Houston to be reachable.
- Failure is legible to a caller that cannot see the screen.
