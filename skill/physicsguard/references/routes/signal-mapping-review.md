# PhysicsGuard Signal Mapping Review

## Entry boundary

Accept this route only when:

- The task concerns external-signal or parameter mapping identity, unit, conversion, confidence, review, timing, or staleness.
- Mapping evidence must be resolved before residual, adequacy, or predictive checks can use it.

Reject or hand off when:

- A concrete many-field test file first needs a complete field contract. Handoff: the `test-file-contract-review` route.
- Mappings are current and the task is exact model/dataset validation. Handoff: the `model-dataset-validation` route.

## Minimum workflow

1. Name the audit file this route binds to and read it with `python -m physicsguard.cli hierarchy describe AUDIT.yaml` (no audit yet: build one first, as in `## Start from the model`); then bind every governed external object to its exact variable named by `target`, unit, conversion, revision, and evidence.
2. Following the route protocol below, check confidence, review, time coverage, intervals, and stale conditions.
3. Keep unresolved mappings visible and do not mutate observed values.

## Required outputs

- `mapping_status`
- `review_gaps`
- `temporal_boundary`
- `safe_mapping_claim`

Claim boundary: A mapping pass licenses only the exact external signal, variable named by `target`, conversion, revision, temporal range, and reviewed confidence in the command output.

## Route protocol

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
the `test-file-contract-review` route first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Put optional external model context in the snapshot or test-file contract's `source_model`: `model_name`, `tool`, `tool_version`, `model_version`, `scenario` and `export_time` are optional strings. Unknown keys are rejected. This header supplies context, not evidence that the model or audit passed.
2. Run `python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml`.
   The full report (`--json`) retains `signal_mapping_ledger`; compact `mapping_summary`
   counts all ledger rows, rows with issues, explicit review requests, stale mappings,
   low confidence and missing units. Both outputs use the same native ledger.

3. If `signal_mapping_ledger` rows report `low_confidence`, `missing_unit`, `missing_conversion`, `review_required` or `stale_mapping`, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.
   Every variable a residual uses is either observed with its source signal and unit, or listed in `missing_required_variables` with its residuals skipped; both kinds of gap stay open in the claim.
4. Keep uncertainty and its source explicit. A point audit does not establish robustness
   over an untested range; use declared validation envelopes for bounded dataset claims.

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

Variables used for prediction must have exact units, scales, step/time alignment, and
accepted mappings in both generated trajectory and future holdout. Mapping
confidence alone does not make a pointwise relation stateful or predictive.

`source_model` context never converts or mutates observed values or changes an audit verdict.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.

## Check against the audit model
`python -m physicsguard.cli preflight review PREFLIGHT.yaml --audit AUDIT.yaml`
checks each declared block ID (`preflight_block_unknown` on an unknown block).
Omitting `--audit` preserves the structural review.

A failed observed audit may add `unit_conversion_family` with a named variable
and a tested factor/offset. The bounded probe checks native residuals in the
worst failing block and rederives affected intermediates; it never changes the
observations or proves that a unit error is the real cause. Verify the source
and record any actual correction in the test-file contract.
