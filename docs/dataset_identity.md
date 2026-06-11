# Dataset Identity

PhysicsGuard dataset identity records keep large raw test files in place while
the project stores machine-checkable evidence about what each file is and how it
relates to other files.

## Layers

```text
raw test file, not moved
  -> DataFileManifest
  -> LogicalDatasetRecord
  -> TestFileContract
  -> optional relation index
```

- `DataFileManifest` records file path, hash, format, fields, timing, and
  extractor evidence.
- `LogicalDatasetRecord` records the logical test dataset represented by one or
  more manifests.
- `TestFileRelationIndex` records symmetric relationships such as same test
  run, equivalent export, redundant sensor, or fallback sensor.

Non-identical files keep separate logical datasets and separate contracts.
Shared testbench profiles, model bindings, policies, and mapping templates
reduce duplicated maintenance without making one contract the parent of another.

## Commands

```powershell
python -m physicsguard.cli dataset logical-check DATASET.yaml --pretty
python -m physicsguard.cli dataset relation-check RELATIONS.yaml --pretty
```

These checks prove identity and relationship evidence only. They do not prove
model physical correctness.
