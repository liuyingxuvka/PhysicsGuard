## 1. Planning and strict current contract

- [x] 1.1 Reconcile proposal, design, spec, and tasks with the strict re-audit; remove the false 14/14 closure claim.
- [x] 1.2 Replace optional task/purpose/coverage/assumption/unknown/predecessor fields with one strict current `HypothesisPlanSpec` shape.
- [x] 1.3 Add exact observation evidence and frozen-plan binding; remove caller-owned gap transitions.
- [x] 1.4 Add typed six-family native-depth and regression/holdout/predictive receipt contracts.

## 2. Native evaluation and CLI

- [x] 2.1 Derive six gap families and next actions from the current native receipt.
- [x] 2.2 Emit a task-model miss when all hypotheses are contradicted.
- [x] 2.3 Compute resolved/persisted/introduced gaps from base/candidate receipts and derive progress/stall/limit/external terminals.
- [x] 2.4 Require same-task, same-coverage, same-revision, same-candidate typed checks and independent holdout evidence.
- [x] 2.5 Preserve exact rollback, SI-unit, low-fidelity, and no-physical-truth boundaries in CLI receipts.

## 3. Prompts and maintained contracts

- [x] 3.1 Update `scripts/upgrade_purpose_contracts.py` with the strict no-self-report task-local loop and native owner/check language.
- [x] 3.2 Regenerate all ten target prompts, runtime requirements, guard contracts, and author contracts.
- [x] 3.3 Assert all ten skills contain the strict loop and their exact native owner/route binding.
- [x] 3.4 Bind each `depth_profile.model_deepening_check_id` to the target's real strict runtime/negative-test check and reject missing or foreign bindings.

## 4. FlowGuard and test evidence

- [x] 4.1 Add the dedicated `task_local_model_deepening` FlowGuard model and runner.
- [x] 4.2 Expand the regression manifest to cover schema, core, CLI, generator, all ten skills, and focused tests.
- [x] 4.3 Add known-bad tests for legacy/empty plans, stale/wrong receipts, self-reported progress, all-hypotheses-miss, external input, stall, and iteration limit.
- [x] 4.4 Add known-good tests for real gap reduction, exact multi-iteration linkage, independent checks, and closed-task evidence.
- [x] 4.5 Run focused Python tests, generated-contract checks, OpenSpec validation, and affected FlowGuard model checks.

## 5. Version and integration handoff

- [x] 5.1 Update package/version/README/CHANGELOG sources to 0.15.0.
- [x] 5.2 Report changed files, focused receipts, model-authority freshness, and remaining final-integration work to the parent owner.
- [ ] 5.3 Parent integration owner only: freeze all repositories, run final full SkillGuard validation, install, commit, tag, push, and publish. This subtask must not execute those actions.
