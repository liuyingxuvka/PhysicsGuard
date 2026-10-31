---
name: physicsguard
description: "Use for engineering-simulation results and test data, and also for a physics or engineering calculation you make yourself (units, balances, conversions): low-fidelity physics residual audits that localize the faulty block, signal mapping, test-file contracts and model-vs-dataset validation. Not for software code behavior, including a simulation's code; use flowguard."
---

# PhysicsGuard

## Start from the model

1. Find this system's audit file (the path you were given, or `grep -rl "^hierarchy:" --include=*.yaml .`) and run `python -m physicsguard.cli hierarchy describe AUDIT.yaml` (add `--observed SNAPSHOT.yaml` when a snapshot exists). Name the blocks the request is about; keep the discussion on those blocks.
2. No audit yet: build a coarse balance from `references/templates/audit_model.yaml` and read it back with `hierarchy describe` before any evaluation.
3. After evaluating or comparing causes, read the verdicts on the same tree (the default output of `hierarchy evaluate|variants`).
4. A refinement that is not built yet shows as `(planned)` on the tree: that is the target; once built it shows as `(block)`.
5. When one block of the audit tree gets too big to localize a fault, refine it into a finer block tree (a child block names the coarse components it refines with refines; a refinement not built yet shows as (planned)), and keep the work on the blocks the request names.

## Quick check of your own calculation

1. Find coarse relations with `python -m physicsguard.cli modules list --find WORDS` (replace WORDS with terms from the question), inspect a candidate with `python -m physicsguard.cli modules describe TYPE`, and choose a self-contained component with nonempty declared `variables` for a standalone check; a reference-only balance needs those variables' owning components. Write `audit.yaml` from `references/templates/audit_model.yaml` with the requested blocks and tolerable residual scales.
2. Write `observed.yaml` from `references/templates/observed_snapshot.yaml`: preserve given inputs in their original units as paired `raw_value` and `raw_unit`; if the answer also claims a converted input, retain it as `value` so the loader checks agreement. Preserve claimed answer outputs as raw quantities too. Use supported unit names (for example `degC` for Celsius), declare each target `unit`, and record an explicit factor for cross-dimension conversion. Inspect the supplied values with `cat observed.yaml`.
3. Read back the audit and mappings without solving: `python -m physicsguard.cli hierarchy describe audit.yaml --observed observed.yaml`.
4. Check the supplied answer with `python -m physicsguard.cli hierarchy evaluate audit.yaml observed.yaml > check.txt`. Exit 1 means a checked failure; keep its output for the next steps.
5. Read `cat check.txt`: locate `own FAIL`, its hint and local resolution, and retain all non-pass states and mapping warnings.
6. State only the conclusion supported by the saved result, name its checked boundary, and keep any unresolved parts visible.

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
- Readback: `hierarchy describe` (text; `--observed`, `--json`, `--mermaid`); `hierarchy run|evaluate|compare|variants` print the same tree with verdicts, the `hint:` lines and the `resolution:` lines (`--json` for the full report).
- Current vs target: the audit file is the current model; a refinement whose next template is not built yet is `planned`, the target, and once built the refined tree replaces the coarse one in the same file.

Choose a residual scale as the error you can tolerate in the residual's unit; read the resolution line before you state a number as checked.
Read it with `python -m physicsguard.cli hierarchy describe audit.yaml`: default text, `--observed SNAPSHOT.yaml` for signal counts, `--json` for the full structure or `--mermaid` for a diagram. No solve or observed audit is performed.

Exit codes: 0 passed, 1 checked and not passed, 2 could not run.

- If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.
- For audit YAML, observed snapshots and model growth, load `references/model-format.md`.
- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.
- A hand-off names another route: load that route file. Templates are in `references/templates/`.
