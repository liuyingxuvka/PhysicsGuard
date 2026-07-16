## Context

The completed SkillGuard V2 migration correctly removed former runtime authority from all ten PhysicsGuard skills, but the shared retirement inventory remained inside the migration's active OpenSpec directory. `verify_guard_simulation_readiness.py` imports that path directly, and `verify_physicsguard_suite_parent.py` imports the verifier while the parent contract declares neither the imported script nor the inventory as owner inputs. OpenSpec archive therefore both removes the runtime file and exposes a freshness-model gap.

## Goals / Non-Goals

**Goals:**

- Establish one PhysicsGuard-owned current retirement inventory outside planning history.
- Make post-archive runtime audits, installed parity checks, and parent receipt replay deterministic.
- Declare transitive runtime dependencies as exact parent owner inputs so affected-only revalidation is honest.
- Reissue only invalidated receipts and retain child-owned physical-purpose evidence.

**Non-Goals:**

- Do not search OpenSpec archive history at runtime.
- Do not add a legacy reader, alias, migration command, compatibility mode, or optional inventory selection.
- Do not change the ten child purpose declarations, physical oracles, known-good cases, or per-failure known-bad cases.

## Decisions

1. The single current inventory lives at `.flowguard/physicsguard_v1_retirement_inventory.json`. This is part of the project runtime authority, while the archived OpenSpec copy remains historical evidence only. Searching active or archived change directories was rejected because it creates multiple possible authorities and date-dependent behavior.
2. The readiness verifier imports only the project-owned path and fails visibly if it is absent or invalid. No caller can select another inventory.
3. Every parent child-replay owner declares the readiness verifier and current inventory in `input_selectors` and `implementation_paths`. This makes a change to either file invalidate exactly the parent replay owners that consume them.
4. A regression constructs the post-archive state by asserting the active migration path is absent, then exercises retirement receipt status and suite replay against the current authority.
5. Existing retirement receipts may be reused only if their inventory and current-authority hashes remain exact; parent receipts are reissued because their declared input graph changes.

## Risks / Trade-offs

- [Risk] Copying the inventory could temporarily create two maintained authorities. → The runtime references only the project path; the archived copy is never read and a regression rejects active-change dependencies.
- [Risk] Adding transitive selectors invalidates all eleven parent owners. → Execute each affected owner once, freeze the new parent plan, and aggregate immutable receipts without rerunning child physical proofs.
- [Risk] Future refactors may add another imported verifier without declaring it. → The focused regression inspects generated selectors and the model-miss record makes transitive runtime inputs an explicit review obligation.

## Migration Plan

1. Add the canonical inventory with bytes matching the archived migration inventory.
2. Update runtime and generated parent ownership paths, then add focused regressions.
3. Reissue retirement receipts only if their exact hashes change; regenerate and compile the parent contract.
4. Run readiness, source/install parity, parent supervision, full TestMesh aggregation, and receipt-only OpenSpec verification.
5. Archive this corrective change and repeat the post-archive read-only audit.

Rollback removes the corrective change only before new parent evidence is issued. After closure, rollback requires restoring a valid project-owned current authority and reissuing affected evidence; reverting to an active or archived OpenSpec path is not allowed.

## Open Questions

None.
