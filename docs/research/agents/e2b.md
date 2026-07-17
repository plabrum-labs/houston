# E2B

**What it is:** Code sandbox for AI agents. Firecracker microVMs, network egress controlled by SNI/Host-header allowlisting without TLS termination.
**Axis:** agent platform (sandbox/execution).
**Depth:** thin, by design — short file per research scope.

## Products & surfaces

- **E2B Sandbox** — Firecracker microVM per session, dedicated kernel.
- **Domain allowlisting** — the egress control mechanism.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| SNI/Host-header domain allowlisting | Filters HTTP/80 via Host header, TLS/443 via SNI, without terminating TLS | yes, see ladder below |
| Allow-list only (no deny-list domain matching) | Positive-list model for domain filtering | yes |
| CIDR fallback for non-HTTP(S) ports | Non-80/443 traffic filtered by IP/CIDR only | maybe |

## Worth noting

Egress filtering is **allow-only for domains** — E2B's own docs state deny-list domain matching isn't supported, only CIDR-based blocking outside HTTP(S). Blocked connections can appear to succeed *inside* the sandbox before the firewall decides to drop them, because the firewall must accept the TCP connection before it can inspect Host/SNI. UDP-based protocols (QUIC/HTTP3) aren't covered by domain filtering at all.

Reported cold-start figure: **~150ms** — this is **unverifiable against E2B's own official documentation** in this pass; treat as secondary/marketing.

## Sources

- [e2b.dev/docs/sandbox/internet-access](https://e2b.dev/docs/sandbox/internet-access)
- [github.com/e2b-dev/E2B — Credential/Secret Brokering issue #1160](https://github.com/e2b-dev/E2B/issues/1160)
- Cold-start figure (~150ms): secondary comparison sites only, not confirmed in E2B's own docs.

See `daytona.md` for the comparison and the shared egress-ladder framing (recorded once, in `daytona.md`, to avoid duplication).
