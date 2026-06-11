## ADDED Requirements

### Requirement: Project evidence map summarizes project state
PhysicsGuard SHALL provide a Project Evidence Map report derived from the
project evidence registry.

#### Scenario: AI enters an existing project
- **WHEN** an AI agent runs the evidence map command
- **THEN** the report summarizes registered artifacts, tests, model contexts,
  facts, bindings, validation reports, and open gaps.

### Requirement: Map exposes project profile
PhysicsGuard SHALL include project-level basic profile information such as
project name, run period, locations, known unknowns, and source count in the
Project Evidence Map.

#### Scenario: New AI enters a project
- **WHEN** the map is generated
- **THEN** the AI can see whether project name, timing, and locations are known,
  unknown, sourced, or still missing.

### Requirement: Map separates navigation from validation proof
PhysicsGuard SHALL mark the evidence map as a navigation/onboarding artifact
and not as validation proof.

#### Scenario: Map shows a validation report
- **WHEN** the map references validation reports
- **THEN** it does not claim those reports pass unless downstream validation
  evidence says so.

### Requirement: Map reports coverage from bindings and requirements
PhysicsGuard SHALL summarize which model targets and required evidence are
covered by registered bindings and facts, and which remain missing.

#### Scenario: Required binding is missing
- **WHEN** a model context requires a model target binding that no binding
  record covers
- **THEN** the map lists that target under missing required coverage.

### Requirement: Map exposes binding maintenance state
PhysicsGuard SHALL summarize binding expectations, satisfied bindings,
explicit exemptions, and unresolved binding gaps so a new AI can see which
test/physical/model items still need maintenance.

#### Scenario: A field is exempted from model binding
- **WHEN** the registry includes a binding expectation with an exemption reason
- **THEN** the map lists the exemption separately from missing bindings.

### Requirement: Map exposes model and project coverage scope
PhysicsGuard SHALL summarize model parts, project/testbench/test-object scope,
tested model targets, untested model targets, and tested quantities when those
records are available.

#### Scenario: Model has declared parts
- **WHEN** a model context declares model parts and bindings cover some of
  their targets
- **THEN** the map reports which parts and targets are covered by tests and
  which remain uncovered or unknown.
