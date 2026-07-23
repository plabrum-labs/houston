# Ledger — todo

Double-entry accounting primitive — balances, journal entries, reconciliation. Sits alongside
Billing; not Stripe-specific.

- Source: Houston (net-new; confirmed absent from snacks)

## What it is

A double-entry accounting core an app pulls in when it needs real balances and journals —
distinct from Billing, which is payment / subscription-facing.

## To design

- [ ] Account / journal-entry / posting model, with double-entry invariants enforced.
- [ ] Balance computation and reconciliation.
- [ ] Multi-currency posture.
- [ ] Seam with Billing (Stripe events posting to the ledger) and with org / tenant isolation.

## Open questions

- Immutability / audit posture of postings.
