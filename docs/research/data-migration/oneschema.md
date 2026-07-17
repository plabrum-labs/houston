# OneSchema

**What it is:** Embeddable CSV/spreadsheet importer for customer-facing data onboarding — the same product category as Flatfile, oriented more toward drop-in UI speed than developer-programmable pipelines.
**Axis:** data migration (onboarding surface).
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Embeddable Importer** | Drop-in widget: customer uploads a file, gets guided through mapping/cleaning/validation, clean rows come out the other side. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Bulk autofix / find-and-replace | Cleans data in bulk across the whole uploaded file rather than row-by-row | maybe |
| Library of 50+ no-code validations/transforms | Common data-quality rules configurable without code | no — table stakes for the category |
| Claimed throughput | Validates/transforms files up to 4GB "in under 1 second" for the initial pass, scaling to 20M rows (**vendor-reported**, unverified) | n/a |

## Worth stealing

Setup framed explicitly as a **20-minute integration**: define validation rules (5 min) → embed via snippet (3 min) → customize look/feel (4 min) → wire up the clean-data callback. The category's competitive axis is time-to-integrate, not sophistication of matching — worth noting as a floor Houston's own onboarding surface would be compared against.

## Worth avoiding

Nothing specific surfaced in this pass — docs are thin on mechanism (no equivalent of Flatfile's documented accuracy thresholds was found), so failure modes aren't independently verifiable here.

## Facts & figures

- Claims SOC 2 Type 2, SOC 3, GDPR, CCPA, HIPAA compliance; AES-256 at rest, TLS 1.2 in transit (**vendor-reported**).
- Claimed processing: up to 4GB / 20M rows.

## Sources

- [OneSchema Embeddable Importer](https://www.oneschema.co/embeddable-importer)
- [Getting Started with Importer](https://docs.oneschema.co/docs/getting-started)
- [5 Best Practices for Building a CSV Uploader](https://www.oneschema.co/blog/building-a-csv-uploader)

**See `flatfile.md`** for the adjacent-player note on Nuvo, and for the one documented accuracy-threshold mechanism found in this category.
