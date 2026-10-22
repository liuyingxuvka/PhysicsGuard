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

### Requirement: Reproducible heated-tank reference boundary
The heated-tank reference SHALL regenerate its 121-row non-SI CSV and four measured snapshots deterministically, expose six hierarchy blocks under `tank`, and declare heater efficiency as an explicit nameplate variable assumption. Its coupled snapshots SHALL contain eleven measured signals and no hand-computed intermediate quantities.

#### Scenario: The reference is reproduced
- **WHEN** its generator and measurement mapper run on the committed inputs
- **THEN** the CSV and snapshots SHALL match the committed bytes, including current halving at 600 seconds and inflow changing at 900 seconds

#### Scenario: Coupled measurement inputs are insufficient
- **WHEN** the current observed evaluator cannot evaluate residuals without missing connected inputs
- **THEN** the example SHALL expose that limitation and SHALL NOT claim automatic intermediate propagation or fill it with initial guesses

### Requirement: Command exit codes preserve the checked verdict
Single-system and hierarchy audit commands SHALL exit `0` when `audit_pass` is true and `1` when it is false. Compare commands SHALL use `observed_audit_pass`; other checks SHALL retain their native `ok` or status policy. Any command that cannot run because of input, file, schema, missing-required-variable or usage errors SHALL exit `2`. Successful non-judgment inspection, manifest generation and diff commands SHALL exit `0`. These exit codes SHALL NOT change the report JSON.

#### Scenario: The observed pitch feedback is faulty
- **WHEN** hierarchy evaluation or comparison reports the observed audit as false
- **THEN** the command SHALL exit `1` even if the reference solve converged

#### Scenario: An audit file cannot be loaded
- **WHEN** an audit file does not exist or fails YAML/schema validation
- **THEN** the command SHALL exit `2` rather than returning a checked-failure verdict

### Requirement: Connections preserve physical identity
A connection SHALL have default residual scale `1e-6 * max(endpoint variable scales)` without changing either variable scale. An explicit connection scale SHALL be positive and finite and SHALL replace the default. Physically different quantities SHALL require an explicit relation rather than a relaxed identity.

#### Scenario: A pinned heated-tank energy fault is solved
- **WHEN** step 70 measurements are pinned as boundaries in the coarse reference model
- **THEN** the audit SHALL fail with the thermal block worst instead of hiding the mismatch in a loose temperature connection

#### Scenario: The pinned reference is clean
- **WHEN** step 30 measurements are pinned in the same coarse reference model
- **THEN** the audit SHALL pass

#### Scenario: A connection tolerance is invalid
- **WHEN** its scale is zero, negative, infinite or NaN
- **THEN** schema validation SHALL reject the model
