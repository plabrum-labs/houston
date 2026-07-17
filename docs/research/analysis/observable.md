# Observable Framework

**What it is:** A static site generator for data apps/dashboards where data loaders run once at build time and the published site ships pre-computed snapshots.
**Axis:** app-builder, deploy.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **Observable Framework** | Open-source static site generator: Markdown + JavaScript pages, compiled to a deployable static site. |
| **Data loaders** | Build-time programs, any language, that produce static data snapshots consumed by pages. |
| **Observable Cloud** | Hosted deploy target for Framework sites (separate from the open-source generator). |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Data loaders run at build time only | Any language/program that writes to stdout; output is cached as a static file in the build | yes |
| No runtime warehouse access for viewers | The published site serves only pre-computed static snapshots — viewers need no data-source credentials | yes |
| Incremental build | A loader only reruns if its output file is referenced by a page and (per Framework's caching) is stale | maybe |

## Worth stealing

**Build-time compute, zero-query viewing.** A data loader is defined narrowly: "a program that runs on the machine that builds the project and outputs information to standard output" — in Python, SQL, JavaScript, R, Julia, or anything else with a stdout. Framework's compiler runs each referenced loader once at build time and bakes its output into the static site as a file. The resulting site is genuinely static HTML+JS: **no viewer ever issues a live query**, no viewer needs warehouse credentials, and load time is bounded by static-asset serving rather than query latency. This is the sharpest possible contrast to Hex/Sigma/live-BI's "every page view is a live query" model — Observable is explicitly optimizing for instant, credential-free distribution at the cost of freshness (a rebuild is required to update data).

## Worth avoiding

The tradeoff is the whole story here and it's not free: no interactivity beyond what's baked into client-side JS at build time (no ad hoc drill-down against a live warehouse), and freshness is bounded by build cadence, not real time. This is a good fit for "publish a report," a poor fit for "let anyone slice this dataset live."

## Facts & figures

- Open source: `observablehq/framework` on GitHub.
- Data loader output caching is keyed to whether the output file is referenced by at least one page in the build.

## Sources

- [Observable Framework GitHub](https://github.com/observablehq/framework) · [Data loaders docs](https://observablehq.com/framework/data-loaders) · [Data loaders for the win](https://observablehq.com/blog/data-loaders-for-the-win) · [Getting started](https://observablehq.com/framework/getting-started)
- **Not directly verified:** incremental/staleness caching rules beyond "output referenced by a page" were not independently confirmed against the full docs in this pass.
