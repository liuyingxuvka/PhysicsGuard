## ADDED Requirements

### Requirement: Closure Gated Localization
PhysicsGuard SHALL provide closure guidance and helper behavior that blocks or scopes localization claims when audits fail, inputs are missing, mappings require review, evidence is stale, checks are skipped, refinements remain, or bug-family follow-ups remain open.

#### Scenario: Closure with missing audit
- **WHEN** closure is run without an audit file
- **THEN** the closure report is partial and includes a next action to provide the audit and observed snapshot.

#### Scenario: Closure with review-required mappings
- **WHEN** closure sees review-required mapping evidence
- **THEN** the closure report is partial or blocked and states that mapping review is required before full localization claims.

### Requirement: Safe Claim Boundary
PhysicsGuard SHALL include `safe_claim` and `unsafe_claim_boundary` in closure output so AI agents know what can and cannot be concluded.

#### Scenario: Closure output generated
- **WHEN** a closure report is generated
- **THEN** it includes a scoped safe claim and an unsafe claim boundary that rejects high-fidelity equivalence, commercial-model recovery, and complete localization beyond the checked audit boundary.
