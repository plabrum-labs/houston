# infra/ — stub (to be designed)

Houston's infrastructure is **not built yet**. This folder is a placeholder.

Houston is a **platform**, not an app that deploys itself, so its infra is a
shared *substrate* — one VPC, one Aurora Postgres, one Redis, one ECS cluster,
one ALB, S3 for per-app Pulumi state, and the Cloudflare zone — that apps attach
to, plus Houston's own control-plane service. That is a fundamentally different
shape from a single-app deploy, so it is being designed **ground-up** rather than
inherited from marlin.

Design happens in a dedicated session, per [`docs/planning/v0.md`](../docs/planning/v0.md)
(`infra/v0`). The CI/CD workflows under `.github/workflows/` (`_infrastructure`,
`_build`, `_deploy_*`) are **kept as scaffolding** and expect a Terraform root
here; they will be wired up when the substrate is designed. Until then they are
inert (no AWS credentials configured), and the `_deploy_*` workflows still encode
marlin's app-deploy model — expect to rework them for the substrate + Pulumi
design.
