## 1. OpenSpec And FlowGuard Governance

- [x] 1.1 Create and validate OpenSpec proposal, design, specs, and tasks for the Test File Contract System.
- [x] 1.2 Upgrade FlowGuard project records to the installed version and rerun project audit.
- [x] 1.3 Add FlowGuard model/checks for test-file contract lifecycle and claim gating.
- [x] 1.4 Update FlowGuard/model-code traceability ledger for new schemas, core checks, CLI, scripts, tests, docs, and skills.

## 2. Schemas And Loaders

- [x] 2.1 Add `DataFileManifest` schema for file identity, format, shape, fields, timing, and extractor evidence.
- [x] 2.2 Add test-bench profile, extractor profile, test-file contract, dataset segment, known defect, and project index schemas.
- [x] 2.3 Add parameter catalog, role matrix, mapping edge, coverage policy, and coverage report schemas.
- [x] 2.4 Add model-binding schema for hierarchy/audit file paths, hashes, PhysicsGuard version, compatible profiles, expected variables, and stale rules.
- [x] 2.5 Add loaders for test-file contract and related artifacts with clear validation errors.

## 3. Core Contract Logic

- [x] 3.1 Implement manifest hashing, field signature hashing, and lightweight CSV/TSV manifest extraction.
- [x] 3.2 Implement contract resolution from shared profiles, manifests, parameter artifacts, model bindings, and policy files.
- [x] 3.3 Implement fail-closed parameter coverage checks: missing catalog entries, missing roles, missing dispositions, invalid mapping targets, excluded-without-reason, stale evidence, and duplicate active mappings.
- [x] 3.4 Implement model-binding checks against hierarchy/model files and hashes.
- [x] 3.5 Implement contract diffing for new/removed/renamed fields, unit changes, timing changes, extractor changes, and model-binding changes.
- [x] 3.6 Ensure coverage checks do not mutate observed values and do not imply physical correctness.

## 4. CLI And Scripts

- [x] 4.1 Add `physicsguard testfile manifest`.
- [x] 4.2 Add `physicsguard testfile inspect`.
- [x] 4.3 Add `physicsguard testfile contract-check`.
- [x] 4.4 Add `physicsguard testfile project-check`.
- [x] 4.5 Add `physicsguard testfile diff`.
- [x] 4.6 Add `physicsguard coverage check`.
- [x] 4.7 Add CI-friendly scripts for manifest extraction, test-file contract checking, parameter coverage checking, and installed skill sync checking.

## 5. Templates, Examples, And Documentation

- [x] 5.1 Add templates for data file manifest, test-bench profile, extractor profile, test-file contract, project index, parameter catalog, role matrix, mapping edges, model binding, and coverage policy.
- [x] 5.2 Add a `examples/testfile_contracts/pump_loop/` fixture with clean, added-field, renamed-field, stale-model, stale-extractor, unclassified, excluded-without-reason, and multi-segment cases.
- [x] 5.3 Add docs for test-file contracts, data-file manifests, parameter role matrix, model binding contracts, schema drift, and optional skill routing.
- [x] 5.4 Update README, AI debugging protocol, hierarchical audit workflow, and external model intake docs.

## 6. Codex Skill Routes And Installed Sync

- [x] 6.1 Add repository skill `skill/physicsguard-test-file-contract-review/SKILL.md`.
- [x] 6.2 Update main `physicsguard-ai-debugging` skill to route test-file workflows conditionally.
- [x] 6.3 Update signal mapping, preflight, audit closure, and agent prompt guidance to account for test-file contract evidence.
- [x] 6.4 Update `.physicsguard/project.yaml` skill routes and policy with `require_test_file_contract_for_test_data`.
- [x] 6.5 Sync repository skills into `%USERPROFILE%/.codex/skills` and verify installed copies match.

## 7. Tests And Validation

- [x] 7.1 Add schema tests for manifests, contracts, coverage artifacts, and model bindings.
- [x] 7.2 Add core tests for manifest extraction, field signatures, stale evidence, role coverage, mapping targets, model binding, and contract diffs.
- [x] 7.3 Add CLI tests for manifest, inspect, contract-check, project-check, diff, and coverage commands.
- [x] 7.4 Add skill sync tests.
- [x] 7.5 Run OpenSpec strict validation, FlowGuard checks, model-code ledger, module/equation ledger, focused tests, full pytest, CLI smoke checks, and installed skill diff checks.

## 8. Versioning, Sync, And Closure

- [x] 8.1 Bump version surfaces if required by the repository release policy for this capability.
- [x] 8.2 Reinstall/sync the local editable package and verify imports resolve to the current workspace.
- [x] 8.3 Record FlowGuard adoption log entries with commands, evidence, skipped checks, and next actions.
- [x] 8.4 Run a final completion audit against all explicit requirements before declaring the goal complete.
