# marimo

**What it is:** An open-source reactive Python notebook whose file format is a plain, valid `.py` module — not JSON.
**Axis:** app-builder, analysis.
**Depth:** thin.

## Products & surfaces

| Surface | What it is |
|---|---|
| **marimo notebook** | Reactive Python (+ SQL cell support) editor, run locally or via `marimo edit`. |
| **`marimo run`** | Deploys a notebook as a read-only interactive app. |
| **`python notebook.py`** | Runs the notebook as a plain script, in dependency order, with no marimo runtime required. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Cells are functions in a valid `.py` file | Notebook *is* a Python module — importable, `git diff`-able as code, runnable as a script | yes |
| Reactive dependency graph | Running a cell auto-runs everything downstream that references its variables (default "auto-run") | yes |
| Configurable lazy/stale runtime | Switch "on cell change" to lazy: downstream cells are marked **stale**, not auto-executed, until the user explicitly triggers them | yes |
| pytest-testable cells | Functions named `test_*` or classes named `Test*` are picked up directly by pytest, running only the tests — not the whole notebook | yes |
| PEP 723 inline deps | Dependency metadata lives inline in the `.py` file per the PEP 723 single-file-script spec | maybe |

## Worth stealing

**Cells-as-functions, notebook-as-module.** marimo's core bet: each cell compiles to a function in a real `.py` file, and the file as a whole is a valid, importable Python module. This buys, in one design decision: clean `git diff`s (code, not a JSON blob of cell outputs and execution counts), `python notebook.py` running standalone with no special runtime, `import notebook` reuse in other code, and direct pytest collection of any cell shaped like a test. Compare to Jupyter's `.ipynb` — output-embedded JSON that diffs badly and can't be imported.

**Lazy/stale as a first-class runtime mode, not just a settings footnote.** Default reactivity is "auto-run all descendants," identical in spirit to Hex's model. But marimo also ships a **lazy mode**: a cell edit marks its descendants **stale** without executing them, and the user chooses when to pay the cost. This is a direct answer to the standard complaint about reactive notebooks — "I changed one input and now it re-ran a 10-minute query" — without giving up reactivity's correctness guarantee (stale ancestors still get force-run before a cell that depends on them executes, so you never see output computed from outdated inputs).

## Worth avoiding

Not enough independent evidence gathered in this pass to make a strong avoid-list claim; treat this file as thin.

## Facts & figures

- Open source (marimo-team/marimo on GitHub).
- PEP 723 support for inline script dependency metadata.

## Sources

- [marimo docs home](https://docs.marimo.io/) · [Reinventing notebooks as reusable Python programs](https://marimo.io/blog/python-not-json) · [GitHub](https://github.com/marimo-team/marimo)
- [Runtime configuration](https://docs.marimo.io/guides/configuration/runtime_configuration/) · [Reactivity guide](https://docs.marimo.io/guides/reactivity/)
- [pytest guide](https://docs.marimo.io/guides/testing/pytest/)
- **Not directly verified:** SQL-cell dependency-inference mechanics (whether it mirrors Hex's cross-language static analysis) were not independently confirmed in this pass.
