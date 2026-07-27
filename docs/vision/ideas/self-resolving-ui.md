# Self-Resolving UI

*Out-there idea. Speculative, not a committed platform or a directable spec — a concept worth keeping alive.*

## The idea

Split the app into two layers with very different tolerance for change:

- **Ontology (fixed, solid):** actions, state machine, durable workflows — the legal moves the app can make. This does not get creative. It stays boring and reliable on purpose.
- **UI (fluid, exploratory):** composition, copy, layout — expressed as *data*, not compiled code, rendered by a fixed registry of components.

Because presentation and mechanism are separate layers, the UI can be explored recklessly without risk to the backend: no matter how far a variant wanders — different layout, different copy, agent-generated composition — it can only ever select among presentations of already-legal actions. It can't invent an illegal one.

## What this unlocks

- **Variants become data points, not builds.** No bundle-per-variant, no redeploy, no client-side flicker — a "variant" is a row picked at render time.
- **Stratification stops costing engineering-hours.** Forking to N contexts doesn't mean building N pages; it means exploring a data space the render layer already knows how to express.
- **Selection becomes a policy, not a flag.** Contextual bandits over composition, not static 50/50 splits — picking the best-known arm per session, not per global rollout.
- **The reward loop closes in-process.** Render and event-emission share a request lifecycle, so "shown → clicked → converted" is exact, not reconstructed from client analytics.
- **Variant generation could itself be agentic** — proposing new compositions as data, not code, for the policy layer to try.

## The reframe

A global A/B winner (think: Amazon's product page) is optimized for *least average regret* across an enormous, heterogeneous population — which likely isn't anyone's actual optimum, just the point with nowhere worse to fall for the median case. Houston's bet: if the ontology is fixed and safe, a page stops being an engineering artifact with one canonical form and becomes an output — each context settling toward its own local maximum, all drawing legal moves from the same well.

## Open questions / honest risks

- **Unit of variation** — whole page vs. component/copy level (safety and convergence speed trade off directly).
- **Reward signal** — crisp (click, conversion) vs. fuzzy (dwell time, sentiment) — the latter leans hard on embeddings to be legible at all.
- **Stratifying on behavior/context is safe ground; stratifying on demographic is not** — differential treatment by protected class is a real legal/ethical minefield, distinct from personalizing on behavior.
- **Loss of shared reference** — if no two users see the same page, "click the blue button" stops being a sentence support can say. Full fluidity trades away debuggability and a shared mental model of "the app."
- **Vetting agent-generated variants before they go live to real users** is a different risk profile than a human authoring variant B, even with the ontology firewall in place.
