# PhysicsGuard Signal Mapping Review

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
`physicsguard-test-file-contract-review` first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Create or review an intake file based on templates/external_model_intake.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

3. If mappings are low confidence, missing conversion notes, review-required, or stale, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.
4. If mapping or measurement error is bounded, preserve the lower and upper
   bounds as an interval and identify the bound source. Do not replace a bounded
   interval with its midpoint for robust residual or fault-signature analysis.
   An interval that overlaps an acceptance boundary remains `indeterminate`.

For model-dataset validation depth, the current project evidence registry and
named bundle are the consumed mapping review. Every required model input,
validation output, diagnostic check, or redundant measurement must have an
active bundle binding with unit evidence, confidence at or above the declared
threshold, and an accepted reviewer state. Bind the registry by SHA-256.
Missing units, low/unknown confidence, inactive bindings, review-required
status, bundle absence, or a changed registry blocks the broad validation
receipt or confines work to unaffected relations.

For quantitative adequacy, review the entire artifact-derived signal universe,
not only the signals selected by the validation plan. Mark critical signals and
subsystem/declared families, preserve source-row lineage and time alignment,
and ensure each selected signal has enough valid points, distinct timestamps,
span, and gap coverage for the requested scope. A missing signal needs an
explicit project-specific exclusion or remains a blocker; repeating one generic
reason across thousands of signals is not adequate coverage evidence.

Classify model parameters separately from signals. A static parameter needs a
current fact-to-parameter binding and classification source. A time-varying
parameter needs a series mapping and must independently pass per-parameter
point count/ratio, distinct timestamps, span, and maximum-gap floors; one mapped
value is not temporal coverage.

Predictive targets must have exact units, scales, step/time alignment, and
accepted mappings in both generated trajectory and future holdout. Mapping
confidence alone does not make a pointwise relation stateful or predictive.

Intake metadata does not convert or mutate observed values.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.
