# Superblocks

**What it is:** Low-code internal-tools builder whose newer product, **Clark**, is an AI agent that generates full apps (React/TypeScript) from a prompt, governed centrally by IT.
**Axis:** app-builder, agent, enterprise governance.
**Depth:** thin — vendor blog/docs and third-party coverage only; no hands-on verification.

## Products & surfaces

| Product | What it is |
|---|---|
| **Superblocks** | Drag-drop internal-tools builder; connects to DBs/APIs; JS/Python transforms. |
| **Clark** | Conversational AI agent that drafts a full app from a prompt, using a multi-agent backend (designer/engineer/IT-admin/security-analyst/QA roles). |
| **Superblocks Enterprise React** | Superblocks rebuilt its own app runtime as a standard React project so Clark (and human engineers) can edit it directly in an external IDE. |
| **On-premise Agent** | Self-hosted execution layer for queries/connectors, for customers who won't let Superblocks' cloud touch their data plane. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Runtime rebuilt as real React project | Generated/edited apps are ordinary React+TS, editable in VS Code/Cursor, changes sync back to the visual editor | yes |
| Org Knowledge / sub-agents | Admin-defined design system, code/security policy, integration schemas retrieved by specialized sub-agents at generation time | yes |
| Bidirectional visual↔code sync | Every code edit must remain parseable back into the visual model | no (cautionary) |
| Agent-in-the-loop governance | Clark verifies against org policy "on commit," not just at generation time | maybe |

## Worth stealing

**The runtime rewrite was in service of editability, not aesthetics.** Superblocks says it rebuilt its own product as "Superblocks Enterprise React" specifically so that Clark's generated output — and a human's follow-up edits — are a normal React+TypeScript codebase openable in any IDE, with edits syncing back to the visual canvas in real time. The sequencing matters: they didn't bolt an AI agent onto an existing proprietary runtime; they changed the runtime's representation *to make agent editing tractable*, the same move Retool made with Toolscript (see `retool.md`) but taken one step further — Superblocks' target format is a real language ecosystem (npm, IDEs, TypeScript's own tooling) rather than a bespoke serialization.

**Sub-agents scoped to org context.** Admins define "Organization Knowledge" — design system, code/security policy, domain terminology — plus integration knowledge (data sources, schemas, endpoints). Specialized sub-agents (described as playing designer/engineer/IT-admin/security-analyst/QA roles) pull the subset of that context relevant to their part of the build, rather than one general agent holding everything. This is the same shape as Retool's "fetch only relevant schemas" problem (see `retool.md`) — solved here by dividing labor across agents instead of by selective retrieval within one agent.

## Worth avoiding

**Bidirectional sync is a permanent tax on what code is allowed to look like.** If every code edit must be re-parseable back into the visual model, the code surface is constrained to whatever subset of React the visual editor can represent — arbitrary refactors, unusual component compositions, or patterns the visual model doesn't have a slot for either break the sync or get silently reverted at re-render. This is the generalizable failure mode of any product promising "edit the code AND keep the drag-drop editor in sync": the visual model becomes the ceiling on the code, not just a view of it.

## Facts & figures

- $60M raised (cumulative, per company announcement); latest $23M round included Spark Capital, Kleiner Perkins, Meritech Capital, Greenoaks (vendor/press-reported).
- Clark reported as running on Anthropic Claude 4 (vendor-reported, may be outdated by publication).

## Sources

- [Announcing $60m for Clark](https://www.superblocks.com/blog/announcing-clark-ai)
- [Clark AI docs](https://docs.superblocks.com/generative-ai/generate-code/clark-ai) · [Building with Clark AI](https://docs.superblocks.com/building-with-clark)
- [Announcing Superblocks 2.0: Governed Enterprise Vibe Coding](https://www.superblocks.com/blog/announcing-superblocks-2-0-a-new-era-for-governed-enterprise-vibe-coding)
- [On-premise Agent Overview](https://docs.superblocks.com/on-premise-agent/overview)
- **Not directly verified:** internal mechanics of the visual↔code sync parser; exact scope of what "verifying upon commit" checks.
