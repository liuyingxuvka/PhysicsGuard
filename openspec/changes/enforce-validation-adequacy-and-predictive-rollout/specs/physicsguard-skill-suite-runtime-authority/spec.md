## MODIFIED Requirements

### Requirement: Generic SkillGuard supervision and single current authority
Each migrated target SHALL use only `contract-source.json`, `compiled-contract.json`, and `check-manifest.json` as SkillGuard runtime authority plus explicitly referenced PhysicsGuard-native assets. The source contract MUST use the single fixed `native-integrated` identity only to project the exact PhysicsGuard `native_route_owner` and `default_route_id`. Every real route binding MUST use `{binding_id, native_route_id, required_before_closure: true, source}`. Every declared purpose-contract, candidate-binding, known-good, and known-bad check MUST have exactly one `{binding_id, evidence_source, native_check_id, required: true}` binding whose `native_check_id` equals its declared `check_id`. A non-optional `skillguard.depth_profile.v2` MUST repeat the exact native owner, all real native route ids, the complete declared check-id inventory, `native-integrated` mode, `enforced` level, and sole required `enforced` closure; the compiled contract MUST preserve the same profile unchanged. Every covered obligation MUST remain required before that sole closure. `may_define_parallel_execution_route` and `may_define_skillguard_runtime_route` MUST both be false, and the source contract MUST NOT be independently release-eligible. The source and depth profile SHALL NOT contain generic calibration, target classification, Guard-family semantics, optional integration modes, compatibility readers, or an alternate success route.

#### Scenario: One declared proof check lacks a target-native binding
- **WHEN** a purpose-contract, candidate-binding, known-good, or known-bad check is absent from `native_check_bindings`, has `required` false, differs from `native_check_id`, is absent from the depth profile, or is omitted from the sole enforced closure
- **THEN** target compilation, family mesh review, and route projection SHALL remain blocked

#### Scenario: Compiled depth profile drops or changes target identity
- **WHEN** the compiled contract omits the source depth profile or changes its owner, native route ids, native check ids, integration mode, enforcement level, or required closure profile
- **THEN** the target SHALL remain non-current even when all source-only top-level metadata appears correct

#### Scenario: SkillGuard is allowed to define a parallel route
- **WHEN** either parallel-execution or SkillGuard-runtime authority is enabled, or a second route/closure can succeed independently of the PhysicsGuard owner
- **THEN** the source contract SHALL be rejected as non-current

#### Scenario: Former V1 control surface remains executable
- **WHEN** a former manifest, work contract, generic V1 checker, mutable report/ledger, fallback instruction, or alternate success route remains in source or installed skill roots
- **THEN** migration and installation parity SHALL fail

#### Scenario: Narrow retirement receipt omits live V1 residue
- **WHEN** a completion receipt scans only the former work contract and manifest while generic V1 checkers, policies, mutable evidence/reports/ledgers, run outputs, or caches remain
- **THEN** that receipt SHALL be invalid and retirement SHALL remain incomplete

#### Scenario: Retirement history is placed inside current SkillGuard authority
- **WHEN** a V1 retirement receipt or other historical control artifact is stored inside a maintained skill's `.skillguard` directory
- **THEN** current SkillGuard authority and installation SHALL be blocked; retirement history MUST remain in the PhysicsGuard project-level evidence root
