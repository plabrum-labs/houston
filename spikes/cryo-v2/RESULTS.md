# Cryo v2 — spike results

Results of running the spikes in `docs/platforms/cryo/v2/spikes.md` against real AWS
infrastructure. Each entry records what ran, the outcome, and anything discovered along the way
that isn't captured by the pass/fail criteria themselves.

## Fork-to-ready latency

**Ran:** 2026-07-25. **Result: pass.** No notable findings beyond the pass/fail criteria.

## Runner-managed memory enforcement

**Ran:** 2026-07-25. **Result: pass, with a design change.**

The spike tested whether `/sys/fs/cgroup` delegation could give each forked backend a real
kernel-enforced memory limit, nested inside the ECS task's own cgroup. It doesn't work on either
substrate:

- **EC2-backed tasks:** `/sys/fs/cgroup` is mounted read-only even with the `SYS_ADMIN` Linux
  capability explicitly added to the task definition — delegation is blocked outright.
- **Fargate tasks:** `memory.max` is writable and reads back whatever you write, giving the
  appearance of a configurable limit, but `memory.current` and `memory.events` — the files a real
  kernel-backed cgroup v2 memory controller exposes — don't exist at all. It's a non-functional
  write-only facade, not real enforcement. Confirmed independently via `/proc/<pid>/status` RSS
  tracking: a test process grew unimpeded past its "limit."

Given this, Cryo v2's Runner manages per-backend memory in userspace instead: the runner polls
each forked backend's RSS via `/proc/<pid>/status` and kills/restarts anything over budget,
backstopped by the ECS task's own memory limit (which genuinely is enforced by Fargate/EC2 at the
task level — only the nested per-process delegation is broken). `docs/platforms/cryo/v2/design.md`
reflects this as the Runner's isolation model.

This is a deliberate risk tradeoff, not a workaround: a runaway backend can transiently pressure
the task's shared memory and potentially affect other backends colocated on the same task before
the runner's watchdog catches it. Acceptable because Cryo v2's target apps are free-tier and their
runtimes are considered ephemeral anyway — strict cross-tenant blast-radius containment isn't worth
chasing after two substrates both failed to deliver real kernel-level isolation. Poll interval and
per-backend memory headroom are the real design levers now, not a "set once" kernel guarantee.

## xDS propagation, end to end

**Ran:** 2026-07-25. **Result: pass.** No notable findings beyond the pass/fail criteria.

## Scheduler placement consistency under concurrent triggers

**Ran:** 2026-07-25. **Result: pass.** No notable findings beyond the pass/fail criteria.
