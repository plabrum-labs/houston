# Comms — todo

Email transport for apps — a state-machine-backed email service.

- Source: snacks (port)

## What it is

The outbound email primitive: send, track delivery state, back it with a state machine. The
email channel that feeds Notifications (`../notifications/`).

## To design

- [ ] Adopt the snacks email-transport service as this platform's implementation.
- [ ] State-machine model for email lifecycle (queued → sent → delivered / bounced).
- [ ] Seam with Launchpad's `email` capability (SES identity, DKIM / SPF): Comms is the
      application-level service; Launchpad provisions the sending infrastructure.
- [ ] Threads / in-app messaging: decide whether in-app chat lives here or folds into
      Notifications.

## Open questions

- Relationship between Comms (email), Threads (in-app), and Notifications (the unifying hub).
