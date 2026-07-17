# Bolt.new

**What it is:** StackBlitz's prompt-to-app builder. The distinguishing bet: code execution happens **entirely inside the browser**, not on a remote VM.
**Axis:** app-builder, deploy.
**Depth:** medium — architecture is well-documented by StackBlitz/PostHog; token-cost and diff claims are secondary-sourced.

## Products & surfaces

- **Bolt.new** — chat-to-app, runs the generated project live in-browser via WebContainer, npm install, dev server, deploy.
- **WebContainer** (`@webcontainer/api`) — the underlying StackBlitz technology, licensable separately from Bolt itself.

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| WebContainer: WASM-based OS running Node.js in-browser | "100% of code execution occurs in the browser security sandbox," not a remote VM | maybe — see cost below |
| Filesystem as a single `SharedArrayBuffer` | Rust-compiled-to-WASM filesystem module loaded once; every Web Worker treats it as "the disk" | yes, mechanism |
| Atomics API for FS access | Provides atomic writes and file locks for safe concurrent access across workers | yes |
| CDN-cached npm installs | Popular packages pre-compressed in CDN layers, browser-cached after first hit — installs often complete in <500ms or are skipped entirely | yes |
| Model controls terminal + browser console | The agent can run shell commands and read console output as part of its loop | yes |
| Diffs (off by default) | Sends only the changed portion of a file instead of a full rewrite | no — the default is wrong, not the feature |

`Steal?` is a first-pass signal only, not a decision.

## Worth stealing

- **In-browser execution as a distribution mechanism**: zero backend provisioning per session, the "VM" is the user's own browser tab. That's a real cost model advantage over spinning a remote sandbox per session (contrast E2B/Daytona/Vercel Sandbox, all of which provision a remote microVM or container per run).
- **The `SharedArrayBuffer` + Atomics filesystem design** is a clean, generalizable pattern for "many workers, one consistent virtual disk, no server round-trip" — worth understanding even outside a browser-sandbox context.
- **CDN-layer pre-compression of popular npm packages** turns install time into a cache hit instead of a network fetch for the common case.

## Worth avoiding

- **The cost of in-browser execution is capability, and it's a hard ceiling, not a rough edge.** No native addons unless they compile to WebAssembly — `sharp`, `bcrypt`, and most native Postgres/MySQL drivers simply won't load. Python support is real but **pure-Python only, with no pip** — the entire native/compiled-extension Python AI ecosystem (numpy compiled wheels, etc.) is out. No Docker. No local Postgres. If your app's dependency graph touches anything native, the in-browser bet fails silently or loudly depending on the package.
- **Diffs are off by default**, and full-file rewrites on every edit reportedly cost roughly **3x the tokens** of a diff-based tool for equivalent changes — one benchmark cited a CSS color fix at ~15,000 tokens on Bolt versus ~5,000 on Cursor via fast diffs. The feature that fixes this exists but is opt-in and, per user reports, easy to miss — a default that costs real money before most users discover the toggle.

## Facts & figures

- WebContainer requires `SharedArrayBuffer`, which requires specific cross-origin isolation headers — a real deployment constraint for anyone embedding it.
- Python support added to WebContainers per StackBlitz's own announcement (native, no pip).
- Diffs ~3x token multiplier and the ~15,000 vs ~5,000 token CSS-fix figure are **secondary-sourced** (reviewer benchmarks), not from StackBlitz/Bolt's own documentation.

## Sources

- [github.com/stackblitz/bolt.new](https://github.com/stackblitz/bolt.new)
- [PostHog — From $0 to $40M ARR: Inside the tech that powers Bolt.new](https://posthog.com/newsletter/inside-bolt-dot-new)
- [npmjs.com/package/@webcontainer/api](https://www.npmjs.com/package/@webcontainer/api)
- [StackBlitz on X — Python running natively in WebContainers](https://x.com/stackblitz/status/1709960017825473014)
- **Unverified / secondary:** token-multiplier and CSS-fix benchmark figures (reviewer blog comparisons, not StackBlitz-published).
