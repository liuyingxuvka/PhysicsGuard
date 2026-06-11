# Project Closure Gate

Project closure is the final claim-readiness gate for a PhysicsGuard project.
It reads the current route-owned evidence and states whether the requested
claim is `passed`, `partial`, `downgraded`, or `blocked`.

It is separate from the project evidence registry:

- the registry is the map of files, facts, bindings, contexts, and gaps;
- the closure report is the current-run decision about what the AI may safely
  claim.

## Command

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

The command exits with code `0` only when closure status is `passed`.

## Plan Fields

```yaml
closure_id: example_project_closure
claim_scope: validation_ready
project_root: .
evidence_registry: evidence/project_evidence_registry.yaml
evidence_bundle_ids:
  - example_validation_bundle
test_contracts:
  - contracts/example_contract.yaml
validation_plans:
  - validation/example_validation_plan.yaml
model_library_indexes:
  - model_library.yaml
audit_pairs: []
required_checks:
  project_audit: true
  evidence_check: true
  evidence_gap_check: true
  evidence_map: true
  test_contracts: true
  validation: true
  model_library: true
  hierarchy_closure: false
allow_review_gaps: true
allow_optional_gaps: true
allow_skipped_required_checks: false
```

`claim_scope` keeps the final wording honest. A project map claim, validation
readiness claim, validated reuse claim, and fault-localization claim do not need
the same downstream evidence.

## Gate Semantics

- Project audit failure blocks closure.
- Missing evidence registry blocks required evidence checks.
- Blocking evidence gaps block broad claims.
- Review gaps downgrade closure to partial unless explicitly disallowed, in
  which case they block.
- Optional gaps may pass only when `allow_optional_gaps` is true.
- Evidence maps are navigation only. A successful map cannot make closure pass
  if gap-check, test contracts, validation, model-library, or required closure
  inputs fail.
- Skipped required checks block by default.

## Output

The report includes:

- `closure_status`
- `safe_claim`
- `unsafe_claim_boundary`
- `blocking_findings`
- `review_findings`
- `optional_findings`
- `skipped_checks`
- `next_actions`

Use `safe_claim` and `unsafe_claim_boundary` directly when explaining final
status to a user.
