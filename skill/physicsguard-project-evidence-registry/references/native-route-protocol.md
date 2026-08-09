# PhysicsGuard Project Evidence Registry

Use this sibling route to maintain the project-level map. It does not replace
per-file test contracts or model-dataset validation. It tells AI agents where
the evidence is, what is known, what is unknown, which fields and facts bind to
the model, and which gaps still need work.

## Blueprint evidence projection

Use summary for project navigation and the exact affected projection when a file, resource, oracle, receipt, or evidence fingerprint changes. Bind each registry artifact and freshness result to the exact blueprint element, semantic, physical obligation, and native binding that owns it. Report missing, stale, unsupported, unresolved, or outside-scope endpoints distinctly. Registry status must not upgrade the native blueprint review. Load full only for a whole-boundary handoff or closure, and never replace a missing/stale projection with a repository scan.

Executable projection entry: use `physicsguard.summary_physical_blueprint_projection(blueprint, review)` for navigation, `physicsguard.affected_physical_blueprint_projection(blueprint, review, seed_ids, target_inventory_authority=authority, blueprint_base_dir=blueprint_root, authority_base_dir=authority_root)` for a changed evidence identity, and `physicsguard.full_physical_blueprint_projection(blueprint, review)` only for a declared whole-boundary handoff. The affected query reruns the canonical reviewer once against the exact blueprint artifacts, frozen authority, and raw target material and requires the supplied review to equal that passing result before graph compilation; it reports non-current identity rather than mutating or replacing the review.

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
- If this project appears in an external database ledger, keep this route scoped
  to the project's physical evidence registry. Do not update or repair the
  external ledger from this PhysicsGuard skill.

## Workflow

1. Locate or create the project evidence registry, usually:

   ```powershell
   python -m physicsguard.cli evidence check evidence/project_evidence_registry.yaml --pretty
   ```

2. Fill or review `project_profile`: project name, objective, run period,
   locations, known unknowns, and source references.
3. Register important files in `artifacts`: test data, test-file contracts,
   logical datasets, source documents, model files, validation plans/reports,
   bounded `observed_series`, signal-mapping reviews, native
   `validation_depth_receipt` files, and model-library indexes.
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
   For validation depth, include the exact observed-series artifact and every
   binding used by the mapping gate. Units, mapping confidence, active status,
   reviewer state, and bundle membership must be current; the validation plan
   binds the registry by SHA-256.
   Treat the manifest, role matrix, hierarchy, and current bindings as coverage
   authorities: they define available signals/parameters and hierarchy-required
   critical members. Record subsystem/family membership, intentional
   exclusions with specific reasons, and source evidence for required events,
   peaks, boundaries, modes, and adequacy thresholds. A validation plan cannot
   shrink this universe merely by omitting members.
   Record a source-backed static/time-varying classification for every
   available model parameter. Static parameters need current fact/binding
   evidence; time-varying parameters need an exact series mapping so their own
   point/time depth can be checked.
   For predictive work, register the exact stateful model, training inputs,
   producer receipt, generated trajectory, future holdout, and native rollout
   receipt. Preserve path/hash/case disjointness evidence.
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
- What is the available coverage universe, which members are critical, and
  which members were explicitly excluded for a project-specific reason?
- Is the model pointwise or stateful, and is there a disjoint future-rollout
  receipt for any predictive claim?
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

If an external database ledger owns this project, this skill can provide current
project evidence, gap reports, closure inputs, validation status, and model
library evidence. It does not update, refresh, audit, or render the external
ledger itself.
