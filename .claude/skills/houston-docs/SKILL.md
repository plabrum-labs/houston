---
name: houston-docs
description: >
  Structure and altitude rules for authoring Houston's design record under docs/ — especially
  platform docs (design.md and implementation.md), plus vision/ and planning/. Use whenever
  writing or editing anything in docs/: creating a new platform version, filling in a design or
  implementation, converting a todo stub, or restructuring an existing doc. Carries the templates
  and the design↔implementation altitude discipline that docs/CLAUDE.md points to.
---

# Authoring Houston docs

Read `docs/CLAUDE.md` first — it holds the everywhere-rules (present tense, no history, no decision
logs, each doc stands alone, BLUF) and the four-area map. This skill adds the *structure* those
rules are applied within. Everything here obeys those rules; nothing here overrides them.

## The altitude ladder

Three doc kinds are the **same subject at increasing resolution**, and each assumes the one above it
is settled and refuses to re-argue it. A fourth thing, planning, is not an altitude — it's a
schedule that cuts across the ladder.

| Kind | Answers | Altitude | Lives in |
|---|---|---|---|
| **Vision** | What future are we creating; what principles guide decisions? | Principles | `vision/` |
| **Design** | What is this platform and how is it shaped? | Architecture | `platforms/<name>/vN/design.md` |
| **Implementation** | How, concretely, is this design built? | Build | `platforms/<name>/vN/implementation.md` |
| **Planning** | Which versions combine into a deliverable, in what order? | Schedule (cross-cut) | `planning/` |

`research/` is external reference material (what comparable companies do) that feeds Design. It is
orthogonal to the ladder.

Decision rationale — "why Pulumi over Terraform," alternatives rejected — has **no home** in `docs/`
by deliberate choice (everywhere-rule 3). Don't add one.

## Platform layout

```
platforms/<name>/
  v0/
    design.md
    implementation.md
  v1/
    design.md
    implementation.md
```

Each `vN/` is a full standalone picture of the platform at that stage — never a diff against `v(N-1)`
and never a reference to it. A platform matures **in place** by filling sections, not by switching
templates: an early platform is just a `v0/design.md` with a strong opening and a short
`## Not yet designed` tail, and `implementation.md` may be absent until the platform is actually built.

## design.md — architecture altitude

The platform's shape: its concepts, invariants, seams, and boundaries. A peer engineer should
understand the system without building it. Structure:

```
# <Platform> — v<N>

<Purpose — the opening, walled off at product altitude, no mechanism.>
What it is, the problem it solves, where it sits in the fleet. This is the BLUF. A reader who only
needs the shape stops here.

## <topic sections — the design, one per major moving part>
Lead with the concept, then its mechanism *in principle*. Topic-coherent: an idea and the detail
that grounds it stay together.

## Seams
One subsection per neighbouring platform: who owns what across the boundary, and which way the
dependency runs.

## Boundaries
The negative space — what this platform explicitly does NOT own. This is the strongest, most load-
bearing section; every platform has one.

## Cost profile        (optional — only where it earns its place)

## Not yet designed     (early versions only — delete as sections fill in)
- bullets for what's still open
```

**Altitude discipline — the one rule that keeps design and implementation from re-blurring:**
`design.md` stays present-tense architecture. Concrete detail (exact schemas, state transitions,
retry constants, tech choices, `SIGTERM`/`SIGKILL`, cgroups) is **illustrative only** — allowed as a
single snippet where the detail *is* the argument (e.g. an RLS `USING (...)` clause that carries the
security model). Everything *exhaustive* lives one altitude down, in `implementation.md`.

## implementation.md — build altitude

A single file of numbered, build-ordered steps that realize `design.md`. Each step is an
**independently-buildable slice** — the unit that later becomes a ticket or PR.

```
# <Platform> — v<N> implementation

<One-line BLUF: what building this version entails.>

## Step 1 — <slice>
Implements: <the design.md section this realizes>

<The exhaustive detail: schemas, state machines, interfaces, retry/concurrency, error handling,
tech choices, deployment workflow. This is where premature-in-a-spec detail belongs.>

## Step 2 — <slice>
Implements: <design section>
...
```

Conventions:
- **Numbering is build order**, not just enumeration. Number sparsely if you expect inserts (`10, 20, 30`) or accept the occasional renumber.
- **Every step names the design section it implements** (`Implements: …`). This makes steps traceable and surfaces two defects: a design section no step covers (a gap), and a step mapping to nothing in the design (scope creep).
- **Keep it one file.** `## Step N — <slice>` sections, not a directory of files — a platform's build fits in one document.
- Steps sequence the build *within this version*. Sequencing *across* platforms toward a deliverable is `planning/`'s job, not this file's.

## Voice, content, and length

These apply to `design.md` above all, but the voice carries across every doc under `docs/`.

**Voice.**
- Present tense, declarative — describe the built thing as if it exists ("The control plane maps each request by Host header").
- Third person. No "we", "you", "I" — the platform and its parts are the subjects.
- Assert the design as fact. No hedging ("might", "probably", "we think"), no future-tense roadmap-in-prose.
- Bold the load-bearing nouns and invariants on first definition (**Owned**, **Pinned**, **Routing**).

**What goes in.**
- Lead with identity: "*<Platform> is Houston's <role>.*"
- The concepts and invariants a peer needs to reason about the system, plus its seams and boundaries.
- The *why*, woven inline and compressed — justify a choice in the same sentence that states it ("Because it is `SECURITY DEFINER`, the `_runtime` role needs no grant…"), never in a separate rationale section.

**What to cut.**
- History, alternatives, decisions, roadmaps (the everywhere-rules).
- Exhaustive implementation detail — that belongs in `implementation.md`.
- Meta-commentary about the doc, hedging, filler. If a reader could delete a sentence without losing the intended state, cut it.

**Length.** No target and no ceiling — as long as the platform's complexity demands and no longer, with a firm bias toward concise. Density over volume. Use length as a smell test: if a `design.md` is growing because of concrete mechanism, that detail belongs in `implementation.md` — length is leaking altitude, not tracking genuine complexity.

## vision/ and planning/

- **vision/** — beliefs and direction. BLUF, then thesis/principles. Prescribes no mechanism, selects no technology, defines no APIs. Rare — platform/product-line/company scope only.
- **planning/** — sequencing. Which platform *versions* assemble into a deliverable and in what order. References design versions by what they describe; restates none of their content.

## Quick checklist before you commit a doc

- Opens with a BLUF; understandable from opening + headings alone.
- Present tense, third person, declarative; no hedging; load-bearing terms bolded on first use.
- No history, no decision log, no "previously/superseded" (everywhere-rules).
- Concise — no sentence a reader could delete without losing the intended state; length not leaking implementation detail up from `implementation.md`.
- `design.md`: has Boundaries; detail is illustrative only, not exhaustive.
- `implementation.md`: steps are build-ordered and each carries an `Implements:` back-reference.
- Nothing exhaustive leaked up into `design.md`; nothing re-argues the design down in `implementation.md`.
