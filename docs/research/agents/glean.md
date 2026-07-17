# Glean

**What it is:** Enterprise search/RAG platform where the core security mechanism is filtering by permissions **before** any content reaches the model.
**Axis:** enterprise governance, semantic layer (partial — indexing/permissions layer, not an ontology).
**Depth:** medium — the ACL/indexing mechanism is well-documented; agent-specific access-policy failure behavior is thin.

## Products & surfaces

- **Glean** — enterprise search and RAG assistant that acts **as the signed-in user** across connected data sources.
- **Indexing API** — `DocumentPermissionsDefinition` with `allowedUsers` / `allowedGroups`, set per document at index time.
- **Agent access policies** — governs what data an agent (as opposed to interactive search) can reach.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Pre-LLM ACL filtering | Permissions resolved and content discarded **before** the model ever sees it, not filtered from the model's output after | yes |
| `DocumentPermissionsDefinition` | Explicit `allowedUsers`/`allowedGroups` set at index time, referenced by email or by datasource user ID depending on connector config | yes |
| Acts as the signed-in user | Search results and RAG context are scoped to what that specific user, not a service principal, can see | yes |
| Agent access policies | Governs data reach for autonomous agents distinct from interactive search | maybe — see caveat |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

**Filtering happens before generation, not after.** Glean's own framing: content is filtered through the user's permissions, **discarding anything they don't have access to**, and only that pre-filtered result set is passed to the LLM to generate an answer. This is the architecturally correct place to enforce access control for a RAG system — it means the model is structurally incapable of leaking a document it was never shown, rather than being trusted (via prompting or post-hoc output filtering) not to repeat something it did see. It also means a prompt-injection or jailbreak against the model can't recover access the retrieval layer never granted.

The permission model itself is unremarkable and correct: per-document `allowedUsers`/`allowedGroups` set at index time, referenced either by email or by a connector-specific user ID depending on configuration, with users required to be indexed before they can be referenced in group memberships.

## Worth avoiding

**Glean's agent access policies are fail-open by design** — meaning they are not described as a hard control that blocks by default when policy is ambiguous or unset; they're a configuration surface an administrator must actively use correctly. That distinction matters for anyone evaluating Glean (or building something in this shape): the pre-LLM ACL filtering for **interactive search** is a strong, structural control; the equivalent guarantee for **autonomous agent** data access is weaker and depends on correct configuration rather than a safe default. Don't assume the search-layer guarantee automatically extends to agent behavior — it's a different policy surface with different failure characteristics.

## Facts & figures

None with independent (non-Glean) verification found for scale, latency, or accuracy claims — not included here for that reason.

## Sources

- [developers.glean.com — Permissions](https://developers.glean.com/api-info/indexing/documents/permissions)
- [Glean — Secure generative AI for the enterprise requires the right permissions structure](https://www.glean.com/blog/secure-generative-ai-for-the-enterprise-requires-the-right-permissions-structure)
- [docs.glean.com — MCP Security, Data Flow, and Permissions](https://docs.glean.com/administration/platform/mcp/security)
- [docs.glean.com — Group-based permissions](https://docs.glean.com/administration/identity/roles/group-based-permissions)
- **Gap:** no public documentation found describing agent access policies as fail-closed by default; this file treats that as an open configuration risk rather than assuming either way beyond what Glean states.
