# Model Understanding Preflight

PhysicsGuard should not let an AI agent jump straight from an external model to a fault claim. For non-trivial external-model debugging, first capture a model-understanding preflight: visible symptom, external model identity, low-fidelity physical boundary, subsystem blocks, conserved quantities, interfaces, expected SI units, assumptions, uncertain mappings, first audit level, and stop conditions.

Use:

```powershell
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
```

The preflight is planning evidence only. It does not replace `hierarchy evaluate`, `hierarchy compare`, FlowGuard checks, pytest, examples, or closure evidence.

## Required Sections

- `visible_symptom`: what went wrong from the user's perspective.
- `external_model`: model name, tool/source, version if known, and source-of-truth statement.
- `physical_boundary`: what low-fidelity boundary PhysicsGuard is allowed to check.
- `subsystem_blocks`: blocks the first audit will reason about.
- `conserved_quantities`: mass, energy, heat, power, species, charge, or signal relation families.
- `key_interfaces`: important flows or signals across block boundaries.
- `expected_units`: SI expectations for the first audit.
- `known_assumptions`: explicit assumptions, not hidden defaults.
- `uncertain_mappings`: mappings that need review before fault claims.
- `first_audit_level`: the starting audit level, usually Level 0.
- `stop_conditions`: conditions that block or downgrade claims.

## Interpretation

A passing preflight means the AI has a coherent starting map. It does not mean the external model is understood in full or that a fault is localized. A preflight with uncertain mappings can still be useful, but it must route to signal mapping review before model blame.
