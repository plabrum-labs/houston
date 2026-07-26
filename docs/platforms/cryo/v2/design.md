# Cryo — v2

Cryo is Houston's scale-to-zero runtime for vertical app backends. It runs a fleet of ECS tasks,
each holding many small backend processes at once, and exposes them through a routing layer that
dispatches every request to a task authorized to serve it. A **runner** on each task executes a
fixed assignment handed to it — which apps to keep hot, which to keep cold and start on demand —
and reports its state back. A **scheduler** decides that assignment fleet-wide: which apps run
where, when the pool needs to grow or shrink, and when to consolidate a sparse task. An **edge**
layer resolves every request's Host header to the specific tasks currently assigned that app and
load-balances across them.

None of the three needs the others' internals. The runner only ever manages processes on its own
task, the scheduler only ever manages assignments, and the edge only ever manages routing — the
three-way split is what keeps each of them small, and what lets a runner stay a dumb executor
instead of accumulating fleet-wide logic just because it happens to be the thing that runs
backends.

## Runner

The runner is Cryo's only per-task component — a small process that owns its ECS task's single
exposed port and a shared unix-socket directory, and reconciles its local process set against a
**desired-state assignment** it's handed: a **hot** list (keep running continuously, restart on
crash with backoff, a circuit breaker on repeated failure, never idle-reaped) and a **cold** list
(this task is authorized to run it, but doesn't unless a request arrives). A request for a hot
app proxies straight through to its socket. A request for a cold app forks the binary — already
cached on the task's local disk, or fetched from S3 and checksummed on first use — assigns it a
socket, waits for its one-time readiness signal, then proxies the held connection through; the
fork takes tens of milliseconds, so the wait fits inside an ordinary request timeout with no
special buffering. Anything running that isn't in either list is pruned.

Each forked process runs under its own uid/gid and dropped capabilities — isolation nested within
the ECS task's own boundary rather than a bare host's. Memory is the runner's own responsibility
rather than the kernel's: it polls each process's RSS and kills and restarts anything over its
budget, backed by the ECS task's own memory ceiling as the real enforcement point. A process that
outgrows its budget faster than the runner's next poll can pressure that shared ceiling and take
other backends on the same task down with it; Cryo accepts this because its backends are free-tier
and their runtimes already ephemeral, not a cross-tenant isolation guarantee it makes to them. The
runner reports its state — which apps are actually running, and its free capacity — to the
scheduler on a heartbeat and on significant events, and otherwise has no opinion about anything
beyond its own task: it never talks to another runner, never decides what it should be running,
and never routes by Host.

## Scheduler

The scheduler is the fleet's only decision-maker, run as its own service independent of every
runner. It holds the **assignment table** — which apps are hot or cold on which tasks — and
recomputes it as apps are added, as traffic shifts, and as an app graduates between tiers. It
tracks live runner tasks and their reported free capacity, bin-packs new placements onto tasks
with room, drives the runner pool's ECS service to grow ahead of saturation and shrink behind it,
and migrates apps off sparsely-used tasks in the background to reclaim them — gently, since
moving a running app costs it a restart. It is the only component in Cryo that makes a placement
decision; a runner only ever executes whatever assignment it was most recently given.

## Registry

Every assignment the scheduler decides is written to a shared **registry** (Redis) keyed by app,
recording which tasks currently hold it hot or cold. This is the one piece of state both the
runners and the edge read: a runner's own assignment is its slice of the registry, and the edge's
routing table is derived from the same data — at the granularity of which *tasks* are authorized
to serve an app, never which processes or sockets exist on them, since that detail never needs to
leave the task it lives on.

## Edge routing

Requests reach Cryo through **Envoy**, configured dynamically over **xDS** rather than a static
file. A thin xDS server watches the registry and streams the current state to every Envoy
instance: one cluster per app, its endpoints the task IPs the registry currently lists for it.
Envoy resolves a request's Host header to a cluster through its route table, then load-balances
across that cluster's endpoints — the same mechanism whether the app sits on one task or many, so
scaling an app out is nothing more than the scheduler adding a task to its assignment and the next
registry push carrying a longer endpoint list. Envoy health-checks each endpoint itself,
independently of the registry, so a task gone unresponsive stops receiving traffic before the
scheduler's own view has caught up.

The edge resolves which *task* serves a request; the runner resolves which *process on that task*
does. Neither needs the other's internals — a unix socket is unreachable outside the task it lives
on regardless, so the two-hop split isn't a design preference so much as the shape the network
already forces.

Envoy sits behind a **Network Load Balancer** — a dumb, highly available L4 front door with no
per-app rule or certificate ceiling, since it never inspects past the transport layer. Nothing
past the NLB is app-aware except Envoy's own routing table, which is what lets the roster of apps
grow without growing the ingress configuration itself.

Envoy terminates TLS itself, selecting a certificate by SNI and receiving certificates over
**SDS** — the same dynamic-push model xDS uses for routing state, so a newly issued certificate
reaches every Envoy instance with no restart and no per-domain NLB configuration.

## Runtime

A backend is a static Go binary that accepts connections on the socket its runner provides,
signals readiness once, and serves requests. It holds no durable in-process state — sessions live
in Redis, application data in Postgres — so it can be started, stopped, or reassigned to a
different task transparently. It opens its database pool lazily on first use and releases it on
exit, so a stopped backend holds no connections. Binaries live in S3; a runner fetches, verifies,
and caches one on first use, and LRU-evicts cold ones from its task's local disk. Scheduled and
queued jobs run in a separate always-on worker fleet backed by Redis, independent of runners
entirely, so a stopped backend never blocks job execution.

## Seams

### Launchpad

Launchpad decides that an app belongs on Cryo's shared fleet rather than a dedicated task, and
registers it with the scheduler; from there the scheduler owns everything about where it runs and
the edge owns everything about how a request reaches it. Cryo never makes a placement or
entitlement decision, and Launchpad never operates the fleet. Cryo's own ingress begins at the
NLB; the domain a request arrives on, its DNS, and its TLS termination in front of that NLB belong
to Launchpad's domain layer, not to Cryo.

## Boundaries

Cryo runs backends, places them across a scaling pool of tasks, and routes traffic to them. It
does not build binaries, does not own application data or perform application-level
authentication, does not provision the ECS cluster, the NLB, or the domains and certificates in
front of it — those are Houston's infra and Launchpad's domain layer — and does not manage
east-west traffic between backends. It is a process supervisor, a placement scheduler, and a
routing layer, nothing more.

## Cost profile

**Per-backend footprint** is unchanged from the fleet's basic economics: an idle backend consumes
nothing; a running one holds ~15–25 MB RSS and near-zero CPU between requests.

**Fixed overhead** grows by a few small, stateless pieces beyond the runner pool itself: the
scheduler, the xDS translator, and the Envoy fleet sitting behind the NLB. None holds per-app
state beyond what's in the registry, so none scales with the size of the roster — only with
request volume.

**Scale-to-zero economics carry through unchanged**: steady-state compute tracks the concurrently
active set, not the total roster, and the roster itself is bounded only by registry entries and,
where cached, the disk each task's binaries occupy.

## Not yet designed

- **Binary rollout mechanics.** How a new version of an already-hot app rolls across every task
  currently assigned it without a coordinated multi-task outage.
- **Deleting an app.** Removing it from the assignment table, the registry, and every task that
  still has it cached.
- **Scheduler availability.** Whether the scheduler runs as a single replica behind ECS's own
  restart, or as several replicas coordinating through a lease — and what a runner does with a
  stale assignment if the scheduler is briefly unreachable.
- **Bin-packing against cache locality.** The scheduler places new assignments by free capacity
  alone, with no visibility into which tasks already have an app's binary cached locally; a
  runner's LRU eviction likewise proceeds with no signal back to the scheduler when it invalidates
  a task's cache locality. Whether placement should weigh cache locality against capacity, and how
  the two components would share that signal, isn't yet designed.
