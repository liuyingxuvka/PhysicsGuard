## ADDED Requirements

### Requirement: Current retirement authority survives specification archival
PhysicsGuard SHALL keep the former-authority retirement inventory in one project-owned current path outside active and archived OpenSpec change directories. Runtime authority audits, installed-skill parity checks, retirement receipt validation, and parent child-replay owners MUST consume only that path, and every transitive verifier and inventory file MUST be declared in the consuming parent's exact input set.

#### Scenario: Migration change is archived
- **WHEN** the OpenSpec migration change has moved from the active change directory into archive history
- **THEN** the PhysicsGuard runtime-authority audit and receipt-only parent replay pass using the single project-owned retirement inventory without reading archive history or executing child physical proofs

#### Scenario: Current retirement authority is missing
- **WHEN** the project-owned retirement inventory is absent, invalid, or does not cover a maintained PhysicsGuard skill
- **THEN** retirement receipt issuance and parent replay fail visibly with no archive search, compatibility reader, alternate path, or silent fallback

#### Scenario: Transitive retirement input changes
- **WHEN** the current retirement inventory or imported retirement verifier changes
- **THEN** the parent impact plan invalidates every consuming replay owner and requires new exact owner receipts before a current parent closure can be claimed
