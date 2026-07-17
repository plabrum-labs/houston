# Airtable

**What it is:** The citizen-developer end of the spectrum — its field-type system and typed-layout-role model are the gold standard for "the schema carries enough semantic and render metadata that every downstream consumer (formula, UI, API) treats a derived value exactly like a stored one."
**Axis:** semantic layer, app-builder.
**Depth:** deep — field model and Interface Designer verified directly against Airtable's own MCP schema definitions, not just docs.

## Products & surfaces

| Product | What it is |
|---|---|
| **Base / Table / Field** | The core relational-with-attachments data model |
| **Views** | Personal/collaborative/locked saved filters+sorts+layouts over a table |
| **Interface Designer** | A typed, layout-role-based app builder distinct from the raw table grid |
| **Sync** | Read-only (or limited two-way) mirrored tables from another base or external source |
| **Omni** | Airtable's AI agent surface, including ad hoc "web tables" for research/CRM workflows |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| 8+ field types that are all "a number" | `number`/`currency`/`percent`/`duration`/`rating`/`count`/`autoNumber`/numeric `formula` are semantic types, not one storage type | yes |
| Render metadata lives in the field schema | `currency{precision,symbol}`, `date{dateFormat}`, `dateTime{timeZone,timeFormat}`, `rating{max,icon,color}` | yes |
| `singleSelect.choices[].id` stable across renames | Renaming a choice's display name doesn't break filters/automations keyed on it | yes |
| Derived fields carry a full nested `result` field descriptor | A rollup or formula's `result` is itself a complete field config, so downstream treats it like a stored field | yes |
| Primary field | The one field every relation picker/link renders instead of a raw UUID | yes |
| Interface Designer record review: typed layout **roles**, not a field list | `titleFieldId`/`subtitleFieldId`/`thumbnailFieldId`/`recordColorFieldId`/`detailFieldIds`, each with its own type-eligibility rule | yes |
| Legacy drag-and-drop canvas, walked back to typed layouts | Only "Blank" layouts still support free-form canvas | yes (as cautionary lesson) |
| `viewIdForRecordSelection` | Scopes a link-record picker to a view instead of the whole table | yes |
| `prefersSingleRecordLink` | UI hint that fakes single-record cardinality over a many-link field | maybe |
| Views as user data | Personal/collaborative/locked — a view's ownership model is itself a permission | yes |
| `recordScopeFilters` (builder) vs interactive filters (end-user) | Builder-set scope filters exclude records from the client entirely; user-facing filters operate only inside that scope | yes |
| Explicit "hidden ≠ secure" warning | Documented admission that visually hidden fields can still leak underlying values | yes (as caution) |
| Synced tables: read-only base, but locally enrichable | New local fields/views/links can be added on top of a read-only synced table | yes |
| Omni: "can only perform actions the user could perform" | Agent authority is capped at the invoking user's own permissions, enforced in app code | yes |

## Worth stealing

### The field model — semantic types over one storage type

Airtable exposes **at least eight distinct field types that all store a JSON number**: `number`, `currency`, `percent`, `duration`, `rating`, `count`, `autoNumber`, and a numeric-result `formula`. Confirmed directly against Airtable's field schema (Web API field model):

- `number`: `{ precision: 0-8 }`
- `currency`: `{ precision: 0-7, symbol: string }`
- `percent`: `{ precision: 0-8 }`
- `duration`: `{ durationFormat: "h:mm" | "h:mm:ss" | "h:mm:ss.S" | "h:mm:ss.SS" | "h:mm:ss.SSS" }`
- `rating`: `{ icon: star|heart|thumbsUp|flag|dot, color: one of 10 bright colors, max: 1-10 }`
- `count`: `{ isValid: boolean, recordLinkFieldId }`
- `autoNumber`: read-only, no configurable options
- `formula`: numeric only when its `result` resolves to a numeric type

**Every one of these is "a number" at the storage layer and a completely different UI, validation, and formatting contract at the semantic layer.** A generic numeric-storage field would lose the ability to know a currency needs a symbol and 2 decimal places, a duration needs `h:mm:ss` parsing, and a rating needs a 1–10 bound with an icon — none of that is inferable from the stored value alone; it has to live in the schema.

The same pattern holds for date/time: `date` carries `dateFormat: { name: local|friendly|us|european|iso, format }`; `dateTime` adds **both** `timeZone` **and** `timeFormat: { name: 12hour|24hour, format }` — and critically, **`timeZone` is a property of the field, not the user viewing it.** Every viewer sees the same field-defined timezone; personalization is explicitly not part of this model.

### `singleSelect.choices[].id` — stable identity survives renames

A `singleSelect` field's `options.choices` is an array of `{ id, name, color }`. Filters, automations, and links reference the choice by **`id`**, which is immutable — renaming "In Progress" to "Active" changes only `name`, so every filter, view, and automation built against that choice keeps working. The obvious alternative (referencing choices by their display string) would silently break every consumer on a rename; Airtable avoided that by giving every choice a stable synthetic identity independent of its label. `checkbox` fields carry the same `{icon, color}` render-metadata pattern even though there's only one boolean value to render.

### Derived fields carry a full field descriptor for their result

The mechanism that makes Airtable's computed fields interoperable with everything else in the schema: `formula`, `rollup`, and `lookup` (API type `multipleLookupValues`) fields don't just carry their computation logic (`formula` string, or `recordLinkFieldId`/`fieldIdInLinkedTable` for rollup/lookup) — they carry a nested **`result`** property that is **itself a complete field-type descriptor**. A rollup summing a linked table's `currency` field carries `result: { type: "currency", options: { precision, symbol } }`. The practical consequence: any downstream consumer — a UI renderer, another formula, an API client — can treat a derived field exactly like a stored field, because its full semantic type (not just its raw value type) travels with it. Nothing has to special-case "this number came from a rollup" to know how to format it.

### Primary field — the display anchor every relation depends on

Every table has exactly one **primary field**, and it's what renders wherever a record is referenced compactly — in a linked-record chip, a search result, a relation picker. Without a well-chosen primary field, every relation picker across the base renders a bare row ID instead of something a human can recognize. It's a small mechanism (one designated field per table) with an outsized effect on whether the rest of the schema is usable by non-builders.

### Interface Designer's `recordReview` — typed layout roles, not a field list

Verified directly against Airtable's own element-config schema (`describe_page_element` for `recordReview`), which is the actual contract the builder enforces, not just documentation prose:

- **`titleFieldId`** (required) — the header of the record. Eligible types are constrained to `singleLineText, email, url, multilineText, date, dateTime, phoneNumber, autoNumber, barcode, number, percent, currency, duration, formula` **or a formula whose result resolves to one of those types** — i.e., type eligibility follows through a derived field's `result`, same as above. Must **not** also appear in `detailFieldIds` — it's rendered automatically as the header, and including it again is explicitly disallowed by the schema description.
- **`subtitleFieldId`** — anything **except** `multipleAttachments` (or a formula resolving to that).
- **`thumbnailFieldId`** — must be `multipleAttachments` (or a formula resolving to it) — the inverse constraint of subtitle.
- **`recordColorFieldId`** — must be `singleSelect`.
- **`groups[]`** — max **3** entries, each `{ fieldId, direction }`.
- **`detailFieldIds[]`** — an **ordered** array of fields shown on the detail pane, explicitly excluding the title field.

The mechanism: **a layout is defined as a set of named field *roles*, each with its own type-eligibility rule, not as an arbitrary list of fields with free-form placement.** The builder can't accidentally put an attachment field in the title slot or a long-text field in the color slot — the schema itself rules it out before it ever reaches a render step.

### The legacy-canvas retreat

Airtable's Interface Designer previously supported free-form drag-and-drop element placement on a blank canvas. That capability is now **legacy** — current guidance and product surface area steer builders toward the typed, table-bound layout elements (record review, grid, kanban, calendar, gallery, timeline, list, charts), and **"only 'Blank' layouts still support" the old drag-and-drop canvas.** Airtable started with an unconstrained canvas and walked it back to a fixed vocabulary of typed, role-based layouts. That's a specific, falsifiable lesson: **an open canvas is easy to build and hard to keep coherent; a fixed set of typed layout roles is more constrained to build but composes and validates far better** — and a company that started with the flexible option chose to deprecate it in favor of the constrained one.

### Scoped relation pickers and cardinality hints

`viewIdForRecordSelection` scopes a linked-record picker to a specific **view** rather than the entire target table — the difference between choosing from a curated, filtered set of candidates and a raw dropdown of 40,000 rows. `prefersSingleRecordLink` is a UI hint that renders a many-to-many link field as if it only ever holds one record, faking single-record cardinality in the UI without changing the underlying data model — useful where the schema is technically many-to-many but the product experience should feel one-to-one.

### Views as user-owned data, not just saved queries

Airtable views are explicitly typed by ownership: **personal** (visible only to the creator), **collaborative** (shared, editable by anyone with access), and **locked** (frozen — configuration can't be changed even by editors). A view's ownership category is itself part of the base's permission model, not a separate feature bolted on top.

### `recordScopeFilters` vs. interactive filters — two mechanisms that look identical, but aren't

Airtable draws an explicit line between two filtering mechanisms that produce visually indistinguishable results:

- **`recordScopeFilters`** — set by the interface **builder**. Records excluded by a scope filter are **never sent to the client** at all.
- **Tabs / dropdown filters** — controlled by the **end user**, but operating strictly *within* whatever scope the builder already locked in via `recordScopeFilters`.

The distinction matters because it's the difference between a real security boundary (data never leaves the server) and a UX convenience (data is present but filtered client-side). Airtable pairs this with an unusually candid documented warning: **"although visually hidden, underlying record/field values may still be exposed"** — a direct admission that hiding a field from a layout is not the same as restricting access to its value, and that builders relying on hidden-field-as-security are misusing the mechanism. (August 2025 changes further tightened this: dynamically filtered linked-record fields in interface forms can no longer show additional fields, specifically to prevent interface-only collaborators from having data exposed to them through dynamic filter combinations.)

### Synced tables — read-only source of truth, locally enrichable

A synced table mirrors data from another base or an external system and is fundamentally **read-only relative to its source** (editing synced fields directly is disallowed by default, though a 2024 "expanded editing" update allows editing synced linked-record and user fields specifically when the sync source has "All fields editable" turned on). Critically, **the destination base can still add net-new local fields, views, and links on top of the synced table** — those new fields simply don't sync back. This is the direct answer to the extremely common enterprise shape: *"our system of record is [Salesforce/whatever], but we need three extra fields, a couple of views, and a lightweight workflow layered on top without owning or duplicating their data."*

### Omni's authority ceiling

Airtable's documented constraint on its AI agent surface (Omni): it **"can only perform actions that the user could perform"** — the agent's effective permission ceiling is capped at whatever the invoking human is already authorized to do, and this is enforced in application code rather than left as a prompt-level instruction. A directly reusable governance pattern for any agent surface sitting on top of a permissioned data model.

## Worth avoiding

- **The abandoned free-canvas Interface Designer** is worth reading as a cautionary tale about scope: an unconstrained visual builder is attractive to ship first, but it doesn't compose with typed data the way a fixed vocabulary of layout roles does — Airtable's own roadmap bears this out by demoting the canvas to a legacy, single-layout-type feature.
- **"Hidden ≠ secure" is a real, documented failure mode**, not a hypothetical — Airtable had to ship a policy change (no additional fields shown under dynamic filters) specifically because interface-only collaborators were being exposed to data through a combination of features that looked safe individually.
- **Field-level timezone (not user-level) on `dateTime`** is a legitimate simplification but a real limitation — there's no per-viewer personalization of how a shared date/time field renders; every collaborator sees the field's own configured timezone.

## Facts & figures

- `currency.precision`: 0–7. `number`/`percent.precision`: 0–8.
- `rating.max`: 1–10; `rating.icon` ∈ {star, heart, thumbsUp, flag, dot}.
- `duration.durationFormat` ∈ 5 named formats (`h:mm` through `h:mm:ss.SSS`).
- `recordReview.groups`: max 3 entries.
- `singleSelect` choice colors: 30 supported values (per field-model API fetch).
- Two-way sync field editing (linked-record, user fields) shipped August 2024.

## Sources

- [Airtable Web API — Field model](https://airtable.com/developers/web/api/field-model)
- [Airtable Support — Supported field types overview](https://support.airtable.com/docs/supported-field-types-in-airtable-overview) · [Airtable Support — Number-based fields](https://support.airtable.com/docs/number-based-fields-in-airtable)
- [Airtable — Interface layout: Record review](https://support.airtable.com/docs/interface-layout-record-review) · **Primary/verified source: Airtable MCP `describe_page_element(elementType="recordReview")` schema fetch, run directly during this research pass** — titleFieldId eligibility list, detailFieldIds exclusion rule, groups maxItems=3, thumbnail/subtitle/color type constraints all confirmed against the live schema rather than docs prose.
- [Airtable Support — Interface layout: Record detail](https://support.airtable.com/docs/airtable-interface-layout-record-detail) · [Airtable Community — Why can't additional fields be shown when dynamic filters are applied?](https://community.airtable.com/interface-designer-12/why-can-t-additional-fields-be-shown-when-dynamic-filters-are-applied-46055)
- [Airtable Support — Two-way syncing in Airtable](https://support.airtable.com/docs/two-way-syncing-in-airtable) · [Airtable Support — Expanded editing capabilities for synced fields](https://support.airtable.com/docs/expanded-editing-capabilities-for-synced-fields)
- [Airtable Community — Web Tables in Omni](https://community.airtable.com/announcements-6/web-tables-in-omni-powering-crm-and-research-apps-46412)
- **Not directly verified:** the exact August-2025 policy-change date for dynamic-filter field exposure is inferred from community-forum discussion timing, not a dated changelog entry reached directly in this pass.
