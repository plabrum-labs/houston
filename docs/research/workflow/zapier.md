# Zapier

**What it is:** The largest third-party connector ecosystem in workflow automation; notable for how it handles vendors with no webhook support — polling.
**Axis:** workflow.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **Zaps** | Trigger + action chains across ~8,000–9,000 connected apps. |
| **Polling triggers** | For apps without webhook support, Zapier periodically calls the app's API to check for new data. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| ~8,000–9,000 connectors | Breadth as the core product bet | no — see below |
| Polling triggers (`Retrieve Poll`) | Periodic GET against a REST endpoint when no webhook exists | yes, as a fallback pattern |

## Worth stealing

**Polling as the honest fallback, not a hidden hack.** Where a third-party vendor has no webhook support, Zapier's `Retrieve Poll` trigger periodically issues a GET against a REST endpoint on a fixed cadence (roughly every 1–15 minutes depending on plan tier), rather than requiring the vendor to support push. This is named and documented as a first-class trigger type (distinct from `Catch Hook`, which waits for a vendor's POST), not an undocumented degraded mode — worth stealing the framing, not just the mechanism: **explicitly support "we poll because this vendor can't push," rather than silently degrading.**

## Worth avoiding — the landscape point

**The connector ecosystem is unwinnable as a strategy to compete on directly.** ~8,000–9,000 connectors (vendor-reported, count varies by source) represents enormous, continuously-maintained integration surface area that a challenger cannot realistically match head-on. The practical implication for any competing platform: **ship a great generic HTTP step (see `n8n.md`) plus a small number of connectors for the handful of services that are truly enterprise-critical** for your specific customers, rather than attempting breadth-first parity with an incumbent whose entire business model is the connector catalog.

## Facts & figures

- ~8,000–9,000 connected apps (vendor-reported, figure varies across Zapier's own marketing pages — 8,000+ in some places, 9,000+ in others as of 2026).
- Polling interval: roughly 1–15 minutes per active Zap depending on plan level (vendor docs).

## Sources

- [How Zap triggers work](https://help.zapier.com/hc/en-us/articles/8496244568589-How-Zap-triggers-work) · [Trigger Zaps from polling webhooks](https://help.zapier.com/hc/en-us/articles/8496274719757-Trigger-Zaps-from-polling-webhooks) · [Polling for New Data with a Trigger](https://developer.zapier.com/cli-guide/polling-for-new-data-with-a-trigger)
- [Zapier MCP — "Connect AI tools to 9,000 apps"](https://zapier.com/mcp)
- **Not directly verified:** the discrepancy between "8,000+" and "9,000+" across Zapier's own pages was not reconciled to a single authoritative figure.
