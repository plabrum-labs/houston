# n8n

**What it is:** Open-source workflow automation tool (trigger → action nodes); notable mainly for the HTTP Request node as its universal escape hatch.
**Axis:** workflow.
**Depth:** thin.

## Products & surfaces

| Product | What it is |
|---|---|
| **n8n workflows** | Trigger node + chain of action nodes, visually composed. |
| **HTTP Request node** | Generic REST-call node — the fallback for any service without a bespoke connector. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| HTTP Request node | Call any REST API directly from the canvas, no custom connector needed | yes |

## Worth stealing

**The HTTP Request node as the escape hatch.** n8n's own framing: it lets you *"query data from any app or service with a REST API"* without a bespoke, maintained connector — configure the request directly (or import a curl command), including pagination handling for large result sets. It can also be attached to an AI agent as a callable tool, not just used as a static pipeline step. The reusable idea: **a great generic HTTP step is a force multiplier against the connector-maintenance treadmill** — every unsupported third-party service is still reachable on day one, at the cost of the user hand-configuring auth/pagination/parsing instead of getting it for free.

## Facts & figures

- (none independently verified beyond the HTTP Request node's documented capabilities.)

## Sources

- [HTTP Request node docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest) · [HTTP Request node cookbook](https://docs.n8n.io/code/cookbook/http-node/)
- **Not directly verified:** broader n8n connector-count/ecosystem-size figures were not researched for this file; see `zapier.md` for the connector-ecosystem framing.
