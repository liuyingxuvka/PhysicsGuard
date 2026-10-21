## Why

PhysicsGuard now has a test-file contract route that checks field coverage and
model binding before AI analysis. That route deliberately stops short of three
needed workflow layers:

- symmetric identity records for large external test files that should not be
  moved into the project;
- model-versus-dataset validation after a file contract passes;
- reuse records for models that have evidence from prior datasets.

Without these layers, agents can either duplicate contract work across similar
test files or overclaim from a file-coverage pass as if it proved physical
model validity.

## What Changes

- Add logical dataset records and relation indexes so every concrete test file
  keeps its own representation evidence while non-identical files keep
  symmetric contracts.
- Extend parameter coverage roles with validation usage, source-use policy,
  measurement confidence, and data quality status.
- Add a model-dataset validation workflow with explicit plans, direct
  no-fit validation, physical envelope checks, redundant-sensor consistency,
  conservative bounded calibration, holdout validation, confidence feedback,
  and safe-claim output.
- Add a model library index that stores reusable model metadata and validation
  evidence references without storing large raw datasets.
- Add Codex skill routes, CLI commands, FlowGuard models, docs, templates,
  examples, tests, installed skill sync, and local validation evidence.

## Non-Goals

- No movement or copying of large raw test data.
- No parent/child base-delta relationship between non-identical test-file
  contracts.
- No Adam or SPSA implementation in the first version.
- No high-fidelity physical model generation, commercial-tool adapter, or
  automatic repair.
- No claim that optimizer convergence is the same as validation pass.

## Capabilities

### New Capabilities

- `dataset-identity`: in-project metadata for file representations, logical
  datasets, and symmetric relation indexes.
- `model-dataset-validation`: plans and reports for model validation against
  contracted test data.
- `calibration-confidence-feedback`: conservative bounded calibration and
  confidence updates derived from validation evidence.
- `model-library-index`: reusable model asset records backed by validation
  reports.

### Modified Capabilities

- `test-file-contract`: optional link to a logical dataset record and richer
  validation-facing roles.
- `physicsguard-skill-routes`: route from test-file contracts into
  model-dataset validation.
- `physicsguard-closure-workflow`: closure reads validation reports and does
  not allow broad claims from contract-only or optimizer-only evidence.

## Impact

- Affected code: new schema/core modules, loaders, CLI commands, package
  exports, test-file contract schema, and parameter coverage schema.
- Affected artifacts: OpenSpec files, FlowGuard models, templates, examples,
  docs, Codex skills, project policy, installed skill copies, and tests.
