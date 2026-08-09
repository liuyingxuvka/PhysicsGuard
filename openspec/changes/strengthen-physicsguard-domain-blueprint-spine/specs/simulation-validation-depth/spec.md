## ADDED Requirements

### Requirement: Validation is accounted per governed blueprint element
Every broad validation claim SHALL bind the current physical blueprint fingerprint and reconcile the complete governed denominator of physical elements, interfaces, equations, residuals, state updates, parameters, scenarios, files, datasets, observations, tests, oracles, and resources required by the claim. Aggregate counts or a passing subset MUST NOT hide an omitted, unsupported, stale, or unevaluated required member.

#### Scenario: One required equation has no validation binding
- **WHEN** all reported tests pass but one governed equation or state update has no exact native validation evidence
- **THEN** broad validation remains incomplete and identifies that model element

#### Scenario: Required member is excluded without evidence
- **WHEN** a required blueprint member is marked excluded without a current non-contributing disposition and evidence
- **THEN** it remains in the uncovered denominator and the broad claim is blocked

### Requirement: Validation evidence binds physical meaning and current identity
Each governed blueprint element SHALL bind exact simulation or experiment mode, scenario, target revision, initial state where applicable, time basis, parameter source, file and dataset fingerprints, observed signals, native test or execution receipt, oracle, and validity boundary needed for its claim. A passing result from another element, target revision, scenario, or evidence domain MUST NOT substitute for that binding.

#### Scenario: Stateful element lacks initial-state identity
- **WHEN** a stateful physical element is validated without an exact initial state, step or time basis, and trajectory identity
- **THEN** its dynamic validation layer remains non-pass

#### Scenario: Evidence belongs to another model element
- **WHEN** a current-looking receipt names another physical element or obligation
- **THEN** the receipt is rejected for the requested element even if the executed command was identical

### Requirement: Blueprint changes invalidate only exact consumers
A changed blueprint element, relation, semantic, resource, or binding SHALL invalidate the exact validation owners and parent qualifications that consume it. Unchanged evidence MAY be reused only when its subject, inputs, dependencies, toolchain, environment, and blueprint member fingerprints remain exact; ambiguous impact SHALL block reuse rather than trigger automatic run-all.

#### Scenario: Shared lookup resource changes
- **WHEN** a resource fingerprint changes and three elements consume it
- **THEN** those three elements and their dependent parent claims require new evidence while unrelated elements remain reusable

#### Scenario: Validation result has no mapped blueprint owner
- **WHEN** a result cannot be mapped unambiguously to a current blueprint element and obligation
- **THEN** it contributes no coverage and validation closure remains blocked on the mapping gap

### Requirement: Validation receipts report blueprint coverage and depth
The native validation receipt SHALL include the physical blueprint fingerprint, governed and evaluated element identities, exact uncovered dispositions, affected-slice fingerprint when applicable, per-element evidence bindings, first unresolved blueprint gap, deepest validation-supported blueprint layer, and bounded safe claim.

#### Scenario: Aggregate receipt omits element identities
- **WHEN** a receipt reports only totals or an overall pass without the exact governed and evaluated blueprint elements
- **THEN** it cannot support broad validation or blueprint qualification

#### Scenario: All affected validation obligations pass
- **WHEN** every required member in an exact affected slice has current passing evidence and all ancestor qualifications remain current
- **THEN** the receipt may license only that affected validation boundary and does not imply whole-target validation

### Requirement: Object-DNA behavior cases consume native results rather than caller verdicts
For object-DNA readiness, every required behavior case SHALL bind one exact replayable native case result. Each expected output or post-state SHALL map to one native observed value with an explicit tolerance, and terminal status and effects SHALL be compared. Caller-authored `observed_*`, `status`, or case fingerprints SHALL be treated as claims to verify, not proof.

#### Scenario: Claimed observed value is self-consistent but false
- **WHEN** a caller changes an observed model value, marks the case pass, and recomputes all caller-owned fingerprints while the native result is unchanged
- **THEN** validation fails at the exact port-to-native-value mapping

#### Scenario: Native case disappears from a revised request
- **WHEN** an object-DNA behavior case maps to a native case result that is absent from the current replay
- **THEN** validation reports that case as non-pass rather than accepting the caller's stored result
