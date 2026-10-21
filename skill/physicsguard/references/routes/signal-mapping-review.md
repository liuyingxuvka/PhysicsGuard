# PhysicsGuard Signal Mapping Review

## Entry boundary

Accept this route only when:

- The task concerns external-signal or parameter mapping identity, unit, conversion, confidence, review, timing, or staleness.
- Mapping evidence must be resolved before residual, adequacy, or predictive checks can use it.

Reject or hand off when:

- A concrete many-field test file first needs a complete field contract. Handoff: the `test-file-contract-review` route.
- Mappings are current and the task is exact model/dataset validation. Handoff: the `model-dataset-validation` route.

## Minimum workflow

1. Bind every governed external object to its exact target, unit, conversion, revision, and evidence.
2. Following the route protocol below, check confidence, review, time coverage, intervals, and stale conditions.
3. Keep unresolved mappings visible and do not mutate observed values.

## Required outputs

- `mapping_status`
- `review_gaps`
- `temporal_boundary`
- `safe_mapping_claim`

Claim boundary: A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the command output.

## Route protocol

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
the `test-file-contract-review` route first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Create or review an intake file starting from `references/templates/external_model_intake.yaml` in this skill's directory.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml
   ```

3. If `signal_mapping_ledger` rows report `low_confidence`, `missing_unit`, `missing_conversion`, `review_required` or `stale_mapping`, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.
   Every variable a residual uses is either observed with its source signal and unit, or listed in `missing_required_variables` with its residuals skipped; both kinds of gap stay open in the claim.
4. If mapping or measurement error is bounded, preserve the lower and upper
   bounds as an interval and identify the bound source. Do not replace a bounded
   interval with its midpoint for robust residual or fault-signature analysis.
   An interval that overlaps an acceptance boundary remains `indeterminate`.

For model-dataset validation depth, the mapping edges of the test-file
contracts that the validation plan references are the consumed mapping review.
Every required model input, validation output, diagnostic check, or redundant
measurement needs a mapping edge with unit evidence, confidence at or above
`depth.mapping_review.minimum_confidence`, and no `review_required` or stale
marker. Otherwise the broad validation stays blocked or is confined to
unaffected relations.

For quantitative adequacy, review the entire artifact-derived signal universe,
not only the signals selected by the validation plan. Mark critical signals and
subsystem/declared families, preserve source-row lineage and time alignment,
and ensure each selected signal has enough valid points, distinct timestamps,
span, and gap coverage for the requested scope. A missing signal needs an
explicit project-specific exclusion or stays an adequacy warning that narrows the
claim; repeating one generic
reason across thousands of signals is not adequate coverage evidence.

Classify model parameters separately from signals. A static parameter needs a
classification source; it is bound by the value the executable model declares. A time-varying
parameter needs a series mapping and must independently pass per-parameter
point count/ratio, distinct timestamps, span, and maximum-gap floors; one mapped
value is not temporal coverage.

Predictive targets must have exact units, scales, step/time alignment, and
accepted mappings in both generated trajectory and future holdout. Mapping
confidence alone does not make a pointwise relation stateful or predictive.

Intake metadata does not convert or mutate observed values.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.
