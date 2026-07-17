# Base44

**What it is:** Prompt-to-app builder acquired by Wix for $80M six months after founding (8 employees at acquisition). The cleanest example in the category of "you own your code" meaning only the frontend.
**Axis:** app-builder, deploy.
**Depth:** thin — product surface confirmed via docs, no independent security research located.

## Products & surfaces

- **Base44** — chat-to-app; generates a React + Vite + Tailwind + shadcn/ui frontend against a managed, MongoDB-compatible NoSQL backend with Deno serverless functions, auth, and file storage.
- **GitHub integration** — exports frontend code to a GitHub repo (Builder+ plans).
- **CLI** — create projects from templates, sync local code with the Base44 backend, deploy to Base44 hosting.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| GitHub sync | Real export, but **frontend only** | no — the asymmetry is the finding, not the feature |
| Managed NoSQL backend | MongoDB-compatible, entities/auth/storage/functions bundled | maybe |
| CLI-based local sync | Local dev against the same backend via CLI | maybe |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

Nothing distinctive beyond what's already covered under Lovable/v0/Bolt — Base44's product surface is a narrower version of the same category pattern (chat → React frontend → managed backend).

## Worth avoiding

**GitHub sync exists, but only the frontend syncs.** Database, auth, business logic, and integrations all stay behind Base44's SDK — never exported. Download the code and, per third-party review coverage, you get *"a pretty shell where screens load, but every button that does something real returns nothing."* The connection between the exported frontend and the live backend is **one-way and permanent**: the frontend can call the backend, but the backend was never yours to take with you.

This makes Base44 the sharpest instance of a category-wide claim: **"you own your code" is, across this entire category, a claim about the frontend.** Lovable's GitHub sync is real and bidirectional but the backend can still be Lovable Cloud (Supabase underneath, no service-role key, no DB URL exposed — see `lovable.md`). Base44 doesn't even offer that ambiguity — the backend was never on the table.

## Facts & figures

- Acquired by Wix for **$80M cash**, ~6 months after founding, 8 employees at acquisition time (June 2025).
- Frontend export requires Builder+ paid tier.

## Sources

- [Base44 — GitHub integration](https://base44.com/blog/base44-github-integration) · [docs.base44.com — GitHub Integration](https://docs.base44.com/developers/app-code/local-development/github)
- [github.com/base44/cli](https://github.com/base44/cli)
- [Lovable — Base44 vs Lovable comparison](https://lovable.dev/guides/base44-vs-lovable) (competitor-published, read with that bias in mind)
- **Gap:** no independent security research on Base44 was located during this pass — unlike Lovable, there is no public incident record to report, positive or negative.
