# Palantir

**What it is:** The Ontology plus a suite of products built on it. The closest existing thing to Houston's shape, and the reference for the semantic-object bet.
**Axis:** semantic layer, agent platform, enterprise governance, GTM.
**Depth:** deep. `platforms/README.md` already carries the per-product Houston mapping — this file covers what the products *are* and the mechanisms worth stealing, not the mapping.

## Products & surfaces

| Product | What it is |
|---|---|
| **Ontology** | Governed, typed, live, bidirectional knowledge graph. The substrate everything else reads/writes through. |
| **Object Explorer** | Search/discovery over the Ontology. |
| **Workshop / Slate** | No-code operational app builder / drag-drop + full HTML-CSS-JS escape hatch. |
| **Quiver / Contour** | Point-and-click object/time-series analysis; large-scale tabular analysis. |
| **Notepad** | Collaborative rich-text docs embedding live widgets. |
| **Map** | Geospatial. |
| **Model Studio** | No-code ML training/deployment. |
| **AIP Logic / Agent Studio / Evals** | Explicit agent control flow; conversational agent builder; eval framework. |
| **Apollo** | Continuous deployment / ops control plane. |
| **Automate** | Condition-triggered actions on objects. |
| **Data Connection / Pipeline Builder / Code Workbook / Code Repositories** | Ingestion and transformation. |
| **Object Data Funnel** | Human edits to ontology data, held as an overlay. |
| **Marketplace** | Package & distribute bundled ontology + pipeline + app + automation. |
| **Ontology MCP (OMCP)** | For ontology **consumers** — external agents writing ontology **data**, restricted by app permissions. |
| **Palantir MCP** | For ontology **builders** — 70+ tools over ontology **structure**. Explicitly *cannot write ontology data*. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Semantic / kinetic split | Nouns (objects, properties, links, interfaces) *and* verbs (actions, functions, security) in one model | yes |
| **Action types** | A transactional set of edits with parameters, rules, submission criteria, side effects | yes |
| **Scenarios** | Agent-proposed changes staged as a sandboxed ontology subset, reviewed as a diff, applied transactionally | yes |
| **Markings** | Mandatory, conjunctive access control that even an Owner cannot remove | yes |
| Marking propagation | Markings travel through lineage to every derived dataset | yes |
| Granular / property policies | Row-level rules; column-level policies returning **null, not an error** | yes |
| Object-type vs object-data permissions | Two distinct permission levels — schema vs. rows | yes |
| Decision lineage | When a decision was made, atop which data version, through which application | yes |
| **Bootcamps** | 0-to-use-case in 1–5 days on the customer's real data | yes |
| **FDE model** | Forward-deployed engineers embedded in the customer's environment | see below |
| Notepad live/frozen docs | Same doc live-updating *or* frozen to capture point-in-time context | yes |
| Docs enrich the ontology | Embedded objects maintain structured links back into the graph | yes |

## Worth stealing

### Action types — the whitespace

The Ontology splits into **semantic** elements (object types, properties, link types, interfaces, shared properties) and **kinetic** elements (**action types**, functions, dynamic security). An action type is *"a transactional set of edits to objects/properties/links"* with parameters, rules, submission criteria, and side effects (notifications, webhooks, build triggers).

Their justification for actions as a first-class concept: enforce identical validation across every app, **capture decisions rather than diffs**, integrate approvals, produce a meaningful audit trail.

Palantir's own framing: *"the actions can be considered 'the verbs' (the kinetic, real-world execution), and with every Ontology-driven workflow, the nouns and the verbs are brought together into complete sentences through human- and/or AI-driven reasoning."*

**Cube, LookML, MetricFlow, Malloy, and Unity Catalog are all read-only analytics layers. None of them has an Action type.** This is unoccupied territory.

### Scenarios — staged effects

Agent-proposed changes are *"staged as ontology scenarios, which safely package the proposed changes into a **sandboxed subset of the Ontology** — enabling teams to safely explore and analyze the implications of the decision before committing to it."*

- By default *"these actions can only be **staged** by the AI, and are then handed off to a human for final review."*
- Applied **transactionally** — *"either all of the Actions will be applied or none of them will be applied if there is a validation failure."*
- Autonomy is dial-able: *"surgically choose which trusted, well-worn AI processes can automatically close the action loop without human review... expanded or contracted — and instantly reflected across all Ontology-driven workflows."*

Note Palantir uses **"sandbox" to mean staged writes over an ontology**, not a VM. Two different senses of the word in this research folder — see `ramp.md` for the other.

### Markings — mandatory vs. discretionary control

Binary, all-or-nothing eligibility. **Conjunctive** — you must hold *all* markings on a resource. **Even an Owner cannot remove a marking** without explicit "Expand Access" permission on the marking itself.

The distinction that matters: **mandatory controls restrict; roles expand.** Most platforms only have the discretionary half, where an admin can grant themselves anything. Regulated buyers are specifically purchasing the property that their own administrators cannot override a control.

**Markings propagate through lineage** — *"every dataset that depends on it inherits that Marking."* Protection travels through transforms.

### The permission split

Two distinct levels: permissions on the **object type** (schema) vs. the **objects** (data). *"To see an object type you must have View on the object type, but do not need View on the backing datasource."* Action types are gated separately, and **editing an action requires edit on the action type plus all ontology resources it modifies.**

Property security policies: **restricted properties return null, not an error**, and the user still sees the object. Cannot cover primary keys. Each property belongs to at most one policy.

### Object Data Funnel — human edits as an overlay

Human edits live in a Funnel-owned dataset, **never the source**; the merge is a read/build-time overlay. Two named, explicit merge policies rather than implicit last-writer-wins:
- **Apply User Edits** — human always wins per-property, regardless of future datasource updates. The default.
- **Apply Most Recent Value** — timestamp arbitration.

**Deletes are deliberately outside the conflict policy:** *"Once a deletion is applied, the object is no longer visible regardless of datasource state."*

**Action log as an object type** — every submission logged immutably, *"cannot be deleted or modified by end users, even if the corresponding ontology edits are reverted."*

### Bootcamps — the GTM weapon

**0 to use case in 1–5 days**, hands-on-keyboard, on the customer's *real* data. Working LLM-grounded application by day three. **1,000+ run by end of 2024**, converting at high rate into seven-figure contracts.

Karp's framing: compare what you built internally *"no matter how many resources or years"* against 10 hours on the platform. This is a direct assault on the SI discovery phase — replace a six-week requirements document with a three-day working app.

### Notepad — live vs. frozen

The same doc can be **live-updating or frozen to capture point-in-time context**. That's what makes a data doc trustworthy ("freeze this section as of the board meeting"). Docs also **enrich the ontology back** — embedded objects maintain structured links, so a report *about* an object appears *on* that object.

### AIP context scoping

Expose *"the Ontology capabilities that are configured, authorized, and relevant to the current task... rather than exposing all 500 Object Types and 2000 Properties."* Authorization doubles as context pruning. A described five-layer runtime: **Context → Query → Logic → Action → Governance** (third-party analysis; the official blog post was not directly reachable).

## Worth avoiding / the cautionary read

### The FDE model didn't do what the rhetoric says

FDEs are engineers who *"combine deep product expertise with the ability to work directly in the client's operational environment,"* focused exclusively on one customer, paired with Deployment Strategists. Everest Group's framing: *"Software companies typically rely on customer teams or partners to implement, and consulting firms often build from scratch on varied tech stacks — Palantir deploys its own people, on its own stack."*

The flywheel is real: *"every time an FDE solved a problem, the core team would generalize that solution for future clients. This is why Palantir launched Foundry and Apollo: to codify those learnings so the next customer needed less custom work."* Engagements are structured to end — the customer stands up a Center of Excellence and runs it themselves. Services are *"a means to drive product adoption, not the primary revenue stream."*

**But it did not displace the systems integrators. It married them:**

- **Accenture Palantir Business Group**, formed **December 2025**. Accenture named a preferred global partner. **2,000+ Palantir-skilled Accenture professionals** plus dedicated Palantir FDEs — and Accenture contributes its own FDEs.
- **Accenture Federal** named preferred implementation partner (June 2025); **1,000 Accenture Federal Data & AI professionals** being trained on Foundry and AIP.
- Accenture **acquired Palantir-specialist firms Rangr Data and Decho** in 2025.
- **Deloitte + Palantir** built an "Enterprise Operating System" combining Deloitte IP with Foundry/AIP.

The company with the most aggressive anti-consultant rhetoric in enterprise software ended up with Accenture building a 2,000-person practice on its platform and buying up its implementation ecosystem. The plausible reading: **FDE was product discovery funded by services revenue, plus a capacity bootstrap until partners could carry delivery.** The dependence moved from "Accenture's bespoke Java app" to "Accenture's Foundry practice."

### Opacity

Palantir does **not disclose professional services as a separate revenue line** — the 10-Ks report by Government/Commercial segment only (FY2024: Government $1.57B / 54.78%, Commercial $1.30B / 45.22%). The FDE model's true economics are not public, and that's probably deliberate.

### The ontology cost

The "ontology generates the tool surface at the right altitude" pattern only works **if you've already paid the ontology cost** — which is the entire Palantir business model, and why the pattern hasn't generalized.

## Facts & figures

- 1,000+ bootcamps by end of 2024; high conversion to seven-figure contracts.
- FY2024 revenue: Government $1.57B, Commercial $1.30B.
- Accenture Palantir Business Group: 2,000+ professionals (Dec 2025).
- Accenture Federal: 1,000 professionals in training (June 2025).

## Sources

- [Ontology overview](https://www.palantir.com/docs/foundry/ontology/overview) · [Core concepts](https://www.palantir.com/docs/foundry/ontology/core-concepts) · [Ontology system architecture](https://www.palantir.com/docs/foundry/architecture-center/ontology-system)
- [Action types](https://www.palantir.com/docs/foundry/action-types/overview)
- [Markings](https://www.palantir.com/docs/foundry/security/markings) · [Object and property policies](https://www.palantir.com/docs/foundry/object-permissioning/object-and-property-policies) · [Ontology permissions](https://www.palantir.com/docs/foundry/object-permissioning/ontology-permissions) · [Granular policies](https://www.palantir.com/docs/foundry/platform-security-management/manage-granular-policies) · [Restricted views](https://www.palantir.com/docs/foundry/security/restricted-views) · [CBAC](https://www.palantir.com/docs/foundry/security/classification-based-access-controls)
- [Ontology MCP](https://www.palantir.com/docs/foundry/ontology-mcp/overview) · [Palantir MCP](https://www.palantir.com/docs/foundry/palantir-mcp/overview)
- [AIP Bootcamp](https://www.palantir.com/platforms/aip/bootcamp/) · [Deploying Full Spectrum AI in Days](https://blog.palantir.com/deploying-full-spectrum-ai-in-days-how-aip-bootcamps-work-21829ec8d560)
- [AIP architecture](https://www.palantir.com/docs/foundry/architecture-center/aip-architecture)
- [Everest Group on FDEs](https://www.everestgrp.com/palantir-inside-the-category-of-one-forward-deployed-software-engineers-blog/)
- [Accenture + Palantir](https://newsroom.accenture.com/news/2025/accenture-and-palantir-expand-global-strategic-partnership-to-drive-ai-reinvention) · [Accenture Federal](https://newsroom.accenture.com/news/2025/palantir-and-accenture-federal-services-join-forces-to-help-federal-government-agencies-reinvent-operations-with-ai) · [Deloitte + Palantir](https://www.deloitte.com/us/en/about/press-room/deloitte-palantir-strategic-alliance.html)
- [FY2024 10-K](https://www.sec.gov/Archives/edgar/data/1321655/000132165525000022/pltr-20241231.htm)
- **Not directly verified:** "Connecting Agents to Decisions" (Medium redirect blocked); the five-layer AIP runtime is third-party analysis. OMCP transport/OAuth mechanics are undocumented in reachable pages.
