# Microsoft Power Platform (Dataverse)

**What it is:** Microsoft's low-code app platform (Power Apps / Power Automate / Dataverse) — the industry's clearest worked example of "what happens at runtime when a customer has customized a vendor-shipped app and the vendor ships an upgrade."
**Axis:** deploy/migration, enterprise governance, app-builder.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Dataverse** | The underlying typed data platform (tables, relationships, security) beneath Power Apps/Automate/Dynamics |
| **Solutions** | Versioned, packaged bundles of components (tables, forms, flows, apps) — the unit of ALM |
| **Solution layers** | The runtime merge/precedence model across installed managed + unmanaged solutions |
| **Security roles** | Privilege-and-depth (User/Business Unit/Organization) access control |
| **Column security profiles** | Per-column Create/Read/Update access control, independent of security roles |
| **DLP policies** | Tenant/environment-level connector classification (business / non-business / blocked) |
| **Power Platform admin center** | Environment lifecycle, governance settings, including blocking unmanaged customizations |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Two-tier layering: unmanaged (single, shared) above managed (stacked, ordered) | The active/top-most definition of a component wins at runtime | yes |
| "Last managed solution installed sits above the one before it" | Managed solutions form an ordered stack; later installs can customize earlier ones | yes |
| Hard rule: one solution with all your tables | Cross-solution table relationships create upgrade/delete hazards later | yes (as caution) |
| Hard rule: don't put the same unmanaged component in two solutions | All unmanaged solutions share one layer; duplicate membership is silently contentious | yes (as caution) |
| Block unmanaged customizations (env setting) | Admin can force all changes through packaged ALM; ad hoc edits error out | yes |
| Column security profiles | Create/Read/Update, independently assignable per column, per user/team | yes |
| DLP connector classification (business/non-business/blocked) | A resource using a "business" connector cannot also use a "non-business" one | yes |
| Security role depth (User/BU/Organization) | Same privilege, three concentric radii of applicability | maybe |

## Worth stealing

### Solution layering — the mechanism for "vendor ships an upgrade, customer already customized it"

Dataverse has exactly two kinds of layer:

- **The unmanaged layer** — a single, shared layer. Every unmanaged solution installed in an environment, plus every ad hoc customization a maker makes directly in the environment, lands here. There is only one of these per environment; nothing distinguishes which unmanaged solution a change "belongs to" at runtime.
- **Managed layers** — one per installed managed solution, **stacked in install order**. "When multiple managed solutions are installed, the last one installed is above the managed solution installed previously" — so a second managed solution can override behavior a first managed solution defined, purely by virtue of installing later.

The unmanaged layer always sits **above every managed layer**. At runtime, for any given component property, the platform "walks the stack top-to-bottom and takes the first layer that defines that property" — so **unmanaged customizations, wherever and whenever made, define runtime behavior**, full stop, until removed. Uninstalling a managed solution doesn't restore a clean state; it just exposes whatever layer is now on top, which might be another managed layer or the unmanaged layer if anyone ever touched the component directly.

Two derived best practices Microsoft states explicitly, because they've watched customers break them:

- **Use unmanaged solutions only in dev.** Since managed solutions are the deployable/upgradeable artifact and the unmanaged layer always wins, an unmanaged customization made outside of dev silently and permanently shadows every future managed upgrade to that component until someone finds and removes it.
- **Don't put the same unmanaged component in two different unmanaged solutions**, and **have exactly one solution that owns all your tables** — because cross-solution table relationships create dependency edges that make later solution deletion or upgrade order-sensitive and failure-prone.

### Blocking unmanaged customizations entirely

The direct answer to "how do you stop the failure mode above": an environment-level admin setting, **"Block unmanaged customizations"** (GA), which — once enabled — makes the environment reject: import of unmanaged solutions, creation of new solution-tracked objects (apps, tables, forms) outside a solution context, and direct edits to existing solution-tracked objects. Attempting any of these returns an explicit error ("This environment doesn't allow unmanaged customizations"). Notably, some operations remain allowed even under the block — toggling a flow on/off, sharing/ownership changes, environment variable value changes, and creating/exporting *new* unmanaged solutions (for later merge into a managed pipeline) — because those aren't structural customizations. Default state: **disabled** — the platform doesn't force this discipline unless an admin opts in.

The mechanism worth extracting: **give the platform a single switch that converts "changes can happen anywhere" into "changes can only arrive through the approved packaging/ALM path,"** without removing the ability to develop unmanaged solutions somewhere else (dev) and promote them properly.

### Column security profiles — orthogonal to security roles

Column-level security is a **separate permission system layered on top of** (not replacing) table/row-level security roles. To use it: a column must first have column security explicitly enabled (opt-in, per column, under "Advanced options"), then a **Column Security Profile** grants **Create / Read / Update** independently for that column to specific users or teams. A user with full row-level edit access via their security role can still be blocked from ever setting or seeing one specific "high business impact" column (e.g., SSN, salary) if no profile grants them access to it.

This is the same two-axis shape found in Salesforce (object/record permissions + FLS) and ServiceNow (row ACL + field ACL): **row/record access and column/field access are consistently modeled as two independently-administered, both-must-pass gates** across every mature enterprise platform surveyed in this research set — strong convergent evidence that's close to the right primitive.

### DLP policies — connector classification as a hard incompatibility rule, not a scored risk

Every connector (Dataverse-native or third-party) in a DLP policy is bucketed into exactly one of three groups: **Business**, **Non-Business**, or **Blocked**. The rule that makes this a real guardrail rather than a suggestion: **a single Power App or Flow that uses a Business-classified connector cannot also use any Non-Business connector, and vice versa** — the two groups are mutually exclusive *within one resource*, not just independently allow/denied. Blocked connectors can't be used anywhere, by any resource, full stop. New policies default every connector to Non-Business, forcing an admin to make an affirmative decision to elevate something to Business (i.e., "trusted with sensitive data can talk to other trusted-with-sensitive-data systems only") rather than defaulting open. A short explicit exception list exists for connectors that drive core platform function (Dataverse itself, Approvals, Notifications) which can never be blocked, because blocking them would break the platform's own critical path.

## Worth avoiding

- **The unmanaged layer is a single, environment-wide, undifferentiated pool.** Nothing at runtime remembers *which* unmanaged solution or maker made a given customization — it's one shared shadow layer. That's exactly why Microsoft's own guidance is so emphatic about restricting unmanaged customization to dev: the layer model has no finer-grained attribution or rollback once you're in it, so the only safe way to manage it is to keep it out of anywhere that matters.
- **Cross-solution table relationships are a documented later-stage hazard** — "frequently risks of a single relationship between tables... causes solution upgrade or delete issues... at a later point in time." The failure surfaces long after the decision that caused it (which solution owns which table) was made, which is the same delayed-failure shape as ServiceNow's update-set/repo mixing problem.
- **Block unmanaged customizations is opt-in and off by default** — the safer, more auditable mode of operation exists but isn't the platform's default posture; an org has to know to turn it on.

## Facts & figures

- "Block unmanaged customizations" reached General Availability (exact GA date not confirmed in this pass; public preview announcement predates GA by roughly one release wave per Microsoft's blog cadence).
- Column security profiles support exactly three permission flags per column: Create, Read, Update (no separate Delete — deletion is governed at the row level).
- DLP connector groups: exactly three (Business / Non-Business / Blocked); default bucket for new connectors in a new policy is Non-Business.
- Security role access levels: User / Business Unit (and its "Parent:Child" deep variant) / Organization — three concentric levels, cumulative across multiple assigned roles.

## Sources

- [Microsoft Learn — Solution layers in Power Platform](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/solution-layers) · [Microsoft Learn — Solution layers and merge behavior](https://learn.microsoft.com/en-us/power-platform/alm/solution-layers-alm)
- [Microsoft Learn — Organize your solutions](https://learn.microsoft.com/en-us/power-platform/alm/organize-solutions)
- [Microsoft Learn — Block unmanaged customizations in Dataverse environments](https://learn.microsoft.com/en-us/power-platform/alm/block-unmanaged-customizations) · [Microsoft Power Platform Blog — Announcing GA of Block unmanaged customizations](https://www.microsoft.com/en-us/power-platform/blog/power-apps/announcing-general-availability-of-block-unmanaged-customizations/)
- [Microsoft Learn — Column-level security](https://learn.microsoft.com/en-us/power-platform/admin/field-level-security) · [Microsoft Learn — Column-level security example](https://learn.microsoft.com/en-us/power-platform/admin/column-level-security-example)
- [Microsoft Learn — Connector classification (DLP)](https://learn.microsoft.com/en-us/power-platform/admin/dlp-connector-classification) · [Microsoft Learn — Manage data policies](https://learn.microsoft.com/en-us/power-platform/admin/prevent-data-loss)
- [Microsoft Learn — Security roles and privileges for Dataverse](https://learn.microsoft.com/en-us/power-platform/admin/security-roles-privileges) · [Microsoft Learn — Assign security roles](https://learn.microsoft.com/en-us/power-platform/admin/assign-security-roles)
- **Not directly verified:** precise GA date for "Block unmanaged customizations"; exact wording of the runtime merge algorithm for conflicting managed-layer definitions (described here as "top-most defining layer wins," consistent across multiple third-party explainer sources but not quoted verbatim from a single primary doc).
