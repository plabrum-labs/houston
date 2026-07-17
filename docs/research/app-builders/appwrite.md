# Appwrite

**What it is:** Self-hostable BaaS — database, auth, storage, functions — with a collection/document permission model and client SDKs.
**Axis:** enterprise governance (permissions), semantic layer.
**Depth:** thin — official docs and community threads only.

## Products & surfaces

| Product | What it is |
|---|---|
| **Databases** | Collections of documents, each collection with its own permission set. |
| **Document Security** | A per-collection toggle that turns on document-level (as opposed to purely collection-level) permission checks. |
| **Storage / Functions / Auth** | Standard BaaS complement, permissioned via the same model. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Collection + document permissions | Two permission layers meant to compose | no (cautionary) |
| Document Security toggle | A settings-panel switch enabling document-level permission checks at all | no (cautionary) |

## Worth avoiding

**Collection-level and document-level permissions OR together, additively — they don't intersect.** Appwrite's own docs state it plainly: "if collection permissions allow you to do something, document permissions won't override it." The two layers **stack** rather than narrow each other: a permissive collection-level grant is not tightened by a stricter document-level rule underneath it — it's *widened* by any document-level grant, and never *restricted* by a document-level deny, because there is no document-level deny primitive, only additional grants. A collection permission of "any authenticated user can read" makes every document readable by any authenticated user regardless of what permissions are set on individual documents.

**Document Security is a settings-panel toggle, off by default per collection.** Document-level permissions are only even evaluated if "Document security" is enabled in that collection's settings — meaning the finer-grained layer can be silently inert (all documents effectively governed by collection-level rules only) unless a builder remembers to flip a switch that isn't visible from the permission-editing surface itself.

**The general lesson, applicable well beyond Appwrite**: an *additive-only* permission model — where every applicable rule can only grant, never restrict — has no way to express "revoke." Any system built this way inherits the property that adding a permission layer for defense-in-depth can only ever make access *more* permissive than the least restrictive layer, never less. Contrast with conjunctive models (Palantir's Markings, `palantir.md`: you must hold *all* applicable markings) or Postgres RLS's `USING`/`WITH CHECK` split (a policy narrows what's visible; multiple permissive policies OR together but restrictive policies AND — see `hasura.md`/`postgrest.md` for the underlying Postgres semantics) where a stricter rule can genuinely restrict a looser one.

## Facts & figures

- None independently verified beyond the permission-composition behavior documented above.

## Sources

- [Database permissions (legacy)](https://appwrite.io/docs/products/databases/legacy/permissions) · [Permissions (current)](https://appwrite.io/docs/advanced/platform/permissions)
- [Community thread: Collection vs Document Permissions](https://appwrite.io/threads/1116800315291881482) · [Community thread: Meaning of permissions set on a collection](https://appwrite.io/threads/1123702516123705385)
- **Not directly verified:** whether Appwrite's newer permission docs (post the "legacy" split) have changed the additive-only behavior described above — the "stack, don't override" behavior is sourced from both the legacy permissions doc and a community thread; not independently tested against a live Appwrite instance.
