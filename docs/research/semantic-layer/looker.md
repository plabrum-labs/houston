# Looker

**What it is:** Google Cloud's BI platform built on LookML, a declarative modeling language compiled to SQL. The originator of the "declared model, not raw schema" argument in this research set — its access-control split and its join-correctness guarantee are both consequences of the model being declared rather than freeform SQL.
**Axis:** semantic layer, data modeling, access policy, git-native dev workflow.
**Depth:** medium — access control and symmetric aggregates verified against current Google Cloud docs; git/deploy settings verified; pricing and Looker Studio/Looker (Core) product-line distinctions not explored.

## Products & surfaces

| Product | What it is |
|---|---|
| **LookML** | Declarative modeling language: views, explores, joins, measures, dimensions, access controls — compiled to SQL per query. |
| **Looker IDE** | Git-backed dev environment for LookML, with per-developer dev-mode branches. |
| **LookML Validator** | Static validator for LookML projects; can gate commits. |
| **Data tests** | LookML `test` blocks that assert expected query results; can gate production deploy. |
| **Looker (platform)** | The BI application itself: Explores, dashboards, scheduling, embedding, on top of the LookML model. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **`access_filter`** | Row axis — filters returned rows by a user attribute | yes |
| **`access_grant` / `required_access_grants`** | Field axis — gates Explores/joins/views/fields; ungranted fields vanish from the picker | yes |
| **Symmetric aggregates** | Automatically rewrites `SUM`/`AVG` to avoid join-fanout double-counting, only when needed | yes |
| **Dev mode / prod mode** | Every developer works in a personal branch; production reflects a designated branch | yes |
| **Git options ladder** | Off → show links → PRs recommended → PRs required | yes |
| **Code Quality setting** | Can require a clean LookML Validator run before any commit is even allowed | yes |
| **Data tests gate deploy** | Deploy-to-production can require passing data tests | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### Two axes of access control, and the field axis fails invisibly

Looker splits access control the same way Cube does, with different names:

- **`access_filter`** (row axis) — an Explore- or field-level filter driven by a user attribute (e.g., `region: {user_attribute_name: region}`), restricting which *rows* a query can return.
- **`access_grant`** + **`required_access_grants`** (field axis) — an `access_grant` names a user attribute and its allowed values; `required_access_grants` is then attached to an Explore, a join, a view, or an individual field. A user lacking the grant loses access to that structure.

The critical UX detail: **unauthorized fields are absent, not rejected.** Per the docs, "users who don't have access to all of the access grants assigned to the field won't have access to the field. They won't see the field in the field picker while exploring." There is no 403, no greyed-out row, no visible evidence the field ever existed for that user — it is simply not there. This is a stronger governance posture than most tools: a user with a narrower grant can't even discover the existence of restricted fields by probing the UI.

### Symmetric aggregates — the canonical argument for a declared model

This is the sharpest artifact in the category for why a compiled model beats raw SQL. The failure mode: join `orders` (three rows, `SUM(total) = $124.84`) to `order_items` on `order_id` with a one-to-many relationship, then `SUM(total)` again post-join. Because each order row is now repeated once per line item, the naive sum comes back as **$223.44** — order 1's $50.36 counted twice, order 2's $24.12 counted three times.

Looker's fix, generated automatically into the compiled SQL: `SUM(DISTINCT <hash of primary key, total>) - SUM(DISTINCT <hash of primary key>)`, using a large unique number derived from the declared primary key so that repeated rows collapse to one contribution regardless of join fanout. Two declarations make this possible, and only these two:

- a **primary key** declared on the base view (`primary_key: yes` on a dimension, non-null, unique)
- the **join relationship** (`relationship: one_to_many` / `many_to_many`) that tells Looker fanout is possible

**Looker only applies the rewrite when it detects fanout is actually possible** — "when an aggregation will work properly without the need for symmetric aggregates, Looker detects this automatically and doesn't use the function," avoiding the performance cost of `SUM(DISTINCT ...)` on joins that don't need it.

The argument this makes for a declared model over a raw schema: **the engine guarantees a correctness property the user never asked for and might not know to ask for.** Nobody writing `SELECT SUM(total) FROM orders JOIN order_items` thinks to add `DISTINCT`-on-hashed-key logic — the bug is invisible until someone notices the total is impossible. A model that knows the primary key and the join cardinality can silently prevent the entire bug class. (Malloy — see `malloy.md` — solves the identical problem a different way: structurally, in the query language itself, rather than via a runtime rewrite triggered by declared metadata.)

### Dev mode / prod mode, and the git ladder

Every Looker developer works in a personal branch (dev mode); production reflects a single designated branch. Git integration is configured on a ladder of increasing rigor:

- **Off** — no external git links shown
- **Show links** — links out to the git provider, no enforcement
- **Pull requests recommended** — developers *can* open a PR but can bypass it
- **Pull requests required** — merges to production must go through the git provider's PR review/approval flow; cannot be bypassed

### Code Quality — a validator gate before commit even happens

The **Code Quality** project setting has three positions: require fixing errors *and* warnings before a commit is allowed, require fixing errors only (warnings permitted), or allow committing broken code (not recommended). This runs the LookML Validator **before the commit lands**, not as CI after the fact — a stricter gate than most systems, which validate post-merge.

Separately, **data tests can gate the production deploy**: if a project has one or more `test` parameters, the setting to require data tests to pass before deploying to production forces developers through a "Run Tests" step after commit and before their changes can go live. Commit-time validation and deploy-time testing are two distinct, independently configurable gates.

## Worth avoiding

- LookML's fanout-safety is a **runtime rewrite triggered by metadata** (primary key + relationship declarations), not a language-level guarantee. If a developer declares the wrong relationship (e.g., mislabels a `many_to_many` join as `one_to_one`), Looker won't know to protect the aggregate — the correctness depends on the model author getting the join cardinality declaration right, which is exactly the kind of manual metadata that rots. Malloy's alternative (encode the graph in the query language itself) is structurally harder to get wrong in the same way.
- The field-axis "just vanishes" UX is powerful for governance but can be a debugging trap for legitimate users: a field silently missing from the picker looks identical to a field that was never modeled, with no error to search for.

## Facts & figures

- Symmetric aggregate worked example (Google Cloud docs): naive post-join `SUM(total)` = $223.44 vs. correct pre-join total $124.84, across 3 orders / 7 items.
- Git provider support: GitHub, GitLab, Bitbucket Cloud, Bitbucket Server.
- Code Quality has exactly three settings; the strictest ("require fixing errors and warnings") is Google's documented recommendation.

## Sources

- [access_grant](https://docs.cloud.google.com/looker/docs/reference/param-model-access-grant) · [required_access_grants (fields)](https://docs.cloud.google.com/looker/docs/reference/param-field-required-access-grants) · [required_access_grants (Explores)](https://docs.cloud.google.com/looker/docs/reference/param-explore-required-access-grants) · [required_access_grants (views)](https://cloud.google.com/looker/docs/reference/param-view-required-access-grants) · [required_access_grants (joins)](https://docs.cloud.google.com/looker/docs/reference/param-explore-join-required-access-grants)
- [Access control and permission management](https://docs.cloud.google.com/looker/docs/access-control-and-permission-management)
- [symmetric_aggregates parameter](https://docs.cloud.google.com/looker/docs/reference/param-explore-symmetric-aggregates) · [Understanding symmetric aggregates](https://docs.cloud.google.com/looker/docs/best-practices/understanding-symmetric-aggregates)
- [Configuring project version control settings (git options / Code Quality)](https://docs.cloud.google.com/looker/docs/git-options)
- [Using version control and deploying](https://docs.cloud.google.com/looker/docs/version-control-and-deploying-changes)
- [Validating your LookML](https://docs.cloud.google.com/looker/docs/lookml-validation)
- [test parameter reference](https://cloud.google.com/looker/docs/reference/param-model-test)
- **Not directly verified:** exact SQL Looker emits for symmetric aggregates was paraphrased from secondary sources (Data Engineer Things, AnalytxEdge) alongside Google's own conceptual description — not confirmed against a raw generated-SQL example in primary docs.
