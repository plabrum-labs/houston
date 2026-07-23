# Observability — todo

Logging, tracing, and error monitoring across tenant apps.

- Source: Houston (net-new; confirmed absent from snacks)

## What it is

Per-app logging, tracing, and error monitoring — the visibility layer over apps that, on the
shared fleet, ECS / CloudWatch container metrics cannot see below the container level.

## To design

- [ ] Per-app log tagging / forwarding — builds on Cryo's per-backend stdout/stderr capture and
      metrics endpoint (`../cryo/`).
- [ ] Tracing (`otel`) across the fleet.
- [ ] Error monitoring / alerting.
- [ ] What the app builder sees vs. what the platform operator sees.

## Open questions

- Self-hosted vs. an external backend for traces / errors.
