---
name: physicsguard
description: "Use for engineering-simulation results and test data: low-fidelity physics residual audits that localize the faulty block, signal mapping, test-file contracts and model-vs-dataset validation. Not for software code behavior; use flowguard."
---

# PhysicsGuard

## Start from the model

1. Find this system's audit file (the path you were given, or `grep -rl "^hierarchy:" --include=*.yaml .`) and run `python -m physicsguard.cli hierarchy describe AUDIT.yaml` (add `--observed SNAPSHOT.yaml` when a snapshot exists). Name the blocks the request is about; keep the discussion on those blocks.
2. No audit yet: build a coarse balance from `references/templates/audit_model.yaml` and read it back with `hierarchy describe` before any evaluation.
3. After evaluating or comparing causes, read the verdicts on the same tree (the default output of `hierarchy evaluate|variants`).
4. A refinement that is not built yet shows as `(planned)` on the tree: that is the target; once built it shows as `(block)`.

## Choose a route

Pick one route, then load only its file.

| The request | Route file |
|---|---|
| A simulation result looks wrong: localize the faulty block, compare hypotheses, ask for the next signals, or build a candidate model from a validated hierarchy (default) | `references/routes/ai-debugging.md` |
| Understand an external model's boundary, inventory, units and stop conditions before a non-trivial audit | `references/routes/model-understanding-preflight.md` |
| Check how external signals or parameters map into PhysicsGuard variables: identity, unit, conversion, confidence, timing | `references/routes/signal-mapping-review.md` |
| Concrete test-data files need a file and field contract before analysis | `references/routes/test-file-contract-review.md` |
| Check a model against a contracted dataset: no-fit residuals, envelopes, calibration with holdout, validation depth | `references/routes/model-dataset-validation.md` |

## Rules for every route

- Node: a block in `hierarchy.blocks` (components, connections, children); a failing block shows its counterexample: the checked residuals with their sign.
- Parent: `parent_id`; a finer block names the coarse components it refines with `refines`.
- Known-bad: `fault_variants` in the audit file; each one must fail in its `expect_blocks`, and a `benign` one must stay neutral (`hierarchy variants`).
- Real binding: observed snapshots and series written by `testfile snapshot|series` from one test-file contract.
- Test binding: `validation run` checks the audit against a contracted dataset (holdout, depth, adequacy).
- Readback: `hierarchy describe` (text; `--observed`, `--json`, `--mermaid`); `hierarchy run|evaluate|compare|variants` print the same tree with verdicts (`--json` for the full report).
- Current vs target: the audit file is the current model; a refinement whose next template is not built yet is `planned`, the target, and once built the refined tree replaces the coarse one in the same file.
Read it with `python -m physicsguard.cli hierarchy describe audit.yaml`: default text, `--observed SNAPSHOT.yaml` for signal counts, `--json` for the full structure or `--mermaid` for a diagram. No solve or observed audit is performed.

Exit codes: 0 passed, 1 checked and not passed, 2 could not run.

- If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.
- For audit YAML, observed snapshots and model growth, load `references/model-format.md`.
- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.
- A hand-off names another route: load that route file. Templates are in `references/templates/`.
