# Citizen developer

**What this category is:** the spreadsheet/database-native end of the builder spectrum — Airtable, Notion, Smartsheet. Tools built for non-engineers that nonetheless had to solve real schema, permission, and typed-layout problems.
**Why it's in this research:** semantic layer (field-type systems, typed layout roles), app-builder (override points), enterprise governance (permissions, audit).
**Files:** 3.

## The players

| Company | What it is | Depth |
|---|---|---|
| [airtable](airtable.md) | The gold standard for semantic field types and typed layout roles in this survey; field model and Interface Designer verified directly against Airtable's own schema, not just docs | deep |
| [smartsheet](smartsheet.md) | Fortune-500-scale spreadsheet-native tool; deliberately thin constraint system, but two genuinely differentiated mechanisms (Update Requests, Sheet Summary) and a full working anti-pattern (Control Center) | deep |
| [notion](notion.md) | Docs/database hybrid; independently converges with Airtable on typed layout roles, but makes a documented, opposite tradeoff on numeric field typing | medium |

Airtable is the reference implementation for this category — its field model and layout-role schema were verified against live API/MCP schema fetches, not just prose docs. Notion and Smartsheet are each valuable for a specific, narrower finding rather than as all-around reference points.

## Convergence

**Typed layout roles as the primitive for a database-backed UI — Airtable and Notion arrived here independently.** Airtable's Interface Designer `recordReview` element requires named, typed field roles (`titleFieldId`, `subtitleFieldId`, `thumbnailFieldId`, `recordColorFieldId`, `detailFieldIds`), each with its own type-eligibility rule enforced by the schema itself — a builder cannot put an attachment field in the title slot. Notion's views API requires different mandatory, typed configuration per view type (`board` requires `group_by`; `calendar` requires `date_property_id`; `timeline` requires both `date_property_id` and `end_date_property_id`). Two products, built independently, landed on "a layout/view is a named set of typed field roles, enforced at the schema level" as the right primitive. Two independent instances of the same convergence is stronger evidence than either alone — see `airtable.md` and `notion.md` for the verified schema detail.

**Airtable's retreat from a free-form drag-and-drop canvas to fixed typed layouts is the headline finding of this category.** Interface Designer used to support open drag-and-drop element placement; that capability is now legacy, and only "Blank" layouts still support it. Current guidance steers builders toward the typed, table-bound layout vocabulary (record review, grid, kanban, calendar, gallery, timeline, list, charts). This is a specific, falsifiable lesson from a company that shipped the flexible option first and walked it back: **an open canvas is easy to ship and hard to keep coherent; a fixed set of typed layout roles is more constrained to build but composes and validates far better** (`airtable.md`). Notion never had the open-canvas phase to walk back from — it went straight to typed views — which reads as independent confirmation of the same lesson rather than a counter-example.

**Semantic field types over one storage type is the core Airtable finding, and Notion's numeric model is the documented counter-case.** Airtable exposes 8+ distinct field types that all store a JSON number (`number`, `currency`, `percent`, `duration`, `rating`, `count`, `autoNumber`, numeric `formula`) — each with its own render/validation contract that can't be inferred from the stored value alone. Notion instead collapses all of these into one `type: "number"` property with a `format` string enum — simpler to implement, but `format` is a display hint on one underlying type, not a semantic type with its own bounds (no analog to Airtable's `rating.max` or `duration.durationFormat` parsing). Both are documented, deliberate design choices, not oversights — a genuine data point that this convergence has a real, defensible dissent.

## Worth stealing

- **Airtable's semantic field-type system** — `Money ≠ Float`, each numeric-shaped field type (`currency`, `duration`, `rating`, etc.) carries its own render/validation contract in the schema — see `airtable.md`.
- **`singleSelect.choices[].id` stable across renames** — filters/automations reference the immutable id, not the display string, so renaming a choice never breaks a downstream consumer — `airtable.md`.
- **Derived fields carry a full nested `result` field descriptor** — a rollup or formula's computed result is itself a complete field-type descriptor, so any downstream consumer treats it exactly like a stored field — `airtable.md`.
- **`recordScopeFilters` vs. interactive filters as two mechanisms that look identical but aren't** — builder-set scope filters mean excluded records are never sent to the client at all; end-user filters operate only within that already-locked scope. A real security boundary vs. a UX convenience — `airtable.md`.
- **Notion's two-level status property** (options nested inside named groups; views can group by either level) — solves "12 values that really mean 3 phases" without a duplicated derived field — `notion.md`.
- **Smartsheet's Update Requests** — an emailed, editable, column-scoped, single-row form sendable to any email address with no sheet share required. The one mechanism in this survey that lets a non-collaborator edit one row without onboarding them as a user — `smartsheet.md`.
- **Smartsheet's Sheet Summary** — typed scalar attributes *about* the sheet, rendered separately from the row grid, rather than forced into a synthetic header row — `smartsheet.md`.
- **Symbols columns (Smartsheet)** — the render hint lives entirely in the column config; the cell value stays a plain string/boolean, so filters/formulas/API need zero special-casing — `smartsheet.md`.
- **The "derived-value changes don't participate in the trigger graph" boundary**, independently drawn by both Salesforce (roll-up recalculation doesn't fire workflow) and Smartsheet (cross-sheet formulas/links don't trigger automations) — a strong convergent signal, cross-referenced in `smartsheet.md` and `enterprise-platforms/salesforce.md`.

## Worth avoiding

- **Smartsheet Control Center is a full, working anti-pattern worth reading end to end.** No schema — "changing the schema" means writing a robot that edits up to 20,000 independent template copies. Profile data is encoded via row indentation and a magic-string match on the Primary column ("Summary"), not any typed structure. Global Updates (the only way to propagate a change) is not undoable in its legacy form, and even Enhanced Global Updates has no rollback, only a forward-only publish plus a manual audit trail. The generalizable warning: **when "provisioned instances" are truly independent copies rather than instances of a shared schema, every later schema change becomes a distributed, rate-limited, individually-fallible batch operation across thousands of artifacts** — and that fact is invisible until the fleet is large enough for the batch job's wall-clock time to matter (`smartsheet.md`).
- **"Hidden ≠ secure" is a real, documented Airtable failure mode, not hypothetical** — Airtable had to ship a policy change specifically because interface-only collaborators were exposed to data through a combination of individually-safe-looking features (`airtable.md`).
- **Smartsheet's additive-only sharing model** — workspace and item permissions apply simultaneously and the higher of the two always wins; there is no way to grant broad workspace access while pulling one sensitive sheet's access back down. A real architectural ceiling, not a misconfiguration — `smartsheet.md`.
- **Notion's formula-engine/API type mismatch** — the formula engine internally supports 7 data types (including `person` and `page`), but the public API's formula result type is capped at 4 (`boolean`, `date`, `number`, `string`). A formula computing a person or page inside the product never survives as a typed value through the API — a caution that internal type richness is only as useful as the narrowest interface downstream consumers actually read through — `notion.md`.

## Gaps

- **Smartsheet's own constraint system is deliberately, radically minimal** — `Column.validation` is literally a boolean (picklist-restricted or not), with no regex, numeric range, uniqueness, or cross-field conditional rule anywhere in the column model. Whether that's the right bet for a spreadsheet-shaped product at Fortune-500 scale is left as an open question by this research, not resolved — `smartsheet.md`.
- **None of the three has a Salesforce/ServiceNow-grade two-mechanism audit trail** — Smartsheet's activity log is the strongest of the three (it records reads, not just writes, and distinguishes human vs. system-principal events), but nothing here approaches the config-audit/data-audit split covered in `enterprise-platforms/README.md`.

## Notes

- Airtable's field-model claims are the most rigorously sourced in this category — verified directly against the live Web API field-model and an MCP `describe_page_element` schema fetch during this research pass, not just docs prose.
- The exact August-2025 policy-change date for Airtable's dynamic-filter field-exposure fix is inferred from community-forum discussion timing, not a dated changelog entry.
- Smartsheet's ~500-hour/~3-week Global Update propagation estimate for a 20,000-project blueprint is this research's own extrapolation from the documented 40-projects/hour provisioning throughput, not a directly published update-throughput figure.
- Notion's `number.format` currency-value count (~30+) is an approximate count from partial API-reference enumeration, not a verbatim complete list.
