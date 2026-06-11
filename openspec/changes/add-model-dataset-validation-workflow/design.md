## Context

The existing test-file contract system has the right first boundary: it proves
that concrete file fields were cataloged, classified, and mapped with evidence.
It does not prove that the bound low-fidelity PhysicsGuard model is physically
consistent with those data.

This design keeps the existing route intact and adds adjacent layers instead of
turning the contract into an all-purpose validation database.

## Design Decisions

### Decision: Keep non-identical file contracts symmetric

Every concrete test file keeps a generated file representation manifest. If two
files are byte-identical or canonically equivalent, they may share a logical
dataset or contract. If data values differ, each file gets its own logical
dataset and contract. Shared testbench profiles, model bindings, coverage
policies, and mapping templates reduce duplication.

Alternative considered: shared base contract plus delta contracts. Rejected
because it implies one file is authoritative and other files are secondary.

### Decision: Store raw data references, not raw data

Large raw datasets remain wherever the user keeps them. PhysicsGuard stores
paths, hashes, extractor evidence, signatures, and relation metadata in the
project.

### Decision: Validation starts with no-fit checks

Model-dataset validation first runs direct observed evaluation, physical
envelope checks, and redundant-sensor consistency checks. Calibration is
optional and cannot be the first or only validation evidence.

### Decision: First calibration backend is conservative

The first version supports `none`, `bounded_least_squares`, and optionally a
coarse-start least-squares mode. Adam and SPSA are future backends. Calibration
can adjust only explicit bounded calibration parameters, never observed values.

### Decision: Confidence feedback is report evidence

Contracts keep initial mapping and measurement confidence. Validation reports
add post-validation confidence updates, but they do not silently mutate source
data or rewrite contracts.

### Decision: Model library stores evidence references

The model library indexes model files, hashes, validation reports, known limits,
and reuse status. It does not store large raw data or claim universal validity.

## FlowGuard Plan

Add models for:

- dataset identity and symmetric relation handling;
- model-dataset validation gates, including no-fit direct validation,
  conservative calibration, holdout validation, and confidence updates;
- model library evidence indexing and stale validation boundaries.

Key invariants:

- no broad validation without passing test-file contracts;
- no validation pass from optimizer convergence alone;
- no calibration of observed values;
- no calibration parameter without finite bounds, initial value, and scale;
- no model library validated status without a validation report.

## Risks

- Calibration could hide mapping or sensor problems. Mitigation: direct no-fit
  validation first, holdout validation after calibration, and parameter-at-bound
  warnings.
- Relation indexes could become implicit parent/child contracts. Mitigation:
  keep relations project-level and symmetric.
- Model library entries could be mistaken for physical proof. Mitigation: store
  claim boundaries and validation status per report.
