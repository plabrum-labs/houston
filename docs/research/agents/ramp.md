# Ramp

**What it is:** Spend-management fintech that ships two separate things we care about — an internal agent sandbox (**Inspect**) and a customer-facing agent line (**Ramp Agents**).
**Axis:** agent platform, agent sandbox.
**Depth:** deep on Inspect and the Agents trust model; **the Agents permission model is not publicly documented** and was not guessed at.

Note: secondary coverage of Inspect is contradictory and unreliable — sources disagree on whether it touches production data. Only `builders.ramp.com` and `modal.com/blog` are primary here.

## Products & surfaces

- **Inspect** — internal background coding agent. Writes Ramp's own product code; reported at ~30% of merged PRs to frontend/backend repos (some accounts say over half) within a couple of months of launch.
- **Ramp Agents** — customer-facing: Policy Agent, AP Agent, Accounting Agent, a procurement fleet.
- **Ramp's workflow builder** — pre-existing product surface, reused as the place agent authority is defined.

## Inspect: the sandbox

This is the interesting artifact. Each session runs in a sandboxed VM **on Modal** containing:

- The **full local dev stack** — Postgres, Redis, Temporal, RabbitMQ, Vite.
- **OpenCode**, a **VS Code server**, and a **web terminal**.
- A **VNC/Chromium stack** for visual frontend verification — the agent can *look at* what it built.

Supporting machinery:

| Concern | Mechanism |
|---|---|
| Cold start | Modal **cron every 30 min** clones repos, installs deps, builds, captures a **filesystem snapshot**. New sandboxes restore from a snapshot at most 30 min stale. |
| Identity | Runs on **the user's own GitHub token** — specifically so a bot can't approve/merge its own code. |
| Coordination | Modal **Dicts** for session locks, **Queues** for routing prompts. |
| Entry points | Slack, web, **Chrome extension**. |
| Integrations | Sentry, Datadog, LaunchDarkly, Braintrust, GitHub, Slack, Buildkite. |

**The shape worth generalizing:** the sandbox exists to give the agent *more* capability, not less — a real machine, real services, real tools, real observability, and a real output channel (a PR). Coding is the first instance of the pattern, not the pattern itself. The generic version is: *snapshot-booted environment + domain tooling + connectivity to the systems the work touches + a reviewable artifact at the end.*

## Ramp Agents: the trust model

From the Builders post *"How To Build Agents Users Can Trust."*

| Mechanism | Detail |
|---|---|
| **Authority lives in the workflow builder** | *"That same workflow builder defines exactly where and when agents can act."* Not a new config surface — the existing one. |
| **Graduated autonomy** | *"suggestions → acting on subsets → full autonomy."* |
| **Hard stops** | Dollar limits, vendor blocklists, category restrictions. Deterministic, outside the model. |
| **Cite your sources** | The Policy Agent *"links directly to sections of the user's expense policy that its reasoning references."* |
| **Escalate on uncertainty** | *"the agent wasn't sure, we fall back to the pre-agent escalation process users are accustomed to."* In production it escalates only the **10–15%** of expenses needing human judgment. |
| **Evals** | *"Evals are the new unit tests."* They use Braintrust. |

Ramp's public AI Principles: *"AI decisions should be auditable and humans should have the final say over decisions that are irreversible."*

## Worth stealing

- **The snapshot-cron pattern.** A scheduled job that pre-builds and snapshots the environment, so session start is a restore rather than a build. Bounded staleness (30 min) as an explicit tradeoff.
- **The sandbox as a *capability* story.** Full stack + browser + terminal + observability integrations. The agent can run the app, look at it, read the traces, and check the feature flags.
- **Agent runs as the human's token**, so the approval boundary is structural — the agent cannot merge its own work.
- **The output is a PR**, i.e. a reviewable artifact in a system that already has review, history, and rollback. Generalizes: whatever the domain, the agent's output should land in a medium that already has a review culture.
- **Authority declared in an existing product surface**, not a new "agent permissions" panel.
- **Graduated autonomy as a shipped ladder**, not a philosophy.
- **Cite-your-sources** — the agent links to the policy text its reasoning used.
- **Escalation to the pre-agent path** — the fallback is the process users already know, not a new one.

## Worth avoiding

- Nothing clearly identified. The main caution is epistemic: most public writing about Inspect is secondary and wrong in both directions.

## Facts & figures

- Inspect: **~30% of merged PRs** (some accounts "over half") within ~2 months. Vendor-reported.
- Snapshot refresh: **every 30 minutes**.
- Policy Agent escalation rate: **10–15%** of expenses. Vendor-reported.
- Runs on **Modal** — see `modal.md`.

## Sources

- [builders.ramp.com](https://builders.ramp.com) — "How To Build Agents Users Can Trust" (primary)
- [modal.com/blog](https://modal.com/blog) — Inspect architecture (primary)
- Ramp AI Principles (primary)
- **Unreliable:** SoftwareSeni, Bunnyshell, firecrawl, "Ry Walker Research" — confidently contradict each other on Inspect's production-data posture. Disregard.
- **Gap:** Ramp Agents' permission model — whether the Policy Agent runs as a service principal with org-wide read or inherits an individual user's scope — is **not publicly documented.**
