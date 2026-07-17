# Salesforce

**What it is:** The incumbent enterprise app platform — 20+ years of hard-won mechanisms for permissions, audit, packaging, and automation that every buyer's procurement checklist is implicitly modeled on.
**Axis:** enterprise governance, workflow, app-builder, deploy/migration.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Sandboxes** | Isolated copies of a production org, tiered by data policy (metadata-only → full production copy) |
| **Permission sets / profiles / FLS** | Object, field, and record-level access control layered independently |
| **Validation rules** | Declarative formula-driven record-save gating, with a field-anchored error location |
| **Formula fields** | Declarative computed fields, evaluated on read |
| **Roll-up summary fields** | Declarative aggregation (Count/Sum/Min/Max) across a master-detail relationship |
| **Flow (Record-Triggered)** | Declarative automation, split into before-save and after-save triggers |
| **2GP packaging (unlocked / managed)** | Source-driven, versioned application packaging, successor to org-dependent 1GP |
| **Scratch orgs + source tracking** | Disposable, config-as-code dev environments |
| **Setup Audit Trail** | Log of configuration/metadata changes |
| **Field History Tracking / Field Audit Trail (Shield)** | Log of data changes, free tier and paid extended tier |
| **Approval processes** | Declarative multi-step, multi-approver record sign-off workflows |
| **Agentforce** | Agent platform: builder, dedicated agent user, Testing Center, Data Cloud-backed audit trail |
| **Governor limits** | Hard per-transaction resource caps enforced on the multi-tenant runtime |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Sandbox tiers defined by data policy + refresh interval | Four tiers gated by how much prod data you get and how often it resyncs | yes |
| Four-mechanism record access (OWD/role hierarchy/sharing rules/manual sharing) | Layered, additive record-level security model | yes |
| FLS enforced universally regardless of access path | One field permission covers layout, related list, report, search, formula | yes |
| Validation rule error anchored to a specific field | Turns a rejection into an actionable inline message, not a toast | yes |
| Roll-up summary landmines (no `NOW`/`TODAY`, doesn't trigger workflow, can't be error location) | Documents where declarative aggregation breaks down | yes (as caution) |
| Before-save vs after-save flow split | Fast in-place validation vs full side-effect automation, same trigger surface | yes |
| 2GP unlocked/managed packaging, version control as source of truth | No packaging orgs; git branch = package version | yes |
| Two separate audit logs for two separate questions | Setup Audit Trail (config) vs Field History Tracking (data) | yes |
| Field Audit Trail as paid Shield upsell | Extended retention/field-count gated behind a SKU | yes (as pattern) |
| Approval process parallel/unanimous + delegated approver + recall actions | Full declarative approval state machine | yes |
| Agentforce dedicated agent user | Service account, not requester-impersonation | yes |
| Governor limits | Hard per-transaction caps, non-negotiable, shared pool across all automation | maybe |

## Worth stealing

### Sandbox tiers — defined by data policy, gated by refresh interval

Salesforce sells four sandbox tiers, and the differentiator in every tier is **how much production data you get and how stale it's allowed to become**, not compute or feature access:

| Tier | Data | Storage | Refresh interval |
|---|---|---|---|
| **Developer** | Metadata only | 200 MB | 1 day |
| **Developer Pro** | Metadata only | 1 GB | 1 day |
| **Partial Copy** | Metadata + templated data subset, **max 10,000 records per object** | 5 GB | 5 days |
| **Full** | Metadata + all data | Production-sized | **29 days** |

The mechanism worth noting: **the refresh interval is the governor.** A Full sandbox is the most faithful copy of production, but you can only re-sync it once every 29 days — so it's simultaneously the most realistic and the most likely to be stale during a long release cycle. Partial Copy's 10k-records-per-object cap is enforced via a **sandbox template** (an admin-defined query per object), so "sample of production" is a deliberate, versioned selection, not a random truncation.

### Record access — four layered mechanisms

1. **Organization-Wide Defaults (OWD)** — the baseline, most-restrictive-possible setting per object (Private / Public Read Only / Public Read-Write / Controlled by Parent).
2. **Role hierarchy** — access flows upward; a manager automatically sees what reports own.
3. **Sharing rules** — automatic, criteria- or ownership-based exceptions to OWD, targeting public groups/roles/territories.
4. **Manual sharing** — one owner, one record, one grant; not automated, exists for the case the other three don't cover.

These stack additively — nothing in the model can *remove* access once one of the four grants it. **FLS is layered independently on top and is checked regardless of which of the four mechanisms got you to the record**: "page layout, related lists, report, and so forth" — hiding a field from a page layout does not stop the value being read through a formula field or an API query; only field-level security does that. When a field is both required-on-layout and read-only-in-FLS, FLS wins — **the most restrictive setting always takes precedence.**

### Validation rules — the error location is the feature

A validation rule is a formula that evaluates to true/false plus an error message — unremarkable on its own. The detail that makes it usable in practice is that **the error can be pinned to a specific field**, so the user sees the rejection inline next to the offending input instead of as a page-level toast. Roll-up summary fields can appear in the *condition* of a validation rule but **cannot be the error location** — they don't live on edit pages, so there's nowhere to anchor the message.

### Roll-up summary fields — declarative aggregation and its documented landmines

Count/Sum/Min/Max across a master-detail relationship, no code. The failure modes are specific and worth internalizing as a checklist for any declarative aggregation feature:

- **Can't reference functions that derive values at evaluation time** — `NOW()`, `TODAY()`, `DATEVALUE`, current-user fields are all disallowed inputs, because a roll-up is a stored, recalculated value and "now" isn't stable to store.
- **Recalculation does not trigger workflow rules or field validations on the parent** — a roll-up changing is not itself a "record saved" event for automation purposes, so anything depending on the roll-up value has to be triggered separately.
- **Deleting a child record does not always force recalculation** in some paths — a known source of stale aggregates.
- Max 40 roll-up summary fields per object; no lookup relationships, only master-detail.

### Before-save vs after-save flow — trigger point as a performance dial

Record-triggered flows split into two entry points on the same object event:

- **Before-save**: runs before the commit, can only touch fields on the triggering record itself, and — because it never causes a second save cycle — is reported at **~10x faster** than after-save equivalents (some benchmarks cite up to ~85x). No record ID is available yet.
- **After-save**: runs after the record has an ID, can create/update related records, send notifications, call external systems — at the cost of a second DML/save cycle.

The mechanism: **expose "when in the save lifecycle" as an explicit, user-facing choice**, because "validate/normalize the record I'm already writing" and "cascade effects to other records" have an order-of-magnitude different cost profile and belong in different buckets.

### 2GP packaging — version control as the source of truth

Second-generation packaging (2GP) replaced the first-generation model where a **packaging org** held the authoritative metadata state. Under 2GP, "with version control being the source of truth, there are no packaging or patch orgs" — every package version is built directly from a git-tracked metadata directory via CLI, branchable and diffable like normal source.

Two flavors with different intended audiences:
- **Unlocked packages** — recommended for internal business applications. No IP protection, contents are visible/editable by the installing org (with constraints).
- **Managed 2GP packages** — for ISV distribution via AppExchange; contents are locked down in subscriber orgs.

Paired with **scratch orgs** (disposable, spun up from a config file, source-tracked) this is Salesforce's answer to "how do you do CI/CD against a multi-tenant SaaS platform with no concept of a container" — package-as-unit-of-deploy, git as system of record, disposable orgs as ephemeral environments.

### Two audit logs for two different questions

Salesforce deliberately does not merge these:

- **Setup Audit Trail** — records **who changed what configuration/metadata setting, and when**. Does **not** capture before/after values for most entries, and retention is roughly **180 days**, after which entries are permanently and non-recoverably deleted through native tooling.
- **Field History Tracking** — records **who changed what data value on a record, and when**, with old/new values, for a maximum of **20 fields per object**, retained roughly **18 months** in the UI (up to 24 via API).
- **Field Audit Trail** (paid Salesforce Shield add-on) — extends the same field-change tracking to **60 fields per object** and **10 years of retention**, with configurable per-object retention policies between 0–10 years.
- **Event Monitoring** — a *separate* Shield SKU again, for user-behavior/API-transaction-level logs (logins, exports, API calls) rather than config or field changes.

The pattern: **config-change auditing and data-change auditing are two different logs with two different retention regimes**, and the enterprise-grade version of either (longer retention, more fields, richer detail) is upsold as a paid add-on rather than bundled.

### Approval processes — a full declarative state machine

- **Parallel approval**: request goes to multiple approvers at once; the first response decides — no consensus required.
- **Unanimous approval**: request goes to all selected approvers; **all must approve, and any single rejection kills the whole request.**
- **Delegated approver**: a checkbox per approval step — "the approver's delegate may also approve this request" — lets a stand-in act with the same authority as the actual named approver. This is a same-authority delegate model, distinct from patterns (e.g., Camunda) where a delegate merely *returns* a task to the original owner rather than deciding it outright.
- **Recall**: submitters can be permitted to recall (pull back) an in-flight approval request; **recall actions** (field updates, notifications) fire on that path just like approve/reject actions do, so recall is a first-class transition in the state machine, not an escape hatch.

### Agentforce — a dedicated agent user, not requester impersonation

Agentforce runs actions as its **own service-account user** (an "Agent User"), configured with its own permission set/license, rather than executing under the identity and access grants of whichever human triggered the agent. That means the effective ACL an agent operates under is whatever was explicitly provisioned to the agent user — deliberately decoupled from what the requesting human happens to be able to see. This is the same shape as ServiceNow's `sys_user_delegate` problem in reverse: instead of "delegate inherits the original approver's authority," Agentforce chooses "agent has its own, separately administered authority," which is the safer default for an autonomous actor.

Agentforce's audit trail is Data Cloud-backed: **conversation/action logging for agents flows through Data Cloud** (rebranded Data 360 as of October 2025). A zero-cost Data Cloud "Starter" SKU is bundled with Enterprise Edition+ so basic Agentforce audit logging works without a paid Data Cloud contract, but richer analytics (Agentforce Analytics, Utterance Analysis) and heavier usage draw from **metered Data Cloud/Agentforce credits tracked in a "Digital Wallet."** *(Vendor-reported / not independently verified: specific "hourly refresh" and "30-day retention" figures for agent audit data — Salesforce's public docs describe the mechanism and the credit-metering model clearly but did not surface those exact numbers in reachable pages during this research pass.)*

## Worth avoiding

- **Two audit systems with different retention windows** means a real investigation ("who changed this config, and did it correlate with a data change?") requires manually correlating two systems with two different lookback horizons — 180 days of config history against 18 months of data history. A buyer doing real forensics hits the wall on the *config* side first.
- **Field Audit Trail is gated behind Shield**, so the "compliance-grade" version of the free tracking feature is a paid SKU on top of a paid SKU — the same governance feature exists in two qualities, and the good one costs extra.
- **Roll-up summary fields have real, well-documented landmines** (no live-derived functions, no workflow trigger on recalculation, can't anchor a validation error to them) — declarative aggregation over a relationship is powerful but the failure modes are subtle enough that Salesforce's own community produces regular "why didn't my roll-up update" content.
- **Governor limits are a hard multi-tenant tax**: 100 SOQL queries per synchronous transaction (200 async), shared across every trigger, flow, and process running in the same execution context — not per-feature, per-transaction. Most limits are **fixed and cannot be raised by support**, which pushes complexity onto app developers to batch/bulkify rather than the platform absorbing it.

## Facts & figures

- Sandbox refresh intervals: Developer/Developer Pro 1 day, Partial Copy 5 days, Full 29 days.
- Partial Copy sandbox template cap: ~10,000 records per object (vendor-documented, template-driven, not a hard platform ceiling).
- Setup Audit Trail retention: ~180 days native.
- Standard Field History Tracking: 20 fields/object, ~18 months (24 via API).
- Field Audit Trail (Shield): 60 fields/object, up to 10 years, configurable per-object retention.
- SOQL governor limit: 100 queries/sync transaction, 200/async transaction.
- Roll-up summary fields: max 40 per object.

## Sources

- [SFDC Developers — Sandbox types](https://sfdcdevelopers.com/2026/01/07/salesforce-sandbox-types-guide/) · [Salesforce Ben — What is a Sandbox](https://www.salesforceben.com/salesforce-sandbox/) · [Gearset — Refresh a sandbox](https://gearset.com/blog/how-to-refresh-a-salesforce-sandbox/)
- [Trailhead — FLS & permission sets](https://trailhead.salesforce.com/content/learn/projects/keep-data-secure-in-a-recruiting-app/fls-perm-sets-sharing) · [Salesforce Help — Page layouts and FLS](https://help.salesforce.com/s/articleView?id=sf.managing_page_layouts_and_field-level_security.htm&language=en_US&type=5)
- [Salesforce Help — Roll-Up Summary Field](https://help.salesforce.com/s/articleView?id=platform.fields_about_roll_up_summary_fields.htm&language=en_US&type=5) · [Traction on Demand — Rollup limitations](https://tractioncomplete.com/articles/salesforce-rollup-summary-field-limitations/)
- [Salesforce Ben — Before-Save vs After-Save Flow](https://www.salesforceben.com/before-save-flow-vs-after-save-flow-in-salesforce/)
- [Salesforce Ben — Unlocked Packages](https://www.salesforceben.com/unlocked-packages-in-salesforce-a-comprehensive-guide-for-developers/) · [Salesforce Developers — 2GP dev guide](https://developer.salesforce.com/docs/atlas.en-us.pkg2_dev.meta/pkg2_dev/sfdx_dev_dev2gp.htm)
- [Gearset — Salesforce Audit Trail and Field History Tracking](https://gearset.com/blog/salesforce-audit-trail/) · [Flosum — Field Audit Trail](https://www.flosum.com/blog/salesforce-field-audit-trail) · [Field Audit Trail Implementation Guide PDF](https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/field_history_retention.pdf) · [Netwrix — Setup Audit Trail vs Field History Tracking](https://netwrix.com/en/resources/blog/auditing-salesforce-the-setup-audit-trail-and-field-history-tracking/)
- [Salesforce Ben — How to build an Approval Process](https://www.salesforceben.com/how-to-build-salesforce-approval-processes-end-to-end/) · [Perficient — Multi-step approval process](https://blogs.perficient.com/2023/07/28/multi-step-approval-process-in-salesforce-using-standard-setup-wizard/)
- [Salesforce Help — Best Practices for Agent User Permissions](https://help.salesforce.com/s/articleView?language=en_US&id=ai.agent_user.htm&type=5) (page did not fully render on fetch; title/existence confirmed via search only) · [Salesforce Help — Generative AI Audit Trail](https://help.salesforce.com/s/articleView?id=ai.generative_ai_audit_trail.htm&language=en_US&type=5) · [TitanDXP — Is Data Cloud required for Agentforce?](https://titandxp.com/article/agentforce/require-data-cloud/)
- [Developer Blog — Salesforce Data Security Model Explained Visually](https://developer.salesforce.com/blogs/developer-relations/2017/04/salesforce-data-security-model-explained-visually) · [Salesforce Ben — 25+ Ways to Share a Record](https://www.salesforceben.com/25-ways-to-share-a-record-in-salesforce/)
- [Salesforce Developers — Execution Governors and Limits](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_gov_limits.htm)
- **Not directly verified:** exact Agentforce agent-audit "hourly refresh" and "30-day retention" figures — the Data Cloud-backed mechanism and credit-metering model are confirmed, precise numbers were not found in reachable public docs during this pass.
