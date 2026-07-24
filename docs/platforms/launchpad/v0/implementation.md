# Launchpad — v0 implementation

Building v0 means standing up a Go service that owns an app registry and one Pulumi stack per app,
then teaching it to reconcile a validated configuration into a dedicated ECS task, an ALB routing
rule, a migrated schema, a published frontend, and working DNS. The document runs in a workable
build order; each slice's `Depends on:` line carries the real constraints. The first end-to-end
deploy lands at *Migration runner*.

## Configuration schema and validator

Implements: Configuration schema
Depends on: Nothing

Define the app configuration as a Go type set with a generated JSON Schema, and a validator that
runs before anything else in a deploy.

The schema's top level carries `identity`, `domains`, `capabilities`, `backend`, and `frontend`.
`identity.name` is the root of everything downstream — it derives the namespace, the database
schema, the resource name prefix, and the IAM role name — so it is constrained hard: lowercase
alphanumeric and hyphens, 3–32 characters, must start with a letter, and is immutable once an app
is registered. `backend` carries CPU and memory sizing drawn from a fixed set of ECS-valid pairs,
scaling bounds as `min`/`max` task counts, and a map of non-secret environment variables.
`frontend` carries `type` (`spa` or `static`), the build output directory, and the domain it binds
to. `capabilities` is a map keyed by capability name, each value validated against that
capability's own schema fragment.

Validation is total and happens in one pass, returning every error rather than the first:
structural errors from the JSON Schema, then semantic checks the schema cannot express — an
unknown capability name, a domain claimed by another app, a frontend binding to a domain the app
did not declare, sizing outside the allowed pairs, `min` greater than `max`. Errors carry a JSON
pointer to the offending field so the caller can report the exact line.

The schema is versioned with an explicit `version` field. The validator accepts the current version
and rejects anything else with a message naming the version it expects.

## App registry and deploy API

Implements: Control, The deploy handshake
Depends on: Configuration schema and validator

Stand up the Launchpad service itself: a Go service in Houston's platform schema, with the registry
tables and the HTTP API CI calls.

Two tables in the platform schema. `apps` holds one row per app — its name, its tenant, its current
validated configuration as JSONB, its namespace, and timestamps. `deploys` holds one row per deploy
attempt — the app it belongs to, the configuration and artifact digests it was given, a status, a
failure reason, and start and finish times. Status is an enum, not a string:
`pending → validating → reconciling → migrating → rolling → verifying → complete`, with `failed`
reachable from any non-terminal state. Every transition is written before the work it represents
begins, so a crashed deploy is recoverable by reading where it stopped.

The API is three endpoints. `POST /apps` registers an app and reserves its name. `POST
/apps/{name}/deploys` accepts a configuration and references to the two artifacts and returns a
deploy id immediately, running the deploy asynchronously. `GET /deploys/{id}` returns status and
failure reason. Authentication is Houston's service-to-service credential; the caller's tenant must
match the app's.

The per-app deploy lock is a Postgres advisory lock keyed on the app id, taken for the life of a
deploy. A second deploy for the same app blocks rather than failing, so a rapid push sequence
serializes instead of racing. Deploys for different apps take different locks and run concurrently.
The lock releases with its session, so a crashed service does not strand an app.

## Pulumi state and the per-app stack

Implements: Control, Reconciliation
Depends on: App registry and deploy API

Wire Pulumi's Automation API into the service so reconciliation runs in-process rather than by
shelling out.

State lives in an S3 backend under a prefix Launchpad owns, one stack per app named from the app's
namespace, with the passphrase held in Houston's secret store. The stack's program is an inline Go
function that receives the validated configuration and constructs the app's resources — the same
binary that serves the API constructs the infrastructure, so there is no separate Pulumi project to
version independently.

The substrate every app attaches to — the ECS cluster ARN, the ALB and its listener ARN, the VPC
and its subnets, the Aurora endpoint, the Redis endpoint — is read from `infra/`'s stack outputs
via a stack reference, resolved once at service start and cached. Launchpad never creates these and
never writes to that stack.

Every resource carries a common tag set applied through a stack transformation rather than
per-resource: `houston:app`, `houston:tenant`, `houston:managed-by=launchpad`. The transformation
also enforces the naming prefix, so a resource that escapes the app's namespace is impossible to
construct rather than merely discouraged.

## Namespace, IAM role, and log group

Implements: Baseline
Depends on: Pulumi state and the per-app stack

The first resources the stack program creates, and the ones every app gets regardless of its
configuration.

The app's **task role** is an IAM role the running backend assumes, with a trust policy admitting
only ECS tasks and a permission boundary restricting it to resources tagged with the app's name.
It starts with no permissions beyond the boundary; declared capabilities attach policies to it.
A separate **execution role** — shared across apps, not per-app — lets ECS pull images and write
logs.

A CloudWatch log group per app, named from the namespace with a fixed retention, gives the task
somewhere to write from its first deploy. Where those logs go afterward is the observability
question v0 leaves open; the group exists so nothing is lost in the meantime.

The database schema and its roles are created here too, by calling the data layer's provisioning
path with the app's name — Launchpad requests the schema, the data layer creates it along with the
app's migrator and runtime roles and their grants.

## Ingress routing

Implements: Baseline
Depends on: Pulumi state and the per-app stack

Give the app a routable address before there is anything to route to.

The stack creates a target group of type `ip` pointed at the app's VPC, with a health check against
the backend's health path, and a listener rule on the shared ALB matching the app's Host header and
forwarding to it. Rule priorities are assigned from a range Launchpad owns, allocated from a
sequence in the registry so two concurrent app creations cannot collide on a priority.

The rule matches every domain the app declares, including its default domain, so adding a custom
domain later modifies one rule rather than creating another.

## Dedicated ECS service

Implements: Backend runtime
Depends on: Namespace, IAM role, and log group; Ingress routing

The task definition and the service that runs it — the point at which an app has a backend.

The task definition carries the app's binary as a container image, its CPU and memory from the
configuration, its task role, its log configuration pointing at the app's log group, and its
environment: the configuration's plain variables, plus the Aurora and Redis endpoints injected from
the substrate. Each deploy registers a new revision rather than mutating one.

The ECS service runs on Fargate in private subnets with the app's security group, registers into the
app's target group, and is configured for rolling replacement — `minimumHealthyPercent` at 100 and
`maximumPercent` at 200, so the new task is healthy and registered before the old one drains.
Deployment circuit breaker is on, so ECS itself rolls back a task that never stabilizes. Desired
count sits within the configuration's scaling bounds, with an application autoscaling target
tracking CPU between them.

## Migration runner

Implements: Database migrations
Depends on: Namespace, IAM role, and log group; App registry and deploy API

Run the app's `migrations/` folder against its schema, before the new binary takes traffic.

The runner receives the migration folder as part of the deploy's artifacts and connects as the app's
migrator role — credentials fetched from the secret store at deploy time and never handed to the
app. It sets `search_path` to the app's schema alone, applies pending migrations in order inside a
transaction per migration, and records each in the migration history table the data layer defines.

The runner asserts its own scoping before it runs: the role it connected as must be the app's
migrator role and it must hold DDL rights on exactly one schema. A migration that fails aborts the
deploy at the `migrating` state, leaving the previous task serving and no partial DDL from the
failed file. Migrations already applied stay applied — the forward-only property the design commits
to.

## Deploy lifecycle and health gate

Implements: Deploy lifecycle
Depends on: Dedicated ECS service; Migration runner

Turn the sequence of slices into a lifecycle that either reaches serving or leaves the app alone.

After the service update, the orchestrator polls the ECS deployment and the target group until the
new tasks are healthy and registered, or a timeout elapses. Success advances the deploy to
`complete` and records the new configuration as the app's current one. Timeout or failure stops the
new tasks, leaves the previous task definition serving, and writes `failed` with the reason —
distinguishing a task that never started, one that started and failed health checks, and one that
crash-looped, since these point at different bugs in the app.

Deploy state transitions are written before their work begins, so a service restart mid-deploy finds
deploys stuck in a non-terminal state and marks them failed on startup rather than leaving them
open forever.

## Preview gate and namespace guard

Implements: Reconciliation
Depends on: Pulumi state and the per-app stack

Interpose the safety gate between validation and apply, once there is a real stack to guard.

Every reconciliation runs `preview` first and inspects the resulting change set before applying.
The apply is refused if any change is a delete or replace of a resource on the stateful list — the
database schema, buckets, and anything carrying retained data — or if any changed resource's URN
falls outside the app's namespace prefix. A refusal fails the deploy with the offending resources
named, and applies nothing.

The namespace check is belt-and-braces against the stack transformation: the transformation makes
an out-of-namespace resource hard to construct, and this gate makes one impossible to apply.

## Frontend publish

Implements: Frontend hosting
Depends on: Pulumi state and the per-app stack

Publish the frontend bundle to Cloudflare Pages, independent of the backend rollout.

One Pages project per app per frontend, created by the stack and named from the namespace. The
deploy uploads the build output through the Pages API and promotes the resulting deployment to
production. A `spa` frontend gets a fallback rewrite serving `index.html` for unmatched paths; a
`static` frontend does not, so a missing path is a real 404.

The frontend publish does not gate the backend rollout and the backend rollout does not gate it —
they run concurrently within a deploy, and the deploy completes when both have.

## DNS, TLS, and the default domain

Implements: Domains, DNS, and TLS
Depends on: Ingress routing; Frontend publish

Make the app reachable at the names it declares.

Every app gets a default domain on first registration: a subdomain of Houston's platform zone
derived from the app's name, with a `CNAME` to the Pages project for the frontend and an `A`/`ALIAS`
to the ALB for the API subdomain. The API record is DNS-only — proxying disabled — so backend
traffic reaches AWS without an extra edge hop.

Declared custom domains create the same record pair in the app's own Cloudflare zone, plus a
verification record proving control before Launchpad writes anything else. TLS is Cloudflare-managed
for the frontend, and an ACM certificate validated by DNS for the API domain, requested by the stack
and attached to the ALB listener.

## Capability framework and the first capabilities

Implements: Capabilities
Depends on: Namespace, IAM role, and log group

Generalize capability expansion, then implement three.

A capability is a Go interface: a name, a schema fragment for its configuration, and an expand
function that receives the app's identity and its capability configuration and returns the resources
plus the IAM policy statements to attach to the app's task role. Capabilities are registered in a
map at service start; the validator and the stack program both read that map, so adding a capability
is one registration and no change to either.

**Email** creates an SES domain identity for the app's sending domain, its DKIM records and SPF
entry in the app's zone, and a policy permitting `ses:SendEmail` conditioned on that identity alone.
**Object storage** creates a private bucket in the app's namespace with public access blocked and
a policy scoped to that bucket's ARN. **Secrets** creates one secret per declared key and binds it
into the task definition's `secrets` block, so ECS resolves it at task start and the running backend
reads it from its environment — never calling the secret store itself.
