# Inngest

**What it is:** Event-driven durable execution platform whose sharpest contribution is a precise, named vocabulary for flow control — the five or six ways you might want to throttle, dedupe, or prioritize function runs, kept as distinct primitives instead of one overloaded "rate limit" knob.
**Axis:** workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Inngest functions** | Event-triggered, step-based durable functions (their unit of durable execution). |
| **Flow control** | Concurrency, throttling, rate limiting, debounce, priority, singleton, batching — configured per function. |
| **Inngest Cloud / self-hosted** | Managed or self-hosted execution + event ingestion. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Concurrency limits | Cap simultaneous executing steps, keyed by tenant/user/resource | yes |
| Throttling | Cap throughput over a time window; **excess is queued** | yes |
| Rate limiting | Cap runs over a time period; **excess is skipped**, not queued | yes |
| Debounce | Dedupe events over a sliding window, run once after the flurry settles | yes |
| Priority | Dynamically reorder execution using data from the triggering event | yes |
| Singleton | At most one run per key; `skip` or `cancel` mode for the new arrival | yes |
| Batching | Collect N events or wait T, process as one function run | yes |

## Worth stealing

### Five knobs that are commonly conflated — kept as separate primitives

Inngest's flow-control vocabulary is worth adopting wholesale because it names distinctions that most systems blur into a single "rate limit" setting:

- **Concurrency limits** — cap how many steps run *simultaneously*, keyed (per user, per tenant, per resource, or globally). This bounds parallelism, not rate.
- **Throttling** — *"Limit the throughput of function execution over a period of time"*, designed for calling third-party APIs with their own rate limits. The defining behavior: **excess work is queued**, not dropped — it runs later, just slower.
- **Rate limiting** — *"Prevent excessive function runs over a given time period by skipping events beyond a specific limit."* This is abuse protection, not throughput shaping — the defining behavior is the opposite of throttling: **excess is skipped**, not queued. Same shape of knob (a limit over a window), opposite failure behavior — this skip-vs-delay split is the whole semantic difference between the two, and it's the detail systems most often get wrong by using one word ("rate limit") for both.
- **Debounce** — de-duplicate events over a sliding window and run once after the flurry settles, avoiding wasted repeated work from bursty triggers (e.g., a user rapidly editing a document — only run downstream processing once they stop).
- **Priority** — dynamically order execution using data from the run itself (a paid tier, an urgent flag) rather than static FIFO.
- **Singleton** — mutual exclusion per key: only one run per key executes at a time, with an explicit choice of what happens to the new arrival — `skip` mode preserves the in-flight run, `cancel` mode kills it and starts fresh with the newer input. This is a different problem than concurrency limits (which allow N-at-once) — singleton is N=1 with an explicit disposition for collisions.
- **Batching** — collect N events or wait T (bounded, e.g. 1–60s), then process the batch as a single function run, trading latency for reduced per-run overhead.

### The queue-anti-pattern framing

Inngest's own framing of what a bare queue leaves unsolved: whether a job *"completes, and what to do if it fails midway are outside the queue's contract."* Their described anti-pattern for teams without durable execution: *"Teams manually write progress to Redis or databases, checking completion status at each step"* — a hand-rolled state table, retry logic that re-checks and skips already-completed sub-operations, and a polling loop checking status every few minutes for anything that waits on a human or external event. **Polling overhead is the tell of a queue used past its contract** — a durable engine's wait primitive (`step.waitForEvent()`, in Inngest's case) suspends at zero compute cost for arbitrarily long instead of requiring a poll loop.

## Worth avoiding

The six flow-control primitives are individually simple but compose in non-obvious ways when stacked on the same function (e.g., a singleton function that's also throttled) — the source material didn't surface documented edge cases here, but it's a natural place for behavior to become hard to reason about; worth testing combinations explicitly rather than assuming independence.

## Facts & figures

- Batch timeout bound: 1s–60s across all Inngest SDKs; hard batch size cap of 10 MiB (vendor docs).
- Singleton key expressions use CEL (Common Expression Language) over the triggering event.

## Sources

- [Flow Control overview](https://www.inngest.com/docs/guides/flow-control) · [Throttling](https://www.inngest.com/docs/guides/throttling) · [Rate limiting](https://www.inngest.com/docs/guides/rate-limiting) · [Singleton Functions](https://www.inngest.com/docs/guides/singleton) · [Batch Processing Events](https://www.inngest.com/docs/guides/batching)
- [Rate Limiting vs Debouncing vs Throttling explained](https://www.inngest.com/blog/rate-limit-debouncing-throttling-explained)
- [When a queue isn't enough](https://www.inngest.com/blog/when-a-queue-isnt-enough) — source of the queue-contract-ends-at-delivery framing (also cited in `restate.md`).
- [AI in production: Managing capacity with flow control](https://www.inngest.com/blog/ai-in-production-managing-capacity-with-flow-control)
