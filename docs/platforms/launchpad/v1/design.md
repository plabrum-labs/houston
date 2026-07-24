# Launchpad — v1

Launchpad is Houston's deploy-and-provisioning platform. It is a platform within Houston, not a
separate service: it holds Houston's authority over per-app cloud infrastructure and runs as part
of Houston's flows. Its job is to turn a built app — a backend binary, a frontend build, and a
declared configuration — into running, reachable infrastructure, and to place each app's backend
on the runtime tier its organization is entitled to.

Launchpad works at the per-app altitude. The platform substrate every app shares — the ECS
cluster, the ALB, the Aurora Postgres, the Redis, and the shared scale-to-zero fleet — is
provisioned by Houston's own `infra/` and already exists. Launchpad reads that substrate and
attaches each app to it, provisioning only what belongs to a single app.

## The deploy handshake

An app deploys through Launchpad. During CI the app builds its Go backend binary and its frontend
bundle and emits a configuration in Launchpad's schema. CI hands all three to Launchpad, and
Launchpad drives the deploy: validate the configuration, reconcile the app's infrastructure, run
the app's schema migration, place and roll the backend, publish the frontend, and confirm the app
is serving before the deploy completes.

## Configuration schema

The app authors its configuration as declarative data in a schema Launchpad defines; it never
writes cloud infrastructure directly. The schema expresses the app's **identity** (its name, which
derives its namespace, database schema, resource naming, and cloud identity), its **domains**, its
**capabilities** (opt-in infrastructure declared by name — email, object storage, a queue,
secrets, …), its **backend** sizing and runtime environment, and its **frontend** type and domain
binding. An app cannot declare a raw cloud resource, so it can only ask for what Launchpad has
modeled.

The tier an app runs on is **not** part of this configuration. It is chosen in the Houston UI and
governed by the organization's subscription, not declared by the app.

## Runtime tiers

An app's backend runs in one of two modes, and Launchpad decides which from the app's
organization's entitlement:

1. **Dedicated task** — the app gets its own always-on ECS service, one app per task. The task
   stays warm, so a request never waits on a cold boot, and the app is its own failure domain.
   Launchpad provisions this per app.
2. **Shared fleet** — the app runs on the scale-to-zero fleet operated by Cryo (see `../cryo/`),
   started on demand and reaped when idle. The fleet is shared substrate; Launchpad places the app
   onto it rather than provisioning anything of its own.

Both modes run the same backend binary, so an app is byte-identical in either — only where it runs
and how it is supervised differ.

## Subscription-aware placement

Launchpad reads the organization's subscription level to determine which tier an app is entitled
to, and places the app accordingly. Placement is expressed at the ingress: the app's Host maps
through an ALB listener rule to a target group — its own dedicated target group when entitled, or
the Cryo fleet's target group otherwise.

When an organization's entitlement changes, the app **graduates** between tiers. Graduating to a
dedicated task provisions the app's own service and target group and repoints its listener rule
from the fleet's target group to the dedicated one once the task is healthy; moving the other way
repoints the rule back to the fleet and tears the dedicated service down. Either direction is a
change to the app's routing alone — the app's domain and callers are untouched, and the app serves
continuously through the cutover.

## Baseline

Every app gets a fixed baseline regardless of tier or what its configuration opts into: a
**database schema** of its own, created and migrated within the shared Postgres; a **cloud
identity** — an IAM role scoped to exactly the resources the app owns; **ingress routing** mapping
its Host to its current tier's target group; a **frontend deployment**; and a **default domain**
on which it is reachable with no custom-domain configuration.

## Capabilities

A capability is a named, vetted unit of infrastructure Launchpad knows how to build and wire to an
app. The app declares the capability; Launchpad expands it into concrete resources and grants the
app's role least-privilege access. An app that declares **email** receives an SES sending
identity, its authorizing DKIM and SPF records, and an IAM policy permitting exactly that identity
to send. The capability set is Launchpad's library: adding a kind of infrastructure means modeling
a capability once, after which any app can declare it, and every instance across every app is
built, scoped, and named the same way.

## Reconciliation

Launchpad reconciles an app's declared configuration against what exists in the cloud, using
Pulumi as its execution engine. This runs behind two gates: **validation** of the configuration
against the schema before any infrastructure is touched, and a **preview** that refuses a change
which would destroy or replace a stateful resource or reach outside the app's namespace. Every
resource Launchpad creates for an app lives under that app's namespace, so no app's reconciliation
can name, read, or mutate another app's resources.

## Backend deploys

Deploying rolls the app's backend to the new binary. For a dedicated task, Launchpad rolls the
app's ECS service — start the new task, wait for health checks, drain and stop the old one — so
the deploy touches only that app and serves through the changeover. For a fleet app, Launchpad
publishes the new binary for Cryo to pick up on the backend's next start. Either way the schema
migration runs before the new binary takes traffic, so the binary always meets a schema it
expects.

## Frontend hosting

Launchpad hosts each app's frontend — a single-page app or a static site, both treated as static
build output with an optional SPA-fallback rewrite — on Cloudflare Pages, independent of the
backend's tier. The common shape is three pieces on one domain: the landing site on `domain.com`,
the single-page app on `app.domain.com`, and the backend API on `api.domain.com`.

## Domains, DNS, and TLS

Launchpad manages each app's domain. DNS is served from Cloudflare, where Launchpad points the
frontend at Cloudflare Pages and the API subdomain straight at the AWS backend (DNS-only, no extra
edge hop). TLS uses Cloudflare-managed certificates for the frontend and ACM certificates for the
API. An app that declares only its default domain still gets working DNS and TLS.

## Database migrations

An app's entire migration responsibility is a `migrations/` folder in its repo: the schema-scoped
migration files, and nothing else. The app declares no roles, holds no database credentials, and
never applies its own migrations. As part of a deploy, Launchpad applies that folder against the
app's schema before the new backend takes traffic, under a migrator role that holds DDL rights on
that app's schema alone — never on the platform schema and never on another app's. The running
backend connects under a separate runtime role with no DDL rights, so DDL happens only at deploy
time, under the migrator role, scoped to the one schema. The migration file format and the role
model are owned by Houston's shared data layer; Launchpad is the component that applies them.

## Seams

### Cryo

The seam is one-way: **Launchpad places, Cryo runs.** Launchpad decides that a given app belongs on
the shared fleet and routes its Host to the fleet's target group; Cryo owns everything from there —
starting the backend on demand, supervising it, and reaping it when idle. Launchpad never operates
the fleet, and Cryo never makes placement or entitlement decisions. A free app is simply one whose
Host Launchpad has pointed at the fleet.

### Billing

Billing owns the organization's subscription and what it entitles. Launchpad reads that entitlement
to choose a tier and never interprets, prices, or changes it — an entitlement change is an event
Launchpad reacts to by graduating the app, not a decision it participates in. The dependency runs
one way: Launchpad depends on billing, and billing knows nothing about tiers or placement.

### Data

The data layer owns the logical database: the schema-per-app model, the migrator and runtime roles
and their grants, and the migration file format. Launchpad owns none of it — it is the component
that *applies* a migration, under a role the data layer defines, against a schema the data layer's
model describes. Tier does not enter this seam: an app's schema and roles are identical whichever
tier its backend runs on.

### Snacks and CI

CI produces the three inputs a deploy consumes — the backend binary, the frontend bundle, and the
configuration — and Launchpad consumes all three without building any of them. The configuration
schema is Launchpad's; snacks delivers the app-side primitive that emits a valid one. Because both
tiers run the same binary, CI's output does not depend on where the app will run.

## Boundaries

Launchpad provisions and deploys per-app infrastructure and places each app on its entitled tier.
It does not provision the shared substrate — the ECS cluster, the ALB, Aurora, Redis, and the
fleet are Houston's `infra/` and already exist. It does not build the artifacts it deploys. It
does not run the shared fleet — it points apps at it and lets Cryo run them. It does not own
application data or perform application-level authentication. It is the layer that makes an app's
declared infrastructure real, puts the app on the internet, and decides where its backend runs —
nothing above that, nothing below it.
