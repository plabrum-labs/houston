# SAP

**What it is:** The ERP incumbent's answer to "how do you let customers extend a monolith without forking it" — relevant to Houston only for the extensibility taxonomy, not for ERP-specific process content.
**Axis:** deploy/migration, app-builder.
**Depth:** thin — SHORT by design, only the clean-core extensibility mechanism is in scope.

## Products & surfaces

| Product | What it is |
|---|---|
| **S/4HANA Cloud** | The core ERP product SAP wants kept unmodified ("clean core") |
| **Key User Extensibility** | In-app, low/no-code extension tooling exposed inside Fiori, for business users |
| **Developer (in-app) Extensibility** | On-stack ABAP extensions using released, versioned APIs only |
| **SAP BTP (Business Technology Platform)** | Separate cloud platform for "side-by-side" extensions that call the core via API rather than living inside it |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| "Clean core" as an explicit strategy | Keep the core product unmodified; push all customization outward | yes (as framing) |
| Three extension types (key-user / developer in-app / side-by-side) | Extension surface is tiered by who builds it and how coupled it is to the core | yes |
| Extensibility levels A–D | Classifies custom code by upgrade-safety and API compliance, not by feature | maybe |

## Worth stealing

**Clean core** is SAP's framing for a problem every extensible platform eventually hits: customer-written customizations inside the core product make every future vendor upgrade a merge conflict. The strategy is to make "don't modify the core" the default path by giving customers three explicitly different extension surfaces, ordered by how coupled they are to the vendor's release cycle:

1. **Key user extensibility (Type 1)** — low/no-code tools exposed directly in the product UI (Fiori) for business users; the SAP-blessed no-code layer, sanctioned and forward-compatible by construction because it's a defined, versioned tool surface, not arbitrary code.
2. **Developer / in-app extensibility (Type 2)** — code-level ABAP extensions, but constrained to **released APIs only** ("in-app" = still on-stack, but walled off from arbitrary core object access).
3. **Side-by-side extensibility (Type 3)** — extensions built and run entirely on a **separate platform (BTP)**, integrating with the core purely over API. Nothing about the extension lives inside the core codebase at all; an upgrade to the core cannot break it by construction, only a breaking API change can.

The **extensibility levels (A–D)** are a scoring rubric layered on top, classifying any given custom development by upgrade-safety and API-compliance rather than by what the code does — a governance lens ("how risky is this to our next upgrade") independent of the functional lens ("what does this do").

The mechanism worth extracting for Houston: **make the safest extension mechanism (no-code, in-app) the path of least resistance, and make the riskiest mechanism (code with core access) require deliberately opting out to a separate, isolated surface** — rather than one undifferentiated "customization" bucket.

## Worth avoiding

Not enough independently-verified detail in this research pass to assert specific SAP failure modes beyond the well-known industry narrative that **S/4HANA migrations from heavily-customized on-prem ECC systems are notoriously expensive and slow precisely because customizations lived inside the core** — which is the entire reason "clean core" now exists as a named strategy. Vendor-reported: 50% of SAP customers "actively use BTP services" as of the 2026 reporting cycle, up 10 points year over year — read as evidence the clean-core push is landing, not as an independently audited figure.

## Facts & figures

- Three canonical extension types: key user (Type 1), developer in-app (Type 2), side-by-side on BTP (Type 3).
- Extensibility governance levels: A–D, by upgrade-safety/API-compliance.
- Vendor-reported: ~50% of SAP customers actively using BTP services (2026), +10pp YoY; ~26% more "beginning their journey."

## Sources

- [SAP News Center — How to Extend SAP S/4HANA Cloud the Right Way](https://news.sap.com/2025/08/extend-sap-s4hana-cloud-right-way-clean-clear/)
- [SAP Community — ABAP Extensibility Guide: Clean Core for SAP S/4HANA Cloud](https://community.sap.com/t5/technology-blog-posts-by-sap/abap-extensibility-guide-clean-core-for-sap-s-4hana-cloud-august-2025/ba-p/14175399)
- [SAP Community — Clean Core Extensibility: Balancing Standardization and Differentiation](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/clean-core-extensibility-balancing-standardization-and-differentiation/ba-p/14260149)
- [SAVIC Technologies — SAP Clean Core Strategy 2026](https://www.savictech.com/insights/sap-clean-core-strategy-2026/) · [erpimplementation.eu — SAP Clean Core 2026: BTP Extensions, Levels A-D](https://www.erpimplementation.eu/en/sap-clean-core-strategy-btp-extensions-s4hana-2026/)
- **Not directly verified:** the 50%/26% BTP adoption figures are third-party-reported (SAVIC), not sourced to a primary SAP investor/analyst disclosure in this pass.
