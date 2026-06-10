## ADDED Requirements

### Requirement: Script-generated data file manifest
PhysicsGuard SHALL provide a Data File Manifest format that records data-file identity, format, field inventory, shape, time basis, sampling evidence, and extractor identity.

#### Scenario: Manifest records file shape
- **WHEN** a manifest is generated for a supported test data file
- **THEN** it records file path, content hash, size, format kind, field count, row count or sample count, field names, data types, units when available, and generation time.

#### Scenario: Manifest records time-series evidence
- **WHEN** a manifest describes time-series data
- **THEN** it records the time column or time basis, start time, end time, duration, nominal sampling frequency when inferable, sampling mode, and continuity or gap status.

#### Scenario: Manifest records extractor provenance
- **WHEN** a manifest is generated
- **THEN** it records the extractor script path or id, extractor version when available, script hash, config hash when available, and generated-at timestamp.

### Requirement: Manifest facts are produced by deterministic tooling
PhysicsGuard SHALL treat file counts, field names, row counts, time ranges, and sampling facts as generated evidence rather than AI-counted narrative.

#### Scenario: Contract uses manifest counts
- **WHEN** a contract check reports field count, sample count, or time range
- **THEN** those facts come from the manifest or the extractor output, not from AI text.

### Requirement: Manifest freshness is checkable
PhysicsGuard SHALL detect stale manifests when bound file, extractor, or configuration evidence changes.

#### Scenario: Source file changed
- **WHEN** the manifest content hash no longer matches the source file hash expected by a contract
- **THEN** the contract check fails with stale manifest evidence.

#### Scenario: Extractor changed
- **WHEN** the extractor script hash or config hash differs from the contract binding
- **THEN** the contract check fails or returns partial according to policy, and broad analysis claims are blocked.
