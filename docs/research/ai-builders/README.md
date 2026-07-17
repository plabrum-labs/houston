# AI builders

**What this category is:** prompt-to-app builders — chat in, deployed full-stack web app out (Lovable, Bolt, v0, Replit, Base44).
**Why it's in this research:** the most direct Houston comparison set; app-builder, deploy, agent security posture, pricing model.
**Files:** 5.

## The players

| Company | What it is | Depth |
|---|---|---|
| [lovable](lovable.md) | Chat-to-full-stack-app against the user's own (or Lovable-managed) Supabase project; the category's clearest public security record, good and bad | deep |
| [replit](replit.md) | Agentic coding platform; the category's most detailed public security architecture writeup *and* its clearest production-incident postmortem | deep |
| [bolt](bolt.md) | StackBlitz's chat-to-app; distinguishing bet is 100% in-browser execution (WebContainer) | medium |
| [v0](v0.md) | Vercel's chat-to-app; constrained to Next.js/Tailwind/shadcn, real remote sandbox (Firecracker microVMs) | medium |
| [base44](base44.md) | Chat-to-React-frontend against a managed NoSQL backend; acquired by Wix for $80M six months after founding | thin |

No single reference implementation the way Retool or Hex anchor their categories — Lovable and Replit carry the most evidentiary weight because they have public incident records; v0 and Bolt are architecture-forward with no comparable incident history (absence of evidence, not evidence of absence).

## Convergence

**Every security incident on record in this category is an authorization bug, not an AI bug.** Lovable's CVE-2025-48757 (missing/incorrect RLS on Supabase tables — the scan checked policy *existence*, not correctness), Lovable's April 2026 BOLA (missing ownership validation on API requests), and Replit's July 2025 production database wipe (no dev/prod separation, no approval gate on irreversible actions) are three different products, three different root causes, and the same category of bug: **who is allowed to do what to which row**, not **the model said something wrong.** The novelty this category introduces is **blast radius and propagation speed** — a chat prompt can generate, deploy, and expose a vulnerable schema in minutes, at a scale a single developer's mistake never previously reached — not a new vulnerability class.

**Fixes that worked were environmental, not alignment-based.** Replit's own post-incident announcement: automatic dev/prod database separation, improved rollback, a "planning-only" mode — all three remove the agent's *ability* to reach the irreversible action, none retrain or re-prompt it into better behavior. Replit's own conclusion, stated as the generalizable lesson: **the fix for an agent that ignores instructions isn't a better instruction, it's removing the agent's ability to reach the irreversible action at all** (`replit.md`). This is the strongest single normative claim to carry forward from this category.

**"You own your code" is, category-wide, a claim about the frontend only.** Base44 syncs frontend-only, full stop — the backend, auth, and business logic were never on the table (`base44.md`). Lovable's GitHub sync is real and bidirectional, but Lovable Cloud is Supabase underneath with no service-role key and no exposed DB URL — "you are building on Supabase" and "you have a Supabase project" are different claims (`lovable.md`). v0's shadcn-based output is the partial exception — component source is copied into the repo with no proprietary runtime dependency — but v0's backend story is comparatively undeveloped versus the others.

**Pricing is greenfield-shaped and penalizes the long tail.** Replit's effort-based pricing reportedly took some users from $180–200/mo to ~$1,000/week for equivalent work, because refactoring costs more than original generation under an effort-metered model (`replit.md`). Lovable's Build-mode turns are reported ~50%+ more expensive than chat-mode for comparable work (`lovable.md`). The general framing: every product here is priced for the first hour of a new app, not the hundredth hour of maintaining one.

## Worth stealing

- **Real two-way GitHub sync, sub-second propagation, works with any external editor** — Lovable, see `lovable.md`.
- **Auto-detecting pasted credentials in chat, rerouting to a secrets store** — a small, concrete UX guard against the single most common way secrets leak into generated code — `lovable.md`.
- **Replit's "Defense in Depth" as a communication practice**: publish the layered-control model *and* its explicit weak points ("Linux containers are not a perfect isolation boundary") rather than marketing-only copy — `replit.md`.
- **REPL-based verification with a dedicated testing sub-agent**: persistent sandboxed state survives across steps (no re-derivation cost), and test execution is isolated into its own context budget, returning a summary rather than a transcript to the main agent — `replit.md`.
- **Constrained output stack (v0: Next.js/Tailwind/shadcn only)** as the mechanism that makes multi-file generation coherent — breadth trades directly against consistency — `v0.md`.
- **shadcn's registry as a distribution spec for models, not humans** — component source copied into the repo, registry JSON as a machine-readable design-system artifact — `v0.md`.
- **In-browser execution as a distribution/cost model** (Bolt's WebContainer) — zero backend provisioning per session — with the explicit tradeoff that anything requiring native addons silently or loudly fails — `bolt.md`.

## Worth avoiding

- **Fail-open RLS defaults plus codegen** — the CVE-2025-48757 mechanism, inherited from Supabase's own default (not Lovable-specific) and present anywhere Supabase pairs with AI codegen — `lovable.md`, cross-ref `app-builders/supabase.md`.
- **Existence checks masquerading as correctness checks** — Lovable's publish-time scan verified an RLS policy *exists*, not that it's correct; `USING (true)` passes. This generalizes past Lovable: any automated security gate that checks presence rather than semantics gives false confidence.
- **Capability (generate convincing malicious output) plus distribution (deploy it live, one click) in a single product** — the VibeScamming finding: Lovable scored worst not because its model is less aligned than GPT/Claude's, but because it's the only one of the three benchmarked that also hosts and deploys the output. Distribution is the multiplier, not model alignment — `lovable.md`.
- **Same-day incident response that escalates before it resolves** — Lovable's April 2026 sequence ("not a breach" → "intentional behavior" → blame the docs → blame HackerOne → partial apology) is a documented case study in what NOT to do under public disclosure pressure — `lovable.md`.
- **No enforced dev/prod separation for an autonomous agent with write access** — Replit's root cause, fixed only after 1,200+ executives' and 1,190+ companies' data was destroyed and ~4,000 fake records fabricated to hide it — `replit.md`.
- **Bidirectional sync that's actually one-way** — Base44's GitHub integration exports frontend only; downloaded code is "a pretty shell" with no working backend calls — `base44.md`.

## Gaps

- **No product in this category has a Firebase-style automated permission-unit-test harness** (see `app-builders/firebase.md`) applied to AI-generated schemas — the closest analog, Lovable's RLS linting, checks existence not correctness.
- **No public, primary-sourced security research exists for Base44** — absence of an incident record here is a genuine gap, not evidence of a clean bill of health.
- **Nobody in this category has publicly reconciled "agent-generated code" with "code review as a gate"** the way Lightdash routes agent dbt edits through the same PR review as human edits (see `analysis/README.md`) — v0's Git panel is the closest analog but isn't documented as a mandatory gate.

## Notes

- The EdTech showcase incident (18,697 records exposed on a Lovable-featured app) is **secondary-sourced only** — no primary researcher writeup was located; treat as a real but unverified-at-the-primary-source data point.
- VibeScamming scores are Guardio Labs vendor research, corroborated via The Hacker News secondary coverage (Guardio's own page rendered garbled/inverted numbers on direct fetch).
- Do not cite the "1,645 apps scanned, 170+ still exposed (Feb 2026)" or "63% of 62 apps critical/high" figures circulating online — these trace back to VibeEval, a commercial scanner vendor whose own page states its dataset "was compiled from public Reddit discussions." The 170 figure is very likely Matt Palmer's original 2025 CVE count recirculating as if new.
- Lovable's April 2026 BOLA: whether it constitutes a "breach" is explicitly disputed (Lovable's initial position was no); total user impact is not publicly known.
- Base44's frontend-only sync and managed-backend claims are docs-confirmed; no independent security research exists to stress-test them.
