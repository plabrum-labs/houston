# Celonis

**What it is:** The category-defining process mining company — reconstruct an "as-is" model of how a business process actually executes from raw system logs, then compare it against how the process is supposed to work.
**Axis:** analysis, enterprise.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Process mining / EMS (Execution Management System)** | Core platform: extract events, discover the actual process, check conformance, recommend fixes. |
| **Conformance Checker** | Compares a reference/modeled process against the discovered "as-is" process. |
| **Extraction/transformation packages** | Prebuilt connectors for SAP ECC, Oracle EBS, and other ERPs — turn source schemas into an event log. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| (Case ID, Activity, Timestamp) event log | The entire minimum input requirement for process mining | yes |
| Conformance checking | Diffs the modeled path against the observed path | yes |
| Prebuilt SAP/Oracle extraction packages | Turn hostile ERP schemas into a clean event log | yes (concept), no (build cost) |

## Worth stealing

### The event log is three columns, and that's the whole input contract

Process mining's entire input requirement, stated as plainly as it gets: *"a CSV file that contains at least these three columns: Case ID, Activity, and Timestamp."* **Case ID** — a unique reference to the business object moving through the process (an order, a claim, a ticket). **Activity** — which stage of the process this event represents. **Timestamp** — when the case reached that stage. Everything downstream (process discovery, conformance checking, bottleneck analysis, root-cause views) is derived purely from a table shaped this way, optionally enriched with extra context columns (vendor, priority, amount) that don't change the core mining algorithms but add slicing dimensions.

The reason this is worth stealing conceptually: it's a genuinely minimal, general-purpose schema for "what happened, to what, when" — any system that already emits or can be made to emit (case_id, activity, timestamp) tuples gets process-mining-style analysis for free, without a bespoke data model per process type.

### Conformance checking — "as defined" vs. "as is"

Conformance checking is the mechanism that turns a discovered process into an actionable finding: it *"relates and compares events in the event log to activities in the process model to find commonalities and discrepancies between modeled behavior and observed behavior,"* comparing an existing reference model (**as defined** — how the process is supposed to run) against the process reconstructed from real event data (**as is** — what actually happened). Concretely, Celonis's Conformance Checker reports the percentage of conforming vs. non-conforming cases against a reference model, surfacing skipped steps, out-of-order execution, and unusually slow stages directly, rather than requiring a human to notice them by eyeballing dashboards.

The generalizable idea: **once you have an event log, "as designed" vs. "as executed" becomes a computable diff**, not a manual audit. Any system that can log (case, activity, timestamp) for its own workflows gets this analysis essentially for free once the log exists — the value is entirely in having the log in the right shape, not in a bespoke conformance algorithm per process.

### The extraction problem, not the analysis problem, is where the engineering effort goes

The critical, load-bearing context for evaluating Celonis as a company: **most of the engineering effort goes into *reconstructing* usable event logs from hostile ERP schemas** (SAP ECC, Oracle EBS, and similar systems whose tables were never designed to answer "what happened to this case, in what order, when"), not into the mining/conformance algorithms themselves, which are comparatively well-understood and academically established. Their own materials note that *"an error in reconstructing the end-to-end process may cascade to a completely flawed process mining exercise"* — the extraction/transformation layer isn't a preprocessing footnote, it's the part that determines whether the whole analysis is trustworthy. Celonis ships prebuilt extraction/transformation packages specifically for SAP ECC and Oracle EBS as productized artifacts, which is a strong signal about where the actual product moat lives: not "we can detect conformance gaps" (a known technique) but "we can reliably turn *your specific, messy, decades-old ERP schema* into a correct event log."

**Read as a build-vs-buy signal**: a >$10B company (reported valuations ranged $11–16B across 2022–2026 sources) was built on process mining as a category — but the defensible, hard-to-replicate part of that business is the extraction engineering against real-world enterprise schemas, not the mining algorithm. Anyone evaluating "should we build process-mining-style analysis" should budget accordingly: the mining/conformance logic is the easy 20%, and getting a trustworthy (case_id, activity, timestamp) log out of the actual source systems is the hard 80%.

## Worth avoiding

No independently-verified negative findings surfaced in this pass — this file is medium-depth; a deeper investigation into Celonis's known implementation pain points (project timelines, extraction-package maintenance burden as ERPs get customized/upgraded, pricing model) would strengthen this section.

## Facts & figures

- Reported valuation: **$13B (Aug 2022, $1B raise led by Qatar Investment Authority)**; some 2026 sources cite figures as high as $16B — treat the exact current number as unverified/fluctuating (press-reported, not confirmed via a single authoritative 2026 source).
- Total funding raised: ~$1.77B (press-reported).
- Prebuilt extraction/transformation packages exist for SAP ECC and Oracle EBS specifically (vendor docs).

## Sources

- [How Does Process Mining Work?](https://www.celonis.com/insights/topics/how-does-process-mining-work)
- [How Process Mining Modernizes Process Discovery](https://www.celonis.com/blog/how-process-mining-modernizes-process-discovery) · [Conformance Checker docs](https://help.celonis.de/cpm46/en/conformance-checker)
- [Data extractions and transformations for object-centric process mining](https://docs.celonis.com/en/data-extractions-and-transformations-for-object-centric-process-mining.html) · [A Practitioner's View on Process Mining Adoption, Event Log Engineering and Data Challenges (Springer)](https://link.springer.com/chapter/10.1007/978-3-031-08848-3_7)
- [Celonis $13B valuation — TechCrunch](https://techcrunch.com/2022/10/16/with-a-13b-valuation-celonis-defies-current-startup-economics/) · [Celonis Wikipedia](https://en.wikipedia.org/wiki/Celonis)
- **Not directly verified:** current (2026) precise valuation figure — sources disagree between $11B and $16B; IPO status/timing was mentioned in secondary sources but not confirmed against a primary announcement.
