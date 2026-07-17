# PostgREST

**What it is:** A standalone server that turns a Postgres schema directly into a REST API by reflecting on the database's own catalogs — no application code, the schema (and its grants/RLS) *is* the API definition.
**Axis:** semantic layer.
**Depth:** thin — official docs only.

## Products & surfaces

| Product | What it is |
|---|---|
| **PostgREST server** | Reads Postgres catalog (tables, views, functions, comments, grants) at startup/on schema reload, serves REST endpoints reflecting it directly. |
| **Resource Embedding** | Nested-resource fetching (`?select=col,related_table(col)`) derived from FK relationships. |
| **Functions as RPC** | Any Postgres function becomes a callable endpoint (`POST /rpc/function_name`), including ones returning `SETOF table`. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| `SETOF table`-returning functions get full table grammar | Filter/order/embed operators apply to function results exactly as to a table, if inlinable | yes |
| Planner inlining for eligible functions | Filters/order/limit get pushed *into* the function call by Postgres itself, not applied after | yes |

## Worth stealing

### The filter/embedding grammar keys off the return *type*, not the origin of the rows

A Postgres function declared to `RETURNS SETOF some_table` is queryable through PostgREST with the **exact same filter, order, and resource-embedding operators** as a real table or view — `?col=eq.value`, `?order=col.desc`, `?select=col,related(col)` all work identically, because PostgREST's grammar is generated from the *declared row type*, not from whether the rows physically came from a table scan or from executing a function body. This is a clean instance of an API surface deriving entirely from a type signature rather than from a hand-maintained list of "which endpoints support which query params" — add a function with the right return type and it inherits the whole grammar for free.

### Inlining makes the pushdown real, not cosmetic

This only performs well because Postgres can, under specific conditions (the function is `STABLE`/`IMMUTABLE`, SQL-language, and meets a few other inlining requirements — not `PL/pgSQL`, not `VOLATILE`), **inline the function body into the surrounding query plan**. When inlining succeeds, filters/order/limit passed from the API request are pushed *into* the function's underlying query before execution — there's no "Function Scan" node in the plan, and no full-result materialization followed by client-side-style filtering. When a function doesn't meet the inlining rules, the same API surface still works, but the filtering happens after the function has already produced its full result set — same grammar, very different performance profile, and the difference is invisible from the API shape alone.

## Facts & figures

- Inlining eligibility requires (per PostgREST/Postgres docs): SQL-language function body, `STABLE` or `IMMUTABLE` volatility, and other planner-imposed constraints (e.g., no polymorphic/variadic complications) — exact full rule set is Postgres's own function-inlining criteria, not a PostgREST-specific list.

## Sources

- [Tables and Views (v10)](https://docs.postgrest.org/en/v10/api.html)
- [Resource Embedding (v12)](https://docs.postgrest.org/en/v12/references/api/resource_embedding.html) · [Resource Embedding (stable)](https://docs.postgrest.org/en/stable/references/api/resource_embedding.html)
- [Functions as RPC (v12)](https://docs.postgrest.org/en/v12/references/api/functions.html) · [Functions as RPC (stable)](https://docs.postgrest.org/en/stable/references/api/functions.html)
- [Using Function Filters for Stored Procedures with Predicate Pushdown (discussion)](https://github.com/PostgREST/postgrest/discussions/2087)
- **Not directly verified:** exhaustive list of Postgres's function-inlining eligibility rules — summarized from docs/discussion, not cross-checked against Postgres source.
