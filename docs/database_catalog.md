# Database Catalog

The database catalog is the AI-facing map above many PhysicsGuard projects. It
does not store raw test data and does not replace project evidence registries,
test-file contracts, validation reports, or model-library checks.

Use it when an AI agent needs to answer questions such as:

- Which projects are in this database?
- Which projects have test data, models, validation reports, or reusable model
  entries?
- Which projects cover a tag, component, tested quantity, or model target?
- Which project registries, model libraries, or validation reports should be
  inspected next?
- Which projects have blocking or review gaps before broad comparison or reuse
  claims?

## Layering

```text
database catalog
  -> project evidence registry
       -> test-file contracts
       -> validation plans/reports
       -> model-library entries
```

The catalog stores project cards and indexes. The project registry remains the
detailed source for project facts, files, bindings, evidence bundles, and gaps.

## What To Record

- `catalog_id`, `catalog_name`, catalog roots, version, and description.
- `projects`: one lightweight card per project.
- `project_evidence_registry`: path to the project-level registry when known.
- Generic tags: `domain_tags`, `system_tags`, `subsystem_tags`,
  `component_tags`, `test_object_tags`, `testbench_tags`, and
  `measurement_tags`.
- `has_test_data`, `has_model`, `has_validation`, and
  `has_model_library_entry` when known.
- Separate confidence states for source, mapping, data quality, validation,
  reuse, catalog freshness, and review.
- `model_library_indexes`: references to reusable model-library indexes.

Do not place raw rows, bulk samples, or time-series values in catalog metadata.
Keep large files in place and reference them through the project evidence
registry.

## Commands

```powershell
python -m physicsguard.cli database check CATALOG.yaml --pretty
python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
python -m physicsguard.cli database refresh CATALOG.yaml --pretty
python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
python -m physicsguard.cli database map CATALOG.yaml --pretty
python -m physicsguard.cli database query CATALOG.yaml --tag TAG --pretty
```

Query filters include `--tag`, `--quantity`, `--component`,
`--model-target`, `--has-validation`, `--has-test-data`, and
`--project-status`.

## Claim Boundary

Database maps and queries are search/navigation outputs. They can identify
related candidate projects, but they cannot prove physical consistency,
validation pass, model reuse, or direct cross-project comparability. Before
making broad claims, inspect the project evidence registry, gap report,
validation evidence, and comparison scope.
