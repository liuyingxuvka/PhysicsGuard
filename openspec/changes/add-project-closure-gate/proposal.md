## Why

PhysicsGuard now has project evidence maps, test-file contracts, model-dataset validation, and model-library checks, but final AI completion claims still depend on manually remembering the correct order. A project-level closure gate makes the last decision explicit: what passed, what is partial, what is blocked, and what the AI may safely claim.

## What Changes

- Add a project closure plan and report schema for final readiness checks.
- Add a `physicsguard project closure PLAN.yaml --pretty` command that aggregates project audit, evidence registry checks, evidence gap checks, evidence map generation, test-file contracts, model-dataset validation, model-library checks, and optional hierarchy closure evidence.
- Add templates, examples, tests, and FlowGuard governance for the closure route.
- Strengthen PhysicsGuard skill prompts so final completion, validation, reuse, or localization claims route through the closure gate instead of relying on the evidence map alone.

## Capabilities

### New Capabilities
- `project-closure-gate`: Project-level final closure gate that converts current project evidence and downstream checks into scoped pass, partial, downgraded, or blocked claim readiness.

### Modified Capabilities

## Impact

- Affected code: `src/physicsguard/schema`, `src/physicsguard/core`, `src/physicsguard/cli.py`, loader exports, templates, tests, docs, and local Codex skills.
- Affected workflow: final AI claims for project readiness, validation readiness, validated reuse, and fault localization gain a single explicit report.
- No new runtime dependencies.
