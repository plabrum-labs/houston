# Auth — v0

Auth is Houston's identity and access platform. It is the layer above Data (`../data/`) that
answers three questions on every request: who is this, which organization are they acting as, and
does that organization's membership let them act at all. Any app that has its own users and
customer organizations pulls Auth in through Snacks rather than deriving login and membership
itself. Auth issues sessions and sets the request-scoping variables Data's row-level-security
policies read; it does not define the policies or own the schema they protect.

## Identity

An app's users authenticate by **magic link**, and v0 has no other path — no passwords, no SSO.
A user requests a link by email; Auth emails a single-use, time-limited token; following the link
verifies the token and establishes a session. The request side always responds identically
whether or not the email is known, so an attacker cannot use it to enumerate accounts, and it is
rate-limited per email. The verify side accepts a token exactly once, with a short grace window
for a link opened twice in quick succession — enough to tolerate a page reloading the same request
before the first response lands.

## Membership

A user can belong to more than one **organization**, and this is a many-to-many relationship, not
a column on the user: a **membership** joins one user to one organization and carries that
member's role within it, since a person can be an admin in one organization and a viewer in
another. Ownership is a role like any other, but at most one organization: a user can be **owner**
of only one organization at a time, enforced as a database invariant rather than an application
check —

```sql
CREATE UNIQUE INDEX ON memberships (user_id) WHERE role = 'owner';
```

— so a race between two requests can't produce a user who owns two organizations at once.

## Sessions

A session is server-side state, held in Houston's shared Redis and referenced by an opaque id in
the client's cookie — never a self-contained token, so a session can be revoked by deleting its
Redis entry rather than waiting out an expiry. Its payload is small and deliberate: the
authenticated user's identity and the **active organization** the session currently acts as.
Everything else a request needs — role, permissions — is derived from the active organization at
request time, not cached into the session payload, so a membership change takes effect on the
user's very next request.

## Active organization selection

A session always acts as exactly one organization, and picking that organization is a client
concern Auth exposes an API for, not a server guess. The client remembers the user's last-chosen
organization; Auth's login response tells the client whether that remembered choice is still a
membership the user holds. When it is, the client re-enters that organization with no further step
— the common case, and the *only* case for a user with a single membership, who never sees a
picker at all. When there is no remembered choice, or the remembered organization is no longer one
of the user's memberships, the client is told to prompt for one from the user's current membership
list, and whatever the user picks becomes the new remembered choice. Switching organizations later
is the same operation as this initial pick: it re-points the session's active organization and
nothing about the user's identity changes.

## Row-level security scope

Auth sets the session-scoped variables that Data's contract defines —
`app.organization_id`, `app.actor_id`, `app.actor_type` — at the start of each request's
transaction, from the session's authenticated user and active organization. Auth's own policy
shape covers exactly two of Data's postures: **organization-scoped** rows, visible only within the
session's active organization, and **user-owned** rows, visible only to the user that owns them,
with no notion of sharing a row outside either boundary. Because Data's policies deny by default
when their session variables are unset, a request that never reaches Auth's session-setting step —
an unauthenticated request, or a background job outside a request — sees none of either kind of
row, not everything.

Membership itself cannot be organization-scoped, since a user must be able to see every
organization they belong to — including ones that are not the active one — in order to switch
between them. The membership table, and the organization table it joins to, are Data's one
standing exception to "every table has an explicit posture": their posture is *enumerable by the
authenticated user across all their memberships*, not scoped to a single active organization the
way every other table is.

## Seams

### Data

Data owns the schema, the database roles, and the row-level-security policies that read
`app.organization_id` / `app.actor_id` / `app.actor_type`; Auth owns deciding what those variables
are set to on a given request and setting them at the start of its transaction. The dependency
runs one way — Auth depends on Data's session-variable contract, and Data's policies are indifferent
to how a session came to hold the values it does.

### Launchpad

A magic-link email is one outbound send, and Auth reaches Launchpad's `email` capability directly
to make it — the SES identity and DKIM/SPF records an app's configuration already provisions. Auth
composes and sends the one transactional message v0 needs; it takes no dependency on a
comms platform for delivery tracking, retries, or bounce handling, because a login link has no
audit or delivery-state requirement beyond "did the send call succeed."

### Snacks

Auth is delivered as a primitive: the identity, membership, session, and RLS-wiring mechanics are
**pinned** — every app relies on them working identically, the same way every app relies on Data's
roles — while the login page, organization picker, and organization switcher are an **owned**
surface an app pulls in and restyles freely, since their markup carries no contract anything else
depends on.

## Boundaries

Auth authenticates a request and decides which organization it acts as; it does not own anything
beneath or beyond that. It does not own the database roles, schemas, or policy definitions that its
session variables gate — that is Data. It does not send or track email beyond the one magic-link
message — a real comms platform, if an app needs one, is a separate dependency. It does not
implement sharing a row with a specific user or group outside organization and ownership boundaries
— that is out of scope for v0 entirely. It does not decide what a role is permitted to do beyond
gating row visibility — an app's own authorization logic, if it needs more than "which rows are
visible," is built on top of the role Auth resolves, not inside Auth.

## Not yet designed

- **Inviting a user into an additional organization** — the token, delivery, and acceptance flow
  that turns an invitation into a new membership.
- **Per-object sharing** — a Zanzibar-style relationship model granting access to a specific row
  outside the organization/ownership boundary, deferred to v1.
- **Account recovery** when a user loses access to their email entirely.
- **Device trust / multi-factor** beyond possession of the magic-link email.
