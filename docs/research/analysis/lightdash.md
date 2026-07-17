# Lightdash

**What it is:** Open-source BI built directly on a dbt project — dashboards live in version control, and an agent can propose dbt-project edits via pull request.
**Axis:** semantic layer, agent, workflow.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Lightdash** | Open-source BI reading dbt models/metrics/descriptions directly; dashboards-as-code with preview environments. |
| **Preview Projects** | Temporary Lightdash environments spun up from a dbt feature branch, mirroring that branch's state. |
| **AI agent (chat / Slack / MCP)** | Answers questions against the governed semantic layer; can propose dbt-project edits as a PR. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Dashboards as code | Charts/dashboards are version-controlled, testable in CI, reviewed and merged like application code | yes |
| Preview environments per PR | Every dbt PR gets an isolated preview Lightdash environment against dev data before merge | yes |
| AI writeback via PR | Chat-driven agent edits to the dbt project are proposed as a pull request, not applied directly | yes |
| MCP integration | Agents (Slack, UI) query the governed semantic layer rather than generating raw SQL | maybe |

## Worth stealing

**Preview environments validate dashboard changes against dev data before promotion.** A Lightdash "Preview Project" is a full, temporary, isolated environment created from any branch of the connected dbt repo — so a reviewer looking at a PR that changes a dbt model can click through to a live Lightdash instance reflecting *that branch's* schema and data, not just read a diff of YAML. This closes the gap between "the SQL diff looks right" and "the dashboard actually renders correctly" before merge, which is the failure mode most BI-on-dbt setups hit (a model change silently breaks a downstream chart, discovered only in production).

**Agent writes go through the same PR gate as human writes.** Lightdash's AI agent, when asked to edit the dbt project (e.g., add a metric), doesn't apply the change directly — it **opens a pull request**, subjecting agent output to the identical review/CI/merge process as human-authored changes. This is a clean instance of "don't build a separate trust tier for agent output — route it through the review mechanism you already have."

## Worth avoiding

Not enough independent evidence gathered in this pass on scaling limits or where the dbt-coupling becomes a constraint (e.g., non-dbt warehouses, teams not using dbt at all).

## Facts & figures

- Open source: `lightdash/lightdash` on GitHub.

## Sources

- [Dashboards as code docs](https://docs.lightdash.com/guides/developer/dashboards-as-code) · [Lightdash GitHub](https://github.com/lightdash/lightdash) · [Validating dbt before merging with Lightdash Previews](https://driftwave.io/blog/lightdash_previews/) · [Storing dashboards as code builds trust](https://driftwave.io/blog/lightdash_dashboards_code/)
