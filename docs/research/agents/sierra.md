# Sierra

**What it is:** Agent OS for customer-facing conversational agents, built around a primary agent watched in real time by secondary "supervisor" agents, sold on outcome-based pricing.
**Axis:** agent platform, enterprise governance.
**Depth:** medium — the supervisor architecture and pricing model are well-documented by Sierra itself; the billing audit mechanism and the independence assumption in their reliability math are not.

## Products & surfaces

- **Sierra Agent OS** — the platform: a primary conversational agent plus supervisory agents, deterministic guardrails, and a tolerance-tier config layer.
- Sierra describes its model layer as a **"Constellation of Models"** — 15+ models from multiple providers (OpenAI, Anthropic, Meta, Google) doing different jobs rather than one model doing everything.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Supervisor/interceptor agents | Secondary models with narrow, independently-evaluable jobs, watching the primary agent in real time | yes |
| Observe → intercept escalation | Supervisors default to watching; escalate to steering/blocking only on high-risk topics | yes |
| Tolerance tiers | Adversarial topics get maximum adherence (robotic answers acceptable); tone gets flexibility | yes |
| Task-specialized models | Low-latency models for lookups, high-precision classifiers for behavior detection, tone-optimized models for sensitive turns | yes |
| Outcome-based pricing | Charge only on a defined successful outcome (resolved conversation, saved cancellation, completed transaction); unresolved/escalated conversations typically don't bill | maybe — see caveat |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

### Supervisors as a narrow, independently-evaluable check, not a second opinion from the same model

Sierra's own shorthand for these is **"Jiminy Crickets"** — agents whose entire job is to watch the primary agent for ambiguous or sensitive situations and take **subtle corrective action** (e.g., steering the agent away from mentioning a competitor) rather than only killing the conversation outright. The premise, stated by Sierra: engineering **bounded error rates**, not perfect adherence — *"at scale, a one-in-ten-thousand hallucination rate is a daily occurrence."* That's a different design target than "make the model never wrong": it's "make the system catch the model when it's wrong, often enough that the residual rate is tolerable."

### Tolerance tiers as an explicit, topic-scoped policy

Not every failure mode gets the same response. Adversarial or high-stakes topics get maximum adherence — even at the cost of stiff, robotic answers. Tone and style get more slack. This is a concrete, generalizable pattern for calibrating how tightly a supervisor should constrain the primary agent, topic by topic, rather than applying one global strictness setting.

## Worth avoiding

### The reliability math doesn't hold up on inspection

Sierra's public claim is roughly: 90% agent accuracy + 90% supervisor catch rate → 99% combined. **That arithmetic assumes the agent's and supervisor's errors are independent events.** They plausibly aren't — both are LLMs, likely trained on overlapping data and possibly sharing failure modes (the same ambiguous input that confuses the primary agent may also confuse a supervisor built the same way). No published methodology addresses this. Treat the "99%" figure as a marketing extrapolation, not a measured system-level error rate.

### Outcome-based billing has no documented audit mechanism

The commercial pitch — pay only for defined outcomes — genuinely aligns incentives between Sierra and its customers. But **the outcome metric is both defined and scored by Sierra itself**, and there is no publicly documented independent audit of that scoring. Aligned incentives are not the same thing as verifiable billing; a customer has no described way to check Sierra's own count of "resolved conversations" against ground truth.

### The Gap.com counter-evidence

The Gap.com customer-service misconfiguration incident is the one piece of independent, non-Sierra-controlled evidence bearing on how these systems actually fail in production, as distinct from Sierra's self-reported success claims. (Treat as a landscape data point — Sierra's own material does not discuss it.)

## Landscape note (cross-category, not Sierra-specific)

**External-facing support agents have no end-user identity to inherit** — there's no "requester's ACL" to scope against, because the requester is a customer, not an employee with existing permissions. The pattern every vendor in this space independently converged on is scoping by **action authorization** — deterministic, non-model code gating refunds, identity checks, and other irreversible actions — rather than data-access scoping. Sierra (hard stops: dollar limits, vendor blocklists, category restrictions, all outside the model — see also `ramp.md`'s Ramp Agents section, which uses the identical shape), Decagon (see `decagon.md`), Glean (see `glean.md`), and Salesforce Agentforce (its dedicated-agent-user model is covered in `salesforce.md`, not duplicated here) all landed on the same conclusion from different starting points: **don't trust the model with irreversible actions — gate those with deterministic code, not model judgment.**

## Facts & figures

- 15+ models across multiple providers in Sierra's "Constellation" architecture. Vendor-reported.
- Outcome-based pricing: no charge on unresolved or escalated conversations, per Sierra's own description. Vendor-reported, no third-party audit found.

## Sources

- [Sierra — Outcome-based pricing for AI Agents](https://sierra.ai/blog/outcome-based-pricing-for-ai-agents)
- [Sierra — Product overview](https://sierra.ai/product)
- Secondary coverage of "Constellation of Models" and supervisory-agent ("Jiminy Cricket") framing via third-party guides (myaskai, getmacha) — cross-check against Sierra's own blog where possible; not all claims traced to a Sierra-published primary source.
- **Gap:** no public methodology for the 90%+90%→99% reliability claim; no public audit mechanism for outcome-based billing.
