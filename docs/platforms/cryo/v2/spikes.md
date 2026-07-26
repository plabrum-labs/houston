# Cryo — v2 spikes

Before Cryo v2 is built, four assumptions its design rests on need to be tested against the real
stack rather than taken on faith. Each spike below names the piece of `design.md` it tests, how to
test it, and the result that would send the design back to the drawing board. The first two gate
the most: if fork latency or memory enforcement don't hold up in situ, the runner's whole
cold-start and isolation story needs rethinking before the scheduler or edge are worth building at
all.

## Fork-to-ready latency

Tests: the **Runner** section's claim that a cold start is cheap enough to hold a request open
with no dedicated buffering component in front of it.

Method: a minimal runner forks a trivial static Go binary onto a unix socket inside a real ECS
task — both a Fargate task and an EC2-backed task — with the isolation from the next spike
(cgroup v2 limits, uid/gid switch) applied, since an unisolated fork wouldn't reflect production.
Measure wall-clock time from fork to the binary's readiness signal to first proxied byte, across
many repeated cold starts and both task types.

Pass/fail: tens of milliseconds, consistently, passes. Latency in the hundreds of milliseconds or
higher means an ordinary request timeout can't absorb a cold hit, and the design needs a
hold-and-buffer component after all.

## Runner-managed memory enforcement

Tests: the **Runner** section's claim that polling each forked backend's RSS and killing and
restarting anything over its budget is enough to protect the ECS task's shared memory ceiling from
a runaway backend, without a kernel-enforced per-process limit.

Method: on a single real ECS task, run a cohort of well-behaved forked backends alongside one
deliberately runaway backend that grows its memory as fast as it can. Run the runner's poll loop
against them at its real interval, and measure the time from budget breach to kill, and the task's
total memory usage — read from the task's own top-level cgroup, which the platform does enforce —
at the moment of the kill, relative to the task's actual memory limit.

Pass/fail: the runaway backend is reliably killed with enough of the task's memory ceiling still
unconsumed that well-behaved siblings are undisturbed, across repeated trials against a
deliberately fast leak. If the leak can outpace the poll interval closely enough to put the task's
own ceiling at risk before the runner reacts, the poll interval or per-backend budget margin needs
rework.

## xDS propagation, end to end

Tests: the **Edge routing** section's claim that a registry change reaches Envoy and reroutes live
traffic within an acceptable window, with no restart.

Method: stand up a minimal `go-control-plane` server reading a key from Redis, connected to a real
Envoy instance over ADS. Change the Redis key (add/remove an endpoint from an app's cluster) and
measure the time until Envoy's routing decisions reflect it, confirmed by observing which
endpoint actually receives traffic.

Pass/fail: sub-second propagation, applied without a restart or dropped connections, passes.
Anything requiring an Envoy restart or reload to pick up a change fails the design as written.

## Scheduler placement consistency under concurrent triggers

Tests: the **Scheduler** section's claim that it is the fleet's only decision-maker — that
concurrent triggers for the same app resolve to one placement decision and one registry write,
never two conflicting ones.

Method: simulate two concurrent placement triggers for the same not-yet-assigned app arriving at
the scheduler at the same instant. Confirm the scheduler serializes them internally and writes
exactly one assignment to the registry, with the second trigger observing and reusing that
assignment rather than producing a competing one.

Pass/fail: exactly one registry entry and one started backend under repeated concurrent trials
passes. Two distinct assignments for the same app is a real bug in the scheduler's internal
serialization, since **Registry** treats every write as authoritative and neither runners nor edge
reconcile conflicting entries.
