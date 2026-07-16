## 1. Receipts And Field Lifecycle

- [x] 1.1 Add dataset, mapping, time-window, scenario, split, residual-series, envelope, report, and depth-receipt types
- [x] 1.2 Extend the existing evidence registry and model-dataset validation FlowGuard owners with the new fields
- [x] 1.3 Add field-lifecycle and validation-depth process checks

## 2. Native Validation Depth

- [x] 2.1 Bind validation to exact dataset, schema, testbench, mapping, and parameter identities
- [x] 2.2 Enforce snapshot/time/scenario scope and disjoint calibration/holdout identity
- [x] 2.3 Add bounded pointwise time-series residual and physical-envelope evaluation
- [x] 2.4 Emit a native PhysicsGuard depth receipt with low-fidelity and no-commercial-equivalence boundaries

## 3. Integration And Adoption

- [x] 3.1 Update CLI/reports, evidence registry, examples, and all affected PhysicsGuard skills
- [x] 3.2 Bind native validation and closure checks to SkillGuard without physical recomputation
  - PhysicsGuard emits and closure-consumes the native receipt with `physical_recomputation: false`; the parent integration attached the external SkillGuard contract binding without adding physical recomputation.
- [x] 3.3 Adopt the repository with the generated SkillGuard project-maintenance block
  - The parent integration installed and audited the marker-bounded root `AGENTS.md` block and project adoption manifest while preserving surrounding content.

## 4. Verification

- [x] 4.1 Add stale dataset, uncertain mapping, snapshot overclaim, split overlap, interval violation, and receipt tests
- [x] 4.2 Run FlowGuard validation-depth checks, focused/full pytest, SkillGuard target checks, OpenSpec verification, and project audits
  - All required checks passed; the remaining unmatched freshness-watch warning is non-blocking and does not represent skipped runtime evidence.
