## Why

The PhysicsGuard suite retirement verifier reads its current inventory from an active OpenSpec change directory. Archiving the completed migration therefore removes a runtime dependency and makes every child replay fail even though the installed skills and their receipts remain current.

## What Changes

- Promote the former-V1 retirement inventory into a stable PhysicsGuard-owned current authority outside OpenSpec change history.
- Bind the inventory and the imported runtime verifier into every parent child-replay owner's declared inputs.
- Add a regression that archives or removes the planning copy and proves source, installed, and parent receipt-only verification still work without a fallback reader.
- Reissue only evidence invalidated by these exact input changes and close the repaired parent under current SkillGuard.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `physicsguard-skill-suite-runtime-authority`: The current retirement authority and parent replay must remain available after the implementing OpenSpec change is archived.

## Impact

Affected surfaces are the PhysicsGuard retirement inventory, readiness and parent verification scripts, parent SkillGuard contract generator, focused regressions, parent receipts, and OpenSpec verification artifacts. Child-owned physical purpose models and their native good/bad proofs do not change.
