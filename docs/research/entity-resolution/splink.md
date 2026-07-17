# Splink

**What it is:** Open-source probabilistic record linkage library (UK Ministry of Justice), implementing Fellegi-Sunter matching on top of any of several SQL backends (DuckDB, Spark, Athena, SQLite).
**Axis:** data migration (entity resolution/deduplication).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Splink library** | Python API over a chosen SQL backend; define comparisons, estimate parameters via EM, predict match probabilities. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Term-frequency adjustments** | Down-weights matches on common values, up-weights matches on rare values, independent of the EM-trained `m` probability | yes |
| Comparison-level DSL (`cl.ExactMatch(...).configure(...)`) | Composable per-column comparison definitions | maybe |

## Worth stealing

**Term-frequency adjustment is orthogonal to the trained model, so it needs no retraining to turn on or off.** In the Fellegi-Sunter framework, `m` (probability of agreement given a true match) is normally a single EM-estimated number per comparison level — a match on "John" and a match on "Lucas" score identically as "first name matches." TF adjustment corrects this: a match on a rare value like "Lucas" carries more evidentiary weight than a match on a common value like "John," because two random records agreeing on "Lucas" is much less likely by chance. The reason this is worth stealing specifically (not just "weight by frequency," which is an old idea) is the implementation property: **the TF adjustment term is independent of `m`,** so it doesn't have to be estimated by the EM algorithm — it's computed directly from the frequency table and can be toggled on/off per comparison without retraining the model:

```python
cl.ExactMatch("sex").configure(term_frequency_adjustments=True)
```

That decoupling — a correction that layers on top of a probabilistic model without re-touching the model's own parameters — is the generalizable pattern: any place Houston has a learned/estimated weight, look for corrections that can be applied as a separate multiplicative term rather than folded back into training.

## Worth avoiding

Nothing distinct surfaced in this pass; see the shared OpenSanctions Pairs finding below for the field-level cautionary note that applies to Splink, Zingg, and any pairwise matcher.

## Facts & figures

No published benchmark numbers independently verified in this pass.

## Shared finding: OpenSanctions Pairs (arXiv 2603.11051)

A large-scale, real-world entity-matching benchmark relevant to every matcher in this file and `zingg.md`: **755,540 labeled pairs**, spanning **293 sources** across **31 countries**, built from actual sanctions-list aggregation and analyst deduplication — multilingual, cross-script names, noisy/missing attributes, set-valued fields.

- The production **rule-based baseline** (nomenklatura's RegressionV1) scores **91.33% F1**.
- **Off-the-shelf LLMs beat it substantially**: GPT-4o reaches **98.95% F1**; a locally-deployable open model, **DeepSeek-R1-Distill-Qwen-14B, reaches 98.23% F1**.
- **DSPy MIPROv2** prompt optimization gives consistent but modest additional gains.
- **In-context examples give little benefit and can degrade performance** — few-shot prompting is not a reliable lever here.
- Results approach observed **human labeling consistency** on the dataset — the paper's authors conclude pairwise matching is **"approaching a practical ceiling"** and argue future effort should shift to **blocking, clustering, provenance modeling, and uncertainty-aware review** rather than further tuning the pairwise classifier itself.
- **Error modes are complementary, not overlapping**: the rule-based system over-matches (higher false-positive rate); LLMs specifically fail on cross-script transliteration and on minor identifier/date inconsistencies that a rule can catch trivially. Neither approach dominates the other's failure cases.

This was cross-checked directly against the arXiv abstract page rather than taken from a single search summary, given a documented prior hazard of fabricated summaries for this exact paper (invented cost metrics in an earlier fetch). The figures above match what the abstract and search-indexed summary independently report; no cost-per-match or dollar figures are claimed anywhere in the abstract, and none should be attributed to this paper.

## Sources

- [Term frequency adjustments — Splink docs](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html)
- [Defining and customising comparisons](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/customising_comparisons.html)
- [Splink GitHub](https://github.com/moj-analytical-services/splink)
- [OpenSanctions Pairs — arXiv:2603.11051](https://arxiv.org/abs/2603.11051)
