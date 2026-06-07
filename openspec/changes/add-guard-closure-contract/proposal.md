## Why

PhysicsGuard hierarchy reports already expose useful audit fields, but AI can stop before requesting missing signals, reviewing mappings, refining suspicious blocks, or checking same-family followups. A closure adapter turns those fields into explicit next actions.

## What Changes

- Add a PhysicsGuard closure helper for hierarchy audit results.
- Update the AI debugging skill to require closure routing before localization/completion claims.
- Keep low-fidelity and commercial-tool-equivalence boundaries explicit.

## Capabilities

### New Capabilities
- `guard-closure-contract`: PhysicsGuard audit closure ledger and aggregate closure report.

### Modified Capabilities
- None.

## Impact

Affected surfaces: `physicsguard-ai-debugging` skill and installed skill sync.
