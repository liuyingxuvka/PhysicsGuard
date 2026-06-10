## Why

PhysicsGuard can already run low-fidelity residual audits and review signal mappings, but test-bench projects add a stronger requirement: every test data file has its own field set, time basis, extraction script, test-bench version, and model binding. AI analysis must not silently miss fields, reuse stale mappings after schema drift, or claim broad coverage when a test file has unclassified, unmapped, or stale parameters.

## What Changes

- Add an optional, parallel PhysicsGuard route for test-bench and test-data files. It is required only when a workflow uses concrete test files, test-bench exports, CSV/TSV files, database/historian exports, run files, or field-level test data; ordinary model-only PhysicsGuard usage remains on the existing AI debugging routes.
- Add a script-generated Data File Manifest that records file format, hashes, field names and counts, row/sample counts, time range, sampling frequency, continuity, units, basic field summaries, and extractor script/config identity.
- Add a Test File Contract that binds one test data file to its manifest, test-bench profile, extractor profile, model binding, parameter catalog, role matrix, mapping edges, coverage policy, optional segments, and known defects.
- Add parameter coverage artifacts for parameter identity, multi-view roles, mapping edges, coverage status, and fail-closed contract checking.
- Add model-binding artifacts that connect a test file contract to specific PhysicsGuard hierarchy/audit files and hashes.
- Add CLI commands and scripts for manifest generation, contract inspection/checking, project-level batch checking, contract diffing, and CI-friendly validation.
- Add FlowGuard model/checks, model-code traceability rows, docs, examples, tests, and Codex skill routes for the new workflow.
- Add and install a Codex child skill `physicsguard-test-file-contract-review`, while keeping it conditionally routed rather than globally mandatory.

## Capabilities

### New Capabilities
- `data-file-manifest`: Script-generated data-file shape, timing, field, and extractor evidence.
- `test-file-contract`: One resolved contract per test data file, with freshness, profile, segment, and claim-gating semantics.
- `parameter-coverage`: Parameter catalog, role matrix, mapping edges, coverage policy, and no-missing-parameter contract checks.
- `model-binding-contract`: Explicit binding from a test file contract to PhysicsGuard hierarchy/model artifacts and version/hash evidence.
- `test-file-skill-route`: Optional Codex skill route and closure behavior for test-bench/test-file workflows.

### Modified Capabilities
- `physicsguard-skill-routes`: Add a conditional test-file contract route; do not require it for ordinary model-only PhysicsGuard workflows.
- `physicsguard-closure-workflow`: Closure must account for test-file contract evidence when a workflow includes test data files.

## Impact

- Affected code: new schema/core/io modules for manifests, contracts, parameter coverage, model bindings, and diffs; `src/physicsguard/cli.py`; `src/physicsguard/workflow.py`; package exports.
- Affected scripts: new extractor/checker/sync helpers under `scripts/`.
- Affected artifacts: templates, examples, docs, FlowGuard models/checks, model-code ledger, project policy, skill routes, and installed Codex skill copies.
- No new high-fidelity physical models, no commercial-tool adapter, no automatic repair behavior, and no hidden unit conversion tables.
- The initial extractor support should remain dependency-light: CSV/TSV and standard manifest files in core; richer formats may be supported by project-provided extractors that emit the standard Data File Manifest.
