## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create proposal, design, specs, and task records for DataBank extraction.
- [x] 1.2 Validate the OpenSpec change.
- [x] 1.3 Add or update FlowGuard model checks for DataBank closure, root, lifecycle, and audit claims.
- [x] 1.4 Record FlowGuard adoption/version evidence after the project upgrade.

## 2. DataBank Skill And Scripts

- [x] 2.1 Add `databank-workflow` skill to the source repository.
- [x] 2.2 Add explicit root layout check/init script.
- [x] 2.3 Strengthen contract checking beyond field presence.
- [x] 2.4 Add provider adapter script.
- [x] 2.5 Add lifecycle transition script with history.
- [x] 2.6 Add one-command audit script.
- [x] 2.7 Add fixture database example.

## 3. PhysicsGuard Boundary Cleanup

- [x] 3.1 Update legacy PhysicsGuard database skills to route total-ledger work to DataBank.
- [x] 3.2 Update PhysicsGuard caller skills so non-database routes do not send total-ledger work to legacy database skills.
- [x] 3.3 Verify installed and source skill copies match.

## 4. Tests And Validation

- [x] 4.1 Add DataBank script tests for root, strict contracts, provider adapter, lifecycle, fixture audit, freshness, closure, navigation, query, and routing cleanup.
- [x] 4.2 Run DataBank unittest suite.
- [x] 4.3 Run fixture one-command audit.
- [x] 4.4 Run skill quick validation.
- [x] 4.5 Run OpenSpec apply/status validation.
- [x] 4.6 Run FlowGuard model regression.

## 5. Sync And Git

- [x] 5.1 Sync source DataBank skill to the installed Codex skills directory.
- [x] 5.2 Sync updated PhysicsGuard skill files to the installed Codex skills directory.
- [x] 5.3 Run installed-skill validation after sync.
- [x] 5.4 Inspect git diff and avoid staging unrelated peer-agent changes.
- [x] 5.5 Create a local git commit for the DataBank extraction work.
