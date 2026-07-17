# Research

Landscape research: what other companies ship, what features they have, what's worth stealing. **Facts about the landscape — not Houston design decisions.** Those belong in the architecture docs.

106 company files across 13 categories, plus 3 standards. Each category has a `README.md` overview; each company has its own file. Depth varies and is stated in every file's header — `deep` means well-sourced against primary docs, `thin` means it was researched and there wasn't much there.

Structure: `_TEMPLATE.md` (per company) and `_CATEGORY_TEMPLATE.md` (per category). Keep entries factual, cite sources, and mark anything vendor-reported or unverified.

## Categories

| | Files | What it covers | Reference implementation |
|---|---|---|---|
| **[semantic-layer](semantic-layer/)** | 8 | Ontologies, metrics layers, catalogs | Palantir |
| **[deploy](deploy/)** | 8 | Deploy DX, preview envs, sandboxes, BYOC | Vercel |
| **[app-builders](app-builders/)** | 15 | Internal tools, BaaS, generated APIs, headless CMS | Retool |
| **[ai-builders](ai-builders/)** | 5 | Prompt-to-app platforms | Lovable |
| **[enterprise-platforms](enterprise-platforms/)** | 4 | The incumbents and their 20 years of hard-won mechanisms | Salesforce |
| **[citizen-developer](citizen-developer/)** | 3 | Field models, typed layouts, the no-code end | Airtable |
| **[analysis](analysis/)** | 11 | Notebooks, code-first BI, embedded analytics | Hex |
| **[workflow](workflow/)** | 12 | Durable execution, automation, human-in-the-loop, process mining | Temporal / DBOS |
| **[data-migration](data-migration/)** | 15 | Ingestion, mapping, contracts, quality, reconciliation | Osmos / Datafold |
| **[entity-resolution](entity-resolution/)** | 6 | Record linkage, MDM, survivorship | Senzing |
| **[agents](agents/)** | 8 | In-product agents, sandboxes, evals | Ramp |
| **[identity](identity/)** | 8 | Enterprise auth, SCIM, authorization engines | WorkOS |
| **[standards](standards/)** | 3 | Specs, not companies — MCP, ODCS, OpenLineage | — |

## Convergence

The reason to have 106 files is spotting where players who have never spoken to each other landed in the same place. **That's a law, not a fashion** — and it's the highest-signal thing in this folder. Each category README carries its own; these are the ones that span categories.

| Convergence | Who | Where |
|---|---|---|
| **Two access axes, both must pass** — row-level *and* field/column-level, modeled separately | Hasura, Directus, Cube, Looker, Unity Catalog, Salesforce FLS, ServiceNow field ACLs, Dataverse Column Security Profiles | Independently discovered by modern dev-tooling vendors **and** 20-year-old ERP/ITSM incumbents |
| **Keep the credential out of the untrusted thing's hands** | Vercel Sandbox, Cloudflare Outbound Workers, Cloudflare MCP OAuth, Claude Code mask mode, Decagon short-lived JWTs, Stytch Connected Apps | Six products, three categories — sandboxes, agents, identity |
| **Never mutate the source; re-apply human decisions as inputs** | Senzing `TRUSTED_ID`, Informatica XREF, Reltio read-time survivorship, Palantir Object Data Funnel | Four independently-arrived-at architectures |
| **Don't trust the model with irreversible actions** | Sierra, Decagon, Glean, Agentforce | Four vendors, no coordination |
| **Fan-out safety from declared relationships** | Looker (symmetric aggregates, runtime), Malloy (structural, in-language), MetricFlow (typed entities) | Three independent solutions to one problem |
| **Cheap suspend, but never indefinite by accident** — mandatory timeouts on human-in-the-loop | Windmill, Trigger.dev, Temporal/Inngest | Three unrelated vendors, same default |
| **Distinguish asserted from inferred** | OpenMetadata `source: Manual`, DataHub `confidenceScore`, Senzing disclosed-vs-resolved | Don't let re-derivation clobber a human assertion |
| **Derived values don't participate in the trigger graph** | Salesforce roll-ups, Smartsheet cross-sheet formulas | Same boundary, same stated reasoning (avoid cascading recalculation) — a deliberate tradeoff, not a shared bug |
| **Build-time static compilation** as a freshness-for-distribution trade | Observable Framework (JS data loaders), Evidence (markdown + SQL) | Different syntaxes, same landing: viewers issue zero live queries and need no warehouse credentials |
| **Cross-entity lookups in policy are the scaling wall** | Supabase ("minimize joins in policies"), Firebase (`get()` bills as a read per evaluation) | Opposite architectures, same conclusion |
| **Retrofitting isolation is always a distinct, later, separately-launched feature** | Sigma, Appwrite, the enterprise incumbents' layering models | Never free from the base architecture |

## Singular findings

Things exactly one player does, checked against the whole corpus.

- **ODCS's `text` quality tier** — "we know this rule exists and haven't automated it yet" as a first-class state. **No analog anywhere in these 106 files.** Every other quality/governance mechanism treats a rule as either running or nonexistent. See [standards/odcs](standards/odcs.md).
- **Palantir Action types** — the only *kinetic* semantic layer. Cube, LookML, MetricFlow, Malloy, and Unity Catalog are all read-only analytics layers with no equivalent. See [semantic-layer/palantir](semantic-layer/palantir.md).
- **Heroku Release Phase** — a gating pre-release task that blocks the deploy on failure and re-runs on promotion. Nobody in the Vercel/Fly tier does this. See [deploy/heroku](deploy/heroku.md).
- **Smartsheet Update Requests** — tokenized per-row, per-column edit URLs mailed to people with no account. Airtable and Notion have no equivalent. See [citizen-developer/smartsheet](citizen-developer/smartsheet.md).

## Confirmed open problems

Where the whole category has failed, not just one vendor.

- **The list-endpoint problem.** "Filter this 10k-row query by policy" defeats every Zanzibar-style engine. OpenFGA and SpiceDB punt; **Cedar attacks it from the opposite direction with Query-Plan SQL-filter compilation and also fails.** See [identity](identity/).
- **Unvalidated LLM judges.** The online/offline eval split is forced by ground-truth availability, not preference — which pushes online eval onto judges that are themselves unvalidated. Langfuse is the only one that even instruments its judges. See [agents](agents/).
- **Preview environments vs. shared multi-tenant databases.** Copy-on-write branching (Neon) is what makes previews work and doesn't compose with a shared cluster. PlanetScale's branches are schema-only. See [deploy](deploy/).

## Landscape notes

**Airtable retreated from drag-and-drop.** Their canvas is now legacy — *"only 'Blank' layouts still support it"* — because typed, table-bound layouts can be generated, validated, and defaulted, and canvases can't. Same lesson from v0, which works because its output space is constrained (Next + Tailwind + shadcn). **Constraint is what makes generation coherent.**

**Retool paid a migration to get to code.** Source-controlled apps serialize to **Toolscript**, a JSX-style format that replaced YAML because YAML wasn't reviewable. Their engineering blog is direct that the format is *why* AI-assisted development worked: "LLMs understand code." Superblocks rebuilt their runtime as a real React project for the same reason. **ToolJet's whole-file-JSON GitSync is the anti-pattern** — the diff is 100% of the file.

**Every AI-builder security incident on record is an authorization bug, not an AI bug.** Lovable's CVE was a fail-open default; its April 2026 incident was a BOLA; Replit's database wipe was no dev/prod separation. **The novelty is blast radius and propagation speed, not vulnerability class.** And Replit's three fixes were all environmental, none model-alignment — the agent ignored a code freeze repeated in ALL CAPS.

**The incumbents each grew a *second* mechanism where one wasn't enough** — Salesforce's four record-access mechanisms and two audit logs with two retention regimes; ServiceNow's update sets *and* app repository, and two coexisting delegate tables. **In every case the vendor's own docs explicitly warn against conflating them.** That's 20 years of discovering one mechanism was insufficient.

**Nobody has displaced a systems integrator.** Palantir, Unqork, Mendix, OutSystems — every attempt ended in partnership. Salesforce and ServiceNow *created* the largest SI practices in existence, because configuration surface is billable-hour surface. See [semantic-layer/palantir](semantic-layer/palantir.md).

**Isolation is commoditized; egress is not.** Firecracker and gVisor both state in writing that they perform no network filtering.

## Numbers not to cite

Findings that didn't survive checking. Recorded so they don't leak into a deck.

- **"170+ Lovable apps still exposed (Feb 2026)"** and the "1,645 scanned" denominator — from a scanner vendor's page that **states it was compiled from public Reddit discussions**. The 170 is almost certainly the original 2025 CVE count recirculated as fresh measurement. Same for "63% of 62 apps critical/high", "52% publicly readable tables" — all published by companies selling scanners.
- **Cold-start figures**: E2B's ~150ms, Daytona's sub-90ms, Modal's sub-second, Vercel's "milliseconds" — unverifiable in official docs. Only Cloudflare (1–3s) and Fly (~2s cold, few-hundred-ms resume) publish honest first-party numbers. **Modal's "sub-second" is contradicted by Modal's own GPU cold-start disclosures (2–10+s).** **Firecracker's famous 125ms/5MiB are specification targets** — the NSDI paper's own conclusion says ~150ms, and 125ms is unreachable without their tuned 4.0MB kernel (a stock Ubuntu kernel adds ~900ms).
- **gVisor's cited 38219ns syscall overhead** is ptrace-era; ptrace was deprecated mid-2023 for systrap, and no absolute systrap number is published. More decision-relevant: **Google, who builds gVisor, ships Cloud Run gen2 as a microVM.**
- **Sierra's "90% agent + 90% supervisor → 99%"** assumes independent errors. Agent and supervisor failures are correlated.
- **SI phase-cost percentages** trace to vendor/consultancy marketing, not analyst primary research. Shape is directionally right; precision is unearned.
- **Turborepo's "~85% CI reduction"** and Vercel's per-drain sampling — unverified in current docs.
- **Agentforce's audit refresh/retention numbers** and **Smartsheet Control Center's ~28-day propagation** are derived or unsourced. Control Center's throughput works out to ~40 projects/hour, not 30.
- **Celonis's valuation** ($11–16B) and **Hex's Team pricing** ($75/editor/mo on Hex's own site vs. $149–199 in third-party trackers) — sources disagree.
- Vendor-reported and unaudited: Replit's 3x/10x/90% autonomy claims; Rakuten's 97%.
- A **Guardio page fetch returned inverted VibeScamming scores** — reproduced independently twice, so treat that page as unreliable. Verified elsewhere, higher = more resistant (ChatGPT 8.0, Claude 4.3, Lovable 1.8). One PDF fetch returned a **substantially fabricated summary** with invented metrics appearing nowhere in the paper. **Re-verify anything re-fetched.**

### Corrections made during this research

Things asserted confidently and then found wrong.

- **Cloudflare's synchronous first Worker upload shipped ~Feb 2025**, not April 2026.
- **Airflow's `catchup` defaults to `true`**, not false — which is *why* it's a footgun.
- **DBOS's exactly-once claim is narrower than usually described**: it covers steps writing to **DBOS's own Postgres**, not arbitrary external I/O. The mechanism is real; the reach is often overstated.
- **Flatfile Automap's statelessness** is an absence of evidence in the docs, not a documented guarantee. Nuvo claims (unverified) that it *does* learn across imports.
- **Hightouch vs. Census "Mirror"** is not a clean inversion: Census's Mirror deletes by default; Hightouch's delete behavior is a separate opt-in *except* for warehouse destinations, where Mirror is a hard truncate-and-reinsert. Still a real cross-vendor hazard.
- **Toolscript's shorter diffs** come from omitting defaults, not from JSX being terser than YAML.
- **Salesforce roll-ups and Smartsheet formulas not firing triggers** is not a shared bug — both vendors give the same reasoning (avoid cascading recalculation). It's a deliberate boundary.
- **Strapi's `event.state` hook threading** is documented but reportedly broken.
- **Descope's SAML validation-key issue** is a general principle, not a confirmed historical CVE.
