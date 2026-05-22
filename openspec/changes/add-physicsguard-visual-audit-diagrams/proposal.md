## Why

PhysicsGuard already describes a low-fidelity physical understanding map, but the Codex skill does not yet tell agents when to show that map visually or how to keep diagram semantics distinct from residual evidence. Adding explicit visual-audit communication rules makes AI debugging conversations clearer without changing runtime physics or solver behavior.

## What Changes

- Add a PhysicsGuard-specific diagram intent gate for non-trivial AI debugging, audit explanation, refinement, and candidate-model blueprint work.
- Define a visual toolbox for physical topology, residual localization, observed-signal mapping, assumption boundaries, coarse-to-fine refinement, and candidate-model blueprints.
- Require clear edge semantics such as physical flow, signal mapping, residual check, assumption boundary, refinement, and required signal.
- Document that diagrams and tables explain the audit path but do not replace FlowGuard checks, PhysicsGuard CLI output, pytest, or residual evidence.
- Update the local Codex skill source and installed skill copy so agents get the new guidance immediately.
- No breaking changes to PhysicsGuard CLI behavior, YAML schemas, solver behavior, residual modules, or public APIs.

## Capabilities

### New Capabilities
- `visual-audit-communication`: Defines how PhysicsGuard agents choose and present compact diagrams or tables for physical audit conversations.

### Modified Capabilities
- None.

## Impact

- Affected artifacts: `skill/physicsguard-ai-debugging/`, installed Codex skill copy, `docs/`, `README.md`, OpenSpec change files, version/changelog release metadata, and FlowGuard adoption logs.
- No new runtime dependency is required.
- Public runtime behavior stays unchanged; this is a Codex skill, documentation, and release presentation upgrade.
