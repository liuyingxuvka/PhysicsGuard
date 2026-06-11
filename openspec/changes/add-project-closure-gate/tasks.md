## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Validate proposal, design, specs, and task records for project closure.
- [x] 1.2 Add a FlowGuard model and runner for project closure states, gates, and skipped/stale evidence hazards.
- [x] 1.3 Update FlowGuard traceability/adoption records for the new closure route.

## 2. Schema And Core Implementation

- [x] 2.1 Add project closure plan and report schemas.
- [x] 2.2 Add loader support for closure plans.
- [x] 2.3 Implement project closure aggregation over project audit, evidence check, gap-check, map, contracts, validation, model-library, and optional hierarchy closure inputs.
- [x] 2.4 Add safe claim, unsafe claim boundary, next action, skipped check, and status derivation logic.

## 3. CLI, Templates, Docs

- [x] 3.1 Add `physicsguard project closure PLAN.yaml --pretty`.
- [x] 3.2 Add project closure plan/report templates and pump-loop example plan.
- [x] 3.3 Update README, docs, CHANGELOG, VERSION, and package metadata for the closure gate release.

## 4. Skill Prompt Updates

- [x] 4.1 Strengthen audit-closure, project-evidence, project-adoption, AI-debugging, model-dataset-validation, model-library, and test-file-contract skills with project closure claim gates.
- [x] 4.2 Sync repository skills into installed Codex skills and verify hashes match.

## 5. Tests And Validation

- [x] 5.1 Add schema/core/CLI tests for clean pass, blocking evidence gap, review-only downgrade, map-not-proof, skipped required checks, validation evidence, and model-library evidence.
- [x] 5.2 Run OpenSpec strict validation.
- [x] 5.3 Run FlowGuard project closure checks and existing affected FlowGuard checks.
- [x] 5.4 Run focused pytest and full pytest as practical.
- [x] 5.5 Run project audit, import/version checks, installed skill sync check, and final git status review.
