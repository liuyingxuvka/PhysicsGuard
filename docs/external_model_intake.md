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
- `stale_when`: conditions that make this mapping evidence stale. `stale_when` records when a mapping needs reconfirmation; when a listed condition occurs, set `mapping_status` to `stale`.

## Claim Boundary

When mappings are low-confidence, missing conversion notes, or marked review-required, PhysicsGuard should not claim the physical model is faulty yet. The next action is to review mapping, unit, sign, gain, timing, or neighboring balance signals.

## Test Data Files

If the external evidence is a concrete testbench data file, use a
`TestFileContract` alongside intake review:

```powershell
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
```

The contract accounts for every file field and records mapping evidence. Intake
records source-of-truth context for the observed snapshot. Neither one converts
or mutates observed values.

## Check against the audit model
`python -m physicsguard.cli preflight review PREFLIGHT.yaml --audit AUDIT.yaml`
checks each declared block ID (`preflight_block_unknown` on an unknown block).
`python -m physicsguard.cli intake review INTAKE.yaml --audit AUDIT.yaml`
checks registered variables and conversion from the source unit using the
documented unit table (`intake_variable_unknown`, `intake_unit_not_convertible`).
Omitting `--audit` preserves the structural review.

A failed observed audit may add `unit_conversion_family` with a named variable
and a tested factor/offset. The bounded probe checks native residuals in the
worst failing block and rederives affected intermediates; it never changes the
observations or proves that a unit error is the real cause. Verify the source
and record any actual correction in the test-file contract.
