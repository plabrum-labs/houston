# Zingg

**What it is:** Open-source entity resolution / deduplication library built around active learning — instead of hand-tuned rules or a fully-labeled training set, a human labels a small, algorithm-chosen set of ambiguous pairs.
**Axis:** data migration (entity resolution/deduplication).
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Zingg** | Spark-based matching library: blocking, active-learning-driven training, prediction, runnable on Databricks/Snowflake/Fabric/Glue/GCP. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Active learning loop (`findTrainingData`)** | Surfaces the pairs the current model is *least* confident about for human labeling, rather than random or exhaustive sampling | yes |
| **30–50 labeled pairs sufficient** | Reported as enough to reach production-quality matching for many datasets | yes |

## Worth stealing

**Active learning collapses the labeling burden by an order of magnitude versus naive supervised approaches.** Zingg's `findTrainingData` samples candidate pairs from blocking output, prioritizing the ones where the model's current confidence is lowest — each label answers a question the model didn't already know the answer to, rather than confirming what it already believed. Reported guidance: **as few as 30–50 labeled pairs** are enough to train a production-quality model (roughly 40+ matches and 40+ non-matches for a ~100k-record dataset is the cited target), reached over **3–5 rounds** of label-and-retrain iteration until confidence stabilizes. The generalizable mechanism — sample by *lowest model confidence*, not randomly — is the part worth stealing anywhere a human is being asked to supervise a matcher: it's a way to make the "how many examples do I need" question tractable rather than "label thousands and hope."

## Worth avoiding

Nothing Zingg-specific surfaced independently in this pass beyond the shared caution below.

## Facts & figures

No independently verified benchmark numbers beyond the training-set-size guidance above (itself drawn from vendor/community documentation, not an academic benchmark).

## See also

**`splink.md`** carries the shared finding on the **OpenSanctions Pairs** paper (arXiv 2603.11051) — relevant here because it's evidence that off-the-shelf LLM pairwise matching now beats both rule-based and (by strong implication, though not directly benchmarked in that paper) traditional probabilistic/active-learning approaches on raw pairwise F1, while needing zero labeled training pairs at all. That doesn't make active learning obsolete — Zingg's mechanism is cheap, auditable, and runs without sending data to a third-party model — but it changes where the marginal effort should go: the paper's own conclusion (pairwise matching "approaching a practical ceiling") applies to Zingg's core value proposition as much as to rule-based systems.

## Sources

- [Fuzzy Matching at Scale, Part 4: Thresholds, Scores, and Active Learning](https://www.zingg.ai/post/fuzzy-matching-at-scale-part-4-thresholds-scores-and-active-learning)
- [Step By Step Identity Resolution With Python and Zingg](https://www.zingg.ai/documentation-article/step-by-step-identity-resolution-with-python-and-zingg)
- [Zingg homepage](https://www.zingg.ai/)
- [OpenSanctions Pairs — arXiv:2603.11051](https://arxiv.org/abs/2603.11051)
