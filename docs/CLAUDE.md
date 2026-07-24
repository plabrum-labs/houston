# Working in docs/

This directory is Houston's design record. It has four areas, each with a distinct job. Before writing or editing anything here, know which area you're in and follow its rules — and always follow the authoring rules that apply everywhere.

## The four areas

| Area | What it is | What goes in it |
|---|---|---|
| **[vision/](vision/)** | Ideation and the pitch. | Thoughts and ideas about what Houston should do, what could be built on it, and how it's positioned. Exploratory and forward-looking — this is where ideas live before they become specs. |
| **[platforms/](platforms/)** | Design and implementation for the things we build. | One folder per platform, versioned (`v0`, `v1`, …). Each version is a **directory** holding a `design.md` (the platform at architecture altitude) and an `implementation.md` (the named, independently-buildable slices that realize that design). See the `houston-docs` skill for the full template. |
| **[planning/](planning/)** | Sequencing. | Which platforms and which versions come together toward a concrete deliverable, and in what order. Planning references specific platform versions; it doesn't restate their specs. |
| **[research/](research/)** | Architectural reference. | What comparable companies offer and how they solved things — source material we draw on when designing. Facts about other products, not Houston design. |

The natural flow is vision → platform spec → planning, but these are areas, not gates. An idea in `vision/` becomes a spec in `platforms/` when we're ready to build it; a set of platform versions gets pulled together in `planning/` when we're aiming at a deliverable; `research/` is drawn on throughout.

## Authoring rules (everywhere)

1. **Describe the intended state, in the present tense.** A platform spec reads as a description of the thing to be built — not the conversation that produced it.

2. **Never reference previous ideas.** No "previously," no "we used to," no "instead of X," no "superseded by," no changelogs, no notes on what a doc used to say. When direction changes, rewrite the doc so it cleanly describes the new intent — or, for a platform, cut a new version. The old thinking simply isn't there.

3. **Don't track decisions or opinions.** No decision logs, no "rejected alternatives," no "options considered," no Accepted/Pending/Rejected status, no gates. If something is the design, state it as the design.

4. **Each doc stands on its own.** A reader should understand it without needing the history of how it came to be. Cross-reference other current docs by what they describe, not by the discussion that shaped them.

5. **Lead with the conclusion (BLUF).** Every doc opens by stating what it is; every section states its point before elaborating. A reader should grasp the shape from the opening and the headings alone, and never have to reach the end to discover the conclusion.

## Versioning platforms

- Each platform is a folder: `platforms/<name>/`. Its versions are **directories** inside it — `v0/`, `v1/`, `v2/`, …
- Each version directory holds two files: `design.md` (the platform's shape at architecture altitude) and `implementation.md` (the named, independently-buildable slices that realize that design). The `houston-docs` skill defines the structure of each.
- Start every platform at `v0`. Later stages are `v1`, `v2`, …
- Each version is a **full standalone picture** of the platform at that stage — not a diff against the version before it, and it never refers to the version before it.
- `planning/` sequences versions *across* platforms into a deliverable; `implementation.md` sequences the build *within* one version. Same verb, different scope — they don't overlap.
