## Purpose

Define deterministic affected-only and reverse-trace behavior over a qualified PhysicsGuard domain blueprint so a change or claim can be followed through physical semantics, hierarchy, artifacts, tests, datasets, and evidence without loading or rerunning unrelated work.

## ADDED Requirements

### Requirement: Affected closure follows typed blueprint relations
Given one or more changed physical elements, interfaces, semantics, artifacts, tests, datasets, evidence members, or resources, PhysicsGuard SHALL derive the smallest closed affected set by traversing only declared current relations. The affected set SHALL include required ancestors, dependent descendants, connected siblings, consuming claims, native bindings, tests, datasets, evidence, oracles, and resources, while reporting each inclusion reason.

#### Scenario: Child output semantics change
- **WHEN** a child output equation or state-update identity changes
- **THEN** the affected set includes that child, every consumer of the output, the owning parent refinement, affected parent claims, and their exact bound validation evidence

#### Scenario: Unrelated branch exists
- **WHEN** another branch has no typed relation to the changed identities
- **THEN** it remains outside the affected set and is reported as not selected rather than implicitly passed or rerun

#### Scenario: Shared resource changes
- **WHEN** one current resource is consumed by several physical elements
- **THEN** every consumer and its dependent qualification is included even when those elements are in different child branches

### Requirement: Reverse trace reaches independent physical grounds
PhysicsGuard SHALL support a reverse trace from a selected model output, diagnostic, validation result, blueprint layer, or project claim to the contributing physical elements, inputs, states, equations, residuals, assumptions, validity limits, artifacts, tests, datasets, observations, evidence, oracles, and provider results. The trace SHALL preserve relation types, direction, identities, fingerprints, and unresolved boundaries. Every reverse projection SHALL expose `trace_status` plus exact terminal input, binding, and resource identities. Finding a graph node alone is not a successful reverse trace.

#### Scenario: Output is traced to evidence
- **WHEN** a user selects one qualified parent output
- **THEN** the reverse trace identifies the child outputs and state, physical semantics, input sources, native bindings, tests, datasets, and evidence that support that output

#### Scenario: Claim crosses an unresolved relation
- **WHEN** the reverse path reaches a missing, ambiguous, stale, unsupported, or provider-owned relation
- **THEN** the trace stops at that exact boundary, reports the gap, and does not invent the missing predecessor

#### Scenario: Seed is a non-terminal aggregate dead end
- **WHEN** a blueprint id, target id, inventory id, aggregate, or other seed reaches no explicit input, binding, or resource terminal
- **THEN** reverse trace returns `trace_non_terminal_dead_end`, a non-pass `trace_status`, and empty terminal identities rather than an empty-chain success

#### Scenario: Source review is incomplete or stale
- **WHEN** the source blueprint review is incomplete, stale, or blocked even though a selected path reaches graph terminals
- **THEN** reverse trace explicitly remains non-pass and preserves the source review boundary

### Requirement: Impact and trace consume exact-current blueprint authority
Every affected or reverse-trace result SHALL bind the source blueprint fingerprint, target subject revision, requested seed identities, selected scope, and relation-set fingerprint. Before graph compilation, indexing, or seed resolution, each query SHALL execute the canonical native reviewer exactly once against the exact blueprint, frozen `TargetInventoryAuthority`, blueprint artifact root, and authority artifact root. The supplied source review SHALL be admitted only when that canonical result is `pass` and the supplied review equals it field-for-field. A result from another blueprint, target revision, relation set, foreign review, stale review, incomplete review, blocked review, or caller-rehashed review MUST be rejected atomically with no selected members.

#### Scenario: Blueprint changed after impact analysis
- **WHEN** a blueprint element or relation changes after an affected result was produced
- **THEN** the result becomes stale and cannot authorize affected-only implementation or validation

#### Scenario: Raw target material changes after source review
- **WHEN** a blueprint review passed but the raw target material bound by its frozen inventory authority changes before an affected or reverse query
- **THEN** both queries re-observe that exact authority, return a stale non-pass projection with no selected members, and do not repair or rewrite the review, authority, or raw material

#### Scenario: Native blueprint binding changes after source review
- **WHEN** a blueprint review passed but one local implementation, test, dataset, evidence, oracle, or resource binding changes before an affected or reverse query
- **THEN** canonical re-review is non-pass, the query returns no selected members, and graph compilation does not run

#### Scenario: Caller recomputes a plausible passing review
- **WHEN** a caller supplies a foreign review or removes genuine gaps from an incomplete or blocked review and recomputes its self-fingerprint as `pass`
- **THEN** canonical re-review and full result comparison reject the supplied review before graph compilation rather than trusting its status or self-hash

#### Scenario: Unknown seed identity is requested
- **WHEN** a requested changed item or trace target is absent from the current qualified blueprint
- **THEN** the operation fails visibly with that identity and does not broaden automatically to the whole project

### Requirement: Ambiguity remains a bounded gap
An ambiguous ownership, connection, provider, or dependency relation SHALL remain an explicit impact gap. PhysicsGuard MUST NOT resolve ambiguity by arbitrary owner selection, graph ordering, fallback discovery, or automatic run-all. A whole-boundary review MAY be requested explicitly as a separate scope.

#### Scenario: Two possible consumers are undeclared
- **WHEN** an output could feed two elements but no current connection relation selects either
- **THEN** both possible relations are reported as unresolved and neither is promoted into the authoritative affected set

#### Scenario: Explicit whole-boundary review is requested
- **WHEN** the caller explicitly selects whole-boundary blueprint qualification rather than affected-only impact
- **THEN** PhysicsGuard evaluates the declared whole inventory while preserving every unknown and unsupported disposition

### Requirement: Compact deterministic projections preserve claim boundaries
Affected and reverse-trace outputs SHALL be deterministic projections of the current blueprint, contain only the selected members plus the exact shared objects needed to interpret them, and preserve the source safe claim and every selected gap. A compact projection MUST NOT become a new authority or imply that omitted members passed.

#### Scenario: Same current seed is projected twice
- **WHEN** the same seed identities, blueprint fingerprint, and scope are supplied twice
- **THEN** PhysicsGuard emits the same logical member set, relation set, and projection fingerprint

#### Scenario: Compact slice omits unrelated members
- **WHEN** a targeted route consumes an affected slice
- **THEN** omitted unrelated members are marked outside the selected scope and are not described as validated

### Requirement: Whole and affected review identities preserve the global denominator
Review identity SHALL include scope, exact selected-element closure, blueprint fingerprint, source-census fingerprint, and inventory denominator fingerprint. Whole and affected reviews of the same blueprint MUST have different review ids and report fingerprints. An affected review SHALL retain the complete global source/inventory denominator and explicitly separate governed affected members from outside-scope members.

#### Scenario: Whole and affected reviews share one blueprint
- **WHEN** the canonical reviewer checks the whole blueprint and then an exact affected element slice
- **THEN** the two review ids differ, both retain the same global denominator fingerprint, and the affected report lists the unselected denominator as outside scope
