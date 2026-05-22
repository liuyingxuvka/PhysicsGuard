## 1. Traceability Artifacts

- [x] 1.1 Add `.flowguard/model_code_ledger.yaml` covering core PhysicsGuard lifecycle model blocks.
- [x] 1.2 Add `docs/model_code_traceability.md` with agent-facing usage and stale-evidence guidance.

## 2. Validation

- [x] 2.1 Add `scripts/check_model_code_ledger.py` to validate ledger structure, referenced files, and source symbols.
- [x] 2.2 Add pytest coverage for the ledger validator and committed ledger.

## 3. Evidence And Release

- [x] 3.1 Record FlowGuard adoption evidence for the traceability upgrade.
- [x] 3.2 Run FlowGuard checks, ledger checks, pytest, install verification, and release/version consistency checks.
- [x] 3.3 Bump patch version, update changelog, sync installed/local package metadata, push GitHub, and publish the new release.
