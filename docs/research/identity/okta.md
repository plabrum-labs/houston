# Okta

**What it is:** The incumbent enterprise identity provider — the IdP most Houston enterprise customers will already have deployed, whether or not Houston builds anything Okta-specific.
**Axis:** enterprise.
**Depth:** thin.

## Products & surfaces

Workforce Identity (employee SSO/MFA/lifecycle), Customer Identity Cloud (formerly Auth0, kept as a separate product line post-acquisition), Identity Governance, Privileged Access. For Houston's purposes, Okta matters as **the SSO/SCIM endpoint on the other side of the integration**, not as a platform to build on.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Step-up auth via `acr_values`/`max_age` | Re-authenticate for a sensitive action without killing the whole session | yes (see auth0.md — same OIDC mechanism, Okta has a well-documented developer guide for it) |
| 7,000+ pre-built app integrations | Breadth as the moat | n/a — GTM, not a mechanism |

## Facts & figures (vendor/analyst-reported, not independently verified)

- **18,000+ customers**, **100B+ monthly authentications** cited as scale figures.
- **~41%** reported market share in IAM (source: 6sense, a marketing-attribution/tech-tracking firm — methodology not verified here).
- **7,000+** pre-built SSO integrations cited as the largest catalog in the category.
- Named a **Leader in the Forrester Wave: Workforce Identity Security Platforms, Q2 2026**.
- A live competitive theme as of mid-2026: **pricing criticism** — module-based, quote-driven, total deployment cost often not apparent until late in a sales cycle. Some analyst commentary describes teams declining auto-renewal to shop the governance/lifecycle layers Okta sells as paid add-ons.

## Sources

- [Okta named a Leader in the 2026 Forrester Wave](https://www.okta.com/newsroom/press-releases/forrester-wave-workforce-identity-security-2026/)
- [Okta in 2026 — Still the Identity Standard, But Now It Has to Earn It](https://digitalbydefault.ai/blog/okta-identity-management-review-2026)
- [Okta market share (6sense)](https://6sense.com/tech/identity-access-management/okta-market-share)
- [Top 7 enterprise SSO providers for B2B SaaS apps in 2026 (WorkOS)](https://workos.com/blog/enterprise-sso-providers-b2b-saas)
- [Step-up authentication using ACR values (Okta Developer)](https://developer.okta.com/docs/guides/step-up-authentication/main/)
- **Not verified beyond search-result level:** the 18,000-customer / 100B-authentication figures and the 41% market-share number are third-party/analyst-reported and were not cross-checked against an Okta primary source in this pass.
