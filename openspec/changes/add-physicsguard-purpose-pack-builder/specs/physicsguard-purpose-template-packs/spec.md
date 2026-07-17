## ADDED Requirements

### Requirement: PhysicsGuard publishes a current purpose-pack manifest
PhysicsGuard SHALL publish one target-owned manifest whose catalog and template identities bind stable ids, revisions, canonical digests, native family/routes, applicability rules, field ownership, builders, validators, fixtures, generated surfaces, and claim boundaries.

#### Scenario: Current manifest is accepted
- **WHEN** the catalog and every template are structurally complete and their canonical digests match current content
- **THEN** PhysicsGuard accepts the exact manifest identity for selection

#### Scenario: Stale manifest is rejected
- **WHEN** a catalog or template digest, native route, builder, validator, generated surface, or claim boundary is missing or mismatched
- **THEN** PhysicsGuard blocks selection without inferring or loading an older authority

### Requirement: Native route evidence precedes applicability
The builder MUST require an explicit PhysicsGuard family and native route before evaluating target-owned hard predicates and forbidden conditions, and MUST NOT infer applicability from lexical similarity.

#### Scenario: Exact native route can select
- **WHEN** a request supplies the manifest family, an allowed native route, and every hard predicate input
- **THEN** the builder evaluates the complete frozen catalog for that request

#### Scenario: Name resemblance cannot select
- **WHEN** only a purpose phrase resembles a template id but the native route or hard predicates do not match
- **THEN** the candidate is rejected with an explicit reason

### Requirement: Zero one and many candidates terminate deterministically
The builder SHALL produce exactly one of `base_no_match`, `single_selected`, `composed`, `strictly_dominated_selection`, or `ambiguous_template_selection` from the complete eligible set.

#### Scenario: Zero candidates selects approved base
- **WHEN** no domain template is eligible and the manifest declares one current base template
- **THEN** the builder selects that base, records exact no-match evidence, and marks harvest review required

#### Scenario: Zero candidates without base blocks
- **WHEN** no domain template is eligible and the manifest does not declare an approved base
- **THEN** the builder blocks instead of creating a blank work package

#### Scenario: One candidate is selected
- **WHEN** exactly one domain template satisfies every hard rule
- **THEN** the builder returns `single_selected` and a read-only preview may be instantiated

#### Scenario: Unresolved many candidates block
- **WHEN** several candidates neither compose safely nor have one explicit strict dominator
- **THEN** the builder returns `ambiguous_template_selection` and refuses instantiation

### Requirement: Composition preserves dependencies and one owner
The builder SHALL compose only candidates with satisfied fragment dependencies, explicit pairwise compatibility, no declared conflicts, canonical order, and exactly one owner for every generated field and artifact surface.

#### Scenario: Compatible disjoint fragments compose
- **WHEN** every dependency is provided, every pair is compatible, and owned fields/surfaces are disjoint
- **THEN** the builder returns one canonical composition order and field-owner map

#### Scenario: Field collision blocks composition
- **WHEN** two eligible candidates own the same field or artifact surface
- **THEN** the builder returns a blocked ambiguous decision that identifies every conflict

### Requirement: Selection receipts account for every candidate
Every decision SHALL have an immutable fingerprint that binds the request, native route, manifest, every considered candidate and rejection reason, selected ids, composition order, field-owner map, disposition, and no-match/harvest state.

#### Scenario: Unchanged inputs reproduce selection identity
- **WHEN** request, native route, manifest content, and predicates are unchanged
- **THEN** repeated selection produces the same canonical receipt fingerprint

#### Scenario: Changed manifest stales selection
- **WHEN** any request field, route, template revision, digest, predicate input, or catalog identity changes
- **THEN** the prior selection fingerprint cannot authorize instantiation

### Requirement: Instantiation is content-addressed and placeholder-closed
Instantiation SHALL bind exact parameters, native builder id, selected templates, generated artifact content, artifact surfaces, unresolved-placeholder scan, validator ids, and selection fingerprint into a separate immutable instance identity.

#### Scenario: Valid instance is reproducible
- **WHEN** the same current selection and exact parameters are instantiated
- **THEN** the generated artifact and instance fingerprints are identical

#### Scenario: Unresolved placeholder blocks
- **WHEN** any declared input or parameter placeholder remains unresolved
- **THEN** native instance validation fails and no closable instance receipt is emitted

### Requirement: PhysicsGuard-native validation preserves safety boundaries
Native validators MUST verify manifest identity, decision completeness, allowed terminal state, field-owner parity, placeholder closure, explicit assumptions, SI-unit policy, native-check requirement, and claim boundary without claiming physical truth or audit pass.

#### Scenario: Structurally valid instance passes the adapter boundary
- **WHEN** every adapter validator passes for the current selection and artifact
- **THEN** the instance is eligible to be consumed by later PhysicsGuard-native checks

#### Scenario: Rendering does not prove audit success
- **WHEN** a template is successfully selected and rendered
- **THEN** the result still states that physical validity, dataset validity, optimizer convergence, `audit_pass`, installation, and release are unproven

### Requirement: Fixtures cover good and bad decision families
PhysicsGuard SHALL maintain target-owned focused fixtures and tests for current single selection, composition, base no-match, no-base block, ambiguity, field conflict, stale digest, unresolved placeholder, deterministic fingerprints, and manifest reload parity.

#### Scenario: Known-good fixtures pass
- **WHEN** focused tests run current single, composed, and base-no-match fixtures
- **THEN** each reaches its declared success terminal with stable fingerprints

#### Scenario: Known-bad fixtures are rejected
- **WHEN** focused tests run ambiguous, field-conflict, no-base, stale-digest, or unresolved-placeholder fixtures
- **THEN** each fails at its declared guard with no alternate success path

### Requirement: Existing starter-pack ownership remains unchanged
The new adapter MUST NOT rewrite, copy, replace, or silently invoke the existing expanded-starter-pack generator or any existing template asset.

#### Scenario: Adapter runs without existing asset writes
- **WHEN** selection and instantiation execute in focused tests
- **THEN** all outputs remain in memory and existing generator/template paths are unchanged

### Requirement: SkillGuard consumes only a target-owned neutral projection
PhysicsGuard SHALL expose one strict `skillguard.target_template_projection.v1` projection whose candidate inventory, applicability, native route, builder, validator, artifact, fixture, and claim-boundary fields are derived from the current PhysicsGuard manifest and selector before SkillGuard consumption.

#### Scenario: Current projection reproduces native strict dominance
- **WHEN** the native dataset-validation request makes both basic and comprehensive templates applicable
- **THEN** the neutral projection lets the generic selector reproduce the target-authored comprehensive-over-basic strict dominance without lexical scoring

#### Scenario: Stale native authority blocks before projection
- **WHEN** the native manifest digest, request, route, candidate inventory, builder, or validator identity is stale or mismatched
- **THEN** PhysicsGuard refuses to produce a consumable projection and SkillGuard receives no alternate semantic authority
