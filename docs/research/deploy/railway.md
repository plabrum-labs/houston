# Railway, Render, Northflank

**What they are:** Three PaaS variants on the same theme — Railway and Render both do git-driven preview environments with different granularity tradeoffs; Northflank is the reference for BYOC (Bring Your Own Cloud), the vocabulary enterprises actually mean when they say "self-hosted."
**Axis:** deploy.
**Depth:** thin (per file convention — short entries).

## Railway

**PR Environments** clone the **entire base environment** — services, networking, and variables — into an isolated ephemeral environment on PR open, by default inheriting from production (configurable). Each PR environment gets fresh databases/dependencies, unique per-service URLs, and **isolated private networking** — services in one PR environment cannot reach services in another PR environment over the private network. Sealed variables are deliberately excluded from the clone; regular variables are inherited. Destroyed on merge/close.

**Focused PR Environments** address the obvious cost of full-clone-per-PR: per-service **watch paths** let Railway determine which services a given PR actually touched, and skip provisioning/redeploying the untouched ones. A monorepo PR that only changes `frontend/` doesn't spin up a fresh backend. Toggle: Project Settings → Environments → PR Environments → Enable Focused PR Environments.

**Steal:** the pairing of "clone everything by default" with "opt into path-based scoping" — full fidelity is the safe default, the watch-path mechanism is the deliberate cost-reduction escape hatch, not the other way around.

## Render

Preview environments are driven by a `render.yaml` Blueprint file. Setting `previews.generation: automatic` makes Render **create a full preview environment for every PR** against the Blueprint's linked branch — fresh instances of every service and datastore declared in the Blueprint, **without copying production data**. An `initialDeployHook` can run setup/seeding on first deploy. Cost control via `previews.plan`/`previewPlan` to use smaller instance sizes than production. Auto-destroyed on merge/close; `previews.expireAfterDays` also reaps inactive preview environments on a timer. Billed at standard rates, prorated by the second.

Separately, simpler **Service Previews** exist for a single service (not the full Blueprint) — a temporary instance with its own URL, copying the base service's settings/env vars, auto-deleted on PR merge/close, tagged `noindex`.

**Steal:** declaring the entire preview topology in one committed config file (`render.yaml`) rather than inferring it from repo structure — the preview environment's shape is explicit and versioned, not implicit.

## Northflank — BYOC

**BYOC (Bring Your Own Cloud):** deploy Northflank-orchestrated workloads into the *customer's own* AWS/GCP/Azure/Oracle/CoreWeave/on-prem/bare-metal account — services, databases, background jobs, CI/CD, GitOps, preview environments, GPU workloads, and microVM sandbox isolation all run **inside the customer's infrastructure and account**, not Northflank's.

**The vocabulary distinction that matters:** Northflank still operates the control plane — cluster lifecycle, deployment pipelines, upgrades, patches, the UI/CLI/API — as a managed service; the customer doesn't touch Kubernetes directly. Only the *runtime and data plane* (containers, databases, secrets, GPU jobs) live in the customer's account. This is **BYOC**, not self-hosted: the vendor still operates the platform, inside your infrastructure. **Self-hosted** would mean the customer runs the control plane too. Enterprises asking for "self-hosted" are very often actually describing BYOC — they want data residency, network control, and cloud-billing consolidation, not the operational burden of running the platform itself.

**Porter** is the lighter comparison point: also Heroku-like DX deployed into the customer's own AWS/GCP/Azure account, handling Kubernetes setup/networking/TLS/autoscaling/CI-CD — but explicitly **without** managed databases, GPU workloads, or microVM sandbox isolation. Porter covers standard web-workload BYOC; Northflank adds the data-plane and GPU/isolation surface on top.

**Steal:** the vocabulary itself. "BYOC" vs. "self-hosted" is a real, load-bearing distinction for enterprise sales conversations — who operates the control plane is the actual question being asked, not where the bytes live.

## Sources

- [Railway PR Environments guide](https://docs.railway.com/guides/preview-deployments-with-pr-environments) · [Railway Environments docs](https://docs.railway.com/environments) · [CI/CD for Modern Deployment (Railway blog)](https://blog.railway.com/p/cicd-for-modern-deployment-from-manual-deploys-to-pr-environments)
- [Render Preview Environments](https://render.com/docs/preview-environments) · [Render PR previews (Service Previews)](https://render.com/docs/pull-request-previews)
- [Northflank BYOC](https://northflank.com/product/bring-your-own-cloud) · [Best options for BYOC in 2026 (Northflank blog)](https://northflank.com/blog/best-options-for-byoc-in-cloud-computing) · [What's the best PaaS that runs in my own cloud account? (Northflank blog)](https://northflank.com/blog/best-paas-that-runs-in-my-own-cloud-account-bypc-self-hosted-paas)
- **Not directly verified in this pass:** Porter's current feature set was characterized via a third-party (Northflank) comparison blog rather than Porter's own docs — worth a direct check of porter.run before quoting the "no managed DBs/GPU/microVM isolation" claim externally, since it's a competitor's framing of Porter.
