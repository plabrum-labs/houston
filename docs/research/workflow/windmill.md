# Windmill

**What it is:** Open-source workflow/script platform; the notable mechanism is **suspend & approval** — a flow step that pauses for an arbitrary schema-defined form, with the submitted values flowing directly into later steps.
**Axis:** workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Windmill flows** | Multi-step scripts/workflows with suspend/resume support. |
| **Suspend & Approval** | A flow step that pauses execution pending one or more external "resume" events, optionally gated by a custom form. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Custom approval form | Arbitrary schema form rendered on the approval page; submitted args flow into later steps | yes |
| `resume["..."]` payload | Subsequent steps read approval-form fields directly (e.g. `resume["Action"]`, `resume["Message"]`) | yes |
| Multiple approvers + required count | Configurable N-of-M approvals before the flow proceeds | yes |
| Custom timeout / auto-cancel | A per-step timeout after which the flow auto-cancels if under-approved | yes |

## Worth stealing

### An arbitrary form on the approval page, not a fixed approve/reject button

Windmill lets you *"add an arbitrary schema form to be provided and displayed on the approval page,"* where the approver fills in defined properties (name, description, type, default value) before submitting. The submitted values are then directly readable by downstream steps via `resume["Action"]`, `resume["Message"]`, or the whole payload via `resume` — described in the docs as *"the keys you can use as predicate expressions for your branches."* This turns an approval step into a structured data-collection point, not a binary gate: the approver can select a routing option, attach a note, or supply a corrected value, and the flow branches or is parameterized directly off that input. (A form on the approval page is Cloud/Enterprise Self-Hosted only.)

### Multiple approvers with a required count

*"The number of required approvals can be customized. This allows flexibility and security for cases where you either require approvals from all authorized people or only from one."* This is a lightweight N-of-M quorum mechanism, distinct from a single hardcoded approver — the flow tracks how many resume events have arrived against the configured threshold before proceeding.

### The explicit under-approval warning — a timeout is not optional

Windmill's docs state the failure mode plainly: *"The flow will remain suspended and will not proceed to the next step until the exact number of required approval events is received. If fewer approvals than required are received, the flow stays suspended indefinitely (unless a timeout is configured)."* A **custom timeout** can be set per step, after which the flow auto-cancels (or, if configured, continues to a branch that explicitly handles the "not enough approvals" case rather than just erroring). The explicit callout — indefinite suspension is the *default* consequence of not setting a timeout — is the useful transferable lesson: any N-of-M human-approval gate needs a mandatory expiry path designed in from the start, not bolted on after the first flow gets stuck.

## Worth avoiding

The source material here didn't surface Windmill's mechanics for *changing* required-approval count or approver list mid-flight (compare Camunda's explicit support for reassigning/modifying task metadata on already-running instances, `camunda.md`) — worth checking directly if in-flight reconfiguration of an approval gate matters.

## Facts & figures

- Custom approval forms: Cloud & Enterprise Self-Hosted only (vendor docs).

## Sources

- [Suspend & Approval / Prompts](https://www.windmill.dev/docs/flows/flow_approval) · [Custom timeout for step](https://www.windmill.dev/docs/flows/custom_timeout)
