## Context

The existing layers each own a narrow proof:

- test-file contracts prove source fields are cataloged and mapped;
- logical dataset records prove dataset identity without moving large files;
- model-dataset validation checks model/data consistency;
- model libraries index reusable model assets and validation evidence.

The missing layer is a project-level evidence map that AI agents can scan,
check, and use as a common reference before those downstream routes run.

## Design Decisions

### Decision: Project evidence is a common registry, not a database

The first version stores YAML records in the project. It references source
files, raw data, documents, and reports by path or external reference. It does
not copy large raw data or run a database service.

### Decision: Facts are broader than physical parameters

Engineering facts can be physical parameters, equipment identity, vendor/model
numbers, software/configuration versions, time-series references, calibrated
values, derived values, or human overrides.

### Decision: Registry entries may be minimal

AI may register a file with only id, kind, path or external reference,
registered time, status, and review state. Optional details can be filled
later. Known missing source/lineage information must be recorded with a reason
instead of left ambiguous.

### Decision: Gap checks classify severity

Missing evidence is classified as:

- `blocking`: prevents validation pass or validated reuse;
- `review`: allows scoped progress but must remain visible;
- `optional`: useful metadata that does not affect the current claim.

### Decision: Scan is read-only

The scanner reports candidates and missing entries. It does not write registry
records automatically. This keeps AI from silently adding guessed facts or
inventing source evidence.

### Decision: Evidence bundles connect downstream routes

Validation and reuse routes consume evidence bundles that list model contexts,
artifacts, facts, contracts, validation reports, and known gaps. A bundle is the
handoff between project evidence and model-dataset validation/model library.

### Decision: Binding records are projections, not contract copies

The registry stores concise binding records such as source field to model
target or engineering fact to model parameter. The authoritative detailed
mapping remains in the test-file contract or source artifact named by the
binding authority. This prevents duplicate truth while making global project
relationships easy for AI agents to inspect.

### Decision: Project evidence map is an onboarding/report output

The map report is derived from registry records. It summarizes tests, model
contexts, model parts, project/testbench/test-object scope, facts, bindings,
validation reports, coverage, and open gaps. It is a navigation artifact for AI
agents and colleagues, not proof by itself.

## FlowGuard Plan

Add a project-evidence model that covers:

- minimal artifact registration;
- source anchored or missing reason recorded;
- context/fact requirements declared;
- scan candidates reviewed;
- blocking gaps preventing validation/reuse pass;
- conflict records not silently resolved;
- missing required evidence producing missing evidence records.

Key invariants:

- no validation-ready bundle with unresolved blocking gaps;
- no model reuse validated status without validation report references;
- no required fact silently invented when missing;
- no binding record without an authority/source reference;
- no copied raw data requirement for large test files;
- no source-free record without source_missing_reason or review state.

## Risks

- The registry could become too strict and block early exploration. Mitigation:
  allow minimal records and distinguish blocking/review/optional gaps.
- The registry could become a dumping ground. Mitigation: keep required fields
  small, use structured `ai_workspace` only for notes, and add scan/gap reports.
- AI might treat source guesses as facts. Mitigation: require review state,
  source references or missing reasons, and explicit missing evidence records.
