# Launchpad — v0

Launchpad is Houston's deploy-and-provisioning platform. It is a platform within Houston, not a
separate service: it holds Houston's authority over per-app cloud infrastructure and runs as
part of Houston's flows. Its job is to turn a built app — a backend binary, a frontend build, and
a declared configuration — into running, reachable infrastructure. It takes each app from "built
in CI" to "live on the internet with the resources it asked for."

Launchpad works strictly at the per-app altitude. The platform substrate every app shares — the
ECS cluster, the ALB, the Aurora Postgres, the Redis — is provisioned by Houston's own `infra/`
and already exists. Launchpad reads that substrate and attaches each app to it, provisioning only
what belongs to a single app: its dedicated backend task, its routing, its capabilities, its
domain, and its database schema.

## The deploy handshake

An app deploys through Launchpad. During CI the app builds two artifacts — its Go backend binary
and its frontend bundle — and emits a configuration in Launchpad's schema describing what the app
is and what it needs. CI hands all three to Launchpad, and Launchpad drives the deploy from
there: validate the configuration, reconcile the app's infrastructure to match it, run the app's
database migration, roll the backend to the new binary, publish the frontend, and confirm the app
is serving before the deploy is considered done.

## Control

Launchpad is a long-running Houston service, not a step that runs inside CI. It exposes the deploy
API that CI calls, and it holds the state that makes reconciliation safe and repeatable:

- **The app registry** — one record per app, carrying its identity, its current configuration, and
  the state of its most recent deploy. The registry is what makes an app a first-class object in
  Houston rather than a side effect of a CI run, so the Houston UI can show what is deployed and
  what happened last.
- **Infrastructure state** — one Pulumi stack per app, keyed by the app's namespace. Because state
  lives with Launchpad rather than with the caller, a deploy is reconciliation against known prior
  state, not a fresh guess at what exists.
- **A per-app deploy lock** — deploys for one app run one at a time. Two concurrent reconciliations
  of a single namespace would race on the same resources; deploys for *different* apps are
  independent and run concurrently.

## Deploy lifecycle

A deploy either reaches "serving" or it leaves the app as it was. After the migration runs and the
new backend starts, Launchpad holds the deploy open until the new task passes its health checks.
If it does, the old task drains and the deploy is **complete**. If it does not, the new task is
stopped, the previous task keeps serving, and the deploy is **failed** — recorded on the app's
registry record with the reason.

Schema migrations are **forward-only**: a failed deploy does not unwind the migration that preceded
it. An app's migration must therefore be compatible with the binary already running, since that
binary is what continues to serve when a deploy fails. This is the one constraint Launchpad's
deploy model places on how apps write migrations.

## Configuration schema

The app's configuration is the contract between the app and Launchpad. The app authors it as
declarative data in a schema Launchpad defines; the app never writes cloud infrastructure
directly. The schema expresses:

- **Identity** — the app's name, which derives its namespace: its database schema, the naming
  and tagging of every resource Launchpad creates for it, and its cloud identity.
- **Domains** — the domain(s) the app answers on, and which piece of the app serves each.
- **Capabilities** — the opt-in infrastructure the app needs (email, object storage, a queue,
  secrets, …), declared by name rather than by resource.
- **Backend** — sizing and scaling bounds for the app's dedicated task, and its runtime
  environment.
- **Frontend** — whether the frontend is a single-page app or a static site, and the domain it
  binds to.

Everything an app can ask for is something the schema can express and Launchpad knows how to
build. An app cannot declare a raw cloud resource, so it cannot ask for anything Launchpad has
not modeled — which is what keeps every app's footprint validated, least-privilege, and
consistently named by construction.

## Baseline

Every app gets a fixed baseline from Launchpad regardless of what its configuration opts into:

- **A database schema** of its own, created within the shared Postgres and migrated to the app's
  current version.
- **A cloud identity** — an IAM role scoped to exactly the resources the app owns, which the app's
  running backend assumes.
- **A dedicated backend task** — an always-on ECS service running the app's binary.
- **Ingress routing** — a target group and an ALB listener rule mapping the app's Host to its
  task.
- **A frontend deployment** and a **default domain** on which the app is reachable without any
  custom-domain configuration.

Capabilities layer on top of this baseline; the baseline is what an app receives with an
otherwise empty configuration.

## Capabilities

A capability is a named, vetted unit of infrastructure that Launchpad knows how to build and wire
to an app. The app declares the capability; Launchpad expands it into the concrete resources and
grants the app's role least-privilege access to them. For example, an app that declares **email**
receives an SES sending identity, the DKIM and SPF DNS records that authorize it, and an IAM
policy on the app's role permitting exactly that identity to send — the app names "email," and
Launchpad owns everything that makes email work.

The capability set is Launchpad's library, not the app's: adding a new kind of infrastructure to
the platform means modeling a capability once inside Launchpad, after which any app can declare
it. Because Launchpad owns the expansion, every instance of a capability across every app is
built, scoped, and named the same way.

Capabilities that carry credentials resolve at reconcile time, not at runtime. An app's **secrets**
are bound into its task definition when Launchpad reconciles it, so the running backend reads them
from its own environment and never calls a secret store or holds credentials to one.

## Reconciliation

Launchpad reconciles an app's declared configuration against what actually exists in the cloud,
using Pulumi as its execution engine. The app's schema is the desired state; Launchpad translates
it into Pulumi resources and drives them to match. This runs behind two gates:

1. **Validation.** The configuration is checked against Launchpad's schema before any
   infrastructure is touched — an unknown capability, a malformed field, or a name collision is
   rejected at submit time with a clear error.
2. **Preview.** Launchpad previews the reconciliation before applying it and refuses a change that
   would destroy or replace a stateful resource, or that reaches outside the app's own namespace.
   A deploy only applies changes that are safe and in-bounds.

Every resource Launchpad creates for an app lives under that app's namespace, derived from its
identity, so no app's reconciliation can name, read, or mutate another app's resources.

## Backend runtime

Each app's backend runs as its own dedicated, always-on ECS service — one app per task. The task
stays warm, so a request never waits on a cold boot, and a single app is its own failure domain:
a crash, a leak, or a bad deploy is contained to that app and never reaches a neighbor. The task
runs under the app's own IAM role and reaches the shared Postgres and Redis that `infra/`
provides.

Deploying rolls the app's service to the new binary — start the new task, wait for it to pass
health checks, then drain and stop the old one — so a redeploy touches only that app and serves
continuously through the changeover. The service scales between the bounds the app's configuration
declares, independently of every other app.

## Frontend hosting

Launchpad hosts each app's frontend alongside its backend. A frontend is either a single-page app
or a static site; Launchpad treats both as static build output with an optional SPA-fallback
rewrite, so it hosts either without special-casing the framework that produced it. Frontends are
published to Cloudflare Pages, which carries their traffic; the backend stays on AWS.

The common shape for an app is three pieces on one domain — the landing site on `domain.com`, the
single-page app on `app.domain.com`, and the backend API on `api.domain.com` — deployed together
as one app on each Launchpad deploy.

## Domains, DNS, and TLS

Launchpad manages each app's domain. DNS is served from Cloudflare, where Launchpad creates the
records that point an app's frontend at Cloudflare Pages and its API subdomain straight at the
AWS backend, kept DNS-only so backend traffic reaches AWS without an extra edge hop. TLS is
terminated with Cloudflare-managed certificates for the frontend and ACM certificates on the AWS
side for the API. Every app is reachable at a **default domain** — a subdomain of Houston's own
platform domain, derived from the app's identity — the moment it first deploys, so an app that
declares no domain at all is still live and addressable. Custom domains are additive: an app that
declares one answers on both.

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

### Data

The data layer owns the logical database: the schema-per-app model, the migrator and runtime roles
and their grants, and the migration file format. Launchpad owns none of it — it is the component
that *applies* a migration, under a role the data layer defines, against a schema the data layer's
model describes. The dependency runs one way: Launchpad depends on the data layer's role model, and
the data layer knows nothing about deploys.

### Snacks and CI

CI produces the three inputs a deploy consumes — the backend binary, the frontend bundle, and the
configuration — and Launchpad consumes all three without building any of them. The configuration
schema is Launchpad's; snacks delivers the app-side primitive that emits a valid one, so an app
authors its configuration the same way it takes any other platform dependency. The dependency runs
one way: Launchpad depends on CI producing artifacts, and never reaches back into how they are
built.

## Boundaries

Launchpad provisions and deploys per-app infrastructure and nothing beneath it. It does not
provision the shared substrate — the ECS cluster, the ALB, Aurora, and Redis are Houston's
`infra/` and already exist; Launchpad attaches apps to them. It does not build the artifacts it
deploys — CI produces the backend binary and the frontend bundle. It does not run application
code beyond supervising the dedicated task through ECS, and it does not own application data or
perform application-level authentication. It makes no placement decision: every app's backend is a
dedicated task, so there is no tier to choose and nothing about an organization's subscription
reaches Launchpad. It is the layer that makes an app's declared infrastructure real and puts the
app on the internet — nothing above that, nothing below it.

## Not yet designed

- **Observability of the deployed app.** Where a dedicated task's logs and metrics go, and how much
  of that wiring Launchpad owns versus the observability platform.
- **Deleting an app.** Tearing a namespace down, and what happens to its schema and its data.
