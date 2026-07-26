# Launchpad v0 — spike results

Results of running the spikes in `docs/platforms/launchpad/v0/spikes.md` against real AWS and
Cloudflare infrastructure. Each entry records what ran, the outcome, and anything discovered along
the way that isn't captured by the pass/fail criteria themselves.

## Cross-provider reconciliation, end to end

**Ran:** 2026-07-26. **Result: pass.**

`spikes/launchpad-v0/main.go` implements this spike as a single Go program using Pulumi's
Automation API, driving both the `aws` and `cloudflare` providers in one stack (`go run .`). It
provisioned an ACM certificate and an SES domain identity on AWS, created the matching Cloudflare
DNS validation records from their outputs, and waited for both to reach a validated state — all in
one `pulumi up`, no manual DNS step, no second reconciliation. Confirmed independently via
`aws acm describe-certificate` (`Status: ISSUED`) and `aws ses get-identity-verification-attributes`
(`VerificationStatus: Success`). All resources were destroyed afterward (`go run . -destroy`) and
confirmed gone from both providers.

Findings that don't change the pass/fail verdict but matter for how the rest of Launchpad's
Cloudflare integration gets built:

- **Cloudflare DNS record tags aren't universally available.** The spike's zone is on Cloudflare's
  Free plan, which has a DNS-record tag quota of 0 — tagging calls fail outright there, and
  separately the tag name used also exceeded Cloudflare's 32-character limit. Naming convention
  (embedding the app ID in the record name) is the durable ownership/teardown-tracking mechanism
  for Cloudflare-side resources, not tags — tags can't be assumed to work depending on account plan
  tier. AWS resources (the ACM cert) tagged fine; SES domain identities support neither tags nor
  this constraint, so the same naming-convention fallback applies there too.
- **Cloudflare has two token classes with different verify endpoints and zone visibility.** An
  account-owned token (`cfat_...` prefix, created under the account's own token management, not a
  user's profile) verifies at `/accounts/{account_id}/tokens/verify`, not `/user/tokens/verify` —
  the latter reports "Invalid API Token" for a perfectly valid account token, a red herring. More
  importantly, an account-owned token showed zero visible zones via `/zones` even while reported
  `active`, while a user-owned token scoped identically to the same zone worked immediately. Prefer
  user-scoped tokens for zone-level DNS work; if Launchpad's own credential model ends up needing
  account-owned tokens, confirm zone visibility explicitly rather than trusting "active" status
  alone. Directly relevant to the credential-scoping spike below.
- Running the spike required bridging this device's AWS auth: `~/.aws/config` uses a custom
  `login_session` key that only the Python `aws` CLI understands, which Pulumi's Go-SDK-based `aws`
  provider can't resolve on its own. Every run needs
  `eval "$(aws configure export-credentials --format env)"` first. Workstation-specific, not a
  finding about the design — but worth knowing if this spike is re-run from a different machine.

## Protected resource under a bad reconciliation

Not yet run.

## Per-app credential scoping across providers

Not yet run.
