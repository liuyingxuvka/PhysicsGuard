## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create proposal, design, specs, and task records for dataset identity, model-dataset validation, calibration/confidence feedback, and model library.
- [x] 1.2 Validate the OpenSpec change with strict validation.
- [x] 1.3 Add FlowGuard models/checks for dataset identity, model-dataset validation, and model library evidence gates.
- [x] 1.4 Update model-code traceability and adoption logs.

## 2. Dataset Identity And Symmetric Contracts

- [x] 2.1 Add logical dataset and relation index schemas.
- [x] 2.2 Add loaders and core checks for logical dataset records and relation indexes.
- [x] 2.3 Extend test-file contracts with an optional logical dataset reference.
- [x] 2.4 Add templates, docs, examples, and CLI checks.

## 3. Validation Roles And Confidence Inputs

- [x] 3.1 Extend role/mapping schemas with validation role, use policy, measurement confidence, and data quality status.
- [x] 3.2 Preserve backwards compatibility for existing contract examples.
- [x] 3.3 Add tests for redundant sensors and same-target mappings that remain distinct sources.

## 4. Model-Dataset Validation

- [x] 4.1 Add model validation plan and report schemas.
- [x] 4.2 Implement direct no-fit validation from bound audit/observed files.
- [x] 4.3 Implement physical envelope checks and redundant-sensor consistency checks.
- [x] 4.4 Add CLI command for validation plans.
- [x] 4.5 Add docs, templates, and examples.

## 5. Conservative Calibration And Confidence Feedback

- [x] 5.1 Implement `none` and bounded least-squares calibration methods.
- [x] 5.2 Require finite bounds, initial values, scales, and reasons for calibration parameters.
- [x] 5.3 Separate `optimization_success`, direct audit pass, holdout audit pass, and final validation status.
- [x] 5.4 Emit confidence updates without mutating contracts.

## 6. Model Library

- [x] 6.1 Add model library schema, core checks, template, docs, and CLI command.
- [x] 6.2 Require validation report references for validated reuse status.
- [x] 6.3 Keep raw data out of the model library.

## 7. Codex Skill Routes And Project Policy

- [x] 7.1 Add `physicsguard-model-dataset-validation` skill.
- [x] 7.2 Add `physicsguard-model-library` skill.
- [x] 7.3 Update main AI debugging and audit closure skills.
- [x] 7.4 Update `.physicsguard/project.yaml` routes and policies.
- [x] 7.5 Sync repository skills to installed Codex skills and verify matching hashes.

## 8. Tests And Validation

- [x] 8.1 Add schema/core/CLI tests for all new routes.
- [x] 8.2 Run focused tests for test-file, dataset identity, validation, and model library.
- [x] 8.3 Run OpenSpec, FlowGuard, ledger, skill sync, CLI smoke, and full pytest checks.
- [x] 8.4 Reinstall/sync local editable package if needed and verify imports resolve to the workspace.
- [x] 8.5 Perform final completion audit against the original objective.
