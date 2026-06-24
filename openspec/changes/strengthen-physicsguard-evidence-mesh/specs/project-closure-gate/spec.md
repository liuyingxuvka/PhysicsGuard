## MODIFIED Requirements

### Requirement: Project closure report aggregates route evidence
PhysicsGuard SHALL provide a project closure report that aggregates project audit, evidence registry checks, evidence gap checks, evidence map generation, test-file contracts, model-dataset validation, model-library checks, optional hierarchy closure inputs, and optional required evidence-mesh reports.

#### Scenario: Clean project evidence, validation, and evidence mesh pass
- **WHEN** all required route checks pass for the declared claim scope and every required evidence mesh report passes
- **THEN** the closure report status is `passed`, `ok` is true, and the safe claim is scoped to the checked boundary.

#### Scenario: Required evidence mesh is missing
- **WHEN** the closure plan requires evidence mesh checks but provides no evidence mesh file
- **THEN** the closure report status is `blocked` and includes a skipped required check finding.

#### Scenario: Required evidence mesh blocks
- **WHEN** a required evidence mesh report has blocking findings
- **THEN** the closure report status is `blocked` and includes evidence-mesh findings.

### Requirement: Evidence maps are navigation, not validation proof
PhysicsGuard SHALL treat project evidence maps as AI onboarding/navigation evidence only, not as validation proof or evidence-mesh closure proof.

#### Scenario: Evidence map succeeds while evidence mesh fails
- **WHEN** evidence map generation succeeds but a required evidence mesh report has blocking findings
- **THEN** the closure report is not `passed`.
