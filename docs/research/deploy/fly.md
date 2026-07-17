# Fly.io

**What it is:** A low-level Machines API for fast-launching Firecracker VMs, plus a proxy layer (Fly Proxy) that implements autostop/autostart, regional routing, and `fly-replay` request forwarding on top of it. The most honest first-party numbers in this market on both cold-start and the limits of its own mechanisms.
**Axis:** deploy, infra, runtime.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Fly Machines** | Firecracker microVMs, individually addressable and API-controlled — not a scheduler abstraction, the actual unit. |
| **Machines API** | REST API for creating/starting/stopping/suspending Machines directly; the substrate `fly deploy`, `fly scale`, and third-party tools all sit on top of. |
| **Fly Proxy** | Edge routing layer: TLS termination, autostop/autostart, `fly-replay` request forwarding, network policies. |
| **Managed Postgres (MPG)** | Fly-operated Postgres clusters in a fixed regional list. |
| **6PN** | Automatic private IPv6 mesh network joining every app in an org. |
| **Volumes** | Local NVMe-backed persistent disks attached to a Machine. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Machines API as the whole product** | Everything (deploys, scale-to-zero, region placement) is this one REST API; `fly` CLI is just a client of it | yes |
| Autostop/autostart formula | `excess = num_machines - (num_over_soft_limit + 1)`; stops/starts at most one Machine per region per pass, every few minutes | yes |
| **Autostop never creates/destroys Machines** | Only ever acts on Machines that already exist — max concurrency ceiling is whatever `fly scale count` pre-created | yes — as a documented limit to design around |
| Suspend vs stop | Suspend snapshots full VM state (CPU/memory/network) to disk; resume in "a few hundred ms" vs ~2s cold stop/start; billed identically to stopped (storage only) | yes |
| `fly-replay` | A response header that re-routes a request to a different region, Machine, or app — no client redirect round-trip | yes |
| Network policies | Port/protocol allow/deny rules on Machine ingress/egress | maybe — see caveat below |
| 6PN | Every app gets automatic private IPv6 mesh connectivity; custom 6PNs give per-tenant isolated networks | yes |

## Worth stealing

### The Machines API is the product

Fly's own framing (blog): Machines are meant to be driven by *anything* — the CLI, your own control plane, a customer-facing UI. There is no separate "deployment object" hidden behind an opinionated scheduler; a Machine is directly created, started, stopped, or updated via one REST call, and higher-level Fly tooling (`fly deploy`, autoscaling blueprints) is implemented *as a client of that same API*, not as privileged internal machinery. This is the architecture lesson: build the primitive as a real API first, then build convenience layers on top of it, rather than baking convenience into the primitive.

### Autostop/autostart — the formula and its explicit boundary

Fly Proxy periodically (**"every few minutes"**) checks each region for excess capacity using each Machine's `concurrency.soft_limit`:

```
excess = num_machines - (num_machines_over_soft_limit + 1)
```

If excess ≥ 1, the proxy stops (or suspends) **one Machine per region per pass** — not a batch, one at a time. Autostart runs the inverse check: if every running Machine in the nearest region is over its soft limit, the proxy starts one stopped/suspended Machine. `min_machines_running = 0` combined with `auto_stop_machines = "stop"` is the default for `fly launch`-created apps — true scale-to-zero by default, not an opt-in.

**The documented boundary that actually matters for capacity planning**: *"Fly Proxy autostop/autostart never creates or destroys Machines for you."* The count of Machines that can ever be running is capped by whatever `fly scale count` provisioned — autostop only toggles state on a fixed pool, it is not autoscaling in the "spin up new capacity" sense. Two further documented caveats: `min_machines_running` **only applies to the app's primary region**, not others; and at large fleet sizes, the docs concede the per-pass, one-Machine-per-region throttle **can't keep up** — at thousands of Machines, the stop loop falls behind and idle Machines stay running longer than the policy intends, pushing Fly's own guidance toward "one app per tenant" architectures for extreme scale rather than one giant app with thousands of Machines.

### Suspend vs stop — a real state-preservation tradeoff, not just a naming difference

**Stop** is a cold shutdown; restart takes about the same as any cold boot (~2s for a typical app). **Suspend** snapshots the entire VM state — CPU registers, memory, network — to disk via Firecracker's own snapshot mechanism, and resume "picks up exactly where it left off, without rebooting the OS or restarting your app," in a few hundred milliseconds. Both are billed identically (storage only while stopped/suspended — no CPU/RAM charge). The tradeoffs that make suspend non-default: **snapshots are not durable** — discarded on deploy (new code + old memory state is "unsafe and unpredictable"), host migration, or hardware failure, so *"always design for both resume and cold start paths"*; eligible Machines must be ≤2GB memory, no swap, no scheduled starts, no GPU. This is a genuinely honest constraint list, not marketing.

### `fly-replay` — proxy-level request forwarding, not a redirect

A response header (`fly-replay: region=nrt` or `app=customer-app-123` or targeting a specific Machine) tells Fly Proxy to resend the *original* request to a different region/Machine/app — the client never sees a redirect round-trip. The canonical use case: a read replica in Tokyo receives a write, replies with `fly-replay` pointing at the primary in Virginia, and the proxy transparently forwards it. Combined with custom 6PNs, the same mechanism lets a public "router" app forward requests into a customer's private per-tenant app/network without exposing that app publicly — a clean multi-tenant routing primitive built entirely out of proxy behavior, no service mesh required.

## Worth avoiding

### Network policies are port/protocol only — not an egress control

Fly's Network Policies let you allow/deny ingress/egress by port and protocol (e.g. "allow TCP 5432 outbound"). They **cannot express domain-based rules** like "allow only github.com" — there is no hostname-aware egress filtering. Once you create any rule for a direction, the default for that direction flips to deny-all, so it is useful for locking a Machine down to a known set of ports. But the documentation states directly: **"Network policies only apply to traffic directly to and from Machines. They do not affect traffic routed through the Fly Proxy."** That means the policy has a hole exactly where most traffic actually flows — anything going through the proxy layer (which is most inbound and a lot of app-to-app traffic) is unaffected. This is not an exfiltration control; it's a coarse firewall for direct Machine sockets.

### Scale ceiling is proxy responsiveness, not compute

At thousands of Machines in a single app, the autostop loop's one-region-one-Machine-per-pass cadence can't keep idle Machines stopped fast enough — Fly's own community guidance for multi-tenant platforms is **one app per tenant**, explicitly to keep each app's Machine count in the range where the proxy's stop/start loop stays effective, rather than one giant multi-tenant app with an unbounded Machine count.

### Cold-start honesty, with a gap right after start

Fly publishes real numbers: **~2s cold start**, **few-hundred-ms resume from suspend**. But there's a second documented gap worth carrying forward: after a Machine starts, *"there may be a short delay before all proxy nodes recognize that it is running,"* which can cause a handful of initial requests to fail or route to the wrong (still-starting) Machine before the fleet converges. Autostart solves "is a Machine running" faster than it solves "does every proxy node know it."

## Facts & figures

- Autostop check cadence: every few minutes; stops/starts at most one Machine per region per pass.
- `excess = num_machines - (num_machines_over_soft_limit + 1)`.
- Default for `fly launch` apps: `min_machines_running = 0`, `auto_stop_machines = "stop"`.
- Cold start: **~2s** (documented, e.g. Rails-class app). Suspend resume: **a few hundred ms**.
- Suspend eligibility: ≤2GB memory, no swap, no scheduled starts, no GPU.
- Managed Postgres regions: AMS, FRA, LHR, IAD, LAX, GRU, NRT, ORD, SIN, SJC, SYD, YYZ.
- `min_machines_running` applies to the app's **primary region only**.

## Sources

- [Machines overview](https://fly.io/docs/machines/overview/) · [Fly Machines: an API for fast-booting VMs (blog)](https://fly.io/blog/fly-machines/)
- [Fly Proxy autostop/autostart](https://fly.io/docs/reference/fly-proxy-autostop-autostart/) · [Autostop/autostart Machines](https://fly.io/docs/launch/autostop-autostart/)
- [Machine Suspend and Resume](https://fly.io/docs/reference/suspend-resume/)
- [Network Policies](https://fly.io/docs/machines/guides-examples/network-policies/)
- [Dynamic Request Routing with fly-replay](https://fly.io/docs/networking/dynamic-request-routing/) · [Multi-region databases and fly-replay](https://fly.io/docs/blueprints/multi-region-fly-replay/)
- [Custom private networks (6PN)](https://fly.io/docs/networking/custom-private-networks/)
- [Managed Postgres](https://fly.io/docs/mpg/)
- **Not directly verified in this pass:** exact wording of "an API, and anything can drive it" as a literal quote (paraphrase of Fly's stated philosophy across blog/docs, not confirmed verbatim in currently reachable pages); precise per-region Fly Proxy convergence delay duration after Machine start (documented as "a short delay," no figure given).
