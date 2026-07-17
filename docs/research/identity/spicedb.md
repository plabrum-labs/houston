# SpiceDB

**What it is:** Open-source, Zanzibar-inspired permissions database from Authzed — the most Zanzibar-faithful of the ReBAC engines. See `openfga.md` for the shared Zanzibar/ReBAC background (not repeated here).
**Axis:** enterprise (permissions substrate).
**Depth:** thin.

## What distinguishes it from OpenFGA

**Consistency model, not just a schema-language difference.** SpiceDB implements **ZedTokens** — its equivalent of Zanzibar's original "Zookie" concept — specifically to address Zanzibar's **"new enemy problem"**: without a consistency token, a permission check can race a very recent write and return a stale allow/deny. A ZedToken returned from a write (or an earlier check) can be passed into a later check with one of two modes:

- **`at_least_as_fresh`** — use data at least as fresh as the token's point-in-time; use even-fresher data if available.
- **`at_exact_snapshot`** — pin the check to the *exact* point-in-time the token represents.

This lets a caller trade freshness for latency per-request rather than the engine imposing one global consistency policy.

**Watch API** — a streaming API that emits every relationship create/touch/delete from a given point onward, used for cache invalidation in downstream systems that maintain their own denormalized permission caches rather than calling SpiceDB on every read.

**Positioning**: gRPC-first, schema language close to the original Zanzibar paper's notation, self-hosted or managed via Authzed. Third-party comparisons (2026) consistently place it as the **"Zanzibar-purist"** choice — the tradeoff being a steeper onramp than OpenFGA's REST-first, broader-SDK approach, in exchange for closer fidelity to the paper's consistency guarantees.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| ZedToken / new-enemy-problem mitigation | Per-request freshness/consistency tradeoff on permission checks | yes — the pattern, not necessarily the exact API |
| Watch API | Streaming relationship-change feed for cache invalidation | yes |
| Zanzibar-faithful schema language | Closer mapping to the original paper for teams that want that fidelity | n/a — positioning |

## Worth knowing: same list-endpoint and recursive-group cost as the rest of the category

SpiceDB is not exempt from the list-endpoint problem described in `openfga.md` — it mitigates it with the same reverse-indexed "list objects" query shape, not a different solution. And per the shared Zanzibar lineage: **recursive/nested-group userset rewriting is the dedicated hard engineering problem across the entire category** — resolving "is user U in a group that's in a group that's in a group with viewer access" cheaply requires a heavily cached, purpose-built graph-index service; it isn't a side effect you get for free from a general-purpose graph database.

## Facts & figures

- Company: Authzed (commercial entity behind SpiceDB, offers managed hosting).
- Consistency modes: `at_least_as_fresh`, `at_exact_snapshot` (ZedToken-based).

## Sources

- [Consistency (Authzed docs)](https://authzed.com/docs/spicedb/concepts/consistency) · [ZedTokens and Zookies (Authzed docs)](https://authzed.com/docs/reference/zedtokens-and-zookies) · [Zed Tokens, Zookies, Consistency for Authorization (Authzed blog)](https://authzed.com/blog/zedtokens)
- [Watching Relationship Changes (Authzed docs)](https://authzed.com/docs/spicedb/concepts/watch)
- [Google Zanzibar (Authzed docs)](https://authzed.com/docs/spicedb/concepts/zanzibar) · [GitHub — authzed/spicedb](https://github.com/authzed/spicedb)
- [OpenFGA vs Permify vs SpiceDB (2026)](https://www.pkgpulse.com/guides/openfga-vs-permify-vs-spicedb-zanzibar-authorization-2026) · [SpiceDB vs Auth0 FGA](https://sph.sh/en/posts/spicedb-vs-auth0-fga/)
- **Not directly verified:** no independent benchmark comparing SpiceDB's actual latency/consistency tradeoffs against OpenFGA in production was located; claims here are drawn from Authzed's own docs plus third-party comparison posts, not a hands-on test.
