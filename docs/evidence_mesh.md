# Evidence Mesh

Evidence mesh is the strong claim-readiness layer for PhysicsGuard projects. It
borrows the FlowGuard idea that a parent claim is not allowed to pass just
because each child check is green locally. The parent must consume current child
evidence, and the final risk row must consume every required route.

It is not physical correctness proof. It proves that the declared evidence chain
is closed for a specific PhysicsGuard claim boundary.

## Command

```powershell
python -m physicsguard.cli evidence mesh-check EVIDENCE_MESH.yaml --pretty
```

The command exits with code `0` only when the mesh status is `pass`.

## What The Mesh Checks

An evidence mesh has six route sections:

| Section | What must be true |
| --- | --- |
| `model_mesh` | Parent mesh rows consume current child-model evidence. |
| `model_test_alignment` | Required model obligations bind to owner code contracts and current external or mixed tests. |
| `contract_exhaustion` | Required bad cases are generated, have an oracle, and are consumed downstream. |
| `test_mesh` | Parent test suites consume current child suites; progress-only evidence cannot pass. |
| `field_lifecycle` | Behavior-bearing fields have projections, downstream evidence, and old-field disposition when needed. |
| `risk_ledger` | The final claim row is current and consumes all required route receipts. |

## Minimal Shape

```yaml
mesh_id: pump_loop_validation_evidence_mesh
claim_scope: validation_ready
required_routes:
  - model_mesh
  - model_test_alignment
  - contract_exhaustion
  - test_mesh
  - field_lifecycle
  - risk_ledger
parent_models: []
child_model_evidence: []
model_obligations: []
code_contracts: []
test_evidence: []
contract_cases: []
test_suites: []
field_lifecycle: []
risk_ledger: []
```

In a real mesh, each required route must have rows. Empty required sections
block the report.

## Project Closure Handoff

Project closure can require one or more meshes:

```yaml
evidence_meshes:
  - evidence_mesh.yaml
required_checks:
  evidence_mesh: true
```

When the mesh fails, project closure also fails and includes the specific mesh
finding, such as a missing parent-child consumption receipt or a risk row that
forgot a required route.

## Example

The pump-loop fixture includes a complete example:

```powershell
python -m physicsguard.cli evidence mesh-check examples/testfile_contracts/pump_loop/evidence_mesh.yaml --pretty
python -m physicsguard.cli project closure examples/testfile_contracts/pump_loop/project_closure_plan.yaml --pretty
```

The fixture remains a low-fidelity relation example. Passing it does not imply a
real pump model or commercial-tool equivalence.
