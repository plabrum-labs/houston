# Deepnote

**What it is:** A Jupyter-compatible cloud notebook with a fully autonomous "Auto AI" agent mode and an open block-schema package underlying its no-code cells.
**Axis:** app-builder, analysis, agent.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Deepnote notebook** | Cloud notebook, Python/R/SQL, drop-in Jupyter-compatible, real-time collaboration. |
| **Deepnote Agent / Auto AI** | Autonomous agent mode that writes, executes, and self-corrects blocks until a task completes. |
| **Deepnote apps** | Deployable data apps built from notebook blocks. |
| **`@deepnote/blocks`, `@deepnote/convert`, `@deepnote/database-integrations`** | Open-source npm packages: block schema/validation, notebook format conversion, and DB integration code. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Auto AI autonomous loop | Agent adds blocks, executes them, reads the outputs, and iterates/self-corrects until the task is done — including starting the machine and fixing its own errors | yes |
| Runs without user presence | Once started, Auto AI continues executing even if the user closes the notebook; user can interrupt/stop at any time | maybe |
| Open block schema (`@deepnote/blocks`) | Block types (SQL, chart, input, etc.) are defined and validated by a published, open package rather than a private internal format | yes |

## Worth stealing

**Auto AI's loop is read-execute-adapt, not generate-once.** The documented mechanism: the agent adds a block, **executes it**, reads the actual output, and uses that output as context for the next block it generates — including blocks it generated itself earlier in the same run. This closes the loop that most "AI writes code" features leave open (generate code, hope it's right, human debugs). Deepnote's framing is that it will "start up your machine, fix its own errors, and basically do anything else it needs" to finish the notebook, unattended, continuing to run even if the user closes the tab.

**Block schema as a public package, not a private format.** `@deepnote/blocks` defines and validates every block type (SQL, chart, input, etc.) and is published as open source alongside a format-conversion package (`@deepnote/convert`). Making the cell/block schema itself an externally consumable artifact is a smaller commitment than open-sourcing the product, but it lets third-party tooling (import/export, agents, CI) validate and generate Deepnote-native content without reverse-engineering an internal format.

## Worth avoiding

Autonomous, unattended execution against live compute/data connections is exactly the surface that needs the most guardrails (cost, side effects, writeback safety) — this file doesn't have independent evidence on what containment Deepnote applies (sandboxing, spend caps, writeback confirmation) during an unattended Auto AI run; flag as an open question rather than a confirmed gap.

## Facts & figures

- Positions itself as "a drop-in replacement for Jupyter" (vendor description, GitHub README).
- Three published open-source npm packages: `@deepnote/blocks`, `@deepnote/convert`, `@deepnote/database-integrations`.

## Sources

- [Deepnote GitHub](https://github.com/deepnote/deepnote) · [Revolutionizing data work with Deepnote AI — again](https://deepnote.com/blog/deepnote-auto-ai) · [A new era for data work: autonomous Deepnote AI](https://deepnote.com/blog/a-new-era-for-data-work-introducing-autonomous-deepnote-ai) · [Deepnote Agent docs](https://deepnote.com/docs/deepnote-agent) · [Generative analysis docs](https://deepnote.com/docs/ai-analysis)
- **Not directly verified:** sandboxing/spend-limit mechanics for unattended Auto AI runs; exact scope of what `@deepnote/blocks` covers vs. proprietary block types.
