# Estuary

**What it is:** Streaming-first data movement platform (Estuary Flow) — CDC and batch sources land in a durable, replayable log rather than being pulled fresh on every sync, then fan out to many destinations from that one log.
**Axis:** data migration (ingestion), workflow.
**Depth:** thin/medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Estuary Flow** | Captures (source → durable collection), Materializations (collection → destination). |
| **Collections** | The durable log itself — append-only, replayable, of unlimited size. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Durable collection log** | Capture once into a replayable, append-only log; fan out to many destinations from the same log | yes |
| **Backfill-then-tail** | Capture starts by backfilling current state, then transitions to ongoing change capture from the same task | yes |
| **Exactly-once where the endpoint is transactional** | Delivery guarantee holds when the destination supports transactions | maybe |
| **Unit cost decreasing under load** | Per-document cost falls as throughput rises, because transactions batch larger and amortize fixed overhead across more documents | yes |

## Worth stealing

**The durable log as the point of re-read, not the source.** Estuary's core structural bet: a **collection** is a durable, append-only transaction log (architecturally similar to a WAL) that a capture writes into once. Every downstream materialization reads from that log, not from the original source system. This means:

- **Backfill and tail from one task**: a capture starts by backfilling the source's current state into the collection, then transitions seamlessly into capturing ongoing changes — both phases write to the same log, so there's no separate "initial load" vs. "CDC" pipeline to keep in sync.
- **Replay without re-hitting the source**: because the full historical content of a collection is retained, adding a new destination later, or re-deriving a transform, replays from the log rather than re-querying the original system.
- **Fan-out is free relative to source load**: N destinations reading from one collection puts load on Estuary's log, not N-times load on the source database.

**Unit economics that improve under load is the specific, non-obvious claim worth flagging**: because Estuary batches into larger transactions as throughput increases, the fixed per-transaction overhead amortizes across more documents, so **cost per document falls as volume rises**. This is the structural opposite of classic batch ELT, which **re-reads the entire source (or a large window of it) on every sync interval** regardless of how much actually changed — batch ELT's cost scales with *how often you sync*, not with *how much changed*, whereas a durable-log architecture's marginal cost scales with actual change volume.

## Worth avoiding

Nothing distinct surfaced independently in this pass — the architecture's actual failure modes under sustained backpressure or extreme fan-out weren't documented in accessible sources.

## Facts & figures

- Claimed **sub-100ms end-to-end latency** with exactly-once delivery (**vendor-reported**).
- Exactly-once is conditioned on the destination endpoint being transactional — not a universal guarantee across every possible materialization target.

## Sources

- [Estuary product overview](https://estuary.dev/product/)
- [Concepts — Estuary docs](https://docs.estuary.dev/concepts/)
- [Backfilling Data](https://docs.estuary.dev/reference/backfilling-data/)
- [Change Data Capture (CDC) Done Correctly](https://estuarydev.substack.com/p/change-data-capture-cdc-done-correctly)
