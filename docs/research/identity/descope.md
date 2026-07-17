# Descope

**What it is:** Developer-first CIAM/auth platform, notable here for tenant-aware multi-IdP SSO and a specific SAML validation pitfall worth recording.
**Axis:** enterprise.
**Depth:** thin.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Multi-IdP per tenant | Each tenant gets its own SAML/OIDC connection, routed by email domain | yes |
| Documented SAML key-selection warning | Names a specific cross-tenant impersonation footgun | yes — as a checklist item |

## Worth stealing / worth avoiding: never pick the validation key from inside the assertion

Descope supports **tenant-aware SSO** — each tenant can have its own SAML or OIDC configuration, with automatic routing based on the user's email domain to the correct IdP.

The security note worth keeping as a standing checklist item for anyone implementing multi-tenant SAML (Houston included, if Houston ever terminates SAML directly rather than delegating entirely to WorkOS/Okta/etc.): **you must never select the SAML signature-validation key from a claim inside the assertion itself.** If the validation key is chosen based on something the assertion carries (an issuer field, a tenant identifier claim), an attacker who controls *any one* of the connected IdPs can forge an assertion claiming to be a *different* tenant, and the validator will pick the attacker's own (validly-signed-by-them) key to check the attacker's own (self-consistent) forged assertion — passing validation while impersonating a tenant the attacker doesn't control.

**The fix**: bind the validation key to the tenant via a channel outside the assertion's control — the resolved SSO connection record looked up by, e.g., the login route or subdomain the user arrived through — and cross-check the assertion's `AudienceRestriction` (SAML) or `aud` claim (OIDC) against the service provider's own registered entity ID for that specific connection, not against a value pulled from inside the assertion being validated. In practice: the standard SAML `AudienceRestriction` error surfaces exactly this — the WorkOS SAML-debugging guide describes it as thrown when the assertion's `AudienceRestriction` doesn't match the SP's own configured Entity ID, which is the correct direction of the check (compare against a value *you* hold, not one *the assertion* asserts).

## Sources

- [Multiple SSO Per Tenant (Descope docs)](https://docs.descope.com/sso/multi-sso) · [Authorization with SSO Providers (Descope docs)](https://docs.descope.com/management/tenant-management/sso/how-authorization-works-with-sso-providers)
- [Diagnosing SAML assertion failures: A step-by-step debugging guide (WorkOS)](https://workos.com/blog/saml-assertion-failures-debugging-guide) — source for the `AudienceRestriction` mismatch behavior.
- **Not directly verified:** no Descope security advisory or CVE describing this exact attack was located; the mechanism is stated here as a general SAML multi-tenant validation principle (consistent with how `AudienceRestriction`/`aud` checks are documented to work), not as a confirmed historical Descope vulnerability.
