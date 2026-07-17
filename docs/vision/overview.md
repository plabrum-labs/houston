# Houston

Houston is an app builder for running many small apps together on shared, lightweight infrastructure.

## The apps come first

Houston exists because building a small app involves a tedious amount of boilerplate and setup before it does anything interesting. Houston removes that: you build an app and deploy it, and the platform handles everything every app needs in common.

Houston is where a portfolio of small apps lives together. subway-status, marlin, arive, and pear are the first apps to run on it — each a standalone project today, each ported over and deployed on Houston.

## Who builds on it

Houston starts with my own apps, but it isn't only for me. The same ease that lets me port and deploy an app should let friends build and deploy their own apps on Houston just as easily. It's meant to be shared — a place where a handful of builders each run their projects on the same infrastructure.

## From idea to published app

Building on Houston should feel effortless:

- **Each app is its own repository** — self-contained, nothing shared to coordinate.
- **Push to main deploys it.** No manual deploy step and no infrastructure to manage; merging to main publishes the app.
- **The app declares what it needs from Houston in one small config file** it owns and checks in.
- **A Houston skill (or plugin / MCP)** lets anyone with a local Claude go from idea to a published app in a single session — scaffold, build, and ship without leaving the conversation.

That last point is the promise in one line: **idea to published app, in one session**, on shared infrastructure you never have to think about.

## The abstraction repository

Building app after app surfaces the same handful of solid abstractions worth reusing. Houston carries them in a central repository, native to its Go stack, that each app imports from — taking only what it needs. It's shadcn for the backend: not a framework you're locked into, but a set of well-made pieces you pull in.

snacks is the reference for this repository — the set of abstractions already proven across the existing apps. Houston's version is its own, rebuilt in Go for the platform.

Houston's value grows with the depth of this repository. The more good abstractions it holds, the less any individual app has to build.

## Shared, lightweight infrastructure

These apps have almost no traffic. Giving each its own dedicated compute — a box apiece, spread across providers — is the wrong shape for that. Houston runs them together instead:

- **One shared Postgres database** behind all of them.
- **A lightweight compute layer** with serverless-style economics — scaling toward zero when idle, no standing cost per app — while staying warm enough that requests never wait on a cold boot, and able to hold persistent connections.

The whole portfolio runs at a fraction of the cost and operational overhead of running each app on its own infrastructure.

## Where it goes: from app builder to operational machine

A deep enough repository of abstractions turns Houston from a convenient app builder into an enterprise-grade operational machine. Two abstractions carry most of that promise:

- **Semantic object layer** — cleans and transforms data into fully live operational objects, in a way nothing available does today. These live objects become the substrate other parts of Houston build on.
- **Ledger** — a diffing ledger. Its power comes from how it interacts with the semantic objects above.

The two are coupled: the ledger's value is unlocked by the live objects the semantic layer produces.

These sit a few levels beyond the near-term goal — porting the apps and getting the shared infrastructure right — but they're where the platform is headed, and the reason a deep abstraction repository is worth investing in.

## The pitch, in one line

Kill the boilerplate for building a small app, run a whole portfolio of them together on shared near-free infrastructure, and grow a repository of abstractions deep enough that the same platform can run serious operational systems.
