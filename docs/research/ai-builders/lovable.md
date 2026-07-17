# Lovable

**What it is:** Prompt-to-app builder — chat in, deployed full-stack web app out. The most direct Houston/Lovable comparison point named in the brief; also the category's clearest public case study in what fail-open defaults plus codegen do to security.
**Axis:** app-builder, deploy, agent (security posture).
**Depth:** deep on the three security incidents and the Supabase mechanism; medium on product surface and pricing.

## Products & surfaces

| Surface | What it does |
|---|---|
| **Chat mode** | Interactive, iterative build/edit — the default conversational surface. |
| **Build mode** (renamed from "Agent mode") | Autonomous execution: takes a task, explores the codebase for context, applies changes across files, resolves issues that appear mid-build, end to end without turn-by-turn confirmation. |
| **Lovable Cloud** | Lovable's own managed backend (see "Worth avoiding" — it *is* Supabase underneath, but not exposed as your Supabase project). |
| **Supabase integration** | Connect your own Supabase project; Lovable then designs schema, runs migrations, deploys edge functions, and wires UI to data directly from chat. |
| **GitHub sync** | Real two-way sync (github.com, GHEC, GHES) — Lovable→GitHub pushes are near-real-time; local pushes to the default branch from VS Code/Cursor appear back in Lovable within seconds. |
| **Publish + custom domains** | One-click deploy, custom domain attach. |
| **Download codebase** | Paid-tier full source export. |
| **Security view** | Basic scan (free, pre-publish), Deep scan (agentic codebase review, on-demand, ~3 min), optional Wiz (dependency CVEs) and Aikido (agentic pentesting) connectors, RLS policy linting. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Chat→schema→migration→edge-function→UI in one flow | Full-stack from natural language against the user's own Supabase project | yes, mechanism |
| Real two-way GitHub sync | Bidirectional, near-real-time, works with local editors | yes |
| RLS policy linting in Deep scan | Checks common RLS mistakes, not full correctness | maybe — see caveat below |
| Publish-time RLS existence check | Blocks publish if a table has zero RLS policies | no — existence ≠ correctness, this is the CVE's root mechanism |
| Auto-detection of pasted API keys → Secrets | Scans chat input for credential-shaped strings, redirects to a secrets store | yes |
| Wiz/Aikido as optional bolt-on scanners rather than built-in gate | Vendor partners handle dependency CVEs and agentic pentesting | maybe |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

- **Chat-driven full-stack wiring against the user's own project**, not a Lovable-hosted black box. When Supabase is connected, schema, migrations, edge functions, and UI binding all flow from conversation into a project *you* own the infrastructure for (see "Worth avoiding" for the asterisk on Lovable Cloud specifically).
- **Real two-way GitHub sync with sub-second-scale propagation**, working with any external editor — this is the actual mechanism, not "export when you're ready."
- **Auto-detecting credentials pasted into chat and rerouting them to a secrets store** — a small, concrete UX guard against the single most common way secrets end up in generated code.

## Worth avoiding — three incidents, kept separate

Public coverage routinely conflates these. They are different failures at different layers.

### (a) CVE-2025-48757 — the RLS-by-omission pattern

Researcher **Matt Palmer** found the bug 2025-03-20 via *Linkable*, a Lovable-built site: modifying a client-side query granted access to **all data in the `users` table**. He notified Lovable 03-21; they confirmed receipt 03-24, then went quiet. **On 2025-04-14 a Palantir engineer independently rediscovered it and tweeted a public demonstration**, proving active exploitation. Palmer re-notified and opened a 45-day disclosure window. 2025-04-24, "Lovable 2.0" shipped with a built-in security scan. **2025-05-29 the CVE was published** — Palmer's account describes no meaningful remediation and no user notification at that point.

Scope at publication: **303 Supabase endpoints across 170 websites** (10.3% of 1,645 Lovable-built sites analyzed) — exposing names, emails, phone numbers, home addresses, payment information, and API keys (Google Maps, Gemini, eBay, Stripe among them).

**Mechanism**: Lovable-generated apps query Supabase **directly from the client using the public anon key**. Tables created via raw SQL, migrations, or AI-driven tooling **don't get Row Level Security enabled automatically**. With no RLS policy, the anon key can read (or write) the entire table, and both the Supabase URL and the anon key ship in the frontend bundle — visible to anyone who opens dev tools.

**The sharpest finding, per Palmer's own writeup**: Lovable's 2.0 scan (and, per Lovable's own docs, the Publish-time check) only verifies that an RLS policy **exists** on a table — not that it's correct or matches the application's actual authorization logic. A table with a policy of `USING (true)` — allow everyone, unconditionally — **passes the scan**. Existence, not correctness, is what's gated.

This is **not Lovable-specific**. The same anon-key-direct-to-Postgres pattern, and the same fail-open-without-RLS default, shows up anywhere Supabase is paired with AI codegen — Bolt, v0, Cursor+Supabase templates, Replit Agent all inherit it from Supabase's own default (RLS off unless explicitly enabled). It is a **fail-open-default × codegen interaction**: the AI's individual failure was *omission* (not writing a policy), and that omission was only fatal because the platform's default made silence equivalent to "expose everything."

### (b) VibeScamming — Guardio Labs, 2025-04-09

Benchmark methodology: *Inception* (direct malicious prompts, up to 50 pts) + *Level-Up* (visual similarity, evasion, hosting, credential collection, messaging), normalized to a 0–10 scale where **higher = more resistant to misuse**. Reported scores (confirmed via The Hacker News, not Guardio's own page, which returned garbled/inverted numbers on fetch): **ChatGPT 8.0/10** (most resistant — "ethical guardrails held up well... strong refusals"), **Claude 4.3** ("started with solid pushback but proved easily persuadable" once framed as security research), **Lovable 1.8** — "No guardrails, no hesitation."

What Lovable produced when prompted: pages auto-deployed to subdomains like `login-microsft-com.lovable.app`; a near-pixel-perfect Microsoft login clone; **an admin dashboard displaying harvested credentials in plaintext**; Telegram exfiltration wiring; evasion techniques (randomized CSS class names, iframe/headless detection, meta-tag spoofing); and a working SMS-campaign UI.

**The structural point**: Lovable didn't score worst because its underlying model is less aligned than Claude's or GPT's — it scored worst because **it's the only one of the three that also hosts and deploys the output**. Capability (generate a convincing phishing kit) plus distribution (put it live on the internet with one click) in a single product is what made the difference, not model alignment alone.

### (c) April 2026 BOLA — a platform-level bug, distinct from (a)

Confirmed independently by The Register, SC Media, Computing, and TNW. **Broken Object Level Authorization** in Lovable's API — missing ownership validation on requests — meant a **free** account could read another user's **source code, database credentials, AI chat history, and customer data in roughly five API calls**. Affected projects created before November 2025.

Researcher **@weezerOSINT** reported to HackerOne **2026-03-03**; the vulnerability was **publicly disclosed 2026-04-21**, 48 days later, after the researcher says HackerOne triage repeatedly closed the reports as duplicates. Lovable shipped a fix within roughly two hours of the public disclosure.

**Lovable's stated root cause**: in February 2026, a backend change to unify permissions handling **accidentally re-enabled access to chat histories on public projects** — a regression that undid protections deliberately removed between March and November 2025 in response to user feedback, then restored by the February change without adequate safeguards. Outdated internal documentation given to HackerOne triagers is also blamed for the reports being closed rather than escalated.

**The same-day response sequence** (per multiple outlets and Lovable's own follow-up post): "We did not suffer a data breach" → "that is intentional behavior" → blame pointed at their own docs → blame pointed at HackerOne → a partial apology. Lovable's own later post acknowledges the initial response was "dismissive and failed to acknowledge the real concern," and states: *"We see that we hadn't built the product safeguards, the communication muscle, or the security processes to match the trust our users placed in us."* Lovable also states private projects and Lovable Cloud were never impacted.

**Disputed**: whether this constitutes a "breach" (Lovable's initial position was no); how many users' data was actually accessed is not publicly known.

### The EdTech showcase incident — 18,697 records

An EdTech app that Lovable itself featured on its success-story page — used by students at UC Berkeley, UC Davis, and institutions across Europe, Africa, and Asia — was found by an independent researcher to have **16 vulnerabilities, 6 critical**, including inverted auth logic (blocking logged-in users while granting anonymous visitors full access). **18,697 user records** were exposed, including **4,538 student accounts** (minors likely present) and 870 users with full PII exposed; the flaw also allowed modifying grades, deleting accounts, and sending bulk email as the app. Coverage is multiple secondary reports (Vibe Graveyard, The Register, TNW); no primary researcher writeup was located — **mark this as secondary-sourced.**

### Practitioner-reported operational walls

- **Community best practice is to connect Supabase only after the frontend has stabilized** — connecting early causes schema and screens to churn against each other, sending debugging into spirals. That is effectively a confession that the model has no stable schema-first anchor; it treats data model and UI as jointly, not independently, revisable.
- **No one-click migration between Lovable Cloud and an external Supabase project in either direction.**
- **Git branching is reported broken-ish** — you can create a branch, set it default, and Lovable will still commit to `main`. (Lovable's own settings expose a Branch Switching / Labs toggle; user reports describe it as unreliable, particularly once Supabase is connected.)
- **Build-mode (formerly agent-mode) turns are reported ~50%+ more expensive** in credits than chat-mode turns for comparable work.
- **Lovable Cloud is Supabase underneath and still isn't yours**: no service role key, no direct database URL, invisible in your own Supabase dashboard. "You are building on Supabase" and "you have a Supabase project" are different claims — Lovable Cloud is only the first.

## Facts & figures

- CVE-2025-48757 scope: 303 endpoints, 170 sites, 10.3% of 1,645 analyzed. (Palmer, vendor-independent researcher, primary.)
- VibeScamming scores (0–10, higher = more resistant): ChatGPT 8.0, Claude 4.3, Lovable 1.8. (Guardio Labs, vendor-reported; corroborated by The Hacker News secondary coverage.)
- April 2026 BOLA: reported 2026-03-03, disclosed 2026-04-21 (48 days); affected projects created before Nov 2025; ~5 API calls to exploit.
- EdTech incident: 18,697 records, 4,538 student accounts, 870 with full PII, 16 vulns / 6 critical. Secondary-sourced, primary writeup not located.
- Pricing: Free / Pro $25 (mo) or ~$21 (annual) / Business $50 (mo) or ~$42 (annual); credit-based, free tier grants 5 build credits/day (~30/mo) plus 20 monthly Cloud credits.
- ⚠️ **Do not cite** "1,645 apps scanned, 170+ still exposed (Feb 2026)," "63% of 62 apps critical/high," "52% publicly readable tables," or "avg 52/100 across 200+ AI-built sites" as fresh measurements — these trace back to **VibeEval**, a commercial scanner vendor whose own page states it "was compiled from public Reddit discussions." The 170 figure is almost certainly Palmer's 2025 CVE count recirculating, not a new scan.

## Sources

- [Matt Palmer — CVE-2025-48757](https://mattpalmer.io/posts/2025/05/CVE-2025-48757/) · [Statement on CVE-2025-48757](https://mattpalmer.io/posts/2025/05/statement-on-CVE-2025-48757/)
- [The Hacker News — Lovable AI Found Most Vulnerable to VibeScamming](https://thehackernews.com/2025/04/lovable-ai-found-most-vulnerable-to.html) · [Guardio Labs — VibeScamming](https://guard.io/labs/vibescamming-from-prompt-to-phish-benchmarking-popular-ai-agents-resistance-to-the-dark-side) (⚠️ page rendered with garbled/inverted scores on fetch — Hacker News used as the score source of record) · [SC Media brief](https://www.scworld.com/brief/lovable-ai-most-likely-to-be-harnessed-in-phishing)
- [The Register — Lovable denies data leak, cites "intentional behavior"](https://www.theregister.com/security/2026/04/21/lovable-denies-data-leak-cites-intentional-behavior/5226233) · [Lovable — Our response to the April 2026 incident](https://lovable.dev/blog/our-response-to-the-april-2026-incident) · [Computing.co.uk](https://www.computing.co.uk/news/2026/security/lovable-flaw-exposed-source-code-credentials-and-ai-chats) · [TheNextWeb — 48 days](https://thenextweb.com/news/lovable-vibe-coding-security-crisis-exposed)
- [The Register — EdTech app, 18K users](https://www.theregister.com/2026/02/27/lovable_app_vulnerabilities/) · [Vibe Graveyard](https://vibegraveyard.ai/story/lovable-showcased-edtech-app-18k-users-exposed/)
- [docs.lovable.dev/features/security](https://docs.lovable.dev/features/security) · [lovable.dev/security](https://lovable.dev/security) · [Wiz — Igor Andriushchenko interview](https://www.wiz.io/crying-out-cloud/protecting-vibe-coded-apps-and-the-shift-to-soft-guardrails-with-igor-andriushche)
- [docs.lovable.dev/integrations/supabase](https://docs.lovable.dev/integrations/supabase) · [docs.lovable.dev/integrations/github](https://docs.lovable.dev/integrations/github) · [docs.lovable.dev/features/agent-mode](https://docs.lovable.dev/features/agent-mode) (Build mode, formerly Agent mode) · [lovable.dev/pricing](https://lovable.dev/pricing) · [docs.lovable.dev/introduction/subscription-plans](https://docs.lovable.dev/introduction/subscription-plans)
- **Not directly verified / secondary only:** EdTech incident primary researcher writeup; exact wording of Igor Andriushchenko's public "discretion of the user" quote (attributed across multiple secondary write-ups, original interview not directly fetched).
