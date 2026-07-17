# Count

**What it is:** A data analysis tool that deliberately killed its SQL notebook UI and rebuilt around an infinite canvas.
**Axis:** app-builder, workflow.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Count Canvas** | Infinite-whiteboard analysis surface — SQL, viz, and freeform notes/annotation as first-class citizens on the same canvas. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Canvas replaces linear notebook | Analysis blocks (queries, charts, text) placed freely on an infinite 2D surface instead of a top-to-bottom cell list | maybe |
| Side-by-side query comparison | Two query versions sit next to each other spatially, compared directly, instead of via tabs/diffs | maybe |
| Stakeholders co-located with analysts | Non-technical stakeholders work in the *same* canvas space as the analyst, rather than receiving a finished export | maybe |

## Worth stealing / worth recording

Count's own framing for abandoning the notebook: *"The usefulness of any piece of analysis depends on the communication between the person doing the analysis, and the person doing something with that analysis"* — and they describe conventional notebook-plus-export workflows as building *"a wall between the analyst and the business,"* forcing a "dance between a SQL IDE, google doc or some heinous powerpoint." The canvas is pitched as removing that wall: reasoning becomes visible in place (*"the 'how' is now as easy to share as the 'what'"*), non-practitioner stakeholders can be brought directly into the workspace rather than receiving a finished artifact, and comparing two versions of a query side by side is spatial rather than requiring a diff view or duplicated notebook.

The tradeoff worth recording even though it argues against the mechanism: **an infinite canvas is close to the worst possible substrate for both git-diff review and agent-driven editing.** There's no natural linear order to diff against, no stable "cell N" addressing scheme for an agent to target, and spatial layout carries meaning that a text diff can't represent. Every other product in this batch (Hex, marimo, Observable) is converging toward *more* structure (DAGs, typed cells, file-based formats) specifically because that structure is what makes both version control and agent editing tractable — Count is a real data point that the opposite bet (structure-optional, freeform, stakeholder-first) also has a coherent rationale, just one this research folder's other subjects are moving away from.

## Worth avoiding

The anti-diff, anti-agent property above is the central risk of the canvas model for anyone building agent-authored analysis — worth stealing the *stakeholder-colocation* motivation without necessarily stealing the *canvas* mechanism to satisfy it.

## Facts & figures

- None independently verified beyond the blog post itself in this pass (no usage/scale figures found).

## Sources

- [Bye-bye notebooks. Hello, canvas.](https://count.co/blog/bye-bye-notebooks-hello-canvas) · [A data notebook buyer's guide](https://count.co/blog/a-data-notebook-buyers-guide) · [Count vs Notebooks](https://count.co/comparison/count-vs-notebooks)
- **Not directly verified:** any claims about adoption/scale; this file relies on a single primary source (Count's own blog post) plus comparison pages.
