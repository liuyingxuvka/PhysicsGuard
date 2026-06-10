---
name: physicsguard-model-understanding-preflight
description: Use before PhysicsGuard audits of external models to capture visible symptom, physical boundary, subsystem blocks, units, assumptions, uncertain mappings, and stop conditions.
---

# PhysicsGuard Model Understanding Preflight

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to `physicsguard-test-file-contract-review` before broad
analysis claims.

## Workflow

1. Create or review a preflight file based on `templates/model_understanding_preflight.yaml`.
2. Run:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

3. If missing inputs or uncertain mappings are reported, complete them or route to signal mapping review before fault claims.

Preflight pass is planning evidence only. It is not residual validation.
