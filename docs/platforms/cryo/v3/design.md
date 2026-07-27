# Cryo — v3

Cryo is Houston's scale-to-zero runtime for vertical app backends. It runs two independently
operated **runtimes** — **Cryo-Go** and **Cryo-Python** — each its own pool of ECS tasks, its own
task type, and its own runner implementation, sharing one **scheduler**, one **registry**, and one
**edge** routing layer, since placement and request-routing don't depend on what language a
backend happens to be written in. An app is assigned to exactly one runtime at registration, and
that assignment is fixed: the runtime a request belongs to never has to be inferred, only looked
up.

A runtime is an opaque capacity provider from the scheduler's point of view — a pool of tasks with
free capacity to bin-pack onto — and the scheduler never inspects how a runtime starts, isolates,
or stops a process on its own tasks. That boundary is what lets Cryo-Go and Cryo-Python diverge
completely in their internals while still sharing one placement and routing story.

## Cryo-Go

A Cryo-Go task runs a **runner** that reconciles a hot/cold assignment against its own local
process set. A request for a hot app proxies straight to its socket; a request for a cold app
forks the app's binary — a static, self-contained Go binary, already cached on the task's local
disk or fetched from S3 and checksummed on first use — assigns it a socket, waits for its one-time
readiness signal, then proxies the held connection through. The fork takes tens of milliseconds,
fast enough that the wait fits inside an ordinary request timeout with no dedicated buffering
component. Each forked process runs under its own uid/gid and dropped capabilities; memory is the
runner's own responsibility rather than the kernel's, polling each process's RSS and killing and
restarting anything over its budget, backed by the task's own memory ceiling as the real
enforcement point.

Because each binary is statically linked, many different apps' processes share a task with zero
dependency surface between them — nothing about one app's binary can collide with another's.

A backend holds no durable in-process state — sessions live in Redis, application data in
Postgres — so it starts, stops, or moves to a different task transparently, opening its database
pool lazily on first use and releasing it on exit.

## Cryo-Python

A Cryo-Python task runs a different kind of runner: instead of forking a fresh interpreter for
every cold start, it keeps one **base template** process running continuously per task — an
interpreter with Litestar and its ASGI server already imported, and Litestar's router and DI
scaffolding already constructed. The template is **inert**: it holds no live socket, no database
connection, no secret, and no request state, by construction — nothing it does before a fork can
be shared across apps, because it never does anything that produces shareable state in the first
place.

Starting a cold app forks the template with `fork(2)`, not `fork`-and-`exec` of a fresh binary: the
child inherits the already-imported framework state through copy-on-write, at effectively zero
cost, then mounts the app's own routes onto the already-built Litestar instance and only then
opens whatever I/O, connections, or secrets that specific app needs. This ordering is an
entrypoint contract, not a convention — anything the template opened before forking would be
inherited by every future app forked from it, so the template's inertness is the isolation
boundary, not a process boundary layered on top of it.

Each app's own dependencies are resolved and packaged in isolation at publish time, independent of
the template and of every sibling process's own package set, so two apps pinned to conflicting
versions of the same library coexist on one task without collision — the template only ever
shares the framework layer, never an app's own dependencies.

A forked child is never reused for a different app. Reclaiming it means killing the process
outright: every page it holds, whether inherited from the template or opened on its own, returns
to the kernel unconditionally on exit, so memory reclaim never depends on Python's own garbage
collector or on any in-process cleanup running correctly. The template itself is retired and
rebuilt periodically, independent of any app's lifecycle, to bound the memory fragmentation that
accumulates from repeated forking.

## Scheduler

The scheduler is the fleet's only decision-maker, run independent of every runner. It holds an
**assignment table** per runtime — which apps are hot or cold on which tasks in that runtime's pool
— and recomputes it as apps are added, as traffic shifts, and as an app graduates between tiers.
It tracks each runtime's live tasks and their reported free capacity, bin-packs new placements
within the app's own runtime, drives that runtime's task pool to grow ahead of saturation and
shrink behind it, and migrates apps off sparsely-used tasks in the background to reclaim them. It
is the only component in Cryo that makes a placement decision; a runner only ever executes
whatever assignment it was most recently given.

## Registry

Every assignment the scheduler decides is written to a shared **registry** (Redis) keyed by app,
recording which tasks currently hold it hot or cold. A runtime's own assignment is its slice of the
registry, and the edge's routing table is derived from the same data — at the granularity of which
*tasks* are authorized to serve an app, never which processes or sockets exist on them, since a
unix socket never needs to be resolved outside the task it lives on.

## Edge routing

Requests reach Cryo through **Envoy**, configured dynamically over **xDS**. A thin xDS server
watches the registry and streams the current state to every Envoy instance: one cluster per app,
its endpoints the task IPs the registry currently lists for it, regardless of which runtime those
tasks belong to. Envoy resolves a request's Host header to a cluster through its route table, then
load-balances across that cluster's endpoints — scaling an app out is nothing more than the
scheduler adding a task to its assignment and the next registry push carrying a longer endpoint
list.

Envoy sits behind a **Network Load Balancer**, a dumb L4 front door with no per-app rule or
certificate ceiling. Envoy terminates TLS itself, selecting a certificate by SNI and receiving
certificates over **SDS**, so a newly issued certificate reaches every Envoy instance with no
restart.

## Seams

### Launchpad

Launchpad decides that an app belongs on Cryo's shared fleet rather than a dedicated task, and
which runtime it belongs to, then registers it with the scheduler; from there the scheduler owns
everything about where it runs and the edge owns everything about how a request reaches it. Cryo
never makes a placement, entitlement, or runtime-selection decision on its own, and Launchpad never
operates the fleet. Cryo's own ingress begins at the NLB; the domain a request arrives on, its DNS,
and its TLS termination in front of that NLB belong to Launchpad's domain layer, not to Cryo.

## Boundaries

Cryo runs backends, places them across a scaling pool of tasks per runtime, and routes traffic to
them. It does not build binaries or package Python dependency bundles, does not own application
data or perform application-level authentication, does not provision the ECS clusters, the NLB, or
the domains and certificates in front of it, and does not manage east-west traffic between
backends. Cryo-Python supports exactly one application framework, Litestar; it does not run
arbitrary Python web frameworks, does not accelerate on GPU, and does not manage model weights. It
is a process supervisor, a placement scheduler, and a routing layer, nothing more.

## Not yet designed

- **Python dependency bundle packaging.** The exact mechanism (frozen venv, PEX, shiv, or similar)
  for resolving and shipping an app's own dependencies as a self-contained, cacheable artifact
  analogous to a Go binary in S3.
- **Base template recycling policy.** The threshold — fork count, wall-clock age, or both — at
  which a task retires its base template and builds a fresh one.
- **Binary and bundle rollout mechanics.** How a new version of an already-hot app rolls across
  every task currently assigned it, for both runtimes, without a coordinated multi-task outage.
- **Deleting an app.** Removing it from the assignment table, the registry, and every task that
  still has it cached, for either runtime.
- **Scheduler availability.** Whether the scheduler runs as a single replica behind ECS's own
  restart, or as several replicas coordinating through a lease.
- **Bin-packing against cache locality.** Whether placement should weigh which tasks already have
  an app's binary or dependency bundle cached against raw free capacity.
