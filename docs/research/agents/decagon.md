# Decagon

**What it is:** Customer-facing conversational AI agent platform ("AI concierge").
**Axis:** agent platform.
**Depth:** thin — public documentation is marketing-forward; no deep technical or incident writeups located. Don't guess past what's stated.

## Products & surfaces

- **Decagon** — conversational support agent, configured via **Agent Operating Procedures (AOPs)**: natural-language workflow definitions that teams write by converting existing SOPs.
- Identity-provider integrations (Okta, Microsoft Entra) for platform-side access control of human users.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Agent Operating Procedures (AOPs) | Natural-language workflow specs, converted from existing human SOPs | maybe |
| Short-lived, scoped JWTs for agent-to-system calls | Agent gets a minimal-privilege token per session, discarded after | yes |
| Read vs. write API permission split | Read-only access lets the agent retrieve data; write access is a separate, explicit grant for taking action | yes |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

- **Short-lived JWTs scoped for minimal privilege, discarded per session** — a standard but correctly-applied pattern for bounding what a conversational agent's backend calls can reach, and for how long.
- **Explicit read/write separation at the API-permission level**: an agent can be wired for read-only retrieval without also being wired for write actions (create/update/trigger-workflow), and those are described as separately granted.

## Worth avoiding

Nothing identified — there isn't enough public material to assess failure modes either way.

## The honest state of this research

Decagon's public docs describe **identity verification, payment processing, and case escalation** as example multi-step actions an agent can run "independently or with an agent's approval," but do not publicly specify the underlying authorization model in the depth Sierra, Glean, or Salesforce do (no published equivalent of Sierra's supervisor architecture, Glean's pre-LLM ACL filtering, or Salesforce's dedicated-agent-user model). Say so rather than infer a mechanism from marketing copy.

## Facts & figures

None with independent verification found. Do not cite customer counts, resolution rates, or accuracy figures from Decagon's own site without flagging them as vendor-reported — none were pulled into this file because none could be cross-checked.

## Sources

- [decagon.ai/security](https://decagon.ai/security)
- [decagon.ai — AI customer support setup](https://decagon.ai/blog/ai-customer-support-setup)
- [decagon.ai — AI agent assistance](https://decagon.ai/resources/ai-agent-assistance)
- **Gap:** no independent (non-vendor) technical or security review of Decagon was located during this pass.
