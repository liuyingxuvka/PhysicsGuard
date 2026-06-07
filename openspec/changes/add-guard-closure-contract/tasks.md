## 1. Closure Helper

- [x] Add `skill/physicsguard-ai-debugging/scripts/physicsguard_closure_check.py`.
- [x] Update PhysicsGuard skill closure guidance.

## 2. Validation

- [x] Run helper smoke checks.
- [x] Run focused PhysicsGuard CLI validation.
- [x] Run FlowGuard project audit after edits.

## 3. Sync

- [x] Sync installed physicsguard-ai-debugging skill folder.
- [x] Record verification evidence and remaining gaps.

## Verification Evidence

- `python -m pytest tests -q`: passed, 689 tests.
- `python skill/physicsguard-ai-debugging/scripts/physicsguard_closure_check.py --json`: partial report smoke passed with next actions.
- `python .flowguard/guard_closure_contract/run_checks.py`: passed.
- `python -m flowguard project-audit --root .`: passed with FlowGuard 0.40.12.
- Installed skill hash check: source and local `.codex/skills` copies match.
