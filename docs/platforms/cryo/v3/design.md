# Cryo — v3

Cryo is Houston's scale-to-zero runtime for vertical app backends. Hundreds of backends share one
pool of ECS tasks behind a single **scheduler**, **registry**, and **edge** routing layer: each app
sits idle the large majority of the time and costs nothing while it does, and each reaches serving
state fast enough that a cold request waits inside an ordinary request timeout rather than behind a
dedicated buffering component.

Every task in the fleet is identical and runs the same **runner**, so placement is a bin-packing
problem over uniform capacity, and a request never has to be resolved to anything more specific
than the set of tasks currently authorized to serve its app.

## Runner

A runner reconciles a hot/cold assignment against its own local process set. A request for a hot
app proxies straight to its socket; a request for a cold app starts the app, waits for its one-time
readiness signal, then proxies the held connection through.

Starting an app never launches a fresh interpreter. Each task keeps one **base template** process
running continuously — a Python interpreter with Litestar and its ASGI server already imported, and
Litestar's router and DI scaffolding already constructed. The template is **inert**: it holds no
live socket, no database connection, no secret, and no request state, by construction — nothing it
does before a fork can be shared across apps, because it never does anything that produces
shareable state in the first place.

The template is a **fork server**. The runner drives it over a control socket — *fork, mount this
app, bind this socket* — and the template calls `fork(2)` itself, so the runner supervises Python
children without ever hosting a Python interpreter of its own. The child inherits the
already-imported framework state through copy-on-write at effectively zero cost, mounts the app's
own routes onto the already-built Litestar instance, drops to its own uid/gid with capabilities
dropped, and only then opens whatever I/O, connections, or secrets that specific app needs.

That ordering is an entrypoint contract, not a convention. Anything the template opened before
forking would be inherited by every future app forked from it, so the template's inertness is the
isolation boundary rather than a process boundary layered on top of it. Privilege drop obeys the
same logic in the other direction: a child inherits the template's uid and capabilities by default,
so shedding them is the child's own first act, not something the runner can impose from outside.

Each app's dependencies are resolved and packaged in isolation at publish time, independent of the
template and of every sibling process's package set, so two apps pinned to conflicting versions of
the same library coexist on one task without collision. The template shares only the framework
layer, never an app's own dependencies.

A forked child is never reused for a different app. Reclaiming it means killing the process
outright: every page it holds, whether inherited from the template or opened on its own, returns to
the kernel unconditionally on exit, so memory reclaim never depends on Python's garbage collector or
on any in-process cleanup running correctly. The runner polls each child's RSS and kills anything
over its budget, backed by the task's own memory ceiling as the real enforcement point. The template
itself is retired and rebuilt periodically, independent of any app's lifecycle, to bound the memory
fragmentation that accumulates from repeated forking.

A backend holds no durable in-process state — sessions live in Redis, application data in Postgres —
so it starts, stops, or moves to a different task transparently, opening its database pool lazily on
first use and releasing it on exit.

## Scheduler

The scheduler is the fleet's only decision-maker, run independent of every runner. It holds an
**assignment table** — which apps are hot or cold on which tasks — and recomputes it as apps are
added, as traffic shifts, and as an app graduates between tiers. It tracks live tasks and their
reported free capacity, bin-packs new placements, drives the task pool to grow ahead of saturation
and shrink behind it, and migrates apps off sparsely-used tasks in the background to reclaim them.
It is the only component in Cryo that makes a placement decision; a runner only ever executes
whatever assignment it was most recently given.

## Registry

Every assignment the scheduler decides is written to a shared **registry** (Redis) keyed by app,
recording which tasks currently hold it hot or cold. A runner's own assignment is its slice of the
registry, and the edge's routing table is derived from the same data — at the granularity of which
*tasks* are authorized to serve an app, never which processes or sockets exist on them, since a unix
socket never needs to be resolved outside the task it lives on.

## Edge routing

Requests reach Cryo through **Envoy**, configured dynamically over **xDS**. A thin xDS server
watches the registry and streams the current state to every Envoy instance: one cluster per app, its
endpoints the task IPs the registry currently lists for it. Envoy resolves a request's Host header to
a cluster through its route table, then load-balances across that cluster's endpoints — scaling an
app out is nothing more than the scheduler adding a task to its assignment and the next registry push
carrying a longer endpoint list.

Envoy sits behind a **Network Load Balancer**, a dumb L4 front door with no per-app rule or
certificate ceiling. Envoy terminates TLS itself, selecting a certificate by SNI and receiving
certificates over **SDS**, so a newly issued certificate reaches every Envoy instance with no
restart.

## Seams

### Launchpad

Launchpad decides that an app belongs on Cryo's shared fleet rather than a dedicated task, then
registers it with the scheduler; from there the scheduler owns everything about where it runs and the
edge owns everything about how a request reaches it. Cryo never makes a placement or entitlement
decision on its own, and Launchpad never operates the fleet. Cryo's own ingress begins at the NLB;
the domain a request arrives on, its DNS, and its TLS termination in front of that NLB belong to
Launchpad's domain layer, not to Cryo.

## Boundaries

Cryo runs backends, places them across a scaling pool of tasks, and routes traffic to them. It does
not package dependency bundles, does not own application data or perform application-level
authentication, does not provision the ECS clusters, the NLB, or the domains and certificates in
front of it, and does not manage east-west traffic between backends. It supports exactly one
application framework, Litestar; it does not run arbitrary Python web frameworks, does not accelerate
on GPU, and does not manage model weights. It is a process supervisor, a placement scheduler, and a
routing layer, nothing more.

## Not yet designed

- **Dependency bundle packaging.** The exact mechanism (frozen venv, PEX, shiv, or similar) for
  resolving and shipping an app's own dependencies as a self-contained, cacheable artifact.
- **Cost of an app's own initialization.** The template shares only the framework layer, so every
  cold start re-runs the app's own imports and module-level work. Whether that cost is small enough
  to ignore or large enough to need per-app reuse of post-initialization state is unmeasured, and it
  determines whether the fork model is sufficient on its own.
- **Base template recycling policy.** The threshold — fork count, wall-clock age, or both — at which
  a task retires its base template and builds a fresh one.
- **Bundle rollout mechanics.** How a new version of an already-hot app rolls across every task
  currently assigned it without a coordinated multi-task outage.
- **Deleting an app.** Removing it from the assignment table, the registry, and every task that still
  has its bundle cached.
- **Scheduler availability.** Whether the scheduler runs as a single replica behind ECS's own restart,
  or as several replicas coordinating through a lease.
- **Bin-packing against cache locality.** Whether placement should weigh which tasks already have an
  app's dependency bundle cached against raw free capacity.
