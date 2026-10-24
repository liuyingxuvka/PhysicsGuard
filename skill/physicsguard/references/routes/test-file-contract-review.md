# Test-file contract review

## Entry boundary
Use only for concrete CSV/TSV test data. Model-only work uses `ai-debugging`.
After a contract passes, hand model/data consistency work to `model-dataset-validation`.
One contract stores field roles, units, variable mappings, conversion, confidence and evidence; its generated manifest stores file identity, without separate catalogs or mapping sidecars.

## Workflow
1. Copy `references/templates/test_file_contract.yaml`. Set `data_file`, `model`,
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
The only automatic table is `src/physicsguard/core/units.py`: K/degC;
W/kW/MW; m³/s/L/s/L/min/m³/h; Pa/kPa/bar/MPa; rad/s/rpm;
kg/s/g/s/kg/h; m/mm; s/min/h. Identical unit labels are unchanged.
Other pairs require explicit `conversion: {factor: ..., offset: ...}`.
An explicit conversion that contradicts a known pair fails. Each output value
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
