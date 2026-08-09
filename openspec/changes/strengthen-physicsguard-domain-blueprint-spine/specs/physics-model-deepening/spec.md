## ADDED Requirements

### Requirement: Deepening preserves blueprint refinement and licensed depth
Every non-trivial model-deepening iteration SHALL bind the current physical blueprint fingerprint, affected element identities, parent/child refinement contracts, independent target-inventory fingerprint, deepest licensed blueprint layer, and first unresolved blueprint gap. A candidate revision MUST preserve or explicitly revise every affected ancestor, descendant, sibling interface, native binding, assumption, validity boundary, and protected failure before it can count as progress.

#### Scenario: Candidate changes a child interface only
- **WHEN** a candidate changes a child input, output, state, effect, or physical semantic without revising an affected parent refinement or sibling connection
- **THEN** candidate evaluation remains non-terminal and reports the exact unpropagated blueprint relations

#### Scenario: Candidate closes the first gap
- **WHEN** current native evidence closes the first unresolved blueprint gap and no earlier layer becomes stale
- **THEN** the derived deepest licensed layer may advance and the new receipt records the before/after gap and layer identities

#### Scenario: Gap text is renamed
- **WHEN** a caller renames, deletes, or reorders a gap without changing current target inventory, semantics, bindings, or native evidence
- **THEN** no blueprint progress is credited

### Requirement: Model misses revise the living blueprint
When current runtime, experiment, dataset, observation, test, replay, manual, or production evidence contradicts all affected modeled expectations, PhysicsGuard SHALL classify a model miss, preserve the contradictory evidence, invalidate the previous broad-claim blueprint fingerprint, and require a new blueprint revision that accounts for the missing or incorrect physical element, relation, semantic, assumption, validity boundary, or evidence binding. It MUST NOT select an undeclared cause, repeat the same broad claim from the old revision, or alter only the narrative.

#### Scenario: Every declared hypothesis is contradicted
- **WHEN** a current observation matches none of the affected candidate predictions
- **THEN** the iteration creates an exact blueprint-gap revision action and does not declare a physical cause

#### Scenario: Evidence exposes an omitted child
- **WHEN** current evidence demonstrates an in-boundary subsystem or state path absent from the blueprint inventory
- **THEN** the omitted item is added to the unresolved inventory before any candidate can close

### Requirement: Affected deepening remains bounded
Task-local deepening SHALL load and revise the exact affected blueprint slice plus required ancestors, connected siblings, shared resources, and bound evidence. It SHALL NOT require the full blueprint for an ordinary affected task unless an unresolved relation prevents a bounded closure or the requested claim covers the whole target.

#### Scenario: Local parameter issue has a closed affected slice
- **WHEN** one parameter mapping and its dependent relations are fully represented in a current affected slice
- **THEN** deepening may proceed on that slice while unrelated branches remain not selected

#### Scenario: Dependency relation is missing
- **WHEN** the affected traversal reaches an ambiguous or absent relation needed to establish scope
- **THEN** the task remains blocked on that gap rather than silently broadening to run-all or claiming local completeness

### Requirement: Deepening advances an explicit understanding target
Deepening SHALL state whether it is improving declared consistency or object-DNA readiness. It SHALL close the earliest missing obligation for that target and SHALL NOT rename a lightweight pass as deep understanding. Object-DNA deepening proceeds by closing observed-source census, source-to-model mapping, reverse model coverage, independent semantic fact, and native case/result gaps in deterministic order.

#### Scenario: Lightweight model requests deeper understanding
- **WHEN** a declared-consistency blueprint is selected for object-DNA deepening
- **THEN** the next action begins with independent source observation and mapping gaps rather than adding prose detail to the existing model
