## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create proposal, design, specs, and task records for project evidence registry, scan, and gap checking.
- [x] 1.2 Validate the OpenSpec change with strict validation.
- [x] 1.3 Add FlowGuard models/checks for registry, scan, and gap-check evidence gates.
- [x] 1.4 Update model-code traceability and adoption logs.

## 2. Project Evidence Schemas

- [x] 2.1 Add project evidence registry and project profile schemas.
- [x] 2.2 Add artifact, engineering fact, context card, evidence bundle, conflict, and missing evidence schemas.
- [x] 2.3 Add evidence binding, binding expectation, and project evidence map report schemas.
- [x] 2.4 Add loader support.

## 3. Core Checks And Scanning

- [x] 3.1 Implement project evidence registry checks.
- [x] 3.2 Implement read-only project evidence candidate scan.
- [x] 3.3 Implement evidence gap checks with blocking/review/optional classification, binding-completeness audit, and project-profile completeness audit.
- [x] 3.4 Implement evidence bundle checks.
- [x] 3.5 Implement project evidence map generation for AI onboarding, including project profile and model/test binding maintenance state.

## 4. CLI And Existing Route Integration

- [x] 4.1 Add `evidence check`, `evidence scan`, `evidence gap-check`, `evidence bundle-check`, and `evidence map` CLI commands.
- [x] 4.2 Allow model-dataset validation plans to reference an evidence bundle and block pass when blocking gaps remain.
- [x] 4.3 Allow model library entries to reference model context and evidence bundle records.
- [x] 4.4 Allow test-file contracts to reference registered artifact ids.

## 5. Skills, Policy, Docs, Templates, Examples

- [x] 5.1 Add `physicsguard-project-evidence-registry` skill.
- [x] 5.2 Update test-file, model-dataset validation, model-library, AI debugging, and audit-closure skills.
- [x] 5.3 Update `.physicsguard/project.yaml` routes and policies.
- [x] 5.4 Add docs, templates, project-map templates, and pump-loop examples.

## 6. Tests And Validation

- [x] 6.1 Add schema/core/CLI tests for registry, scan, gap-check, bundle checks, binding index, binding expectations, and project map.
- [x] 6.2 Add integration tests for model-validation blocking gaps and model-library evidence references.
- [x] 6.3 Run OpenSpec, FlowGuard, ledger, CLI smoke, focused tests, and full pytest.
- [x] 6.4 Sync repository skills to installed Codex skills and verify matching hashes.
- [x] 6.5 Reinstall/sync local editable package if needed and verify imports resolve to the workspace.
- [x] 6.6 Perform final completion audit against the original objective.
