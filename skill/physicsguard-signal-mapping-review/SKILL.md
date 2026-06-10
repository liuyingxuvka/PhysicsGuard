---
name: physicsguard-signal-mapping-review
description: Use when external simulation signals are mapped into PhysicsGuard variables and confidence, unit evidence, review state, or stale conditions need inspection before residuals can support fault claims.
---

# PhysicsGuard Signal Mapping Review

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
`physicsguard-test-file-contract-review` first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Create or review an intake file based on `templates/external_model_intake.yaml`.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

3. If mappings are low confidence, missing conversion notes, review-required, or stale, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.

Intake metadata does not convert or mutate observed values.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.
