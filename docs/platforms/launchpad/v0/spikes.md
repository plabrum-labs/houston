# Launchpad — v0 spikes

Before Launchpad reconciles real app infrastructure, three assumptions its `design.md` rests on
need to be proven against a real Pulumi program in Go rather than read off documentation. Each
spike below names the claim it tests, how to test it, and the result that would send the
reconciliation model back to the drawing board. The first gates the other two: neither protection
nor credential scoping mean much until a reconciliation can actually reach both providers arive's
story depends on, in one pass.

## Cross-provider reconciliation, end to end

Tests: the **Reconciliation** section's claim that a single reconciliation drives an app's
infrastructure to match its config, and the **Domains, DNS, and TLS** section's claim that an app's
default domain, TLS, and email capability all come up together with no manual DNS step.

Method: one Go Automation API program, driving both the `aws` and `cloudflare` Pulumi providers in
a single stack, provisions a throwaway app end to end — an ACM certificate for its API subdomain
and an SES domain identity for its email capability on the AWS side, each of which returns a DNS
validation record as an output. The program takes that output and creates the corresponding
Cloudflare DNS record from it, in the same `up`. Confirm the ACM certificate reaches `ISSUED` and
the SES identity reaches `Verified` without a manually entered DNS record or a second `pulumi up`.

Pass/fail: both resources validate from records the program itself created, and the whole chain
completes in one reconciliation, passes. Needing a human to copy a validation record between
providers, or a second run to pick up state the first didn't wait for, means the reconciliation
model needs an explicit multi-pass or polling step Launchpad doesn't yet account for.

## Protected resource under a bad reconciliation

Tests: the **Reconciliation** section's claim that a stateful resource — an app's database schema
and role — cannot be destroyed or replaced as a side effect of reconciling a declared
configuration, only through a distinct, deliberate deletion.

Method: provision an app's `postgresql.Schema` and `postgresql.Role` as protected resources keyed
by an immutable app id. Then reconcile a deliberately bad configuration against the same stack —
one that changes the app's mutable display name and any other field derived from it — through the
same Automation API path Launchpad would use, with no human reviewing the diff in between. Confirm
Pulumi refuses the operation rather than silently dropping and recreating the schema.

Pass/fail: the reconciliation errors out and the schema and role are untouched, passes. Any path by
which an ordinary config change reaches a drop or recreate of a protected resource is a defect in
the protection model, not a case Launchpad can route around later.

## Per-app credential scoping across providers

Tests: the **Isolation** claim (Reconciliation section) that one app's reconciliation holds no
credential that reaches another app's resources — proven for AWS by assume-role scoping per stack,
but not yet checked against Cloudflare's credential model.

Method: provision two apps' stacks, each under its own scoped credential — an assumed AWS IAM role
per stack, and the narrowest Cloudflare API token scope available per stack (per-zone or finer).
From one app's stack, attempt to read or modify a resource belonging to the other app's zone or
account, using only the credential that stack holds.

Pass/fail: the attempt is rejected by Cloudflare's own permission model, on par with the AWS
assume-role boundary, passes. If Cloudflare's token granularity can't express a boundary narrower
than the whole account, Launchpad's namespace isolation holds on the AWS side only, and needs a
second mechanism — most likely enforced naming discipline within the program itself — to cover
Cloudflare.
