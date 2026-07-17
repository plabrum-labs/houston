# Enterprise platforms

**What this category is:** the incumbents — Salesforce, ServiceNow, Microsoft Power Platform, SAP. Twenty-plus years of hard-won mechanisms for permissions, audit, packaging, and safe customization of a shared/multi-tenant codebase.
**Why it's in this research:** enterprise governance, deploy/migration (packaging/ALM), workflow, app-builder (extensibility surfaces). What a real enterprise buyer's procurement checklist is implicitly modeled on.
**Files:** 4.

## The players

| Company | What it is | Depth |
|---|---|---|
| [salesforce](salesforce.md) | The reference incumbent — sandbox tiers, four-mechanism record access, 2GP packaging, two audit logs, declarative approval state machine | deep |
| [servicenow](servicenow.md) | ITSM/workflow incumbent — the enterprise reference for "how do you customize a shared-codebase multi-tenant platform without corrupting the upgrade path" | deep |
| [microsoft-power-platform](microsoft-power-platform.md) | Dataverse — the clearest worked example of solution-layer merge semantics at runtime | medium |
| [sap](sap.md) | ERP incumbent — narrow scope, in only for the "clean core" extensibility taxonomy | thin, deliberately short |

Salesforce and ServiceNow are effectively co-reference-implementations here — each is deep and each independently arrived at the same core primitives. Power Platform is the clearest runtime-mechanics explainer for solution layering specifically. SAP is intentionally scoped narrow: only the extensibility-tiering idea is in play, not ERP process content.

## Convergence

**Row/record access and field/column access are independently modeled as two separate, both-must-pass gates, by every platform in this set.** Salesforce: four record-access mechanisms (OWD, role hierarchy, sharing rules, manual sharing) stack additively, then **FLS is checked independently and always wins** regardless of which access path got you to the record. ServiceNow: ACLs with no dot in the name are row-level, ACLs with a dot are field-level, and **both must pass** — "the most restrictive applicable ACL wins," the same wording as Salesforce's. Power Platform: security roles (row/record) plus Column Security Profiles (Create/Read/Update per column) are **independently administered permission systems**, one layered on the other. Three platforms, three independent engineering organizations, the identical two-axis primitive. This is named directly in `microsoft-power-platform.md` as "strong convergent evidence that's close to the right primitive" — cross-referenced against Directus and Hasura's independent arrival at the same shape in `app-builders/README.md`.

**Each platform grew a *second* mechanism because one wasn't enough — repeatedly, across unrelated subsystems.** Salesforce: four record-access mechanisms *plus* FLS as a fifth, independent layer; two audit logs (Setup Audit Trail for config, Field History Tracking/Field Audit Trail for data) with two different retention regimes, deliberately not merged. ServiceNow: update sets *and* Application Repository as two mutually exclusive distribution mechanisms — explicitly, by KB article, "do not combine the two approaches for the same scoped application" — plus a legacy delegate table (`sys_user_delegate`) coexisting alongside the newer, more granular `sys_granular_delegate` rather than replacing it. Power Platform: two layer types (single shared unmanaged layer, ordered stack of managed layers) with an explicit best-practice ("use unmanaged only in dev") that exists because the two-layer model has no finer attribution once you're in the shared layer. The pattern across all three: **complexity that looks like duplication is often a deliberate response to a mechanism that turned out to need two different provenance channels or two different retention regimes for two different questions** — and in every case, the platform's own documentation warns admins not to conflate the two.

**Delayed-failure customization corruption is a named, documented risk on both ServiceNow and Power Platform, independently.** ServiceNow's update-set/repository mixing produces "skipped update" entries only discovered at the *next* upgrade, months later. Power Platform's cross-solution table relationships create "solution upgrade or delete issues... at a later point in time" — the same delayed-failure shape, independently documented, for a structurally different mechanism (solution layering vs. package provenance).

**Delegation-with-attribution, not silent impersonation, is the shared design for "someone else acts on my behalf."** ServiceNow's `sys_user_delegate` explicitly logs "X approved the task as delegate of Y" when the relevant audit property is enabled. Salesforce's approval delegated-approver checkbox gives the delegate the same authority as the named approver, and Agentforce goes a different direction for a different actor type — a **dedicated agent service-account user**, not requester impersonation, so an autonomous agent's authority is separately administered rather than inherited from whoever triggered it.

## Worth stealing

- **Sandbox tiers gated by data policy and refresh interval, not compute** — the refresh interval *is* the governor (Full sandbox: most realistic, syncs only every 29 days) — `salesforce.md`.
- **Validation-rule errors anchored to a specific field** — turns a rejection into an inline message, not a page-level toast — `salesforce.md`.
- **Before-save vs. after-save as an explicit, user-facing performance dial** on the same trigger surface — "validate the record I'm already writing" and "cascade effects elsewhere" have an order-of-magnitude cost difference and belong in different buckets — `salesforce.md`.
- **2GP packaging: version control as the actual source of truth**, no packaging orgs, unlocked vs. managed as separate tracks for internal vs. ISV distribution — `salesforce.md`.
- **SLA escalation as a first-class timeline object** with flow-attachable actions at multiple percentage-elapsed thresholds, not a single breach notification — `servicenow.md`.
- **CMDB/IRE's prioritized identification rules** for "is this incoming record an update to an existing entity or a new one" — directly reusable for merging records from multiple untrusted/partial integrations — `servicenow.md`.
- **A single admin switch that converts "changes can happen anywhere" into "changes can only arrive through the approved ALM path"** (Power Platform's "Block unmanaged customizations") — `microsoft-power-platform.md`.
- **DLP's mutual-exclusion connector classification** (Business / Non-Business / Blocked, new connectors default Non-Business) — a hard incompatibility rule within one resource, not a scored risk — `microsoft-power-platform.md`.
- **SAP's "make the safest extension mechanism the path of least resistance"** — tiered extensibility (key-user no-code → developer in-app on released APIs only → side-by-side on a fully separate platform) ordered by coupling to the vendor's release cycle — `sap.md`.

## Worth avoiding

- **Two audit systems with different retention windows** forces manual correlation across mismatched lookback horizons (Salesforce: 180 days config vs. 18 months data) — real forensics hits the wall on the shorter side first — `salesforce.md`.
- **The compliance-grade version of a governance feature gated behind a paid SKU on top of a paid SKU** (Salesforce Field Audit Trail via Shield) — `salesforce.md`.
- **Update sets vs. Application Repository — a warning in a KB article is not a guardrail.** The platform offers two provenance channels for the same artifact and will not reconcile between them; the failure (skipped updates) surfaces silently, months later, at the next upgrade — `servicenow.md`.
- **A native test framework introduced after its primary authoring surface, never fully retrofitted** — ServiceNow's ATF cannot directly test Flow Designer Flows/Subflows/Actions, despite Flow Designer being where most modern business logic now lives — `servicenow.md`.
- **A single, undifferentiated shared layer with no per-change attribution** — Power Platform's unmanaged layer always wins at runtime and nothing records which unmanaged solution or maker made a given customization — the only safe operating mode is keeping it entirely out of anywhere that matters — `microsoft-power-platform.md`.
- **Domain separation without process separation is a false sense of isolation** — turning on data-only separation leaves every domain running identical business rules — `servicenow.md`.

## Gaps

- None of these four platforms has a public, primary-sourced account of what happens when **AI-agent-generated customization** collides with the packaging/layering model described above — Salesforce's Agentforce dedicated-agent-user pattern is the only piece of this set that even names agent authority as a distinct problem, and its own audit-retention specifics (hourly refresh, 30-day retention) weren't independently confirmed in this pass.
- Nobody in this set publishes a **rollback** mechanism for their packaging systems — Power Platform's solution layering, ServiceNow's Application Repository, and Salesforce's 2GP all describe forward-moving install/upgrade paths; none of the sourced docs describe an equivalent "undo this install" primitive.

## Notes

- SAP's file is deliberately short by design — only the clean-core extensibility taxonomy is in scope; no ERP-specific process content was researched.
- SAP's BTP adoption figures (~50% of customers actively using BTP services, +10pp YoY) are third-party-reported (SAVIC), not sourced to a primary SAP investor disclosure.
- Salesforce's Agentforce audit-trail "hourly refresh" and "30-day retention" figures are **not independently verified** — the Data Cloud-backed mechanism and credit-metering model are confirmed, the precise numbers were not found in reachable public docs.
- Power Platform's exact GA date for "Block unmanaged customizations," and the precise wording of the managed-layer runtime merge algorithm, are not quoted verbatim from a single primary doc — consistent across multiple third-party explainers but not confirmed against one canonical source.
- ServiceNow's SLA escalation percentage thresholds (50%/75-90%/breach) are representative practitioner patterns, not a single canonical out-of-box spec page.
