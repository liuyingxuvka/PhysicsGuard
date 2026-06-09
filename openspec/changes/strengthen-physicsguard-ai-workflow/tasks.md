## 1. Governance And Planning

- [x] 1.1 Upgrade FlowGuard project adoption records to the installed package version and confirm project audit passes.
- [x] 1.2 Create OpenSpec proposal, design, specs, and implementation tasks for the workflow upgrade.
- [x] 1.3 Add a FlowGuard upgrade workflow model covering project adoption, preflight, intake, ledger, skill sync, closure, and validation gates.

## 2. Project Adoption

- [x] 2.1 Add PhysicsGuard project adoption/audit/upgrade helpers.
- [x] 2.2 Add CLI commands for `physicsguard project adopt`, `physicsguard project audit`, and `physicsguard project upgrade`.
- [x] 2.3 Add tests for adopted, missing, and stale project records.
- [x] 2.4 Run adoption command for the current repository and record the generated project manifest/log.

## 3. Preflight And Intake Workflow

- [x] 3.1 Add model-understanding preflight schema helpers, review logic, template, docs, and tests.
- [x] 3.2 Add external-model intake schema helpers, review logic, template, docs, and tests.
- [x] 3.3 Add CLI review commands for preflight and intake artifacts.

## 4. Module Equation Ledger

- [x] 4.1 Add a curated module/equation ledger with representative module-family coverage.
- [x] 4.2 Add a ledger checker script and tests for required fields and file references.
- [x] 4.3 Document the module ledger as navigation evidence, not physical proof.

## 5. Closure And Skill Routes

- [x] 5.1 Strengthen closure helper handling of review-required mappings, stale evidence, skipped checks, refinements, and bug-family follow-ups.
- [x] 5.2 Update the main PhysicsGuard AI debugging skill prompt and README prompt examples.
- [x] 5.3 Add route-oriented subskill folders and docs for project adoption, preflight, signal mapping review, closure, and candidate blueprints.
- [x] 5.4 Sync repository skill folders into local installed Codex skills and verify installed copies match.

## 6. Version, Validation, And Evidence

- [x] 6.1 Bump PhysicsGuard version surfaces and reinstall editable local package.
- [x] 6.2 Run OpenSpec validation, FlowGuard model checks, project audit, module/model ledgers, focused tests, full pytest, CLI smoke checks, installed skill diff checks, and diff hygiene.
- [x] 6.3 Update FlowGuard adoption logs with commands, findings, skipped steps, and next actions.
