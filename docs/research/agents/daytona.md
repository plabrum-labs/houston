# Daytona

**What it is:** Code sandbox for AI agents. CIDR-based network allowlisting, IPv4 only, capped at 10 entries. Isolation technology is unnamed in official docs.
**Axis:** agent platform (sandbox/execution).
**Depth:** thin, by design — short file per research scope.

## Products & surfaces

- **Daytona Sandbox** — isolated execution environment: "dedicated kernel, filesystem, network stack" per Daytona's own docs, plus allocated vCPU/RAM/disk.
- **Network Limits (Firewall)** — the `networkAllowList` configuration surface.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| CIDR allowlist, IPv4 only, max 10 entries | `networkAllowList`: comma-separated IPv4 CIDR blocks, no hostnames/domains/IPv6, hard cap of 10 | maybe |
| Configurable auto-stop/archive/delete | Lifecycle policies on idle sandboxes | maybe |

## Worth noting

⚠️ **Daytona's own docs describe the isolation as "dedicated kernel, filesystem, network stack" but never name the underlying technology.** Secondary sources (comparison blogs, not Daytona) claim it's Docker/OCI containers under the hood — **this is unresolved from official documentation and should be stated as such**, not asserted as fact. If true (container-based), "dedicated kernel" language in Daytona's docs would be worth scrutinizing against Replit's own explicit concession that containers share a kernel and aren't a perfect isolation boundary (see `replit.md`).

CIDR-only allowlisting is a materially weaker egress control than SNI/Host filtering: it **survives DNS tricks a domain-name allowlist would catch differently, but is effectively unusable against any CDN-fronted service** — you can't allowlist "just api.github.com" by IP when GitHub's API sits behind a CDN with a large, shifting IP range.

Reported cold-start figures — sub-90ms, with some sources claiming 27ms in optimized configurations — are **secondary/marketing only, not confirmed in Daytona's own official documentation**.

## The egress-enforcement ladder (recorded here, applies across the category)

From weakest to strongest, observed across Fly, E2B, Daytona, Modal, Vercel Sandbox, and Anthropic's own sandboxing:

1. **Port/protocol only** (e.g. Fly's default) — not an exfiltration control at all, just a network-shape restriction.
2. **CIDR allowlists** (Daytona) — survives DNS-rebinding-style tricks, but unusable against CDN-fronted services where the IP range is large and shifting.
3. **SNI/Host allowlisting without TLS termination** (E2B, Modal, Vercel's default) — the practical default across most sandbox vendors today; can allowlist by domain name rather than IP.
4. **TLS-terminating inspection + credential brokering** (Vercel's advanced tier, Anthropic) — the only tier that actually engages the real threat, because it can see and control what flows *through* an allowed connection, not just whether the connection is permitted.

**Even a correct allowlist only authorizes connections — it can't inspect what flows through them.** If `github.com` is allowlisted, a gist is a viable exfiltration endpoint. If `npm`/PyPI are allowlisted for legitimate installs, `npm publish` is an equally legitimate-looking exfil path through the same allowlist entry. And DNS itself is a covert channel most default firewalls leave open — a hostname like `aws-AKIAxxxxxxxx.attacker.com` leaks a credential at the moment of DNS resolution, before any HTTP request is even made.

## Sources

- [daytona.io/docs/en/network-limits](https://www.daytona.io/docs/en/network-limits/)
- [daytona.io/docs/en/sandboxes](https://www.daytona.io/docs/en/sandboxes/)
- [github.com/daytonaio/daytona](https://github.com/daytonaio/daytona)
- **Unresolved:** underlying isolation technology (container vs. VM) not named in Daytona's own docs; secondary sources claim Docker/OCI, unconfirmed by Daytona itself.
- Cold-start figures: secondary comparison sites only (Northflank, ZenML, others), not Daytona's own published documentation.
