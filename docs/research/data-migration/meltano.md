# Meltano (Singer SDK)

**What it is:** Open-source ELT built on the Singer tap/target protocol; the **Meltano Singer SDK** is the framework for building taps (extractors) and targets (loaders) with a well-specified state/checkpointing contract.
**Axis:** data migration (ingestion), workflow.
**Depth:** medium — one mechanism researched in depth.

## Products & surfaces

| Product | What it is |
|---|---|
| **Meltano** | CLI/orchestration layer for running Singer taps/targets as an ELT pipeline. |
| **Singer SDK** | The framework taps/targets are built against; defines the state contract described below. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **`is_sorted` as an explicit stream contract** | A boolean the tap author declares: are records monotonically increasing by replication key? | yes |

## Worth stealing

**Sortedness is what makes mid-run checkpointing safe — and the SDK makes you declare it rather than assume it.** Set `is_sorted = True` on a stream, and the SDK enforces it at runtime: it checks each record and raises `InvalidStreamSortException` if an out-of-order record actually shows up, so the contract isn't just documentation, it's checked.

The consequence of the flag is the interesting part:

- **`is_sorted = True`**: because newer records are guaranteed to always come later, the replication-key state can be written and emitted **continuously, batch by batch**, during the sync. If the tap has processed a state message and that state has been written by the target, everything before that point is safely known to be durably written — so on a **mid-run failure, the tap resumes from the last successfully processed state message**. Progress up to the interruption is preserved.
- **`is_sorted = False` (the default)**: there's no guarantee a later-read record has a higher replication-key value than an earlier one, so a checkpoint taken mid-run **cannot be trusted to reflect the true maximum value seen** — a later record might still be lower, but an even-later one might jump past what's already checkpointed in a way that would cause records to be skipped on resume. The SDK's documented consequence: **"the tap has to run to completion so the state can safely reflect the largest replication value seen."** A mid-run failure on an unsorted stream loses *all* progress for that run — there's a separate `progress_tracking` mechanism, but it's explicitly reset/ignored for resume purposes and only promoted to a real bookmark once the sync reaches 100% completion.

The generalizable point: **checkpointing safety isn't a property of "did we save state periodically," it's a property of whether the underlying stream's ordering guarantee makes a partial checkpoint meaningful.** A framework that makes you declare the ordering guarantee explicitly (and enforces it) prevents the much worse failure mode of a state file that looks fine but is silently wrong.

## Worth avoiding

The flip side of `is_sorted = False`'s honesty: any tap author who doesn't know or doesn't check whether their source actually returns sorted results, and defaults to `is_sorted = True` anyway to get incremental checkpointing, gets exactly the silent-corruption failure mode the flag exists to prevent — the enforcement only catches it if an out-of-order record is actually encountered during a given run, not necessarily on every occasion the source could violate the assumption.

## Facts & figures

None beyond the mechanism itself.

## Sources

- [Stream State — Meltano Singer SDK docs](https://sdk.meltano.com/en/latest/implementation/state.html)
- [Frequently Asked Questions — Meltano Singer SDK docs](https://sdk.meltano.com/en/latest/faq.html)

## See also (`airbyte.md`, shared context)

Meltano/Singer, Airbyte, Fivetran, and Estuary have all had to build around the same decade-old Postgres CDC hazards: **replication-slot disk exhaustion** (an unadvanced slot retains WAL indefinitely, risking forced shutdown to avoid transaction-ID wraparound), **silent full-resync on `confirmed_flush_lsn` lag** (if the consumer's offset falls behind what's been purged, the only recovery is a full resync), and **`xmin` wraparound** (the 32-bit transaction-ID counter wrapping breaks `xmin`-based cursors, forcing resyncs of already-synced data). See `airbyte.md` for sourcing on these.
