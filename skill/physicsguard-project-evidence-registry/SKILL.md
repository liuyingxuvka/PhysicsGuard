---
name: physicsguard-project-evidence-registry
description: Use when a PhysicsGuard project needs a project-level evidence registry, project profile, file map, binding expectations, evidence bundles, project evidence map, or gap scan across test files, physical parameters, model contexts, validation plans, and model-library reuse.
---

# PhysicsGuard Project Evidence Registry

Use this sibling route to maintain the project-level map. It does not replace
per-file test contracts or model-dataset validation. It tells AI agents where
the evidence is, what is known, what is unknown, which fields and facts bind to
the model, and which gaps still need work.

## Hard Rules

- Large test data stays where it is; register paths or external references
  instead of copying raw data into the project.
- Small source documents may have local copies, but the registry must say so.
- Basic project profile facts are maintenance targets: project name, objective,
  run period, locations, and source references. If unknown, write an explicit
  unknown reason instead of inventing values.
- Every important test field, physical parameter, or model target must have a
  binding record, a binding expectation, or an explicit exemption reason.
- Manufacturer names, serial numbers, timestamps, comments, or unrelated
  metadata may be exempt from model binding only when the exemption reason is
  recorded.
- The Project Evidence Map is an onboarding/navigation artifact. It is not
  validation proof.
- Blocking evidence gaps prevent validation pass or validated reuse claims.
- If this project is listed in a database catalog, refresh or flag the catalog
  after project evidence changes so multi-project maps do not become stale.

## Workflow

1. Locate or create the project evidence registry, usually:

   ```powershell
   python -m physicsguard.cli evidence check evidence/project_evidence_registry.yaml --pretty
   ```

2. Fill or review `project_profile`: project name, objective, run period,
   locations, known unknowns, and source references.
3. Register important files in `artifacts`: test data, test-file contracts,
   logical datasets, source documents, model files, validation plans/reports,
   and model-library indexes.
4. Register engineering facts in `facts`: physical parameters, equipment or
   vendor identity, configuration facts, software versions, derived values,
   calibrated values, and human overrides.
5. Add `evidence_bindings` for project-level links from test fields or facts to
   model targets. The authoritative detailed mapping remains in the test-file
   contract or source document.
6. Add `binding_expectations` for every field/fact/model target that must be
   checked. Use `must_bind`, `unknown`, or `exempt` with a reason.
7. Add `context_cards` for model/testbench/test-object/dataset scope. Model
   contexts should list model parts and required evidence.
8. Add `evidence_bundles` for validation and model-library handoff.
9. Run:

   ```powershell
   python -m physicsguard.cli evidence gap-check evidence/project_evidence_registry.yaml --pretty
   python -m physicsguard.cli evidence map evidence/project_evidence_registry.yaml --pretty
   ```

10. Before broad claims, resolve blocking gaps. For review/optional gaps, keep
    them visible in the final claim boundary.
11. For project completion, validation readiness, validated reuse, or
    localization readiness, hand off to project closure:

    ```powershell
    python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
    ```

    The evidence map remains onboarding/navigation only. The closure report is
    the final claim-readiness gate.

## AI Onboarding Map

When another AI enters the project, show or inspect `evidence map` first. It
should answer:

- What project is this, when and where did it run, and which basics are unknown?
- Which files matter, and where are they?
- Which tests exist and what model targets do they cover?
- Which model parts exist and which are tested?
- Which physical parameters are registered and source-backed?
- Which fields or facts are exempt from model binding and why?
- Which blocking/review/optional gaps remain?

## Commands

```powershell
python -m physicsguard.cli evidence check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence scan PROJECT_OR_FOLDER --registry EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence bundle-check EVIDENCE.yaml BUNDLE_ID --pretty
python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
```

For final project claims, follow with:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

If a database catalog owns this project, follow with:

```powershell
python -m physicsguard.cli database refresh CATALOG.yaml --pretty
python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
```
