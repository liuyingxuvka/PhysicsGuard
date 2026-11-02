# Test-file contract review

## Entry boundary
Use only for concrete CSV/TSV test data. Model-only work uses `ai-debugging`.
After a contract passes, hand model/data consistency work to `model-dataset-validation`.
One contract stores field roles, units, variable mappings, conversion, confidence and evidence; its generated manifest stores file identity, without separate catalogs or mapping sidecars.

## Workflow
1. Name the audit the contract's `model` points to and read it with `python -m physicsguard.cli hierarchy describe AUDIT.yaml`
   (no audit yet: build one first, as in `## Start from the model`). Copy `references/templates/test_file_contract.yaml`. Set `data_file`, `model`,
   `manifest` and `time_column`. All paths are relative to that contract.
2. Generate the manifest, using the contract's field units and optional exporter:
   `python -m physicsguard.cli testfile manifest DATA.csv --profile CONTRACT.yaml --out MANIFEST.yaml`.
   The source path is relative to the manifest directory (absolute across drives).
   Content hashes identify the actual data and extractor; regenerate after changes.
3. Declare every field once under `fields`: `measured` or `command` with unit,
   `target`, confidence and evidence; or `ignored` with a reason. The named
   `time_column` already declares its timing role. Do not invent the variable named by `target`.
4. Run `python -m physicsguard.cli testfile contract-check CONTRACT.yaml`.
   Missing roles, unknown mapped variables, stale hashes, absent evidence and uncertain
   units block a pass. `review_required` or a reasoned `planned_child_model`
   remains partial, so request evidence or model extension before proceeding.
5. Generate SI observations without changing the raw data:
   `python -m physicsguard.cli testfile snapshot CONTRACT.yaml --row 70 --out measured.yaml`,
   or `python -m physicsguard.cli testfile series CONTRACT.yaml --rows 0:120 --out series.yaml`.
   Rows are zero-based and A:B excludes B. `targets: {row: ..., next_row: ...}`
   maps adjacent rows into a single-step relation; an absent next row is an error.
6. Use `hierarchy evaluate` for snapshots or `validation run` for series, scoped
   to the declared model, mapped fields, rows and assumptions. Review critical
   parameter mappings, operating modes and holdout boundaries in the validation plan.

## Units and evidence
The only automatic table is `src/physicsguard/core/units.py`. It reads units written with its
symbols (kg, g; m, mm, cm, km; L, mL; s, min, h; W, kW, MW; Pa, kPa, MPa, bar; K, degC, degF;
rad, rev, rpm) joined by `/` or `*` with `^n` powers, and other spellings of them (l/min, LPM,
kg/sec, m3/h, °C). Identical unit labels are unchanged. A field in a unit the tool cannot read is
`unit_not_convertible`, whatever factor it records; only a transducer output (V, mV, A, mA, ohm)
takes an explicit calibration `conversion: {factor: ..., offset: ...}`, applied unchecked.
An explicit conversion that contradicts a known pair fails, and a field cannot change
quantity (a kg/s field mapped to an m³/s variable) with a bare factor: `unit_not_convertible`.
To change quantity, declare the linking property once under the contract's `properties`
(`water_density: {value: 1.0, unit: kg/L, source: ...}`) and name it on the field with
`conversion_property`; the tool computes the factor, a recorded `conversion` must agree with it
(`conversion_disagrees_with_property`), and a property that cannot link the two units is
`unit_not_convertible`. Snapshots and series carry each reading as `raw_value`/`raw_unit` (and the
contract's properties) beside the converted value, so loading them checks the conversion again; a
series row from a transducer output is marked `conversion_unchecked`. Each output value
records the unit of the variable named by `target`, factor, offset, field@row, confidence and source.
Audit evaluation never performs a hidden conversion or moves observed values.
Mapping confidence accepts high, medium, low or proposed; the default minimum is medium.
Proposed mappings remain below low. Use an explicitly justified word threshold when appropriate; numeric mapping confidence is rejected.

## Required outputs
Report `contract_status`, every field disposition, mapping gaps, and the safe
analysis boundary. `testfile inspect` reads the single declaration and current
review; `testfile diff OLD NEW` compares files and declarations.

## Claim boundary
A pass licenses scoped analysis of this identified and mapped file, not proof
of physical correctness. Unknown fields, missing evidence, planned models and
stale data must remain visible. Preserve the manifest's raw row/signal universe
for adequacy and the training/holdout separation; do not claim that ignored
fields were validated. Old multi-file contracts must be rewritten; they are not read.
