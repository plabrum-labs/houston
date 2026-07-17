# Firebase

**What it is:** Google's mobile/web BaaS — Firestore/Realtime Database with a client-evaluated security-rules language, Auth, App Check, Cloud Functions, Storage.
**Axis:** semantic layer, enterprise governance (rules-as-permissions), deploy/migration (testability).
**Depth:** medium — official docs; no independent load-testing.

## Products & surfaces

| Product | What it is |
|---|---|
| **Firestore / Realtime Database** | Document/tree databases, access-controlled by Security Rules evaluated per-request. |
| **Security Rules** | A declarative rules language (`match`/`allow`) gating every read/write, evaluated server-side but authored client-facing. |
| **Local Emulator Suite** | Local emulation of Firestore/Auth/Storage/Functions, including rules evaluation. |
| **rules-unit-testing** | An SDK for writing unit tests against Security Rules, run against the emulator. |
| **App Check** | Attestation layer that rejects backend requests not provably from your real app. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Rules unit-test SDK | Security rules can be exercised with normal test-runner assertions, locally, pre-deploy | yes |
| Coverage reports for rules | The emulator can report which rule branches were actually evaluated by a test run | yes |
| `get()`/`exists()` cross-document reads bill as reads | A rule that looks up another document is charged like any other read, even on a rejected request | no (cautionary — cost/scaling wall) |
| App Check | Attests requests are from a genuine instance of your app before they hit rules evaluation | yes |

## Worth stealing

### Security Rules are locally, automatically testable — rare in this category

Firebase ships `@firebase/rules-unit-testing`, a dedicated SDK for writing rules tests: `initializeTestEnvironment` spins up a `RulesTestEnvironment` against the Local Emulator Suite; `initializeTestApp`-style helpers let a test authenticate *as* an arbitrary user (real or fabricated) and assert whether a given read/write is allowed or denied, without touching production data or deploying anything. Tests can seed fixture data with rules **disabled** (`withSecurityRulesDisabled`) and then re-enable rules for the assertion phase. After a run, the emulator exposes a coverage endpoint reporting which rule branches were actually exercised.

This matters because almost none of the declarative-permission systems surveyed elsewhere in this research set (Postgres RLS, Hasura permissions, PocketBase API rules) have an equivalent first-party **unit-test harness for the permission logic itself** — permission bugs are typically caught by manual QA or in production. Firebase treats "does this rule allow what I think it allows" as a testable proposition with the same tooling shape as testing application code.

### App Check — attestation as a layer beneath the rules layer

App Check attaches a per-request attestation (via platform-specific providers — Play Integrity, App Attest, reCAPTCHA, etc.) proving a request originates from a genuine instance of your registered app, and can reject unattested traffic before it's even evaluated against Security Rules. Stated abuse vectors covered: billing fraud, phishing, app impersonation, data poisoning, copied APKs, emulators/bots. Google's own docs are careful to caveat it "prevents some, but not all, abuse vectors" — it's a defense-in-depth layer, not a replacement for rules-based authorization.

## Worth avoiding

### `get()`/`exists()` in rules bill as reads, even when the request is rejected

Any rule that cross-references another document — `get(/databases/$(database)/documents/roles/$(request.auth.uid)).data.role == 'admin'`, the canonical pattern for role-based rules — **executes an actual document read against the database and is billed accordingly, whether or not the rule ultimately allows the request.** Storage rules additionally cap this at **two Firestore document reads per rule evaluation**. The practical effect: any rule design that does cross-entity lookups (checking a separate roles/permissions document rather than fields on the document itself) scales its *cost* with request volume, not just its latency — the very thing that makes rules expressive (referencing other collections) is the thing that makes them expensive under load.

**Cross-reference**: Supabase's docs independently arrive at the same operational advice — "minimize joins in [RLS] policies" (see `supabase.md`) — for a different underlying reason (query-planner cost inside Postgres, not per-call billing). Two architecturally opposite systems (client-evaluated rules language vs. server-side SQL policies) converge on the same guidance: **cross-entity permission checks are the scaling wall**, regardless of which side of the client/server boundary the check is evaluated on.

## Facts & figures

- Storage Security Rules: hard cap of 2 Firestore document reads per rule evaluation (documented limit).
- Rules unit-test SDK ships for both v8 and v9 JS SDKs; v9 is the recommended/streamlined version (vendor docs).

## Sources

- [Build unit tests (Security Rules)](https://firebase.google.com/docs/rules/unit-tests) · [Test your Cloud Firestore Security Rules](https://firebase.google.com/docs/firestore/security/test-rules-emulator) · [rules-unit-testing package reference](https://firebase.google.com/docs/reference/emulator-suite/rules-unit-testing/rules-unit-testing)
- [Writing conditions for Cloud Firestore Security Rules](https://firebase.google.com/docs/firestore/security/rules-conditions) · [Use conditions in Cloud Storage Security Rules](https://firebase.google.com/docs/storage/security/rules-conditions)
- [Firebase App Check](https://firebase.google.com/docs/app-check) · [App Check product page](https://firebase.google.com/products/app-check)
- **Not directly verified:** exact current billing formula for `get()`/`exists()` calls beyond "counts as a document read"; whether the 2-document cap in Storage Rules has changed in recent releases.
