## MODIFIED Requirements

### Requirement: Existing native route remains authoritative
Each maintained skill MUST retain its existing PhysicsGuard domain route and SHALL declare exactly one route-specific PhysicsGuard native owner. All ten skills SHALL remain independent direct routes; `physicsguard-ai-debugging` SHALL act only as the mixed/unclear debugging coordinator and SHALL NOT become a parent, wrapper, alias, fallback, or prerequisite for another skill. SkillGuard and prompt-loading machinery MUST NOT create an alternate physical-analysis success path.

#### Scenario: Generic SkillGuard command replaces a native check
- **WHEN** a contract closes from a generic command without the maintained skill's PhysicsGuard-native receipt
- **THEN** execution depth and closure SHALL remain non-pass

#### Scenario: Broad route captures a clear satellite request
- **WHEN** exactly one satellite capsule accepts the request and the broad AI-debugging route is selected first or exclusively
- **THEN** route validation SHALL fail and the satellite SHALL remain the direct owner

#### Scenario: Prompt contraction changes native ownership
- **WHEN** a compact prompt, route capsule, reference split, or UI metadata changes a skill's current native owner, native route, declared checks, or bounded claim
- **THEN** the target contract and suite validation SHALL block

## ADDED Requirements

### Requirement: Generated consumer references share current author authority
The ten native depth/purpose references, validated-template-pack references, route capsules, and compact entry prompts SHALL be generated or projected from the current author-side source identities declared for this change. Generated references SHALL remain target-owned consumer material and SHALL contain no SkillGuard receipt, run, maintenance-unit, or private evidence authority.

#### Scenario: Generated reference drifts from generator inputs
- **WHEN** a purpose, prevented failure, native route identity, package version, deepening terminal, or template-pack rule differs from its current generation source
- **THEN** the affected skill's source contract and consumer projection SHALL be stale

#### Scenario: Consumer reference exposes author authority
- **WHEN** a generated consumer reference contains SkillGuard run state, receipt identity, maintenance-unit identity, or private evidence paths
- **THEN** consumer-distribution validation SHALL block

