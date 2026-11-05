---
name: physicsguard
description: "Use for engineering-simulation results and test data, and for a physics or engineering calculation you make yourself (units, balances, conversions): low-fidelity residual audits, signal mapping, test-file contracts and model-vs-dataset validation. Software code behavior belongs to flowguard."
---

# PhysicsGuard

## Start from the model

1. Find the supplied audit file and run `python -m physicsguard.cli hierarchy describe AUDIT.yaml` (`--observed SNAPSHOT.yaml` when supplied). Name the blocks the question concerns.
2. No audit: choose coarse relations with `modules list --find WORDS` and `modules describe TYPE`, then build from `references/templates/audit_model.yaml`. A standalone component needs nonempty declared variables; a reference-only balance needs their owning components. Read the audit back before evaluating it.
3. Refine only a block too broad to localize the problem. A proposed template is `(planned)`; a built child block names its coarse components with `refines`.

## Check a calculation against its original

1. Write `observed.yaml`: **quote each given number from the question file; do not convert it yourself and then fill it in.** Declare `sources: {question: question.txt}` and, on a variable or property, `quote: {from: question, text: "6 L/min"}`. End a numeric quote at its unit. A pipe-table cell uses `quote: {from: question, row: "run 3", column: "Flow"}`. See `references/model-format.md` and `examples/source_reading/` in the repository.
2. Retain the answer's claimed SI `value` and target `unit`; the tool reads the matching original span and compares them. For a change of quantity (L/min to kg/s), declare the linking property once under `properties`, with its own quote, and name it using `conversion_property`. The only unit table is the tool's; an unsupported or ambiguous reading stays grey. A transducer calibration is explicitly unchecked. An original numeric range checks containment and retains the AI's chosen point.
3. Quoted physical parameters go under `parameters`, keyed `component.parameter`, and replace the audit parameter for evaluation. For CSV, `testfile snapshot CONTRACT.yaml --at t_s=90` records the selection key; a row without a key is grey. CSV units come from column headers, never a stored conversion factor. Example commands and the quote/cell/key forms are in the repository example.
4. Read the mappings with `hierarchy describe audit.yaml --observed observed.yaml`. Then run `hierarchy evaluate audit.yaml observed.yaml > check.txt` and read the saved tree, `sources:` summary, hints and resolution. Exit 1 is a checked failure; exit 2 means the command could not run. Do not replace a red or grey result with a narration of success.
5. A passing block is source-backed green only when its actual check used at least one sourced variable or parameter; otherwise it is grey `passes on AI values only`. A derived value is not an external observation. Choose residual scales as tolerable errors, read their local resolution, and state only the checked boundary.

## One route per task

Pick one route; load only its file.

| Request | Route |
|---|---|
| Localize a simulation's faulty block, compare causes or ask for the next signals (default) | `references/routes/ai-debugging.md` |
| Establish an external model's boundary, inventory, units and stop conditions | `references/routes/model-understanding-preflight.md` |
| Check signal/parameter identities, units, conversion, confidence and timing | `references/routes/signal-mapping-review.md` |
| Review concrete data-file and field contracts | `references/routes/test-file-contract-review.md` |
| Check a contracted dataset, holdout, depth and adequacy | `references/routes/model-dataset-validation.md` |

## Rules for every route

- Node: a block in `hierarchy.blocks`, with components, connections and children.
- Parent: `parent_id` links blocks; a finer block names its coarse components with `refines`.
- Known-bad: `fault_variants` must fail their `expect_blocks`; a `benign` case stays neutral (`hierarchy variants`).
- Real binding: `testfile snapshot|series` binds real observations from the data contract.
- Test binding: `validation run` checks the contracted dataset, holdout, depth and adequacy.
- Readback: `hierarchy run|evaluate|compare|variants` print verdicts on the same tree; `describe` reads structure without solving (`--json` for detail).
- Current vs target: the audit file is current; a proposed template is `(planned)` until a built refinement replaces its coarse block.
- When discussing a set-up, show the Mermaid output of `hierarchy flow AUDIT.yaml` with the relevant `--observed`, `--focus BLOCK` or `--quantity mass_flow`. It comes from real relations and says what it omits. If too large, use a smaller choice it names; if none fits, read `--json`. Routine edits need no picture.
- Source text, mappings and model assumptions have different limits. Preserve unknowns; pointwise consistency does not prove stateful prediction or physical truth. See `references/model-format.md` for YAML, snapshots and growth.
- If the engine is absent, install it once with `python -m pip install -e <PhysicsGuard checkout>`. No version gate. A handoff names another route: load that route file.
