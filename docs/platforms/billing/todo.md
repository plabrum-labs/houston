# Billing — todo

Subscription and payment handling via Stripe.

- Source: snacks (port)

## What it is

The subscription / payment primitive an app pulls in to charge its customers — the mechanism
behind Houston's success case: an app charging a SaaS fee via Houston.

## To design

- [ ] Port the snacks billing / Stripe integration to Go.
- [ ] Subscription model: plans, entitlements, per-org subscription state.
- [ ] Seam with Launchpad's subscription-aware placement (v1) — the entitlement that decides an
      app's runtime tier reads from here.
- [ ] Relationship to Ledger (`../ledger/`): Billing is Stripe-facing; Ledger is the
      double-entry accounting primitive alongside it.

## Open questions

- Where the org's subscription-tier entitlement is owned and read by Launchpad.
