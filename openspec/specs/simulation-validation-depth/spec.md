# simulation-validation-depth Specification

## Purpose
Bound every model-dataset validation claim to the files, mappings, time and scenario scope, split and residual series that were actually checked, and report adequacy shortfalls as warnings in a compact `depth_summary`.

## Requirements
### Requirement: Declared dataset files are checked
`validation run` SHALL fail when a declared data, schema, profile or series file is missing, and SHALL compare training and holdout files byte for byte.

#### Scenario: A declared series file is missing
- **WHEN** an observed series named in the plan does not exist
- **THEN** the status SHALL be `fail` with the finding `observed_series_missing`

### Requirement: Current mapping gate
Validation MUST read the mapping edges of the referenced test-file contracts and require unit evidence, confidence at or above `depth.mapping_review.minimum_confidence`, and no review flag for every required signal.

#### Scenario: A required signal is uncertain
- **WHEN** a required signal mapping lacks unit evidence or enough confidence
- **THEN** broad validation SHALL be blocked or bounded to unaffected relations

### Requirement: Time and scenario scope
PhysicsGuard SHALL report whether the evidence is a scalar snapshot, a time window or a declared scenario set and MUST NOT silently extrapolate between scopes.

#### Scenario: Snapshot only
- **WHEN** only one timestamp is evaluated
- **THEN** the report SHALL state snapshot scope and SHALL NOT claim time-series behavior

### Requirement: Disjoint calibration and holdout
When calibration is enabled, training and holdout evidence MUST be disjoint.

#### Scenario: The same data under different labels
- **WHEN** the training and holdout files have identical bytes or share case ids
- **THEN** holdout validation SHALL fail with an overlap finding

### Requirement: Residual-series and envelope evidence
Time-series validation SHALL keep pointwise residual results, missing or invalid intervals, physical envelope violations and aggregate statistics.

#### Scenario: A short violation hidden by the average
- **WHEN** the average residual passes but a bounded interval violates a hard physical envelope
- **THEN** the audit pass SHALL be false or explicitly partial

### Requirement: Adequacy floors are warnings
PhysicsGuard SHALL compute per-signal, per-parameter and temporal adequacy and report each shortfall as a warning that limits the status to `partial`; the report SHALL carry the compact `depth_summary` and the full computation under `depth`.

#### Scenario: A time-varying parameter is shallow
- **WHEN** a time-varying parameter has fewer points than its floor
- **THEN** the status SHALL be `partial` and `depth_summary.adequacy.parameters_below_floor` SHALL name the parameter

### Requirement: Manifest paths resolve from the manifest
When `testfile manifest` writes `--out`, `source_file.path` SHALL be relative to that manifest's directory, use forward slashes, and fall back to an absolute path when the source is on a different drive. Content hashes and sizes SHALL remain unchanged.

#### Scenario: Output is in a sibling directory
- **WHEN** the source is `data/run.csv` and the output is `val/manifest.yaml`
- **THEN** the source path SHALL be `../data/run.csv` and resolve to the original data file

#### Scenario: The manifest is printed without an output file
- **WHEN** `--out` is not given
- **THEN** `source_file.path` SHALL retain the supplied source path

### Requirement: Observed mapping staleness is explicit
A hierarchy mapping ledger SHALL preserve `stale_when` as reconfirmation conditions. Those conditions alone SHALL NOT create `stale_mapping`. Only `mapping_status` equal to `stale`, case-insensitively, SHALL mark the mapping stale.

#### Scenario: A clean mapping records a future review condition
- **WHEN** a high-confidence clean pitch mapping records `stale_when: [controller retuned]` without stale status
- **THEN** the condition SHALL remain in the ledger and SHALL NOT create a mapping issue or signal-mapping followup

#### Scenario: The reconfirmation condition has occurred
- **WHEN** the mapping status is `stale` or a case variant of it
- **THEN** the row SHALL include `stale_mapping` and a mapping-review followup
