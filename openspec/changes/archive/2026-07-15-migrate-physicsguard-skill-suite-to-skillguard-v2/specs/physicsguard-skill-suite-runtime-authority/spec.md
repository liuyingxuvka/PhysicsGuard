## ADDED Requirements

### Requirement: Complete PhysicsGuard maintained-skill inventory
The suite SHALL govern exactly the ten maintained PhysicsGuard skill ids declared by this change: the primary dataset-validation skill and nine satellites. Parent closure MUST consume one current child result for every id.

#### Scenario: One maintained skill is absent
- **WHEN** any declared maintained skill lacks a current V2 child receipt or parent reattachment row
- **THEN** family-wide PhysicsGuard skill-suite closure SHALL be blocked

### Requirement: Existing native route remains authoritative
Each maintained skill MUST retain its existing PhysicsGuard domain route and SHALL declare exactly one route-specific PhysicsGuard native owner; SkillGuard MUST NOT create an alternate physical-analysis success path.

#### Scenario: Generic SkillGuard command replaces a native check
- **WHEN** a contract closes from a generic command without the maintained skill's PhysicsGuard-native receipt
- **THEN** execution depth and closure SHALL remain non-pass

### Requirement: Exact current-run target identity
Every enforced receipt MUST bind the exact target skill, native owner, native route/check, run, target obligations, evidence domain, target-input inventory/fingerprint, and immutable native receipt id/hash/ref.

#### Scenario: Receipt belongs to another maintained skill
- **WHEN** a structurally valid receipt names a different PhysicsGuard skill or native owner
- **THEN** the target run SHALL reject it before depth evaluation

### Requirement: Route-specific deep execution
Each maintained skill SHALL expose complete relevant native object and obligation inventories. Data/time-bearing routes MUST enforce per-object target-owned dynamic floors, temporal distribution, maximum-hole limits, and stricter project policies; inventory/decision routes MUST reconcile declared, discovered, required, excluded, evaluated, and unresolved items without mechanical expansion.

#### Scenario: Large time series uses two points
- **WHEN** a governed time-varying parameter or signal contains a large eligible series but only one or two points are evaluated
- **THEN** that object SHALL remain shallow and no aggregate evidence from other objects may hide it

#### Scenario: Critical object is hidden as an exclusion
- **WHEN** a required or critical object is moved into exclusions, or an exclusion lacks current hashed evidence and a closed non-contributing disposition
- **THEN** broad depth SHALL be blocked and the excluded object SHALL contribute no coverage, validation, or claim evidence

#### Scenario: Duplicate timestamps inflate a temporal sample
- **WHEN** several point ids for one governed series resolve to the same time coordinate
- **THEN** duplicate coordinates SHALL NOT count toward the dynamic floor, temporal strata, or maximum-gap proof

#### Scenario: Receipt keeps only a temporal count
- **WHEN** a time-varying object reports only available/evaluated counts but omits the exact available point identities, selected point identities and coordinates, and their content fingerprints
- **THEN** the receipt SHALL be insufficient for broad depth because a later verifier cannot reproduce the per-object floor, strata, or maximum-gap decision

#### Scenario: One critical inventory item is omitted
- **WHEN** a project registry, mapping set, contract field, model asset, preflight boundary, blueprint obligation, or closure blocker is critical but unevaluated
- **THEN** the maintained skill's broad closure SHALL remain blocked or explicitly bounded

### Requirement: PhysicsGuard-owned purpose declaration precedes candidate construction
Every governed PhysicsGuard model or route MUST freeze a target-owned guard-model contract before candidate construction. The contract MUST declare what failure classes the model prevents, the physical/evidence boundary, the native oracle and predicate, expected finding code, proof strength and known limit, and the bounded claim. This chain has no selectable mode.

#### Scenario: Candidate exists before its purpose contract
- **WHEN** a candidate model is authored before the exact purpose, universe, oracle, and prevented-failure identities are frozen
- **THEN** the candidate SHALL be invalid for closure and MUST be rebuilt or rebound after a valid declaration

### Requirement: Every declared prevented failure is proven natively
Every governed target MUST provide one target-owned known-good proof covering all required obligations and one known-bad proof for every declared prevented failure class. Every known-bad MUST execute the PhysicsGuard-native evaluator, block, identify the exact failure class, and emit its declared finding code.

#### Scenario: Generic fixture relabeled as target evidence
- **WHEN** a proof contains generic obligations or only changes an expected-status label without executing the target's native evaluator
- **THEN** proof authorization SHALL fail

#### Scenario: One declared failure has no bad proof
- **WHEN** a guard-model contract declares a prevented failure class but no exact native known-bad case proves it is blocked
- **THEN** the model SHALL remain non-pass even if all other cases pass

#### Scenario: SkillGuard decides the physical meaning
- **WHEN** a SkillGuard field, target classification, integration mode, or generic calibration policy supplies the failure class or oracle instead of PhysicsGuard
- **THEN** the contract SHALL be rejected as non-current

### Requirement: Fixture and production evidence domains are disjoint
Known-good and known-bad capability proofs SHALL prove target checker behavior only and MUST NOT satisfy scheduled-project closure. Project closure MUST consume a current target-native receipt bound to the exact installation and project evidence identities; an identity supplied only through the generic supervisor request SHALL NOT satisfy the native provider. Each target check SHALL read the exact target-owned execution package and referenced evidence; a missing, extra, outside-root, stale, or hash-mismatched file SHALL block before closure.

#### Scenario: Fixture receipt is supplied to production closure
- **WHEN** a valid positive fixture receipt is referenced by a scheduled-production run
- **THEN** closure SHALL reject the evidence-domain mismatch

#### Scenario: Installation identity is attached only to the supervisor request
- **WHEN** a maintained-skill execution package omits `scheduled_production_identity` while the generic run request carries identity-shaped fields
- **THEN** the target-owned provider SHALL block as missing production identity and SHALL NOT copy those request fields into native evidence

#### Scenario: Fixture is relabeled with every production-shaped field
- **WHEN** a calibration package is copied and supplied with the correct domain, `input_origin`, run identity, and scheduled installation identity, or its references resolve only to generic placeholder files
- **THEN** production SHALL still block because the scheduled constructor did not independently discover the current project artifact/object/timepoint universe and the referenced files do not carry exact target/run/route-bound semantic ids and range anchors

#### Scenario: Every self-reported universe is shrunk together
- **WHEN** a production-shaped package removes current project artifacts, semantic catalog rows, parameters, series, or timepoints from all of its declared/discovered/evaluated lists while retaining current files and matching hashes
- **THEN** the adapter SHALL independently re-discover the canonical current project root and SHALL block the package on authoritative-universe mismatch

### Requirement: Parent mesh reattachment
The PhysicsGuard parent suite SHALL record child input/output classes, state or side-effect ownership where applicable, outgoing guarantees, current child evidence ids, and affected-sibling relationships without duplicating child internals.

#### Scenario: Locally green child is not reattached
- **WHEN** one migrated maintained skill passes locally but the parent consumes no current child evidence id or an older id
- **THEN** parent suite confidence SHALL remain blocked

#### Scenario: Primary shared-depth sibling is stale
- **WHEN** all nine satellites are current but `physicsguard-model-dataset-validation` lacks a current exact V2 receipt or its receipt is relabeled under the parent owner
- **THEN** PhysicsGuard family closure SHALL remain blocked

### Requirement: Generic SkillGuard supervision and single current authority
Each migrated target SHALL use only `contract-source.json`, `compiled-contract.json`, and `check-manifest.json` as SkillGuard runtime authority plus explicitly referenced PhysicsGuard-native assets. The source contract SHALL declare only checks, owners, dependencies, inputs, obligations, and closure; it SHALL NOT contain `depth_profile`, `calibration`, `integration_mode`, target classification, Guard-family semantics, or an alternate success route.

#### Scenario: Former V1 control surface remains executable
- **WHEN** a former manifest, work contract, generic V1 checker, mutable report/ledger, fallback instruction, or alternate success route remains in source or installed skill roots
- **THEN** migration and installation parity SHALL fail

#### Scenario: Narrow retirement receipt omits live V1 residue
- **WHEN** a completion receipt scans only the former work contract and manifest while generic V1 checkers, policies, mutable evidence/reports/ledgers, run outputs, or caches remain
- **THEN** that receipt SHALL be invalid and retirement SHALL remain incomplete

#### Scenario: Retirement history is placed inside current SkillGuard authority
- **WHEN** a V1 retirement receipt or other historical control artifact is stored inside a maintained skill's `.skillguard` directory
- **THEN** current SkillGuard authority and installation SHALL be blocked; retirement history MUST remain in the PhysicsGuard project-level evidence root

### Requirement: Transactional installation and currentness replay
The ten migrated source skills and installed copies MUST be byte-accounted in governed installation transactions, and issuance, native terminal closure, parent mesh consumption, and replay MUST verify the exact current installation receipt for every child together with the one current SkillGuard installation authority.

#### Scenario: Installed prompt or contract changes after receipt
- **WHEN** any installed governed file changes after installation receipt issuance
- **THEN** the prior production closure SHALL become stale and MUST NOT be reused

### Requirement: Validation execution has one owner and reusable receipts
Every affected native, calibration, mesh, installation, and parent check SHALL have exactly one execution owner. A consumer SHALL verify and project a current terminal-success receipt and MUST NOT rerun the owner command or treat `--resume` as a read-only audit.

#### Scenario: Prompt requests blanket rerun after any change
- **WHEN** a maintained skill instruction tells an AI to rerun SkillGuard broadly after every entrypoint, route, evidence, or closure change without affected-input analysis
- **THEN** that instruction SHALL be invalid and SHALL be replaced by exact affected-check ownership, receipt reuse, and one frozen final full gate
