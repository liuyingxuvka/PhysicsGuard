## Purpose

Define one current, provider-neutral PhysicsGuard blueprint that expresses the physical semantics, hierarchy, interfaces, inventories, native bindings, and licensed understanding depth of a bounded physical system, experiment, testbench, model, or workflow.

## ADDED Requirements

### Requirement: Exact target identity and independent inventory
Every PhysicsGuard domain blueprint SHALL bind one target-system id, target kind, subject revision, boundary fingerprint, purpose, and claim boundary. Review SHALL also require a frozen `TargetInventoryAuthority` supplied outside the caller-owned blueprint. PhysicsGuard SHALL resolve adapter capability, execution owner, supported schema, tool/version, and execution mode only from its runtime-closed current registry; no caller-supplied registry SHALL enter the loader, API, or CLI. The registry SHALL NOT whitelist target ids, requests, revisions, locators, or content hashes. The current adapter SHALL derive provider, request id, inventory id, target, revision, boundary, raw byte identity, and inventory result from the exact observable target-material snapshot. Raw target material SHALL contain no caller-selected inventory disposition rows, SHALL carry a canonical content-derived material-revision fingerprint, and SHALL derive its request id from that revision. The runtime-derived inventory SHALL be reconciled bidirectionally with both the frozen authority projection and caller blueprint inventory before it can govern coverage; a provider result embedded in the blueprint is observation only and cannot establish the denominator.

#### Scenario: Non-Python target is admitted
- **WHEN** the target is an experiment bench, proprietary model, exchange-format model, or physical workflow with no Python source
- **THEN** the blueprint accepts the target through its declared provider and artifact identities without requiring a Python file or language-specific implementation surface

#### Scenario: Target identity is incomplete
- **WHEN** the subject revision or boundary fingerprint is missing or does not match the supplied target evidence
- **THEN** blueprint review is blocked before any depth or readiness claim is produced

#### Scenario: Discovered inventory member is omitted
- **WHEN** the independent inventory contains an in-boundary item that has no modeled owner and no evidenced terminal disposition
- **THEN** the item remains an exact blueprint gap and whole-boundary qualification is non-pass

#### Scenario: Caller shrinks every self-reported surface together
- **WHEN** a caller removes a child branch, its ports, semantics, bindings, caller inventory members, and embedded provider payload fingerprint while the external target authority still contains those members
- **THEN** the runtime-derived denominator remains unchanged, every omitted member remains uncovered, and review is non-pass

#### Scenario: Caller self-signs every supplied surface
- **WHEN** a caller leaves raw target material unchanged but shrinks the blueprint, caller inventory, authority projection, and embedded provider payload, recomputes every self-fingerprint, and supplies a matching self-created provider registry
- **THEN** the public interface rejects the caller registry, native replay restores the complete raw-material denominator, every omitted member remains uncovered, and review is non-pass

#### Scenario: A different target snapshot is explicitly supplied
- **WHEN** an arbitrary experiment, model, testbench, or non-code workflow supplies different valid raw material with a newly derived material-revision fingerprint and request id
- **THEN** the same registered adapter reviews it as a new snapshot without requiring a fixture-specific target, revision, locator, or hash entry

#### Scenario: Local authority input changed after attestation
- **WHEN** a registered local inventory adapter replays the frozen request and an input byte fingerprint or terminal receipt no longer matches
- **THEN** target-inventory qualification is stale and the caller inventory cannot replace the failed authority

#### Scenario: External authority cannot be replayed
- **WHEN** the authority names an adapter capability or version that the current runtime cannot execute and verify
- **THEN** the authority remains `unverified`, produces a typed gap, and does not license target-inventory qualification

### Requirement: Single-root physical hierarchy and stable ownership
The blueprint SHALL contain one root physical element, stable element identities, explicit parent/child relations, strictly increasing child depth, and exactly one primary semantic owner for every modeled physical behavior, interface, state, and effect. Supporting relations MAY refer to an owner but MUST NOT become a second primary authority.

#### Scenario: Two roots are supplied
- **WHEN** two physical elements have no declared parent inside one blueprint boundary
- **THEN** review is blocked with the exact root identities rather than silently choosing one

#### Scenario: Behavior has duplicate primary owners
- **WHEN** two elements claim primary ownership of the same physical behavior, interface, state, or effect
- **THEN** review is blocked and neither owner is selected by ordering or prose

#### Scenario: Supporting helper is declared
- **WHEN** a unit converter, lookup resource, observer, or helper supports a primary physical owner
- **THEN** the blueprint records the supporting relation without duplicating the primary owner's semantic authority

### Requirement: Typed physical interfaces and compositional refinement
Every modeled element SHALL declare typed input, output, state, and effect interfaces as applicable, including quantity identity, direction, unit, time basis, value shape, validity boundary, and owner. Every parent/child refinement SHALL account for how parent inputs and states feed child inputs, how child outputs and states feed siblings or aggregate into parent outputs and states, and how child assumptions, validity ranges, conserved quantities, guarantees, and effects constrain the parent claim.

#### Scenario: Child input has no source
- **WHEN** a required child input is not mapped from a parent input, parent state, sibling output, or evidenced external source
- **THEN** the refinement is incomplete and the first unresolved interface is reported

#### Scenario: Child output is unconsumed
- **WHEN** a child output is neither consumed by another child nor mapped to a parent output or state nor explicitly dispositioned as non-contributing with evidence
- **THEN** static blueprint qualification is non-pass

#### Scenario: Child state disappears at the parent
- **WHEN** a child owns state that is neither represented in the parent state nor explicitly retained as child-local state
- **THEN** the refinement is incomplete and the state identity remains visible in the gap report

#### Scenario: Interface units conflict
- **WHEN** connected interfaces use incompatible units and no current conversion semantic is bound
- **THEN** review blocks that connection and does not infer a conversion

#### Scenario: Child validity is narrower than the parent claim
- **WHEN** a child assumption or validity range restricts a parent output or guarantee but the restriction is absent from the parent boundary
- **THEN** the parent cannot qualify until its claim is narrowed or the restriction is resolved with current native evidence

### Requirement: Independent physical semantics and exact native bindings
Every qualified physical element SHALL bind source-independent physical semantics for its applicable equations, residuals, constraints, state updates, parameters, assumptions, invariants, validity limits, and protected failures. The same element SHALL bind exact current native model, implementation or workflow, test, dataset, observation, evidence, oracle, and resource identities sufficient for its requested layer. A reference name without a current identity and fingerprint MUST NOT satisfy the binding.

#### Scenario: Element lists only source locations
- **WHEN** an element points to a file or symbol but provides no independently stated physical semantics
- **THEN** source traceability MAY pass while independent-semantics qualification remains incomplete

#### Scenario: Test name exists without exact evidence
- **WHEN** a test is named but its evidence identity, covered physical obligation, or current fingerprint is absent
- **THEN** the model-code-test layer remains non-pass

#### Scenario: Resource changed after review
- **WHEN** a table, calibration, scenario file, testbench profile, external result, or oracle changes after the blueprint receipt
- **THEN** every consuming element and derived parent qualification becomes stale

#### Scenario: Pointwise relation claims stateful behavior
- **WHEN** a pointwise semantic has no state-update and initial-state contract but is used to support a stateful simulation or prediction claim
- **THEN** review blocks the stateful claim while preserving any separately supported pointwise claim

### Requirement: Every behavior has an exact transition-and-oracle contract
Every behavior-bearing physical element SHALL expose one reviewable contract of the form `Input + PreState -> Output + PostState + Effect`. The contract SHALL reference every applicable typed input, pre-state, output, post-state, and effect by stable blueprint identity and SHALL state its preconditions, postconditions, protected failures, termination behavior, and source-independent oracle binding. Stateless behavior SHALL declare empty pre-state and post-state explicitly. Behavior with no externally visible effect SHALL declare an empty effect set explicitly. Source signatures, variable-name lists, implementation locations, test names, or prose summaries MUST NOT substitute for the contract.

#### Scenario: Stateless relation declares its absence of state
- **WHEN** an algebraic physical relation has no retained or next state
- **THEN** its behavior contract carries explicit empty pre-state and post-state sets while preserving its inputs, outputs, effects, failures, and oracle

#### Scenario: State update omits the post-state
- **WHEN** an element declares current state and a state-update semantic but its behavior contract does not identify the resulting post-state
- **THEN** independent physical semantics is non-pass at that exact behavior contract

#### Scenario: Protected failure is present only in implementation
- **WHEN** the implementation can reject an invalid input or boundary but the behavior contract omits that protected failure and its oracle expectation
- **THEN** the element cannot license independent semantics or model-code-test binding

#### Scenario: Oracle is the implementation itself
- **WHEN** the behavior contract names the element's own implementation or `residuals()` method as its sole oracle
- **THEN** the oracle binding is non-independent and resource-oracle qualification remains non-pass

### Requirement: Qualification derives understanding depth
PhysicsGuard SHALL derive, rather than accept from the caller, the status of each ordered physical-blueprint layer and the deepest currently licensed layer. The ordered layers SHALL cover target boundary and inventory, hierarchy, interfaces, independent physical semantics, parent/child refinement, native model-code-test bindings, resource-oracle bindings, and static blueprint closure. The result SHALL expose the first unresolved gap, all blocking gap identities in the requested scope, a blueprint fingerprint, and a bounded safe claim.

#### Scenario: Blueprint self-declares ready
- **WHEN** an input artifact says it is ready but one required layer has a current gap
- **THEN** PhysicsGuard ignores the self-declaration and returns the independently derived non-pass status

#### Scenario: Coarse layers are complete
- **WHEN** boundary, inventory, and hierarchy pass but physical semantics or refinement is incomplete
- **THEN** the report identifies the hierarchy layer as the deepest licensed layer and preserves the later gaps

#### Scenario: Static blueprint qualifies
- **WHEN** every required item and ordered static layer is current and complete inside the declared boundary
- **THEN** the report returns static-blueprint readiness with an exact fingerprint and does not extend the claim to empirical physical equivalence

### Requirement: One canonical blueprint review command
PhysicsGuard SHALL expose one canonical read-only command, `python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty`, for YAML or JSON physical-blueprint review. The authority artifact is required and MUST NOT be inferred from blueprint fields. Provider/request ownership SHALL come only from the runtime-closed current registry, with no public registry option. The command SHALL emit canonical machine-readable output, return non-zero for incomplete, stale, or blocked qualification, and SHALL NOT create an alias, compatibility reader, alternate success owner, or silent fallback.

#### Scenario: Current YAML blueprint is reviewed
- **WHEN** the canonical command receives a valid current YAML blueprint
- **THEN** it emits the same logical report and fingerprint as review of an equivalent canonical JSON blueprint

#### Scenario: Unsupported or retired shape is supplied
- **WHEN** the command receives an unknown or retired blueprint shape
- **THEN** it fails visibly with the detected schema identity and does not reinterpret the input through another path

### Requirement: Declared consistency and object-DNA readiness are distinct
PhysicsGuard SHALL require every physical blueprint to select one understanding target: `declared_consistency` or `object_dna`. Declared consistency SHALL check only the supplied boundary, hierarchy, interfaces, semantics, references, and replay evidence and SHALL report object-DNA readiness as `not_requested`. Object-DNA readiness SHALL additionally require a native-adapter-discovered source census, terminal source-to-model mappings, reverse model coverage, independent semantic facts where claimed, and native case/result alignment. A declared-consistency pass MUST NOT license an object-DNA, reconstruction, complete-understanding, or complete-source-coverage claim.

#### Scenario: Lightweight model is internally coherent
- **WHEN** a provider-neutral target supplies a coherent blueprint but no independently observed source census
- **THEN** declared consistency may pass while object-DNA readiness is `not_requested` or non-pass, and the safe claim names that exact boundary

#### Scenario: Object-DNA target omits an observed source member
- **WHEN** the native adapter observes a source member that has no exact mapping or evidenced terminal disposition
- **THEN** object-DNA readiness is non-pass even when the caller synchronously shrinks its blueprint, inventory, cases, and public fingerprints

#### Scenario: Source mapping points to a missing model object
- **WHEN** a source-to-model mapping names an absent element, port, semantic, behavior case, inventory member, or native binding
- **THEN** current schema validation or canonical review blocks at that exact mapping

#### Scenario: Blueprint equation differs from an independent semantic fact
- **WHEN** a mapped source/oracle fact and the blueprint semantic differ after restricted normalization
- **THEN** independent-physical-semantics closure fails and later object-DNA layers remain unlicensed

#### Scenario: Caller changes a claimed observed value
- **WHEN** a behavior case claims an observed value that differs from its exact replayed native result even after the caller recomputes the case fingerprint
- **THEN** native model-code-test closure fails at that case and value mapping
