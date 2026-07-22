## MODIFIED Requirements

### Requirement: Complete PhysicsGuard maintained-skill inventory
The suite SHALL govern exactly the ten maintained PhysicsGuard skill ids in `unit:physicsguard-family`: the primary dataset-validation skill and nine satellites. Each member MUST retain its own declared semantic checks, evidence subjects, execution owners, and receipts. A suite-level inventory or report MUST be non-authoritative and MUST NOT execute, consume, aggregate, or authorize member receipts.

#### Scenario: One maintained skill is absent
- **WHEN** any declared maintained skill is missing from the same-unit author inventory or its own current contract trio
- **THEN** author maintenance SHALL be blocked for that member and any suite-wide structural report SHALL expose the gap without manufacturing a parent closure

#### Scenario: An extra suite parent claims authority
- **WHEN** a separate maintenance unit, pseudo-skill, parent contract, or replay command attempts to consume or authorize any of the ten member receipts
- **THEN** current author maintenance SHALL fail and the parent authority MUST be removed without a compatibility path

### Requirement: Parent mesh reattachment
The PhysicsGuard suite structure SHALL record all ten members' input/output classes, state or side-effect ownership where applicable, outgoing guarantees, and typed relationships without duplicating child internals. The structure is diagnostic model evidence only: it SHALL contain no child receipt ids, run roots, installation transactions, parent success terminal, or authorization status, and it MUST declare itself non-authoritative.

#### Scenario: Structural summary is current
- **WHEN** all ten members are present exactly once, belong to `unit:physicsguard-family`, retain distinct native owners and declared check inventories, and no parent authority surface exists
- **THEN** the suite structure report SHALL pass as a non-authoritative inventory/ownership check only

#### Scenario: Locally green child is summarized
- **WHEN** one member has local evidence or a current SkillGuard receipt
- **THEN** the structural report MAY identify that member but MUST NOT copy, consume, project, or promote its receipt into family closure

### Requirement: Generic SkillGuard supervision and single current authority
Each maintained target SHALL use only `contract-source.json`, `compiled-contract.json`, and `check-manifest.json` as its SkillGuard author authority plus explicitly referenced PhysicsGuard-native assets. All ten SHALL belong to `unit:physicsguard-family`; no `.flowguard/skillguard-parent` contract or second maintenance unit SHALL remain. The target owns every domain obligation and oracle, while SkillGuard SHALL only compile, execute, and reconcile the target's exact declared inventory.

#### Scenario: Former suite-parent authority remains executable
- **WHEN** a parent contract, parent check manifest, parent contract model, parent test mesh, frozen parent receipt inventory, replay generator, or alternate family success route remains reachable
- **THEN** maintenance SHALL fail until the surface is deleted or converted to a receipt-free non-authoritative structure report

#### Scenario: SkillGuard changes target depth
- **WHEN** SkillGuard adds a failure class, obligation, oracle, fixture, or semantic check not declared by the target skill
- **THEN** the contract SHALL be rejected even if generic compilation succeeds

### Requirement: Validation execution has one owner and reusable receipts
Every affected native and SkillGuard check SHALL have exactly one execution owner inside `unit:physicsguard-family`. Each of the ten members MUST keep its own semantic check ids and evidence subjects. A current immutable terminal-success producer receipt MAY be reused only within that same unit and exact producer/projection identity; no parent, foreign unit, report, or consumer SHALL rerun or authorize the owner command.

#### Scenario: Commands are textually identical
- **WHEN** two member checks invoke the same canonical simulator command over similar inputs but declare different semantic checks, subjects, or owners
- **THEN** each member SHALL retain its independent projection and receipt; command equality alone MUST NOT merge responsibility

#### Scenario: Receipt is projected by a parent
- **WHEN** a parent or report references a member receipt as an authorization condition
- **THEN** the projection SHALL be rejected as cross-owner authority and MUST NOT satisfy any closure

## ADDED Requirements

### Requirement: Canonical PhysicsGuard simulator source and runnable consumer entrypoints
`src/physicsguard/skill_execution_depth.py` and `src/physicsguard/guard_model_contract.py` SHALL be the only editable implementations of the shared execution-depth and guard-model verifier behavior. Maintained skill commands SHALL invoke the current PhysicsGuard package or an exact generated projection, and every retained projection MUST be byte-accounted against that canonical source. Removing the dataset bundle requires current isolated package-install, CLI-route, native-verifier, and representative dataset-command parity evidence.

#### Scenario: Satellite uses the shared simulator
- **WHEN** a satellite skill executes depth or guard-model validation on a supported machine with the declared PhysicsGuard package installed
- **THEN** the canonical package entrypoint SHALL run with the same semantic check id, owner, fixtures, expected result, and claim boundary as before, without a copied editable implementation in the skill

#### Scenario: Simulator package is absent
- **WHEN** a consumer invokes a canonical PhysicsGuard module without the declared package installed
- **THEN** execution SHALL fail visibly with no bundled, aliased, or fallback implementation silently selected

#### Scenario: Dataset bundle is proposed for removal
- **WHEN** isolated-machine evidence is missing, stale, imports the repository source tree, omits a required entrypoint, or observes a different command/result boundary
- **THEN** the bundled dataset runtime SHALL remain as a generated projection and the reduction SHALL be reported blocked

### Requirement: Bounded author evidence lifecycle
SkillGuard owner evidence, compressed streams, run state, receipts, reports, and GC plans SHALL be evidence outputs rather than source or freshness inputs. Each maintenance unit SHALL have one canonical evidence root, explicit current/release pins, and read-only audit/GC planning. Quarantine and purge MUST require separate exact authorization and MUST fail for stale plans, reachable candidates, active-store targets, or failed current/release-pin replay.

#### Scenario: Historical receipts are unreachable
- **WHEN** an evidence audit identifies orphaned or temporary objects that are not current or release-pinned
- **THEN** a read-only GC plan MAY list them with exact identities and byte counts, but ordinary validation SHALL NOT delete, quarantine, or refresh source authority from them

#### Scenario: Parent evidence remains after parent retirement
- **WHEN** the retired suite-parent evidence root or run roots contain historical files
- **THEN** they SHALL have no current authorization role and SHALL remain untouched until a separately authorized quarantine and purge proves all current/release pins replay

