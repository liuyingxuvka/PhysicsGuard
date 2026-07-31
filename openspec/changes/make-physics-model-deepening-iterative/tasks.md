## 1. Contract and schemas

- [x] 1.1 Extend the `simulation-validation-depth` spec with iterative task-model closure requirements.
- [x] 1.2 Add purpose, coverage, assumptions, unknowns, iteration, and prior-plan fields to `HypothesisPlanSpec`.
- [x] 1.3 Add observation evidence identity and candidate gap-transition fields.

## 2. Native evaluation

- [x] 2.1 Make hypothesis observation evaluation return open gaps and required next actions.
- [x] 2.2 Make candidate revision evaluation continue when native depth/predictive gaps remain.
- [x] 2.3 Preserve regression, holdout, predictive receipt, rollback, SI-unit, and low-fidelity boundaries.
- [x] 2.4 Update the existing task-model CLI output for terminal reason and next iteration.

## 3. Prompts and tests

- [x] 3.1 Update `scripts/upgrade_purpose_contracts.py` with the no-level iterative rule.
- [x] 3.2 Regenerate all target PhysicsGuard prompts and contracts.
- [x] 3.3 Add shallow-match, stale-identity, no-progress, unexpected-result, and external-signal known-bad tests.
- [x] 3.4 Add multi-iteration candidate-progress and closed-task known-good tests.

## 4. Verification and local projection

- [x] 4.1 Complete affected validation-adequacy and SkillGuard maintenance tasks without overwriting peer evidence.
- [x] 4.2 Run focused PhysicsGuard tests and native depth checks.
- [x] 4.3 Refresh local consumer installation and leave remote GitHub unchanged.
