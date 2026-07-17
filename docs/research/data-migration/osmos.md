# Osmos

**What it is:** An "agentic data engineering" platform that turns messy source files into validated, loadable data by having an LLM write and run the transformation code, rather than transform data through the LLM directly. Acquired by Microsoft, announced January 5, 2026, to be folded into Fabric/OneLake.
**Axis:** data migration, semantic layer (mapping/validation authoring).
**Depth:** thin. Primary docs are gated — see caveat below. Everything here is press/blog-sourced.

## Products & surfaces

| Product | What it is |
|---|---|
| **AI Data Wrangler** | Interactive agent for normalizing chaotic source files — the bridge between raw ("Bronze") and validated ("Silver") data. |
| **AI Data Engineer** | Generates production-grade PySpark notebooks inside Microsoft Fabric for the larger transformation/pipeline job. |
| **Wrangler Context / self-configuration (GA)** | Point it at a folder of business requirement docs, schema designs, and sample data; it generates instructions, field descriptors, and validation rules for human review, rather than requiring them to be hand-written. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Program synthesis, not row-wise LLM transform** | The LLM emits PySpark code; the generated code — not the model — moves the data | yes |
| **Wrangler Context self-configuration** | Ingests business-requirement docs + schema + samples, outputs reviewable instructions/descriptors/validators | yes |
| Hybrid symbolic + neural reasoning (vendor framing) | "Programming by Demonstration" — user supplies example clean rows, system infers the transformation | maybe |

## Worth stealing

**Program synthesis as the trust mechanism.** The stated architectural choice is that the LLM's job is to *write code* that performs the transformation, not to touch each row itself. Because the artifact is PySpark, it is reviewable before running, versionable in source control, deterministic on re-run, and re-runnable without re-invoking the model — the LLM sits outside the per-row data path entirely. This is the same shape as "generate a migration script and let a human approve the diff" rather than "let the model rewrite your data live." Multiple press writeups (GeekWire, InfoWorld, Redmond, The Register) converge on this framing; Microsoft's own announcement frames it as reducing "dev and maintenance effort" by 50% for Fabric Spark customers (vendor-reported, via Microsoft's Roy Hasson).

**Self-configuration from documents (GA).** Per Osmos's own blog, translating business requirements into transformation/validation logic is described as "typically a multi-month effort" that Wrangler Context turns into "a few minutes" by self-learning from uploaded business requirement docs, schema designs, and sample data. Output is three artifact types: **descriptors** (schema-level constraints), **validators** (source-specific business logic), and **instructions** (guardrails the AI works within) — all generated for review rather than applied silently. This is the closest analog among the researched vendors to inferring a semantic layer's field-level contract straight from institutional documentation rather than from a human writing YAML.

## Worth avoiding

No independently verifiable failure modes — the primary docs needed to evaluate error handling, review UX, or where synthesis breaks down are gated (see below).

## Facts & figures

- Acquisition announced **January 5, 2026** (Microsoft Blog). Terms undisclosed.
- Customers running Osmos on Fabric Spark reportedly cut dev/maintenance effort by ~50% — **vendor-reported**, attributed to Microsoft's Roy Hasson, not independently audited.
- Positioned explicitly against Databricks' automated ETL tooling on Azure (multiple outlets' framing, not a direct Osmos/Microsoft quote).

## Sources

- [Microsoft Blog: acquisition announcement](https://blogs.microsoft.com/blog/2026/01/05/microsoft-announces-acquisition-of-osmos-to-accelerate-autonomous-data-engineering-in-fabric/)
- [GeekWire](https://www.geekwire.com/2026/microsoft-acquires-data-analytics-seattle-startup-osmos-to-fuel-push-into-autonomous-data-engineering/) · [InfoWorld](https://www.infoworld.com/article/4113736/microsoft-acquires-osmos-to-ease-data-engineering-bottlenecks-in-fabric.html) · [The Register](https://www.theregister.com/2026/01/06/microsoft_acquires_osmos/) · [Redmondmag](https://redmondmag.com/articles/2026/01/06/microsoft-acquires-osmos-to-bring-autonomous-data-engineering-to-fabric.aspx)
- [Osmos blog: AI Data Wrangler GA with self-configuration](https://www.osmos.io/blog/osmos-ai-data-wrangler-is-now-ga-with-self-configuration-capability)
- [Osmos blog: Meet the Osmos AI Data Engineer](https://www.osmos.io/blog/meet-the-osmos-ai-data-engineer-code-generation-built-for-data)
- [Osmos blog: Introducing Osmos 3.0](https://www.osmos.io/blog/introducing-osmos-3-0)

**Gated/unreachable, explicitly:**
- `fabricdocs.osmos.io` and `agenticdocs.osmos.io` both **307-redirect** to a gated GitBook site (`app.gitbook.com/o/-MYHIPthNCYADz6TdnGw/...`) that requires access not available here.
- `www.osmos.io` fails TLS validation directly: the certificate presented is for `*.azureedge.net`, not `www.osmos.io` — consistent with a mid-migration CDN misconfiguration post-acquisition, but it means the primary marketing/docs site could not be fetched directly (blog posts hosted on the same domain were reachable via search-engine cache/indexing, which is how the above was sourced).
- **Net effect: no mechanism described here comes from Osmos's own technical documentation.** All of it is press coverage or blog posts that survived indexing. Treat every "how it works" claim as vendor narrative, not verified implementation detail.
