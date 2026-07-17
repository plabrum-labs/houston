# Monte Carlo

**What it is:** Data observability platform — automated anomaly detection over warehouse tables (freshness, volume, schema, distribution) without hand-written checks.
**Axis:** data migration (validation), analysis.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Auto-monitors** | ML-derived freshness/volume/schema/distribution thresholds, no manual configuration. |
| **Read-only connectors** | Metadata/query-log/usage-log extraction from warehouses and BI tools. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Metadata-only monitoring** | Reads **query logs and `information_schema`**, not the underlying row data itself, to infer freshness/volume/schema behavior | yes |
| **~2-week baseline learning window** | Auto-monitors need roughly two weeks of observation before thresholds are trustworthy | maybe |

## Worth stealing

**Auto-monitors are cheap specifically because they read metadata, not data.** Monte Carlo's mechanism operates through read-only connectors pulling **query logs and `information_schema`** — table row counts, last-modified timestamps, schema definitions, query patterns — rather than scanning actual row contents. This is what makes "monitor everything automatically" tractable cost-wise: the monitoring load is proportional to metadata volume, not table size or row count. Thresholds mature over roughly **two weeks** (initial thresholds after ~7 days, more reliable by ~14, with a 6-week rolling training window that accounts for weekly seasonality), so the tradeoff is a cold-start period before auto-monitors are trustworthy, in exchange for zero manual threshold configuration afterward.

## Worth avoiding

The cold-start period itself is a real cost — auto-monitors on a newly onboarded table are not trustworthy for roughly the first two weeks, and premature alerting during that window (or false confidence from an undertrained threshold) is a predictable failure mode of the design, not a bug.

## Facts & figures

- Auto-monitor threshold maturity: **~7 days initial, ~14 days mature**, 6-week rolling window for seasonality (**vendor-reported**).

## Sources

- [Monitors overview — Monte Carlo docs](https://docs.getmontecarlo.com/docs/monitors-overview)
- [Table — Monte Carlo docs](https://docs.getmontecarlo.com/docs/pipeline-observability)
