# Auth0

**What it is:** Developer-first CIAM/auth-as-a-service, acquired by Okta (2021) and run as a separate product line (Auth0 by Okta / Okta Customer Identity Cloud).
**Axis:** enterprise.
**Depth:** thin.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Step-up auth via `acr_values` / `max_age` | Force re-authentication or a higher assurance level for one sensitive action without ending the whole session | yes |

## Worth stealing: step-up via standard OIDC params, not a bespoke flow

Two OIDC authorization-request parameters do the whole job, and the mechanism is worth reusing verbatim rather than inventing a bespoke "confirm your identity" flow:

- **`acr_values`** (Authentication Context Class Reference) — the client requests a specific assurance level (e.g., "MFA was used") on the *next* authentication event; the resulting ID token's `acr` claim confirms what was actually satisfied, and `amr` lists the specific methods used (`mfa`, `otp`, `hwk`, etc.). The client checks `acr`/`amr` on return, not just "auth succeeded."
- **`max_age`** — caps how old the authentication event is allowed to be before the AS forces a fresh login. Auth0's docs frame this as forcing reauthentication for one operation; the general pattern (documented most thoroughly on Okta's developer blog, since Auth0 and Okta share an OIDC-standards base) is to **elevate for a bounded window** — e.g., allow access to a sensitive resource for the next 30 minutes, then silently fall back to the prior assurance level once the window lapses. Per spec, if a request includes `max_age`, the AS **MUST** include `auth_time` in the returned ID token so the client can verify the window was actually honored.

This is the standard mechanism now being formalized further at the OAuth layer: **RFC 9470 (OAuth 2.0 Step-Up Authentication Challenge Protocol)** defines a way for a resource server to challenge a client mid-flow for a higher `acr`, rather than requiring the client to guess up front — relevant if Houston ever needs a resource server (an app, an agent tool) to demand step-up itself rather than relying on the client to pre-request it.

## Facts & figures

- Owned by Okta since 2021; runs as a distinct product/brand (Auth0 by Okta).

## Sources

- [Force Reauthentication in OIDC (Auth0 Docs)](https://auth0.com/docs/authenticate/login/max-age-reauthentication)
- [Step-up authentication using ACR values (Okta Developer)](https://developer.okta.com/docs/guides/step-up-authentication/main/) · [Step-up Authentication in Modern Applications (Okta Developer)](https://developer.okta.com/blog/2023/03/08/step-up-auth)
- [RFC 9470 — OAuth 2.0 Step Up Authentication Challenge Protocol](https://datatracker.ietf.org/doc/rfc9470/)
- **Not directly verified:** Auth0-specific `acr_values` handling was reconstructed largely from Okta developer docs (same OIDC substrate, same corporate parent) rather than fetched from an Auth0-specific implementation guide.
