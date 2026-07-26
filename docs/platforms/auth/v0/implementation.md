# Auth — v0 implementation

Building v0 means: a magic-link identity flow, a membership model that supports multi-organization
users, Redis-backed sessions, the request-time hook that sets Data's RLS variables from a session,
and the client-side active-organization selection that decides what those variables are set to.

## Identity model

Implements: Identity
Depends on: Nothing

- `users` table (Data's platform schema): `id`, `email` (unique), `email_verified_at`.
- `magic_link_tokens` table: `id`, `user_id` (FK), `token_hash`, `expires_at`, `used_at`.
  - The token itself is a high-entropy random value; only its hash is stored, so a database read
    alone never yields a usable token.
  - Expiry is short — minutes, not hours.
- `POST /auth/magic-link/request { email }`:
  - Rate-limited per email.
  - Looks up the user by email; if found, generates a token, stores its hash and expiry, and sends
    it through the Launchpad email seam.
  - Responds with an identical generic message whether or not the email matched, and never raises
    on a lookup miss — the response carries no signal either way.
- `GET /auth/magic-link/verify?token=...`:
  - Hashes the incoming token and looks up an unexpired match.
  - Accepts the token if `used_at` is null, **or** if `used_at` is within a short grace window
    (seconds) of now — a double-fired verify request from the same click reuses the same result
    instead of failing the second one.
  - On success: sets `used_at` if unset, sets `email_verified_at` on the user if unset, and
    proceeds to session establishment.
  - On failure (expired, unknown, outside the grace window): a single generic error, no detail on
    which condition failed.

## Membership model

Implements: Membership
Depends on: Identity model

- `organizations` table (Data's platform schema): `id`, `name`.
- `memberships` table: `id`, `user_id` (FK, cascade on user delete), `organization_id` (FK,
  restrict), `role` (`owner` | `admin` | `member` | `viewer`).
  - `UNIQUE (user_id, organization_id)` — one membership row per user per organization.
  - `UNIQUE (user_id) WHERE role = 'owner'` (partial index) — a user owns at most one organization,
    enforced by Postgres rather than a service-layer check, so a race between two concurrent
    "create organization" calls can't both succeed.
- `organizations` and `memberships` are Data's named exception to per-row RLS posture (see
  design.md, Row-level security scope): both are readable by a user for their own rows across every
  organization they belong to, rather than scoped to one active organization. Policy shape: a
  membership row is visible when `user_id = current_setting('app.actor_id')`, independent of
  `app.organization_id`; an organization row is visible when a membership joining it to the current
  actor exists. Every other table in an app's schema keeps the standard organization-scoped or
  user-owned posture Data defines.

## Session store

Implements: Sessions
Depends on: Nothing

- Sessions live in Houston's shared Redis, keyed by an opaque session id.
- Cookie carries only the session id — `HttpOnly`, `Secure`, `SameSite=Lax` — no session data in
  the cookie itself.
- Session payload (JSON): `{ user_id, active_organization_id }`. `active_organization_id` is null
  immediately after identity verification and before an organization has been selected.
- Session TTL refreshes on access; deleting the Redis key revokes the session immediately.

## RLS variable wiring

Implements: Row-level security scope; Seams — Data
Depends on: Membership model, Session store

- A single request-scoped hook wraps every authenticated request in one database transaction and,
  before any handler code runs:
  - Reads `user_id` and `active_organization_id` from the session.
  - If `active_organization_id` is set, confirms a `memberships` row still joins that user to that
    organization (a membership may have been revoked since the session was created) and, if valid,
    issues `SET LOCAL app.organization_id = ...`, `SET LOCAL app.actor_id = ...`,
    `SET LOCAL app.actor_type = 'customer'` for the transaction's duration.
  - If the membership no longer holds, treats the session as having no active organization: the
    variables are left unset and the client is signaled to re-select (see Active organization
    selection).
  - If `active_organization_id` is unset, the request proceeds with no organization-scoped
    variables set — routes that only need `memberships`/`organizations` (session bootstrap, the
    picker) are the only ones reachable in this state; every organization-scoped table denies by
    default.
- `SET LOCAL` values are validated as integers before interpolation — `SET LOCAL` takes no bind
  parameters, so this hook is the one place a raw value is written directly into SQL text, and it
  is written only after the value has been read back out of the session/membership lookup, never
  taken directly from request input.

## Active organization selection

Implements: Active organization selection
Depends on: Session store, Membership model

- `GET /auth/memberships` — returns the authenticated user's full membership list (organization id,
  name, role), independent of the session's current active organization. Bypasses the standard
  organization-scoped RLS variables entirely, per the membership/organization RLS exception.
- `POST /auth/select-organization { organization_id }` — validates a membership exists for the
  requesting user, sets the session's `active_organization_id`, and returns the resolved role.
  Used for both the initial pick and every later switch; there is no separate "switch" endpoint.
- Client contract:
  - After verify, the client holds a last-remembered organization id in `localStorage` (or holds
    none, on a first login or a new device).
  - The client checks the remembered id against the membership list from `GET /auth/memberships`.
    If it's present, the client calls `select-organization` with it directly — no picker is shown.
  - If the remembered id is absent, or absent from the current membership list (revoked, or never
    set), the client renders a picker over the membership list; whatever the user picks is sent to
    `select-organization` and written back to `localStorage`.
  - A user with exactly one membership never has a divergent remembered choice, so the picker never
    renders for them.

## Magic-link email delivery

Implements: Seams — Launchpad
Depends on: Identity model

- The magic-link send calls Launchpad's `email` capability directly with a rendered subject/body
  and the target address — one outbound call, no queue, no delivery-state table.
- A send failure surfaces synchronously to the `request` endpoint's caller as a generic error (see
  Identity model); v0 does not retry a failed send, since a user can always request a new link.
