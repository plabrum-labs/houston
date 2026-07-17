# Confluent Schema Registry (Data Contracts)

**What it is:** Kafka's Schema Registry, extended with "data contracts" — rules that run at serialization/deserialization time, not just a passive schema store.
**Axis:** semantic layer, data migration (validation), streaming.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Schema Registry** | Central schema store for Kafka topics (Avro/Protobuf/JSON Schema). |
| **Data Contracts** | Schema plus attached **domain rules** and **migration rules**, evaluated by the client library during (de)serialization. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **`domainRules` with CEL conditions** | A rule expressed in Google's Common Expression Language, e.g. `"size(message.ssn) == 9"`, evaluated against the actual message | yes |
| **`TRANSFORM` / `CEL_FIELD` rules** | Rules that don't just check but actively mask, default, or rewrite a field's value | yes |
| **Execution on WRITE and/or READ** | A rule can run at serialization time, deserialization time, or both (`WRITEREAD`), with independent actions per side | yes |
| **`onSuccess` / `onFailure` actions**: `NONE` \| `ERROR` \| `DLQ` \| custom | What happens when a rule passes or fails is itself configurable, including routing the offending message to a dead-letter queue instead of just rejecting it | yes |

## Worth stealing

**This is preventive, not detective — because it runs code at the moment of serialization, not after the fact.** A `domainRule` is a CEL expression evaluated against the actual message payload at write time: e.g. `"size(message.ssn) == 9"` rejects (or routes, or transforms) a malformed SSN **before it ever lands on the topic**, not after a scheduled scan discovers it hours or days later. Rules can be scoped to `WRITE`, `READ`, or both (`WRITEREAD`, with independently configurable actions per side — e.g. `"NONE,ERROR"` means "allow on write, reject on read"). `TRANSFORM`/`CEL_FIELD` rule types go beyond pass/fail: they can **mask** a field (e.g. redact a value for a consumer without the right access) or **default** it, executing as part of the (de)serialization path itself.

The **`onSuccess`/`onFailure` action model** is the generalizable piece: every rule specifies what happens on each outcome, chosen from `NONE`, the built-in default `ERROR`, `DLQ` (route the offending message to a dead-letter topic for later inspection instead of just failing the write), or a custom action type. Setting `onFailure: DLQ` turns a rejected write into a captured, inspectable artifact rather than a dropped write or a failed producer call — the bad data still exists somewhere, just not on the primary topic.

## The general landscape point this justifies

**The warehouse-centric data-quality tooling in this research set (ODCS, dbt tests, Soda, Monte Carlo, Great Expectations) is entirely detective.** Every one of those tools can only scan data *after* it has already landed — they alert on a violation that already happened, because the warehouse itself does not run arbitrary code at write time; a scheduled job or trigger has to come along afterward and check. **Streaming, specifically because the client library sits directly in the serialization path, is the only category researched here that can reject or transform a bad write at the boundary, before it's committed anywhere.** This is a structural property of the architecture (code executes inline in the write path) rather than a feature one vendor added and another didn't — no warehouse-side tool in this set could replicate it without becoming, in effect, a proxy sitting in front of every write.

## Worth avoiding

The non-Java client SDKs (.NET, Go, Python, JavaScript) are documented as **not yet supporting the `DLQ` action** — so the most operationally useful failure action is Java-only as of the sources checked here; other-language producers get a narrower action set.

## Facts & figures

None beyond the mechanism; no adoption/scale figures independently verified in this pass.

## Sources

- [Schema Registry Data Contracts — Confluent docs](https://docs.confluent.io/platform/current/schema-registry/fundamentals/data-contracts.html)
- [Understanding CEL In Data Contract Rules — Robert Yokota](https://yokota.blog/2023/10/01/understanding-cel-in-data-contract-rules/)
- [Using Data Contracts with Confluent Schema Registry — Robert Yokota](https://yokota.blog/2024/02/13/using-data-contracts-with-confluent-schema-registry/)
- [Using Data Contracts to Ensure Data Quality and Reliability — Confluent blog](https://www.confluent.io/blog/data-contracts-confluent-schema-registry/)
- [How to Protect PII in Kafka With Schema Registry and Data Contracts](https://www.confluent.io/blog/protect-pii-kafka-data-contracts/)
