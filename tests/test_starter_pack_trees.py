from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values


ROOT = Path(__file__).resolve().parents[1] / "examples" / "hierarchical"


@pytest.mark.parametrize("pack", ["coolant_loop", "fuel_cell_system", "building_hvac"])
def test_connected_starter_tree_has_a_measurable_consistent_reference_and_real_faults(pack, monkeypatch) -> None:
    directory = ROOT / pack
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    observed = load_observed_values(directory / "nominal_observed.yaml")
    original_inputs = spec.model_dump(mode="json"), observed.model_dump(mode="json")
    solutions = []
    original_solve = BoundedSolver.solve

    def capture_reference(solver):
        result = original_solve(solver)
        solutions.append(result.variables)
        return result

    monkeypatch.setattr(BoundedSolver, "solve", capture_reference)
    runner = HierarchicalAuditRunner(spec, directory)
    reference = runner.run()
    assert reference.optimization_success and reference.audit_pass
    assert len(solutions) == 1
    assert 0 < len(observed.variables) < len(solutions[0])
    for name, value in observed.variables.items():
        assert value.value == pytest.approx(solutions[0][name], rel=1e-8, abs=1e-8)
        assert value.unit and value.external_signal and value.source

    monkeypatch.setattr(BoundedSolver, "solve", lambda *args, **kwargs: pytest.fail("observed audits must not reference-solve"))
    evaluated = runner.evaluate_observed(observed, skip_unobserved=True)
    assert evaluated.audit_pass and evaluated.checked_residuals
    assert not evaluated.unchecked_residuals and not evaluated.missing_required_variables
    assert all(row["consistent"] is True for row in evaluated.refinement_checks)
    variants = evaluate_fault_variants(spec, observed, base_dir=directory)
    assert variants["nominal_audit_pass"] and variants["ok"]
    declarations = {variant.id: variant for variant in spec.fault_variants}
    assert any(variant.kind == "fault" for variant in declarations.values())
    assert any(variant.kind == "benign" for variant in declarations.values())
    for row in variants["variants"]:
        if declarations[row["id"]].kind == "fault":
            assert row["detected"] and row["expect_blocks_met"] and not row["audit_pass"]
        else:
            assert row["neutral"] and row["audit_pass"]

    description = describe_hierarchy(spec)
    assert not description["unassigned_components"]
    assert len(description["blocks"]) == len(spec.hierarchy.blocks)
    assert any(connection["scope"] == "between_blocks" for connection in description["connections"])
    blocks = {block.id: block for block in spec.hierarchy.blocks}
    assert any(block.refines for block in blocks.values())
    for block in blocks.values():
        if block.refines:
            assert set(block.refines) <= set(blocks[block.parent_id].components)
    assert (spec.model_dump(mode="json"), observed.model_dump(mode="json")) == original_inputs
