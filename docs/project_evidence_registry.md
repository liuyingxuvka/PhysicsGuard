# Project Evidence Registry

The project evidence registry is the AI-facing map for a PhysicsGuard project.
It records where important files live, what basic project facts are known, which
facts and test fields bind to model targets, which items are intentionally not
bound, and which gaps still need maintenance.

It is not a validation report. It is a navigation and governance layer that
helps AI agents avoid losing project context across test files, reports,
physical parameters, model contexts, validation plans, and reusable model
library entries.

## What To Record

Use `ProjectEvidenceRegistry` for project-level evidence:

- `project_profile`: project name, objective, run period, locations, source
  references, and explicit unknown reasons when basic information cannot be
  found.
- `artifacts`: concrete files and external references, including large raw or
  cleaned test data, contracts, logical datasets, source documents, model files,
  validation plans, validation reports, and model-library indexes.
- `facts`: physical parameters, equipment identity, configuration facts,
  software versions, time-series references, calibrated values, derived values,
  and human overrides.
- `evidence_bindings`: project-level summaries that connect test fields or
  facts to model targets while naming the authoritative contract or source.
- `binding_expectations`: every test field, physical parameter, or model target
  that should be checked for binding. Each item is either `must_bind`, `exempt`
  with a reason, or `unknown` so the maintenance gap stays visible.
- `context_cards`: model, testbench, test-object, dataset, or generic context
  cards with applicability, model parts, and required evidence.
- `evidence_bundles`: reusable handoff packages consumed by validation and
  model-library routes.
- `conflicts` and `missing_evidence`: unresolved evidence problems that must not
  be hidden.

Large test data should usually stay in place and be referenced by path or
external reference. Small reports or source documents may be copied locally, but
the registry must say when a local copy is used.

## Basic Project Profile

Project-level facts are required maintenance targets. If the AI cannot find the
project name, run period, or location, it should not invent them. It should
record an unknown reason and keep the gap visible:

```yaml
project_profile:
  project_name_unknown_reason: not found in registered reports yet
  run_period:
    unknown_reason: test period not found in available sources
  location_unknown_reason: test location not found in available sources
```

When values are known, add source references:

```yaml
project_profile:
  project_name: Pump loop fixture project
  run_period:
    run_started_at: "2026-06-10T10:00:00Z"
    run_ended_at: "2026-06-10T10:00:03Z"
    source_refs:
      - artifact_id: clean_run_042
        location: time_s column
  locations:
    - location_id: repository_fixture_workspace
      label: Repository fixture workspace
      source_refs:
        - artifact_id: clean_contract_artifact
          location: contract metadata
```

## Binding Completeness

Every important test field or physical parameter should be handled in one of
three ways:

- It has an `evidence_bindings` record to a model target.
- It has a `binding_expectations` exemption with a clear reason.
- It remains `unknown`, which gap-check reports for later AI maintenance.

Example exemption:

```yaml
binding_expectations:
  - expectation_id: exempt_clean_time_basis
    subject_kind: test_field
    subject_id: field:time_s
    policy: exempt
    source_artifact: clean_run_042
    source_contract: clean_contract_artifact
    source_field: field:time_s
    exemption_reason: Time is the sampling/index axis, not a physical model state.
```

## Commands

```powershell
python -m physicsguard.cli evidence check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence scan PROJECT_OR_FOLDER --registry EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence bundle-check EVIDENCE.yaml BUNDLE_ID --pretty
python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
```

`evidence map` is the handoff view for a new AI agent. It summarizes the project
profile, registered artifacts, tests, model contexts, model parts, bindings,
binding expectations, tested model targets, explicit exemptions, and open gaps.

## Downstream Gates

Model-dataset validation plans and model-library entries can reference an
evidence registry and bundle. Blocking evidence gaps prevent validation pass or
validated reuse claims. Review and optional gaps stay visible and must be
reported in the claim boundary.

```yaml
evidence_registry: ../evidence/project_evidence_registry.yaml
evidence_bundle_id: pump_loop_validation_bundle_001
```

The registry does not replace file-specific test contracts, residual validation
reports, or model-library evidence. It connects them so AI agents can see what
exists, what is covered, and what still needs evidence.
