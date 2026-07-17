# Heroku

**What it is:** The original PaaS deploy-DX vocabulary — pipelines, slugs, review apps, release phase. Most of what Vercel/Render/Railway now do with more polish, Heroku specified first. The one piece nobody has cleanly replicated is Release Phase.
**Axis:** deploy, migration.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Release Phase** | A `release` Procfile process type that runs in a one-off dyno before a new release goes live, gating the release on success. |
| **Pipelines** | Development → Review → Staging → Production stages of apps sharing one codebase. |
| **Slug promotion** | Copy the already-compiled build artifact to the next stage instead of rebuilding. |
| **Review Apps** | Ephemeral apps auto-created per GitHub pull request (2016, the original PR-preview-environment product). |
| **Preboot / Rolling deploys** | Zero-downtime release mechanisms — overlap old/new dynos (Common Runtime) or replace ≤25% of dynos at a time (Private Spaces). |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **Release Phase gating** | New release does not deploy to the dyno formation until the `release` command exits 0 | yes |
| Release Phase re-runs on promotion | Runs again on a pipeline promotion even though promotion produces no new build | yes |
| Release Phase timeout | Hard 1-hour ceiling, non-configurable | maybe |
| Slug promotion | Copies the compiled artifact between stages; "much faster than rebuilding" | yes |
| `heroku releases:retry` | Explicit retry path for a failed release phase | yes |
| Preboot | New dynos boot and receive traffic before old ones stop; up to 3 minutes of both versions running, only one serving | maybe |
| Rolling deploys (Private Spaces) | Stop/replace at most 25% of dynos at a time | maybe |

## Worth stealing

### Release Phase — the gate, not just a migration runner

The mechanism: a `release` process type in the Procfile runs in a one-off dyno *before* the app's regular dynos boot for that release. Heroku's own wording is unambiguous about the gate: *"App dynos don't boot for a new release until the release phase finishes successfully."* If the release command exits non-zero, or the dyno manager kills it, **the release fails and is not deployed** — the app keeps running the previous release, dynos never restart onto the new code, and Heroku sends a failure notification. This is a hard block, not a warning: a broken migration cannot reach production traffic.

**The detail that generalizes best:** release phase runs on *every* new release — a successful build, a config var change, a pipeline promotion, a rollback, a platform API release, or provisioning an add-on — **including promotion, where no new build is produced at all**. Promoting a tested slug from staging to production still re-runs the release task (e.g., migrations) against production's database before the promoted slug goes live. That's what makes slug promotion safe rather than merely fast: the artifact is identical to what was tested in staging, but the release-time side effects (migrations, cache priming) still execute against the target environment's actual state.

One sharp edge preserved from the docs: **a release triggered by a config var change still takes effect even if the release command then fails** — the var change isn't rolled back, only the dyno restart is blocked. Config state and release-phase gating are two different transactions.

### Slug promotion — the artifact never changes, only where it runs

A slug is the single compiled build artifact (code + dependencies + runtime + static assets), built once. Promotion between pipeline stages copies that exact artifact to the next stage's app rather than rebuilding — Heroku's framing: *"ensures that production contains the exact same code that you tested in staging, and it's also much faster than rebuilding the artifact."* This requires **stateless builds** — nothing environment-specific baked into the artifact at build time (e.g., no environment's CDN URL hardcoded during compile) — otherwise promotion silently carries the wrong environment's values forward.

### Review Apps — the 2016 original

Ephemeral, full apps auto-created per GitHub pull request when GitHub integration is enabled, torn down on merge/close. This is the ancestor of every "PR preview environment" product now shipped by Vercel, Netlify, Railway, and Render — Heroku had it running production-grade (full add-ons, full dyno billing) a decade before it became table stakes.

## Worth avoiding

- **Release Phase has a hard 1-hour timeout with no extension path** — a genuinely long-running migration (large table backfill on a big production database) simply cannot use release phase as specified; teams have to split migrations into phases that individually fit the window.
- **Slug promotion's "stateless build" requirement is easy to violate silently** — a build step that reads an environment variable at compile time (rather than at runtime) breaks the "identical artifact across all stages" guarantee without any error; the artifact still promotes, it just carries the wrong baked-in values.

## Facts & figures

- Release phase timeout: 1 hour, not configurable.
- Preboot overlap window: up to ~3 minutes with both old and new dyno versions running (only new version serving after cutover).
- Rolling deploys (Private Spaces): replace at most 25% of dynos per step.
- Review Apps: 2016 launch, GitHub-integration-driven, full dyno/add-on billing during their lifetime.

## Sources

- [Release Phase](https://devcenter.heroku.com/articles/release-phase)
- [Pipelines](https://devcenter.heroku.com/articles/pipelines)
- [Preboot](https://devcenter.heroku.com/articles/preboot) · [Rolling Deploys](https://devcenter.heroku.com/articles/rolling-deploys) · [Rolling deploys changelog](https://devcenter.heroku.com/changelog-items/860)
- **Not directly verified in this pass:** exact current review-app pricing/lifecycle defaults (the 2016-launch framing and general mechanism are well-documented; current-year pricing specifics were not re-checked).
