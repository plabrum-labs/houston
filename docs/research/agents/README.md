# Agents

**What this category is:** platforms and infrastructure for building, running, and governing AI agents in production — coding agents, customer-facing conversational agents, enterprise search/RAG agents, and the sandbox/eval infrastructure underneath them.
**Why it's in this research:** Houston is agent-native and will expose its semantic layer and app surfaces to agents directly. This category is the landscape of how the industry currently scopes agent authority, isolates agent execution, and evaluates agent behavior.
**Files:** 8.

## The players

| Company | What it is | Depth |
|---|---|---|
| [ramp](ramp.md) | Internal coding-agent sandbox (Inspect) + customer-facing agent line (Ramp Agents) with a documented trust model | deep on Inspect + Agents trust model; **permission model undocumented** |
| [sierra](sierra.md) | Agent OS for customer-facing conversational agents — primary agent watched by real-time supervisor agents | medium |
| [glean](glean.md) | Enterprise search/RAG where permissions are resolved and content discarded before the model ever sees it | medium |
| [e2b](e2b.md) | Firecracker microVM code sandbox; SNI/Host-header egress allowlisting | thin, by design |
| [daytona](daytona.md) | Code sandbox; CIDR-only egress allowlisting; isolation technology unnamed in official docs | thin, by design |
| [braintrust](braintrust.md) | Eval/observability platform — the eval framework Ramp uses in production | thin, by design |
| [langfuse](langfuse.md) | Open-source LLM eval/observability — the only tool in the set that instruments its own LLM judges | thin, by design |
| [decagon](decagon.md) | Customer-facing conversational agent platform | thin — marketing-forward docs, no independent technical writeups found |

Ramp is the deepest and most concrete file in the category — a real production sandbox architecture (Inspect) plus a documented trust model (Ramp Agents) — but even it has a load-bearing gap: the permission model behind Ramp Agents is not publicly documented. Sierra and Glean are the two other substantive files. Decagon is thin by evidence, not by editorial choice — say so rather than infer a mechanism from its marketing copy.

## Convergence

**The compute-sandbox problem and the authority-scoping problem are different problems, and this research set has an example of each.** Ramp Inspect is a *capability* story — a sandboxed VM with the full dev stack, VS Code, a browser, and observability integrations, built to give a coding agent *more* surface to act on. Ramp Agents, Sierra, Glean, and Decagon are all *scoping* stories — built to give an agent *less* authority than the system technically could grant. Houston-relevant infrastructure will need both, and they are not the same design problem: one is about isolation and blast-radius containment for an agent that writes code; the other is about authorization and revocability for an agent that acts on behalf of a user.

**Don't trust the model with irreversible actions — independently reached by four vendors.** Sierra (deterministic hard stops: dollar limits, vendor blocklists, category restrictions, all outside the model), Ramp Agents (the identical shape — authority lives in the existing workflow builder, not the model), Decagon (explicit read/write API-permission split — write access is a separate, explicit grant), and Glean (pre-LLM ACL filtering, though its *agent* access policies are explicitly weaker than its *search* guarantee) all land on the same conclusion from different starting points: gate irreversible or sensitive actions with deterministic, non-model code, not model judgment. `sierra.md` names this explicitly as a cross-category pattern, extending it to Salesforce Agentforce as well (not covered as its own file here).

**Isolation is commoditized; egress is not.** E2B and Daytona both isolate compute (Firecracker microVMs vs. an unnamed technology, respectively) but differ sharply on how they control what a sandboxed agent can reach over the network — and `daytona.md` documents an explicit, category-wide egress-enforcement ladder observed across Fly, E2B, Daytona, Modal, Vercel Sandbox, and Anthropic's own sandboxing: (1) port/protocol only — not really an exfiltration control; (2) CIDR allowlists (Daytona) — survives DNS-rebinding tricks but unusable against CDN-fronted services; (3) SNI/Host allowlisting without TLS termination (E2B, Modal, Vercel default) — the practical industry default; (4) TLS-terminating inspection plus credential brokering (Vercel's advanced tier, Anthropic) — the only tier that can see and control what flows *through* an allowed connection, not just whether the connection is permitted. Even a correct allowlist only authorizes connections, not content — an allowlisted `github.com` still lets a gist become an exfiltration endpoint.

**Credential brokering is the answer to "how do you give an agent access without giving it the credential."** Decagon's short-lived, minimally-scoped JWTs discarded per session and Stytch's Connected Apps (covered in `../identity/stytch.md` — the app itself becomes the OAuth IdP so an agent gets a scoped, revocable token instead of a raw credential) are the same idea applied at different layers: keep the actual secret out of the agent's hands, hand it a narrow, expiring, revocable proxy instead.

**Eval/observability converges on one shape across both dedicated tools.** Braintrust and Langfuse both converge on: versioned datasets → code/LLM-judge/human scorers → OTel spans → offline + online eval → CI gating → review queues → trace-to-dataset loop. The difference is emphasis (Braintrust: per-stage scoring, CI-gated regression comments; Langfuse: instrumenting the judge itself), not architecture. Neither — nor anyone else publicly — has solved the underlying bootstrapping problem: online eval has no ground truth, so it gets pushed onto LLM-judges, which are themselves unvalidated models scoring other models.

## Worth stealing

- **The snapshot-cron pattern** (`ramp.md`) — a scheduled job pre-builds and snapshots the environment so session start is a restore, not a build, with an explicit bounded-staleness tradeoff (30 min).
- **Agent runs as the human's own token** (`ramp.md`) — the approval boundary becomes structural: the agent cannot merge/approve its own work.
- **Output lands in a medium with existing review culture** (`ramp.md`) — Inspect's output is a PR, not a new approval surface.
- **Authority declared in an existing product surface** (`ramp.md`) — Ramp Agents reuses the workflow builder rather than inventing a new "agent permissions" panel.
- **Graduated autonomy as a shipped ladder** (`ramp.md`) — suggestions → acting on subsets → full autonomy, not a philosophy.
- **Cite-your-sources** (`ramp.md`) — the Policy Agent links directly to the policy text its reasoning used.
- **Escalation falls back to the pre-agent human process** (`ramp.md`) — not a new escalation path, the one users already know.
- **Supervisors as a narrow, independently-evaluable check** (`sierra.md`) — a second model watching for specific failure modes, not a second opinion from the same model on the same question.
- **Tolerance tiers, topic-scoped** (`sierra.md`) — maximum adherence on adversarial topics, more flexibility on tone; an explicit, calibratable strictness policy rather than one global setting.
- **Filtering before generation, not after** (`glean.md`) — permissions resolved and content discarded before the model sees it, so a jailbreak can't recover access the retrieval layer never granted.
- **Short-lived, scoped JWTs discarded per session** (`decagon.md`) — minimal-privilege, minimal-lifetime agent-to-system credentials.
- **Inline, per-stage eval scoring** (`braintrust.md`) — score each stage of a multi-step pipeline independently, localizing failure instead of leaving one undifferentiated pass/fail on the whole run.
- **Instrumenting the judge, not just the judged** (`langfuse.md`) — a partial, practical answer to "who validates the LLM-judge": make its inputs/reasoning/score inspectable even without solving ground-truth validation.

## Worth avoiding

- **Sierra's reliability arithmetic doesn't hold up** — 90% agent accuracy × 90% supervisor catch rate → 99% combined assumes independent error events; two LLMs built and trained similarly plausibly share failure modes, and no published methodology addresses this (`sierra.md`).
- **Sierra's outcome-based billing has no documented independent audit** — the outcome metric is defined and scored by Sierra itself (`sierra.md`).
- **Glean's agent access policies are fail-open by design**, distinct from and weaker than its pre-LLM search-layer ACL filtering — don't assume the strong search-layer guarantee extends to autonomous agent behavior (`glean.md`).
- **Daytona's isolation technology is unnamed in official docs** — secondary sources claim container-based (Docker/OCI), unconfirmed by Daytona itself; treat "dedicated kernel" language with corresponding skepticism (`daytona.md`).
- **CIDR-only egress allowlisting (Daytona) is largely unusable against CDN-fronted services** — you can't allowlist "just api.github.com" by IP when the service sits behind a large, shifting CDN range (`daytona.md`).
- **Public writing about Ramp Inspect is contradictory** on whether it touches production data — only `builders.ramp.com` and `modal.com/blog` are treated as primary in that file; disregard SoftwareSeni, Bunnyshell, firecrawl, and similar secondary coverage.

## Gaps

- **Ramp Agents' permission model is not publicly documented** — whether the Policy Agent runs as a service principal with org-wide read or inherits an individual user's scope is unknown. This is a real gap, not an oversight in the research.
- **Nobody has solved judge validation.** Both eval platforms converge on LLM-as-judge for online eval because production traffic has no ground truth; neither has (nor does anyone publicly) a way to validate the judge itself.
- **Egress allowlisting stops at the connection layer.** Even the strongest common tier (SNI/Host allowlisting) authorizes a destination, not the content flowing to it — an allowlisted `github.com` gist or an allowlisted npm registry's `publish` are both live exfiltration paths through a "correct" allowlist. Only the rarest tier (TLS-terminating inspection + credential brokering) actually engages this.
- **Decagon has no public equivalent of Sierra's supervisor architecture, Glean's pre-LLM filtering, or Ramp's trust-model writeup** — its authorization model for identity verification, payment, and escalation actions is genuinely undocumented, not just under-researched here.

## Notes

- Several files (`e2b.md`, `daytona.md`, `braintrust.md`, `langfuse.md`) are intentionally thin by research-scope design, not under-covered relative to their real depth.
- Cold-start figures for both E2B (~150ms) and Daytona (sub-90ms, some sources claiming 27ms) are secondary/marketing only in both files — not confirmed against either vendor's own official documentation.
- Ramp's Inspect adoption figures (~30% of merged PRs, some accounts over half, within ~2 months) and Policy Agent escalation rate (10–15%) are vendor-reported.
