# Durable workflows — todo

Durable execution for multi-step, resumable, retry-aware processes — the orchestration primitive
other platforms lean on instead of each hand-rolling retry/resume logic.

- Source: Houston (net-new)

## What it is

A workflow engine (Temporal-shaped: workflows and activities, durable state, configurable retry
policies with a retryable/non-retryable error distinction, resume-after-crash) that platforms with
long-running or multi-step processes run their logic through instead of building their own
retry-and-resume handling per call site. Candidate consumers: Launchpad's reconciliation and deploy
pipeline (migrate → reconcile infra → health-check → drain), Billing/Ledger sagas (charge →
provision → notify, refunds), Comms/Notifications delivery, and Agent/Builder long-running loops.

## To design

- [ ] Engine choice: self-hosted Temporal, Temporal Cloud, or a lighter alternative — weighed
      against Houston's shared-lightweight-infra, minimal-cost thesis (`vision/overview.md`).
- [ ] Workflow/activity model in Go and how a platform author defines one.
- [ ] Worker deployment shape: one shared fleet across all platforms, or per-platform workers.
- [ ] Retryable vs. non-retryable error taxonomy, and how a platform's activity code declares which
      is which.
- [ ] Seam with Events (`../events/`) — pub/sub vs. durable orchestration are different shapes;
      where the line is when a platform could plausibly use either.
- [ ] Seam with Launchpad — whether Launchpad's own reconciliation runs as a workflow, or only
      consumes this for specific steps (e.g. the migrator's assume-role-after-create wait).
- [ ] A shared "await eventual consistency" activity: a just-created cloud resource (an IAM role's
      trust policy, an ACM/SES validation record, a Cloudflare zone) often isn't immediately usable
      by whatever step comes next. Modeled as an activity with a retry policy — exponential backoff
      with jitter, a max elapsed time, and the activity classifying its own errors as retryable
      (still propagating) vs. non-retryable (genuinely denied, fail fast) — this replaces a
      hand-rolled poll loop at each call site with one reusable primitive, and survives a worker
      crash mid-wait by resuming from persisted history instead of restarting the whole
      reconciliation. Launchpad's migrator assuming a role it just created is the first concrete
      case; the same shape applies anywhere a platform creates a cloud resource another step
      depends on right away.

## Open questions

- Whether this earns its own always-on infrastructure at Houston's current scale, or should start
  as a narrower retry/backoff library until 2-3 consumers genuinely need saga/resume semantics
  rather than plain retry.
- Overlap with Events: could one platform cover both, or are pub/sub fan-out and durable
  step-by-step execution different enough to stay separate.
