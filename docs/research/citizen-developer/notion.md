# Notion

**What it is:** A citizen-developer database/docs hybrid. Independently arrives at the same "typed layout roles" pattern as Airtable's Interface Designer for its views API, but makes a deliberate, documented tradeoff to collapse its numeric types and its formula-to-API type surface — useful as both a positive convergence signal and a cautionary example.
**Axis:** semantic layer, app-builder.
**Depth:** medium — views API and status/formula type behavior verified directly against Notion's own API reference.

## Products & surfaces

| Product | What it is |
|---|---|
| **Databases** (data sources, post-2025-09-03) | Typed property schemas over pages |
| **Views** | Table / board / calendar / timeline / gallery / list layouts over one data source, each with its own required config |
| **Status property** | A two-level enum: options grouped into named, ordered groups |
| **Formulas 2.0** | Expanded formula engine supporting 7 internal data types, but a narrower API-exposed result surface |
| **Linked databases** | A view of one data source's rows surfaced inside another page/context |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Views API requires type-specific config | `board` requires `group_by`; `calendar` requires `date_property_id`; `timeline` requires **both** `date_property_id` and `end_date_property_id` | yes |
| Two-level status enum | Options nest inside named `groups`, each carrying `option_ids`; views can group by either level | yes |
| Number property collapses everything into one type + `format` enum | Currency, percent, and plain number are all `type: "number"` with a `format` string, not distinct types | no (cautionary) |
| Formulas 2.0 has 7 internal data types, API exposes 4 | `person`, `page`, `list` computed in the formula engine never survive as a typed API result | no (cautionary) |

## Worth stealing

### Views API — typed layout roles, independently convergent with Airtable

Notion's views API (2025-09-03 data-source model) requires different mandatory configuration depending on view type, verified directly against the current API guide:

- **`board`** views require **`group_by`** — a board fundamentally doesn't make sense without a property to define its columns, so the API rejects a board view definition that omits it.
- **`calendar`** views require **`date_property_id`** — same logic, a calendar has to know which date property places an item on the grid.
- **`timeline`** views require **both `date_property_id` and `end_date_property_id`** — a timeline is a calendar generalized to a *range*, so it needs a start **and** end date property, and both are mandatory in the schema rather than the second being optional.

This is the same shape as Airtable's `recordReview` element schema (`titleFieldId` required, `thumbnailFieldId` type-constrained to attachments, etc.) — **each layout type declares its own required, typed field roles, and the platform enforces them at the schema level rather than leaving them to convention.** Two products, built independently, converged on "a view/layout is a named set of typed field roles" as the right primitive for a typed-database-backed UI. That convergence is stronger evidence for the pattern than either instance alone.

### Two-level status property — the common "12 values that really mean 3 phases" shape

The `status` property type is explicitly two-level: individual **options** (e.g., "Not started," "Researching," "Drafting," "In review," "Done," "Archived") each belong to exactly one **group**, and groups themselves have their own `id`, `name`, `color`, and an ordered `option_ids` array of the options assigned to them. Every new status property ships with three built-in, unchangeable top-level groups — **To-do / In progress / Complete** — and the granular options are freely customizable underneath.

The mechanism directly addresses a shape every enterprise workflow app runs into: a status field with a dozen granular values that business logic and reporting almost always want to reduce to three or four **phases**. Rather than making the app builder maintain a second derived "phase" field and keep it in sync, Notion bakes the two-level structure into the property type itself — **views can group by the option or by its parent group**, so a kanban board can show either the fine-grained 12-column view or the coarse 3-column view of the *same underlying data*, with no duplicated field.

## Worth avoiding

### Cautionary: collapsing all numbers into one type with a giant `format` enum

Where Airtable models `currency`, `percent`, `number`, `duration`, `rating`, `count`, and `autoNumber` as **distinct field types** each with their own options schema, Notion models all of them as a single `type: "number"` property with a **`format`** string enum — confirmed via the API reference to include (non-exhaustively) `number`, `number_with_commas`, `percent`, and roughly three dozen currency variants (`dollar`, `euro`, `pound`, `yen`, `yuan`, `won`, `ruble`, `rupee`, `franc`, `real`, `lira`, `krona`, `ringgit`, and more — Notion's own docs describe this list as extending beyond what's enumerated inline).

The tradeoff this creates: **`format` is purely a display hint on one underlying numeric type**, not a semantic type with its own validation or behavior contract. A currency-formatted number and a percent-formatted number are, to any consumer that doesn't specifically branch on the `format` string, indistinguishable — there's no analog to Airtable's `rating.max` bound or `duration.durationFormat` parsing rules, because those aren't really different *types* in Notion's model, just different labels painted on the same float. This is a real design choice with a real cost: it's simpler to implement (one code path for "number"), but it pushes all the semantic distinctions Airtable encodes in the schema back onto the consumer to infer from a string.

### Cautionary: Formulas 2.0 computes richer types than the API can return

Notion's formula engine internally supports **seven** data types — string, number, boolean, date, list/array, **person**, and **page** — a genuine expansion in Formulas 2.0 that lets a formula reference and manipulate people and page relations, not just scalars. But the **public API's formula property result type is restricted to exactly four**: `boolean`, `date`, `number`, `string` (confirmed directly against Notion's page-property-values API reference). **A formula that computes a person or a page inside the product never survives as a typed value through the API** — it either gets coerced to a string representation or isn't retrievable in its native form at all.

The lesson: **the richest types a computation engine can produce are only as useful as the narrowest interface downstream consumers actually read them through.** If the API — which is what every integration, automation, and external consumer actually sees — caps out below what the in-product formula engine can express, then "Formulas 2.0 supports person and page types" is a UI-only capability from an integration's point of view, not a platform-wide one. Any semantic-layer design should audit whether every internal type has a matching, faithful representation all the way out to its external interface, not just in the primary UI.

## Facts & figures

- API version referenced: **2025-09-03** (the data-source/views API generation this research covers).
- `status` property: exactly 3 fixed top-level groups (To-do / In progress / Complete); options within groups are fully customizable.
- `number` property `format` enum: ~30+ named values spanning plain/comma-formatted numbers, percent, and dozens of currency symbols.
- Formula engine internal types: 7 (string, number, boolean, date, list, person, page). API-exposed formula result types: 4 (boolean, date, number, string).

## Sources

- [Notion Developers — Working with views](https://developers.notion.com/guides/data-apis/working-with-views)
- [Notion Developers — Data source properties / property object](https://developers.notion.com/reference/property-object)
- [Notion Developers — Page properties (page-property-values)](https://developers.notion.com/reference/page-property-values)
- [Notion Developers — Number properties now support more currency formats (changelog)](https://developers.notion.com/changelog/number-properties-now-support-more-currency-formats)
- [Notion Help Center — The status property gives you clarity on task progress](https://www.notion.com/help/guides/status-property-gives-clarity-on-tasks)
- [Notion Help Center — Formulas 2.0: what's changed](https://www.notion.com/help/guides/new-formulas-whats-changed) · [Thomas Frank — Notion Formulas 2.0 cheat sheet](https://thomasjfrank.com/notion-formula-cheat-sheet/) · [Thomas Frank — Data Types](https://thomasjfrank.com/formulas/data-types/)
- [Notion Help Center — Calendar view databases](https://www.notion.com/help/guides/calendar-view-databases) · [Notion Help Center — Timeline view](https://www.notion.com/help/timelines)
- **Not directly verified:** the complete enumerated list of `number.format` currency values (30+ figure is an approximate count from partial enumeration in the API reference, not a verbatim complete list).
