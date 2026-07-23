# Feature flags — todo

Per-tenant / per-app rollout flags.

- Source: Houston (net-new; confirmed absent from snacks)

## What it is

Rollout flags scoped per tenant and per app — turn capabilities on or off without a deploy.

## To design

- [ ] Flag model and evaluation (per-tenant, per-org, per-user targeting).
- [ ] Where flags are stored and how the running backend reads them cheaply.
- [ ] Seam with subscription entitlements (Billing) vs. pure rollout flags.

## Open questions

- Overlap with billing entitlements — one mechanism or two.
