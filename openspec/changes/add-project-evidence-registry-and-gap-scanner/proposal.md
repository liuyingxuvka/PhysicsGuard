## Why

PhysicsGuard now has test-file contracts, logical dataset identity,
model-dataset validation, and model-library reuse records. These routes still
lack one project-level evidence layer that tells AI agents what files, facts,
contexts, and source documents exist before validation or reuse claims.

Without a project evidence registry and gap scanner, agents can miss source
PPT/PDF/Excel files, cleaned/raw data lineage, model-required facts, testbench
context, or missing required parameters. That creates two risks: unchecked
model-data validation and reuse claims that are based on incomplete evidence.

## What Changes

- Add a Project Evidence Registry for project artifacts, engineering facts,
  context cards, evidence bundles, conflicts, and missing evidence records.
- Add an evidence scanner that finds candidate files and already-known
  PhysicsGuard artifacts that may need registry entries.
- Add gap checks that classify missing evidence as blocking, review, or
  optional.
- Add model/test evidence requirements so model validation and model-library
  reuse can ask whether required facts, artifacts, and contexts exist.
- Add evidence binding records so test-field-to-model and fact-to-model
  bindings are visible in the project evidence layer without duplicating full
  test-file contracts.
- Add a Project Evidence Map report that summarizes tests, models, facts,
  bindings, coverage, validation evidence, and open gaps for AI onboarding.
- Add CLI commands, docs, templates, examples, Codex skill route updates,
  FlowGuard models, tests, install sync, and local package version sync.

## Non-Goals

- No OCR or automatic PPT/PDF extraction in the first version.
- No copying of large raw test data into the project.
- No external database service.
- No automatic resolution of evidence conflicts.
- No claim that AI-extracted facts are human-confirmed.
- No high-fidelity physical model creation or commercial-tool reverse
  engineering.

## Capabilities

### New Capabilities

- `project-evidence-registry`: project-level records for artifacts, facts,
  binding indexes, context cards, evidence bundles, conflicts, and missing evidence.
- `evidence-scan`: read-only candidate scan for files and artifacts that may
  need registry entries.
- `evidence-gap-check`: required/review/optional gap classification before
  validation or reuse.
- `project-evidence-map`: AI-readable project map showing where files, tests,
  model contexts, bindings, facts, validation reports, and gaps are found.

### Modified Capabilities

- `test-file-contract`: may reference registered artifacts and should surface
  missing registry entries as gaps.
- `model-dataset-validation`: may consume an evidence bundle and model context;
  blocking gaps prevent pass claims.
- `model-library-index`: may reference model context and evidence bundles;
  validated reuse requires current validation evidence and no blocking gaps.
- `physicsguard-skills`: AI workflows must run or explicitly account for
  evidence scan/gap-check before broad validation or reuse claims.

## Impact

- Affected code: new schema/core/loader modules, CLI commands, package exports,
  model validation/library schema extensions, and optional contract artifact
  references.
- Affected artifacts: OpenSpec files, FlowGuard models, templates, examples,
  docs, Codex skills, project policy, tests, installed skill copies, and local
  package metadata.
