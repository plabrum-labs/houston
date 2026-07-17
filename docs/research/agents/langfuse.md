# Langfuse

**What it is:** Open-source LLM engineering platform — tracing, evals, prompt management, datasets. The only tool in this category that instruments its own LLM judges.
**Axis:** agent platform (eval/observability).
**Depth:** thin, by design — short file per research scope.

## Products & surfaces

- **Tracing** — OTLP endpoint (`/api/public/otel`), native OpenTelemetry backend.
- **Evaluation** — LLM-as-a-judge, code evaluators, user feedback, manual labeling, custom pipelines via API/SDK.
- **Datasets** — turn production traces into offline eval datasets.
- **Prompt management, playground** — round out the same loop as Braintrust.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Instruments its own LLM judges | The judge models themselves are traced/observable, not a black-box scoring call | yes |
| Native OTel backend | Receives traces directly over OTLP, no proprietary SDK required to get data in | yes |
| Online (production traces) + offline (pre-ship experiments) eval in one loop | Score live traffic, promote interesting examples into datasets, run offline comparisons against the same scorers | yes |

## Worth stealing

**Instrumenting the judge, not just the judged.** Langfuse is called out (per the brief for this research pass) as the only tool in the category that applies its own tracing/observability to the LLM-as-judge calls themselves — meaning a judge's own inputs, reasoning, and score are inspectable artifacts, not a trusted black box. This is a direct, partial answer to the "who validates the judge" problem named in `braintrust.md` — visibility into judge behavior, even without solving ground-truth validation, at least makes judge drift and judge failure modes debuggable rather than invisible.

## Worth noting

**Prefer OpenTelemetry GenAI semantic conventions** over a proprietary trace format when instrumenting new pipelines — both Langfuse and Braintrust converge on OTel as the interchange layer, and Langfuse credits itself as an active contributor to the GenAI semconv standardization effort. ⚠️ **The OpenTelemetry GenAI semantic conventions page is now a redirect**, and stability of the spec (which fields are stable vs. experimental) was **not verified** in this pass — treat "OTel GenAI semconv" as directionally correct but don't cite specific field names as stable without checking the current spec directly.

## Sources

- [langfuse.com/integrations/native/opentelemetry](https://langfuse.com/integrations/native/opentelemetry)
- [langfuse.com/docs/evaluation/overview](https://langfuse.com/docs/evaluation/overview)
- [langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)
- **Unverified:** current stability status of OpenTelemetry GenAI semantic conventions — the canonical spec page redirects; not independently confirmed in this pass.
