## Why

PhysicsGuard can validate low-fidelity relations against scalar snapshots, but a few current points must not be allowed to imply temporal, scenario, or general model understanding. Dataset identity, time coverage, mapping, holdout separation, and physical envelope evidence must be explicit in every broad validation claim.

## What Changes

- Add dataset, signal-mapping, time-window, scenario, split/holdout, residual-series, physical-envelope, and report-identity receipts.
- Block snapshot evidence from being projected into time-series or cross-scenario confidence.
- Require train/holdout identity separation and current mapping review before validation can pass.
- Add bounded time-series evaluation while preserving low-fidelity and no-commercial-equivalence boundaries.
- Bind native PhysicsGuard validation and closure checks to a SkillGuard execution-depth receipt.
- Adopt the repository with a generated SkillGuard project-maintenance block that preserves PhysicsGuard as the physical validator.

## Capabilities

### New Capabilities
- `simulation-validation-depth`: Dataset/time/scenario/mapping/holdout-aware validation and execution-depth receipts.

### Modified Capabilities

None.

## Impact

PhysicsGuard validation models, CLI/report output, signal mapping, project evidence registry, skill prompts, examples, fixtures, and tests are affected. PhysicsGuard remains a low-fidelity audit tool and does not claim recovered commercial-model equivalence.
