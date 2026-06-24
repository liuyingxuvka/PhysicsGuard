## 1. OpenSpec and FlowGuard Setup

- [x] 1.1 Create proposal, design, specs, and tasks for the evidence mesh upgrade.
- [x] 1.2 Run OpenSpec strict validation for the new change.
- [x] 1.3 Upgrade the local FlowGuard project record to the installed FlowGuard version and rerun project audit.

## 2. Evidence Mesh Runtime

- [x] 2.1 Add evidence mesh schema models for parent-child mesh, model-code-test alignment, contract-exhaustion cases, test mesh freshness, field lifecycle rows, risk ledger rows, and review reports.
- [x] 2.2 Add the evidence mesh checker that validates receipt freshness, parent consumption, route coverage, blocking findings, summary, and safe claim boundaries.
- [x] 2.3 Add YAML loading and public lazy exports for evidence mesh checks.
- [x] 2.4 Add `physicsguard evidence mesh-check` CLI support.

## 3. Project Closure Integration

- [x] 3.1 Extend project closure plan required checks and inputs for evidence mesh reports.
- [x] 3.2 Make project closure consume evidence mesh reports and block required strong claims when reports fail, are skipped, or are stale.
- [x] 3.3 Update closure report summary and unsafe claim boundary to name evidence mesh evidence.

## 4. Examples and Documentation

- [x] 4.1 Add a pump-loop evidence mesh fixture and update its project closure plan to require it.
- [x] 4.2 Document the evidence mesh workflow, authoring fields, claim boundaries, and CLI usage.
- [x] 4.3 Update README, model-code traceability guidance, and project closure docs.
- [x] 4.4 Update version anchors and changelog for the new release.

## 5. FlowGuard and Traceability

- [x] 5.1 Add a FlowGuard model for the evidence mesh route.
- [x] 5.2 Add a FlowGuard run script for evidence mesh route checks.
- [x] 5.3 Update the model-code ledger with the new model, code, tests, examples, commands, boundaries, and stale conditions.
- [x] 5.4 Append adoption log evidence for the upgrade.

## 6. Tests and Validation

- [x] 6.1 Add schema/core/CLI tests for valid and invalid evidence mesh cases.
- [x] 6.2 Add project closure tests for required evidence mesh pass, missing, and blocking cases.
- [x] 6.3 Run focused tests for evidence mesh, project closure, CLI, model-code ledger, and version consistency.
- [x] 6.4 Run all current `.flowguard` checks including the new evidence mesh route.
- [x] 6.5 Run ledgers, installed skill sync, editable install, project audit, project closure, and full pytest.

## 7. Publish

- [x] 7.1 Verify repository privacy/release boundary and default branch protection.
- [x] 7.2 Commit the scoped change without reverting or absorbing unrelated peer edits.
- [x] 7.3 Push the branch/mainline and create a new source-only GitHub release.
- [x] 7.4 Confirm README version, runtime version, git tag, and GitHub Release agree.
