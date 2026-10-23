---
name: physicsguard
description: "Use for engineering-simulation results and test data: low-fidelity physics residual audits that localize the faulty block, signal mapping, test-file contracts and model-vs-dataset validation. Not for software code behavior; use flowguard."
---

# PhysicsGuard

Pick one route, then load only its file.

| The request | Route file |
|---|---|
| A simulation result looks wrong: localize the faulty block, compare hypotheses, ask for the next signals, or build a candidate model from a validated hierarchy (default) | `references/routes/ai-debugging.md` |
| Understand an external model's boundary, inventory, units and stop conditions before a non-trivial audit | `references/routes/model-understanding-preflight.md` |
| Check how external signals or parameters map into PhysicsGuard variables: identity, unit, conversion, confidence, timing | `references/routes/signal-mapping-review.md` |
| Concrete test-data files need a file and field contract before analysis | `references/routes/test-file-contract-review.md` |
| Check a model against a contracted dataset: no-fit residuals, envelopes, calibration with holdout, validation depth | `references/routes/model-dataset-validation.md` |

## Rules for every route

One model tree: the audit file is one tree. The root block is the whole plant, child blocks are
subsystems, finer blocks refine coarser components (`refines`). Every node has five abilities:
structure (components, connections, children), counterexamples (failing checked residuals with
block and sign), known-bad variants that must fire (`fault_variants`), binding to the real plant
(signals mapped with units into snapshots), and binding to test data (contracts and validation plans).
Read it with `python -m physicsguard.cli hierarchy describe audit.yaml` (`--mermaid` for a diagram).

Exit codes: 0 passed, 1 checked and not passed, 2 could not run.

- If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.
- For audit YAML, observed snapshots and model growth, load `references/model-format.md`.
- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.
- A hand-off names another route: load that route file. Templates are in `references/templates/`.
