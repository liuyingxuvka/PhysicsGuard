# External Model Intake

External model intake records where observed values came from and how external signals map into PhysicsGuard variables. It is a review ledger, not a conversion engine.

Use:

```powershell
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
```

## Required Signal Fields

- `external_signal`: signal name or path in the external model/export.
- `physicsguard_variable`: target `component.variable` name.
- `unit_from_source`: source-side unit as exported or reported.
- `expected_si_unit`: PhysicsGuard-side SI unit expectation.
- `conversion_note`: how unit handling was reviewed.
- `mapping_confidence`: `high`, `medium`, `low`, or a review-oriented value.
- `review_required`: explicit boolean review gate.
- `stale_when`: conditions that make this mapping evidence stale.

## Claim Boundary

When mappings are low-confidence, missing conversion notes, or marked review-required, PhysicsGuard should not claim the physical model is faulty yet. The next action is to review mapping, unit, sign, gain, timing, or neighboring balance signals.
