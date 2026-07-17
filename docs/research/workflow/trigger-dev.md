# Trigger.dev

**What it is:** Durable background-job platform; the notable mechanism is **waitpoint tokens** — an HTTP-completable, unbilled suspension primitive for human-in-the-loop and external-callback waits.
**Axis:** workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Trigger.dev tasks** | Durable, retryable background functions. |
| **Waitpoints / `wait.forToken()`** | Suspend a run until an external HTTP callback (or SDK call) completes a token. |
| **Trigger.dev Cloud / self-hosted** | Managed or self-hosted execution. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Waitpoint tokens | Mint a token with a callback URL; POST to it resumes the run | yes |
| Unbilled suspension | The run is paused (not executing, not billed) while waiting on a token | yes |
| Configurable timeout | Tokens default to a 10-minute timeout, avoiding indefinite waits | yes |

## Worth stealing

### Waitpoint tokens — HTTP-completable, no polling required

`wait.createToken()` mints a token (default timeout `"10m"`) that returns a **callback URL**. A run can then call `wait.forToken()` to suspend until that specific token is completed — either via the SDK or by an external system making a plain **HTTP POST to the callback URL** with the result payload. This makes "wait for a human to approve this" or "wait for a third-party webhook" a first-class suspend point rather than a polling loop: nothing needs to keep checking status, the run itself stays parked until the POST arrives.

**The suspended run is unbilled** — on the Cloud product, calling `wait.forToken()` pauses execution and billing stops until the callback resumes it. This is the same "suspend at zero cost" property that shows up across durable execution engines (Temporal's don't-poll ethos, Inngest's `step.waitForEvent()`), but Trigger.dev's version is notable for being **directly HTTP-addressable** — any external system, including a form on a web page, a Slack button, or a third-party webhook, can complete the wait with a bare POST, no SDK integration required on the calling side.

Because the token carries its own **timeout**, an unanswered wait doesn't hang the run forever by default — it resolves (fails or falls through, depending on configuration) once the timeout elapses, which avoids the "stuck forever" failure mode that unstructured wait-for-external-event code is prone to.

## Worth avoiding

The source material for this file is thinner than the other durable-execution vendors — worth a deeper pass (pricing model for suspended runs at scale, exact timeout/retry semantics on token expiry, self-hosted operational characteristics) before treating this as a complete picture.

## Facts & figures

- Default waitpoint token timeout: 10 minutes (configurable) (vendor docs).

## Sources

- [Wait for token](https://trigger.dev/docs/wait-for-token) · [Wait for HTTP callback (changelog)](https://trigger.dev/changelog/wait-for-http-callback) · [Waitpoints (changelog)](https://trigger.dev/changelog/waitpoints)
- **Not directly verified:** billing/suspension mechanics beyond the changelog description; self-hosted vs. Cloud parity for unbilled suspension was not independently confirmed.
