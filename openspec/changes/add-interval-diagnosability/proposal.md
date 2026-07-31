## Why

PhysicsGuard can maintain task-local hypotheses and rank a next observation, but uncertain measurements are still easily collapsed into point values and several fault candidates can remain observationally indistinguishable without being reported as such. That can produce confident-looking audit conclusions where the correct result is indeterminate.

## What Changes

- Represent relevant observations with explicit intervals, units, provenance, and missing/not-run state.
- Derive fault signatures and equivalence classes to identify hypotheses that current evidence cannot distinguish.
- Return `robust_pass`, `robust_fail`, `indeterminate`, or `not_run` instead of treating missing or interval-overlapping evidence as zero or pass.
- Recommend the next signal by declared discriminatory value, acquisition cost, and risk while preserving the existing task-local hypothesis-revision owner.
- Project the same semantics into affected PhysicsGuard prompts, reports, CLI, FlowGuard models, SkillGuard contracts, and tests.

## Capabilities

### New Capabilities

- `physicsguard-interval-diagnosability`: Defines interval evidence, distinguishability classes, robust terminals, and next-signal discrimination.

## Impact

Affected surfaces: AI debugging, model-understanding preflight, signal mapping, audit closure, hypothesis/evidence runtime modules, schemas, CLI/reports, FlowGuard models, SkillGuard maintenance inputs, tests, docs, and release version.
