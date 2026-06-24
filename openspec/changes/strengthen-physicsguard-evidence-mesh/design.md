## Context

Current PhysicsGuard governance is strong in several isolated places:

- FlowGuard models cover core solve/evaluate/compare behavior, AI workflow gates, test-file contracts, project evidence registry, validation, model library, and project closure.
- The model-code ledger maps model responsibilities to code, tests, examples, and stale conditions.
- Project evidence and project closure already block many broad claims when evidence gaps remain.

The missing layer is a typed, current, parent-consumed evidence chain. The new route should not replace the existing route checks. It should consume their evidence ids and make broad claim confidence depend on the combined chain.

## Goals / Non-Goals

**Goals:**
- Make broad PhysicsGuard claims depend on a complete evidence mesh, not just local green checks.
- Represent parent/child model relationships, child evidence freshness, and parent consumption explicitly.
- Bind important model obligations to owner code contracts and current test evidence.
- Track generated bad-case, test-mesh, field-lifecycle, and risk-ledger receipts as first-class closure inputs.
- Let project closure require evidence mesh reports for strong claim scopes.
- Keep diagnostics JSON-serializable and AI-consumable.

**Non-Goals:**
- Do not add new physical component equations or high-fidelity physical models.
- Do not reverse engineer external simulation tools.
- Do not import raw data into evidence mesh artifacts.
- Do not treat the evidence mesh as physical correctness proof; it is claim-readiness proof inside declared boundaries.
- Do not replace ordinary pytest, FlowGuard checks, test-file contracts, validation, or project evidence checks.

## Decisions

### Decision 1: Add a PhysicsGuard evidence mesh artifact instead of overloading project evidence registry

The registry remains an onboarding/source map. The new mesh is a claim-proof artifact with rows for model mesh, model-test alignment, contract exhaustion, test mesh, field lifecycle, risk ledger, and downstream closure consumption.

Alternative considered: extend only `project_evidence_registry.yaml`. Rejected because registry records source facts and bindings, while evidence mesh needs route receipts, freshness, and parent-consumed proof.

### Decision 2: Make the checker conservative and receipt-based

The checker requires current non-stale receipt rows for each in-scope route. It treats missing, stale, skipped, running, failed, unconsumed, and scoped-out-without-reason rows as gaps. A child-local pass is insufficient unless a parent mesh consumes the child evidence id.

Alternative considered: use human-readable docs only. Rejected because the user wants FlowGuard-grade evidence strength.

### Decision 3: Integrate evidence mesh into project closure as an optional required gate

Existing projects can continue without mesh requirements when their closure plan does not require it. Strong claim plans can set `required_checks.evidence_mesh: true` and list mesh files. Closure then consumes mesh reports and blocks if they are not passed.

Alternative considered: always require mesh for every closure. Rejected because model-only and legacy fixture closures may be intentionally scoped, but new strong claim scopes can make it required.

### Decision 4: Keep FlowGuard model coverage separate from runtime checker logic

The runtime checker is ordinary PhysicsGuard code. A new `.flowguard/physicsguard_evidence_mesh_model.py` models the evidence route itself so the development/release process has executable FlowGuard coverage.

Alternative considered: import FlowGuard helper objects directly into PhysicsGuard runtime artifacts. Rejected because PhysicsGuard should not depend on FlowGuard as a runtime package dependency.

## Risks / Trade-offs

- Risk: The new artifact is detailed and can become tedious to author. Mitigation: provide a compact example and make summary output clear.
- Risk: Claims may become blocked more often. Mitigation: support explicit scoped gaps with reasons while preserving broad-claim blockers.
- Risk: Evidence can go stale after another AI changes files. Mitigation: use receipt freshness fields and rerun closure after local install/version sync.
- Risk: This first version may not prove every future finite boundary. Mitigation: require route-specific receipts and make missing route coverage visible as maintenance gaps.

## Migration Plan

1. Add schema/core/CLI support and tests.
2. Add the pump-loop example mesh and closure integration.
3. Add FlowGuard model and ledger coverage.
4. Update docs, OpenSpec tasks, version anchors, changelog, and installed local package.
5. Validate with FlowGuard, OpenSpec, CLI checks, focused pytest, full pytest, and project closure.
