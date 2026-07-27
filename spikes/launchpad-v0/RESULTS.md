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

**Ran:** 2026-07-26. **Result: pass.**

`spikes/launchpad-v0/spike2.go` (`go run . -spike=2`) reconciles a protected `postgresql.Schema`
and `postgresql.Role` keyed by an immutable app ID against a throwaway local Postgres in Docker,
then reconciles a second, deliberately bad program that derives both the Pulumi identity *and* the
underlying database object names of the same resources from the app's mutable display name instead
— the class of bug the spike exists to catch. The bad reconciliation created new, wrongly-named
objects and then, exactly as it should, errored trying to delete the original protected schema:
`resource ... cannot be deleted because it is protected`. Confirmed independently via `psql` that
the original role and schema were untouched. Torn down by removing the Docker container and the
Pulumi stack's local bookkeeping together, since nothing in the mixed post-failure state (original
protected objects plus the newly-created ones, both also protected) pointed at anything worth
reconciling through — a throwaway local instance makes that unnecessary.

One implementation-worth-noting finding: the first version of this spike had the bug vary only the
Pulumi *logical* resource name, leaving the database-level object name unchanged. That produced a
false pass — the bad reconciliation failed on a Postgres "role already exists" error before Pulumi
ever attempted to delete the protected original, because Pulumi creates the new (orphaning)
resource before deleting the one that fell out of the desired state, and the unchanged DB name
collided. Protection was real (confirmed separately when tearing down the good state), but that
first version of the spike didn't exercise it. Varying both the Pulumi identity and the DB object
name, matching a bug where a refactor ties an app's whole resource identity to its display name, is
what actually drives Pulumi into the delete-a-protected-resource path the design's claim is about.

## Per-app credential scoping across providers

**Ran:** 2026-07-26. **Result: AWS passes; Cloudflare does not have a per-app boundary, as
expected.**

`spikes/launchpad-v0/spike3.go` (`go run . -spike=3`) provisions two apps, each with its own SES
domain identity and an IAM role scoped by inline policy to only that identity's ARN, then assumes
each role via STS and confirms it can read its own app's SES identity but is denied on the other's
(`AccessDeniedException: ... because no identity-based policy allows the ses:GetEmailIdentity
action`) — the AWS half of the isolation claim holds exactly as the design describes. On the
Cloudflare side, both apps' DNS records live in the one zone available to this spike (`SPIKE_ZONE`)
— Cloudflare's API token model has no permission narrower than the whole zone, so rather than
gamble on provisioning a second scoped token, the spike proved that directly: it used the one
available token to `PATCH` app B's record and got back `success=true`, confirmed live rather than
just reasoned from documentation. A zone-scoped credential necessarily reaches every app sharing
that zone. This doesn't fail the spike's own pass/fail bar (the bar for Cloudflare was explicitly
"if token granularity can't express a narrower boundary, isolation needs a second mechanism") — it
confirms the fallback the [reconciliation spike](#cross-provider-reconciliation-end-to-end)'s
findings already anticipated: naming convention, not Cloudflare's permission model, is what has to
carry app-level isolation for two apps in a shared zone.

Two things worth carrying forward:

- **IAM's trust-policy propagation lag is real and needs a state machine, not a fixed sleep.** The
  first run called `sts:AssumeRole` immediately after `pulumi up` finished creating the role, and
  every attempt — including a role reading its *own* identity — was denied with `is not authorized
  to perform: sts:AssumeRole`. A fixed sleep before checking is a guess at how long that takes;
  `waitForAssumeRolePropagation` in `spike3.go` instead polls each role against its own identity
  and treats the two outcomes as distinct states — `sts:AssumeRole`-denied means "propagating, keep
  polling," any other error means "actually failed, stop" — until it resolves or a timeout is hit.
  Re-running showed why a fixed guess would've been wrong either way: one role propagated on the
  first attempt, the other took five (~8s). Once a role's propagation resolves, later checks
  against it need no retry of their own — propagation is a fact about the role, established once.
  Launchpad's real reconciler, if it ever needs to use a role immediately after creating it (rather
  than handing it to a long-running ECS task that assumes it later), needs the same kind of
  poll-to-a-resolved-state handling instead of treating an immediate `AssumeRole` denial as a hard
  failure.

  This only bites a brand-new app's *first* deploy — reconciliation just created the app's IAM role,
  and something has to use it almost immediately: the migrator assuming it to apply the first
  migration, and ECS launching the task under it. The fix belongs at that point of use, not as a
  general wait bolted onto reconciliation itself — most likely the migrator's AssumeRole call (ECS's
  own task-launch retries may already absorb the lag for the task role), wrapped in the same
  poll-and-distinguish behavior `waitForAssumeRolePropagation` uses: `AssumeRole`-denied means keep
  polling, any other error is real and should fail fast. Scoping it to that one call site avoids
  adding latency to every deploy to cover an edge case that only affects the first one.
- **Root-principal trust policies need the assuming identity to have its own `sts:AssumeRole`
  permission too.** The spike's roles trust `arn:aws:iam::<account>:root`, which only grants the
  *resource* side of the AssumeRole authorization; the calling IAM user or role still needs
  `sts:AssumeRole` in its own identity-based policy (satisfied here by `AdministratorAccess`). Not
  a finding about Launchpad's design — its own reconciler will hold assume-role rights by
  construction — but worth knowing if this spike gets re-run under a more locked-down principal.
