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

#### Scenario: Measured inputs determine intermediate values
- **WHEN** the coarse or coupled reference receives its step-30 measured snapshot
- **THEN** observed evaluation SHALL propagate connections and derive supported intermediate values without changing the snapshot or running the reference solver
- **AND** it SHALL pass using remaining checked relations, while reporting producing relations separately in `derived_variables`

#### Scenario: Measured faults remain checks
- **WHEN** the references receive their step-70 measured snapshots with measurement-to-internal components declared first
- **THEN** the coarse reference SHALL expose the thermal-balance failure and the coupled reference SHALL expose the heater-command mismatch
- **AND** producing relations SHALL NOT be counted as checked residuals, block scores or top residuals

### Requirement: Observed derivation preserves evidence boundaries
Observed evaluation SHALL use supported per-residual structural value/control dependencies, not numerical dependency probes or a module-wide read union. Only `equation`, `connection`, `boundary` and `assumption` relations with one unknown MAY derive a finite bounded scalar root. Ambiguous, flat, undefined or unsupported cases SHALL remain unknown; finite sampling SHALL NOT be presented as global nonlinear uniqueness. Observed values and conversion evidence SHALL remain unchanged. Reference `run` and `compare` semantics SHALL remain unchanged.

#### Scenario: Connected measurements disagree
- **WHEN** a connection propagates to an unknown endpoint and another measured endpoint conflicts with that value
- **THEN** propagation SHALL NOT overwrite either observation, and the unconsumed connection SHALL remain a mismatch check

#### Scenario: Partial inputs leave unsupported dependencies
- **WHEN** a residual has unresolved provenance and registered values remain unknown
- **THEN** it SHALL remain unchecked rather than receive guessed inputs or an empty dependency claim
- **AND** a custom residual MAY still receive its native numerical check once every registered value is actually known

#### Scenario: An unrelated channel is missing
- **WHEN** an aggregate balance or fixed-parameter map has all of its own measured inputs and a failing residual, while an unrelated channel remains unknown
- **THEN** observed evaluation SHALL check that residual and report the failure, without requiring the unrelated channel or changing either observation

#### Scenario: No relation remains to check
- **WHEN** every available relation was consumed by derivation or still lacks usable inputs
- **THEN** evaluation SHALL refuse with `no residual can be evaluated without them` rather than report a pass

#### Scenario: Reports distinguish derivation from checks
- **WHEN** observed evaluation runs with intermediate derivation
- **THEN** the full report and block diagnostics SHALL separate `derived_variables`, `checked_residuals` and `unchecked_residuals`
- **AND** the compact summary SHALL list derived names and checked/unchecked counts, with missing required variables judged after derivation
- **AND** strict library evaluation SHALL reject remaining missing values while CLI evaluation MAY skip and list them

#### Scenario: A series requires an intermediate variable
- **WHEN** a series point omits a required variable that native observed evaluation can derive
- **THEN** that variable SHALL satisfy the point's required-variable check without altering the point
- **AND** genuinely unresolved values and all other coverage, gap and adequacy requirements SHALL retain their existing checks

### Requirement: Block trees preserve local and subtree verdicts
Each block's `audit_pass` SHALL include its own verdict and every descendant's verdict. `own_audit_pass` SHALL retain the former local meaning, and `subtree_score` SHALL be the maximum own score across that subtree. The own `score` algorithm, `top_blocks` ordering and overall report `audit_pass` SHALL remain unchanged.

#### Scenario: A detailed block fails
- **WHEN** a child fails while its parent's own checks pass
- **THEN** the parent SHALL report `audit_pass: false` and `own_audit_pass: true`
- **AND** the failing detail SHALL retain its own score and ranking

### Requirement: Refinement links compare actual coarse checks
A child's `refines` SHALL name only components owned directly by its parent. The report SHALL expose `refinement_checks` with `parent`, `coarse_components`, `child_blocks`, `coarse_pass`, `children_pass` and `consistent`, plus `reason` when comparison is unavailable. It SHALL use the coarse components' own checked residuals and existing scoring-role filters rather than an inherited subtree verdict.

#### Scenario: A link names a component outside the parent's ownership
- **WHEN** `refines` names a sibling's component or another component absent from the parent's own list
- **THEN** schema validation SHALL reject the link and name the invalid component

#### Scenario: Detail passes but the coarse relation fails
- **WHEN** all refining children pass and a checked coarse relation fails
- **THEN** consistency SHALL be false and the report SHALL warn `refinement_inconsistent: <parent>`

#### Scenario: The fault is visible only in the detail
- **WHEN** the checked coarse relations pass and a refining child fails
- **THEN** consistency SHALL remain true without changing the child's failed verdict

#### Scenario: There is no coarse check to compare
- **WHEN** every coarse relation was used for derivation, or usable coarse checked evidence is absent
- **THEN** `coarse_pass` and `consistent` SHALL be null with an explicit reason rather than a claim of agreement

### Requirement: Template availability does not execute refinement
Each recommendation SHALL preserve its template ids and give a `template_status` mapping for every id. A same-file block id SHALL resolve as `block`; a file found from the audit directory or its parent, with or without `.yaml`, SHALL resolve as `file`. Missing ids SHALL resolve as `missing` with `refinement_template_missing: <id>`. Lookup SHALL NOT execute templates or imply that a found file passed an audit. Hierarchy inspection SHALL include each block's `refines` links.

#### Scenario: One recommendation names multiple templates
- **WHEN** a recommendation contains both a resolvable id and a missing id
- **THEN** each id SHALL retain its own status and the missing id SHALL produce its warning

### Requirement: Declared device variants preserve nominal evidence
An audit MAY declare `fault_variants` with unique ids, fault or benign kinds, parameter overrides, measurement changes, `rederive` and expected blocks. Each measurement-change entry SHALL use exactly one of scale, offset, set or sign flip. Variant evaluation SHALL copy the nominal data, apply changes, remove the named rederived measurements, derive under the variant device parameters, and audit the result under the nominal model. It SHALL NOT mutate the original specification or observations, optimize their values, or claim time-forward prediction.

#### Scenario: A device parameter changes a measured outcome
- **WHEN** a variant changes a parameter and names an outcome in `rederive`
- **THEN** that outcome SHALL be derived under the changed device before nominal-model evaluation
- **AND** unavailable derivation SHALL remain explicit rather than become a guessed observation

#### Scenario: A valid device case cannot generate its requested measurement
- **WHEN** an otherwise valid edit cannot produce a required rederived measurement
- **THEN** its row SHALL report `not_evaluable` with a reason, null signature and audit verdict, and false detection, neutrality and success flags
- **AND** other cases SHALL remain visible, the aggregate command SHALL exit `1`, and the unavailable case SHALL NOT enter signature groups or observed matches
- **AND** incomplete fault evaluation SHALL NOT produce a complete diagnosis request; schema or unknown-id errors SHALL retain input-error exit `2`
- **AND** explicit diagnosis export SHALL preserve those rows with exit `1` and `diagnose_export.status: not_written` plus reasons in full and compact output, without creating a partial file; fewer than two declared fault hypotheses SHALL remain input error `2`

#### Scenario: A change has multiple operations
- **WHEN** one change entry declares more than one of scale, offset, set or sign flip
- **THEN** schema validation SHALL reject the input

### Requirement: Fault signatures use direct checked evidence
Variant signatures SHALL use blocks with their own checked failures and the sign of each block's largest checked residual under existing role and threshold rules. They SHALL NOT discard a block merely because it has children, prune direct parent/child failures into an antichain, or treat inherited-only, unchecked or producing relations as physical fault evidence.

#### Scenario: A non-leaf thermal block fails directly
- **WHEN** `thermal` has children and its own checked relation fails
- **THEN** the signature SHALL retain `thermal`
- **AND** if both parent and child have direct checked failures, both SHALL remain represented

#### Scenario: A parent fails only through inheritance
- **WHEN** a parent's own checks pass and only a child fails
- **THEN** the signature SHALL include the child's direct failure without adding the inherited-only parent

### Requirement: Detection and discrimination remain separate
Variant reports SHALL distinguish fault detection, benign neutrality and expected-block checks. Identical fault signatures SHALL remain in indistinguishable groups. A group's next signal SHALL be currently unmeasured and selected by device-value separation normalized by variable scale. Observed comparisons SHALL report matching variants by signature equality without claiming the true cause.

#### Scenario: Two faults have the same checked signature
- **WHEN** distinct device variants produce the same direct block-and-sign signature
- **THEN** they SHALL remain indistinguishable and the report SHALL identify an available next signal or an explicit absence
- **AND** identical signatures alone SHALL NOT justify a feature-pair exclusion

#### Scenario: The command writes diagnosis input
- **WHEN** `task-model variants` receives `--write-diagnose`
- **THEN** it SHALL write native diagnosability input with fault-signature intervals using device values plus or minus variable scale times audit threshold
- **AND** `task-model diagnose` SHALL retain its separate discrimination verdict

#### Scenario: Optional composed faults and observations are requested
- **WHEN** `--pairs` or `--observed` is supplied
- **THEN** the report SHALL evaluate the requested fault pairs or compare the observed signature while preserving the original inputs
- **AND** any physical-masking claim SHALL rely on actual composed-device evidence rather than inherited hierarchy failure or expected example labels

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

### Requirement: Assumption inspection accepts the model's hierarchy wrapper
When a file contains top-level `hierarchy` and `system`, `assumptions inspect` SHALL use the native hierarchical loader and inspect its system. Other files SHALL use the existing single-system loader. Card semantics and output format SHALL remain unchanged and inspection SHALL NOT solve.

#### Scenario: An existing system is wrapped in one block
- **WHEN** the parameter-assumption example is wrapped in a one-block hierarchical audit
- **THEN** inspection SHALL exit `0` and list the same card as the unwrapped system

#### Scenario: The heated-tank hierarchy is inspected
- **WHEN** the heated-tank model is passed to `assumptions inspect`
- **THEN** inspection SHALL exit `0` and list the explicit nameplate-efficiency variable assumption


### Requirement: Installed model-writing guidance uses real relations
The installed skill SHALL include `references/model-format.md` and paired audit/observed templates using a real registered physical relation. Guidance SHALL preserve SI units, explicit assumptions, mapping freshness, independent checked residuals and bounded derivation. Its model-tree explanation SHALL include structure, checked counterexamples, known-bad variants, real-signal binding and test-data binding.

#### Scenario: The starter pair is evaluated
- **WHEN** the electrical audit template is evaluated with its three measured voltage, current and power values
- **THEN** the relation SHALL remain an independent check and the paired templates SHALL pass without inventing intermediate measurements

### Requirement: Module and hierarchy descriptions are inspection evidence
`modules list` SHALL list all registered types with their first documentation sentence. `modules describe TYPE` SHALL expose variables with units/bounds/scales/initial guesses, required/optional parameter names, residual names/roles/diagnostic keys/descriptions and validity metadata. Synthetic constructor or external-variable examples SHALL be labeled and SHALL NOT imply physical defaults, solving or device validity.

#### Scenario: A required parameter is unavailable during description
- **WHEN** a module needs synthetic parameters to expose its interface
- **THEN** the description SHALL identify those examples and retain the distinction from actual audit inputs

#### Scenario: A hierarchy is described without solving
- **WHEN** `hierarchy describe AUDIT` is requested
- **THEN** the output SHALL include block levels, parents/children, `refines`, component relations, intra/interblock connections, refinement rules and fault variants
- **AND** `--mermaid` SHALL render declared block subgraphs, component nodes and labeled connections starting with `flowchart TD`, without claiming an audit pass

### Requirement: Compact hierarchy summaries retain assumptions
Compact hierarchy audit summaries SHALL include each assumption card's `id`, `status` and `applied` state without changing card application rules or observed values.

#### Scenario: An unapplied card remains visible
- **WHEN** an audit contains a proposed or rejected card
- **THEN** its compact summary SHALL retain the card with its status and `applied: false`
