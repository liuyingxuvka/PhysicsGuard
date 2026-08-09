# PhysicsGuard Audit Closure

Use this route before final localization or completion claims.

## Blueprint closure projection

Bind the requested claim to one current whole or affected `PhysicalModelBlueprintReview` projection. Reconcile its blueprint/review/projection fingerprints, target revision, exact governed denominator, outside-scope members, deepest licensed layer, first gap, native evidence states, and safe claim. Closure consumes this result and never reimplements physical qualification. Missing, stale, unsupported, unresolved, ambiguous, or not-run evidence remains non-pass; do not substitute a broader projection or source scan.

Executable projection entry: call `physicsguard.affected_physical_blueprint_projection(blueprint, review, seed_ids, target_inventory_authority=authority, blueprint_base_dir=blueprint_root, authority_base_dir=authority_root)` for a bounded claim or `physicsguard.full_physical_blueprint_projection(blueprint, review)` only for an explicitly whole-boundary claim. The affected query reruns the canonical reviewer once against the exact blueprint artifacts, frozen authority, and raw target material, then requires the supplied review to equal that passing result field-for-field before graph compilation; non-current, foreign, incomplete, or self-rehashed review input remains non-pass and is never repaired by the query.

## Portable bundle closure boundary

A portable bundle may be supplied as a frozen handoff. Load it only through `physicsguard.query_physical_blueprint_export_bundle` or the public CLI. With no selector, consume the compact status. A deep read accepts exactly one `module`, `element`, `case`, `impact`, or `reverse` identity:

```powershell
python -m physicsguard.cli blueprint bundle-query BUNDLE --pretty
python -m physicsguard.cli blueprint bundle-query BUNDLE --case ID --pretty
```

Other selectors use the same command with exactly one of `--module ID`, `--element ID`, `--impact ID`, or `--reverse ID`. Do not load the complete bundle into the prompt, combine selectors, scan a repository for missing bytes, or replace an over-budget failure with a hand-written summary.

Bind and report the exact bundle fingerprint and id, target system id, subject revision, source fingerprints, source review status, deepest licensed layer, coverage counts, first gap, safe claim, claim boundary, query kind/id, and execution trust status. Preserve `observed_at_export_unlicensed`. Preserve every `portable_query_identity_only_terminal` gap: the bundle can identify an external source, test, dataset, resource, or oracle without carrying its bytes.

A `frozen_case_status=pass` means only that the exported bundle records that frozen case result. It is not a current run. Bundle presence, bundle load, or a correct AI answer never changes `execution_claim_licensed=false`, never refreshes evidence, and never proves high-fidelity reconstruction. If the requested claim requires current native execution, report `current_execution_status=not_run` until a separate current target-native receipt is supplied and validated by its owner. Keep that current receipt separate from the frozen bundle status.

For project-level completion, validation, reuse, or localization claims, prefer
the project closure gate first:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

Do not treat a project evidence map as proof. The map is navigation; the
project closure report decides whether current route evidence supports a
`passed`, `partial`, `downgraded`, or `blocked` claim.

Run:

```powershell
python <physicsguard-ai-debugging skill directory>\scripts\physicsguard_closure_check.py --ledger CLOSURE.json --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

Blocking or downgrading evidence includes failed audit, missing variables or parameters, review-required mappings, stale evidence, skipped checks, open refinements, and same-family follow-ups.
Portable blocking or downgrading evidence additionally includes a mismatched bundle/source fingerprint, a non-pass frozen source review, promotion of `observed_at_export_unlicensed` to fresh execution, an identity-only terminal that the claim needs as content, a missing exact selector, an over-budget projection, or absent current native execution for an execution claim.
For interval-aware work, `indeterminate` and `not_run` remain visible and
cannot be promoted to robust pass. For diagnosability work, unresolved
hypothesis pairs, missing fault-signature intervals, or a missing recommended
signal disposition block an isolated-fault claim. `isolable` means only that
the declared signatures can be separated by declared signals; it is not proof
of the true fault.
For workflows that include concrete test data files, also treat missing,
partial, stale, or failing test-file contracts as blocking or downgrading
evidence. A residual report cannot make a broad claim from a file whose fields
are not fully cataloged, classified, and evidence-mapped.

For project-level workflows, also read the project evidence map or gap report.
Missing project profile basics, unregistered important files, unresolved
blocking evidence gaps, missing binding summaries, unreviewed physical
parameter bindings, or test-field binding expectations without bindings or
exemptions downgrade or block broad claims.
If a project closure report exists, carry its `closure_status`, `safe_claim`,
`unsafe_claim_boundary`, skipped checks, and next actions into the final answer.
If no report exists for a broad project claim, run it or explicitly downgrade
the claim.

For workflows that validate a model against contracted test data, also read the
model-dataset validation report. Missing, partial, failed, stale, or blocked
validation reports downgrade or block broad model-data consistency claims. Treat
`optimization_success` as numerical optimizer evidence only; it is not
`audit_pass`, holdout pass, or final validation pass. Parameter-at-bound
warnings, low validation confidence, failed physical envelopes, redundant-sensor
mismatches, and review-required confidence updates must remain visible in the
final claim boundary.

For `validation_ready` or `validated_reuse_ready`, require
`required_checks.validation_depth: true`. The validation plan must emit a
passing `physicsguard_validation_depth_receipt` bound to its report type,
status, and SHA-256. Closure consumes that receipt without recomputing physics;
missing/stale/partial/blocked receipts, snapshot overclaim, uncertain mappings,
split overlap, invalid intervals, or hard envelope intervals block the broad
claim.

The native receipt must also contain a passing quantitative adequacy gate for
every non-snapshot claim. Verify that `covered_scope` is compatible with the
requested scope and that the receipt accounts the artifact-derived point,
signal, and parameter universe; temporal strata/gaps; per-signal histories;
source-backed static/time-varying parameter classifications; each time-varying
parameter's own resolved native/project/convergence floor, strata and row-gap
receipt; counterfactual proof that observed values affect executable model
residuals or an exact bounded non-sensitive disposition; critical members and
families; and explicit exclusions. A snapshot or shallow
subset cannot close validation or reuse readiness merely because its evaluated
points passed.

For `prediction_ready`, additionally require
`required_checks.predictive_rollout: true`, `stateful_dynamic` semantics, an
exact training/prediction/future-holdout identity chain, and a passing native
rollout receipt whose stability and error-growth checks pass. A pointwise model
or an in-sample/overlapping holdout blocks prediction closure.

For database-level or cross-project claims, do not answer from this closure
route alone. Missing project registries, stale external summaries, propagated
project evidence blocking gaps, or unknown comparison scope block broad
historical, reuse, or direct-comparison conclusions.

Closure pass supports only a scoped low-fidelity claim inside the checked audit
or project closure boundary.
