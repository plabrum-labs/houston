# Flatfile

**What it is:** Embeddable customer data import — upload a spreadsheet, get mapped/validated/clean rows out. Developer-facing (React/JS SDK + Node backend), not a low-code importer widget.
**Axis:** data migration (onboarding surface).
**Depth:** thin — single mechanism researched in depth (Automap), rest is landscape context.

## Products & surfaces

| Product | What it is |
|---|---|
| **Automap** (`@flatfile/plugin-automap`) | Automatic column-mapping plugin: matches incoming headers to a target schema without a human clicking through a mapping UI. |
| Core Flatfile platform | Sheets, validation rules, transformation hooks, review UI for the cases Automap doesn't clear. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| **`accuracy` threshold gate** | `'confident'`: every mapped field must be `'strong'` (>90%) or `'absolute'` (100%) confidence. `'exact'`: every field must be `'absolute'` (100%). All-or-nothing — one weak field aborts the whole automap. | maybe |
| **`onFailure` callback** | Fires when the accuracy bar isn't met; receives `spaceId`/`fileId` context to trigger notification/webhook/manual-mapping fallback | maybe |

## Worth stealing

The **threshold-as-gate, not threshold-as-score** design: Automap doesn't emit a confidence number for a human to eyeball — it either clears the bar for every field or refuses to run automatically, handing off via `onFailure`. That forces an explicit "who does the fallback mapping" decision into the integration code rather than leaving a half-mapped file to slip through.

## Worth avoiding

**Automap is stateless.** Per the docs available, there is no indication Automap retains or learns from prior mapping decisions across runs or across customers — each file is remapped from scratch against the target schema by the same matching logic every time. A customer who corrects a mapping once gets no benefit from that correction on their next upload; there's no accumulated mapping memory the way (for instance) an active-learning matcher accumulates labels.

## Facts & figures

None published beyond the accuracy thresholds themselves; no volume/accuracy benchmarks found.

## Sources

- [Automap Plugin docs](https://flatfile.com/docs/plugins/automap)
- [Automate with Automap guide](https://flatfile.com/docs/learning-center/guides/automap)
- [How does Flatfile ensure mapping is as accurate as possible?](https://support.flatfile.com/articles/8421984657-how-does-flatfile-ensure-mapping-is-as-accurate-as-possible)

**Adjacent player worth naming:** [Nuvo](https://www.getnuvo.com) ships the same embeddable-importer shape (map/validate/clean spreadsheet data client-side) but with an explicit claim its AI mapping "improves with every import" — i.e. it claims exactly the cross-run learning Automap does not have documented. Not independently verified; vendor claim only. Nuvo also markets that all data processing happens in the target application's frontend, so nothing sensitive transits Nuvo's servers.
