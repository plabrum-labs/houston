# Great Expectations

**What it is:** Open-source data validation framework — define "Expectations" (assertions about data), run them against a dataset, get human-readable results.
**Axis:** data migration (validation), analysis.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **GX Core (OSS)** | Expectations, validation runs, Data Docs. |
| **GX Cloud** | Commercial hosted layer — UI, alerting, results storage/history. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Data Docs** | Validation results rendered as static, self-hostable HTML | maybe |

## Worth stealing

**Data Docs are plain static HTML, not a hosted dashboard you depend on the vendor for.** By default they're written to a local uncommitted directory; for team use, the documented pattern is deploying them to any static-site-capable blob store (S3/GCS/Azure). Multiple sites can be configured per project for different audiences. The generalizable point: validation *results* as durable, ownable, versionable artifacts rather than a live query against a vendor's backend — you can check a Data Docs snapshot into history the same way you'd check in a build artifact.

## Worth avoiding

Nothing distinct surfaced in this pass.

## Facts & figures

None beyond the mechanism.

## Sources

- [Data Docs — GX docs](https://docs.greatexpectations.io/docs/0.18/reference/learn/terms/data_docs/)
- [Configure Data Docs — host and share](https://docs.greatexpectations.io/docs/oss/guides/setup/configuring_data_docs/host_and_share_data_docs)

**Pattern across the whole OSS data-quality tier (GE, Soda, and by extension Monte Carlo/Anomalo's free layers where they exist):** the check/validation *engine* is open and self-hostable; what the commercial tier actually sells is uniformly the **UI, alerting, and results-backend/history layer** on top of it. The differentiation isn't in "can it detect the problem" — it's in "where do the results live and who gets paged."
