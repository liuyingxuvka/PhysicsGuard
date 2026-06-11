## Context

PhysicsGuard currently separates several proof surfaces:

- project adoption proves workflow records are discoverable;
- project evidence registry and map show where evidence lives and which gaps remain;
- test-file contracts prove field coverage discipline;
- model-dataset validation checks low-fidelity model/data consistency;
- model-library checks bound reuse claims to validation evidence;
- hierarchy closure checks residual-localization evidence.

The missing layer is a final project closure report that reads these surfaces in order and states the strongest safe claim. The evidence map remains navigation, not proof.

## Goals / Non-Goals

**Goals:**
- Provide one project-level closure plan input and one closure report output.
- Make blocking evidence gaps block broad pass/reuse/localization claims.
- Keep review and optional gaps visible without always blocking scoped progress.
- Reuse existing checks instead of duplicating evidence logic.
- Make skipped required checks explicit and configurable.
- Update AI skill prompts so final claims use the closure report.

**Non-Goals:**
- Do not move raw data into the registry.
- Do not replace evidence registry, test-file contracts, validation reports, model-library checks, or hierarchy closure.
- Do not add real physical modules, commercial-tool adapters, or high-fidelity solvers.
- Do not mark evidence maps as validation proof.

## Decisions

### Decision: closure is a separate report, not a registry field

The project evidence registry is the map of evidence. The closure report is the final readiness decision derived from current checks. Keeping them separate avoids stale "done" fields inside a registry that may remain after files change.

### Decision: closure reuses existing check functions

The closure core will call existing project evidence, test contract, validation, and model-library check functions. It will not reimplement their rules. This keeps authority with the owner route and avoids duplicate truth.

### Decision: claim scope is explicit

The plan includes `claim_scope` so the closure can distinguish project handoff, analysis readiness, validation readiness, validated reuse, and fault localization. This prevents a narrow evidence pass from being reported as a stronger project claim.

### Decision: skipped required checks are first-class evidence

Required checks that are not supplied are findings. By default, skipped required checks block closure. A plan can allow skipped checks only when the final claim is intentionally limited.

### Decision: hierarchy closure stays optional but claim-bound

Many project evidence tasks do not include fault localization. The closure plan accepts `audit_pairs` for hierarchy closure evidence, but a fault-localization claim requires those checks or an explicit downgrade.

## Risks / Trade-offs

- Over-strict closure could slow early exploration. Mitigation: allow scoped `partial` closure and make claim scope explicit.
- A single command could hide which route failed. Mitigation: report findings grouped by source route with next actions.
- Later writes can stale closure evidence. Mitigation: treat closure as current-run evidence and keep version/check summaries in the report.
