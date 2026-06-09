---
name: physicsguard-signal-mapping-review
description: Use when external simulation signals are mapped into PhysicsGuard variables and confidence, unit evidence, review state, or stale conditions need inspection before residuals can support fault claims.
---

# PhysicsGuard Signal Mapping Review

Use this route when external model outputs are mapped into PhysicsGuard observed values.

## Workflow

1. Create or review an intake file based on `templates/external_model_intake.yaml`.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

3. If mappings are low confidence, missing conversion notes, review-required, or stale, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.

Intake metadata does not convert or mutate observed values.
