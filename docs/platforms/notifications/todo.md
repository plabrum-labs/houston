# Notifications — todo

Cross-channel notification hub — unifies Comms (email) + Threads (in-app) + push behind one
per-user preference / digest center.

- Source: Houston (core platform; promoted — snacks has the channels but no unifying layer)

## What it is

A single hub routing a notification to the right channel(s) per a user's preferences, with a
shared preference and digest layer that snacks does not have today.

## To design

- [ ] Per-user preference model (which events, which channels, digest cadence).
- [ ] Channel adapters: email (via Comms), in-app (Threads), push.
- [ ] Subscription to Events (`../events/`) as the notification source.
- [ ] Digest batching.

## Open questions

- Where in-app threads live (Comms vs. here).
- Push infrastructure (provider, device tokens).
