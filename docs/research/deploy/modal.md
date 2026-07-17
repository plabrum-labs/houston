# Modal

**What it is:** A Python-first serverless compute platform (functions, GPUs, Sandboxes) whose distinguishing mechanism is checkpoint/restore snapshotting — memory snapshots for warm-boot speed, filesystem snapshots for state continuity across a hard session ceiling.
**Axis:** agent sandbox, infra.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Sandboxes** | gVisor-isolated containers for running untrusted/agent-generated code, addressable and controllable via SDK. |
| **Memory Snapshots** | CRIU-style checkpoint of a container's process tree + memory, restored on subsequent cold starts to skip init work. |
| **Filesystem Snapshots** | Point-in-time save of a Sandbox's filesystem, used to carry state across the 24h Sandbox lifetime ceiling. |
| **Dicts / Queues** | Managed key-value store and FIFO queue primitives, usable as coordination infrastructure between Sandboxes and external clients. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **gVisor isolation** | Sandboxes run inside gVisor, which intercepts syscalls to prevent malicious ones | yes |
| **Memory snapshots** | Checkpoint/restore of the full process tree + memory via gVisor's `runsc`; reused on next boot | yes |
| GPU memory snapshots (alpha) | Extends the same mechanism to include GPU state | maybe — narrow applicability |
| **Filesystem snapshots** | Save/restore filesystem state to work around the 24h Sandbox ceiling | yes |
| **Egress controls** | `outbound_domain_allowlist` (TLS/443 only), `outbound_cidr_allowlist`, `block_network=True`; domain and CIDR allowlists combine additively | yes |
| **Dicts + Queues as coordination layer** | Dicts for session locks/metadata, Queues for routing input across multiple client surfaces into one session | yes |
| Sandbox default timeout | 5 minutes by default, configurable up to 24 hours | yes |

## Worth stealing

### gVisor as the isolation boundary, with a stated caveat

Modal's own framing: Sandboxes run on gVisor, which has *"custom logic to prevent Sandboxes from making malicious system calls, giving you stronger isolation than most other container runtimes."* This is the same isolation primitive Google Cloud Run gen2 uses — see the cross-cutting note in `README.md`: isolation via gVisor/Firecracker is commoditized industry-wide; what differs between vendors is the egress and credential story layered on top, not the sandbox boundary itself.

### Memory snapshots — checkpoint/restore as a cold-start bypass, not a caching trick

The mechanism: gVisor's `runsc` checkpoints the entire process tree and memory state of a running container; a subsequent cold start restores directly into that already-initialized state instead of re-running imports, file reads, and JIT compilation. Modal's reported number: *"practical initialization-heavy Functions often start up 3-10x faster from Memory Snapshots."* The speedup scales with how expensive the skipped initialization was — a function with heavy import-time work benefits far more than a function that does little at import time.

**GPU memory snapshots (alpha)** extend the same checkpoint to CUDA state via `enable_gpu_snapshot`, but with real documented limits: generally incompatible with multi-GPU code, ineffective when the bottleneck is loading model weights from storage rather than snapshot overhead, can conflict with `torch.compile`, and doesn't cover non-CUDA GPU operations. This is the CRIU/memory-snapshot pattern this research set has flagged elsewhere as *"exists to skip expensive Python/CUDA init"* (see `README.md` "Don't build" table) — narrow, real, but not a general-purpose cold-start solution.

### Filesystem snapshots as the workaround for a hard session ceiling

Sandboxes have a **24-hour maximum lifetime** and a **5-minute default idle timeout** (configurable up). Rather than extending the ceiling, Modal's documented pattern is: snapshot the filesystem before the Sandbox would be torn down, then restore into a fresh Sandbox from that snapshot — state continuity is achieved by starting a new session from saved disk state, not by keeping one process alive indefinitely.

### Egress controls — real allow/deny, but port-scoped like Fly's

Three composable knobs: `block_network=True` (hard cutoff, incompatible with the other two — an all-or-nothing switch), `outbound_cidr_allowlist` (IP-range scoped), and `outbound_domain_allowlist` (**TLS/443 connections only**, matched by domain, blocked+logged connections go to the Sandbox's stdout stream). CIDR and domain allowlists combine additively — a request is allowed if it matches either. This is a real domain-aware egress control (unlike Fly's port/protocol-only policy), but it's scoped specifically to TLS on 443 — arbitrary-port or non-TLS outbound traffic isn't governed by the domain allowlist, only by the CIDR list or the network cutoff.

### Dicts and Queues as general-purpose coordination primitives — verified via Ramp's Inspect

Ramp's background coding agent (**Inspect**, detailed in `ramp.md`) uses **Dicts** to hold session locks and image metadata — the shared coordination layer that makes multiplayer sessions (multiple humans/interfaces on one agent session) possible — and **Queues** to route prompts from heterogeneous clients (Slack, web UI, Chrome extension) into the correct running session, decoupling "where a request came from" from "which session state it should mutate." The generalizable lesson: a managed KV store + a managed queue, both addressable from inside and outside the sandbox, is enough to build multi-client session routing without a separate message broker.

## Worth avoiding

- **"Sub-second" cold start is a CPU-only, best-case claim.** Modal's own comparative material distinguishes "warm" (container already running, sub-second) from "cold" (image pull + process start, or GPU attach) — GPU cold starts are reported in the 2–10+ second range depending on model/hardware, with functions generally landing in a 2–4 second cold range. **Treat "sub-second" as unverifiable/marketing outside the narrow CPU-warm case** — consistent with this research set's broader finding that cold-start marketing numbers across the sandbox market are mostly unverifiable (see `README.md` "Numbers not to cite").
- GPU memory snapshots are alpha and incompatible with several common patterns (multi-GPU, storage-bound model loading, `torch.compile`) — not a drop-in speedup for most real GPU-serving workloads yet.

## Facts & figures

- Sandbox default timeout: 5 minutes; configurable up to **24 hours** maximum.
- Memory snapshot reported speedup: **3–10x** faster boot for initialization-heavy functions (vendor-reported).
- Pricing (vendor-reported, verify before quoting externally): Sandboxes priced at roughly **3x** standard Function rates — CPU $0.00003942/core/s vs $0.0000131/core/s standard; memory $0.00000667/GiB/s vs $0.00000222/GiB/s standard.
- Egress domain allowlist restricted to TLS/port 443 only.

## Sources

- [Sandbox overview](https://modal.com/docs/guide/sandbox) · [Networking and security](https://modal.com/docs/guide/sandbox-networking)
- [Memory Snapshots](https://modal.com/docs/guide/memory-snapshot) · [GPU Memory Snapshots blog](https://modal.com/blog/gpu-mem-snapshots)
- [Dicts](https://modal.com/docs/guide/dicts) · [Queues](https://modal.com/docs/guide/queues) · [Use Dicts and Queues together](https://modal.com/docs/guide/dicts-and-queues)
- [How Ramp built a full-context background coding agent on Modal (blog)](https://modal.com/blog/how-ramp-built-a-full-context-background-coding-agent-on-modal) — see also `ramp.md` in this folder
- [Pricing](https://modal.com/pricing)
- **Not directly verified in this pass:** "sub-second" cold-start marketing claims are contradicted by Modal's own GPU cold-start disclosures found via search (2–10+s range) — flagged per the standing house rule that cold-start figures in this market are mostly unverifiable; exact current per-second pricing should be reconfirmed against `modal.com/pricing` before quoting in any external-facing doc, as these rates change.
