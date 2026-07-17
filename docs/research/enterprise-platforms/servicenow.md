# ServiceNow

**What it is:** The incumbent workflow/ITSM platform, built on a single-codebase, multi-tenant-by-domain model — its packaging, ACL, and delegation mechanisms are the enterprise reference for "how do you let a customer customize a shared platform without corrupting the upgrade path."
**Axis:** deploy/migration, enterprise governance, workflow.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Update sets** | A portable change record capturing config/customization deltas between instances |
| **Application Repository** | Git-backed, versioned scoped-app distribution, tracked via `sys_store_app` |
| **Access Control Lists (ACLs)** | Row-level (`table`) and field-level (`table.field`) permission rules, independently evaluated |
| **Domain separation** | Logical multi-tenancy within one instance, via `sys_domain` + `sys_overrides` |
| **Delegation** (`sys_user_delegate`, Granular Delegation) | Time-boxed hand-off of approvals/tasks to a stand-in, attributed in the audit trail |
| **SLA engine** | Definitions with escalation stages, attachable Flow Designer flows at each stage |
| **Flow Designer + Spokes** | Low-code automation builder; Spokes are packaged integration action libraries |
| **CMDB + IRE** | Configuration management database with an engine to identify/reconcile incoming CI data |
| **ATF (Automated Test Framework)** | Declarative, record-and-verify UI/data test runner native to the platform |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Update sets vs Application Repository, never mixed | Two mutually-exclusive distribution mechanisms with an explicit incompatibility warning | yes (as cautionary pattern) |
| "Skipped update" on repo install after update-set edits | Customized artifacts silently excluded from a subsequent repo upgrade | yes (as failure mode to design around) |
| Row ACL AND field ACL, most-restrictive-wins | `table` grants a row, `table.field` grants a column; both must pass | yes |
| Domain separation + `sys_overrides` | Per-tenant process override on a shared codebase, not just per-tenant data | yes |
| Delegate approval, audit-attributed | Delegate approves with original approver's authority; log reads "approved as delegate of X" | yes |
| Granular Delegation | Fine-grained control over *what* can be delegated, to whom, not just a blanket OOO switch | yes |
| SLA escalation stages | Flow-attachable actions fired at % elapsed thresholds, not just at breach | yes |
| CMDB + IRE identification rules | Prioritized attribute-match rules decide update-existing vs create-new for incoming CI data | yes |
| ATF | Native declarative test framework, but explicitly cannot test Flow/Subflow/Action directly | maybe |

## Worth stealing

### Update sets vs Application Repository — two systems, and the platform tells you not to mix them

**Update sets** are the older mechanism: a change record capturing config/customization deltas. When applied to a receiving instance, the artifacts inside become **editable, ordinary local customizations** on that instance — but that instance then **cannot receive Application Repository updates for that app** going forward, because the app was never installed *as* a repo-tracked application there.

**Application Repository** is the newer, git-backed mechanism for scoped applications: installing from the repo gives the receiving instance a `sys_store_app` record, and the instance **can query the repository for newer versions** and pull them in cleanly — but in exchange, the app's artifacts **cannot be edited directly in Studio** on that instance; changes have to flow back through the source-controlled app and a new version.

ServiceNow's own support KB is explicit: **do not combine the two approaches for the same scoped application.** The failure mode when you do: the platform tracks customizations via a Customer Updates table, and on the next repository install, **"artifacts with version history are classed as customizations and are skipped"** — i.e., because you touched something via update set, the system now treats it as a local customization that must be manually reconciled rather than a delta to auto-merge, generating a queue of "skipped update" entries that require human review on every subsequent upgrade.

The mechanism worth extracting: **the platform has two different provenance channels for the same artifact, and it will not automatically reconcile between them.** If a Houston-shaped platform lets customers override generated app config from two different surfaces (in-app AND source-controlled), the analogous corruption is a design risk to name explicitly rather than discover in production.

### Row ACL vs field ACL — dot in the name is the difference, and both must pass

An ACL entry with no dot in its name (`incident`, `task`) is a **row-level** rule; one with a dot (`task.number`, `task.*`) is a **field-level** rule. Evaluation moves from most specific match to least specific (`table.field` → `parenttable.field` → `*.field` → `table.*` → `parenttable.*` → `*.*`), and **access requires both the row-level AND the field-level check to pass** — a rule that grants full row write but denies a specific field write still blocks that field. In ServiceNow's own framing: **the most restrictive applicable ACL wins.**

This is the same two-axis shape as Salesforce's object/record permissions plus FLS, arrived at independently — a strong signal that "row access" and "field access" as two orthogonal, both-must-pass checks is close to the correct primitive for an enterprise data platform.

### Domain separation — `sys_overrides` as per-tenant *process*, not just per-tenant *data*

Domain separation splits data, processes, and administration into logical domains within a single codebase/instance. The subtlety: **turning on domain separation for data alone changes nothing about behavior** — "if only data separation is activated without process separation, all domains will use the same business rules." Process separation is a deliberate second step, implemented via the **`sys_overrides`** field present on domain-aware tables: a business rule (or client script, UI policy, notification, assignment rule, SLA, etc.) defined in the parent ("Top") domain can be **overridden inside a child domain**, so that domain runs different logic while every other domain still runs the shared default.

The mechanism worth stealing: **one shared codebase, one shared table, with an explicit per-record "does a more specific domain override this" pointer** — rather than forking the codebase, or storing tenant-specific config in a side table that has to be joined and reasoned about separately. It's the layering answer to "customer wants their own approval rule without their own copy of the app."

### Delegation — audit-attributed, not silent impersonation

`sys_user_delegate` lets an approver set a delegate for a bounded date range, with independent toggles for whether the delegate should also receive approvals, notifications, and/or task assignments during that window. The detail that makes this a governance mechanism rather than just a convenience: **the platform remembers the original approver.** With the relevant audit property enabled, the approval journal literally logs *"X approved the task as delegate of Y"* — so a compliance review six months later can see both who clicked approve and whose authority they were acting under, without any separate reconciliation.

**Granular Delegation** is the newer, more precise layer on top: instead of "delegate can act on everything I could act on," it lets an admin define **rules for exactly which categories of tasks/approvals may be delegated, and to whom** — stored in a separate `sys_granular_delegate` table rather than overloading the legacy one. The evolution (blanket OOO switch → typed, scoped delegation rules) mirrors the general enterprise trend of turning an admin convenience into an auditable, constrained grant.

### SLA escalation stages — flows attach at percentage-elapsed thresholds, not just at breach

An SLA definition isn't just a deadline with a single breach notification. ServiceNow attaches actionable stages at multiple points along the timeline — commonly **50% elapsed** (early warning), **75–90% elapsed** (urgent escalation, often notifying a manager), and **breach** (immediate escalation, logged) — and each stage can trigger an attached **Flow Designer flow**, not just a canned email. The design principle stated by practitioners: *"breach notification shouldn't mean 'tell me I already failed' — the best alert is the one that gives you time to act."* The mechanism is escalation-as-a-first-class-timeline-object, with hooks at multiple percentages rather than a single deadline field.

### CMDB + IRE — prioritized identifier rules resolve "is this a new record or an update to an existing one"

The Identification and Reconciliation Engine solves a hard problem for any system ingesting data from multiple untrusted/partial sources: given an incoming payload describing a configuration item, **is this the same CI as one already in the database, or a new one?** Identification rules define, per CI class, a prioritized list of attribute combinations (serial number, device ID, name + class, etc.) to attempt in order; the first rule that finds a unique match wins and the incoming payload becomes an update; if none match, a new CI is created. This is a directly reusable pattern for any platform that has to merge records from multiple integrations into one semantic entity without either duplicating or false-merging.

## Worth avoiding

- **The update-set/repository split is an unforced complexity tax that the platform itself warns against, and the warning exists precisely because the failure mode is silent and deferred** — you don't find out you mixed the two mechanisms until an upgrade months later generates a pile of skipped updates. A system that offers two provenance channels for the same object needs either an explicit migration path between them or a hard block on using both, not just a KB article telling admins not to.
- **ATF cannot test Flow Designer Flows, Subflows, or Actions directly** — despite Flow Designer being the primary modern automation surface, the native test framework requires a workaround (extracting a "code snippet" from inside an action to build a custom ATF step). A test framework introduced after the primary authoring surface, and never fully retrofitted to cover it, is a recognizable anti-pattern: coverage gaps concentrate exactly where the most business logic now lives.
- **Domain separation without process separation is a trap for the unwary** — turning on data isolation alone gives a false sense of tenant isolation while every domain still runs identical business rules; the two have to be reasoned about and enabled as genuinely separate decisions.

## Facts & figures

- Domain separation is enabled by a specific plugin ("Domain Support - Domain Extensions Installer") — not on by default.
- Delegate audit-comment behavior is gated by a system property (`com.glide.hub.flow.approval.show_higher_role_audit_comment`), introduced in the Yokohama release — off by default, so the attributed audit trail is opt-in, not automatic.
- Granular Delegation stores its grants in a separate table (`sys_granular_delegate`) from the legacy delegate table (`sys_user_delegate`) — the two coexist rather than one replacing the other.

## Sources

- [ServiceNow Support — Steps to switch a scoped app from Application Repository to Update Sets](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0786118) · [ServiceNow Support — How to resolve skipped update records after an upgrade](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0955553) · [ServiceNow Community — Difference between Application Repository and Update Sets](https://www.servicenow.com/community/developer-forum/difference-between-application-repository-and-update-sets-in/td-p/3149399)
- [ServiceNow Support — How ACL evaluation works](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0541355) · [ServiceNow Community — Evaluating Row level and Field level ACLs](https://www.servicenow.com/community/in-other-news/evaluating-row-level-and-field-level-acls/ba-p/2268703)
- [Servistio — Understanding and mastering domain separation](https://servistio.com/en/blog/understanding-and-mastering-domain-separation-in-servicenow/) · [ServiceNow Support — Understanding Domain Separation basics](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0715934)
- [ServiceNow Community — Delegates in ServiceNow](https://www.servicenow.com/community/itsm-articles/delegates-in-servicenow/ta-p/2600517) · [ServiceNow Community — Empower Employees with Granular Delegation](https://www.servicenow.com/community/hrsd-blog/empower-employees-with-granular-delegation/ba-p/2279270) · [ServiceNow Docs — Granular Delegation](https://www.servicenow.com/docs/r/employee-service-management/granular-delegation/granular-delegation.html)
- [ServiceNow Community — Complete Practitioner's Guide to ServiceNow SLAs](https://www.servicenow.com/community/itsm-forum/the-complete-practitioner-s-guide-to-servicenow-slas-from/m-p/3453739) · [ServiceNow Community — How to trigger SLA breach notifications](https://www.servicenow.com/community/itsm-articles/how-to-trigger-sla-breach-notifications-in-servicenow-and-show/ta-p/3499319)
- [ServiceNow Docs — Identification and Reconciliation Engine](https://www.servicenow.com/docs/r/servicenow-platform/configuration-management-database-cmdb/ire.html) · [ServiceNow Guru — CMDB IRE](https://servicenowguru.com/cmdb/servicenow-cmdb-identification-and-reconciliation-engine-ire/) · [Cookdown — ServiceNow IRE identification rules explained](https://www.cookdown.com/blog/servicenow-ire-identification-rules-explained)
- [ServiceNow Docs — Getting started with ATF](https://www.servicenow.com/docs/r/application-development/automated-test-framework-atf/atf-intro.html) · [ServiceNow Community — How to test integrations (spokes) with ATF](https://www.servicenow.com/community/developer-blog/how-to-test-integrations-spokes-with-atf/ba-p/2289539)
- **Not directly verified:** exact default percentage thresholds for SLA escalation stages vary by out-of-box configuration and by ITSM vs other product lines; figures above are representative patterns from practitioner documentation, not a single canonical spec page.
