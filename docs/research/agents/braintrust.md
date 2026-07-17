# Braintrust

**What it is:** Eval and observability platform for LLM applications — the eval framework Ramp uses (see `ramp.md`).
**Axis:** agent platform (eval/observability).
**Depth:** thin, by design — short file per research scope.

## Products & surfaces

- **Eval()** — the core primitive: dataset + task function + scorer(s), run as a versioned, immutable experiment.
- **Tracing** — OpenTelemetry-based, with typed span attributes (`llm`, `tool`, `task`, `function`).
- **CI integration** — evals run per pull request, posting pass/fail/regression as PR comments.
- **AI gateway** — provider-agnostic routing layer.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Inline scorers per pipeline stage | A multi-step pipeline (e.g. tool selection → SQL execution → result translation) can be scored **separately at each stage**, not just on final output | yes |
| Experiment as an immutable, diffable snapshot | Every eval run is versioned; two experiments diff at the row level | yes |
| CI-gated evals | PRs get automatic eval runs with regression comments, blocking merges on quality gates | yes |
| One system for human review + LLM-judge + code scorers + tracing + CI | Braintrust's own differentiation claim vs. point-solution competitors | maybe |

## Worth stealing

**Inline, per-stage scoring** is the concrete, generalizable idea: instead of one end-to-end score on a multi-step agent pipeline, score each stage independently — did the agent pick the right tool, independent of whether the tool's output was then translated correctly into a user-facing answer. This localizes failure to a specific stage instead of leaving "the eval failed" as an undifferentiated verdict across an entire pipeline. Ramp uses Braintrust this way for its Policy Agent evals (see `ramp.md`).

## The category spine (applies to both Braintrust and Langfuse)

**Versioned datasets → code/LLM-judge/human scorers → OTel spans → offline + online eval → CI gating → review queues → trace-to-dataset loop.** Both tools converge on this shape; the difference is emphasis, not architecture.

**The structural constraint worth naming**: the offline/online split is forced by ground-truth availability, not preference. Offline eval needs a labeled dataset; production traffic doesn't come pre-labeled, so online eval gets pushed onto LLM-judges — which are themselves unvalidated models scoring other models. Neither Braintrust nor Langfuse (nor anyone else, publicly) has solved the bootstrapping problem of validating the judge itself.

## Sources

- [braintrust.dev/docs/evaluate](https://www.braintrust.dev/docs/evaluate)
- [braintrust.dev — How to evaluate LLMs and AI agents in production](https://www.braintrust.dev/articles/how-to-eval)
- See `ramp.md` for Braintrust in production use (Ramp's Policy Agent evals).
